"""Smoke tests for the initial PyQt6 main window."""

from threading import Event

import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QDialog,
    QMessageBox,
    QMenuBar,
    QPlainTextEdit,
    QSplitter,
)

from pyvagui.gui.main_window import MainWindow
from pyvagui.gui.result_tab import ResultTab
from pyvagui.model.layup import LayerSpec, LayerType, Layup
from pyvagui.model.materials import EquivalentFluidSpec, FluidSpec, IsoMatSpec
from pyvagui.model.project import Project
from pyvagui.model.library import MaterialLibrary
from pyvagui.model.solvers import (
    FrequencySettings,
    SolverSpec,
    SolverType,
)


def test_main_window_has_menus_splitter_log_and_status(qtbot):
    """Create the main UI shell and verify its primary widgets."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert window.windowTitle() == "pyvaGUI - Untitled project"
    assert isinstance(window.menuBar(), QMenuBar)
    assert isinstance(window.splitter, QSplitter)
    assert window.splitter.orientation().value == 1
    assert isinstance(window.log_panel, QPlainTextEdit)
    assert window.log_panel.isReadOnly()
    assert window.statusBar().currentMessage() == "Ready"
    assert not window.progress_bar.isVisible()
    assert not window.cancel_button.isVisible()


def test_project_tree_groups_materials_and_stores_object_ids(qtbot):
    """Group model objects and keep stable ids separate from display names."""
    air = FluidSpec(name="Air")
    fibre = EquivalentFluidSpec(name="Glass wool")
    aluminium = IsoMatSpec(name="Aluminium")
    project = Project(
        name="Absorber",
        materials=[air, fibre, aluminium],
    )
    window = MainWindow(project)
    qtbot.addWidget(window)

    materials_root = window.model_tree.topLevelItem(0)
    fluid_group = materials_root.child(0)
    equivalent_group = materials_root.child(1)
    isomat_group = materials_root.child(3)

    assert materials_root.text(0) == "Materials"
    assert fluid_group.child(0).text(0) == "Air"
    assert fluid_group.child(0).data(0, Qt.ItemDataRole.UserRole) == air.id
    assert equivalent_group.child(0).text(0) == "Glass wool"
    assert equivalent_group.child(0).data(
        0, Qt.ItemDataRole.UserRole
    ) == fibre.id
    assert (
        isomat_group.child(0).data(0, Qt.ItemDataRole.UserRole)
        == aluminium.id
    )
    assert not materials_root.flags() & Qt.ItemFlag.ItemIsEditable
    assert window.windowTitle() == "pyvaGUI - Absorber"


def test_project_tree_refresh_shows_unsaved_marker(qtbot):
    """Reflect project dirty state and new objects in the model tree."""
    project = Project(name="Absorber")
    window = MainWindow(project)
    qtbot.addWidget(window)
    material = FluidSpec(name="Water")
    project.add_material(material)

    window.refresh_project_view()

    assert window.windowTitle() == "pyvaGUI - Absorber*"
    assert (
        window.model_tree.topLevelItem(0).child(0).child(0).text(0)
        == "Water"
    )


def test_log_adds_timestamped_severity_and_message(qtbot):
    """Add a readable severity-tagged line to the read-only log panel."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.log("warning", "Calculation is waiting")

    entry = window.log_panel.toPlainText()
    assert "[WARNING] Calculation is waiting" in entry
    assert len(entry.split(" ", maxsplit=1)[0]) == 10


def test_log_rejects_unknown_severity(qtbot):
    """Reject misspelled log severity levels."""
    window = MainWindow()
    qtbot.addWidget(window)

    with pytest.raises(ValueError, match="TRACE"):
        window.log("TRACE", "Not supported")


def test_save_and_load_project_updates_window_state(qtbot, tmp_path):
    """Persist and reload through the same operations used by File actions."""
    project = Project(name="Saved absorber", materials=[FluidSpec(name="Air")])
    window = MainWindow(project)
    qtbot.addWidget(window)
    project.is_modified = True
    path = tmp_path / "absorber.json"

    assert window._save_project_to(path)
    assert window.windowTitle() == "pyvaGUI - Saved absorber"
    assert not project.is_modified

    window.project = Project(name="Temporary")
    assert window._load_project(path)
    assert window.project.name == "Saved absorber"
    assert window.project.file_path == path
    assert window.model_tree.topLevelItem(0).child(0).child(0).text(0) == "Air"


def test_open_project_action_loads_selected_file(qtbot, monkeypatch, tmp_path):
    """Open the selected project through the File menu action handler."""
    path = tmp_path / "selected.json"
    Project(name="Selected", materials=[FluidSpec(name="Air")]).save(path)
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: (str(path), "pyvaGUI project (*.json)"),
    )

    window.open_project_action.trigger()

    assert window.project.name == "Selected"
    assert window.windowTitle() == "pyvaGUI - Selected"
    assert window.model_tree.topLevelItem(0).child(0).child(0).text(0) == "Air"


def test_save_as_action_adds_json_extension(qtbot, monkeypatch, tmp_path):
    """Append the default JSON suffix when the save dialog omits one."""
    window = MainWindow(Project(name="My absorber"))
    qtbot.addWidget(window)
    path = tmp_path / "saved-project"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args: (str(path), "pyvaGUI project (*.json)"),
    )

    window.save_project_as_action.trigger()

    assert (tmp_path / "saved-project.json").exists()
    assert window.project.file_path == tmp_path / "saved-project.json"
    assert window.windowTitle() == "pyvaGUI - My absorber"


def test_new_project_action_discards_changes_when_confirmed(
    qtbot,
    monkeypatch,
):
    """Replace the project after the user confirms discard."""
    window = MainWindow(Project(name="Changed", is_modified=True))
    qtbot.addWidget(window)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Discard,
    )

    window.new_project_action.trigger()

    assert window.project.name == "Untitled project"
    assert window.project.is_modified is False
    assert window.windowTitle() == "pyvaGUI - Untitled project"


def test_new_layup_action_adds_editor_result(qtbot, monkeypatch):
    """Add a valid layup returned by the New Layup dialog."""
    air = FluidSpec(name="Air")
    project = Project(materials=[air])
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_layup(dialog):
        dialog.result_layup = Layup(
            name="Air gap",
            layers=[
                LayerSpec(
                    material_id=air.id,
                    thickness=0.02,
                    layer_type=LayerType.FLUID,
                )
            ],
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.LayupEditorDialog.exec",
        accept_layup,
    )

    window.new_layup_action.trigger()

    assert len(project.layups) == 1
    assert project.layups[0].name == "Air gap"
    assert project.is_modified
    assert window.model_tree.topLevelItem(1).child(0).text(0) == "Air gap"


def test_double_click_handler_updates_existing_layup(qtbot, monkeypatch):
    """Commit an accepted edit to an existing tree-selected layup."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Original",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    project = Project(materials=[air], layups=[layup])
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_edit(dialog):
        dialog.result_layup = Layup(
            id=dialog.layup.id,
            name="Edited",
            layers=dialog.layup.layers,
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.LayupEditorDialog.exec",
        accept_edit,
    )
    layup_item = window.model_tree.topLevelItem(1).child(0)

    window.edit_tree_item(layup_item)

    assert project.layups[0].name == "Edited"
    assert project.is_modified
    assert window.model_tree.topLevelItem(1).child(0).text(0) == "Edited"


def test_new_solver_action_adds_result_tab(qtbot, monkeypatch):
    """Add an accepted solver and create its matching placeholder tab."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Absorber",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.05,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    project = Project(materials=[air], layups=[layup])
    solver = SolverSpec(
        name="Normal absorption",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=11,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[layup.id],
    )
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_solver(dialog):
        dialog.result_solver = solver
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.SolverEditorDialog.exec",
        accept_solver,
    )

    window.new_solver_action.trigger()

    assert project.solvers == [solver]
    assert project.is_modified
    assert window.model_tree.topLevelItem(2).child(0).text(0) == solver.name
    assert window.results_tabs.count() == 1
    assert window.results_tabs.tabText(0) == solver.name
    assert window.results_tabs.widget(0).property("solver_id") == solver.id


def test_double_click_handler_updates_existing_solver(qtbot, monkeypatch):
    """Commit an accepted solver edit from its project tree item."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Absorber",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.05,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    solver = SolverSpec(
        name="Original solver",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=11,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[layup.id],
    )
    project = Project(materials=[air], layups=[layup], solvers=[solver])
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_edit(dialog):
        dialog.result_solver = SolverSpec(
            id=solver.id,
            name="Edited solver",
            solver_type=solver.solver_type,
            frequencies=solver.frequencies,
            sending_fluid_id=solver.sending_fluid_id,
            receiving_fluid_id=solver.receiving_fluid_id,
            layup_ids=solver.layup_ids,
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.SolverEditorDialog.exec",
        accept_edit,
    )
    solver_item = window.model_tree.topLevelItem(2).child(0)

    window.edit_tree_item(solver_item)

    assert project.solvers[0].name == "Edited solver"
    assert project.is_modified
    assert window.results_tabs.tabText(0) == "Edited solver"


def make_solver_project():
    """Create a valid solver project for threaded GUI tests."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Air layer",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.05,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    solver = SolverSpec(
        name="Absorption run",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=1000.0,
            n_points=3,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[layup.id],
    )
    return Project(materials=[air], layups=[layup], solvers=[solver]), solver


def test_run_solver_uses_thread_and_updates_result_tab(qtbot, monkeypatch):
    """Run a mocked solver on QThread and pass its result to the GUI."""
    project, solver = make_solver_project()
    window = MainWindow(project)
    qtbot.addWidget(window)
    monkeypatch.setattr(
        SolverSpec,
        "run",
        lambda self, layup, materials: np.array([0.1, 0.5, 0.9]),
    )

    assert window.run_solver(solver.id)
    qtbot.waitUntil(lambda: window.calculation_thread is None, timeout=5000)

    result = window.result_sets[solver.id]
    result_tab = window.results_tabs.widget(0)
    assert isinstance(result_tab, ResultTab)
    assert len(result.results) == 1
    assert np.array_equal(result.results[0].values, [0.1, 0.5, 0.9])
    assert result_tab.result_placeholder.text() == (
        "1 layup results calculated"
    )
    assert len(result_tab.axes) == 1
    assert result_tab.axes[0].get_xscale() == "log"
    assert np.array_equal(
        result_tab.axes[0].lines[0].get_ydata(),
        [0.1, 0.5, 0.9],
    )
    assert not window.progress_bar.isVisible()
    assert not window.cancel_button.isVisible()


def test_result_tab_run_button_passes_its_solver_id(qtbot, monkeypatch):
    """Use the tab's solver identifier, not the clicked(bool) signal value."""
    project, solver = make_solver_project()
    window = MainWindow(project)
    qtbot.addWidget(window)
    calls = []
    monkeypatch.setattr(
        window,
        "run_solver",
        lambda solver_id: calls.append(solver_id),
    )

    window.results_tabs.widget(0).run_button.click()

    assert calls == [solver.id]


def test_cancel_button_stops_before_next_layup(qtbot, monkeypatch):
    """Request cancel from the UI while the first layup is being calculated."""
    project, solver = make_solver_project()
    second_layup = Layup(
        name="Second layer",
        layers=[
            LayerSpec(
                material_id=project.materials[0].id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    project.add_layup(second_layup)
    solver.layup_ids.append(second_layup.id)
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.show()
    calculation_started = Event()
    continue_calculation = Event()

    def wait_for_cancel(self, layup, materials):
        calculation_started.set()
        continue_calculation.wait(timeout=5)
        return np.array([0.2, 0.4, 0.6])

    monkeypatch.setattr(SolverSpec, "run", wait_for_cancel)

    assert window.run_solver(solver.id)
    qtbot.waitUntil(calculation_started.is_set, timeout=5000)
    assert window.cancel_button.isVisible()
    window.cancel_button.click()
    continue_calculation.set()
    qtbot.waitUntil(lambda: window.calculation_thread is None, timeout=5000)

    assert window.calculation_worker is None
    assert len(window.result_sets[solver.id].results) == 1
    assert not window.cancel_button.isVisible()


def test_run_error_is_reported_and_thread_is_cleaned(qtbot, monkeypatch):
    """Show worker errors and restore controls after a failed calculation."""
    project, solver = make_solver_project()
    window = MainWindow(project)
    qtbot.addWidget(window)
    errors = []
    monkeypatch.setattr(
        SolverSpec,
        "run",
        lambda self, layup, materials: (_ for _ in ()).throw(
            RuntimeError("test calculation failure")
        ),
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, message: errors.append(message),
    )

    assert window.run_solver(solver.id)
    qtbot.waitUntil(lambda: window.calculation_thread is None, timeout=5000)

    assert errors == ["test calculation failure"]
    assert window.result_sets == {}
    assert not window.progress_bar.isVisible()
    assert not window.cancel_button.isVisible()


def test_run_solver_validation_blocks_worker_start(qtbot, monkeypatch):
    """Show project validation errors before creating a calculation thread."""
    solver = SolverSpec(
        name=" ",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=0.0,
            f_end=100.0,
            n_points=1,
        ),
    )
    project = Project(solvers=[solver])
    window = MainWindow(project)
    qtbot.addWidget(window)
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    started = window.run_solver(solver.id)

    assert started is False
    assert window.calculation_thread is None
    assert len(messages) == 1
    assert "Solver name must not be empty" in messages[0]
    assert "Number of points must be an integer" in messages[0]


def test_close_during_calculation_requests_cancel_and_defers_close(
    qtbot,
    monkeypatch,
):
    """Cancel a running worker without destroying its QThread parent."""
    project, solver = make_solver_project()
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.show()
    calculation_started = Event()
    continue_calculation = Event()

    def wait_for_cancel(self, layup, materials):
        calculation_started.set()
        continue_calculation.wait(timeout=5)
        return np.array([0.2, 0.4, 0.6])

    monkeypatch.setattr(SolverSpec, "run", wait_for_cancel)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Discard,
    )

    assert window.run_solver(solver.id)
    qtbot.waitUntil(calculation_started.is_set, timeout=5000)
    close_result = window.close()
    assert close_result is False
    assert window.isVisible()
    continue_calculation.set()
    qtbot.waitUntil(lambda: window.calculation_thread is None, timeout=5000)

    assert len(window.result_sets[solver.id].results) == 1
    assert window.isVisible()


def test_end_to_end_project_creation_to_result_curve(
    qtbot,
    monkeypatch,
    tmp_path,
):
    """Create model objects, run the worker, and plot its result."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.new_project()
    library = MaterialLibrary(tmp_path / "library.json")
    monkeypatch.setattr(window, "_get_material_library", lambda: library)
    materials_to_add = iter(
        [
            FluidSpec(name="Air"),
            EquivalentFluidSpec(name="Glass wool"),
        ]
    )

    def accept_material(dialog):
        dialog.material = next(materials_to_add)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.MaterialEditorDialog.exec",
        accept_material,
    )
    window.new_material_action.trigger()
    window.new_material_action.trigger()
    air = next(item for item in window.project.materials if item.name == "Air")
    wool = next(
        item
        for item in window.project.materials
        if item.name == "Glass wool"
    )

    def accept_layup(dialog):
        dialog.result_layup = Layup(
            name="Glass wool absorber",
            layers=[
                LayerSpec(
                    material_id=wool.id,
                    thickness=0.1,
                    layer_type=LayerType.FLUID,
                )
            ],
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.LayupEditorDialog.exec",
        accept_layup,
    )
    window.new_layup_action.trigger()
    layup = window.project.layups[0]

    def accept_solver(dialog):
        dialog.result_solver = SolverSpec(
            name="Normal absorption",
            solver_type=SolverType.ABSORPTION,
            frequencies=FrequencySettings(
                f_start=100.0,
                f_end=1000.0,
                n_points=5,
            ),
            sending_fluid_id=air.id,
            receiving_fluid_id=air.id,
            layup_ids=[layup.id],
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.SolverEditorDialog.exec",
        accept_solver,
    )
    window.new_solver_action.trigger()
    solver = window.project.solvers[0]
    monkeypatch.setattr(
        SolverSpec,
        "run",
        lambda self, layup, materials: np.array(
            [0.2, 0.5, 0.8, 0.9, 0.95]
        ),
    )

    assert window.run_solver(solver.id)
    qtbot.waitUntil(lambda: window.calculation_thread is None, timeout=10000)

    result_tab = window.results_tabs.widget(0)
    assert isinstance(result_tab, ResultTab)
    assert len(result_tab.axes) == 1
    assert len(result_tab.axes[0].lines) == 1
    assert list(result_tab.axes[0].lines[0].get_xdata()) == list(
        solver.frequencies.frequencies()
    )
    assert len(window.result_sets[solver.id].results) == 1
    qtbot.wait(50)


def test_close_event_is_ignored_when_prompt_is_cancelled(
    qtbot,
    monkeypatch,
):
    """Keep a visible window open when the user cancels closing."""
    window = MainWindow(Project(name="Changed", is_modified=True))
    qtbot.addWidget(window)
    window.show()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Cancel,
    )

    closed = window.close()

    assert closed is False
    assert window.isVisible()


@pytest.mark.parametrize(
    ("answer", "should_continue"),
    [
        (QMessageBox.StandardButton.Discard, True),
        (QMessageBox.StandardButton.Cancel, False),
    ],
)
def test_unsaved_changes_prompt_honors_discard_and_cancel(
    qtbot,
    monkeypatch,
    answer,
    should_continue,
):
    """Only discard continues; cancellation preserves the current project."""
    project = Project(name="Changed", is_modified=True)
    window = MainWindow(project)
    qtbot.addWidget(window)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: answer)

    result = window._confirm_discard_changes()

    assert result is should_continue
    assert window.project is project
