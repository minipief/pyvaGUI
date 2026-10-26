"""Tests for material library persistence and file exchange."""

import json

import pytest

from pyvagui.model.library import MaterialLibrary
from pyvagui.model.materials import (
    EquivalentFluidSpec,
    FluidSpec,
    IsoMatSpec,
    PoroElasticMatSpec,
)


def test_default_path_uses_appdata_on_windows(tmp_path, monkeypatch):
    """Place the Windows library under the configured application data."""
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert MaterialLibrary.default_path() == (
        tmp_path / "pyvaGUI" / "library.json"
    )


def test_load_creates_default_library_in_temporary_location(tmp_path):
    """Create the user library from bundled materials when absent."""
    library_path = tmp_path / "user" / "library.json"
    library = MaterialLibrary(library_path)

    materials = library.load()

    assert library_path.exists()
    assert [material.name for material in materials] == [
        "Air",
        "Aluminium",
        "Steel",
        "Glass wool",
        "Delany-Bazley fibre",
    ]
    assert isinstance(materials[0], FluidSpec)
    assert isinstance(materials[3], EquivalentFluidSpec)
    assert json.loads(library_path.read_text(encoding="utf-8"))[
        "format_version"
    ] == 1


def test_load_migrates_legacy_fluid_and_frame_fields(tmp_path):
    """Resolve old fluid references and poroelastic frame field names."""
    path = tmp_path / "legacy-library.json"
    legacy_data = {
        "format_version": 1,
        "materials": [
            {
                "type": "fluid",
                "id": "legacy-air",
                "name": "Air",
                "c0": 340.0,
                "rho0": 1.2,
                "eta": 0.0,
                "dynamic_viscosity": 1.8e-5,
                "kappa": 1.4,
                "Cp": 1005.1,
                "heat_conductivity": 0.025,
            },
            {
                "type": "equivalent_fluid",
                "id": "legacy-wool",
                "name": "Mineral wool",
                "flow_res": 25000.0,
                "porosity": 0.98,
                "tortuosity": 1.02,
                "rho_bulk": 31.2,
                "length_visc": 9e-5,
                "length_therm": 1.8e-4,
                "limp": True,
                "fluid_material_id": "legacy-air",
            },
            {
                "type": "isomat",
                "id": "legacy-frame",
                "name": "Foam frame",
                "E": 300000.0,
                "rho0": 12.0,
                "nu": 0.2,
                "eta": 0.06,
            },
            {
                "type": "poro_elastic",
                "id": "legacy-foam",
                "name": "Foam",
                "frame_material_id": "legacy-frame",
                "fluid_material_id": "legacy-air",
                "flow_res": 6600.0,
                "porosity": 0.98,
                "tortuosity": 1.03,
                "length_visc": 2e-4,
                "length_therm": 3.8e-4,
                "limp": False,
            },
        ],
    }
    path.write_text(json.dumps(legacy_data), encoding="utf-8")
    library = MaterialLibrary(path)

    materials = library.load()

    wool = next(
        material
        for material in materials
        if isinstance(material, EquivalentFluidSpec)
    )
    foam = next(
        material
        for material in materials
        if isinstance(material, PoroElasticMatSpec)
    )
    assert wool.c0 == 340.0
    assert wool.rho0 == 1.2
    assert wool.eta == 0.0
    assert foam.type_name == "poroelastic"
    assert foam.solid_mat_id == "legacy-frame"
    assert foam.c0 == 340.0
    assert foam.rho0 == 1.2
    assert not hasattr(foam, "eta")
    assert json.loads(path.read_text(encoding="utf-8")) == legacy_data


def test_library_add_save_load_and_remove(tmp_path):
    """Persist added materials and remove them by identifier."""
    path = tmp_path / "library.json"
    library = MaterialLibrary(path)
    material = FluidSpec(name="Water")

    library.add(material)
    library.save()
    restored = MaterialLibrary(path)
    loaded = restored.load()

    assert loaded == [material]
    assert restored.remove(material.id) == material
    with pytest.raises(KeyError):
        restored.remove(material.id)


def test_library_rejects_duplicate_ids(tmp_path):
    """Prevent duplicate material identifiers in the library."""
    library = MaterialLibrary(tmp_path / "library.json")
    material = FluidSpec(name="Air")
    library.add(material)

    with pytest.raises(ValueError, match="Material id"):
        library.add(material)


def test_library_update_preserves_identifier_and_order(tmp_path):
    """Replace an existing entry without moving or re-identifying it."""
    first = FluidSpec(name="Air")
    second = IsoMatSpec(name="Aluminium")
    updated = FluidSpec(name="Water", id=first.id)
    library = MaterialLibrary(tmp_path / "library.json")
    library.materials = [first, second]

    previous = library.update(updated)

    assert previous is first
    assert library.materials == [updated, second]
    with pytest.raises(KeyError, match="Material does not exist"):
        library.update(FluidSpec(name="Missing"))


def test_export_selected_materials_and_import_with_new_ids(tmp_path):
    """Export selected materials and assign fresh ids on import."""
    path = tmp_path / "library.json"
    export_path = tmp_path / "exchange.json"
    frame = IsoMatSpec(name="Frame")
    poroelastic = PoroElasticMatSpec(
        name="Porous material",
        solid_mat_id=frame.id,
    )
    library = MaterialLibrary(path)
    library.add(frame)
    library.add(poroelastic)
    library.export_materials([frame.id, poroelastic.id], export_path)

    imported = library.import_materials(export_path)
    imported_frame = next(
        material for material in imported if isinstance(material, IsoMatSpec)
    )
    imported_poroelastic = next(
        material
        for material in imported
        if isinstance(material, PoroElasticMatSpec)
    )

    assert len(imported) == 2
    assert all(
        imported_material.id != original.id
        for imported_material, original in zip(imported, [frame, poroelastic])
    )
    assert imported_poroelastic.solid_mat_id == imported_frame.id
    assert library.materials == [frame, poroelastic]


def test_import_keeps_id_for_frame_not_in_export(tmp_path):
    """Leave an omitted frame reference available for a project prompt."""
    frame = IsoMatSpec(name="External frame")
    poroelastic = PoroElasticMatSpec(
        name="Porous material",
        solid_mat_id=frame.id,
    )
    path = tmp_path / "partial.json"
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "materials": [poroelastic.to_dict()],
            }
        ),
        encoding="utf-8",
    )
    library = MaterialLibrary(tmp_path / "library.json")

    imported = library.import_materials(path)

    assert len(imported) == 1
    assert imported[0].id != poroelastic.id
    assert imported[0].solid_mat_id == frame.id


def test_export_rejects_unknown_material_id(tmp_path):
    """Require every requested export id to exist in the library."""
    library = MaterialLibrary(tmp_path / "library.json")

    with pytest.raises(KeyError, match="unknown"):
        library.export_materials(["unknown"], tmp_path / "out.json")
