"""Main application window and project-management interface."""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QMainWindow,
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

from pyvagui.gui.library_dialog import LibraryDialog
from pyvagui.gui.layup_editor import LayupEditorDialog
from pyvagui.gui.material_editor import MaterialEditorDialog
from pyvagui.gui.result_tab import ResultTab
from pyvagui.gui.solver_dialog import SolverEditorDialog
from pyvagui.model.library import MaterialLibrary
from pyvagui.model.materials import (
    DelanyBazleySpec,
    EquivalentFluidSpec,
    FluidSpec,
    IsoMatSpec,
    PoroElasticMatSpec,
)
from pyvagui.model.project import Project
from pyvagui.model.results import ResultSet
from pyvagui.services.worker import CalculationWorker


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
        self.project = project if project is not None else Project()
        self.material_library: MaterialLibrary | None = None
        self.calculation_thread: QThread | None = None
        self.calculation_worker: CalculationWorker | None = None
        self.result_sets: dict[str, ResultSet] = {}
        self.resize(1100, 760)

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
        layout.setContentsMargins(0, 0, 0, 0)

        # A splitter lets users resize the navigation and results areas.
        splitter = QSplitter(Qt.Orientation.Horizontal, central_widget)
        self.splitter = splitter

        model_layout = QVBoxLayout(self.model_panel)
        model_layout.setContentsMargins(8, 8, 8, 8)
        # QTreeWidget handles visible rows and nested groups directly.
        self.model_tree = QTreeWidget(self.model_panel)
        self.model_tree.setHeaderHidden(True)
        self.model_tree.itemDoubleClicked.connect(self.edit_tree_item)
        model_layout.addWidget(self.model_tree)

        results_layout = QVBoxLayout(self.results_panel)
        results_layout.setContentsMargins(16, 12, 16, 12)
        self.results_placeholder = QLabel("No results", self.results_panel)
        self.results_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_tabs = QTabWidget(self.results_panel)
        results_layout.addWidget(self.results_placeholder, stretch=1)
        results_layout.addWidget(self.results_tabs, stretch=1)

        splitter.addWidget(self.model_panel)
        splitter.addWidget(self.results_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter, stretch=3)
        layout.addWidget(self.log_panel, stretch=1)
        self.setCentralWidget(central_widget)

    def _build_menus(self) -> None:
        """Create application menus and connect available commands."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        library_menu = menu_bar.addMenu("Library")
        view_menu = menu_bar.addMenu("View")
        menu_bar.addMenu("Help")

        self.new_project_action = QAction("New project", self)
        self.open_project_action = QAction("Open...", self)
        self.save_project_action = QAction("Save", self)
        self.save_project_as_action = QAction("Save as...", self)
        self.exit_action = QAction("Exit", self)
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
        edit_menu.addAction(self.new_material_action)
        edit_menu.addAction(self.new_layup_action)
        edit_menu.addAction(self.new_solver_action)
        self.new_material_action.triggered.connect(self.add_new_material)
        self.new_layup_action.triggered.connect(self.add_new_layup)
        self.new_solver_action.triggered.connect(self.add_new_solver)

        self.open_library_action = QAction("Open library...", self)
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
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel_calculation)
        status_bar.addPermanentWidget(self.cancel_button)

    def refresh_project_view(self) -> None:
        """Rebuild the tree and update the window title from the project."""
        self.model_tree.clear()
        materials_root = self._add_group("Materials")
        material_groups = [
            ("Fluid", (FluidSpec,)),
            ("Equivalent fluid", (EquivalentFluidSpec,)),
            ("Delany-Bazley", (DelanyBazleySpec,)),
            ("Isomat", (IsoMatSpec,)),
            ("Poroelastic", (PoroElasticMatSpec,)),
        ]
        for group_name, material_types in material_groups:
            group = self._add_group(group_name, materials_root)
            for material in self.project.materials:
                if isinstance(material, material_types):
                    self._add_object_item(group, material.name, material.id)

        layups_root = self._add_group("Layups")
        for layup in self.project.layups:
            self._add_object_item(layups_root, layup.name, layup.id)

        solvers_root = self._add_group("Solvers")
        for solver in self.project.solvers:
            self._add_object_item(solvers_root, solver.name, solver.id)

        self.model_tree.expandAll()
        self._refresh_result_tabs()
        self._update_window_title()

    def _refresh_result_tabs(self) -> None:
        """Rebuild one placeholder result tab for every project solver."""
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

    def run_solver(self, solver_id: str) -> bool:
        """Validate and start a solver on a background QThread.

        Parameters
        ----------
        solver_id : str
            ID of the solver to run.

        Returns
        -------
        bool
            True when a background calculation was started.
        """
        if self.calculation_thread is not None:
            if self.calculation_thread.isRunning():
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
        worker = CalculationWorker(
            solver,
            layups,
            self.project.materials_by_id(),
        )
        # QThread runs calculations away from the GUI event loop.
        thread = QThread(self)
        thread.setObjectName(f"Calculation: {solver.name}")
        worker.moveToThread(thread)
        self.calculation_worker = worker
        self.calculation_thread = thread
        self._set_calculation_busy(True, len(layups))

        # Queued signals let the GUI thread update widgets safely.
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_calculation_progress)
        worker.layup_finished.connect(self._on_calculation_layup_finished)
        worker.finished.connect(self._on_calculation_finished)
        worker.failed.connect(self._on_calculation_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_calculation_thread_finished)
        self.log("INFO", f"Started solver '{solver.name}'.")
        thread.start()
        return True

    def cancel_calculation(self) -> None:
        """Request cancellation before the worker starts its next layup."""
        if self.calculation_worker is None:
            return
        self.calculation_worker.request_cancel()
        self.cancel_button.setEnabled(False)
        self.statusBar().showMessage("Cancelling after current layup...")
        self.log("WARNING", "Calculation cancellation requested.")

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
        self.progress_bar.setVisible(busy)
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy)
        for index in range(self.results_tabs.count()):
            page = self.results_tabs.widget(index)
            if isinstance(page, ResultTab):
                page.run_button.setEnabled(not busy)
        if busy:
            self.statusBar().showMessage("Calculating...")
        else:
            self.statusBar().showMessage("Ready")

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

    def _on_calculation_failed(self, message: str) -> None:
        """Log and display an exception received from the worker.

        Parameters
        ----------
        message : str
            Error text emitted by the calculation worker.
        """
        self.log("ERROR", f"Calculation failed: {message}")
        QMessageBox.critical(self, "Calculation failed", message)

    def _on_calculation_thread_finished(self) -> None:
        """Restore idle controls after the worker thread has stopped."""
        self._set_calculation_busy(False)
        self.calculation_worker = None
        self.calculation_thread = None

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
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
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

        Returns
        -------
        QTreeWidgetItem
            The newly added project object row.
        """
        item = QTreeWidgetItem([name])
        # UserRole stores the stable model id separately from the display name.
        item.setData(0, Qt.ItemDataRole.UserRole, object_id)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        parent.addChild(item)
        return item

    def _update_window_title(self) -> None:
        """Show the current project name and unsaved marker in the title."""
        modified_marker = "*" if self.project.is_modified else ""
        self.setWindowTitle(
            f"pyvaGUI - {self.project.name}{modified_marker}"
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
        """Open the library browser and refresh project changes afterward."""
        library = self._get_material_library()
        if library is None:
            return
        dialog = LibraryDialog(self.project, library, parent=self)
        dialog.exec()
        self.refresh_project_view()

    def new_project(self) -> None:
        """Replace the current project after resolving unsaved changes."""
        if not self._confirm_discard_changes():
            return
        self.project = Project()
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
            "pyvaGUI project (*.json)",
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
        self.refresh_project_view()
        self.log("INFO", f"Opened project '{project.name}'.")
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
            self.project.name + ".json",
            "pyvaGUI project (*.json)",
        )
        if not path:
            return False
        target = Path(path)
        if target.suffix == "":
            target = target.with_suffix(".json")
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
            self.calculation_thread is not None
            and self.calculation_thread.isRunning()
        ):
            self.cancel_calculation()
            self.statusBar().showMessage(
                "Waiting for the current layup before closing..."
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
