from math import isclose

from pyvagui.model.materials import (
    EquivalentFluidSpec,
    FluidPropertiesSpec,
    FluidSpec,
    IsoMatSpec,
    PoroElasticMatSpec,
    material_from_dict,
)


def test_fluid_specs_share_common_properties():
    frame = IsoMatSpec()
    specs = [
        FluidSpec(),
        EquivalentFluidSpec(
            flow_res=10000,
            porosity=0.9,
            tortuosity=1.2,
            rho_bulk=40,
            length_visc=100e-6,
            length_therm=200e-6,
        ),
        PoroElasticMatSpec(
            solid_mat_id=frame.id,
            flow_res=10000,
            porosity=0.9,
            tortuosity=1.2,
            length_visc=100e-6,
            length_therm=200e-6,
        ),
    ]

    assert all(isinstance(spec, FluidPropertiesSpec) for spec in specs)
    assert all(spec.validate() == [] for spec in specs)

    serialized_equivalent = specs[1].to_dict()
    assert isinstance(
        material_from_dict(serialized_equivalent), EquivalentFluidSpec
    )


def test_poroelastic_spec_round_trips_frame_id():
    frame = IsoMatSpec(name="Frame")
    spec = PoroElasticMatSpec(
        solid_mat_id=frame.id,
        flow_res=10000,
        porosity=0.9,
        tortuosity=1.2,
        length_visc=100e-6,
        length_therm=200e-6,
    )

    restored = material_from_dict(spec.to_dict())

    assert restored == spec
    assert restored.solid_mat_id == frame.id


def test_material_specs_convert_to_pyva():
    frame = IsoMatSpec()
    specs = [
        FluidSpec(),
        EquivalentFluidSpec(
            flow_res=10000,
            porosity=0.9,
            tortuosity=1.2,
            rho_bulk=40,
            length_visc=100e-6,
            length_therm=200e-6,
        ),
        IsoMatSpec(),
        PoroElasticMatSpec(
            solid_mat_id=frame.id,
            flow_res=10000,
            porosity=0.9,
            tortuosity=1.2,
            length_visc=100e-6,
            length_therm=200e-6,
        ),
    ]
    materials = {spec.id: spec for spec in specs}
    materials[frame.id] = frame

    converted = [spec.to_pyva(materials) for spec in specs]

    assert isclose(converted[0].Cp, 1005.1)
    assert isclose(converted[3].Cp, 1005.1)
    assert [type(material).__name__ for material in converted] == [
        "Fluid",
        "EquivalentFluid",
        "IsoMat",
        "PoroElasticMat",
    ]
