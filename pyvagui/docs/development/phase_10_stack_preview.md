# Phase 10 - Stack Preview

## Goal

Show the current layup as a compact vertical cross-section beside the
layer table, with the incident side at the top.

## What was built

- `pyvagui/gui/layup_preview.py`: custom QWidget that paints the material
  stack, labels, and thin-layer summary.
- `pyvagui/gui/layup_editor.py`: side-by-side splitter and model-driven
  preview refresh.
- `tests/gui/test_layup_preview.py`: geometry, thin-layer, and rendered
  pixel tests.
- Expanded `pyqt_primer.md`; updated design decisions and changelog.

## How it works

The preview calculates a rectangle for each layer in incident-first
order, scales the remaining height by the layer thickness, and reserves
a minimum height so thin layers remain visible. Material families select
distinct colors. If a rectangle cannot hold its label, the label is
listed below the stack. `paintEvent` draws the current layup each time
Qt requests a repaint.

## Concepts used

See `pyqt_primer.md`: QPainter and `paintEvent`.

## Decisions

- D-020: color by material family and draw the incident layer at the top.
- D-021: preserve thin layers and move their labels below the stack.

## Tests

- Focused preview tests: 3 passed, including a rendered-pixel color check.
- Full `python -m pytest`: 126 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

Strict proportional scaling made sufficiently thin layers effectively
invisible. The preview now assigns a minimum height first, distributes
the remaining height by thickness, and lists labels that do not fit.

## How to verify manually

Run `python -m pyvagui`, open or create a layup, and compare the preview
with the table. Change thicknesses, material types, and ordering; the
stack should refresh with the first layer at the incident-side top.

## Comprehension questions

1. Why does the preview use a minimum layer height instead of strict
   proportional scaling for every layer?
2. When does `paintEvent` run, and what does `QPainter` draw?
