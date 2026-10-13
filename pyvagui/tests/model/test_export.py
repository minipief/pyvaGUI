"""Tests for CSV and image export services."""

import csv

import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from pyvagui.model.results import LayupResult, ResultSet
from pyvagui.model.solvers import SolverType
from pyvagui.services.export import export_csv, export_image


def make_result_set(
    solver_type: SolverType,
    values: list[np.ndarray],
) -> ResultSet:
    """Create a result set with one named layup per values array."""
    return ResultSet(
        solver_id="solver-id",
        solver_name="Test solver",
        solver_type=solver_type,
        frequencies=np.array([100.0, 1000.0]),
        labels=["100", "1k"],
        results=[
            LayupResult(
                layup_id=f"layup-{index}",
                layup_name=name,
                values=array,
            )
            for index, (name, array) in enumerate(
                zip(("Glass wool", "Steel plate"), values)
            )
        ],
    )


def test_export_csv_writes_frequency_and_real_values(tmp_path):
    """Write one value column per layup with stable headings."""
    result_set = make_result_set(
        SolverType.ABSORPTION,
        [np.array([0.25, 0.75]), np.array([0.4, 0.8])],
    )
    path = tmp_path / "results.csv"

    export_csv(result_set, path, ["value"])

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    assert rows[0] == [
        "Frequency [Hz]",
        "Glass wool | value",
        "Steel plate | value",
    ]
    assert rows[1] == ["100.0", "0.25", "0.4"]
    assert rows[2] == ["1000.0", "0.75", "0.8"]


def test_export_csv_writes_selected_complex_views(tmp_path):
    """Export magnitude, phase, real, and imaginary impedance columns."""
    result_set = make_result_set(
        SolverType.IMPEDANCE,
        [
            np.array([3.0 + 4.0j, 1.0j]),
            np.array([1.0 - 1.0j, -2.0 + 2.0j]),
        ],
    )
    path = tmp_path / "impedance.csv"

    export_csv(
        result_set,
        path,
        ["magnitude", "phase", "real", "imaginary"],
    )

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    assert rows[0] == [
        "Frequency [Hz]",
        "Glass wool | magnitude",
        "Glass wool | phase [deg]",
        "Glass wool | real part",
        "Glass wool | imaginary part",
        "Steel plate | magnitude",
        "Steel plate | phase [deg]",
        "Steel plate | real part",
        "Steel plate | imaginary part",
    ]
    values = [float(value) for value in rows[1][1:]]
    expected = [5.0, 53.130102, 3.0, 4.0, 2**0.5, -45.0, 1.0, -1.0]
    assert np.allclose(values, expected)


@pytest.mark.parametrize("views", [[], ["unknown"]])
def test_export_csv_rejects_empty_or_unknown_views(tmp_path, views):
    """Reject requests without a supported output view."""
    result_set = make_result_set(
        SolverType.ABSORPTION,
        [np.array([0.25, 0.75]), np.array([0.4, 0.8])],
    )

    with pytest.raises(ValueError):
        export_csv(result_set, tmp_path / "results.csv", views)


def test_export_csv_rejects_complex_value_view(tmp_path):
    """Require complex arrays to select a meaningful real-valued view."""
    result_set = make_result_set(
        SolverType.IMPEDANCE,
        [np.array([1.0 + 2.0j, 3.0 + 4.0j]), np.array([2.0j, 3.0j])],
    )

    with pytest.raises(ValueError, match="Complex results"):
        export_csv(result_set, tmp_path / "results.csv", ["value"])


def test_export_csv_rejects_result_length_mismatch(tmp_path):
    """Require every layup array to align with the frequency array."""
    result_set = make_result_set(
        SolverType.ABSORPTION,
        [np.array([0.25]), np.array([0.4, 0.8])],
    )

    with pytest.raises(ValueError, match="frequency count"):
        export_csv(result_set, tmp_path / "results.csv", ["value"])


@pytest.mark.parametrize(
    ("extension", "prefix"),
    [("png", b"\x89PNG"), ("svg", b"<?xml")],
)
def test_export_image_saves_supported_formats(tmp_path, extension, prefix):
    """Save a Matplotlib figure in PNG and SVG formats."""
    figure = Figure()
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    axes.plot([100, 1000], [0.2, 0.8])
    path = tmp_path / f"plot.{extension}"

    export_image(figure, path)

    assert path.exists()
    assert path.read_bytes().startswith(prefix)


def test_export_image_rejects_unknown_format(tmp_path):
    """Reject extensions that Matplotlib export does not support here."""
    figure = Figure()

    with pytest.raises(ValueError, match="PNG and SVG"):
        export_image(figure, tmp_path / "plot.jpg")
