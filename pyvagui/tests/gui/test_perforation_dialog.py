"""Tests for perforation editing and unit conversion."""

from PyQt6.QtWidgets import QDialog, QMessageBox

from pyvagui.gui.perforation_dialog import (
    PerforationDialog,
    m_to_mm,
    mm_to_m,
)
from pyvagui.model.layup import PerforationSpec


def test_length_helpers_convert_between_millimeters_and_meters():
    """Use GUI millimeters and model SI meters consistently."""
    assert mm_to_m(2.5) == 0.0025
    assert m_to_mm(0.0025) == 2.5


def test_perforation_dialog_saves_mm_as_si_values(qtbot):
    """Convert entered millimeter dimensions to meters on Save."""
    dialog = PerforationDialog(None)
    qtbot.addWidget(dialog)
    dialog.radius_edit.setText("1.5")
    dialog.distance_edit.setText("20")

    dialog.save_perforation()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_perforation == PerforationSpec(
        hole_radius=0.0015,
        distance=0.02,
    )


def test_perforation_dialog_remove_clears_existing_value(qtbot):
    """Remove an existing perforation without changing its input object."""
    original = PerforationSpec(hole_radius=0.001, distance=0.02)
    dialog = PerforationDialog(original)
    qtbot.addWidget(dialog)

    dialog.remove_perforation()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_perforation is None
    assert original == PerforationSpec(hole_radius=0.001, distance=0.02)


def test_invalid_perforation_keeps_dialog_open_and_shows_errors(
    qtbot,
    monkeypatch,
):
    """Reject overlapping holes and leave the editor open for correction."""
    dialog = PerforationDialog(None)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.radius_edit.setText("10")
    dialog.distance_edit.setText("20")
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    dialog.save_perforation()

    assert dialog.result() == QDialog.DialogCode.Rejected
    assert dialog.error_label.isVisible()
    assert any("smaller than hole distance" in item for item in messages)
