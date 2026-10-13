"""Tests for the material library dialog workflows."""

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog

from pyvagui.gui.library_dialog import LibraryDialog
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

    item = dialog.material_list.item(0)

    assert item.text() == "Air (Fluid)"
    assert item.data(Qt.ItemDataRole.UserRole) == air.id
    assert dialog.material_list.count() == 3


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
    dialog.material_list.setCurrentRow(0)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)

    dialog.add_to_project()

    assert len(project.materials) == 1
    assert project.materials[0].name == air.name
    assert project.materials[0].id != air.id
    assert project.is_modified


def test_add_poroelastic_material_also_copies_selected_frame(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Ask before copying a missing frame and remap the new frame ID."""
    library, _, frame, foam = make_library(tmp_path)
    project = Project()
    dialog = LibraryDialog(project, library)
    qtbot.addWidget(dialog)
    dialog.material_list.setCurrentRow(2)
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
    assert len(questions) == 1
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
    dialog.material_list.setCurrentRow(2)
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
    assert dialog.material_list.count() == 1


def test_export_selected_action_adds_json_extension(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Export the selected material through the file chooser."""
    library, air, _, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.material_list.setCurrentRow(0)
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
    dialog.material_list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    dialog.delete_selected()

    assert library.materials[0].id != air.id
    assert dialog.material_list.count() == 2


def test_delete_frame_is_blocked_when_library_material_uses_it(
    qtbot,
    tmp_path,
    monkeypatch,
):
    """Protect a frame that is referenced by a library poroelastic spec."""
    library, _, frame, _ = make_library(tmp_path)
    dialog = LibraryDialog(Project(), library)
    qtbot.addWidget(dialog)
    dialog.material_list.setCurrentRow(1)
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    dialog.delete_selected()

    assert any("Open-cell foam" in message for message in messages)
    assert any(material.id == frame.id for material in library.materials)
