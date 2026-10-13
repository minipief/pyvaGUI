"""Dialog for creating and editing project material specifications."""

import copy
import math
from dataclasses import fields

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyvagui.model.library import MaterialLibrary
from pyvagui.model.materials import (
    DelanyBazleySpec,
    EquivalentFluidSpec,
    FluidSpec,
    IsoMatSpec,
    MaterialSpec,
    PoroElasticMatSpec,
)
from pyvagui.model.project import Project


MATERIAL_TYPES = (
    ("Fluid", FluidSpec),
    ("EquivalentFluid", EquivalentFluidSpec),
    ("Delany-Bazley", DelanyBazleySpec),
    ("Isomat", IsoMatSpec),
    ("PoroElasticMat", PoroElasticMatSpec),
)

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
    "solid_mat_id": ("Frame material", "Isomat"),
}

TYPE_GROUP_NAMES = {
    FluidSpec: "Fluid properties",
    EquivalentFluidSpec: "EquivalentFluid properties",
    DelanyBazleySpec: "Delany-Bazley properties",
    IsoMatSpec: "Isomat properties",
    PoroElasticMatSpec: "PoroElasticMat properties",
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
    """

    def __init__(
        self,
        project: Project,
        material: MaterialSpec | None = None,
        library: MaterialLibrary | None = None,
        parent: QWidget | None = None,
    ):
        """Build a material form without changing the project on cancel."""
        super().__init__(parent)
        self.project = project
        self.library = library
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
        self.name_edit = QLineEdit(self.material_spec.name, self)
        layout.addWidget(QLabel("Name", self))
        layout.addWidget(self.name_edit)

        self.type_combo = QComboBox(self)
        layout.addWidget(QLabel("Material type", self))
        layout.addWidget(self.type_combo)
        self.type_combo.setEnabled(self.is_new)

        self.properties_group = QGroupBox(self)
        self.properties_layout = QGridLayout(self.properties_group)
        layout.addWidget(self.properties_group)

        button_row = QHBoxLayout()
        self.add_from_library_button = QPushButton(
            "Add from library...", self
        )
        self.add_from_library_button.setVisible(self.is_new)
        self.add_from_library_button.clicked.connect(self.add_from_library)
        button_row.addWidget(self.add_from_library_button)

        self.save_to_library_button = QPushButton("Save to library", self)
        self.save_to_library_button.setVisible(
            not self.is_new and self.library is not None
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
        """Build one widget for every editable dataclass field."""
        while self.properties_layout.count():
            item = self.properties_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.field_widgets.clear()
        self.properties_group.setTitle(
            TYPE_GROUP_NAMES[type(self.material_spec)]
        )

        editable_fields = [
            item
            for item in fields(self.material_spec)
            if item.name not in ("name", "id")
        ]
        for field_index, material_field in enumerate(editable_fields):
            row = field_index // 2
            column = (field_index % 2) * 2
            label_text, unit = FIELD_INFO.get(
                material_field.name,
                (material_field.name, ""),
            )
            if unit:
                label_text = f"{label_text} [{unit}]"
            label = QLabel(label_text, self.properties_group)
            label.setToolTip(material_field.name)
            widget = self._create_field_widget(material_field)
            widget.setToolTip(material_field.name)
            self.properties_layout.addWidget(label, row * 2, column)
            self.properties_layout.addWidget(
                widget,
                row * 2 + 1,
                column,
                1,
                2 if material_field.name == "solid_mat_id" else 1,
            )
            self.field_widgets[material_field.name] = widget

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
            combo.addItem("Select Isomat", "")
            available_materials = (
                self.project.materials + self.additional_materials
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
            if not isinstance(frame, IsoMatSpec):
                errors.append("Frame material must be an existing Isomat.")
        return errors

    def save_material(self) -> None:
        """Validate all values and accept only when no errors remain."""
        errors = self._validation_errors()
        if errors:
            QMessageBox.warning(
                self,
                "Invalid material",
                "\n".join(errors),
            )
            return
        self.material = self.material_spec
        self.accept()

    def add_from_library(self) -> None:
        """Select a library material as the new dialog's working copy."""
        if self.library is None:
            QMessageBox.warning(
                self,
                "Material library",
                "No material library is available.",
            )
            return
        # The selection-only dialog returns copies and does not change Project.
        from pyvagui.gui.library_dialog import LibraryDialog

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
                self._rebuild_property_fields()

    def save_to_library(self) -> None:
        """Save a validated copy of the edited material to the library."""
        if self.library is None:
            return
        errors = self._validation_errors()
        if errors:
            QMessageBox.warning(
                self,
                "Invalid material",
                "\n".join(errors),
            )
            return
        library_copy = self.material_spec.copy_with_new_id()
        try:
            self.library.add(library_copy)
            self.library.save()
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Material library", str(error))
            return
        QMessageBox.information(
            self,
            "Material library",
            f"Saved '{self.material_spec.name}' to the library.",
        )
