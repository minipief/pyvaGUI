# Deviations and API Clarifications

Implementation adjustments from the initial requirements are listed below.

## Verified pyva details

- `TMmodel` is imported from `pyva.models`, not
  `pyva.systems.infiniteLayers` as the layer classes are.
- A perforation is a `PerforatedLayer` object. Its installed constructor
  accepts `hole_radius` and a `distance` keyword, matching the intended
  `PerforationSpec` fields.
- The frequency helper returns third-octave centers and band limits; it
  does not accept a number-of-points argument.

## Phase 2 clarifications

- `PerforationSpec.to_pyva` accepts the host layer's thickness. pyva uses
  that value in its perforation impedance formulas, so a no-argument
  method would require an arbitrary or duplicated thickness.

## Phase 3 clarifications

- Frequencies retain all three settings and use logarithmic spacing, as
  requested by the user. Samples are therefore not exact third-octave
  centers; see decision D-003.

## Phase 8 library compatibility

- Existing library JSON may contain `fluid_material_id`,
  `frame_material_id`, or the old `poro_elastic` type name. Loading and
  importing resolve those known fields in memory, copy base fluid
  properties from the referenced fluid, and normalize the frame reference.
  The original file is not rewritten during load.
