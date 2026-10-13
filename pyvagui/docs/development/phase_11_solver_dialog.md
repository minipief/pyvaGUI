# Phase 11 - Solver Dialog

## Goal

Configure calculation presets from the project and give each solver a
stable place for its future result view.

## What was built

- `pyvagui/gui/solver_dialog.py`: preset, fluids, angle, frequency,
  boundary-condition, and checkable layup controls with validation.
- `pyvagui/gui/main_window.py`: New/Edit Solver actions and one placeholder
  result tab per project solver.
- `tests/gui/test_solver_dialog.py` and main-window integration tests.
- Expanded `pyqt_primer.md`; updated decisions and changelog.

## How it works

The dialog fills fluid choices from project `FluidSpec` objects and layup
choices from the project layups. Selecting a diffuse preset shows its
maximum angle; other presets show one incidence angle. Save parses the
frequency range and angle fields, builds a copied `SolverSpec`, runs its
project validation, and only returns it when valid. New solver entries
create a named result placeholder tab.

## Concepts used

See `pyqt_primer.md`: QTabWidget. The dialog also reuses QComboBox,
QFormLayout, QGroupBox, QLineEdit, QListWidget, and QDialogButtonBox.

## Decisions

- D-022: create result placeholder tabs with solver configuration.
- D-003: preserve all frequency fields and use logarithmic sample spacing.

## Tests

- Solver-dialog tests: 6 passed.
- Main-window tests cover new solver and result-tab creation plus solver
  editing through the model tree.
- Full `python -m pytest`: 134 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

Angle inputs are kept separately for single and diffuse presets. Switching
presets only changes visibility, so each mode's value is preserved when a
user switches away and back.

## How to verify manually

Run `python -m pyvagui`, add a layup and fluids, then choose Edit > New
solver. Switch between Absorption and Absorption diffuse and observe the
angle field. Select frequencies, boundary condition, and layup, then save
and confirm a new solver tab appears.

## Comprehension questions

1. Why does the dialog keep separate single-angle and diffuse-angle values?
2. What project data is stored on each checked layup-list item?
