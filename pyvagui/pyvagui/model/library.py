"""Persistent material library and material-file import/export.

The library stores plain material specifications as JSON. It is kept
separate from project files so materials can be reused between projects.
"""

import json
import os
from pathlib import Path

from pyvagui.model.materials import (
    MaterialSpec,
    PoroElasticMatSpec,
    material_from_dict,
)


class MaterialLibrary:
    """Manage reusable material specifications stored in a JSON file.

    Parameters
    ----------
    path : pathlib.Path or str
        User library file path. Tests should use a temporary path.
    """

    def __init__(self, path: str | Path):
        """Create an empty library associated with a file path.

        Parameters
        ----------
        path : pathlib.Path or str
            User library file path.
        """
        self.path = Path(path)
        self.materials: list[MaterialSpec] = []

    @staticmethod
    def default_path() -> Path:
        """Return the platform-specific user library path.

        Returns
        -------
        pathlib.Path
            `%APPDATA%/pyvaGUI/library.json` on Windows, or
            `~/.pyvagui/library.json` elsewhere.
        """
        if os.name == "nt":
            app_data = os.environ.get("APPDATA")
            if app_data is None:
                app_data = str(Path.home() / "AppData" / "Roaming")
            return Path(app_data) / "pyvaGUI" / "library.json"
        return Path.home() / ".pyvagui" / "library.json"

    def load(self) -> list[MaterialSpec]:
        """Load the library, creating it from bundled defaults if needed.

        Returns
        -------
        list of MaterialSpec
            Loaded materials.
        """
        source = self.path
        create_from_defaults = not source.exists()
        if create_from_defaults:
            source = (
                Path(__file__).resolve().parent.parent
                / "resources"
                / "default_library.json"
            )

        with source.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if data.get("format_version") != 1:
            raise ValueError("Unsupported material library format version.")
        self.materials = _material_specs_from_data(data["materials"])
        if create_from_defaults:
            self.save()
        return list(self.materials)

    def save(self) -> None:
        """Write all library materials as indented JSON."""
        self._write_material_file(self.path, self.materials)

    def add(self, material: MaterialSpec) -> None:
        """Add a material to the in-memory library.

        Parameters
        ----------
        material : MaterialSpec
            Material to add.

        Raises
        ------
        ValueError
            If this library already contains the material identifier.
        """
        if any(item.id == material.id for item in self.materials):
            raise ValueError(f"Material id already exists: {material.id}")
        self.materials.append(material)

    def remove(self, material_id: str) -> MaterialSpec:
        """Remove and return a material by identifier.

        Parameters
        ----------
        material_id : str
            Identifier of the material to remove.

        Returns
        -------
        MaterialSpec
            Removed material.

        Raises
        ------
        KeyError
            If the identifier is not in the library.
        """
        for material in self.materials:
            if material.id == material_id:
                self.materials.remove(material)
                return material
        raise KeyError(f"Material does not exist: {material_id}")

    def export_materials(
        self, ids: list[str], path: str | Path
    ) -> None:
        """Export selected materials to a versioned JSON file.

        Parameters
        ----------
        ids : list of str
            Identifiers of the materials to export.
        path : str or pathlib.Path
            Destination file.

        Raises
        ------
        KeyError
            If any requested identifier is not in the library.
        """
        selected = []
        for material_id in ids:
            material = next(
                (item for item in self.materials if item.id == material_id),
                None,
            )
            if material is None:
                raise KeyError(f"Material does not exist: {material_id}")
            selected.append(material)
        self._write_material_file(Path(path), selected)

    def import_materials(self, path: str | Path) -> list[MaterialSpec]:
        """Read materials and assign new ids without changing this library.

        Frame references are remapped when the corresponding frame material
        is included in the imported file. Missing frames keep their source id
        so a project can ask whether to import the dependency as well.

        Parameters
        ----------
        path : str or pathlib.Path
            JSON file created by :meth:`export_materials`.

        Returns
        -------
        list of MaterialSpec
            Imported materials with new identifiers.
        """
        source = Path(path)
        with source.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if data.get("format_version") != 1:
            raise ValueError("Unsupported material library format version.")

        original_materials = _material_specs_from_data(data["materials"])
        imported_materials = [
            material.copy_with_new_id() for material in original_materials
        ]
        new_ids = {
            original.id: imported.id
            for original, imported in zip(
                original_materials,
                imported_materials,
            )
        }
        for original, imported in zip(
            original_materials,
            imported_materials,
        ):
            if isinstance(original, PoroElasticMatSpec):
                frame_id = new_ids.get(original.solid_mat_id)
                if frame_id is not None:
                    imported.solid_mat_id = frame_id
        return imported_materials

    @staticmethod
    def _write_material_file(
        path: Path, materials: list[MaterialSpec]
    ) -> None:
        """Write material specifications in the library file format.

        Parameters
        ----------
        path : pathlib.Path
            Destination JSON file.
        materials : list of MaterialSpec
            Materials to serialize.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "format_version": 1,
            "materials": [material.to_dict() for material in materials],
        }
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.write("\n")


def _material_specs_from_data(
    material_data: list[dict],
) -> list[MaterialSpec]:
    """Restore current specs and migrate known legacy library fields.

    Parameters
    ----------
    material_data : list of dict
        Serialized material objects from a version-1 library file.

    Returns
    -------
    list of MaterialSpec
        Restored materials using the current material schema.

    Raises
    ------
    ValueError
        If a legacy fluid reference cannot be resolved.
    """
    records_by_id = {
        item["id"]: item
        for item in material_data
        if "id" in item
    }
    materials = []
    for item in material_data:
        normalized = dict(item)
        material_type = normalized.get("type")
        if material_type == "poro_elastic":
            normalized["type"] = "poroelastic"
        if "frame_material_id" in normalized:
            normalized.setdefault(
                "solid_mat_id",
                normalized["frame_material_id"],
            )
            normalized.pop("frame_material_id")

        fluid_id = normalized.pop("fluid_material_id", None)
        if fluid_id is not None:
            fluid_data = records_by_id.get(fluid_id)
            if fluid_data is None or fluid_data.get("type") != "fluid":
                raise ValueError(
                    f"Material '{normalized.get('name', 'Unknown')}': "
                    f"legacy fluid reference '{fluid_id}' cannot be resolved."
                )
            common_fields = [
                "c0",
                "rho0",
                "dynamic_viscosity",
                "kappa",
                "Cp",
                "heat_conductivity",
            ]
            if normalized.get("type") in (
                "fluid",
                "equivalent_fluid",
                "delany_bazley",
            ):
                common_fields.append("eta")
            for field_name in common_fields:
                if field_name not in normalized and field_name in fluid_data:
                    normalized[field_name] = fluid_data[field_name]

        materials.append(material_from_dict(normalized))
    return materials
