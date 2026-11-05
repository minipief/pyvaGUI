"""Tests for matplotlib result tabs and their export actions."""

import csv

import numpy as np
import pytest
from matplotlib.backend_bases import MouseEvent
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from pyvagui.gui.result_tab import ResultTab
from pyvagui.model.results import LayupResult, ResultSet
from pyvagui.model.solvers import FrequencySettings, SolverSpec, SolverType


def make_result_set(solver_type, values):
    """Build a result set with two named layup curves."""
    return ResultSet(
        solver_id="solver-id",
        solver_name="Test solver",
        solver_type=solver_type,
        frequencies=np.array([100.0, 1000.0, 10000.0]),
        labels=["100", "1k", "10k"],
        results=[
            LayupResult(
                layup_id=f"layup-{index}",
                layup_name=name,
                values=array,
            )
            for index, (name, array) in enumerate(
                zip(("Glass wool", "Air gap"), values)
            )
        ],
    )


def make_solver(solver_type):
    """Create the minimal solver settings required by a result tab."""
    return SolverSpec(
        name="Test solver",
        solver_type=solver_type,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=3,
        ),
    )


def test_real_result_tab_plots_layups_on_log_frequency_axis(qtbot):
    """Plot one curve per layup with logarithmic frequency and labels."""
    solver = make_solver(SolverType.ABSORPTION)
    tab = ResultTab(solver, lambda: None)
    qtbot.addWidget(tab)
    result_set = make_result_set(
        SolverType.ABSORPTION,
        [np.array([0.2, 0.5, 0.8]), np.array([0.1, 0.4, 0.7])],
    )

    tab.set_results(result_set)

    assert len(tab.axes) == 1
    assert tab.axes[0].get_xscale() == "log"
    assert tab.axes[0].get_ylabel() == "Absorption coefficient [-]"
    assert [line.get_label() for line in tab.axes[0].lines] == [
        "Glass wool",
        "Air gap",
    ]
    assert tab.hint_label.isHidden()
    assert tab.export_button.isEnabled()
    assert not tab.run_button.icon().isNull()
    assert not tab.export_button.icon().isNull()


@pytest.mark.parametrize("solver_type", [
    SolverType.ABSORPTION, SolverType.ABSORPTION_DIFFUSE,
])
def test_absorption_y_axis_click_cycles_display_variants(qtbot, solver_type):
    tab = ResultTab(make_solver(solver_type), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(make_result_set(
        solver_type, [np.array([0.2, 0.5, 0.8])],
    ))
    expected = [
        ("Absorption coefficient [%]", [20, 50, 80]),
        ("Reflection coefficient 1 - alpha [-]", [0.8, 0.5, 0.2]),
        ("Reflection magnitude |r| [-]", np.sqrt([0.8, 0.5, 0.2])),
        ("Reflection attenuation [dB]", -10 * np.log10([0.8, 0.5, 0.2])),
        ("Absorption coefficient [-]", [0.2, 0.5, 0.8]),
    ]
    for label, values in expected:
        bounds = tab.axes[0].yaxis.label.get_window_extent(
            tab.canvas.get_renderer()
        )
        event = MouseEvent(
            "button_press_event", tab.canvas,
            (bounds.x0 + bounds.x1) / 2,
            (bounds.y0 + bounds.y1) / 2, button=1,
        )
        tab.canvas.callbacks.process("button_press_event", event)
        assert tab.axes[0].get_ylabel() == label
        np.testing.assert_allclose(tab.axes[0].lines[0].get_ydata(), values)
        assert tab.axes[0].get_xscale() == "log"


@pytest.mark.parametrize("solver_type", [
    SolverType.TRANSMISSION, SolverType.TRANSMISSION_DIFFUSE,
    SolverType.TRANSMISSION_ALLARD,
])
def test_transmission_spine_click_cycles_variants(qtbot, solver_type):
    tab = ResultTab(make_solver(solver_type), lambda: None)
    qtbot.addWidget(tab)
    result = make_result_set(solver_type, [np.array([1.0, 0.1, 0.01])])
    tab.set_results(result)
    views = list(result.display_views())
    for view in views[1:] + views[:1]:
        axis = tab.axes[0]
        event = MouseEvent(
            "button_press_event", tab.canvas, axis.bbox.x0,
            (axis.bbox.y0 + axis.bbox.y1) / 2, button=1,
        )
        tab.canvas.callbacks.process("button_press_event", event)
        assert tab.axes[0].get_ylabel() == result.display_views()[view]
        np.testing.assert_allclose(
            tab.axes[0].lines[0].get_ydata(),
            result.display_values(result.results[0].values, view),
        )
        assert tab.axes[0].get_xscale() == "log"


def test_impedance_axis_cycles_independently_and_preserves_selection(qtbot):
    tab = ResultTab(make_solver(SolverType.IMPEDANCE), lambda: None)
    qtbot.addWidget(tab)
    result = make_result_set(
        SolverType.IMPEDANCE, [np.array([400 + 100j, 800 + 0j, 200j])],
    )
    result.reference_impedance = 400.0
    result.angle_deg = 60.0
    tab.set_results(result)
    views = list(result.display_views())
    for view in views[1:] + views[:1]:
        axis = tab.axes[0]
        bounds = axis.yaxis.label.get_window_extent(tab.canvas.get_renderer())
        event = MouseEvent(
            "button_press_event", tab.canvas,
            (bounds.x0 + bounds.x1) / 2,
            (bounds.y0 + bounds.y1) / 2, button=1,
        )
        tab.canvas.callbacks.process("button_press_event", event)
        assert tab.axes[0].get_ylabel() == result.display_views()[view]
        np.testing.assert_allclose(
            tab.axes[0].lines[0].get_ydata(),
            result.display_values(result.results[0].values, view),
        )
        assert tab.axes[1].get_ylabel() == "Impedance phase [deg]"
    tab._display_views["magnitude"] = "normalized_real"
    tab.view_checkboxes["real"].setChecked(True)
    assert tab.axes[0].get_ylabel() == (
        result.display_views()["normalized_real"]
    )


def test_plot_click_does_not_change_display(qtbot):
    tab = ResultTab(make_solver(SolverType.ABSORPTION), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(make_result_set(
        SolverType.ABSORPTION, [np.array([0.2, 0.5, 0.8])],
    ))
    axis = tab.axes[0]
    event = MouseEvent(
        "button_press_event", tab.canvas,
        *axis.transData.transform((1000.0, 0.5)), button=1,
    )
    tab.canvas.callbacks.process("button_press_event", event)
    assert tab.axes[0] is axis
    assert not tab._display_views


def test_csv_export_uses_axis_display_variant(qtbot, monkeypatch, tmp_path):
    tab = ResultTab(make_solver(SolverType.TRANSMISSION), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(make_result_set(
        SolverType.TRANSMISSION, [np.array([1.0, 0.1, 0.01])],
    ))
    tab._display_views["value"] = "transmission_loss"
    tab.redraw()
    path = tmp_path / "loss.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *args: (str(path), "CSV (*.csv)"),
    )
    tab.export_results()
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    assert rows[0][1] == "Glass wool | Sound reduction index R [dB]"
    np.testing.assert_allclose(
        [float(row[1]) for row in rows[1:]], [0, 10, 20],
    )


def test_complex_result_tab_defaults_to_magnitude_and_phase(qtbot):
    """Create one subplot for each selected impedance view."""
    tab = ResultTab(make_solver(SolverType.IMPEDANCE), lambda: None)
    qtbot.addWidget(tab)
    result_set = make_result_set(
        SolverType.IMPEDANCE,
        [
            np.array([1 + 1j, 2 + 2j, 3 + 3j]),
            np.array([1 + 0j, 0 + 1j, -1 + 0j]),
        ],
    )

    tab.set_results(result_set)

    assert not tab.complex_view_panel.isHidden()
    assert tab.view_checkboxes["magnitude"].isChecked()
    assert tab.view_checkboxes["phase"].isChecked()
    assert not tab.view_checkboxes["real"].isChecked()
    assert len(tab.axes) == 2
    assert all(axis.get_xscale() == "log" for axis in tab.axes)
    assert tab.axes[0].get_ylabel() == "Impedance magnitude |Z| [Pa s/m]"
    assert tab.axes[1].get_ylabel() == "Impedance phase [deg]"
    assert tab.axes[0].get_title() == "Magnitude"
    assert tab.axes[1].get_title() == "Phase"

    tab.view_checkboxes["real"].setChecked(True)
    assert len(tab.axes) == 3
    assert tab.axes[2].get_title() == "Real part"


def test_plot_hover_previews_nearest_line_value(qtbot):
    """Choose the nearest curve when multiple result lines are visible."""
    tab = ResultTab(make_solver(SolverType.ABSORPTION), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(
        make_result_set(
            SolverType.ABSORPTION,
            [
                np.array([0.2, 0.5, 0.8]),
                np.array([0.1, 0.4, 0.7]),
            ],
        )
    )
    tab.canvas.draw()
    axis = tab.axes[0]
    x, y = axis.transData.transform((1000.0, 0.4))
    event = MouseEvent("motion_notify_event", tab.canvas, x, y)

    tab._on_plot_hover(event)

    annotation, marker = tab._hover_artists[axis]
    assert annotation.get_visible()
    assert "Air gap" in annotation.get_text()
    assert "1000 Hz" in annotation.get_text()
    assert "Value: 0.4" in annotation.get_text()
    assert np.allclose(marker.get_offsets(), [[1000.0, 0.4]])


def test_plot_hover_preview_flips_inside_top_right_border(qtbot):
    """Flip the hover annotation inward near the plot's top-right edge."""
    tab = ResultTab(make_solver(SolverType.ABSORPTION), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(
        make_result_set(
            SolverType.ABSORPTION,
            [
                np.array([0.2, 0.5, 0.8]),
                np.array([0.1, 0.4, 0.7]),
            ],
        )
    )
    tab.canvas.draw()
    axis = tab.axes[0]
    x, y = axis.transData.transform((10000.0, 0.8))
    event = MouseEvent("motion_notify_event", tab.canvas, x, y)

    tab._on_plot_hover(event)
    tab.canvas.draw()

    annotation, _ = tab._hover_artists[axis]
    bounds = annotation.get_window_extent(tab.canvas.get_renderer())

    assert annotation.get_position() == (-12, -12)
    assert bounds.x0 >= axis.bbox.x0
    assert bounds.x1 <= axis.bbox.x1
    assert bounds.y0 >= axis.bbox.y0
    assert bounds.y1 <= axis.bbox.y1


def test_result_tab_run_button_calls_main_window_callback(qtbot):
    """Send Run clicks to the callback provided by MainWindow."""
    calls = []
    tab = ResultTab(
        make_solver(SolverType.TRANSMISSION),
        lambda: calls.append(1),
    )
    qtbot.addWidget(tab)

    qtbot.mouseClick(tab.run_button, Qt.MouseButton.LeftButton)

    assert calls == [1]


def test_result_tab_exports_csv_with_selected_complex_views(
    qtbot,
    monkeypatch,
    tmp_path,
):
    """Export chosen impedance views to the selected CSV path."""
    tab = ResultTab(make_solver(SolverType.IMPEDANCE), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(
        make_result_set(
            SolverType.IMPEDANCE,
            [
                np.array([3 + 4j, 2 + 0j, 0 + 1j]),
                np.array([1 + 0j, 0 + 1j, -1 + 0j]),
            ],
        )
    )
    tab.view_checkboxes["magnitude"].setChecked(True)
    tab.view_checkboxes["phase"].setChecked(False)
    path = tmp_path / "impedance.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args: (str(path), "CSV (*.csv)"),
    )
    messages = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args: messages.append(args)
    )

    tab.export_results()

    assert not messages
    assert str(path) in tab.export_status_label.text()
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    assert rows[0] == [
        "Frequency [Hz]",
        "Glass wool | magnitude",
        "Air gap | magnitude",
    ]
    assert rows[1] == ["100.0", "5.0", "1.0"]


@pytest.mark.parametrize(
    ("extension", "image_filter", "signature"),
    [
        ("png", "PNG image (*.png)", b"\x89PNG"),
        ("svg", "SVG image (*.svg)", b"<?xml"),
    ],
)
def test_result_tab_exports_figure_as_image(
    qtbot,
    monkeypatch,
    tmp_path,
    extension,
    image_filter,
    signature,
):
    """Export the displayed Matplotlib figure as PNG or SVG."""
    tab = ResultTab(make_solver(SolverType.ABSORPTION), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(
        make_result_set(
            SolverType.ABSORPTION,
            [np.array([0.2, 0.5, 0.8]), np.array([0.1, 0.4, 0.7])],
        )
    )
    path = tmp_path / f"absorption.{extension}"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args: (str(path), image_filter),
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)

    tab.export_results()

    assert path.read_bytes().startswith(signature)


def test_result_tab_run_signal_uses_provided_callback(qtbot):
    """Call the configured run handler when the button is clicked."""
    calls = []
    tab = ResultTab(
        make_solver(SolverType.ABSORPTION),
        lambda: calls.append("run"),
    )
    qtbot.addWidget(tab)

    tab.run_button.click()

    assert calls == ["run"]


@pytest.mark.parametrize(
    ("solver_type", "expected_label"),
    [
        (SolverType.TRANSMISSION, "Transmission coefficient tau [-]"),
        (SolverType.TRANSMISSION_DIFFUSE, "Transmission coefficient tau [-]"),
        (SolverType.TRANSMISSION_ALLARD, "Transmission coefficient tau [-]"),
    ],
)
def test_transmission_result_tabs_use_transmission_axis_label(
    qtbot,
    solver_type,
    expected_label,
):
    """Use a transmission-specific axis label for all transmission modes."""
    tab = ResultTab(make_solver(solver_type), lambda: None)
    qtbot.addWidget(tab)
    tab.set_results(
        make_result_set(
            solver_type,
            [np.array([0.1, 0.2, 0.3]), np.array([0.3, 0.2, 0.1])],
        )
    )

    assert tab.axes[0].get_ylabel() == expected_label
