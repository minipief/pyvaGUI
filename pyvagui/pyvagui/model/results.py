"""In-memory result containers for solver calculations.

Result objects keep calculated arrays separate from project files and
provide the values needed by the GUI and export services.
"""

from dataclasses import dataclass

import numpy as np

from pyvagui.model.solvers import SolverType


ABSORPTION_VIEWS = {
    "value": "Absorption coefficient [-]",
    "percent": "Absorption coefficient [%]",
    "reflection": "Reflection coefficient 1 - alpha [-]",
    "reflection_magnitude": "Reflection magnitude |r| [-]",
    "reflection_attenuation": "Reflection attenuation [dB]",
}

TRANSMISSION_VIEWS = {
    "value": "Transmission coefficient tau [-]",
    "transmission_loss": "Sound reduction index R [dB]",
}

IMPEDANCE_VIEWS = {
    "magnitude": "Impedance magnitude |Z| [Pa s/m]",
    "phase": "Impedance phase [deg]",
    "real": "Impedance real part [Pa s/m]",
    "imaginary": "Impedance imaginary part [Pa s/m]",
}


@dataclass(kw_only=True)
class LayupResult:
    """Calculated values for one layup.

    Parameters
    ----------
    layup_id : str
        Identifier of the calculated layup.
    layup_name : str
        Name of the calculated layup when the result was produced.
    values : numpy.ndarray
        Real or complex values, one per frequency.
    """

    layup_id: str
    layup_name: str
    values: np.ndarray


@dataclass(kw_only=True)
class ResultSet:
    """All layup results produced by one solver run.

    Parameters
    ----------
    solver_id : str
        Identifier of the solver configuration.
    solver_name : str
        Solver name when the result was produced.
    solver_type : SolverType
        Calculation method that produced these values.
    frequencies : numpy.ndarray
        Frequency values [Hz] shared by every layup result.
    labels : list of str
        Display labels matching the frequencies.
    results : list of LayupResult
        Per-layup values from the calculation.
    reference_impedance : float or None, optional
        Sending-fluid rho0*c0 [Pa s/m] captured at calculation time.
    angle_deg : float, optional
        Incidence angle [degrees] captured at calculation time.
    """

    solver_id: str
    solver_name: str
    solver_type: SolverType
    frequencies: np.ndarray
    labels: list[str]
    results: list[LayupResult]
    reference_impedance: float | None = None
    angle_deg: float = 0.0

    def display_views(self) -> dict[str, str]:
        """Return available frequency-curve variants and their axis labels."""
        if self.solver_type is SolverType.IMPEDANCE:
            return {
                view: label for view, label in IMPEDANCE_VIEWS.items()
                if self.reference_impedance is not None
                or not (view.startswith("normalized_")
                        or view.startswith("reflection_")
                        or view == "absorption")
            }
        if self.solver_type in (
            SolverType.ABSORPTION, SolverType.ABSORPTION_DIFFUSE,
        ):
            return dict(ABSORPTION_VIEWS)
        return dict(TRANSMISSION_VIEWS)

    def display_values(self, values: np.ndarray, view: str) -> np.ndarray:
        """Convert raw solver values without changing the calculated arrays."""
        if view not in self.display_views():
            raise ValueError(f"Unavailable result view: {view}")
        with np.errstate(divide="ignore", invalid="ignore"):
            if self.solver_type is not SolverType.IMPEDANCE:
                coefficient = np.real(values)
                if view == "percent":
                    return 100 * coefficient
                if view == "reflection":
                    return 1 - coefficient
                if view == "reflection_magnitude":
                    return np.sqrt(1 - coefficient)
                if view == "reflection_attenuation":
                    return -10 * np.log10(1 - coefficient)
                if view == "transmission_loss":
                    return -10 * np.log10(coefficient)
                if view == "transmission_level":
                    return 10 * np.log10(coefficient)
                return coefficient

            transformed = np.asarray(values, dtype=complex)
            component = view
            if view.startswith("normalized_"):
                transformed = transformed / self.reference_impedance
                component = view.removeprefix("normalized_")
            elif view.startswith("admittance_"):
                transformed = 1 / transformed
                component = view.removeprefix("admittance_")
            elif view.startswith("reflection_") or view == "absorption":
                normal = transformed * np.cos(np.deg2rad(self.angle_deg))
                transformed = (
                    (normal - self.reference_impedance)
                    / (normal + self.reference_impedance)
                )
                if view == "absorption":
                    return 1 - np.abs(transformed) ** 2
                component = view.removeprefix("reflection_")
            if component == "phase":
                return np.angle(transformed, deg=True)
            if component == "real":
                return np.real(transformed)
            if component == "imaginary":
                return np.imag(transformed)
            return np.abs(transformed)
