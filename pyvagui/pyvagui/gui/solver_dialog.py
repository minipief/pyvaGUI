"""Dialog for creating or editing solver specifications."""

import copy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from pyvagui.gui.material_editor import parse_float
from pyvagui.model.materials import FluidSpec
from pyvagui.model.project import Project
from pyvagui.model.solvers import (
    BoundaryCondition,
    FrequencySettings,
    SolverSpec,
    SolverType,
)


class SolverEditorDialog(QDialog):
    """Configure one solver against the materials and layups in a project.

    Parameters
    ----------
    project : Project
        Project whose fluids and layups can be selected.
    solver : SolverSpec or None, optional
        Existing solver to edit. Omit to create a new solver.
    parent : QWidget or None, optional
        Parent widget that owns the dialog.
    """

    def __init__(
        self,
        project: Project,
        solver: SolverSpec | None = None,
        parent: QWidget | None = None,
    ):
        """Build a solver form using a copy of the selected configuration."""
        super().__init__(parent)
        self.project = project
        self.is_new = solver is None
        self.solver_spec = (
            SolverSpec(
                solver_type=SolverType.ABSORPTION,
                frequencies=FrequencySettings(
                    f_start=20.0,
                    f_end=20000.0,
                    n_points=100,
                ),
            )
            if solver is None
            else copy.deepcopy(solver)
        )
        self.result_solver: SolverSpec | None = None
        self.setWindowTitle(
            "New solver" if self.is_new else "Solver properties"
        )
        self._build_interface()
        self._populate_widgets()

    def _build_interface(self) -> None:
        """Create solver, fluid, angle, frequency, and layup controls."""
        # Form layouts keep each setting beside its descriptive label.
        layout = QVBoxLayout(self)
        name_form = QFormLayout()
        self.name_edit = QLineEdit(self.solver_spec.name, self)
        name_form.addRow("Name", self.name_edit)
        self.solver_type_combo = QComboBox(self)
        for solver_type in SolverType:
            self.solver_type_combo.addItem(
                solver_type.display_name,
                solver_type,
            )
        name_form.addRow("Solver preset", self.solver_type_combo)
        layout.addLayout(name_form)

        fluids_group = QGroupBox("Fluid materials", self)
        fluids_form = QFormLayout(fluids_group)
        self.sending_fluid_combo = self._make_fluid_combo()
        self.receiving_fluid_combo = self._make_fluid_combo()
        fluids_form.addRow("Sending fluid", self.sending_fluid_combo)
        fluids_form.addRow("Receiving fluid", self.receiving_fluid_combo)
        layout.addWidget(fluids_group)

        self.incidence_group = QGroupBox(self)
        incidence_form = QFormLayout(self.incidence_group)
        self.single_angle_label = QLabel("Angle [°]", self.incidence_group)
        self.single_angle_edit = QLineEdit(self.incidence_group)
        self.maximum_angle_label = QLabel(
            "Maximum angle [°]",
            self.incidence_group,
        )
        self.maximum_angle_edit = QLineEdit(self.incidence_group)
        self.diffuse_hint = QLabel(
            "Maximum incidence angle for diffuse averaging.",
            self.incidence_group,
        )
        incidence_form.addRow(self.single_angle_label, self.single_angle_edit)
        incidence_form.addRow(
            self.maximum_angle_label,
            self.maximum_angle_edit,
        )
        incidence_form.addRow(self.diffuse_hint)
        layout.addWidget(self.incidence_group)

        frequency_group = QGroupBox("Frequency range", self)
        frequency_form = QFormLayout(frequency_group)
        self.frequency_start_edit = QLineEdit(frequency_group)
        self.frequency_end_edit = QLineEdit(frequency_group)
        self.frequency_points_edit = QLineEdit(frequency_group)
        frequency_form.addRow("Start [Hz]", self.frequency_start_edit)
        frequency_form.addRow("End [Hz]", self.frequency_end_edit)
        frequency_form.addRow("Number of points", self.frequency_points_edit)
        layout.addWidget(frequency_group)

        boundary_group = QGroupBox("Boundary condition", self)
        boundary_form = QFormLayout(boundary_group)
        self.boundary_combo = QComboBox(boundary_group)
        self.boundary_combo.addItem(
            "Fixed (hard wall)",
            BoundaryCondition.FIXED,
        )
        self.boundary_combo.addItem(
            "Equivalent fluid",
            BoundaryCondition.EQUIVALENT_FLUID,
        )
        boundary_form.addRow("Receiving side", self.boundary_combo)
        layout.addWidget(boundary_group)

        layups_group = QGroupBox("Layups", self)
        layups_layout = QVBoxLayout(layups_group)
        self.layup_list = QListWidget(layups_group)
        for layup in self.project.layups:
            item = QListWidgetItem(layup.name, self.layup_list)
            item.setData(Qt.ItemDataRole.UserRole, layup.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
        layups_layout.addWidget(self.layup_list)
        layout.addWidget(layups_group, stretch=1)

        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save,
            parent=self,
        )
        self.button_box.accepted.connect(self.save_solver)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.solver_type_combo.currentIndexChanged.connect(
            self.update_angle_visibility
        )

    def _make_fluid_combo(self) -> QComboBox:
        """Create a selector containing only project FluidSpec materials.

        Returns
        -------
        QComboBox
            Fluid choice combo with IDs stored as item data.
        """
        combo = QComboBox(self)
        combo.addItem("Select fluid", "")
        for material in self.project.materials:
            if isinstance(material, FluidSpec):
                combo.addItem(material.name, material.id)
        return combo

    def _populate_widgets(self) -> None:
        """Fill inputs and checked layups from the solver copy."""
        self.name_edit.setText(self.solver_spec.name)
        self.solver_type_combo.setCurrentIndex(
            self.solver_type_combo.findData(self.solver_spec.solver_type)
        )
        self.single_angle_edit.setText(f"{self.solver_spec.angle_deg:g}")
        self.maximum_angle_edit.setText(
            f"{self.solver_spec.max_angle_deg:g}"
        )
        frequencies = self.solver_spec.frequencies
        self.frequency_start_edit.setText(f"{frequencies.f_start:g}")
        self.frequency_end_edit.setText(f"{frequencies.f_end:g}")
        self.frequency_points_edit.setText(str(frequencies.n_points))
        self.boundary_combo.setCurrentIndex(
            self.boundary_combo.findData(
                self.solver_spec.boundary_condition
            )
        )
        selected_layups = set(self.solver_spec.layup_ids)
        for index in range(self.layup_list.count()):
            item = self.layup_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) in selected_layups:
                item.setCheckState(Qt.CheckState.Checked)
        self._select_fluid(
            self.sending_fluid_combo,
            self.solver_spec.sending_fluid_id,
        )
        self._select_fluid(
            self.receiving_fluid_combo,
            self.solver_spec.receiving_fluid_id,
        )
        self.update_angle_visibility()

    @staticmethod
    def _select_fluid(combo: QComboBox, material_id: str) -> None:
        """Select a fluid by its project ID.

        Parameters
        ----------
        combo : QComboBox
            Fluid selector to update.
        material_id : str
            ID that should be selected, if present.
        """
        index = combo.findData(material_id)
        if index >= 0:
            combo.setCurrentIndex(index)

    def update_angle_visibility(self, index: int = -1) -> None:
        """Switch the single-angle or diffuse-maximum fields by preset.

        Parameters
        ----------
        index : int, optional
            Changed combo index. The active preset is read from the widget.
        """
        solver_type = self.solver_type_combo.currentData()
        if not isinstance(solver_type, SolverType):
            solver_type = SolverType.ABSORPTION
        is_diffuse = solver_type.uses_diffuse_angle()
        self.single_angle_label.setVisible(not is_diffuse)
        self.single_angle_edit.setVisible(not is_diffuse)
        self.maximum_angle_label.setVisible(is_diffuse)
        self.maximum_angle_edit.setVisible(is_diffuse)
        self.diffuse_hint.setVisible(is_diffuse)
        self.incidence_group.setTitle(
            "Diffuse incidence" if is_diffuse else "Incidence"
        )

    def save_solver(self) -> None:
        """Read fields, validate against the project, and accept if valid."""
        parse_errors = []
        angle_deg = self._parse_angle(
            self.single_angle_edit,
            "Angle",
            parse_errors,
        )
        max_angle_deg = self._parse_angle(
            self.maximum_angle_edit,
            "Maximum angle",
            parse_errors,
        )
        f_start = self._parse_float_field(
            self.frequency_start_edit,
            "Start frequency",
            parse_errors,
        )
        f_end = self._parse_float_field(
            self.frequency_end_edit,
            "End frequency",
            parse_errors,
        )
        n_points = self._parse_points(parse_errors)

        solver = copy.deepcopy(self.solver_spec)
        solver.name = self.name_edit.text().strip()
        solver.solver_type = self.solver_type_combo.currentData()
        solver.angle_deg = angle_deg
        solver.max_angle_deg = max_angle_deg
        solver.boundary_condition = self.boundary_combo.currentData()
        solver.sending_fluid_id = self.sending_fluid_combo.currentData()
        solver.receiving_fluid_id = self.receiving_fluid_combo.currentData()
        solver.frequencies = FrequencySettings(
            f_start=f_start,
            f_end=f_end,
            n_points=n_points,
        )
        solver.layup_ids = self._selected_layup_ids()

        errors = parse_errors + solver.validate(self.project)
        if errors:
            self.error_label.setText("\n".join(errors))
            self.error_label.show()
            QMessageBox.warning(self, "Invalid solver", "\n".join(errors))
            return
        self.result_solver = solver
        self.accept()

    @staticmethod
    def _parse_float_field(
        edit: QLineEdit,
        label: str,
        errors: list[str],
    ) -> float:
        """Parse one floating-point input or report its field label.

        Parameters
        ----------
        edit : QLineEdit
            Input to parse.
        label : str
            Readable field label for errors.
        errors : list of str
            Error collection to append to.

        Returns
        -------
        float
            Parsed value, or zero when invalid so validation can continue.
        """
        value = parse_float(edit.text())
        if value is None:
            errors.append(f"{label} must be a finite number.")
            return 0.0
        return value

    def _parse_angle(
        self,
        edit: QLineEdit,
        label: str,
        errors: list[str],
    ) -> float:
        """Parse an angle input, using the solver default if it is invalid.

        Parameters
        ----------
        edit : QLineEdit
            Angle text field.
        label : str
            Field label used in the parse error.
        errors : list of str
            Error collection to append to.

        Returns
        -------
        float
            Parsed angle or a benign default if the text is invalid.
        """
        value = parse_float(edit.text())
        if value is None:
            errors.append(f"{label} must be a finite number.")
            return 0.0
        return value

    def _parse_points(self, errors: list[str]) -> int:
        """Parse the integer frequency sample count.

        Parameters
        ----------
        errors : list of str
            Error collection to append to.

        Returns
        -------
        int
            Parsed point count or zero when input is invalid.
        """
        text = self.frequency_points_edit.text().strip()
        try:
            value = int(text)
        except ValueError:
            errors.append("Number of points must be an integer >= 2.")
            return 0
        if value < 2:
            errors.append("Number of points must be an integer >= 2.")
        return value

    def _selected_layup_ids(self) -> list[str]:
        """Return checked layup IDs in their visible project order."""
        selected_ids = []
        for index in range(self.layup_list.count()):
            item = self.layup_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_ids
