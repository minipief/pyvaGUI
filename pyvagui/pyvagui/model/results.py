"""In-memory result containers for solver calculations.

Result objects keep calculated arrays separate from project files and
provide the values needed by the GUI and export services.
"""

from dataclasses import dataclass

import numpy as np

from pyvagui.model.solvers import SolverType


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
    """

    solver_id: str
    solver_name: str
    solver_type: SolverType
    frequencies: np.ndarray
    labels: list[str]
    results: list[LayupResult]
