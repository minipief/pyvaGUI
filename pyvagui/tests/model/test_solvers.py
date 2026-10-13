"""Tests for frequency settings and pyva solver calculations."""

from dataclasses import dataclass

import numpy as np
import pytest

from pyvagui.model.layup import LayerSpec, LayerType, Layup
from pyvagui.model.materials import (
    EquivalentFluidSpec,
    FluidSpec,
    MaterialSpec,
)
from pyvagui.model.solvers import (
    BoundaryCondition,
    FrequencySettings,
    SolverSpec,
    SolverType,
)


@dataclass
class ProjectStub:
    """Small project-shaped object for solver validation tests."""

    materials: list[MaterialSpec]
    layups: list[Layup]

    def materials_by_id(self) -> dict[str, MaterialSpec]:
        """Return the stub materials indexed by their identifiers."""
        return {material.id: material for material in self.materials}


def make_project() -> ProjectStub:
    """Create a project with air, fibre, and one valid layup."""
    air = FluidSpec(name="Air")
    fibre = EquivalentFluidSpec(name="Fibre")
    layup = Layup(
        name="Fibre absorber",
        layers=[
            LayerSpec(
                material_id=fibre.id,
                thickness=0.1,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    return ProjectStub(materials=[air, fibre], layups=[layup])


def make_solver(
    project: ProjectStub,
    solver_type: SolverType = SolverType.ABSORPTION,
) -> SolverSpec:
    """Create a valid solver referencing the stub project objects."""
    air = next(
        material
        for material in project.materials
        if isinstance(material, FluidSpec)
    )
    return SolverSpec(
        name="Test solver",
        solver_type=solver_type,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=9,
        ),
        angle_deg=30.0,
        max_angle_deg=78.0,
        boundary_condition=BoundaryCondition.FIXED,
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[project.layups[0].id],
    )


def test_frequency_settings_create_log_spacing_omega_and_labels():
    """Generate the requested number of logarithmically spaced samples."""
    settings = FrequencySettings(
        f_start=100.0,
        f_end=10000.0,
        n_points=5,
    )

    frequencies = settings.frequencies()

    assert np.allclose(frequencies, np.geomspace(100.0, 10000.0, 5))
    assert np.allclose(settings.omega(), 2 * np.pi * frequencies)
    assert settings.labels() == [f"{frequency:g}" for frequency in frequencies]


@pytest.mark.parametrize(
    ("f_start", "f_end", "n_points"),
    [
        (0.0, 1000.0, 5),
        (-1.0, 1000.0, 5),
        (1000.0, 1000.0, 5),
        (1000.0, 100.0, 5),
        (100.0, 1000.0, 1),
        (100.0, 1000.0, 2.5),
    ],
)
def test_frequency_settings_reject_invalid_values(
    f_start: float,
    f_end: float,
    n_points: int,
) -> None:
    """Reject non-positive, unordered, and undersampled frequency ranges."""
    settings = FrequencySettings(
        f_start=f_start,
        f_end=f_end,
        n_points=n_points,
    )

    assert settings.validate()
    with pytest.raises(ValueError):
        settings.frequencies()


def test_frequency_settings_round_trip():
    """Preserve all three frequency values through serialization."""
    settings = FrequencySettings(
        f_start=80.0,
        f_end=8000.0,
        n_points=31,
    )

    assert FrequencySettings.from_dict(settings.to_dict()) == settings


@pytest.mark.parametrize(
    ("solver_type", "display_name", "diffuse", "complex_result"),
    [
        (SolverType.ABSORPTION, "Absorption", False, False),
        (SolverType.ABSORPTION_DIFFUSE, "Absorption diffuse", True, False),
        (SolverType.TRANSMISSION, "Transmission", False, False),
        (
            SolverType.TRANSMISSION_DIFFUSE,
            "Transmission diffuse",
            True,
            False,
        ),
        (
            SolverType.TRANSMISSION_ALLARD,
            "Transmission (Allard)",
            False,
            False,
        ),
        (SolverType.IMPEDANCE, "Impedance", False, True),
    ],
)
def test_solver_type_helpers(
    solver_type: SolverType,
    display_name: str,
    diffuse: bool,
    complex_result: bool,
) -> None:
    """Expose preset labels and angle/result characteristics."""
    assert solver_type.display_name == display_name
    assert solver_type.uses_diffuse_angle() is diffuse
    assert solver_type.uses_single_angle() is (not diffuse)
    assert solver_type.is_complex() is complex_result


def test_solver_spec_helpers_and_round_trip():
    """Serialize enums by value and restore all solver configuration."""
    project = make_project()
    solver = make_solver(project, SolverType.IMPEDANCE)
    data = solver.to_dict()

    restored = SolverSpec.from_dict(data)

    assert data["solver_type"] == "impedance"
    assert data["boundary_condition"] == "fixed"
    assert restored == solver
    assert solver.uses_single_angle()
    assert not solver.uses_diffuse_angle()
    assert solver.is_complex()


def test_solver_validation_accepts_valid_project():
    """Accept a solver with existing layup and fluid references."""
    project = make_project()

    assert make_solver(project).validate(project) == []


def test_solver_validation_reports_missing_references_and_bad_fields():
    """Collect name, selection, reference, frequency, and angle errors."""
    project = make_project()
    solver = SolverSpec(
        name=" ",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=0.0,
            f_end=100.0,
            n_points=1,
        ),
        angle_deg=90.0,
        sending_fluid_id="missing-sending",
        receiving_fluid_id="missing-receiving",
        layup_ids=["missing-layup"],
    )

    errors = solver.validate(project)

    assert any("name" in error for error in errors)
    assert any("does not exist" in error for error in errors)
    assert any("Frequency settings" in error for error in errors)
    assert any("Angle must be" in error for error in errors)


def test_solver_validation_requires_fluid_specs_and_a_layup():
    """Reject non-fluid materials and require at least one selected layup."""
    project = make_project()
    fibre = next(
        material
        for material in project.materials
        if isinstance(material, EquivalentFluidSpec)
    )
    solver = make_solver(project)
    solver.sending_fluid_id = fibre.id
    solver.receiving_fluid_id = fibre.id
    solver.layup_ids = []

    errors = solver.validate(project)

    assert any("must be a FluidSpec" in error for error in errors)
    assert any("Select at least one layup" in error for error in errors)


@pytest.mark.parametrize(
    ("solver_type", "complex_result"),
    [
        (SolverType.ABSORPTION, False),
        (SolverType.ABSORPTION_DIFFUSE, False),
        (SolverType.TRANSMISSION, False),
        (SolverType.TRANSMISSION_DIFFUSE, False),
        (SolverType.TRANSMISSION_ALLARD, False),
        (SolverType.IMPEDANCE, True),
    ],
)
def test_run_performs_real_pyva_calculation(
    solver_type: SolverType,
    complex_result: bool,
) -> None:
    """Run each preset and check shape, finiteness, and plausible values."""
    project = make_project()
    solver = make_solver(project, solver_type)
    layup = project.layups[0]
    materials = {material.id: material for material in project.materials}

    values = solver.run(layup, materials)

    assert values.shape == (solver.frequencies.n_points,)
    assert np.all(np.isfinite(values))
    assert np.iscomplexobj(values) is complex_result
    if not complex_result:
        assert np.all((values >= 0) & (values <= 1))


def test_solver_run_rejects_missing_fluids():
    """Fail clearly when run receives no sending-fluid material."""
    project = make_project()
    solver = make_solver(project)
    solver.sending_fluid_id = "missing-fluid"
    materials = {material.id: material for material in project.materials}

    with pytest.raises(ValueError, match="Sending material"):
        solver.run(project.layups[0], materials)


def test_diffuse_validation_checks_maximum_angle():
    """Validate the diffuse angle rather than the unused single angle."""
    project = make_project()
    solver = make_solver(project, SolverType.ABSORPTION_DIFFUSE)
    solver.angle_deg = 120.0
    solver.max_angle_deg = 90.0

    errors = solver.validate(project)

    assert any("Maximum angle must be" in error for error in errors)
    assert not any(error.startswith("Angle must be") for error in errors)


def test_single_angle_validation_rejects_negative_angle():
    """Reject incidence angles below zero degrees."""
    project = make_project()
    solver = make_solver(project)
    solver.angle_deg = -0.1

    errors = solver.validate(project)

    assert any("Angle must be in [0, 90)" in error for error in errors)
