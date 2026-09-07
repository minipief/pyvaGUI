import numpy as np
import pyva.models as mds


def rechne(projekt):
    """Berechnet die Absorptionskurve für ein komplettes Projekt.

    Gibt zwei Arrays zurück: (frequenzen, absorption).
    """
    umg = projekt.umgebung
    frequenzen = np.logspace(np.log10(umg.f_min),
                             np.log10(umg.f_max),
                             umg.anzahl_punkte)
    omega = 2 * np.pi * frequenzen
    
    theta_max = np.deg2rad(projekt.umgebung.theta_max_grad)

    pyva_layers = [layer.to_pyva() for layer in projekt.layers]

    modell = mds.TMmodel(tuple(pyva_layers))
    absorption = modell.absorption_diffuse(omega, theta_max=theta_max,
                                           signal=False)

    return frequenzen, absorption