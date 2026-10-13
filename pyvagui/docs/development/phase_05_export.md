# Phase 05 - Result Export

## Goal

Export calculated result arrays as CSV and Matplotlib figures as PNG or
SVG without introducing GUI dependencies into the service layer.

## What was built

- `pyvagui/services/export.py`: CSV export for real and complex result
  views, and PNG/SVG figure export.
- `tests/model/test_export.py`: temporary-file tests for columns, views,
  validation errors, and rendered image formats.
- Updated decisions and changelog.

## How it works

`export_csv` writes one frequency column followed by one column for every
layup/view pair. The caller provides views in the desired column order.
Complex arrays are converted to magnitude, phase in degrees, real part,
or imaginary part. `export_image` selects Matplotlib's output format from
the `.png` or `.svg` extension.

## Concepts used

- Python's `csv` module handles quoting and Windows-compatible newlines.
- `numpy.abs`, `numpy.angle`, `numpy.real`, and `numpy.imag` convert
  complex data into real-valued export columns.
- Matplotlib's `Figure.savefig` writes image files.
- No PyQt concepts were introduced; see `pyqt_primer.md`.

## Decisions

- D-009: stable lowercase view names; phase is exported in degrees.
- D-010: support PNG and SVG only.

## Tests

- Focused export tests: 9 passed.
- Full `python -m pytest`: 79 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

CSV export rejects complex arrays requested as a raw `value`, since a
complex number is not a useful scalar table cell. The caller must choose
an explicit real-valued view. Result lengths are checked against the
frequency array before writing.

## How to verify manually

There is no GUI yet. Run `python -m pytest tests/model/test_export.py`.
The tests create all output files under pytest's temporary directory.

## Comprehension questions

1. Why does CSV export require an explicit view for complex impedance?
2. How does `export_image` choose the Matplotlib output format?
