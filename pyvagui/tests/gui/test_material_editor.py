"""Tests for the dataclass-driven material editor dialog."""

import pytest
from PyQt6.QtWidgets import QComboBox, QDialog, QMessageBox

from pyvagui.gui.material_editor import MaterialEditorDialog
from pyvagui.model.materials import (
    FluidSpec,
    IsoMatSpec,
    PoroElasticMatSpec,
)
from pyvagui.model.project import Project


def test_new_material_dialog_creates_valid_fluid(qtbot):
    """Parse a decimal comma and scientific notation before accepting."""
    dialog = MaterialEditorDialog(Project())
    qtbot.addWidget(dialog)
    dialog.name_edit.setText("Water")
    dialog.field_widgets["c0"].setText("1.5e3")
    dialog.field_widgets["rho0"].setText("1,23")

    dialog.save_material()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert isinstance(dialog.material, FluidSpec)
    assert dialog.material.name == "Water"
    assert dialog.material.c0 == 1500.0
    assert dialog.material.rho0 == 1.23


def test_invalid_input_shows_all_errors_and_keeps_dialog_open(
    qtbot,
    monkeypatch,
):
    """Keep invalid material data in the dialog and report all errors."""
    dialog = MaterialEditorDialog(Project())
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.name_edit.setText(" ")
    dialog.field_widgets["c0"].setText("not a number")
    dialog.field_widgets["rho0"].setText("-1")
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    dialog.save_material()

    assert dialog.isVisible()
    assert dialog.result() == QDialog.DialogCode.Rejected
    assert len(messages) == 1
    assert "c0: enter a valid finite number" in messages[0]
    assert "Material name must not be empty" in messages[0]
    assert "density must be > 0" in messages[0]


def test_edit_dialog_uses_copy_and_disables_material_type(qtbot):
    """Keep the original model unchanged when an edit dialog is cancelled."""
    original = FluidSpec(name="Air", c0=343.0)
    dialog = MaterialEditorDialog(Project(), original)
    qtbot.addWidget(dialog)

    assert not dialog.type_combo.isEnabled()
    dialog.name_edit.setText("Changed air")
    dialog.field_widgets["c0"].setText("400")
    dialog.reject()

    assert original.name == "Air"
    assert original.c0 == 343.0
    assert dialog.material is None


def test_poroelastic_dialog_offers_only_project_isomats(qtbot):
    """Show the project's isotropic frame materials in the reference field."""
    frame = IsoMatSpec(name="Aluminium")
    project = Project(materials=[frame])
    dialog = MaterialEditorDialog(
        project,
        PoroElasticMatSpec(name="Foam", solid_mat_id=frame.id),
    )
    qtbot.addWidget(dialog)
    frame_combo = dialog.field_widgets["solid_mat_id"]

    assert isinstance(frame_combo, QComboBox)
    assert frame_combo.count() == 2
    assert frame_combo.itemText(1) == "Aluminium"
    assert frame_combo.currentData() == frame.id


def test_poroelastic_dialog_accepts_frame_copy_from_library(qtbot):
    """Validate a selected poroelastic copy against its pending frame copy."""
    frame_copy = IsoMatSpec(name="Library frame")
    poroelastic_copy = PoroElasticMatSpec(
        name="Library foam",
        solid_mat_id=frame_copy.id,
    )
    dialog = MaterialEditorDialog(Project())
    qtbot.addWidget(dialog)
    dialog.material_spec = poroelastic_copy
    dialog.additional_materials = [frame_copy]
    dialog._rebuild_property_fields()
    frame_combo = dialog.field_widgets["solid_mat_id"]
    frame_combo.setCurrentIndex(frame_combo.findData(frame_copy.id))

    dialog.save_material()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.material.solid_mat_id == frame_copy.id


def test_new_material_type_switch_builds_type_specific_fields(qtbot):
    """Rebuild fields from the selected dataclass when creating a material."""
    dialog = MaterialEditorDialog(Project())
    qtbot.addWidget(dialog)
    equivalent_index = dialog.type_combo.findText("EquivalentFluid")

    dialog.type_combo.setCurrentIndex(equivalent_index)

    assert "flow_res" in dialog.field_widgets
    assert "limp" in dialog.field_widgets
    assert "Pr" not in dialog.field_widgets
    assert dialog.field_widgets["limp"].isChecked()


@pytest.mark.parametrize(
    ("text", "expected"),
    [("7.1e10", 7.1e10), ("1,25", 1.25), ("nan", None), ("", None)],
)
def test_parse_float_accepts_finite_decimal_values(text, expected):
    """Parse comma and exponent notation and reject invalid values."""
    from pyvagui.gui.material_editor import parse_float

    assert parse_float(text) == expected
