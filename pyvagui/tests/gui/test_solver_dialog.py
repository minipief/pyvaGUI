"""Tests for solver preset, frequency, fluid, and layup controls."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QListWidget, QMessageBox

from pyvagui.gui.solver_dialog import SolverEditorDialog
from pyvagui.model.layup import LayerSpec, LayerType, Layup
from pyvagui.model.materials import EquivalentFluidSpec, FluidSpec
from pyvagui.model.project import Project
from pyvagui.model.solvers import (
    BoundaryCondition,
    FrequencySettings,
    SolverSpec,
    SolverType,
)


def make_project():
    """Create a project with two fluids and one selectable layup."""
    air = FluidSpec(name="Air")
    water = FluidSpec(name="Water")
    fibre = EquivalentFluidSpec(name="Glass wool")
    layup = Layup(
        name="Absorber",
        layers=[
            LayerSpec(
                material_id=fibre.id,
                thickness=0.05,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    return Project(
        name="Test project",
        materials=[air, water, fibre],
        layups=[layup],
    ), air, water, layup


def fill_valid_solver(dialog, air, water, layup):
    """Fill fields shared by successful solver-dialog tests."""
    dialog.name_edit.setText("Air to water")
    dialog.sending_fluid_combo.setCurrentIndex(
        dialog.sending_fluid_combo.findData(air.id)
    )
    dialog.receiving_fluid_combo.setCurrentIndex(
        dialog.receiving_fluid_combo.findData(water.id)
    )
    dialog.frequency_start_edit.setText("100")
    dialog.frequency_end_edit.setText("10000")
    dialog.frequency_points_edit.setText("21")
    for index in range(dialog.layup_list.count()):
        item = dialog.layup_list.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == layup.id:
            item.setCheckState(Qt.CheckState.Checked)


def test_solver_dialog_lists_presets_and_switches_angle_fields(qtbot):
    """Display all solver names and toggle the angle controls by preset."""
    project, _, _, _ = make_project()
    dialog = SolverEditorDialog(project)
    qtbot.addWidget(dialog)
    dialog.show()

    assert [
        dialog.solver_type_combo.itemText(index)
        for index in range(dialog.solver_type_combo.count())
    ] == [solver_type.display_name for solver_type in SolverType]
    assert dialog.single_angle_edit.isVisible() is True
    assert dialog.maximum_angle_edit.isVisible() is False

    dialog.solver_type_combo.setCurrentIndex(
        dialog.solver_type_combo.findData(SolverType.TRANSMISSION_DIFFUSE)
    )

    assert dialog.single_angle_edit.isVisible() is False
    assert dialog.maximum_angle_edit.isVisible() is True
    assert dialog.diffuse_hint.isVisible() is True


def test_solver_dialog_fluid_choices_exclude_equivalent_fluids(qtbot):
    """Show only FluidSpec objects in sending and receiving selectors."""
    project, air, water, _ = make_project()
    dialog = SolverEditorDialog(project)
    qtbot.addWidget(dialog)

    sending_names = [
        dialog.sending_fluid_combo.itemText(index)
        for index in range(dialog.sending_fluid_combo.count())
    ]

    assert sending_names == ["Select fluid", "Air", "Water"]
    assert all(
        isinstance(
            project.find_material_by_id(
                dialog.sending_fluid_combo.itemData(index)
            ),
            FluidSpec,
        )
        for index in range(1, dialog.sending_fluid_combo.count())
    )
    assert air.id != water.id


def test_valid_solver_dialog_builds_solver_spec(qtbot):
    """Accept a solver with frequencies, fluid IDs, and a layup selection."""
    project, air, water, layup = make_project()
    dialog = SolverEditorDialog(project)
    qtbot.addWidget(dialog)
    fill_valid_solver(dialog, air, water, layup)
    dialog.single_angle_edit.setText("30")
    dialog.boundary_combo.setCurrentIndex(
        dialog.boundary_combo.findData(BoundaryCondition.EQUIVALENT_FLUID)
    )

    dialog.save_solver()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_solver.name == "Air to water"
    assert dialog.result_solver.solver_type is SolverType.ABSORPTION
    assert dialog.result_solver.sending_fluid_id == air.id
    assert dialog.result_solver.receiving_fluid_id == water.id
    assert dialog.result_solver.layup_ids == [layup.id]
    assert dialog.result_solver.angle_deg == 30.0
    assert dialog.result_solver.frequencies.n_points == 21
    assert dialog.result_solver.boundary_condition is (
        BoundaryCondition.EQUIVALENT_FLUID
    )


def test_diffuse_solver_saves_maximum_angle(qtbot):
    """Use the diffuse-angle field for a diffuse solver preset."""
    project, air, water, layup = make_project()
    dialog = SolverEditorDialog(project)
    qtbot.addWidget(dialog)
    dialog.solver_type_combo.setCurrentIndex(
        dialog.solver_type_combo.findData(SolverType.TRANSMISSION_DIFFUSE)
    )
    fill_valid_solver(dialog, air, water, layup)
    dialog.maximum_angle_edit.setText("78")

    dialog.save_solver()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_solver.max_angle_deg == 78.0
    assert dialog.result_solver.solver_type is SolverType.TRANSMISSION_DIFFUSE


def test_impedance_uses_either_boundary_or_receiving_fluid(qtbot):
    """Keep the impedance termination mutually exclusive in the form."""
    project, air, water, layup = make_project()
    dialog = SolverEditorDialog(project)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.solver_type_combo.setCurrentIndex(
        dialog.solver_type_combo.findData(SolverType.IMPEDANCE)
    )
    fill_valid_solver(dialog, air, water, layup)

    assert dialog.receiving_fluid_combo.isHidden()
    dialog.impedance_termination_combo.setCurrentIndex(
        dialog.impedance_termination_combo.findData(
            BoundaryCondition.EQUIVALENT_FLUID
        )
    )
    assert dialog.receiving_fluid_combo.isVisible()
    dialog.save_solver()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_solver.boundary_condition is (
        BoundaryCondition.EQUIVALENT_FLUID
    )
    assert dialog.result_solver.receiving_fluid_id == water.id

    fixed_dialog = SolverEditorDialog(project)
    qtbot.addWidget(fixed_dialog)
    fixed_dialog.solver_type_combo.setCurrentIndex(
        fixed_dialog.solver_type_combo.findData(SolverType.IMPEDANCE)
    )
    fill_valid_solver(fixed_dialog, air, water, layup)
    fixed_dialog.save_solver()

    assert fixed_dialog.result() == QDialog.DialogCode.Accepted
    assert fixed_dialog.result_solver.boundary_condition is (
        BoundaryCondition.FIXED
    )
    assert fixed_dialog.result_solver.receiving_fluid_id == ""


def test_solver_invalid_values_show_all_errors_and_keep_dialog_open(
    qtbot,
    monkeypatch,
):
    """Combine parsing and model validation messages without closing."""
    project, _, _, _ = make_project()
    dialog = SolverEditorDialog(project)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.name_edit.setText(" ")
    dialog.sending_fluid_combo.setCurrentIndex(0)
    dialog.receiving_fluid_combo.setCurrentIndex(0)
    dialog.frequency_start_edit.setText("not a frequency")
    dialog.frequency_end_edit.setText("10")
    dialog.frequency_points_edit.setText("one")
    dialog.single_angle_edit.setText("90")
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    dialog.save_solver()

    banner = dialog.error_label.text()
    assert dialog.isVisible()
    assert not messages
    assert dialog.error_label.isVisible()
    assert "Start frequency must be a finite number" in banner
    assert "Number of points must be an integer" in banner
    assert "Solver name must not be empty" in banner
    assert "Select at least one layup" in banner
    assert "Angle must be in [0, 90)" in banner


def test_edit_solver_uses_copy_and_restricts_layup_list(qtbot):
    """Preserve the original solver when editing is cancelled."""
    project, air, water, layup = make_project()
    solver = SolverSpec(
        name="Existing",
        solver_type=SolverType.IMPEDANCE,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=10,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=water.id,
        layup_ids=[layup.id],
    )
    dialog = SolverEditorDialog(project, solver)
    qtbot.addWidget(dialog)

    assert not dialog.is_new
    assert isinstance(dialog.layup_list, QListWidget)
    assert dialog.layup_list.count() == 1
    assert dialog.layup_list.item(0).checkState() == Qt.CheckState.Checked
    dialog.name_edit.setText("Changed")
    dialog.reject()

    assert solver.name == "Existing"
    assert dialog.result_solver is None
