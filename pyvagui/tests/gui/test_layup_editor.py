"""Tests for layup layer editing and row reordering."""

from PyQt6.QtCore import QCoreApplication, QPointF, Qt
from PyQt6.QtWidgets import QComboBox, QDialog, QMessageBox, QToolButton

from pyvagui.gui.layup_editor import LayupEditorDialog
from pyvagui.model.layup import LayerSpec, LayerType, Layup, PerforationSpec
from pyvagui.model.materials import FluidSpec, IsoMatSpec
from pyvagui.model.project import Project


def make_project():
    """Create a project with air and a plate-capable material."""
    air = FluidSpec(name="Air")
    aluminium = IsoMatSpec(name="Aluminium")
    return Project(materials=[air, aluminium]), air, aluminium


def select_material(button, material_id):
    """Trigger the menu action matching a project material identifier."""
    for category_action in button.menu().actions():
        submenu = category_action.menu()
        if submenu is None:
            continue
        for material_action in submenu.actions():
            if material_action.data() == material_id:
                material_action.trigger()
                QCoreApplication.processEvents()
                return
    raise AssertionError(f"No material action found for {material_id}")


def test_add_move_and_delete_layer_rows(qtbot):
    """Keep the layup model ordered as rows are added, moved, or removed."""
    project, air, aluminium = make_project()
    layup = Layup(
        name="Test stack",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id=aluminium.id,
                thickness=0.002,
                layer_type=LayerType.MASS,
            ),
        ],
    )
    dialog = LayupEditorDialog(project, layup)
    qtbot.addWidget(dialog)

    dialog.add_layer()
    dialog.layer_table.setCurrentCell(0, 0)
    dialog.move_selected(1)
    dialog.remove_layer(2)

    assert dialog.layer_table.rowCount() == 2
    assert dialog.layup.layers == [layup.layers[1], layup.layers[0]]
    assert dialog.summary_label.text() == "2 layers - 22 mm total"
    assert len(layup.layers) == 2


def test_save_converts_displayed_mm_to_model_meters(qtbot):
    """Convert edited thicknesses to meters and leave the original alone."""
    project, air, _ = make_project()
    original = Layup(
        name="Air gap",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.01,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    dialog = LayupEditorDialog(project, original)
    qtbot.addWidget(dialog)
    dialog.name_edit.setText("Changed gap")
    dialog.layer_table.cellWidget(0, 2).setText("12,5")

    dialog.save_layup()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_layup.name == "Changed gap"
    assert dialog.result_layup.layers[0].thickness == 0.0125
    assert original.layers[0].thickness == 0.01


def test_invalid_layup_shows_errors_and_remains_open(qtbot, monkeypatch):
    """Keep invalid numeric input open and report the affected layer."""
    project, air, _ = make_project()
    layup = Layup(
        name="Invalid",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.01,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    dialog = LayupEditorDialog(project, layup)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.layer_table.cellWidget(0, 2).setText("invalid")
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    dialog.save_layup()

    assert dialog.isVisible()
    assert not messages
    assert dialog.error_label.isVisible()
    assert (
        "Layer 1: thickness must be a finite number"
        in dialog.error_label.text()
    )


def test_changing_material_resets_layer_type_and_perforation(qtbot):
    """Reset a plate layer to fluid and clear its invalid perforation."""
    project, air, aluminium = make_project()
    layup = Layup(
        layers=[
            LayerSpec(
                material_id=aluminium.id,
                thickness=0.002,
                layer_type=LayerType.PLATE,
                perforation=PerforationSpec(
                    hole_radius=0.001,
                    distance=0.02,
                ),
            )
        ]
    )
    dialog = LayupEditorDialog(project, layup)
    qtbot.addWidget(dialog)
    material_button = dialog.layer_table.cellWidget(0, 1)
    assert isinstance(material_button, QToolButton)

    select_material(material_button, air.id)

    assert dialog.layup.layers[0].material_id == air.id
    assert dialog.layup.layers[0].layer_type is LayerType.FLUID
    assert dialog.layup.layers[0].perforation is None


def test_layer_type_options_follow_selected_material(qtbot):
    """Show Solid/Plate/Mass choices and disable single-choice combos."""
    project, air, aluminium = make_project()
    layup = Layup(
        layers=[
            LayerSpec(
                material_id=aluminium.id,
                thickness=0.002,
                layer_type=LayerType.PLATE,
            )
        ]
    )
    dialog = LayupEditorDialog(project, layup)
    qtbot.addWidget(dialog)
    type_combo = dialog.layer_table.cellWidget(0, 3)

    assert isinstance(type_combo, QComboBox)
    assert type_combo.count() == 3
    assert type_combo.isEnabled()

    material_button = dialog.layer_table.cellWidget(0, 1)
    assert isinstance(material_button, QToolButton)
    assert not material_button.icon().isNull()
    assert material_button.text() == "Aluminium"
    assert material_button.toolButtonStyle() == (
        Qt.ToolButtonStyle.ToolButtonTextBesideIcon
    )
    assert [action.text() for action in material_button.menu().actions()] == [
        "Fluid", "Isomat"
    ]
    isomat_menu = material_button.menu().actions()[1].menu()
    assert [action.text() for action in isomat_menu.actions()] == ["Aluminium"]
    select_material(material_button, air.id)
    type_combo = dialog.layer_table.cellWidget(0, 3)
    assert type_combo.count() == 1
    assert not type_combo.isEnabled()
    assert dialog.move_up_button.text() == ""
    assert dialog.move_up_button.accessibleName() == "Move layer up"
    assert not dialog.move_up_button.icon().isNull()
    delete_button = dialog.layer_table.cellWidget(0, 5)
    assert delete_button.text() == ""
    assert delete_button.accessibleName() == "Delete layer"
    assert not delete_button.icon().isNull()


def test_perforation_button_opens_editor_and_updates_row(qtbot, monkeypatch):
    """Apply an accepted perforation from the nested perforation dialog."""
    project, _, aluminium = make_project()
    layup = Layup(
        layers=[
            LayerSpec(
                material_id=aluminium.id,
                thickness=0.002,
                layer_type=LayerType.PLATE,
            )
        ]
    )
    dialog = LayupEditorDialog(project, layup)
    qtbot.addWidget(dialog)

    class AcceptedPerforationDialog:
        """Provide an accepted perforation without opening a modal window."""

        def __init__(self, perforation, parent):
            self.result_perforation = PerforationSpec(
                hole_radius=0.001,
                distance=0.02,
            )

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.layup_editor.PerforationDialog",
        AcceptedPerforationDialog,
    )

    dialog.edit_perforation(0)

    assert dialog.layup.layers[0].perforation == PerforationSpec(
        hole_radius=0.001,
        distance=0.02,
    )
    assert dialog.layer_table.cellWidget(0, 4).text() == (
        "r = 1 mm, d = 20 mm"
    )


def test_drop_event_reorders_model_and_rebuilds_embedded_widgets(qtbot):
    """Route an internal drop through Layup.move_layer and full refresh."""
    project, air, aluminium = make_project()
    layup = Layup(
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id=aluminium.id,
                thickness=0.002,
                layer_type=LayerType.MASS,
            ),
        ]
    )
    dialog = LayupEditorDialog(project, layup)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.layer_table.setCurrentCell(0, 0)
    target_point = dialog.layer_table.visualItemRect(
        dialog.layer_table.item(1, 0)
    ).center()

    class DropEvent:
        """Small event object with the methods used by LayerTableWidget."""

        def __init__(self, point):
            self.point = point
            self.was_accepted = False

        def position(self):
            return QPointF(self.point)

        def accept(self):
            self.was_accepted = True

        def ignore(self):
            self.was_accepted = False

    event = DropEvent(target_point)
    dialog.layer_table.dropEvent(event)

    assert event.was_accepted
    assert dialog.layup.layers[0].material_id == aluminium.id
    assert dialog.layer_table.cellWidget(0, 1).text() == "Aluminium"
