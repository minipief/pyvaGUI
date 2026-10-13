# Phase 13 - Result Views

## Goal

Display solver output in per-solver tabs, plot each selected layup, and
let users change impedance views and export data or figures.

## What was built

- `pyvagui/gui/result_tab.py`: Matplotlib/QTAgg canvas, log-frequency
  axes, solver-specific labels, complex checkboxes, Run, and Export.
- `pyvagui/gui/main_window.py`: create ResultTab pages, pass worker results
  into the matching solver page, and preserve results across refreshes.
- `tests/gui/test_result_tab.py`: curve, axis, complex view, run callback,
  CSV, and PNG tests; the main-window end-to-end test creates a project,
  material, layup, and solver, then checks a plotted worker result.
- Expanded `pyqt_primer.md`; updated decisions and changelog.

## How it works

Each ResultTab owns a Matplotlib figure embedded by
`FigureCanvasQTAgg`. Real-valued solvers draw one curve per layup on a
logarithmic frequency axis. Impedance creates one subplot per selected
view, defaulting to magnitude and phase. Run starts the Phase 12 worker;
the matching `ResultSet` is drawn when the GUI receives the finished
signal. Export uses the existing CSV and PNG/SVG services.

## Concepts used

See `pyqt_primer.md`: FigureCanvasQTAgg, Matplotlib figures, and
logarithmic plot axes.

## Decisions

- D-024: use separate axes for selected complex impedance views.
- D-025: route worker signals to bound GUI-thread slots.
- D-009: CSV view identifiers are stable and phase is in degrees.
- D-010: image export supports PNG and SVG.

## Tests

- ResultTab tests verify log scale, y-axis labels, curves, selected
  impedance views, CSV headers/data, and PNG output.
- Main-window worker integration verifies results reach and update a
  solver tab.
- End-to-end GUI workflow verifies dialog-created project data reaches a
  plotted result curve.
- Full `python -m pytest`: 151 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

Matplotlib labels and CSV data use the same solver frequencies. Complex
impedance arrays are converted to real-valued views before plotting or
CSV export; the underlying arrays remain complex in the `ResultSet`.

## How to verify manually

Run `python -m pyvagui`, choose a solver tab, and press Run. Check that
each selected layup has a curve and the frequency axis is logarithmic.
For impedance, toggle magnitude/phase/real/imaginary and export CSV or
PNG/SVG from the tab.

## Comprehension questions

1. Why are impedance views drawn on separate subplots?
2. How does the ResultTab receive results without the worker touching a widget?
