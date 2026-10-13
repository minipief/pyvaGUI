# Phase 08 - Material Dialogs

## Goal

Create and edit material specifications through PyQt dialogs, and browse
the reusable material library without placing Qt dependencies in the
model.

## What was built

- `pyvagui/gui/material_editor.py`: dataclass-driven material forms,
  parsing, validation, copy-on-edit, and library actions.
- `pyvagui/gui/library_dialog.py`: material list, multi-selection,
  project copies, import/export, deletion, and frame-dependency prompt.
- `pyvagui/gui/main_window.py`: connect New/Edit Material and Open Library
  menu actions to the dialogs.
- `tests/gui/test_material_editor.py` and
  `tests/gui/test_library_dialog.py`: dialog behavior and temporary-file
  workflows.
- Expanded `pyqt_primer.md`; updated decisions and changelog.
- Added read-only migration for legacy material-library references after
  an existing user library exposed obsolete schema fields.

## How it works

`MaterialEditorDialog` edits a deep copy. It builds one control per
dataclass field: line edits for floats, checkboxes for booleans, and a
project Isomat selector for `solid_mat_id`. Save reads every value,
combines parse and model-validation errors, and accepts only when none
remain. Cancel never writes back to the project.

`LibraryDialog` reads stable IDs from list rows. Adding a material copies
it with a fresh ID. If a poroelastic material references a frame absent
from the project, the dialog asks whether to copy that frame too and then
rewrites the copied reference.

## Concepts used

See `pyqt_primer.md`: QDialog, `dataclasses.fields`, QLineEdit,
QCheckBox, QComboBox, QGroupBox, QGridLayout, QDialogButtonBox, and
QListWidget.

## Decisions

- D-014: edit a copy and commit only after validation succeeds.
- D-015: disable material-type changes while editing existing materials.
- D-016: ask before importing an absent poroelastic frame dependency.

## Tests

- Material editor tests: 10 passed.
- Library dialog tests: 8 passed.
- Full `python -m pytest`: 110 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.
- Library tests use `tmp_path`. The actual user library was loaded
  read-only to verify migration; it was not modified.

## Problems and solutions

The library loads bundled defaults when its user file does not exist. The
import test therefore creates an explicit empty temporary library before
importing, keeping the test independent from those defaults. Existing
version-1 files can also contain earlier material reference fields; the
loader migrates recognized fields in memory and waits for an explicit
save before rewriting them.

## How to verify manually

Run `python -m pyvagui`, then choose Edit > New material. Switch among
material types, enter a decimal comma or scientific notation, and try an
invalid value. Open a poroelastic material and inspect the available
project Isomats. Open Library to import, export, or add a material.

## Comprehension questions

1. Why does the editor modify a deep copy rather than the project object?
2. How does the library dialog preserve the poroelastic-to-frame reference
   after assigning new material IDs?
