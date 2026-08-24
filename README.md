# pyvaGUI – Framework (PyQt5)

An extensible GUI framework for the vibroacoustics library
[**pyva**](https://www.pyva.eu). The application allows

- entering **all parameters** of arbitrary pyva materials
  (Fluid, IsoMat, EquivalentFluid, PoroElasticMat, DelanyBazley),
- building ordered **layups** from infinite layers
  (FluidLayer, SolidLayer, PoroElasticLayer, PlateLayer,
  ImperviousScreenLayer, PerforatedLayer, MassLayer),
- computing the **absorption** and **transmission coefficients** via
  `pyva.models.TMmodel` and displaying them over frequency in an
  embedded Matplotlib plot.

## Installation

```bash
pip install -r requirements.txt
```

## Start

```bash
python app.py
```

The menu **Project → Load example (fibre absorber)** loads a simple 10-cm
fibre absorber. Afterwards, click **Compute** in the **3 · Results** tab.

## Architecture (Data-driven)

The core is the **declarative registry** (`pyva_gui/registry.py`): each
pyva class is described once as a list of `ParamSpec` objects. The
generic form widget (`ParameterForm`) automatically generates the
input mask from it. Supporting a new pyva class therefore only requires **one
entry in the registry** – no new GUI code.

| Module | Purpose |
|--------|---------|
| `registry.py` | Description of all pyva classes and their parameters |
| `factories.py` | Instantiates the actual pyva objects (backend lazy import) |
| `store.py` | Shared project model, serializable as JSON |
| `widgets.py` | Generic, registry-driven input form |
| `plotting.py` | Matplotlib canvas + frequency axis |
| `compute.py` | TMM evaluation in a background thread |
| `main_window.py / tabs/` | The interface (3 tabs) |

```
Materials tab  ─►  Lay-up tab  ─►  Results tab
 (Materials)      (Layup)          (α & τ over f)
        │                │                │
        └──────  ProjectStore  ──────────┘
                       │
                   factories  ─►  pyva (TMmodel)
```

## Workflow

- **Materials**: choose a type, assign a name, enter all parameters,
  _Add / Update material_.
- **Lay-up**: choose a layer type, reference a material, set thickness etc.,
  _Add layer_. Order top = incident side.
- **Results**: choose the frequency range (f min/max, points), the maximum
  angle of incidence θ max and the desired quantities, _Compute_.

## Extension

New materials/layers: add an entry in `MATERIALS` or `LAYERS` in
`registry.py` and add the matching branch in `factories.build_material` /
`factories.build_layer`. Everything else (form, saving, references)
works automatically.

## Notes

- The GUI framework itself only requires PyQt5, matplotlib, numpy. The
  pyva backend is imported only when **Compute** is clicked.
- The diffuse evaluation uses
  `TMmodel.absorption_diffuse(omega, theta_max=…, signal=False)` and
  `TMmodel.transmission_diffuse(…)`, respectively.
- The transmission coefficient τ can be displayed either directly or as
  transmission loss TL = −10·log₁₀(τ) in dB.
