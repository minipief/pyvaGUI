# Phase 03 - Solvers and Results

## Goal

Configure the six pyva calculation methods, run them for one layup, and
store their arrays in transient result objects.

## What was built

- `pyvagui/model/solvers.py`: logarithmic frequency settings, boundary
  conditions, solver presets, validation, serialization, and pyva calls.
- `pyvagui/model/results.py`: in-memory `LayupResult` and `ResultSet`
  containers for real or complex arrays.
- `tests/model/test_solvers.py` and `tests/model/test_results.py`: model
  checks and one real pyva calculation for each solver preset.
- Updated API observations, decisions, deviations, and changelog.

## How it works

The frequency settings validate their limits and generate `n_points`
with logarithmic spacing. A solver resolves the two project fluids,
builds the layup's `TMmodel`, converts a single incidence angle to
radians, and uses the sending fluid's wavenumber for
`kx = k * sin(theta)`. Diffuse presets pass `max_angle_deg` in radians.
Each pyva method is called with `signal=False`, so the result container
stores plain NumPy arrays.

```text
SolverSpec + Layup + materials
    -> validate frequency, fluid, layup, and angle settings
    -> build TMmodel and calculate values
    -> LayupResult arrays inside an in-memory ResultSet
```

## Concepts used

- `numpy.geomspace` preserves the requested endpoints and sample count
  while distributing points logarithmically.
- `Enum` values are stored as strings in solver dictionaries.
- NumPy arrays retain complex impedance values without conversion.
- No PyQt concepts were introduced; see `pyqt_primer.md`.

## Decisions

- D-003: retain all frequency fields and use logarithmic spacing, not
  exact third-octave centers.
- D-005: keep results out of project serialization.

## Tests

- Focused solver and result tests: 29 passed after angle-bound coverage.
- Full `python -m pytest`: 55 passed; 19 deprecation warnings originate
  in pyva 1.3.1.
- Full `flake8`: passed with no findings.

## Problems and solutions

pyva 1.3.1 returned finite arrays for all six methods. Its diffuse
integrators emitted NumPy scalar-conversion deprecation warnings, and its
transmission method emitted a Python boolean-inversion deprecation warning.
These warnings originate in installed pyva source and do not change the
current calculation results; they are documented rather than suppressed.

## How to verify manually

There is no GUI yet. Run `python -m pytest tests/model/test_solvers.py`
to exercise all six real calculation methods, or run the full test suite.

## Comprehension questions

1. Why does a single-angle solver calculate `kx` using the sending fluid?
2. Why are impedance arrays complex while absorption and transmission
   arrays are real?
