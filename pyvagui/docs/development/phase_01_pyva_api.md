# Phase 01 - pyva API Inspection

## Goal

Inspect the installed pyva package before implementing model calculations,
and create the development documentation structure.

## What was built

- `pyva_api_notes.md`: installed pyva-toolbox 1.3.1 signatures, observed
  behavior, and comparison with the online documentation.
- `decisions.md`, `pyqt_primer.md`, `deviations.md`, and
  `open_questions.md`: initial project records.
- Updated `tests/test_smoke.py` to use the current ID-based frame
  reference and conversion API. `materials.py` was not changed.
- Updated `CHANGELOG.md` with this phase.

## How it works

The selected Python 3.13.7 environment imports pyva-toolbox 1.3.1.
`inspect.signature()` was used to read constructor and method parameters;
source inspection confirmed return behavior and perforation handling.
The installed package and the online documentation agree on the
inspected signatures.

## Concepts used

No PyQt concepts were introduced. See `pyqt_primer.md`.

## Decisions

- D-001: use installed pyva signatures as the implementation reference.
- D-002: build pyva perforations from radius and spacing values.

## Tests

- `python -m pytest`: 3 passed after updating stale smoke-test assumptions.
- `flake8`: passed with no findings.

## Problems and solutions

The original smoke tests constructed poroelastic material with a nested
frame object and called `to_pyva()` without its material dictionary.
They also expected an unsupported legacy `Pr` field. Tests were aligned
with the documented current API without changing `materials.py`.

## How to verify manually

No GUI exists yet. Review `pyva_api_notes.md` and compare the documented
signatures with the installed package using `inspect.signature()`.

## Comprehension questions

1. Why does `LayerSpec` pass a `PerforatedLayer` object instead of passing
   hole radius and spacing directly to `PlateLayer`?
2. Why is `n_points` not yet enough information to define third-octave
   frequencies together with start and end values?
