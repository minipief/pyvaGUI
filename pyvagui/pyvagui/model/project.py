"""Project model and JSON persistence for pyvaGUI.

Projects own material, layup, and solver specifications. The model has
no GUI dependencies and stores calculation results separately.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from pyvagui.model.layup import Layup
from pyvagui.model.materials import (
    IsoMatSpec,
    MaterialSpec,
    PoroElasticMatSpec,
    material_from_dict,
)
from pyvagui.model.solvers import SolverSpec


@dataclass(kw_only=True)
class Project:
    """Materials, layups, and solvers belonging to one project.

    Parameters
    ----------
    name : str, optional
        Project name shown in the user interface.
    file_path : pathlib.Path or None, optional
        Path of the saved project file.
    materials : list of MaterialSpec, optional
        Materials available to the project's layups and solvers.
    layups : list of Layup, optional
        Ordered layer stacks in this project.
    solvers : list of SolverSpec, optional
        Calculation configurations in this project.
    is_modified : bool, optional
        Whether a project change has not yet been saved.
    """

    name: str = "Untitled project"
    file_path: Path | None = None
    materials: list[MaterialSpec] = field(default_factory=list)
    layups: list[Layup] = field(default_factory=list)
    solvers: list[SolverSpec] = field(default_factory=list)
    is_modified: bool = False

    def materials_by_id(self) -> dict[str, MaterialSpec]:
        """Return project materials indexed by their identifiers.

        Returns
        -------
        dict of str to MaterialSpec
            Material lookup used by layups, solvers, and pyva conversion.
        """
        return {material.id: material for material in self.materials}

    def add_material(self, material: MaterialSpec) -> None:
        """Add a material and mark the project modified.

        Parameters
        ----------
        material : MaterialSpec
            Material to add.

        Raises
        ------
        ValueError
            If another project material already has this identifier.
        """
        if self.find_material_by_id(material.id) is not None:
            raise ValueError(f"Material id already exists: {material.id}")
        self.materials.append(material)
        self.is_modified = True

    def remove_material(self, material_id: str) -> MaterialSpec:
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
            If no project material has this identifier.
        """
        material = self.find_material_by_id(material_id)
        if material is None:
            raise KeyError(f"Material does not exist: {material_id}")
        self.materials.remove(material)
        self.is_modified = True
        return material

    def find_material_by_id(self, material_id: str) -> MaterialSpec | None:
        """Find a project material by identifier.

        Parameters
        ----------
        material_id : str
            Identifier to look up.

        Returns
        -------
        MaterialSpec or None
            Matching material, or None if it does not exist.
        """
        for material in self.materials:
            if material.id == material_id:
                return material
        return None

    def add_layup(self, layup: Layup) -> None:
        """Add a layup and mark the project modified.

        Parameters
        ----------
        layup : Layup
            Layup to add.

        Raises
        ------
        ValueError
            If another project layup already has this identifier.
        """
        if self.find_layup_by_id(layup.id) is not None:
            raise ValueError(f"Layup id already exists: {layup.id}")
        self.layups.append(layup)
        self.is_modified = True

    def remove_layup(self, layup_id: str) -> Layup:
        """Remove and return a layup by identifier.

        Parameters
        ----------
        layup_id : str
            Identifier of the layup to remove.

        Returns
        -------
        Layup
            Removed layup.

        Raises
        ------
        KeyError
            If no project layup has this identifier.
        """
        layup = self.find_layup_by_id(layup_id)
        if layup is None:
            raise KeyError(f"Layup does not exist: {layup_id}")
        self.layups.remove(layup)
        self.is_modified = True
        return layup

    def find_layup_by_id(self, layup_id: str) -> Layup | None:
        """Find a project layup by identifier.

        Parameters
        ----------
        layup_id : str
            Identifier to look up.

        Returns
        -------
        Layup or None
            Matching layup, or None if it does not exist.
        """
        for layup in self.layups:
            if layup.id == layup_id:
                return layup
        return None

    def add_solver(self, solver: SolverSpec) -> None:
        """Add a solver and mark the project modified.

        Parameters
        ----------
        solver : SolverSpec
            Solver configuration to add.

        Raises
        ------
        ValueError
            If another project solver already has this identifier.
        """
        if self.find_solver_by_id(solver.id) is not None:
            raise ValueError(f"Solver id already exists: {solver.id}")
        self.solvers.append(solver)
        self.is_modified = True

    def remove_solver(self, solver_id: str) -> SolverSpec:
        """Remove and return a solver by identifier.

        Parameters
        ----------
        solver_id : str
            Identifier of the solver to remove.

        Returns
        -------
        SolverSpec
            Removed solver.

        Raises
        ------
        KeyError
            If no project solver has this identifier.
        """
        solver = self.find_solver_by_id(solver_id)
        if solver is None:
            raise KeyError(f"Solver does not exist: {solver_id}")
        self.solvers.remove(solver)
        self.is_modified = True
        return solver

    def find_solver_by_id(self, solver_id: str) -> SolverSpec | None:
        """Find a project solver by identifier.

        Parameters
        ----------
        solver_id : str
            Identifier to look up.

        Returns
        -------
        SolverSpec or None
            Matching solver, or None if it does not exist.
        """
        for solver in self.solvers:
            if solver.id == solver_id:
                return solver
        return None

    def copy_from_library(self, material: MaterialSpec) -> MaterialSpec:
        """Create a new-id copy of a material from the library.

        The returned copy is not added automatically, so callers can ask
        about a missing poroelastic frame before adding either material.

        Parameters
        ----------
        material : MaterialSpec
            Library material to copy.

        Returns
        -------
        MaterialSpec
            Independent copy with a new identifier.
        """
        return material.copy_with_new_id()

    def missing_frame_material_id(
        self, material: MaterialSpec
    ) -> str | None:
        """Return a missing frame id for a poroelastic library material.

        Parameters
        ----------
        material : MaterialSpec
            Material whose referenced frame should be checked.

        Returns
        -------
        str or None
            Referenced frame id if it is absent from the project, else None.
        """
        if not isinstance(material, PoroElasticMatSpec):
            return None
        if not material.solid_mat_id:
            return None
        if self.find_material_by_id(material.solid_mat_id) is None:
            return material.solid_mat_id
        return None

    def material_users(self, material_id: str) -> list[str]:
        """List layups, materials, and solvers that use a material.

        Parameters
        ----------
        material_id : str
            Material identifier to search for.

        Returns
        -------
        list of str
            Names of dependent poroelastic materials, layups, and solvers.
        """
        users = []
        for material in self.materials:
            if (
                isinstance(material, PoroElasticMatSpec)
                and material.solid_mat_id == material_id
            ):
                users.append(material.name)
        for layup in self.layups:
            if any(
                layer.material_id == material_id for layer in layup.layers
            ):
                users.append(layup.name)
        for solver in self.solvers:
            if material_id in (
                solver.sending_fluid_id,
                solver.receiving_fluid_id,
            ):
                users.append(solver.name)
        return users

    def validate(self) -> list[str]:
        """Validate materials, references, layups, and solvers.

        Returns
        -------
        list of str
            All validation errors found in the project.
        """
        errors = []
        materials = self.materials_by_id()
        if len(materials) != len(self.materials):
            errors.append("Project contains duplicate material identifiers.")

        for material in self.materials:
            errors.extend(material.validate())
            if isinstance(material, PoroElasticMatSpec):
                frame = materials.get(material.solid_mat_id)
                if not isinstance(frame, IsoMatSpec):
                    errors.append(
                        f"{material.name}: frame material must reference "
                        "an existing Isomat."
                    )

        for layup in self.layups:
            errors.extend(
                f"Layup '{layup.name}': {error}"
                for error in layup.validate(materials)
            )

        for solver in self.solvers:
            errors.extend(
                f"Solver '{solver.name}': {error}"
                for error in solver.validate(self)
            )
        return errors

    def to_dict(self) -> dict:
        """Convert project configuration to JSON-ready values.

        Returns
        -------
        dict
            Versioned project data; transient results are not included.
        """
        return {
            "format_version": 1,
            "name": self.name,
            "materials": [material.to_dict() for material in self.materials],
            "layups": [layup.to_dict() for layup in self.layups],
            "solvers": [solver.to_dict() for solver in self.solvers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create a project from versioned JSON-ready values.

        Parameters
        ----------
        data : dict
            Project dictionary created by :meth:`to_dict`.

        Returns
        -------
        Project
            Restored project, initially marked unmodified.

        Raises
        ------
        ValueError
            If the project format version is unsupported.
        """
        if data.get("format_version") != 1:
            raise ValueError(
                f"Unsupported project format version: "
                f"{data.get('format_version')}"
            )
        from pyvagui.model.solvers import SolverSpec

        return cls(
            name=data["name"],
            materials=[material_from_dict(item) for item in data["materials"]],
            layups=[Layup.from_dict(item) for item in data["layups"]],
            solvers=[SolverSpec.from_dict(item) for item in data["solvers"]],
        )

    def save(self, path: str | Path) -> None:
        """Write project configuration as indented JSON.

        Parameters
        ----------
        path : str or pathlib.Path
            Destination project file.
        """
        target = Path(path)
        with target.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2)
            file.write("\n")
        self.file_path = target
        self.is_modified = False

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        """Read and restore a project from a JSON file.

        Parameters
        ----------
        path : str or pathlib.Path
            Project file to read.

        Returns
        -------
        Project
            Loaded project with its file path set and modified flag cleared.
        """
        source = Path(path)
        with source.open("r", encoding="utf-8") as file:
            data = json.load(file)
        project = cls.from_dict(data)
        project.file_path = source
        project.is_modified = False
        return project
