"""Main application window and project-management interface."""

from datetime import datetime
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
from PyQt6.QtCore import QProcess, QTimer, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyvagui.gui.library_dialog import LibraryDialog, MATERIAL_GROUPS
from pyvagui.gui.layup_editor import LayupEditorDialog
from pyvagui.gui.material_editor import MaterialEditorDialog
from pyvagui.gui.result_tab import ResultTab
from pyvagui.gui.solver_dialog import SolverEditorDialog
from pyvagui.gui.theme import (
    STYLE_SHEET,
    make_rounded_popup,
    resize_to_screen,
)
from pyvagui.gui.tree_icons import ACTION_ICONS, TREE_ICONS
from pyvagui.model.layup import Layup
from pyvagui.model.library import MaterialLibrary
from pyvagui.model.materials import MaterialSpec, PoroElasticMatSpec, new_id
from pyvagui.model.project import Project
from pyvagui.model.results import LayupResult, ResultSet
from pyvagui.model.solvers import SolverSpec, SolverType


class MainWindow(QMainWindow):
    """Top-level window for project navigation and results."""

    def __init__(self, project: Project | None = None):
        """Build the main window around a project.

        Parameters
        ----------
        project : Project or None, optional
            Project to display. A new empty project is created by default.
        """
        super().__init__()
        self.setStyleSheet(STYLE_SHEET)
        self.project = project if project is not None else Project()
        self._clipboard_objects: list[
            tuple[str, MaterialSpec | Layup | SolverSpec]
        ] = []
        self.material_library: MaterialLibrary | None = None
        self.calculation_process: QProcess | None = None
        self._calculation_temp_dir: tempfile.TemporaryDirectory | None = None
        self._calculation_message_path: Path | None = None
        self._calculation_message_offset = 0
        self._calculation_output_buffer = bytearray()
        self._calculation_stderr = bytearray()
        self._calculation_metadata: dict | None = None
        self._calculation_results: list[LayupResult] = []
        self._calculation_failed_message: str | None = None
        self._calculation_cancelled = False
        self._calculation_busy = False
        self._project_view_initialized = False
        self._tree_fitted_on_show = False
        self._calculation_kill_timer = QTimer(self)
        self._calculation_kill_timer.setSingleShot(True)
        self._calculation_kill_timer.timeout.connect(
            self._kill_calculation_process
        )
        self._calculation_poll_timer = QTimer(self)
        self._calculation_poll_timer.setInterval(100)
        self._calculation_poll_timer.timeout.connect(
            self._read_calculation_output
        )
        self.result_sets: dict[str, ResultSet] = {}
        resize_to_screen(self, 0.85, 0.85)

        self.log_panel = QPlainTextEdit(self)
        self.log_panel.setReadOnly(True)
        self.log_panel.setPlaceholderText("Application log")

        self.model_panel = QWidget(self)
        self.model_panel.setObjectName("modelPanel")
        self.results_panel = QWidget(self)
        self.results_panel.setObjectName("resultsPanel")
        self._build_central_widget()
        self._build_menus()
        self._build_status_bar()
        self.refresh_project_view()

    def _build_central_widget(self) -> None:
        """Arrange the model tree, result placeholder, and log panel."""
        # Layouts calculate widget positions whenever their parent resizes.
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 6)

        # A splitter lets users resize the navigation and results areas.
        splitter = QSplitter(Qt.Orientation.Horizontal, central_widget)
        self.splitter = splitter

        model_layout = QVBoxLayout(self.model_panel)
        model_layout.setContentsMargins(0, 0, 4, 4)
        # QTreeWidget handles visible rows and nested groups directly.
        self.model_tree = QTreeWidget(self.model_panel)
        self.model_tree.setHeaderHidden(True)
        self.model_tree.header().setStretchLastSection(False)
        self.model_tree.setIndentation(14)
        self.model_tree.setUniformRowHeights(True)
        self.model_tree.setSelectionMode(
            QTreeWidget.SelectionMode.ExtendedSelection
        )
        self.model_tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.model_tree.customContextMenuRequested.connect(
            self._show_project_tree_context_menu
        )
        self.model_tree.itemSelectionChanged.connect(
            self._update_delete_action
        )
        self.model_tree.itemDoubleClicked.connect(self.edit_tree_item)
        model_layout.addWidget(self.model_tree)

        results_layout = QVBoxLayout(self.results_panel)
        results_layout.setContentsMargins(4, 0, 0, 4)
        self.results_placeholder = QLabel(
            "No solvers yet\nCreate one with Edit > New solver...",
            self.results_panel,
        )
        self.results_placeholder.setObjectName("emptyState")
        self.results_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_tabs = QTabWidget(self.results_panel)
        results_layout.addWidget(self.results_placeholder, stretch=1)
        results_layout.addWidget(self.results_tabs, stretch=1)

        splitter.addWidget(self.model_panel)
        splitter.addWidget(self.results_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(7)

        self.log_splitter = QSplitter(Qt.Orientation.Vertical, central_widget)
        self.log_splitter.setHandleWidth(7)
        self.log_splitter.setChildrenCollapsible(False)
        self.log_splitter.addWidget(splitter)
        self.log_splitter.addWidget(self.log_panel)
        self.log_splitter.setStretchFactor(0, 1)
        self.log_splitter.setStretchFactor(1, 0)
        self.log_splitter.setSizes([680, 160])
        layout.addWidget(self.log_splitter)
        self.setCentralWidget(central_widget)

    def _build_menus(self) -> None:
        """Create application menus and connect available commands."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        calculation_menu = menu_bar.addMenu("Calculation")
        library_menu = menu_bar.addMenu("Library")
        view_menu = menu_bar.addMenu("View")
        help_menu = menu_bar.addMenu("Help")
        for menu in (
            file_menu,
            edit_menu,
            calculation_menu,
            library_menu,
            view_menu,
            help_menu,
        ):
            make_rounded_popup(menu)
        self.about_action = QAction("About pyvaGUI", self)
        help_menu.addAction(self.about_action)
        self.about_action.triggered.connect(
            lambda: QMessageBox.about(
                self,
                "About pyvaGUI",
                "pyvaGUI - infinite layer calculations with pyva.",
            )
        )

        self.new_project_action = QAction("New project", self)
        self.open_project_action = QAction("Open...", self)
        self.save_project_action = QAction("Save", self)
        self.save_project_as_action = QAction("Save as...", self)
        self.exit_action = QAction("Exit", self)
        for action, shortcut in (
            (self.new_project_action, QKeySequence.StandardKey.New),
            (self.open_project_action, QKeySequence.StandardKey.Open),
            (self.save_project_action, QKeySequence.StandardKey.Save),
            (self.save_project_as_action, QKeySequence.StandardKey.SaveAs),
            (self.exit_action, "Ctrl+Q"),
        ):
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            self.addAction(action)
        for action, icon_name in (
            (self.new_project_action, "new"),
            (self.open_project_action, "open"),
            (self.save_project_action, "save"),
            (self.save_project_as_action, "save"),
            (self.exit_action, "close"),
        ):
            action.setIcon(ACTION_ICONS[icon_name])
        file_menu.addAction(self.new_project_action)
        file_menu.addAction(self.open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_project_action)
        file_menu.addAction(self.save_project_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        self.new_material_action = QAction("New material...", self)
        self.new_layup_action = QAction("New layup...", self)
        self.new_solver_action = QAction("New solver...", self)
        for action, shortcut in (
            (self.new_material_action, "Ctrl+Shift+M"),
            (self.new_layup_action, "Ctrl+Shift+L"),
            (self.new_solver_action, "Ctrl+Shift+E"),
        ):
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            self.addAction(action)
        self.new_material_action.setIcon(ACTION_ICONS["plus"])
        self.new_layup_action.setIcon(TREE_ICONS["layup"])
        self.new_solver_action.setIcon(TREE_ICONS["solver"])
        edit_menu.addAction(self.new_material_action)
        edit_menu.addAction(self.new_layup_action)
        edit_menu.addAction(self.new_solver_action)
        edit_menu.addSeparator()
        self.copy_project_items_action = QAction(
            "Copy selected items",
            self.model_tree,
        )
        self.copy_project_items_action.setShortcut("Ctrl+C")
        self.copy_project_items_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.model_tree.addAction(self.copy_project_items_action)
        edit_menu.addAction(self.copy_project_items_action)
        self.paste_project_items_action = QAction(
            "Paste items",
            self.model_tree,
        )
        self.paste_project_items_action.setShortcut("Ctrl+V")
        self.paste_project_items_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.model_tree.addAction(self.paste_project_items_action)
        edit_menu.addAction(self.paste_project_items_action)
        edit_menu.addSeparator()
        self.delete_project_item_action = QAction(
            "Delete selected items", self
        )
        self.delete_project_item_action.setIcon(ACTION_ICONS["trash"])
        self.delete_project_item_action.setShortcut("Delete")
        self.delete_project_item_action.setShortcutContext(
            Qt.ShortcutContext.WidgetShortcut
        )
        self.model_tree.addAction(self.delete_project_item_action)
        edit_menu.addAction(self.delete_project_item_action)
        self.delete_project_item_action.triggered.connect(
            self.delete_selected_project_items
        )
        self.copy_project_items_action.triggered.connect(
            self.copy_selected_project_items
        )
        self.paste_project_items_action.triggered.connect(
            self.paste_project_items
        )
        self._update_delete_action()
        self.new_material_action.triggered.connect(self.add_new_material)
        self.new_layup_action.triggered.connect(self.add_new_layup)
        self.new_solver_action.triggered.connect(self.add_new_solver)

        self.run_calculation_action = QAction(
            "Run current solver", self
        )
        self.run_calculation_action.setShortcut("F5")
        self.run_calculation_action.setIcon(ACTION_ICONS["play"])
        self.run_calculation_action.setShortcutContext(
            Qt.ShortcutContext.WindowShortcut
        )
        self.addAction(self.run_calculation_action)
        self.run_calculation_action.triggered.connect(
            self.run_current_solver
        )
        calculation_menu.addAction(self.run_calculation_action)

        self.cancel_calculation_action = QAction(
            "Cancel calculation", self
        )
        self.cancel_calculation_action.setShortcut("Shift+F5")
        self.cancel_calculation_action.setIcon(ACTION_ICONS["stop"])
        self.cancel_calculation_action.setShortcutContext(
            Qt.ShortcutContext.WindowShortcut
        )
        self.addAction(self.cancel_calculation_action)
        self.cancel_calculation_action.setEnabled(False)
        self.cancel_calculation_action.triggered.connect(
            self.cancel_calculation
        )
        calculation_menu.addAction(self.cancel_calculation_action)

        self.open_library_action = QAction("Open library...", self)
        self.open_library_action.setIcon(TREE_ICONS["folder"])
        library_menu.addAction(self.open_library_action)
        self.open_library_action.triggered.connect(self.open_library)

        self.show_log_action = QAction("Show log", self)
        self.show_log_action.setCheckable(True)
        self.show_log_action.setChecked(True)
        view_menu.addAction(self.show_log_action)

        # QAction signals invoke the corresponding menu command handlers.
        self.new_project_action.triggered.connect(self.new_project)
        self.open_project_action.triggered.connect(self.open_project)
        self.save_project_action.triggered.connect(self.save_project)
        self.save_project_as_action.triggered.connect(self.save_project_as)
        self.exit_action.triggered.connect(self.close)
        self.show_log_action.toggled.connect(self.log_panel.setVisible)

    def _build_status_bar(self) -> None:
        """Add the initial message and hidden calculation controls."""
        status_bar = self.statusBar()
        status_bar.showMessage("Ready")

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        status_bar.addPermanentWidget(self.progress_bar)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setIcon(ACTION_ICONS["stop"])
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel_calculation)
        status_bar.addPermanentWidget(self.cancel_button)

    def refresh_project_view(self) -> None:
        """Rebuild the tree and update the window title from the project."""
        expanded_paths = None
        selected_paths = set()
        if self._project_view_initialized:
            expanded_paths = {
                self._tree_item_path(item)
                for item in self._all_tree_items()
                if item.childCount() and item.isExpanded()
            }
            selected_paths = {
                self._tree_item_path(item)
                for item in self.model_tree.selectedItems()
            }
        self.model_tree.clear()
        materials_root = self._add_group("Materials")
        for group_name, material_type in MATERIAL_GROUPS:
            group = self._add_group(group_name, materials_root)
            for material in self.project.materials:
                if isinstance(material, material_type):
                    self._add_object_item(
                        group, material.name, material.id, "material"
                    )

        layups_root = self._add_group("Layups")
        for layup in self.project.layups:
            self._add_object_item(
                layups_root, layup.name, layup.id, "layup"
            )

        solvers_root = self._add_group("Solvers")
        for solver in self.project.solvers:
            self._add_object_item(
                solvers_root, solver.name, solver.id, "solver"
            )

        if expanded_paths is None:
            self.model_tree.expandAll()
        else:
            for item in self._all_tree_items():
                item_path = self._tree_item_path(item)
                if item.childCount():
                    item.setExpanded(item_path in expanded_paths)
                if item_path in selected_paths:
                    item.setSelected(True)
        self._project_view_initialized = True
        self._fit_tree_width()
        self._refresh_result_tabs()
        self._update_window_title()
        self._update_delete_action()

    def _fit_tree_width(self) -> None:
        """Widen the navigation panel so every tree label is fully visible."""
        # Polishing applies the style sheet font and item padding to size hints.
        self.model_tree.ensurePolished()
        content_width = max(self.model_tree.sizeHintForColumn(0), 120)
        self.model_tree.setColumnWidth(0, content_width)
        margins = self.model_panel.layout().contentsMargins()
        tree_width = (
            content_width
            + 2 * self.model_tree.frameWidth()
            + self.model_tree.verticalScrollBar().sizeHint().width()
            + margins.left()
            + margins.right()
            + 16
        )
        self.splitter.setSizes([tree_width, max(1, self.width() - tree_width)])

    def showEvent(self, event) -> None:
        """Refit the tree once real widget geometry is available."""
        super().showEvent(event)
        if not event.spontaneous() and not self._tree_fitted_on_show:
            self._tree_fitted_on_show = True
            self._fit_tree_width()

    def _all_tree_items(self) -> list[QTreeWidgetItem]:
        """Return project tree items in depth-first display order."""
        items = []
        pending = [
            self.model_tree.topLevelItem(index)
            for index in range(self.model_tree.topLevelItemCount())
        ]
        while pending:
            item = pending.pop()
            items.append(item)
            pending.extend(
                item.child(index)
                for index in reversed(range(item.childCount()))
            )
        return items

    @staticmethod
    def _tree_item_path(item: QTreeWidgetItem) -> tuple[str, ...]:
        """Return the display-label path for a project tree item."""
        path = []
        current = item
        while current is not None:
            path.append(current.text(0))
            current = current.parent()
        return tuple(reversed(path))

    def _refresh_result_tabs(self) -> None:
        """Rebuild one placeholder result tab for every project solver."""
        if self._result_tabs_match_project():
            for index, solver in enumerate(self.project.solvers):
                page = self.results_tabs.widget(index)
                if isinstance(page, ResultTab):
                    page.run_button.setEnabled(not self._calculation_busy)
                self.results_tabs.setTabText(index, solver.name)
            has_solvers = bool(self.project.solvers)
            self.results_tabs.setVisible(has_solvers)
            self.results_placeholder.setVisible(not has_solvers)
            return

        current_solver_id = None
        current_widget = self.results_tabs.currentWidget()
        if current_widget is not None:
            current_solver_id = current_widget.property("solver_id")
        self.results_tabs.clear()
        for solver in self.project.solvers:
            page = ResultTab(
                solver,
                lambda checked=False, solver_id=solver.id:
                    self.run_solver(solver_id),
                self.results_tabs,
            )
            page.setProperty("solver_id", solver.id)
            self.results_tabs.addTab(page, solver.name)
            result_set = self.result_sets.get(solver.id)
            if result_set is not None:
                page.set_results(result_set)
        has_solvers = bool(self.project.solvers)
        self.results_tabs.setVisible(has_solvers)
        self.results_placeholder.setVisible(not has_solvers)
        if current_solver_id is not None:
            for index in range(self.results_tabs.count()):
                page = self.results_tabs.widget(index)
                if page.property("solver_id") == current_solver_id:
                    self.results_tabs.setCurrentIndex(index)
                    break

    def _result_tabs_match_project(self) -> bool:
        """Check whether current pages match all project solvers."""
        if self.results_tabs.count() != len(self.project.solvers):
            return False
        return all(
            isinstance(self.results_tabs.widget(index), ResultTab)
            and self.results_tabs.widget(index).solver == solver
            for index, solver in enumerate(self.project.solvers)
        )

    def _selected_project_ids(self) -> set[str]:
        """Collect selected object IDs, including descendants of folders."""
        selected_ids = set()
        items = list(self.model_tree.selectedItems())
        while items:
            item = items.pop()
            object_id = item.data(0, Qt.ItemDataRole.UserRole)
            if object_id is not None:
                selected_ids.add(object_id)
            else:
                items.extend(
                    item.child(index) for index in range(item.childCount())
                )
        return selected_ids

    def _update_delete_action(self) -> None:
        """Enable deletion only for selected project objects when idle."""
        has_selection = bool(self._selected_project_ids())
        can_edit = not self._calculation_busy
        self.delete_project_item_action.setEnabled(
            has_selection and can_edit
        )
        self.copy_project_items_action.setEnabled(
            has_selection and can_edit
        )
        self.paste_project_items_action.setEnabled(
            bool(self._clipboard_objects) and can_edit
        )

    def _show_project_tree_context_menu(self, position) -> None:
        """Show project deletion on the selected tree item or folder."""
        item = self.model_tree.itemAt(position)
        if item is None:
            return
        if not item.isSelected():
            self.model_tree.clearSelection()
            item.setSelected(True)
        self._update_delete_action()
        if not self.delete_project_item_action.isEnabled():
            return
        menu = QMenu(self)
        make_rounded_popup(menu)
        menu.addAction(self.copy_project_items_action)
        menu.addAction(self.paste_project_items_action)
        menu.addSeparator()
        menu.addAction(self.delete_project_item_action)
        menu.exec(self.model_tree.viewport().mapToGlobal(position))

    def copy_selected_project_items(self) -> bool:
        """Copy selected materials, layups, and solvers to an internal buffer."""
        selected_ids = self._selected_project_ids()
        if not selected_ids or self._calculation_busy:
            return False
        self._clipboard_objects = [
            (kind, deepcopy(item))
            for kind, collection in (
                ("material", self.project.materials),
                ("layup", self.project.layups),
                ("solver", self.project.solvers),
            )
            for item in collection
            if item.id in selected_ids
        ]
        self._update_delete_action()
        return bool(self._clipboard_objects)

    def paste_project_items(self) -> bool:
        """Add independent, newly identified copies of buffered items."""
        if not self._clipboard_objects or self._calculation_busy:
            return False
        existing_names = {
            "material": {item.name for item in self.project.materials},
            "layup": {item.name for item in self.project.layups},
            "solver": {item.name for item in self.project.solvers},
        }
        for kind, original in self._clipboard_objects:
            item = deepcopy(original)
            item.id = new_id()
            item.name = self._copy_name(item.name, existing_names[kind])
            existing_names[kind].add(item.name)
            if kind == "material":
                self.project.add_material(item)
            elif kind == "layup":
                self.project.add_layup(item)
            else:
                self.project.add_solver(item)
        self.refresh_project_view()
        self.log("INFO", "Pasted copies of the selected project items.")
        return True

    @staticmethod
    def _copy_name(name: str, existing_names: set[str]) -> str:
        """Return a readable copy name that is unique within its category."""
        candidate = f"{name} (copy)"
        suffix = 2
        while candidate in existing_names:
            candidate = f"{name} (copy {suffix})"
            suffix += 1
        return candidate

    def delete_selected_project_items(self) -> bool:
        """Delete selected items unless surviving objects reference them.

        Returns
        -------
        bool
            True if one or more project items were deleted.
        """
        selected_ids = self._selected_project_ids()
        if not selected_ids:
            return False
        if (
            self.calculation_process is not None
            and self.calculation_process.state()
            != QProcess.ProcessState.NotRunning
        ):
            self.statusBar().showMessage(
                "Project items cannot be deleted during a calculation."
            )
            return False

        materials = [
            material
            for material in self.project.materials
            if material.id in selected_ids
        ]
        layups = [
            layup
            for layup in self.project.layups
            if layup.id in selected_ids
        ]
        solvers = [
            solver
            for solver in self.project.solvers
            if solver.id in selected_ids
        ]
        material_ids = {material.id for material in materials}
        layup_ids = {layup.id for layup in layups}
        solver_ids = {solver.id for solver in solvers}
        blockers = []

        for layup in self.project.layups:
            if layup.id in layup_ids:
                continue
            if any(
                layer.material_id in material_ids for layer in layup.layers
            ):
                blockers.append(
                    f"Layup '{layup.name}' uses a selected material"
                )
        for solver in self.project.solvers:
            if solver.id in solver_ids:
                continue
            if solver.layup_ids and any(
                layup_id in layup_ids for layup_id in solver.layup_ids
            ):
                blockers.append(
                    f"Solver '{solver.name}' uses a selected layup"
                )
            if (
                solver.sending_fluid_id in material_ids
                or solver.receiving_fluid_id in material_ids
            ):
                blockers.append(
                    f"Solver '{solver.name}' uses a selected material"
                )
        for material in self.project.materials:
            if material.id in material_ids:
                continue
            if (
                isinstance(material, PoroElasticMatSpec)
                and material.solid_mat_id in material_ids
            ):
                blockers.append(
                    f"Material '{material.name}' uses a selected frame "
                    "material"
                )
        if blockers:
            QMessageBox.warning(
                self,
                "Cannot delete project items",
                "Remove their references first:\n" + "\n".join(blockers),
            )
            return False

        count = len(materials) + len(layups) + len(solvers)
        answer = QMessageBox.question(
            self,
            "Delete project items",
            f"Delete {count} selected project item(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False

        for solver in solvers:
            self.project.remove_solver(solver.id)
            self.result_sets.pop(solver.id, None)
        for layup in layups:
            self.project.remove_layup(layup.id)
        for material in materials:
            self.project.remove_material(material.id)
        self.refresh_project_view()
        self.log("INFO", f"Deleted {count} project item(s).")
        return True

    def run_solver(self, solver_id: str) -> bool:
        """Validate and start a solver in a background Python process.

        Parameters
        ----------
        solver_id : str
            ID of the solver to run.

        Returns
        -------
        bool
            True when a background calculation was started.
        """
        if self.calculation_process is not None:
            if (
                self.calculation_process.state()
                != QProcess.ProcessState.NotRunning
            ):
                return False
        solver = self.project.find_solver_by_id(solver_id)
        if solver is None:
            self.log("ERROR", f"Solver does not exist: {solver_id}")
            return False

        errors = self.project.validate()
        errors.extend(solver.validate(self.project))
        errors = list(dict.fromkeys(errors))
        if errors:
            message = "\n".join(errors)
            self.log("ERROR", f"Calculation validation failed: {message}")
            QMessageBox.warning(self, "Cannot run solver", message)
            return False

        selected_layups = [
            self.project.find_layup_by_id(layup_id)
            for layup_id in solver.layup_ids
        ]
        layups = [layup for layup in selected_layups if layup is not None]
        payload = json.dumps({
            "solver": solver.to_dict(),
            "layups": [layup.to_dict() for layup in layups],
            "materials": [
                material.to_dict() for material in self.project.materials
            ],
        })
        self._calculation_temp_dir = tempfile.TemporaryDirectory(
            prefix="pyvagui-calculation-"
        )
        payload_path = Path(self._calculation_temp_dir.name) / "input.json"
        self._calculation_message_path = (
            Path(self._calculation_temp_dir.name) / "messages.jsonl"
        )
        payload_path.write_text(payload, encoding="utf-8")
        self._calculation_message_path.touch()
        self._calculation_message_offset = 0
        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments(
            self._calculation_process_arguments(
                payload_path,
                self._calculation_message_path,
            )
        )
        process.setWorkingDirectory(str(Path.cwd()))
        process.readyReadStandardError.connect(
            self._read_calculation_stderr
        )
        process.started.connect(self._calculation_poll_timer.start)
        process.errorOccurred.connect(self._on_calculation_process_error)
        process.finished.connect(self._on_calculation_process_finished)
        self.calculation_process = process
        self._calculation_output_buffer.clear()
        self._calculation_stderr.clear()
        self._calculation_metadata = None
        self._calculation_results = []
        self._calculation_failed_message = None
        self._calculation_cancelled = False
        self._set_calculation_busy(True, len(layups))
        self.log("INFO", f"Started solver '{solver.name}'.")
        process.start()
        return True

    @staticmethod
    def _calculation_process_arguments(
        payload_path: Path,
        message_path: Path,
    ) -> list[str]:
        """Build worker arguments for source or frozen executable runs."""
        if getattr(sys, "frozen", False):
            return [
                "--calculation-worker",
                str(payload_path),
                str(message_path),
            ]
        return [
            "-m",
            "pyvagui.services.calculation_process",
            str(payload_path),
            str(message_path),
        ]

    def cancel_calculation(self) -> None:
        """Stop the isolated calculation process without blocking the GUI."""
        process = self.calculation_process
        if process is None:
            return
        self._calculation_cancelled = True
        self.cancel_button.setEnabled(False)
        self.statusBar().showMessage("Stopping calculation...")
        self.log("WARNING", "Calculation cancellation requested.")
        process.terminate()
        self._calculation_kill_timer.start(1500)

    def _kill_calculation_process(self) -> None:
        """Force-stop a child that did not exit after a terminate request."""
        process = self.calculation_process
        if (
            process is not None
            and process.state() != QProcess.ProcessState.NotRunning
        ):
            process.kill()

    def _set_calculation_busy(self, busy: bool, total: int = 0) -> None:
        """Show or hide progress controls and enable result Run buttons.

        Parameters
        ----------
        busy : bool
            Whether a calculation is active.
        total : int, optional
            Number of selected layups for the progress range.
        """
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(0)
        self._calculation_busy = busy
        self.progress_bar.setVisible(busy)
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy)
        self.cancel_calculation_action.setEnabled(busy)
        self._update_delete_action()
        self.run_calculation_action.setEnabled(not busy)
        for index in range(self.results_tabs.count()):
            page = self.results_tabs.widget(index)
            if isinstance(page, ResultTab):
                page.run_button.setEnabled(not busy)
        if busy:
            self.statusBar().showMessage("Calculating...")
        else:
            self.statusBar().showMessage("Ready")

    def run_current_solver(self) -> bool:
        """Run the solver belonging to the selected result tab."""
        page = self.results_tabs.currentWidget()
        if page is None:
            return False
        solver_id = page.property("solver_id")
        if not solver_id:
            return False
        return self.run_solver(solver_id)

    def _on_calculation_progress(self, done: int, total: int) -> None:
        """Update status-bar progress from a worker signal.

        Parameters
        ----------
        done : int
            Number of completed layups.
        total : int
            Number of selected layups.
        """
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(done)
        self.statusBar().showMessage(f"Calculated {done} of {total} layups")

    def _on_calculation_layup_finished(self, message: str) -> None:
        """Append a worker message using a slot owned by the GUI thread.

        Parameters
        ----------
        message : str
            Progress message emitted after one layup finishes.
        """
        self.log("INFO", message)

    def _on_calculation_finished(self, result_set: ResultSet) -> None:
        """Store worker output and update the associated result placeholder.

        Parameters
        ----------
        result_set : ResultSet
            Completed or partially cancelled solver results.
        """
        self.result_sets[result_set.solver_id] = result_set
        for index in range(self.results_tabs.count()):
            page = self.results_tabs.widget(index)
            if page.property("solver_id") != result_set.solver_id:
                continue
            if isinstance(page, ResultTab):
                page.set_results(result_set)
            break
        self.log(
            "INFO",
            f"Solver '{result_set.solver_name}' finished "
            f"({len(result_set.results)} layups).",
        )

    def _read_calculation_output(self) -> None:
        """Poll and parse complete messages from the calculation process."""
        if self._calculation_message_path is None:
            return
        try:
            with self._calculation_message_path.open("rb") as message_file:
                message_file.seek(self._calculation_message_offset)
                self._calculation_output_buffer.extend(message_file.read())
                self._calculation_message_offset = message_file.tell()
        except OSError as error:
            self._calculation_failed_message = (
                f"Could not read calculation progress: {error}"
            )
            return
        while b"\n" in self._calculation_output_buffer:
            line, _, remainder = self._calculation_output_buffer.partition(
                b"\n"
            )
            self._calculation_output_buffer = bytearray(remainder)
            if not line:
                continue
            try:
                message = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                self._calculation_failed_message = (
                    f"Invalid message from calculation process: {error}"
                )
                continue
            self._handle_calculation_message(message)

    def _read_calculation_stderr(self) -> None:
        """Keep child diagnostics in memory for process-failure reports."""
        if self.calculation_process is not None:
            self._calculation_stderr.extend(
                bytes(self.calculation_process.readAllStandardError())
            )

    def _handle_calculation_message(self, message: dict) -> None:
        """Update progress and collect result messages from the child."""
        message_type = message.get("type")
        if message_type == "started":
            self._calculation_metadata = message
        elif message_type == "progress":
            self._on_calculation_progress(
                message["done"], message["total"]
            )
        elif message_type == "message":
            self._on_calculation_layup_finished(message["text"])
        elif message_type == "layup_result":
            values = np.asarray(message["values"], dtype=float)
            if message["complex"]:
                values = values[:, 0] + 1j * values[:, 1]
            self._calculation_results.append(
                LayupResult(
                    layup_id=message["layup_id"],
                    layup_name=message["layup_name"],
                    values=values,
                )
            )
        elif message_type == "failed":
            self._calculation_failed_message = message["message"]

    def _build_process_result(self) -> ResultSet | None:
        """Assemble parent-side metadata with completed child results."""
        metadata = self._calculation_metadata
        if metadata is None:
            return None
        return ResultSet(
            solver_id=metadata["solver_id"],
            solver_name=metadata["solver_name"],
            solver_type=SolverType(metadata["solver_type"]),
            frequencies=np.asarray(metadata["frequencies"], dtype=float),
            labels=metadata["labels"],
            results=self._calculation_results,
            reference_impedance=metadata.get("reference_impedance"),
            angle_deg=metadata.get("angle_deg", 0.0),
        )

    def _on_calculation_process_error(
        self,
        error: QProcess.ProcessError,
    ) -> None:
        """Report process startup errors that do not emit ``finished``."""
        if error == QProcess.ProcessError.FailedToStart:
            self._on_calculation_failed(
                "Could not start the calculation process."
            )
            self._finish_calculation_process()

    def _on_calculation_process_finished(
        self,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        """Handle normal completion, failure, or cancellation without waits."""
        self._calculation_poll_timer.stop()
        self._calculation_kill_timer.stop()
        self._read_calculation_output()
        self._read_calculation_stderr()
        if self._calculation_cancelled:
            result_set = self._build_process_result()
            if result_set is not None and result_set.results:
                self._on_calculation_finished(result_set)
            self.log("INFO", "Calculation cancelled.")
        elif (
            self._calculation_failed_message is not None
            or exit_code != 0
            or exit_status != QProcess.ExitStatus.NormalExit
        ):
            message = self._calculation_failed_message
            if message is None:
                message = bytes(self._calculation_stderr).decode(
                    "utf-8", errors="replace"
                ).strip()
            if not message:
                message = f"Calculation process exited with code {exit_code}."
            self._on_calculation_failed(message)
        else:
            result_set = self._build_process_result()
            if result_set is None:
                self._on_calculation_failed(
                    "Calculation process returned no result metadata."
                )
            else:
                self._on_calculation_finished(result_set)
        self._finish_calculation_process()

    def _finish_calculation_process(self) -> None:
        """Release the process and restore GUI controls after completion."""
        process = self.calculation_process
        self.calculation_process = None
        self._calculation_message_path = None
        self._calculation_metadata = None
        self._calculation_results = []
        self._set_calculation_busy(False)
        if process is not None:
            process.deleteLater()
        if self._calculation_temp_dir is not None:
            self._calculation_temp_dir.cleanup()
            self._calculation_temp_dir = None

    def _on_calculation_failed(self, message: str) -> None:
        """Log and display an exception received from the worker.

        Parameters
        ----------
        message : str
            Error text emitted by the calculation worker.
        """
        self.log("ERROR", f"Calculation failed: {message}")
        QMessageBox.critical(self, "Calculation failed", message)

    def _add_group(
        self,
        name: str,
        parent: QTreeWidgetItem | None = None,
    ) -> QTreeWidgetItem:
        """Add a non-editable grouping row to the model tree.

        Parameters
        ----------
        name : str
            Visible group label.
        parent : QTreeWidgetItem or None, optional
            Parent group, or None for a top-level group.

        Returns
        -------
        QTreeWidgetItem
            The newly added group row.
        """
        item = QTreeWidgetItem([name])
        item.setIcon(0, TREE_ICONS["folder"])
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setChildIndicatorPolicy(
            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
        )
        if parent is None:
            self.model_tree.addTopLevelItem(item)
        else:
            parent.addChild(item)
        return item

    @staticmethod
    def _add_object_item(
        parent: QTreeWidgetItem,
        name: str,
        object_id: str,
        icon_name: str,
    ) -> QTreeWidgetItem:
        """Add a project object and store its identifier in the tree row.

        Parameters
        ----------
        parent : QTreeWidgetItem
            Group row that owns the object item.
        name : str
            Visible object name.
        object_id : str
            Stable model identifier associated with the row.
        icon_name : str
            Monochrome icon key for the project object type.

        Returns
        -------
        QTreeWidgetItem
            The newly added project object row.
        """
        item = QTreeWidgetItem([name])
        item.setIcon(0, TREE_ICONS[icon_name])
        # UserRole stores the stable model id separately from the display name.
        item.setData(0, Qt.ItemDataRole.UserRole, object_id)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        parent.addChild(item)
        return item

    def _update_window_title(self) -> None:
        """Show the saved filename or unsaved project name in the title."""
        modified_marker = "*" if self.project.is_modified else ""
        display_name = (
            self.project.file_path.name
            if self.project.file_path is not None
            else self.project.name
        )
        self.setWindowTitle(
            f"pyvaGUI - {display_name}{modified_marker}"
        )

    def _get_material_library(self) -> MaterialLibrary | None:
        """Load the user's material library once for this window.

        Returns
        -------
        MaterialLibrary or None
            Loaded library, or None if its file could not be read or created.
        """
        if self.material_library is not None:
            return self.material_library
        library = MaterialLibrary(MaterialLibrary.default_path())
        try:
            library.load()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.log("ERROR", f"Could not load material library: {error}")
            QMessageBox.critical(self, "Material library", str(error))
            return None
        self.material_library = library
        return library

    def add_new_material(self) -> None:
        """Open the new-material dialog and add its accepted material."""
        library = self._get_material_library()
        if library is None:
            return
        dialog = MaterialEditorDialog(
            self.project,
            library=library,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for material in dialog.additional_materials:
            self.project.add_material(material)
        if dialog.material is not None:
            self.project.add_material(dialog.material)
        self.refresh_project_view()
        self.log("INFO", "Added material to the project.")

    def edit_tree_item(
        self,
        item: QTreeWidgetItem,
        column: int = 0,
    ) -> None:
        """Edit a material item activated by a double-click.

        Parameters
        ----------
        item : QTreeWidgetItem
            Activated tree row.
        column : int, optional
            Activated column. The single-column tree uses column zero.
        """
        material_id = item.data(0, Qt.ItemDataRole.UserRole)
        if material_id is None:
            return
        material = self.project.find_material_by_id(material_id)
        if material is not None:
            library = self._get_material_library()
            if library is None:
                return
            dialog = MaterialEditorDialog(
                self.project,
                material=material,
                library=library,
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            for index, current in enumerate(self.project.materials):
                if current.id == material.id:
                    self.project.materials[index] = dialog.material_spec
                    self.project.is_modified = True
                    break
            self.refresh_project_view()
            self.log("INFO", f"Updated material '{material.name}'.")
            return

        layup = self.project.find_layup_by_id(material_id)
        if layup is not None:
            dialog = LayupEditorDialog(self.project, layup=layup, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            for index, current in enumerate(self.project.layups):
                if current.id == layup.id:
                    self.project.layups[index] = dialog.result_layup
                    self.project.is_modified = True
                    break
            self.refresh_project_view()
            self.log("INFO", f"Updated layup '{layup.name}'.")
            return

        solver = self.project.find_solver_by_id(material_id)
        if solver is None:
            return
        dialog = SolverEditorDialog(self.project, solver=solver, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.result_solver is not None:
            for index, current in enumerate(self.project.solvers):
                if current.id == solver.id:
                    self.project.solvers[index] = dialog.result_solver
                    self.project.is_modified = True
                    break
            self.refresh_project_view()
            self.log("INFO", f"Updated solver '{solver.name}'.")

    def add_new_layup(self) -> None:
        """Open the layup editor and add its accepted layup to the project."""
        dialog = LayupEditorDialog(self.project, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.result_layup is None:
            return
        self.project.add_layup(dialog.result_layup)
        self.refresh_project_view()
        self.log("INFO", "Added layup to the project.")

    def add_new_solver(self) -> None:
        """Open the solver editor and add its accepted result."""
        dialog = SolverEditorDialog(self.project, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.result_solver is None:
            return
        self.project.add_solver(dialog.result_solver)
        self.refresh_project_view()
        self.log("INFO", "Added solver to the project.")

    def open_library(self) -> None:
        """Open the library and refresh only when it changes the project."""
        library = self._get_material_library()
        if library is None:
            return
        before_ids = self._project_object_ids()
        dialog = LibraryDialog(self.project, library, parent=self)
        dialog.exec()
        if self._project_object_ids() != before_ids:
            self.refresh_project_view()

    def _project_object_ids(self) -> tuple[tuple[str, ...], ...]:
        """Return ordered object identifiers for change detection."""
        return (
            tuple(material.id for material in self.project.materials),
            tuple(layup.id for layup in self.project.layups),
            tuple(solver.id for solver in self.project.solvers),
        )

    def new_project(self) -> None:
        """Replace the current project after resolving unsaved changes."""
        if not self._confirm_discard_changes():
            return
        self.project = Project()
        self._clipboard_objects.clear()
        self.refresh_project_view()
        self.log("INFO", "Created a new project.")

    def open_project(self) -> None:
        """Ask for a project file and load it if changes can be discarded."""
        if not self._confirm_discard_changes():
            return
        # QFileDialog returns the selected path and the active filter.
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open project",
            "",
            "pyvaGUI project (*.pyvagui)",
        )
        if path:
            self._load_project(Path(path))

    def _load_project(self, path: Path) -> bool:
        """Load a project file and refresh the displayed project state.

        Parameters
        ----------
        path : pathlib.Path
            Project JSON path.

        Returns
        -------
        bool
            True when the file loaded successfully.
        """
        try:
            project = Project.load(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.log("ERROR", f"Could not open project: {error}")
            QMessageBox.critical(self, "Open project", str(error))
            return False
        self.project = project
        self._clipboard_objects.clear()
        self.refresh_project_view()
        self.log(
            "INFO",
            f"Opened project '{project.file_path.name}'.",
        )
        return True

    def save_project(self) -> bool:
        """Save to the current file, or ask for a path if not saved yet.

        Returns
        -------
        bool
            True when the project was saved successfully.
        """
        if self.project.file_path is None:
            return self.save_project_as()
        return self._save_project_to(self.project.file_path)

    def save_project_as(self) -> bool:
        """Ask for a destination and save the current project there.

        Returns
        -------
        bool
            True when the project was saved successfully.
        """
        # QFileDialog lets the user choose the project destination.
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save project as",
            self.project.name + ".pyvagui",
            "pyvaGUI project (*.pyvagui)",
        )
        if not path:
            return False
        target = Path(path)
        if target.suffix.lower() != ".pyvagui":
            target = target.with_suffix(".pyvagui")
        return self._save_project_to(target)

    def _save_project_to(self, path: Path) -> bool:
        """Write the project and refresh its saved title state.

        Parameters
        ----------
        path : pathlib.Path
            Destination JSON path.

        Returns
        -------
        bool
            True when the project was saved successfully.
        """
        try:
            self.project.save(path)
        except OSError as error:
            self.log("ERROR", f"Could not save project: {error}")
            QMessageBox.critical(self, "Save project", str(error))
            return False
        self.refresh_project_view()
        self.log("INFO", f"Saved project to '{path}'.")
        return True

    def _confirm_discard_changes(self) -> bool:
        """Ask whether to save, discard, or cancel pending project changes.

        Returns
        -------
        bool
            True if the requested action may continue.
        """
        if not self.project.is_modified:
            return True
        # QMessageBox offers explicit save, discard, and cancel choices.
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes to the current project?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        """Prevent closing while the user cancels an unsaved-change prompt.

        Parameters
        ----------
        event : QCloseEvent
            Qt event describing the requested window close.
        """
        if (
            self.calculation_process is not None
            and self.calculation_process.state()
            != QProcess.ProcessState.NotRunning
        ):
            self.cancel_calculation()
            self.statusBar().showMessage(
                "Stopping calculation before closing..."
            )
            event.ignore()
            return
        # closeEvent can accept or ignore a close requested by Qt.
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def log(self, level: str, message: str) -> None:
        """Append a timestamped application message to the log panel.

        Parameters
        ----------
        level : str
            Message severity: ``INFO``, ``WARNING``, or ``ERROR``.
        message : str
            Text to display.

        Raises
        ------
        ValueError
            If the severity is not supported.
        """
        normalized_level = level.upper()
        if normalized_level not in ("INFO", "WARNING", "ERROR"):
            raise ValueError(f"Unsupported log level: {level}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_panel.appendPlainText(
            f"{timestamp} [{normalized_level}] {message}"
        )
