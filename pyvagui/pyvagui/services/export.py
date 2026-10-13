"""Export calculated results to CSV and Matplotlib figures to image files.

These functions are application services: they translate in-memory model
objects into user-selected files without adding GUI dependencies.
"""

import csv
from pathlib import Path
from typing import Sequence

import numpy as np
from matplotlib.figure import Figure

from pyvagui.model.results import ResultSet


_VIEW_LABELS = {
    "value": "value",
    "magnitude": "magnitude",
    "phase": "phase [deg]",
    "real": "real part",
    "imaginary": "imaginary part",
}


def export_csv(
    result_set: ResultSet,
    path: str | Path,
    views: Sequence[str],
) -> None:
    """Write frequencies and selected layup views to a CSV file.

    View names are ``value``, ``magnitude``, ``phase``, ``real``, and
    ``imaginary``. Phase is written in degrees. Complex results require
    an explicit view other than ``value``.

    Parameters
    ----------
    result_set : ResultSet
        Frequencies and results to export.
    path : str or pathlib.Path
        Destination CSV file.
    views : sequence of str
        Views to include for every layup, in column order.

    Raises
    ------
    ValueError
        If views are empty, a view is unknown, a complex array requests
        ``value``, or result lengths do not match the frequencies.
    """
    if not views:
        raise ValueError("Select at least one result view.")
    for view in views:
        if view not in _VIEW_LABELS:
            raise ValueError(f"Unknown result view: {view}")

    frequencies = np.asarray(result_set.frequencies)
    if frequencies.ndim != 1:
        raise ValueError("Frequencies must be a one-dimensional array.")

    columns = []
    header = ["Frequency [Hz]"]
    for result in result_set.results:
        values = np.asarray(result.values)
        if values.ndim != 1 or len(values) != len(frequencies):
            raise ValueError(
                f"Result length for '{result.layup_name}' must match "
                "the frequency count."
            )
        for view in views:
            if view == "value" and np.iscomplexobj(values):
                raise ValueError(
                    "Complex results require an explicit magnitude, "
                    "phase, real, or imaginary view."
                )
            columns.append(_values_for_view(values, view))
            header.append(f"{result.layup_name} | {_VIEW_LABELS[view]}")

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for index, frequency in enumerate(frequencies):
            row = [frequency.item()]
            row.extend(column[index].item() for column in columns)
            writer.writerow(row)


def export_image(figure: Figure, path: str | Path) -> None:
    """Save a Matplotlib figure as a PNG or SVG image.

    Parameters
    ----------
    figure : matplotlib.figure.Figure
        Figure to save.
    path : str or pathlib.Path
        Destination filename. Its extension selects PNG or SVG format.

    Raises
    ------
    ValueError
        If the destination extension is not ``.png`` or ``.svg``.
    """
    target = Path(path)
    image_format = target.suffix.lower().lstrip(".")
    if image_format not in ("png", "svg"):
        raise ValueError("Image export supports only PNG and SVG files.")
    figure.savefig(target, format=image_format)


def _values_for_view(values: np.ndarray, view: str) -> np.ndarray:
    """Extract one real-valued view from a result array.

    Parameters
    ----------
    values : numpy.ndarray
        One-dimensional real or complex result values.
    view : str
        View identifier from ``_VIEW_LABELS``.

    Returns
    -------
    numpy.ndarray
        Real-valued view, with phase expressed in degrees.
    """
    if view == "value":
        return np.real(values)
    if view == "magnitude":
        return np.abs(values)
    if view == "phase":
        return np.angle(values, deg=True)
    if view == "real":
        return np.real(values)
    return np.imag(values)
