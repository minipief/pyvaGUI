"""Dialog for browsing and managing the material library."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyvagui.gui.tree_icons import ACTION_ICONS, TREE_ICONS
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


MATERIAL_GROUPS = (
    ("Fluid", FluidSpec),
    ("Equivalent fluid", EquivalentFluidSpec),
    ("Delany-Bazley", DelanyBazleySpec),
    ("Isomat", IsoMatSpec),
    ("Poroelastic", PoroElasticMatSpec),
)


class LibraryDialog(QDialog):
    """Display library materials and perform library/project actions.

    Parameters
    ----------
    project : Project
        Project that can receive library material copies.
    library : MaterialLibrary
        Persistent source and destination of library materials.
    selection_only : bool, optional
        Return a selected copy to a parent editor instead of adding it to
        the project.
    parent : QWidget or None, optional
        Parent widget that owns the dialog.
    """

    def __init__(
        self,
        project: Project,
        library: MaterialLibrary,
        selection_only: bool = False,
        parent: QWidget | None = None,
    ):
        """Load and display the material list."""
        super().__init__(parent)
        self.project = project
        self.library = library
        self.selection_only = selection_only
        self.selected_materials: list[MaterialSpec] = []
        self.additional_materials: list[MaterialSpec] = []

        self.setWindowTitle("Material library")
        self.resize(720, 520)
        self._build_interface()
        try:
            if not self.library.materials:
                self.library.load()
        except (OSError, ValueError, KeyError, TypeError) as error:
            QMessageBox.critical(self, "Material library", str(error))
        self.refresh()

    def _build_interface(self) -> None:
        """Create the material list and library action buttons."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.material_tree = QTreeWidget(self)
        self.material_tree.setHeaderHidden(True)
        self.material_tree.setIndentation(14)
        self.material_tree.setUniformRowHeights(True)
        self.material_tree.setSelectionMode(
            QTreeWidget.SelectionMode.SingleSelection
            if self.selection_only
            else QTreeWidget.SelectionMode.ExtendedSelection
        )
        self.material_tree.itemSelectionChanged.connect(
            self._update_selection_actions
        )
        layout.addWidget(self.material_tree)
        self.status_label = QLabel(self)
        self.status_label.setObjectName("successBanner")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        self.add_to_project_button = QPushButton("Add to project", self)
        self.import_button = QPushButton("Import...", self)
        self.export_button = QPushButton("Export selected...", self)
        self.delete_button = QPushButton("Delete", self)
        self.close_button = QPushButton("Close", self)

        self.add_to_project_button.clicked.connect(self.add_to_project)
        self.import_button.clicked.connect(self.import_materials)
        self.export_button.clicked.connect(self.export_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.close_button.clicked.connect(self.reject)

        self.add_to_project_button.setText(
            "Select" if self.selection_only else "Add to project"
        )
        self.delete_button.setVisible(not self.selection_only)
        self.import_button.setVisible(not self.selection_only)
        self.export_button.setVisible(not self.selection_only)
        self.add_to_project_button.setObjectName("primaryButton")
        self.delete_button.setObjectName("dangerButton")
        self.add_to_project_button.setIcon(ACTION_ICONS["plus-white"])
        self.import_button.setIcon(ACTION_ICONS["import"])
        self.export_button.setIcon(ACTION_ICONS["export"])
        self.delete_button.setIcon(ACTION_ICONS["trash"])
        self.delete_button.setText("")
        self.delete_button.setToolTip("Delete selected materials")
        self.delete_button.setAccessibleName("Delete selected materials")
        self.delete_button.setFixedSize(38, 38)
        self.close_button.setIcon(ACTION_ICONS["close"])
        self.close_button.setText("")
        self.close_button.setToolTip("Close material library")
        self.close_button.setAccessibleName("Close material library")
        self.close_button.setFixedSize(38, 38)

        for button in (
            self.import_button,
            self.export_button,
            self.delete_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        actions.addWidget(self.close_button)
        actions.addWidget(self.add_to_project_button)
        layout.addLayout(actions)

    def refresh(self) -> None:
        """Rebuild visible material names from the library model."""
        self.material_tree.clear()
        for name, material_type in MATERIAL_GROUPS:
            group = QTreeWidgetItem([name])
            group.setIcon(0, TREE_ICONS["folder"])
            group.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
            )
            self.material_tree.addTopLevelItem(group)
            materials = sorted(
                (material for material in self.library.materials
                 if isinstance(material, material_type)),
                key=lambda material: material.name.casefold(),
            )
            for material in materials:
                item = QTreeWidgetItem([material.name])
                item.setIcon(0, TREE_ICONS["material"])
                item.setData(0, Qt.ItemDataRole.UserRole, material.id)
                group.addChild(item)
        self.material_tree.expandAll()
        self._update_selection_actions()

    def _update_selection_actions(self) -> None:
        """Enable material commands only when material rows are selected."""
        has_selection = bool(self._selected_ids())
        self.add_to_project_button.setEnabled(has_selection)
        self.export_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def add_to_project(self) -> None:
        """Copy the selected material or materials into the project.

        In selection-only mode the selected copy is returned to the parent
        editor and the project remains unchanged.
        """
        selected = self._selected_library_materials()
        if not selected:
            return

        copies = self._prepare_copies(selected)
        selected_ids = [material.id for material in selected]
        self.selected_materials = [
            copies[material_id] for material_id in selected_ids
        ]
        additional_ids = [
            material_id
            for material_id in copies
            if material_id not in selected_ids
        ]
        self.additional_materials = [
            copies[item_id] for item_id in additional_ids
        ]

        if self.selection_only:
            self.accept()
            return

        try:
            for material in copies.values():
                self.project.add_material(material)
        except ValueError as error:
            QMessageBox.warning(self, "Material library", str(error))
            return
        self.refresh()
        self.status_label.setText(
            f"Added {len(copies)} material(s) to the project."
        )
        self.status_label.show()

    def _prepare_copies(
        self,
        selected: list[MaterialSpec],
    ) -> dict[str, MaterialSpec]:
        """Copy selected materials and resolve optional frame dependencies.

        Parameters
        ----------
        selected : list of MaterialSpec
            Selected library materials.

        Returns
        -------
        dict of str to MaterialSpec
            Copies keyed by their original library identifiers.
        """
        copies = {
            material.id: self.project.copy_from_library(material)
            for material in selected
        }
        for material in selected:
            if not isinstance(material, PoroElasticMatSpec):
                continue
            if self.project.missing_frame_material_id(material) is None:
                continue
            if material.solid_mat_id in copies:
                continue
            frame = next(
                (
                    item
                    for item in self.library.materials
                    if item.id == material.solid_mat_id
                ),
                None,
            )
            if not isinstance(frame, IsoMatSpec):
                continue
            copies[frame.id] = self.project.copy_from_library(frame)

        for original in selected:
            if not isinstance(original, PoroElasticMatSpec):
                continue
            frame_copy = copies.get(original.solid_mat_id)
            if frame_copy is not None:
                copies[original.id].solid_mat_id = frame_copy.id
        return copies

    def import_materials(self) -> None:
        """Import a material JSON file into and save the library."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import materials",
            "",
            "Material files (*.json)",
        )
        if not path:
            return
        try:
            imported = self.library.import_materials(path)
            for material in imported:
                self.library.add(material)
            self.library.save()
        except (OSError, ValueError, KeyError, TypeError) as error:
            QMessageBox.critical(self, "Import materials", str(error))
            return
        self.refresh()

    def export_selected(self) -> None:
        """Export selected library materials to a JSON file."""
        selected_ids = self._selected_ids()
        if not selected_ids:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export materials",
            "materials.json",
            "Material files (*.json)",
        )
        if not path:
            return
        target = Path(path)
        if target.suffix == "":
            target = target.with_suffix(".json")
        try:
            self.library.export_materials(selected_ids, target)
        except (OSError, KeyError) as error:
            QMessageBox.critical(self, "Export materials", str(error))

    def delete_selected(self) -> None:
        """Remove selected library materials after confirmation."""
        selected_ids = self._selected_ids()
        if not selected_ids:
            return
        frame_users = [
            material.name
            for material in self.library.materials
            if isinstance(material, PoroElasticMatSpec)
            and material.solid_mat_id in selected_ids
            and material.id not in selected_ids
        ]
        if frame_users:
            QMessageBox.warning(
                self,
                "Material library",
                "Cannot delete a frame used by: " + ", ".join(frame_users),
            )
            return
        answer = QMessageBox.question(
            self,
            "Delete materials",
            f"Delete {len(selected_ids)} selected material(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for material_id in selected_ids:
            self.library.remove(material_id)
        try:
            self.library.save()
        except OSError as error:
            QMessageBox.critical(self, "Material library", str(error))
            return
        self.refresh()

    def _selected_ids(self) -> list[str]:
        """Return selected IDs, including materials in selected folders."""
        selected_ids = set()
        for item in self.material_tree.selectedItems():
            object_id = item.data(0, Qt.ItemDataRole.UserRole)
            if object_id is not None:
                selected_ids.add(object_id)
                continue
            selected_ids.update(
                item.child(index).data(0, Qt.ItemDataRole.UserRole)
                for index in range(item.childCount())
            )
        return [
            material.id
            for material in self.library.materials
            if material.id in selected_ids
        ]

    def _selected_library_materials(self) -> list[MaterialSpec]:
        """Resolve selected tree identifiers to library material specs."""
        selected_ids = set(self._selected_ids())
        return [
            material
            for material in self.library.materials
            if material.id in selected_ids
        ]
