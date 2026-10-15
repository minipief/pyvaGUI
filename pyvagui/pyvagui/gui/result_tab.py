"""Matplotlib result page for one solver configuration."""

from pathlib import Path
from typing import Callable

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyvagui.gui.tree_icons import ACTION_ICONS
from pyvagui.model.results import ResultSet
from pyvagui.model.solvers import SolverSpec, SolverType
from pyvagui.services.export import export_csv, export_image


COMPLEX_VIEWS = (
    ("magnitude", "Magnitude"),
    ("phase", "Phase"),
    ("real", "Real part"),
    ("imaginary", "Imaginary part"),
)


class ResultTab(QWidget):
    """Display and export results for one solver.

    Parameters
    ----------
    solver : SolverSpec
        Solver associated with the tab.
    run_callback : callable
        Function called when the user presses Run.
    parent : QWidget or None, optional
        Parent widget that owns the page.
    """

    def __init__(
        self,
        solver: SolverSpec,
        run_callback: Callable[[], None],
        parent: QWidget | None = None,
    ):
        """Build the result header, canvas, and optional view controls."""
        super().__init__(parent)
        self.solver = solver
        self.run_callback = run_callback
        self.result_set: ResultSet | None = None
        self.figure = Figure(
            figsize=(6, 4), tight_layout=True, facecolor="#ffffff"
        )
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = []
        self._data_lines = {}
        self._hover_artists = {}
        self.canvas.mpl_connect(
            "motion_notify_event",
            self._on_plot_hover,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        header = QHBoxLayout()
        self.title_label = QLabel(f"{solver.name} Results", self)
        self.title_label.setObjectName("titleLabel")
        self.run_button = QPushButton("Run", self)
        self.run_button.setObjectName("primaryButton")
        self.run_button.setIcon(ACTION_ICONS["play-white"])
        self.export_button = QPushButton("Export...", self)
        self.export_button.setIcon(ACTION_ICONS["export"])
        self.export_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_callback)
        self.export_button.clicked.connect(self.export_results)
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.run_button)
        header.addWidget(self.export_button)
        layout.addLayout(header)

        self.complex_view_panel = QWidget(self)
        views_layout = QHBoxLayout(self.complex_view_panel)
        views_layout.setContentsMargins(0, 0, 0, 0)
        self.view_checkboxes: dict[str, QCheckBox] = {}
        for view, label in COMPLEX_VIEWS:
            checkbox = QCheckBox(label, self.complex_view_panel)
            checkbox.setChecked(view in ("magnitude", "phase"))
            checkbox.toggled.connect(self.redraw)
            views_layout.addWidget(checkbox)
            self.view_checkboxes[view] = checkbox
        self.complex_view_panel.setVisible(solver.is_complex())
        layout.addWidget(self.complex_view_panel)

        self.hint_label = QLabel("Press Run to calculate", self)
        self.hint_label.setObjectName("emptyState")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_placeholder = self.hint_label
        layout.addWidget(self.hint_label, stretch=1)
        self.canvas.hide()
        layout.addWidget(self.canvas, stretch=1)

        self.export_status_label = QLabel(self)
        self.export_status_label.setObjectName("successBanner")
        self.export_status_label.setWordWrap(True)
        self.export_status_label.hide()
        layout.addWidget(self.export_status_label)

    def set_results(self, result_set: ResultSet) -> None:
        """Set results for this tab and redraw the chart.

        Parameters
        ----------
        result_set : ResultSet
            Solver results to display.
        """
        self.result_set = result_set
        self.title_label.setText(f"{result_set.solver_name} Results")
        self.hint_label.setText(
            f"{len(result_set.results)} layup results calculated"
        )
        self.hint_label.hide()
        self.canvas.show()
        self.export_button.setEnabled(True)
        self.redraw()

    def redraw(self, checked: bool = False) -> None:
        """Rebuild all axes and curves from the current result set."""
        if self.result_set is None:
            return
        views = self._selected_views()
        self.figure.clear()
        self.axes = []
        self._data_lines = {}
        self._hover_artists = {}
        if not views:
            self.figure.text(
                0.5,
                0.5,
                "Select at least one view",
                ha="center",
                va="center",
            )
            self.canvas.draw()
            return

        axes_grid = self.figure.subplots(
            nrows=len(views),
            ncols=1,
            squeeze=False,
        )
        self.axes = [axes_grid[index][0] for index in range(len(views))]
        frequencies = self.result_set.frequencies
        for axis, view in zip(self.axes, views):
            self._data_lines[axis] = []
            for layup_result in self.result_set.results:
                values = self._values_for_view(layup_result.values, view)
                line, = axis.plot(
                    frequencies,
                    values,
                    label=layup_result.layup_name,
                )
                line.set_pickradius(8)
                self._data_lines[axis].append(line)
            axis.set_xscale("log")
            axis.set_xlabel("Frequency [Hz]")
            axis.set_ylabel(self._y_axis_label())
            axis.grid(True, which="both", alpha=0.25)
            axis.legend()
            annotation = axis.annotate(
                "",
                xy=(0, 0),
                xytext=(12, 12),
                textcoords="offset points",
                bbox={
                    "boxstyle": "round,pad=0.45",
                    "fc": "#ffffff",
                    "ec": "#c3ccd4",
                    "alpha": 0.97,
                },
                arrowprops={"arrowstyle": "->", "color": "#66737e"},
                fontsize=9,
                zorder=20,
            )
            annotation.set_visible(False)
            marker = axis.scatter(
                [],
                [],
                s=34,
                color="#167d70",
                edgecolors="#ffffff",
                linewidths=1.2,
                zorder=19,
            )
            self._hover_artists[axis] = (annotation, marker)
            if self.solver.is_complex():
                axis.set_title(dict(COMPLEX_VIEWS)[view])
        self.figure.tight_layout()
        self.canvas.draw()

    def _on_plot_hover(self, event) -> None:
        """Show the nearest curve's value while the pointer is over it."""
        if event.inaxes not in self._hover_artists:
            self._hide_plot_hover()
            return

        closest = None
        for line in self._data_lines.get(event.inaxes, []):
            contains, details = line.contains(event)
            if not contains:
                continue
            indices = np.asarray(details.get("ind", []), dtype=int)
            if indices.size == 0:
                continue
            x_values = np.asarray(line.get_xdata(), dtype=float)[indices]
            y_values = np.asarray(line.get_ydata(), dtype=float)[indices]
            display_points = event.inaxes.transData.transform(
                np.column_stack((x_values, y_values))
            )
            distances = np.hypot(
                display_points[:, 0] - event.x,
                display_points[:, 1] - event.y,
            )
            nearest_index = int(np.argmin(distances))
            candidate = (
                distances[nearest_index],
                line,
                x_values[nearest_index],
                y_values[nearest_index],
            )
            if closest is None or candidate[0] < closest[0]:
                closest = candidate

        self._hide_plot_hover()
        if closest is None:
            return

        _, line, frequency, value = closest
        annotation, marker = self._hover_artists[event.inaxes]
        annotation.xy = (frequency, value)
        annotation.set_text(
            f"{line.get_label()}\n{frequency:g} Hz\nValue: {value:.6g}"
        )
        annotation.set_visible(True)
        annotation.set_position((12, 12))
        renderer = self.canvas.get_renderer()
        preview_bounds = annotation.get_window_extent(renderer)
        horizontal_offset = (
            -12
            if event.inaxes.bbox.x1 - event.x < preview_bounds.width + 12
            else 12
        )
        vertical_offset = (
            -12
            if event.inaxes.bbox.y1 - event.y < preview_bounds.height + 12
            else 12
        )
        annotation.set_position((horizontal_offset, vertical_offset))
        annotation.set_horizontalalignment(
            "right" if horizontal_offset < 0 else "left"
        )
        annotation.set_verticalalignment(
            "top" if vertical_offset < 0 else "bottom"
        )
        marker.set_offsets([[frequency, value]])
        self.canvas.draw_idle()

    def _hide_plot_hover(self) -> None:
        """Hide hover previews when the pointer leaves a plotted line."""
        changed = False
        for annotation, marker in self._hover_artists.values():
            if annotation.get_visible():
                annotation.set_visible(False)
                marker.set_offsets(np.empty((0, 2)))
                changed = True
        if changed:
            self.canvas.draw_idle()

    def export_results(self) -> None:
        """Export current data as CSV or the figure as PNG/SVG."""
        if self.result_set is None:
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export results",
            f"{self.result_set.solver_name}.csv",
            "CSV (*.csv);;PNG image (*.png);;SVG image (*.svg)",
        )
        if not path:
            return
        target = Path(path)
        if target.suffix == "":
            if selected_filter.startswith("PNG"):
                target = target.with_suffix(".png")
            elif selected_filter.startswith("SVG"):
                target = target.with_suffix(".svg")
            else:
                target = target.with_suffix(".csv")
        try:
            if target.suffix.lower() in (".png", ".svg"):
                export_image(self.figure, target)
            else:
                export_csv(
                    self.result_set,
                    target,
                    self._selected_views(),
                )
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Export results", str(error))
            return
        self.export_status_label.setText(f"Exported results to '{target}'.")
        self.export_status_label.show()

    def _selected_views(self) -> list[str]:
        """Return visible complex views or the single real result view."""
        if not self.solver.is_complex():
            return ["value"]
        return [
            view
            for view, checkbox in self.view_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _values_for_view(self, values: np.ndarray, view: str) -> np.ndarray:
        """Convert complex values to the selected real-valued plot view.

        Parameters
        ----------
        values : numpy.ndarray
            Real or complex result values.
        view : str
            One of magnitude, phase, real, imaginary, or value.

        Returns
        -------
        numpy.ndarray
            Values to plot on the vertical axis.
        """
        if view == "magnitude":
            return np.abs(values)
        if view == "phase":
            return np.angle(values, deg=True)
        if view == "real":
            return np.real(values)
        if view == "imaginary":
            return np.imag(values)
        return np.real(values)

    def _y_axis_label(self) -> str:
        """Return the physical y-axis label for the solver preset."""
        if self.solver.solver_type in (
            SolverType.ABSORPTION,
            SolverType.ABSORPTION_DIFFUSE,
        ):
            return "Absorption coefficient [-]"
        if self.solver.solver_type is SolverType.IMPEDANCE:
            return "Impedance [Pa s/m]"
        return "Transmission coefficient tau [-]"
