"""Umgebungsparameter für die akustische Berechnung.

Das Modul beschreibt das umgebende Fluid sowie Frequenz- und Winkelbereich
einer Berechnung und stellt die Rekonstruktion aus JSON-Daten bereit.
"""

from core.materials import Fluid, material_from_dict

class Umgebung:
    """Bündelt die Randbedingungen eines zu berechnenden Schichtstapels.

    Die Umgebung enthält das anregende Fluid, die logarithmisch abzutastende
    Frequenzspanne und den maximalen Einfallswinkel der diffusen Auswertung.
    """
    
    def __init__(self, fluid=None, anzahl_punkte=100, f_min=50.0, f_max=10000.0, theta_max_grad=90.0):
        """Initialisiert die Berechnungsumgebung.

        Args:
            fluid: Umgebendes Fluid. Bei ``None`` wird Luft verwendet.
            anzahl_punkte: Anzahl der Frequenzstützstellen.
            f_min: Untere Grenzfrequenz in Hertz.
            f_max: Obere Grenzfrequenz in Hertz.
            theta_max_grad: Maximaler Einfallswinkel in Grad.
        """
        self.fluid = fluid if fluid is not None else Fluid("Luft")
        self.anzahl_punkte = anzahl_punkte
        self.f_min = f_min
        self.f_max = f_max
        self.theta_max_grad = theta_max_grad
        
    def to_dict(self):
        """Serialisiert die Umgebungsparameter.

        Returns:
            JSON-kompatibles Dictionary einschließlich des Fluids.
        """
        return {
            "fluid": self.fluid.to_dict(),
            "anzahl_punkte": self.anzahl_punkte,
            "f_min": self.f_min,
            "f_max": self.f_max,
            "theta_max_grad": self.theta_max_grad,
        }


def umgebung_from_dict(daten):
    """Rekonstruiert eine Umgebung aus serialisierten Daten.

    Args:
        daten: Dictionary mit Fluid-, Frequenz- und Winkelparametern.

    Returns:
        Rekonstruierte Berechnungsumgebung.

    Raises:
        KeyError: Wenn ein erforderlicher Eintrag fehlt.
        ValueError: Wenn der gespeicherte Materialtyp unbekannt ist.
    """
    fluid = material_from_dict(daten["fluid"])
    return Umgebung(fluid=fluid,
                    anzahl_punkte=daten["anzahl_punkte"],
                    f_min=daten["f_min"], f_max=daten["f_max"],
                    theta_max_grad=daten["theta_max_grad"])