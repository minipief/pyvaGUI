"""Tests for layup model specifications and pyva conversion."""

import math

import pytest

import pyva.models as pyva_models
import pyva.systems.infiniteLayers as pyva_layers
from pyvagui.model.layup import (
    LayerSpec,
    LayerType,
    Layup,
    PerforationSpec,
)
from pyvagui.model.materials import (
    DelanyBazleySpec,
    EquivalentFluidSpec,
    FluidSpec,
    IsoMatSpec,
    MaterialSpec,
    PoroElasticMatSpec,
)


def make_materials() -> dict[str, MaterialSpec]:
    """Create valid fluid, frame, and poroelastic materials for tests."""
    fluid = FluidSpec(name="Air")
    equivalent_fluid = EquivalentFluidSpec(name="Fibre")
    delany_bazley = DelanyBazleySpec(name="Fibre model")
    frame = IsoMatSpec(name="Frame")
    poroelastic = PoroElasticMatSpec(
        name="Porous layer",
        solid_mat_id=frame.id,
    )
    materials = [
        fluid,
        equivalent_fluid,
        delany_bazley,
        frame,
        poroelastic,
    ]
    return {material.id: material for material in materials}


@pytest.mark.parametrize(
    ("material_type", "expected_types"),
    [
        (FluidSpec, [LayerType.FLUID]),
        (EquivalentFluidSpec, [LayerType.FLUID]),
        (DelanyBazleySpec, [LayerType.FLUID]),
        (PoroElasticMatSpec, [LayerType.POROELASTIC]),
        (
            IsoMatSpec,
            [LayerType.SOLID, LayerType.PLATE, LayerType.MASS],
        ),
    ],
)
def test_allowed_types_match_material_family(
    material_type: type[MaterialSpec],
    expected_types: list[LayerType],
) -> None:
    """Only offer layer representations supported by a material."""
    material = material_type()

    assert LayerSpec.allowed_types(material) == expected_types


def test_perforation_round_trips_and_builds_for_host_thickness():
    """Preserve hole dimensions and pass host thickness to pyva."""
    perforation = PerforationSpec(hole_radius=0.001, distance=0.02)

    restored = PerforationSpec.from_dict(perforation.to_dict())
    pyva_perforation = perforation.to_pyva(thickness=0.005)

    assert restored == perforation
    assert isinstance(pyva_perforation, pyva_layers.PerforatedLayer)
    assert pyva_perforation.thickness == 0.005
    expected_porosity = math.pi * 0.001**2 / 0.02**2
    assert math.isclose(pyva_perforation.porosity, expected_porosity)


@pytest.mark.parametrize(
    ("hole_radius", "distance"),
    [(0.0, 0.02), (-0.001, 0.02), (0.001, 0.0), (0.01, 0.02)],
)
def test_perforation_validation_rejects_invalid_geometry(
    hole_radius: float,
    distance: float,
) -> None:
    """Reject non-positive dimensions and overlapping adjacent holes."""
    perforation = PerforationSpec(
        hole_radius=hole_radius,
        distance=distance,
    )

    assert perforation.validate()


def test_layer_validation_checks_material_type_and_thickness():
    """Report missing materials, incompatible types, and bad thickness."""
    materials = make_materials()
    air = next(
        material
        for material in materials.values()
        if isinstance(material, FluidSpec)
    )
    missing_material = LayerSpec(
        material_id="missing",
        thickness=0.0,
        layer_type=LayerType.PLATE,
    )
    incompatible_layer = LayerSpec(
        material_id=air.id,
        thickness=0.02,
        layer_type=LayerType.MASS,
    )

    missing_errors = missing_material.validate(materials)
    incompatible_errors = incompatible_layer.validate(materials)

    assert any("Thickness" in error for error in missing_errors)
    assert any("does not exist" in error for error in missing_errors)
    assert any("not allowed" in error for error in incompatible_errors)


def test_layer_validation_restricts_perforation_to_plate_and_mass():
    """Reject perforations for fluids and reject invalid hole geometry."""
    materials = make_materials()
    air = next(
        material
        for material in materials.values()
        if isinstance(material, FluidSpec)
    )
    layer = LayerSpec(
        material_id=air.id,
        thickness=0.02,
        layer_type=LayerType.FLUID,
        perforation=PerforationSpec(hole_radius=0.01, distance=0.02),
    )

    errors = layer.validate(materials)

    assert any("only allowed" in error for error in errors)
    assert any("smaller than hole distance" in error for error in errors)


@pytest.mark.parametrize(
    ("layer_type", "material_name", "expected_class"),
    [
        (LayerType.FLUID, "Air", "FluidLayer"),
        (LayerType.POROELASTIC, "Porous layer", "PoroElasticLayer"),
        (LayerType.SOLID, "Frame", "SolidLayer"),
        (LayerType.PLATE, "Frame", "PlateLayer"),
        (LayerType.MASS, "Frame", "MassLayer"),
    ],
)
def test_layer_build_creates_matching_pyva_object(
    layer_type: LayerType,
    material_name: str,
    expected_class: str,
) -> None:
    """Build each supported infinite-layer representation with pyva."""
    materials = make_materials()
    material = next(
        item for item in materials.values() if item.name == material_name
    )
    layer = LayerSpec(
        material_id=material.id,
        thickness=0.01,
        layer_type=layer_type,
    )

    assert type(layer.build(materials)).__name__ == expected_class


def test_plate_and_mass_build_attach_perforation():
    """Pass a pyva perforation with the host layer thickness."""
    materials = make_materials()
    frame = next(
        item for item in materials.values() if isinstance(item, IsoMatSpec)
    )
    perforation = PerforationSpec(hole_radius=0.001, distance=0.02)

    plate = LayerSpec(
        material_id=frame.id,
        thickness=0.005,
        layer_type=LayerType.PLATE,
        perforation=perforation,
    ).build(materials)
    mass = LayerSpec(
        material_id=frame.id,
        thickness=0.005,
        layer_type=LayerType.MASS,
        perforation=perforation,
    ).build(materials)

    assert plate.perforation.thickness == 0.005
    assert mass.perforation.thickness == 0.005


def test_layer_round_trips_enum_value_and_perforation():
    """Serialize enum values as strings and restore optional perforation."""
    layer = LayerSpec(
        material_id="frame-id",
        thickness=0.005,
        layer_type=LayerType.PLATE,
        perforation=PerforationSpec(hole_radius=0.001, distance=0.02),
    )

    serialized = layer.to_dict()

    assert serialized["layer_type"] == "plate"
    assert LayerSpec.from_dict(serialized) == layer


def test_layup_add_remove_move_and_total_thickness():
    """Keep ordering and total thickness consistent after list operations."""
    first = LayerSpec(
        material_id="air",
        thickness=0.01,
        layer_type=LayerType.FLUID,
    )
    second = LayerSpec(
        material_id="frame",
        thickness=0.005,
        layer_type=LayerType.MASS,
    )
    third = LayerSpec(
        material_id="frame",
        thickness=0.002,
        layer_type=LayerType.PLATE,
    )
    layup = Layup(name="Test layup")

    layup.add_layer(first)
    layup.add_layer(second)
    layup.add_layer(third)
    layup.move_layer(2, 0)
    removed = layup.remove_layer(1)

    assert layup.layers == [third, second]
    assert removed is first
    assert layup.total_thickness() == 0.007
    with pytest.raises(IndexError):
        layup.move_layer(0, 2)
    with pytest.raises(IndexError):
        layup.remove_layer(-1)


def test_layup_validation_requires_layers_and_prefixes_layer_errors():
    """Require at least one layer and identify invalid layers by number."""
    materials = make_materials()
    layup = Layup(
        name="Invalid layup",
        layers=[
            LayerSpec(
                material_id="missing",
                thickness=0.0,
                layer_type=LayerType.FLUID,
            )
        ],
    )

    empty_errors = Layup().validate(materials)
    layer_errors = layup.validate(materials)

    assert any("at least one layer" in error for error in empty_errors)
    assert all(error.startswith("Layer 1: ") for error in layer_errors)


def test_layup_round_trip_preserves_identity_and_order():
    """Serialize and restore a layup without changing layer order."""
    layup = Layup(
        name="Round trip",
        layers=[
            LayerSpec(
                material_id="air",
                thickness=0.01,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id="frame",
                thickness=0.005,
                layer_type=LayerType.MASS,
            ),
        ],
    )

    assert Layup.from_dict(layup.to_dict()) == layup


def test_build_tmmodel_keeps_incident_layer_first():
    """Preserve the layup sequence in pyva's transfer-matrix model."""
    materials = make_materials()
    air = next(
        item
        for item in materials.values()
        if isinstance(item, FluidSpec)
    )
    frame = next(
        item for item in materials.values() if isinstance(item, IsoMatSpec)
    )
    layup = Layup(
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.1,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id=frame.id,
                thickness=0.001,
                layer_type=LayerType.MASS,
            ),
        ]
    )

    model = layup.build_tmmodel(materials)

    assert isinstance(model, pyva_models.TMmodel)
    assert isinstance(model.layers[0], pyva_layers.FluidLayer)
    assert isinstance(model.layers[1], pyva_layers.MassLayer)
