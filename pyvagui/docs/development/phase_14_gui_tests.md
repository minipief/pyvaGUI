# Phase 14 - GUI Tests

## Goal

Verify GUI workflows from individual dialogs through project management,
background calculation, result plotting, and export.

## What was built

- Expanded `tests/gui/test_main_window.py` with an end-to-end project to
  calculated-curve test, solver-ID Run routing, invalid-run blocking, and
  worker lifecycle cases.
- Expanded `tests/gui/test_result_tab.py` to exercise the CSV, PNG, and
  SVG choices through the visible result-tab export action.
- Existing material, library, layup, perforation, and solver dialog tests
  remain isolated from user files and patch modal prompts.
- Updated the changelog.

## How it works

Dialog tests verify parsing, validation, selection, and copy-on-edit.
Main-window tests create project objects, run a calculation on a QThread,
and verify the returned values reach a Matplotlib curve. Export tests
inspect the generated files and CSV columns in temporary directories.

## Concepts used

No new Qt concepts were introduced; see `pyqt_primer.md` for the concepts
used in earlier phases.

## Decisions

No new design decisions were required in this test-coverage phase.

## Tests

- Full `python -m pytest`: 154 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.
- GUI tests use `qtbot`, monkeypatched dialogs, and pytest temporary paths.

## Problems and solutions

The end-to-end test mocks the UI dialog acceptance but runs the actual
worker thread and real ResultTab rendering. Real pyva calculations for all
six solver types remain covered by the model tests, keeping GUI tests
quick and deterministic.

## How to verify manually

Run `python -m pyvagui`, create a material, layup, and solver, then run it.
Verify that the result tab shows a logarithmic graph; try the impedance
views and export as CSV, PNG, and SVG.

## Comprehension questions

1. Which parts of the end-to-end workflow use real pyva and which are
   simulated by the GUI test?
2. How does the test confirm that a result is plotted rather than only
   stored in a `ResultSet`?
