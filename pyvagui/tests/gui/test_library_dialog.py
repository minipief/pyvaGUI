"""Tests for the material library dialog workflows."""

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QMenu

from pyvagui.gui.library_dialog import LibraryDialog
from pyvagui.gui.material_editor import MaterialEditorDialog
from pyvagui.model.library import MaterialLibrary
from pyvagui.model.materials import (
    FluidSpec,
    IsoMatSpec,
    PoroElasticMatSpec,
)
from pyvagui.model.project import Project


def make_library(tmp_path):
    """Create an isolated library containing air and a frame-based foam."""
    air = FluidSpec(name="Air")
    frame = IsoMatSpec(name="Aluminium")
    foam = PoroElasticMatSpec(
        name="Open-cell foam",
        solid_mat_id=frame.id,
    )
    library = MaterialLibrary(tmp_path / "library.json")
    library.materials = [air, frame, foam]
    return library, air, frame, foam


def test_library_list_stores_material_ids(qtbot, tmp_path):
    """Display names and types while keeping IDs in UserRole data."""
    library, air, _, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)

    item = dialog.material_tree.topLevelItem(0).child(0)

    assert item.text(0) == "Air"
    assert item.data(0, Qt.ItemDataRole.UserRole) == air.id
    assert not item.icon(0).isNull()
    assert not dialog.material_tree.topLevelItem(0).icon(0).isNull()
    assert [dialog.material_tree.topLevelItem(index).text(0)
            for index in range(5)] == [
        "Fluid", "Equivalent fluid", "Delany-Bazley", "Isomat", "Poroelastic"
    ]


def test_library_sorts_names_and_selects_category_folder(qtbot, tmp_path):
    """Sort categories and include all folder materials in selection."""
    library, _, _, _ = make_library(tmp_path)
    library.materials.extend([
        FluidSpec(name="water"), FluidSpec(name="Argon")
    ])
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    fluid_group = dialog.material_tree.topLevelItem(0)

    assert [fluid_group.child(index).text(0) for index in range(3)] == [
        "Air", "Argon", "water"
    ]
    assert not dialog.add_to_project_button.isEnabled()
    assert not dialog.export_button.isEnabled()
    assert not dialog.delete_button.isEnabled()
    assert not dialog.new_material_button.isHidden()
    assert dialog.import_button.text() == ""
    assert dialog.export_button.text() == ""
    assert dialog.delete_button.text() == ""
    assert dialog.import_button.accessibleName() == "Import materials"
    assert dialog.export_button.accessibleName() == (
        "Export selected materials"
    )
    assert dialog.delete_button.accessibleName() == (
        "Delete selected materials"
    )
    assert dialog.delete_action.text() == "Delete"
    assert not dialog.delete_action.icon().isNull()
    assert not dialog.import_button.icon().isNull()
    assert not dialog.export_button.icon().isNull()
    assert not dialog.delete_button.icon().isNull()
    assert dialog.close_button.text() == ""
    assert dialog.close_button.accessibleName() == "Close material library"
    assert not dialog.close_button.icon().isNull()
    dialog.material_tree.setCurrentItem(fluid_group)
    assert dialog.add_to_project_button.isEnabled()
    assert dialog.export_button.isEnabled()
    assert dialog.delete_button.isEnabled()
    assert set(dialog._selected_ids()) == {
        fluid_group.child(index).data(0, Qt.ItemDataRole.UserRole)
        for index in range(fluid_group.childCount())
    }


def test_selecting_library_folder_adds_all_contained_materials(
    qtbot, tmp_path
):
    """Import every material in a selected category folder."""
    library, air, _, _ = make_library(tmp_path)
    argon = FluidSpec(name="Argon")
    library.materials.append(argon)
    project = Project()
    dialog = LibraryDialog(project, library)
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(dialog.material_tree.topLevelItem(0))

    dialog.add_to_project()

    assert {material.name for material in project.materials} == {
        air.name, argon.name
    }
    assert all(material.id not in {air.id, argon.id}
               for material in project.materials)


def test_add_selected_material_to_project_creates_new_id(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Copy a library material into the project without reusing its ID."""
    library, air, _, _ = make_library(tmp_path)
    project = Project()
    dialog = LibraryDialog(project, library)
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(
        dialog.material_tree.topLevelItem(0).child(0)
    )
    messages = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args: messages.append(args)
    )

    dialog.add_to_project()

    assert len(project.materials) == 1
    assert project.materials[0].name == air.name
    assert project.materials[0].id != air.id
    assert project.is_modified
    assert not messages
    assert dialog.status_label.text() == "Added 1 material(s) to the project."


def test_add_poroelastic_material_also_copies_selected_frame(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Copy a missing frame automatically and remap the new frame ID."""
    library, _, frame, foam = make_library(tmp_path)
    project = Project()
    dialog = LibraryDialog(project, library)
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(
        dialog.material_tree.topLevelItem(4).child(0)
    )
    questions = []

    def answer_yes(*args):
        questions.append(args)
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", answer_yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)

    dialog.add_to_project()

    copied_frame = next(
        material
        for material in project.materials
        if isinstance(material, IsoMatSpec)
    )
    copied_foam = next(
        material
        for material in project.materials
        if isinstance(material, PoroElasticMatSpec)
    )
    assert not questions
    assert copied_frame.id != frame.id
    assert copied_foam.id != foam.id
    assert copied_foam.solid_mat_id == copied_frame.id
    assert dialog.additional_materials == [copied_frame]


def test_selection_only_returns_copy_without_changing_project(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Return selected copies to a parent editor instead of adding them."""
    library, _, frame, _ = make_library(tmp_path)
    project = Project()
    dialog = LibraryDialog(
        project,
        library,
        selection_only=True,
    )
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(
        dialog.material_tree.topLevelItem(4).child(0)
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    dialog.add_to_project()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert len(dialog.selected_materials) == 1
    assert len(dialog.additional_materials) == 1
    assert isinstance(dialog.additional_materials[0], IsoMatSpec)
    assert dialog.selected_materials[0].solid_mat_id == (
        dialog.additional_materials[0].id
    )
    assert project.materials == []
    assert project.find_material_by_id(frame.id) is None


def test_import_materials_action_adds_new_ids_and_saves_library(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Import a JSON file through the dialog and persist the new material."""
    imported_source = FluidSpec(name="Imported air")
    source_path = tmp_path / "source.json"
    source_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "materials": [imported_source.to_dict()],
            }
        ),
        encoding="utf-8",
    )
    library = MaterialLibrary(tmp_path / "library.json")
    library.save()
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: (str(source_path), "Material files (*.json)"),
    )

    dialog.import_materials()

    imported_material = next(
        material
        for material in library.materials
        if material.name == "Imported air"
    )
    assert len(library.materials) == 1
    assert imported_material.id != imported_source.id
    assert library.path.exists()
    assert dialog.material_tree.topLevelItem(0).childCount() == 1


def test_create_material_from_library_persists_new_material(
    qtbot, tmp_path, monkeypatch
):
    """Create a validated material directly in the reusable library."""
    library = MaterialLibrary(tmp_path / "library.json")
    library.save()
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)

    def accept_material(editor):
        editor.name_edit.setText("Water")
        editor.field_widgets["c0"].setText("1480")
        editor.save_material()
        return editor.result()

    monkeypatch.setattr(MaterialEditorDialog, "exec", accept_material)

    dialog.create_material()

    assert len(library.materials) == 1
    assert library.materials[0].name == "Water"
    assert library.materials[0].c0 == 1480
    assert library.path.exists()
    assert dialog.material_tree.topLevelItem(0).child(0).text(0) == "Water"


def test_edit_selected_material_updates_library_entry_in_place(
    qtbot, tmp_path, monkeypatch
):
    """Persist edits while keeping the material's ID and tree position."""
    library, air, _, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(
        dialog.material_tree.topLevelItem(0).child(0)
    )

    def accept_edit(editor):
        editor.name_edit.setText("Dry air")
        editor.field_widgets["c0"].setText("344")
        editor.save_material()
        return editor.result()

    monkeypatch.setattr(MaterialEditorDialog, "exec", accept_edit)

    item = dialog.material_tree.topLevelItem(0).child(0)
    dialog.material_tree.itemDoubleClicked.emit(item, 0)

    updated = next(item for item in library.materials if item.id == air.id)
    assert updated.name == "Dry air"
    assert updated.c0 == 344
    assert library.materials[0].id == air.id
    assert dialog.material_tree.topLevelItem(0).child(0).text(0) == "Dry air"
    persisted = MaterialLibrary(library.path)
    assert next(item for item in persisted.load() if item.id == air.id).name == (
        "Dry air"
    )


def test_left_click_delete_button_deletes_selected_material(
    qtbot, tmp_path, monkeypatch
):
    """Delete the selected material from the icon-only toolbar button."""
    library, air, _, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    item = dialog.material_tree.topLevelItem(0).child(0)
    dialog.material_tree.setCurrentItem(item)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    qtbot.mouseClick(dialog.delete_button, Qt.MouseButton.LeftButton)

    assert all(material.id != air.id for material in library.materials)
    assert dialog.material_tree.topLevelItem(0).childCount() == 0


def test_right_click_material_offers_delete_context_action(
    qtbot, tmp_path, monkeypatch
):
    """Keep Delete available in a tree-row context menu."""
    library, air, _, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    item = dialog.material_tree.topLevelItem(0).child(0)
    position = dialog.material_tree.visualItemRect(item).center()
    shown_actions = []
    monkeypatch.setattr(
        QMenu,
        "exec",
        lambda menu, *args: shown_actions.extend(menu.actions()),
    )

    dialog._show_material_context_menu(position)

    assert dialog._selected_ids() == [air.id]
    assert [action.text() for action in shown_actions] == ["Delete"]


def test_export_selected_action_adds_json_extension(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Export the selected material through the file chooser."""
    library, air, _, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(
        dialog.material_tree.topLevelItem(0).child(0)
    )
    export_path = tmp_path / "selected-materials"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args: (str(export_path), "Material files (*.json)"),
    )

    dialog.export_selected()

    final_path = tmp_path / "selected-materials.json"
    data = json.loads(final_path.read_text(encoding="utf-8"))
    assert data["materials"][0]["id"] == air.id


def test_delete_selected_removes_material_from_library(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Delete a selected item only after explicit confirmation."""
    library, air, _, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(
        dialog.material_tree.topLevelItem(0).child(0)
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    dialog.delete_selected()

    assert library.materials[0].id != air.id
    assert dialog.material_tree.topLevelItem(0).childCount() == 0


def test_delete_selected_library_folder_removes_all_materials(
    qtbot, tmp_path, monkeypatch
):
    """Delete every library material contained in a selected category."""
    library, air, _, _ = make_library(tmp_path)
    argon = FluidSpec(name="Argon")
    library.materials.append(argon)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.material_tree.topLevelItem(0).setSelected(True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    dialog.delete_selected()

    assert not any(
        material.id in {air.id, argon.id} for material in library.materials
    )
    assert dialog.material_tree.topLevelItem(0).childCount() == 0


def test_delete_frame_is_blocked_when_library_material_uses_it(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Protect a frame that is referenced by a library poroelastic spec."""
    library, _, frame, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.material_tree.setCurrentItem(
        dialog.material_tree.topLevelItem(3).child(0)
    )
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    dialog.delete_selected()

    assert any("Open-cell foam" in message for message in messages)
    assert any(material.id == frame.id for material in library.materials)
