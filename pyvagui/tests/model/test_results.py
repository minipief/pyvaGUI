"""Tests for the in-memory calculation result containers."""

import numpy as np

from pyvagui.model.results import LayupResult, ResultSet
from pyvagui.model.solvers import SolverType


def test_result_set_stores_layup_values_and_frequency_metadata():
    """Keep result values aligned with their shared frequencies and labels."""
    frequencies = np.array([100.0, 1000.0])
    values = np.array([0.2, 0.8])
    layup_result = LayupResult(
        layup_id="layup-1",
        layup_name="Fibre absorber",
        values=values,
    )
    result_set = ResultSet(
        solver_id="solver-1",
        solver_name="Absorption",
        solver_type=SolverType.ABSORPTION,
        frequencies=frequencies,
        labels=["100", "1000"],
        results=[layup_result],
    )

    assert result_set.results[0] is layup_result
    assert np.array_equal(result_set.frequencies, frequencies)
    assert np.array_equal(result_set.results[0].values, values)


def test_layup_result_accepts_complex_values():
    """Store complex impedance values without converting to real values."""
    values = np.array([100.0 + 20.0j, 200.0 + 30.0j])
    result = LayupResult(
        layup_id="layup-1",
        layup_name="Plate",
        values=values,
    )

    assert np.iscomplexobj(result.values)
    assert np.array_equal(result.values, values)
