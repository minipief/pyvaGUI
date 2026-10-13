"""Frequency settings and pyva calculation specifications.

Solver specifications keep user settings independent from the GUI and
convert them into pyva calls only when a calculation is requested.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from pyvagui.model.layup import Layup
from pyvagui.model.materials import FluidSpec, MaterialSpec, new_id


@dataclass(kw_only=True)
class FrequencySettings:
    """Start, end, and count for logarithmically spaced frequencies.

    Parameters
    ----------
    f_start : float
        First frequency [Hz], greater than zero.
    f_end : float
        Last frequency [Hz], greater than ``f_start``.
    n_points : int
        Number of frequencies, at least two.
    """

    f_start: float
    f_end: float
    n_points: int

    def frequencies(self) -> np.ndarray:
        """Return logarithmically spaced frequencies [Hz].

        Returns
        -------
        numpy.ndarray
            One-dimensional array from ``f_start`` through ``f_end``.

        Raises
        ------
        ValueError
            If the frequency settings are invalid.
        """
        errors = self.validate()
        if errors:
            raise ValueError("Invalid frequency settings: " + " ".join(errors))
        return np.geomspace(self.f_start, self.f_end, self.n_points)

    def omega(self) -> np.ndarray:
        """Return angular frequencies $\\omega = 2\\pi f$ [rad/s].

        Returns
        -------
        numpy.ndarray
            Angular frequency for every configured frequency.
        """
        return 2 * np.pi * self.frequencies()

    def labels(self) -> list[str]:
        """Return readable labels matching the generated frequencies.

        Returns
        -------
        list of str
            Frequency values formatted for display in hertz.
        """
        return [f"{frequency:g}" for frequency in self.frequencies()]

    def validate(self) -> list[str]:
        """Check the frequency range and point count.

        Returns
        -------
        list of str
            Validation errors, or an empty list if the settings are valid.
        """
        errors = []
        if not math.isfinite(self.f_start) or self.f_start <= 0:
            errors.append("Start frequency must be finite and > 0 Hz.")
        if not math.isfinite(self.f_end) or self.f_end <= self.f_start:
            errors.append(
                "End frequency must be finite and > start frequency."
            )
        if (
            not isinstance(self.n_points, int)
            or isinstance(self.n_points, bool)
            or self.n_points < 2
        ):
            errors.append("Number of points must be an integer >= 2.")
        return errors

    def to_dict(self) -> dict[str, float | int]:
        """Convert the settings to JSON-ready values.

        Returns
        -------
        dict of str to float or int
            Start, end, and number of frequency points.
        """
        return {
            "f_start": self.f_start,
            "f_end": self.f_end,
            "n_points": self.n_points,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float | int]) -> "FrequencySettings":
        """Create frequency settings from serialized values.

        Parameters
        ----------
        data : dict of str to float or int
            Dictionary created by :meth:`to_dict`.

        Returns
        -------
        FrequencySettings
            Restored frequency settings.
        """
        return cls(
            f_start=data["f_start"],
            f_end=data["f_end"],
            n_points=data["n_points"],
        )


class BoundaryCondition(Enum):
    """Termination used at the receiving side of a model."""

    FIXED = "fixed"
    EQUIVALENT_FLUID = "equivalent_fluid"


class SolverType(Enum):
    """Available pyva calculation methods and their display names."""

    ABSORPTION = "absorption"
    ABSORPTION_DIFFUSE = "absorption_diffuse"
    TRANSMISSION = "transmission"
    TRANSMISSION_DIFFUSE = "transmission_diffuse"
    TRANSMISSION_ALLARD = "transmission_allard"
    IMPEDANCE = "impedance"

    @property
    def display_name(self) -> str:
        """Return the English name shown for this solver preset.

        Returns
        -------
        str
            Preset name for the user interface.
        """
        match self:
            case SolverType.ABSORPTION:
                return "Absorption"
            case SolverType.ABSORPTION_DIFFUSE:
                return "Absorption diffuse"
            case SolverType.TRANSMISSION:
                return "Transmission"
            case SolverType.TRANSMISSION_DIFFUSE:
                return "Transmission diffuse"
            case SolverType.TRANSMISSION_ALLARD:
                return "Transmission (Allard)"
            case SolverType.IMPEDANCE:
                return "Impedance"

    def uses_diffuse_angle(self) -> bool:
        """Return whether this solver integrates over incidence angles.

        Returns
        -------
        bool
            True for diffuse absorption and transmission.
        """
        return self in (
            SolverType.ABSORPTION_DIFFUSE,
            SolverType.TRANSMISSION_DIFFUSE,
        )

    def uses_single_angle(self) -> bool:
        """Return whether this solver uses one incidence angle.

        Returns
        -------
        bool
            True for absorption, transmission, Allard transmission,
            and impedance.
        """
        return not self.uses_diffuse_angle()

    def is_complex(self) -> bool:
        """Return whether the solver produces complex-valued results.

        Returns
        -------
        bool
            True only for surface impedance.
        """
        return self is SolverType.IMPEDANCE


@dataclass(kw_only=True)
class SolverSpec:
    """Configuration for one calculation preset.

    Parameters
    ----------
    id : str
        Unique solver identifier, created automatically.
    name : str
        Name shown in the user interface.
    solver_type : SolverType
        Calculation method to run.
    frequencies : FrequencySettings
        Frequency range and number of samples.
    angle_deg : float, optional
        Single incidence angle [degrees].
    max_angle_deg : float, optional
        Maximum diffuse incidence angle [degrees].
    boundary_condition : BoundaryCondition, optional
        Receiving-side termination for applicable methods.
    sending_fluid_id : str, optional
        Project identifier of the incident fluid.
    receiving_fluid_id : str, optional
        Project identifier of the receiving fluid.
    layup_ids : list of str, optional
        Project identifiers of the layups to calculate.
    """

    id: str = field(default_factory=new_id)
    name: str = "New solver"
    solver_type: SolverType
    frequencies: FrequencySettings
    angle_deg: float = 0.0
    max_angle_deg: float = 78.0
    boundary_condition: BoundaryCondition = BoundaryCondition.FIXED
    sending_fluid_id: str = ""
    receiving_fluid_id: str = ""
    layup_ids: list[str] = field(default_factory=list)

    def uses_diffuse_angle(self) -> bool:
        """Return whether this solver uses ``max_angle_deg``.

        Returns
        -------
        bool
            True for diffuse solver presets.
        """
        return self.solver_type.uses_diffuse_angle()

    def uses_single_angle(self) -> bool:
        """Return whether this solver uses ``angle_deg``.

        Returns
        -------
        bool
            True for single-angle solver presets.
        """
        return self.solver_type.uses_single_angle()

    def is_complex(self) -> bool:
        """Return whether this solver produces complex-valued results.

        Returns
        -------
        bool
            True only for impedance.
        """
        return self.solver_type.is_complex()

    def run(
        self,
        layup: Layup,
        materials: dict[str, MaterialSpec],
    ) -> np.ndarray:
        """Run the selected pyva calculation for one layup.

        Parameters
        ----------
        layup : Layup
            Layup to calculate.
        materials : dict of str to MaterialSpec
            Project materials, keyed by their identifiers.

        Returns
        -------
        numpy.ndarray
            One result value per configured frequency. Impedance values
            are complex.

        Notes
        -----
        For single-angle calculations, the in-plane wavenumber is
        ``kx = k * sin(theta)`` using the sending fluid's wavenumber.
        Diffuse methods receive their maximum angle in radians.

        Raises
        ------
        ValueError
            If the settings, selected fluids, or layup are invalid.
        """
        frequency_errors = self.frequencies.validate()
        if frequency_errors:
            raise ValueError(
                "Invalid frequency settings: " + " ".join(frequency_errors)
            )

        angle = self._angle_radians()
        sending_spec = materials.get(self.sending_fluid_id)
        receiving_spec = materials.get(self.receiving_fluid_id)
        if not isinstance(sending_spec, FluidSpec):
            raise ValueError("Sending material must be a project FluidSpec.")
        if not isinstance(receiving_spec, FluidSpec):
            raise ValueError("Receiving material must be a project FluidSpec.")

        sending_fluid = sending_spec.to_pyva(materials)
        receiving_fluid = receiving_spec.to_pyva(materials)
        omega = self.frequencies.omega()
        model = layup.build_tmmodel(materials)
        kx = sending_fluid.wavenumber(omega) * math.sin(angle)

        match self.solver_type:
            case SolverType.ABSORPTION:
                # Calculate angle-dependent surface absorption in pyva.
                values = model.absorption(
                    omega,
                    kx,
                    in_fluid=sending_fluid,
                    boundary_condition=self.boundary_condition.value,
                    signal=False,
                    out_fluid=receiving_fluid,
                )
            case SolverType.ABSORPTION_DIFFUSE:
                # Integrate surface absorption over the diffuse angle range.
                values = model.absorption_diffuse(
                    omega,
                    theta_max=math.radians(self.max_angle_deg),
                    in_fluid=sending_fluid,
                    boundary_condition=self.boundary_condition.value,
                    signal=False,
                    out_fluid=receiving_fluid,
                )
            case SolverType.TRANSMISSION:
                # Calculate the angle-dependent transmission coefficient.
                values = model.transmission_coefficient(
                    omega,
                    kx,
                    fluids=(sending_fluid, receiving_fluid),
                    signal=False,
                )
            case SolverType.TRANSMISSION_DIFFUSE:
                # Integrate transmission over the diffuse angle range.
                values = model.transmission_diffuse(
                    omega,
                    theta_max=math.radians(self.max_angle_deg),
                    fluids=(sending_fluid, receiving_fluid),
                    signal=False,
                )
            case SolverType.TRANSMISSION_ALLARD:
                # Calculate transmission with pyva's Allard method.
                values = model.transmission_allard(
                    omega,
                    kx,
                    fluids=(sending_fluid, receiving_fluid),
                    signal=False,
                )
            case SolverType.IMPEDANCE:
                # Calculate the surface impedance for the selected boundary.
                values = model.impedance(
                    omega,
                    kx,
                    boundary_condition=self.boundary_condition.value,
                    signal=False,
                    out_fluid=receiving_fluid,
                )
            case _:
                message = f"Unsupported solver type: {self.solver_type!r}."
                raise ValueError(message)

        return np.asarray(values).reshape(-1)

    def validate(self, project: Any) -> list[str]:
        """Check solver fields and references against a project.

        Parameters
        ----------
        project : Project
            Project containing the materials and layups referenced here.

        Returns
        -------
        list of str
            Validation errors, or an empty list if the solver is valid.
        """
        errors = []
        if not self.name.strip():
            errors.append("Solver name must not be empty.")
        if not isinstance(self.solver_type, SolverType):
            errors.append("Solver type is invalid.")
        if not isinstance(self.boundary_condition, BoundaryCondition):
            errors.append("Boundary condition is invalid.")

        if not self.layup_ids:
            errors.append("Select at least one layup.")
        layup_ids = {layup.id for layup in project.layups}
        for layup_id in self.layup_ids:
            if layup_id not in layup_ids:
                errors.append(f"Selected layup '{layup_id}' does not exist.")

        materials = project.materials_by_id()
        for label, material_id in (
            ("Sending", self.sending_fluid_id),
            ("Receiving", self.receiving_fluid_id),
        ):
            material = materials.get(material_id)
            if material is None:
                errors.append(f"{label} fluid does not exist in the project.")
            elif not isinstance(material, FluidSpec):
                errors.append(f"{label} material must be a FluidSpec.")

        errors.extend(
            f"Frequency settings: {error}"
            for error in self.frequencies.validate()
        )
        errors.extend(self._angle_errors())
        return errors

    def to_dict(self) -> dict:
        """Convert the solver configuration to JSON-ready values.

        Returns
        -------
        dict
            Solver fields with enum values stored as strings.
        """
        return {
            "id": self.id,
            "name": self.name,
            "solver_type": self.solver_type.value,
            "frequencies": self.frequencies.to_dict(),
            "angle_deg": self.angle_deg,
            "max_angle_deg": self.max_angle_deg,
            "boundary_condition": self.boundary_condition.value,
            "sending_fluid_id": self.sending_fluid_id,
            "receiving_fluid_id": self.receiving_fluid_id,
            "layup_ids": list(self.layup_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SolverSpec":
        """Create a solver configuration from serialized values.

        Parameters
        ----------
        data : dict
            Dictionary created by :meth:`to_dict`.

        Returns
        -------
        SolverSpec
            Restored solver specification.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            solver_type=SolverType(data["solver_type"]),
            frequencies=FrequencySettings.from_dict(data["frequencies"]),
            angle_deg=data["angle_deg"],
            max_angle_deg=data["max_angle_deg"],
            boundary_condition=BoundaryCondition(
                data["boundary_condition"]
            ),
            sending_fluid_id=data["sending_fluid_id"],
            receiving_fluid_id=data["receiving_fluid_id"],
            layup_ids=list(data["layup_ids"]),
        )

    def _angle_errors(self) -> list[str]:
        """Return an error if the angle used by this preset is invalid.

        Returns
        -------
        list of str
            Empty when the applicable angle is finite and in [0, 90).
        """
        if self.uses_diffuse_angle():
            angle = self.max_angle_deg
            label = "Maximum angle"
        else:
            angle = self.angle_deg
            label = "Angle"
        if not math.isfinite(angle) or not 0 <= angle < 90:
            return [f"{label} must be in [0, 90) degrees."]
        return []

    def _angle_radians(self) -> float:
        """Return the active single or diffuse angle in radians.

        Returns
        -------
        float
            Active angle converted from degrees to radians.

        Raises
        ------
        ValueError
            If the active angle is outside [0, 90) degrees.
        """
        errors = self._angle_errors()
        if errors:
            raise ValueError(errors[0])
        if self.uses_diffuse_angle():
            return math.radians(self.max_angle_deg)
        return math.radians(self.angle_deg)
