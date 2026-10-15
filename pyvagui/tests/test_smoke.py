from math import isclose

import pyvagui.__main__ as app_entry
from pyvagui.model.materials import (
    EquivalentFluidSpec,
    FluidPropertiesSpec,
    FluidSpec,
    IsoMatSpec,
    PoroElasticMatSpec,
    material_from_dict,
)


def test_entrypoint_opens_pyvagui_argument(monkeypatch, tmp_path):
    """Pass a double-clicked project path into the main window loader."""
    project_path = tmp_path / "double-click.pyvagui"
    loaded_paths = []

    class FakeApplication:
        def __init__(self, arguments):
            self.arguments = arguments

        def exec(self):
            return 0

    class FakeWindow:
        def __init__(self):
            pass

        def _load_project(self, path):
            loaded_paths.append(path)

        def show(self):
            pass

    monkeypatch.setattr(app_entry, "QApplication", FakeApplication)
    monkeypatch.setattr(app_entry, "MainWindow", FakeWindow)
    monkeypatch.setattr(app_entry, "apply_theme", lambda application: None)

    assert app_entry.main([str(project_path)]) == 0
    assert loaded_paths == [project_path]


def test_entrypoint_dispatches_worker_without_creating_gui(monkeypatch):
    """Run the packaged worker mode before constructing QApplication."""
    calls = []
    monkeypatch.setattr(
        "pyvagui.services.calculation_process.main",
        lambda payload, messages: calls.append((payload, messages)) or 0,
    )
    monkeypatch.setattr(
        app_entry,
        "QApplication",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("Worker mode must not create a GUI")
        ),
    )

    status = app_entry.main([
        "--calculation-worker",
        "payload.json",
        "messages.jsonl",
    ])

    assert status == 0
    assert calls == [("payload.json", "messages.jsonl")]


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
