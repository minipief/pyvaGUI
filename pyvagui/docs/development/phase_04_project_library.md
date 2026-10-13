# Phase 04 - Projects and Material Library

## Goal

Own materials, layups, and solvers in a project; validate their
references; persist projects; and provide reusable material files.

## What was built

- `pyvagui/model/project.py`: project collections, add/remove/find
  operations, reference checks, material-user lookup, and versioned JSON.
- `pyvagui/model/library.py`: platform-specific library paths, bundled
  defaults, persistence, and material import/export.
- `pyvagui/resources/default_library.json`: air, aluminium, steel,
  glass wool, and Delany-Bazley fibre specifications.
- `pyproject.toml`: include the bundled JSON resource in distributions.
- `tests/model/test_project.py` and `tests/model/test_library.py`:
  project, library, file, reference, and ID-remapping coverage.
- Updated decisions and changelog.

## How it works

Projects serialize their material, layup, and solver specifications with
`format_version: 1`. Loading restores those model objects, sets the file
path, and clears the modified flag. Results are intentionally excluded.

The material library loads the bundled JSON into a new user library on
first use. Imported materials receive new IDs. When a poroelastic
material and its frame are imported together, the frame reference is
updated to the new frame ID; if the frame is absent, the original frame
ID remains available for a later project prompt.

## Concepts used

- JSON versioning lets the application reject unsupported project files.
- `pathlib.Path` keeps project and library paths platform-independent.
- `dataclasses.replace`-based material copies preserve values while
  changing identifiers.
- No PyQt concepts were introduced; see `pyqt_primer.md`.

## Decisions

- D-006: persist project configuration only; do not persist runtime state
  or results.
- D-007: importing returns material copies but does not commit them to the
  library automatically.
- D-008: remap included poroelastic frame references during import.

## Tests

- Focused project and library tests: 15 passed.
- Full `python -m pytest`: 70 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.
- Wheel contents could not be checked because `setuptools>=68` is not
  installed and network access to PyPI is unavailable.
- Library tests use `tmp_path`; the real user library is never accessed.

## Problems and solutions

Poroelastic specifications store the frame material by ID. Importing the
frame and poroelastic material together therefore needs an ID mapping;
the library remaps that reference while keeping missing external frame
IDs unchanged.

The resource inclusion is declared in `pyproject.toml`, but a local wheel
build could not verify the packaged archive because the build dependency
was unavailable offline.

## How to verify manually

There is no GUI yet. Run `python -m pytest tests/model/test_project.py
tests/model/test_library.py` to exercise persistence and material-file
operations without touching the real user library.

## Comprehension questions

1. Which project fields are deliberately not written to JSON, and why?
2. What happens to a poroelastic frame reference when its frame is not
   included in an imported material file?
