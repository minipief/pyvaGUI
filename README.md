# pyvaGUI – Framework (PyQt6)

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
python pyvaGUI.py
```