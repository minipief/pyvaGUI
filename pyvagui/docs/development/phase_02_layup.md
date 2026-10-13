# Phase 02 - Layup Model

## Goal

Represent an ordered layer stack as plain Python data, validate it, and
convert valid layers into pyva infinite-layer objects.

## What was built

- `pyvagui/model/layup.py`: `LayerType`, `PerforationSpec`, `LayerSpec`,
  and `Layup`, including validation, serialization, and pyva conversion.
- `tests/model/test_layup.py`: focused tests for allowed material types,
  validation, JSON-ready round trips, ordering, and pyva construction.
- Updated the development decisions, resolved question, deviations,
  and changelog records.

## How it works

The layup stores material IDs and SI-unit thicknesses. A layer resolves
its material from the project dictionary, checks the selected
representation, then constructs the matching pyva layer. A layup validates
all rows and passes them to `TMmodel` in stored order; the first layer is
the incident side.

```text
Layup.layers -> LayerSpec.validate(materials)
             -> LayerSpec.build(materials)
             -> pyva layer objects in the same order
             -> pyva.models.TMmodel
```

For a perforated plate or mass layer, the host thickness is passed to
`PerforationSpec.to_pyva(thickness)` because pyva includes it in the
perforation impedance calculation.

## Concepts used

- `Enum` stores stable string values for layer types; see
  `pyqt_primer.md` (no PyQt concepts yet).
- Dataclasses hold serializable model values without GUI dependencies.
- `match` selects the pyva layer implementation from `LayerType`.

## Decisions

- D-002: represent perforations as radius and spacing values.
- D-003: retain all frequency fields and use logarithmic spacing in
  Phase 3; the samples are not guaranteed to be exact third-octave bands.
- D-004: pass host thickness to the pyva perforation constructor.

## Tests

- `python -m pytest tests/model/test_layup.py`: 23 passed.
- Full `python -m pytest`: 26 passed.
- Full `flake8`: passed with no findings.

## Problems and solutions

The task description names `PerforationSpec.to_pyva()` without specifying
its thickness input. Installed pyva source showed that thickness affects
both the transfer resistance and reactance. The method therefore accepts
the host layer thickness, which is supplied by `LayerSpec.build()`.

## How to verify manually

There is no GUI yet. Run `python -m pytest tests/model/test_layup.py` to
exercise layer validation, serialization, reordering, and conversion to
pyva objects.

## Comprehension questions

1. Why does `LayerSpec` store a material ID instead of a pyva material?
2. Why must a perforation use the thickness of the plate or mass layer?
