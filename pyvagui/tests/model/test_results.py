"""Tests for the in-memory calculation result containers."""

import numpy as np
import pytest

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


def make_display_result(solver_type, **kwargs):
    return ResultSet(
        solver_id="solver", solver_name="Display", solver_type=solver_type,
        frequencies=np.array([100.0, 1000.0]), labels=["100", "1000"],
        results=[], **kwargs,
    )


@pytest.mark.parametrize("solver_type", [
    SolverType.ABSORPTION, SolverType.ABSORPTION_DIFFUSE,
])
def test_absorption_display_values(solver_type):
    result = make_display_result(solver_type)
    values = np.array([0.0, 0.75])
    expected = [[0, 0.75], [0, 75], [1, 0.25], [1, 0.5], [0, 6.02059991]]
    for view, converted in zip(result.display_views(), expected):
        np.testing.assert_allclose(
            result.display_values(values, view), converted,
        )
    np.testing.assert_array_equal(values, [0, 0.75])


@pytest.mark.parametrize("solver_type", [
    SolverType.TRANSMISSION, SolverType.TRANSMISSION_DIFFUSE,
    SolverType.TRANSMISSION_ALLARD,
])
def test_transmission_display_values(solver_type):
    result = make_display_result(solver_type)
    values = np.array([1.0, 0.01])
    expected = [[1, 0.01], [100, 1], [0, 20], [0, -20]]
    for view, converted in zip(result.display_views(), expected):
        np.testing.assert_allclose(
            result.display_values(values, view), converted,
        )
    np.testing.assert_array_equal(values, [1, 0.01])


def test_impedance_display_values_use_reference_fluid_and_angle():
    result = make_display_result(
        SolverType.IMPEDANCE, reference_impedance=400.0, angle_deg=60.0,
    )
    values = np.array([800.0 + 0j, 400.0 + 400j])
    reflection = (values * 0.5 - 400) / (values * 0.5 + 400)
    expected = {
        "magnitude": np.abs(values),
        "phase": np.angle(values, deg=True),
        "real": values.real,
        "imaginary": values.imag,
        "normalized_magnitude": np.abs(values / 400),
        "normalized_real": values.real / 400,
        "normalized_imaginary": values.imag / 400,
        "admittance_magnitude": np.abs(1 / values),
        "admittance_real": (1 / values).real,
        "admittance_imaginary": (1 / values).imag,
        "reflection_magnitude": np.abs(reflection),
        "reflection_phase": np.angle(reflection, deg=True),
        "absorption": 1 - np.abs(reflection) ** 2,
    }
    assert set(result.display_views()) == set(expected)
    for view, converted in expected.items():
        np.testing.assert_allclose(
            result.display_values(values, view), converted, atol=1e-14,
        )
    np.testing.assert_array_equal(values, [800 + 0j, 400 + 400j])


def test_impedance_without_fluid_omits_reference_dependent_views():
    result = make_display_result(SolverType.IMPEDANCE)
    assert set(result.display_views()) == {
        "magnitude", "phase", "real", "imaginary", "admittance_magnitude",
        "admittance_real", "admittance_imaginary",
    }
    with pytest.raises(ValueError, match="Unavailable"):
        result.display_values(np.array([1j, 2j]), "normalized_real")


def test_logarithmic_views_preserve_infinite_limits_without_warnings():
    transmission = make_display_result(SolverType.TRANSMISSION)
    absorption = make_display_result(SolverType.ABSORPTION)
    with np.errstate(all="raise"):
        assert np.isposinf(transmission.display_values(
            np.array([0.0]), "transmission_loss",
        )[0])
        assert np.isneginf(transmission.display_values(
            np.array([0.0]), "transmission_level",
        )[0])
        assert np.isposinf(absorption.display_values(
            np.array([1.0]), "reflection_attenuation",
        )[0])
