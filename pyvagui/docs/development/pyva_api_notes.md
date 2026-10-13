# pyva API Notes

## Inspected environment

| Item | Value |
| --- | --- |
| Python | 3.13.7 |
| Distribution | `pyva-toolbox` 1.3.1 |
| Import package | `pyva` |
| Runtime | Workspace-selected `.venv` in the parent `Own` folder |

Signatures below were read with `inspect.signature()` from the installed
package. Source behavior was checked where return values or perforation
handling mattered. The installed version is the implementation reference.

## Materials

Module: `pyva.properties.materialClasses`

```text
Fluid(c0=343.0, rho0=1.23, eta=0.01, dynamic_viscosity=1.84e-05,
      kappa=1.4, Cp=1005.1, heat_conductivity=0.0257673, **kwargs)
EquivalentFluid(flow_res, porosity, tortuosity, rho_bulk, length_visc,
                length_therm, limp=True, c0=343.0, rho0=1.23, eta=0.0,
                dynamic_viscosity=1.84e-05, kappa=1.4, Cp=1005.1,
                heat_conductivity=0.0257673)
DelanyBazley(flow_res, c0=343.0, rho0=1.23, eta=0.0,
             dynamic_viscosity=1.84e-05, kappa=1.4, Cp=1005.1,
             heat_conductivity=0.0257673, miki=False)
IsoMat(E=71000000000.0, rho0=2700.0, nu=0.34, eta=0.01, **params)
PoroElasticMat(solid_mat, flow_res, porosity, tortuosity, length_visc,
               length_therm, limp=False, c0=343.0, rho0=1.23,
               dynamic_viscosity=1.84e-05, kappa=1.4, Cp=1005.1,
               heat_conductivity=0.0257673)
```

`Fluid.wavenumber(self, omega)` returns the complex wavenumber and is used
to calculate the in-plane wavenumber for a single incidence angle.

## Structural and infinite layers

Module: `pyva.properties.structuralPropertyClasses`

```text
PlateProp(thickness, material)
```

Module: `pyva.systems.infiniteLayers`

```text
FluidLayer(thickness, fluid=<class 'pyva.properties.materialClasses.Fluid'>)
PoroElasticLayer(poroelasticmat, thickness)
SolidLayer(plate_prop)
PlateLayer(plate_prop, perforation=None)
MassLayer(thickness, rho, perforation=None)
ResistiveLayer(thickness, impedance)
PerforatedLayer(thickness, hole_radius,
                fluid=Fluid(c0=343.0, rho0=1.23, eta=0.01),
                pattern='square', alpha=2.0, **kwargs)
```

`PlateLayer` and `MassLayer` take a perforation object, not radius and
distance directly. Construct it with `PerforatedLayer`; `distance` is a
supported keyword in `**kwargs`. For the default square pattern, pyva
calculates porosity as `pi * hole_radius**2 / distance**2`. The porous
layer object is passed as the `perforation` argument.

`pyva.models.TMmodel(layers, **kwargs)` accepts a sequence of layer
objects. Its constructor is in `pyva.models`, not
`pyva.systems.infiniteLayers`.

## TMmodel solver methods

All methods below belong to `pyva.models.TMmodel`. Angles passed as
`theta_max` are in radians. `signal=False` returns an ndarray; the
default `signal=True` returns a `pyva.data.matrixClasses.Signal` for
the methods that support that option.

```text
absorption(self, omega, kx,
         in_fluid=Fluid(c0=343.0,rho0=1.23,eta=0.01), ID=1,
         boundary_condition='fixed', allard=False, signal=True,
         out_fluid=Fluid(c0=343.0,rho0=1.23,eta=0.01))
absorption_diffuse(self, omega, theta_max=1.3613568165555772,
               theta_step=0.017453292519943295,
               in_fluid=Fluid(c0=343.0,rho0=1.23,eta=0.01),
                   ID=1, boundary_condition='fixed', allard=False,
               signal=True,
               out_fluid=Fluid(c0=343.0,rho0=1.23,eta=0.01))
transmission_coefficient(
    self, omega, kx,
    fluids=(Fluid(c0=343.0,rho0=1.23,eta=0.01),
          Fluid(c0=343.0,rho0=1.23,eta=0.01)),
    ID=0, signal=True)
transmission_diffuse(self, omega, theta_max=1.3613568165555772,
                     theta_step=0.017453292519943295,
                 fluids=(Fluid(c0=343.0,rho0=1.23,eta=0.01),
                       Fluid(c0=343.0,rho0=1.23,eta=0.01)), ID=0,
                     signal=True, allard=False)
transmission_allard(self, omega, kx=0.0, ID=1,
                fluids=(Fluid(c0=343.0,rho0=1.23,eta=0.01),
                      Fluid(c0=343.0,rho0=1.23,eta=0.01)),
                signal=True, plot=0)
impedance(self, omega, kx=0.0, ID=1, boundary_condition='fixed',
        signal=True,
        out_fluid=Fluid(c0=343.0,rho0=1.23,eta=0.01))
```

`transmission_allard` does not accept a `boundary_condition` argument.
For absorption, `in_fluid` is the incident fluid; transmission methods
receive a two-fluid tuple.

## Frequency helpers

Module: `pyva.useful`

```text
get_n_th_oct_frequencies(f_min, f_max, N=3)
get_3rd_oct_axis_labels(range='SEA')
```

`get_n_th_oct_frequencies` returns `(fc, flim)`: center frequencies and
one-longer band-limit frequencies. `N` is bands per octave, not a
requested number of points. `get_3rd_oct_axis_labels` returns fixed
standard frequencies and labels for either `range='SEA'` or
`range='hybrid'`; it does not generate labels for arbitrary input
frequencies.

## Documentation comparison

The online pyva documentation was checked on 2026-10-13. The published
API and installed signatures agree for the inspected layer constructors,
`PerforatedLayer`, `TMmodel`, and frequency helpers. The online guide
also demonstrates `PerforatedLayer(..., distance=...)` and passing it
to `PlateLayer(perforation=...)`.

One documentation limitation matters to callers: some API pages describe
the result as a `Signal`, although the methods return arrays when
`signal=False`; the installed source and examples confirm that option.
No installed/documented signature discrepancy was found for the APIs
listed above.

## Phase 3 runtime check

All six `TMmodel` solver methods were called with `signal=False` using a
0.1 m equivalent-fluid layer and nine logarithmic frequencies from 100 Hz
to 10 kHz. Each returned a finite one-dimensional array. Absorption and
transmission values were between zero and one; impedance values were
complex. The diffuse methods and transmission method emitted deprecation
warnings from pyva 1.3.1 under the installed Python/NumPy environment.
