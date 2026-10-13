"""Dialog for editing an ordered layup and its layer specifications."""

import copy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyvagui.gui.material_editor import parse_float
from pyvagui.gui.layup_preview import LayupPreview
from pyvagui.gui.perforation_dialog import (
    PerforationDialog,
    m_to_mm,
    mm_to_m,
)
from pyvagui.model.layup import LayerSpec, LayerType, Layup, PerforationSpec
from pyvagui.model.materials import MaterialSpec
from pyvagui.model.project import Project


LAYER_TYPE_LABELS = {
    LayerType.FLUID: "Fluid",
    LayerType.POROELASTIC: "Poroelastic",
    LayerType.SOLID: "Solid",
    LayerType.PLATE: "Plate",
    LayerType.MASS: "Mass",
}


class LayerTableWidget(QTableWidget):
    """Layer table that delegates drops to the Layup model.

    Parameters
    ----------
    move_callback : callable
        Function called with source and target row indices for a drop.
    parent : QWidget or None, optional
        Parent widget that owns the table.
    """

    def __init__(self, move_callback, parent: QWidget | None = None):
        """Configure internal drag-and-drop for layer rows."""
        super().__init__(0, 6, parent)
        self.move_callback = move_callback
        self.setHorizontalHeaderLabels(
            [
                "Move",
                "Material",
                "Thickness [mm]",
                "Layer type",
                "Perforation",
                "Delete",
            ]
        )
        self.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def dropEvent(self, event) -> None:
        """Read the source and target rows and delegate reordering.

        Parameters
        ----------
        event : QDropEvent
            Qt drop event emitted for an internal table drag.
        """
        source = self.currentRow()
        target = self.indexAt(event.position().toPoint()).row()
        if source < 0 or target < 0:
            event.ignore()
            return
        self.move_callback(source, target)
        event.accept()


class LayupEditorDialog(QDialog):
    """Create or edit an ordered layup on a private copy.

    Parameters
    ----------
    project : Project
        Project providing materials and receiving a new layup.
    layup : Layup or None, optional
        Existing layup to edit. Omit to create a new layup.
    parent : QWidget or None, optional
        Parent widget that owns the dialog.
    """

    def __init__(
        self,
        project: Project,
        layup: Layup | None = None,
        parent: QWidget | None = None,
    ):
        """Build the layer editor around a copy of an existing layup."""
        super().__init__(parent)
        self.project = project
        self.is_new = layup is None
        self.layup = Layup() if layup is None else copy.deepcopy(layup)
        self.result_layup: Layup | None = None
        self.setWindowTitle("New layup" if self.is_new else "Layup properties")
        self._build_interface()
        self.refresh()

    def _build_interface(self) -> None:
        """Create the layer table, preview, and dialog actions."""
        # Layouts keep controls together as the window resizes.
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Name", self))
        self.name_edit = QLineEdit(self.layup.name, self)
        layout.addWidget(self.name_edit)

        # The splitter keeps the editable table and stack preview side by side.
        content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.content_splitter = content_splitter

        layer_panel = QWidget(content_splitter)
        layer_layout = QVBoxLayout(layer_panel)
        layer_layout.setContentsMargins(0, 0, 8, 0)
        self.summary_label = QLabel(layer_panel)
        layer_layout.addWidget(self.summary_label)

        # The table's embedded controls are rebuilt from the Layup model.
        self.layer_table = LayerTableWidget(
            self._move_layer_by_drop,
            layer_panel,
        )
        self.layer_table.setColumnWidth(0, 48)
        self.layer_table.setColumnWidth(1, 190)
        self.layer_table.setColumnWidth(2, 120)
        self.layer_table.setColumnWidth(3, 130)
        self.layer_table.setColumnWidth(4, 180)
        self.layer_table.setColumnWidth(5, 70)
        layer_layout.addWidget(self.layer_table, stretch=1)

        self.preview = LayupPreview(
            self.layup,
            self.project.materials_by_id(),
            content_splitter,
        )
        content_splitter.addWidget(layer_panel)
        content_splitter.addWidget(self.preview)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)
        layout.addWidget(content_splitter, stretch=1)

        controls = QHBoxLayout()
        self.add_layer_button = QPushButton("+ Add layer", self)
        self.move_up_button = QPushButton("Move up", self)
        self.move_down_button = QPushButton("Move down", self)
        self.add_layer_button.clicked.connect(self.add_layer)
        self.move_up_button.clicked.connect(lambda: self.move_selected(-1))
        self.move_down_button.clicked.connect(lambda: self.move_selected(1))
        controls.addWidget(self.add_layer_button)
        controls.addStretch(1)
        controls.addWidget(self.move_up_button)
        controls.addWidget(self.move_down_button)
        layout.addLayout(controls)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save,
            parent=self,
        )
        self.button_box.accepted.connect(self.save_layup)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def refresh(self) -> None:
        """Rebuild every row and summary from the layup model."""
        self.name_edit.setText(self.layup.name)
        self.layer_table.setRowCount(0)
        for row, layer in enumerate(self.layup.layers):
            self.layer_table.insertRow(row)
            self._build_row(row, layer)
        self._update_summary()
        self.preview.set_data(
            self.layup,
            self.project.materials_by_id(),
        )

    def _build_row(self, row: int, layer: LayerSpec) -> None:
        """Create all cell widgets for one layer row.

        Parameters
        ----------
        row : int
            Row to populate.
        layer : LayerSpec
            Layer model object represented by the row.
        """
        handle = QTableWidgetItem("Move")
        handle.setFlags(handle.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.layer_table.setItem(row, 0, handle)

        material_combo = QComboBox(self.layer_table)
        materials = self.project.materials_by_id()
        for material in self.project.materials:
            layer_types = LayerSpec.allowed_types(material)
            if layer_types:
                material_combo.addItem(
                    f"{material.name} ({self._material_type(material)})",
                    material.id,
                )
        material_index = material_combo.findData(layer.material_id)
        if material_index >= 0:
            material_combo.setCurrentIndex(material_index)
        material_combo.currentIndexChanged.connect(
            lambda index, layer_row=row: self._material_changed(
                layer_row,
                index,
            )
        )
        self.layer_table.setCellWidget(row, 1, material_combo)

        thickness_edit = QLineEdit(f"{m_to_mm(layer.thickness):g}")
        thickness_edit.editingFinished.connect(
            lambda layer_row=row: self._thickness_changed(layer_row)
        )
        self.layer_table.setCellWidget(row, 2, thickness_edit)

        material = materials.get(layer.material_id)
        allowed_types = (
            [] if material is None else LayerSpec.allowed_types(material)
        )
        type_combo = QComboBox(self.layer_table)
        for layer_type in allowed_types:
            type_combo.addItem(
                LAYER_TYPE_LABELS[layer_type],
                layer_type,
            )
        type_index = type_combo.findData(layer.layer_type)
        if type_index >= 0:
            type_combo.setCurrentIndex(type_index)
        type_combo.setEnabled(len(allowed_types) > 1)
        type_combo.currentIndexChanged.connect(
            lambda index, layer_row=row: self._layer_type_changed(
                layer_row,
                index,
            )
        )
        self.layer_table.setCellWidget(row, 3, type_combo)

        perforation_button = QPushButton(
            self._perforation_label(layer.perforation),
            self.layer_table,
        )
        perforation_button.setEnabled(
            layer.layer_type in (LayerType.PLATE, LayerType.MASS)
        )
        perforation_button.clicked.connect(
            lambda checked=False, layer_row=row: self.edit_perforation(
                layer_row
            )
        )
        self.layer_table.setCellWidget(row, 4, perforation_button)

        delete_button = QPushButton("Delete", self.layer_table)
        delete_button.clicked.connect(
            lambda checked=False, layer_row=row: self.remove_layer(layer_row)
        )
        self.layer_table.setCellWidget(row, 5, delete_button)

    def _material_changed(self, row: int, index: int) -> None:
        """Update material and reset type/perforation after selection.

        Parameters
        ----------
        row : int
            Layer row being changed.
        index : int
            Selected material combo index.
        """
        if index < 0 or row >= len(self.layup.layers):
            return
        combo = self.layer_table.cellWidget(row, 1)
        material = self.project.find_material_by_id(combo.currentData())
        if material is None:
            return
        allowed_types = LayerSpec.allowed_types(material)
        if not allowed_types:
            return
        layer = self.layup.layers[row]
        layer.material_id = material.id
        layer.layer_type = allowed_types[0]
        if layer.layer_type not in (LayerType.PLATE, LayerType.MASS):
            layer.perforation = None
        self.refresh()

    def _layer_type_changed(self, row: int, index: int) -> None:
        """Update the model type and clear incompatible perforations.

        Parameters
        ----------
        row : int
            Layer row being changed.
        index : int
            Selected layer type combo index.
        """
        if index < 0 or row >= len(self.layup.layers):
            return
        combo = self.layer_table.cellWidget(row, 3)
        layer_type = combo.currentData()
        if not isinstance(layer_type, LayerType):
            return
        layer = self.layup.layers[row]
        layer.layer_type = layer_type
        if layer_type not in (LayerType.PLATE, LayerType.MASS):
            layer.perforation = None
        self.refresh()

    def _thickness_changed(self, row: int) -> None:
        """Store a valid displayed millimeter value as model meters.

        Parameters
        ----------
        row : int
            Layer row whose thickness was edited.
        """
        if row >= len(self.layup.layers):
            return
        widget = self.layer_table.cellWidget(row, 2)
        value_mm = parse_float(widget.text())
        if value_mm is not None:
            self.layup.layers[row].thickness = mm_to_m(value_mm)
            self._update_summary()

    def edit_perforation(self, row: int) -> None:
        """Edit or remove perforation parameters for one layer.

        Parameters
        ----------
        row : int
            Layer row whose perforation is edited.
        """
        if row >= len(self.layup.layers):
            return
        layer = self.layup.layers[row]
        if layer.layer_type not in (LayerType.PLATE, LayerType.MASS):
            return
        dialog = PerforationDialog(layer.perforation, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            layer.perforation = dialog.result_perforation
            self.refresh()

    def add_layer(self) -> None:
        """Append a default 10 mm layer using the first project material."""
        if not self.project.materials:
            QMessageBox.information(
                self,
                "Add layer",
                "Add a material to the project before adding a layer.",
            )
            return
        material = self.project.materials[0]
        layer_types = LayerSpec.allowed_types(material)
        if not layer_types:
            QMessageBox.warning(
                self,
                "Add layer",
                f"Material '{material.name}' cannot be used in a layer.",
            )
            return
        self.layup.add_layer(
            LayerSpec(
                material_id=material.id,
                thickness=0.01,
                layer_type=layer_types[0],
            )
        )
        self.refresh()

    def remove_layer(self, row: int) -> None:
        """Remove one layer row and rebuild the table.

        Parameters
        ----------
        row : int
            Zero-based row to remove.
        """
        if 0 <= row < len(self.layup.layers):
            self.layup.remove_layer(row)
            self.refresh()

    def move_selected(self, offset: int) -> None:
        """Move the selected layer up or down by one row.

        Parameters
        ----------
        offset : int
            Relative destination, normally -1 or 1.
        """
        source = self.layer_table.currentRow()
        target = source + offset
        self._move_layer(source, target)

    def _move_layer_by_drop(self, source: int, target: int) -> None:
        """Handle a drag-and-drop reorder from the table subclass.

        Parameters
        ----------
        source : int
            Current row index.
        target : int
            Destination row index.
        """
        self._move_layer(source, target)

    def _move_layer(self, source: int, target: int) -> None:
        """Reorder model layers and rebuild all cell widgets.

        Qt moves table items during its default drop operation, but widgets
        installed with ``setCellWidget`` are not moved with those items.

        Parameters
        ----------
        source : int
            Current layer index.
        target : int
            Destination layer index.
        """
        if not 0 <= source < len(self.layup.layers):
            return
        if not 0 <= target < len(self.layup.layers):
            return
        if source == target:
            return
        self.layup.move_layer(source, target)
        self.refresh()
        self.layer_table.selectRow(target)

    def save_layup(self) -> None:
        """Read thickness fields, validate the layup, and accept if valid."""
        self.layup.name = self.name_edit.text().strip()
        parse_errors = []
        for row, layer in enumerate(self.layup.layers):
            widget = self.layer_table.cellWidget(row, 2)
            value_mm = parse_float(widget.text())
            if value_mm is None:
                parse_errors.append(
                    f"Layer {row + 1}: thickness must be a finite number."
                )
            else:
                layer.thickness = mm_to_m(value_mm)
        errors = parse_errors + self.layup.validate(
            self.project.materials_by_id()
        )
        if not self.layup.name:
            errors.append("Layup name must not be empty.")
        if errors:
            QMessageBox.warning(self, "Invalid layup", "\n".join(errors))
            return
        self.result_layup = self.layup
        self.accept()

    def _update_summary(self) -> None:
        """Display layer count and total thickness in millimeters."""
        total_mm = m_to_mm(self.layup.total_thickness())
        self.summary_label.setText(
            f"{len(self.layup.layers)} layers - {total_mm:g} mm total"
        )

    @staticmethod
    def _perforation_label(perforation: PerforationSpec | None) -> str:
        """Return the short label shown on a layer perforation button.

        Parameters
        ----------
        perforation : PerforationSpec or None
            Perforation configuration for the layer.

        Returns
        -------
        str
            ``None`` or the radius and spacing in millimeters.
        """
        if perforation is None:
            return "None"
        radius_mm = m_to_mm(perforation.hole_radius)
        distance_mm = m_to_mm(perforation.distance)
        return f"r = {radius_mm:g} mm, d = {distance_mm:g} mm"

    @staticmethod
    def _material_type(material: MaterialSpec) -> str:
        """Return a readable type for the material combo box.

        Parameters
        ----------
        material : MaterialSpec
            Material displayed by a combo-box item.

        Returns
        -------
        str
            Class name without its ``Spec`` suffix.
        """
        return type(material).__name__.removesuffix("Spec")
