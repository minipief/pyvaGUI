"""Numerische Berechnung diffuser Absorptionsgrade mit pyva."""

import numpy as np
import pyva.models as mds


def rechne(projekt):
    """Berechnet die Absorptionskurve für ein komplettes Projekt.

    Args:
        projekt: Projekt mit Schichtstapel und Berechnungsumgebung.

    Returns:
        Tupel aus Frequenzstützstellen in Hertz und den zugehörigen diffusen
        Absorptionsgraden.

    Raises:
        ValueError: Wenn Frequenzparameter oder Schichtdaten ungültig sind.
        Exception: Von pyva ausgelöste Modellierungs- und Berechnungsfehler.
    """
    umg = projekt.umgebung
    frequenzen = np.logspace(np.log10(umg.f_min),
                             np.log10(umg.f_max),
                             umg.anzahl_punkte)
    omega = 2 * np.pi * frequenzen
    
    theta_max = np.deg2rad(projekt.umgebung.theta_max_grad)

    pyva_layers = [layer.to_pyva() for layer in projekt.layers]

    # pyva wertet den gesamten Schichtstapel als Transfermatrixmodell aus.
    modell = mds.TMmodel(tuple(pyva_layers))
    absorption = modell.absorption_diffuse(omega, theta_max=theta_max,
                                           signal=False)

    return frequenzen, absorption