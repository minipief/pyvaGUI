# Phase 09 - Layup Editor

## Goal

Edit ordered layers and their perforations while preserving the model's SI
units and keeping table widgets synchronized with the `Layup` object.

## What was built

- `pyvagui/gui/layup_editor.py`: layer table with material/type selectors,
  thickness, perforation and delete controls, plus move buttons and drops.
- `pyvagui/gui/perforation_dialog.py`: hole-radius and spacing editor with
  remove, cancel, and save actions.
- `pyvagui/gui/main_window.py`: enable New Layup and double-click editing.
- `tests/gui/test_layup_editor.py`,
  `tests/gui/test_perforation_dialog.py`, and main-window integration
  tests for editing, validation, units, and ordering.
- Expanded `pyqt_primer.md`; updated decisions and changelog.

## How it works

The dialog edits a copy of the layup. Each material selector lists only
materials supported by `LayerSpec.allowed_types`; choosing another
material resets the type and removes incompatible perforation data.
Thickness is displayed in millimeters and converted to meters when saved.
The perforation dialog applies the same conversion to radius and spacing.

Drag-and-drop and Move up/down call `Layup.move_layer()` and then rebuild
the whole table. This keeps `setCellWidget` controls attached to the
correct model layer rather than relying on Qt's item-only row movement.

## Concepts used

See `pyqt_primer.md`: QTableWidget and cell widgets,
QAbstractItemView drag-and-drop modes, and QFormLayout.

## Decisions

- D-018: display layer/perforation lengths in mm and store meters.
- D-019: reorder the model and rebuild table widgets after every move.

## Tests

- Focused layup/perforation dialog tests: 11 passed.
- Main-window layup integration tests: 2 passed.
- Full `python -m pytest`: 123 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

Qt moves table items during its default internal drop operation, but does
not move widgets installed with `setCellWidget`. The table subclass now
reads source and target rows, delegates the move to the model, and calls
`refresh()` to recreate every row.

## How to verify manually

Run `python -m pyvagui`, add materials, then choose Edit > New layup. Add
layers, change a material and its representation, set or remove a
perforation, and reorder rows by dragging or using Move up/down. Save and
confirm the model tree shows the new layup.

## Comprehension questions

1. Why does the editor show millimeters while `LayerSpec` stores meters?
2. Why must the table be rebuilt after a row is moved?
