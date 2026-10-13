"""Tests for project ownership, references, and JSON persistence."""

import json

import pytest

from pyvagui.model.layup import LayerSpec, LayerType, Layup
from pyvagui.model.materials import (
    EquivalentFluidSpec,
    FluidSpec,
    IsoMatSpec,
    PoroElasticMatSpec,
)
from pyvagui.model.project import Project
from pyvagui.model.solvers import (
    FrequencySettings,
    SolverSpec,
    SolverType,
)


def make_project() -> tuple[
    Project, FluidSpec, EquivalentFluidSpec, Layup, SolverSpec
]:
    """Create a valid project with one material, layup, and solver set."""
    air = FluidSpec(name="Air")
    fibre = EquivalentFluidSpec(name="Fibre")
    layup = Layup(
        name="Absorber",
        layers=[
            LayerSpec(
                material_id=fibre.id,
                thickness=0.1,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    solver = SolverSpec(
        name="Normal absorption",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=11,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[layup.id],
    )
    project = Project(name="Test project")
    project.add_material(air)
    project.add_material(fibre)
    project.add_layup(layup)
    project.add_solver(solver)
    return project, air, fibre, layup, solver


def test_project_save_and_load_round_trip(tmp_path):
    """Persist project objects and reset path and modified state on load."""
    project, air, fibre, layup, solver = make_project()
    path = tmp_path / "project.json"

    project.save(path)
    loaded = Project.load(path)

    assert project.file_path == path
    assert project.is_modified is False
    assert loaded.file_path == path
    assert loaded.is_modified is False
    assert loaded.name == project.name
    assert loaded.materials == [air, fibre]
    assert loaded.layups == [layup]
    assert loaded.solvers == [solver]
    assert "results" not in json.loads(path.read_text(encoding="utf-8"))


def test_project_to_dict_and_from_dict_preserve_project_data():
    """Restore material, layup, and solver values from a project dictionary."""
    project, _, _, _, _ = make_project()

    restored = Project.from_dict(project.to_dict())

    assert restored.name == project.name
    assert restored.materials == project.materials
    assert restored.layups == project.layups
    assert restored.solvers == project.solvers
    assert restored.file_path is None
    assert restored.is_modified is False


def test_project_rejects_unsupported_format_version():
    """Reject project files whose format version is not supported."""
    with pytest.raises(ValueError, match="format version"):
        Project.from_dict({"format_version": 2})


def test_project_add_find_remove_and_modified_state():
    """Manage all project object types and mark mutations as unsaved."""
    project, air, _, layup, solver = make_project()
    project.is_modified = False

    assert project.find_material_by_id(air.id) is air
    assert project.find_layup_by_id(layup.id) is layup
    assert project.find_solver_by_id(solver.id) is solver
    assert project.find_material_by_id("unknown") is None
    assert project.find_layup_by_id("unknown") is None
    assert project.find_solver_by_id("unknown") is None

    removed_solver = project.remove_solver(solver.id)
    removed_layup = project.remove_layup(layup.id)
    removed_material = project.remove_material(air.id)

    assert removed_solver is solver
    assert removed_layup is layup
    assert removed_material is air
    assert project.is_modified
    materials_by_id = project.materials_by_id()
    assert materials_by_id == {
        project.materials[0].id: project.materials[0]
    }


def test_project_add_rejects_duplicate_identifiers():
    """Prevent duplicate IDs in each project-owned collection."""
    project, air, _, layup, solver = make_project()

    with pytest.raises(ValueError, match="Material id"):
        project.add_material(air)
    with pytest.raises(ValueError, match="Layup id"):
        project.add_layup(layup)
    with pytest.raises(ValueError, match="Solver id"):
        project.add_solver(solver)


def test_project_copy_from_library_and_missing_frame_lookup():
    """Give a library copy a new id and report its absent frame dependency."""
    project, _, _, _, _ = make_project()
    frame = IsoMatSpec(name="Library frame")
    poroelastic = PoroElasticMatSpec(
        name="Library porous material",
        solid_mat_id=frame.id,
    )

    copied = project.copy_from_library(poroelastic)

    assert copied.id != poroelastic.id
    assert copied.solid_mat_id == frame.id
    assert project.missing_frame_material_id(poroelastic) == frame.id
    project.add_material(frame)
    assert project.missing_frame_material_id(poroelastic) is None
    assert project.missing_frame_material_id(frame) is None


def test_material_users_lists_material_layup_and_solver_names():
    """Find poroelastic, layer, and solver dependencies by display name."""
    project, air, fibre, layup, solver = make_project()
    frame = IsoMatSpec(name="Frame")
    poroelastic = PoroElasticMatSpec(
        name="Frame-backed foam",
        solid_mat_id=frame.id,
    )
    project.add_material(frame)
    project.add_material(poroelastic)

    assert project.material_users(air.id) == [solver.name]
    assert project.material_users(fibre.id) == [layup.name]
    assert project.material_users(frame.id) == [poroelastic.name]


def test_project_validation_collects_material_and_reference_errors():
    """Report missing frames, layer materials, and solver references."""
    air = FluidSpec(name="Air")
    poroelastic = PoroElasticMatSpec(
        name="Broken foam",
        solid_mat_id="missing-frame",
    )
    broken_layup = Layup(
        name="Broken stack",
        layers=[
            LayerSpec(
                material_id="missing-material",
                thickness=0.01,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    solver = SolverSpec(
        name="Broken solver",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=1000.0,
            n_points=3,
        ),
        sending_fluid_id="missing-sender",
        receiving_fluid_id=air.id,
        layup_ids=["missing-layup"],
    )
    project = Project(
        materials=[air, poroelastic],
        layups=[broken_layup],
        solvers=[solver],
    )

    errors = project.validate()

    assert any("frame material" in error for error in errors)
    assert any(
        "Layer 1" in error and "does not exist" in error
        for error in errors
    )
    assert any("Sending fluid does not exist" in error for error in errors)
    assert any("missing-layup" in error for error in errors)
