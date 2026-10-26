"""Dialog for creating and editing project material specifications."""

import copy
import math
from dataclasses import fields

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyvagui.gui.library_dialog import LibraryDialog, MATERIAL_GROUPS
from pyvagui.gui.tree_icons import ACTION_ICONS
from pyvagui.model.library import MaterialLibrary
from pyvagui.model.materials import (
    IsoMatSpec,
    MaterialSpec,
    PoroElasticMatSpec,
    FluidSpec,
)
from pyvagui.model.project import Project


MATERIAL_TYPES = MATERIAL_GROUPS

FIELD_INFO = {
    "c0": ("Speed of sound", "m/s"),
    "rho0": ("Density", "kg/m^3"),
    "dynamic_viscosity": ("Dynamic viscosity", "Pa s"),
    "kappa": ("Ratio of specific heats", "-"),
    "Cp": ("Heat capacity at constant pressure", "J/(kg K)"),
    "heat_conductivity": ("Heat conductivity", "W/(m K)"),
    "eta": ("Damping loss factor", "-"),
    "flow_res": ("Flow resistivity", "Pa s/m^2"),
    "porosity": ("Porosity", "-"),
    "tortuosity": ("Tortuosity", "-"),
    "rho_bulk": ("Bulk density", "kg/m^3"),
    "length_visc": ("Viscous characteristic length", "m"),
    "length_therm": ("Thermal characteristic length", "m"),
    "limp": ("Limp frame", ""),
    "miki": ("Miki model", ""),
    "E": ("Young's modulus", "Pa"),
    "nu": ("Poisson ratio", "-"),
    "solid_mat_id": ("Frame material", ""),
}


def parse_float(text: str) -> float | None:
    """Parse a finite float, allowing a comma as decimal separator.

    Parameters
    ----------
    text : str
        Text entered into a numeric field.

    Returns
    -------
    float or None
        Parsed finite value, or None if parsing fails.
    """
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value


class MaterialEditorDialog(QDialog):
    """Create or edit one material using an isolated working copy.

    Parameters
    ----------
    project : Project
        Project whose Isomat materials can be used as frame references.
    material : MaterialSpec or None, optional
        Existing material to edit. When omitted, a new Fluid spec is made
        and the user can choose its type.
    library : MaterialLibrary or None, optional
        Material library used by the optional library actions.
    parent : QWidget or None, optional
        Parent widget that owns the dialog.
    library_context : bool, optional
        Allow frame references to other library materials while managing the
        library directly.
    """

    def __init__(
        self,
        project: Project,
        material: MaterialSpec | None = None,
        library: MaterialLibrary | None = None,
        parent: QWidget | None = None,
        library_context: bool = False,
    ):
        """Build a material form without changing the project on cancel."""
        super().__init__(parent)
        self.project = project
        self.library = library
        self.library_context = library_context
        self.is_new = material is None
        self.material_spec = (
            FluidSpec() if material is None else copy.deepcopy(material)
        )
        self.material: MaterialSpec | None = None
        self.additional_materials: list[MaterialSpec] = []
        self.field_widgets: dict[str, QWidget] = {}

        self.setWindowTitle(
            "New material" if self.is_new else "Material properties"
        )
        self._build_interface()
        self._populate_type_combo()
        self._rebuild_property_fields()

    def _build_interface(self) -> None:
        """Create the name, type, property, and action controls."""
        # A form dialog keeps labels and input widgets together as one unit.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.setMinimumWidth(480)
        header_form = QFormLayout()
        header_form.setHorizontalSpacing(16)
        self.name_edit = QLineEdit(self.material_spec.name, self)
        self.name_edit.setPlaceholderText("Material name")
        header_form.addRow("Name", self.name_edit)

        self.type_combo = QComboBox(self)
        header_form.addRow("Material type", self.type_combo)
        self.type_combo.setEnabled(self.is_new)
        layout.addLayout(header_form)

        self.properties_group = QGroupBox(self)
        self.properties_layout = QFormLayout(self.properties_group)
        self.properties_layout.setHorizontalSpacing(16)
        self.properties_layout.setVerticalSpacing(8)
        self.properties_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        layout.addWidget(self.properties_group)

        self.error_label = QLabel(self)
        self.error_label.setObjectName("errorBanner")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.library_status_label = QLabel(self)
        self.library_status_label.setObjectName("successBanner")
        self.library_status_label.setWordWrap(True)
        self.library_status_label.hide()
        layout.addWidget(self.library_status_label)

        button_row = QHBoxLayout()
        self.add_from_library_button = QPushButton(
            "Add from library...", self
        )
        self.add_from_library_button.setIcon(ACTION_ICONS["open"])
        self.add_from_library_button.setVisible(
            self.is_new and self.library is not None
        )
        self.add_from_library_button.clicked.connect(self.add_from_library)
        button_row.addWidget(self.add_from_library_button)

        self.save_to_library_button = QPushButton("Save to library", self)
        self.save_to_library_button.setIcon(ACTION_ICONS["save"])
        self.save_to_library_button.setVisible(
            not self.is_new
            and self.library is not None
            and not self.library_context
        )
        self.save_to_library_button.clicked.connect(self.save_to_library)
        button_row.addWidget(self.save_to_library_button)
        button_row.addStretch(1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save,
            parent=self,
        )
        self.button_box.accepted.connect(self.save_material)
        self.button_box.button(
            QDialogButtonBox.StandardButton.Save
        ).setObjectName("primaryButton")
        self.button_box.rejected.connect(self.reject)
        button_row.addWidget(self.button_box)
        layout.addLayout(button_row)

        self.type_combo.currentIndexChanged.connect(
            self._change_material_type
        )

    def _populate_type_combo(self) -> None:
        """Fill the type selector and select the working spec type."""
        for display_name, material_type in MATERIAL_TYPES:
            self.type_combo.addItem(display_name, material_type)
        current_index = self.type_combo.findData(type(self.material_spec))
        self.type_combo.setCurrentIndex(current_index)

    def _change_material_type(self, index: int) -> None:
        """Replace a new material's working spec when its type changes.

        Parameters
        ----------
        index : int
            Selected type index in the combo box.
        """
        if not self.is_new or index < 0:
            return
        material_type = self.type_combo.itemData(index)
        name = self.name_edit.text()
        self.material_spec = material_type(name=name)
        self._rebuild_property_fields()

    def _rebuild_property_fields(self) -> None:
        """Build one form row for every editable dataclass field."""
        # removeRow deletes widgets immediately, so old rows cannot linger.
        while self.properties_layout.rowCount():
            self.properties_layout.removeRow(0)
        self.field_widgets.clear()
        self.error_label.hide()
        type_label = next(
            label
            for label, material_type in MATERIAL_TYPES
            if type(self.material_spec) is material_type
        )
        self.properties_group.setTitle(f"{type_label} properties")

        editable_fields = [
            item
            for item in fields(self.material_spec)
            if item.name not in ("name", "id")
        ]
        for material_field in editable_fields:
            label_text, unit = FIELD_INFO.get(
                material_field.name,
                (material_field.name, ""),
            )
            if unit and unit != "-":
                label_text = f"{label_text} [{unit}]"
            widget = self._create_field_widget(material_field)
            widget.setToolTip(material_field.name)
            if isinstance(widget, QCheckBox):
                widget.setText(label_text)
                self.properties_layout.addRow("", widget)
            else:
                self.properties_layout.addRow(label_text, widget)
            self.field_widgets[material_field.name] = widget
        self.adjustSize()

    def _create_field_widget(self, material_field) -> QWidget:
        """Create a checkbox, frame selector, or text input for a field.

        Parameters
        ----------
        material_field : dataclasses.Field
            Dataclass field from the active material spec.

        Returns
        -------
        QWidget
            Input widget initialized from the working copy.
        """
        value = getattr(self.material_spec, material_field.name)
        if material_field.type is bool:
            checkbox = QCheckBox(self.properties_group)
            checkbox.setChecked(value)
            return checkbox
        if material_field.name == "solid_mat_id":
            combo = QComboBox(self.properties_group)
            combo.addItem("Select Isomat frame", "")
            available_materials = (
                self.project.materials + self.additional_materials
            )
            if self.library_context and self.library is not None:
                available_ids = {
                    material.id for material in available_materials
                }
                available_materials.extend(
                    material
                    for material in self.library.materials
                    if isinstance(material, IsoMatSpec)
                    and material.id not in available_ids
                )
            for project_material in available_materials:
                if isinstance(project_material, IsoMatSpec):
                    combo.addItem(
                        project_material.name,
                        project_material.id,
                    )
            index = combo.findData(value)
            if index >= 0:
                combo.setCurrentIndex(index)
            return combo
        line_edit = QLineEdit(str(value), self.properties_group)
        if material_field.type is float:
            line_edit.setPlaceholderText("Enter value")
        return line_edit

    def _read_fields(self) -> list[str]:
        """Read widgets into the copy and return every parse error."""
        errors = []
        self.material_spec.name = self.name_edit.text().strip()
        for material_field in fields(self.material_spec):
            name = material_field.name
            if name in ("name", "id"):
                continue
            widget = self.field_widgets[name]
            if material_field.type is bool:
                setattr(self.material_spec, name, widget.isChecked())
            elif name == "solid_mat_id":
                setattr(self.material_spec, name, widget.currentData())
            elif material_field.type is float:
                value = parse_float(widget.text())
                if value is None:
                    errors.append(
                        f"{name}: enter a valid finite number."
                    )
                else:
                    setattr(self.material_spec, name, value)
        return errors

    def _validation_errors(self) -> list[str]:
        """Combine widget parsing, spec validation, and frame errors."""
        errors = self._read_fields()
        if not self.material_spec.name:
            errors.append("Material name must not be empty.")
        errors.extend(self.material_spec.validate())
        if isinstance(self.material_spec, PoroElasticMatSpec):
            frame = self.project.find_material_by_id(
                self.material_spec.solid_mat_id
            )
            if not isinstance(frame, IsoMatSpec):
                frame = next(
                    (
                        material
                        for material in self.additional_materials
                        if material.id == self.material_spec.solid_mat_id
                    ),
                    None,
                )
            if (
                not isinstance(frame, IsoMatSpec)
                and self.library_context
                and self.library is not None
            ):
                frame = next(
                    (
                        material
                        for material in self.library.materials
                        if material.id == self.material_spec.solid_mat_id
                    ),
                    None,
                )
            if not isinstance(frame, IsoMatSpec):
                errors.append("Frame material must be an existing Isomat.")
        return errors

    def save_material(self) -> None:
        """Validate all values and accept only when no errors remain."""
        errors = self._validation_errors()
        if errors:
            self._show_errors(errors)
            return
        self.material = self.material_spec
        self.accept()

    def _show_errors(self, errors: list[str]) -> None:
        """Show validation errors inline and keep the dialog open.

        Parameters
        ----------
        errors : list of str
            Messages explaining why the material cannot be saved.
        """
        self.library_status_label.hide()
        self.error_label.setText("\n".join(errors))
        self.error_label.show()

    def add_from_library(self) -> None:
        """Select a library material as the new dialog's working copy."""
        if self.library is None:
            QMessageBox.warning(
                self,
                "Material library",
                "No material library is available.",
            )
            return
        dialog = LibraryDialog(
            self.project,
            self.library,
            selection_only=True,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_materials:
                self.material_spec = dialog.selected_materials[0]
                self.additional_materials = dialog.additional_materials
                self.name_edit.setText(self.material_spec.name)
                # Blocked so the type change keeps the selected values.
                self.type_combo.blockSignals(True)
                self.type_combo.setCurrentIndex(
                    self.type_combo.findData(type(self.material_spec))
                )
                self.type_combo.blockSignals(False)
                self._rebuild_property_fields()

    def save_to_library(self) -> None:
        """Save a validated copy of the edited material to the library."""
        if self.library is None:
            return
        errors = self._validation_errors()
        if errors:
            self._show_errors(errors)
            return
        library_copy = self.material_spec.copy_with_new_id()
        try:
            self.library.add(library_copy)
            self.library.save()
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Material library", str(error))
            return
        self.error_label.hide()
        self.library_status_label.setText(
            f"Saved '{self.material_spec.name}' to the library."
        )
        self.library_status_label.show()
