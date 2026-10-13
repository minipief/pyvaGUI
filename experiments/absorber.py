"""First pyva experiment: sound absorption of a fibre absorber.

This script is not part of the application. It shows how pyva
calculates the diffuse absorption of a fibre layer in front of a
hard wall.
"""

from cProfile import label
from traceback import print_tb

import matplotlib.pyplot as plt
import numpy as np

import pyva.models as mds
import pyva.properties.materialClasses as matC
import pyva.systems.infiniteLayers as iL

# 1. Frequencies: 100 values from 10 Hz to 10 kHz (logarithmic).
#    pyva works with the angular frequency omega = 2 * pi * f.
frequency = np.logspace(1, 4, 100)
omega = 2 * np.pi * frequency

# 2. Material: a fibre material described as an equivalent fluid.
fibre = matC.EquivalentFluid(
    porosity=0.98,
    flow_res=25000.0,
    tortuosity=1.02,
    length_visc=90.0e-6,
    length_therm=180.0e-6,
    rho_bulk=0.98 * 1.20 + 30.0,
    rho0=1.208,
    dynamic_viscosity=1.81e-5,
)

# 3. Layers: the same material with two different thicknesses [m].
fibre_10cm = iL.FluidLayer(0.10, fibre)
fibre_20cm = iL.FluidLayer(0.20, fibre)
fibre_5cm = iL.FluidLayer(0.05, fibre)

# 4. Layups: a TMmodel gets a tuple of layers (here only one each).
tmm_10cm = mds.TMmodel((fibre_10cm,))
tmm_20cm = mds.TMmodel((fibre_20cm,))
tmm_5cm = mds.TMmodel((fibre_5cm,))

# 5. Solver: diffuse absorption, angles from 0 to 90 degrees.
alpha_10cm = tmm_10cm.absorption_diffuse(
    omega, theta_max=np.pi / 2, signal=False
)
alpha_20cm = tmm_20cm.absorption_diffuse(
    omega, theta_max=np.pi / 2, signal=False
)
alpha_5cm = tmm_5cm.absorption_diffuse(
	omega, theta_max=np.pi / 2, signal=False
)

print(type(alpha_10cm))

# 6. Plot the results.
plt.plot(frequency, alpha_10cm, label="10 cm fibre")
plt.plot(frequency, alpha_20cm, label="20 cm fibre")
plt.plot(frequency, alpha_5cm, label="5 cm fibre")
plt.xscale("log")
plt.xlabel("Frequency [Hz]")
plt.ylabel("Absorption coefficient [-]")
plt.legend()
plt.grid(True)
plt.show()