# pyvaGUI

Desktop application for creating infinite-layer models and calculating
absorption, transmission, and surface impedance with
[pyva](https://pyva.eu).

## Features

- Project materials, ordered layups, and reusable solver presets.
- Fluid, equivalent-fluid, Delany-Bazley, isotropic-solid, and poroelastic
    material specifications.
- Single-angle and diffuse absorption/transmission, Allard transmission,
    and impedance calculations.
- Log-frequency plots with one curve per layup; impedance also supports
    magnitude, phase, real, and imaginary views.
- CSV result export and PNG/SVG figure export.

For the architecture and complete user workflow, see
[`docs/development/overview.md`](docs/development/overview.md).

## Installation (development)

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
python -m pyvagui
```

## Basic workflow

1. Create a project and add materials with **Edit > New material**. The
     bundled material library is available under **Library > Open library**.
2. Choose **Edit > New layup**, add layers, then save the layup.
3. Choose **Edit > New solver**, select fluids, frequencies, an angle,
     boundary condition, and one or more layups.
4. Open the solver's result tab and press **Run**. Progress and messages
     appear in the status bar and application log.
5. Use **Export...** on the result tab to save CSV data or a PNG/SVG plot.

Projects are saved as versioned JSON. Materials in the user library are
stored separately. Calculated result arrays are transient and are not
written into project files.

Most model lengths use SI meters. The layup and perforation dialogs show
lengths in millimeters and convert them to meters when saving.

## Test

```powershell
python -m pytest
flake8
```
