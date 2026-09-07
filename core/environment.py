from core.materials import Fluid, material_from_dict

class Umgebung:
    """Die Umgebungsbedingungen um den Schichtstapel"""
    
    def __init__(self, fluid=None, anzahl_punkte=100, f_min=50.0, f_max=10000.0, theta_max_grad=90.0):
        self.fluid = fluid if fluid is not None else Fluid("Luft")
        self.anzahl_punkte = anzahl_punkte
        self.f_min = f_min
        self.f_max = f_max
        self.theta_max_grad = theta_max_grad
        
    def to_dict(self):
        return {
            "fluid": self.fluid.to_dict(),
            "anzahl_punkte": self.anzahl_punkte,
            "f_min": self.f_min,
            "f_max": self.f_max,
            "theta_max_grad": self.theta_max_grad,
        }


def umgebung_from_dict(daten):
    fluid = material_from_dict(daten["fluid"])
    return Umgebung(fluid=fluid,
                    anzahl_punkte=daten["anzahl_punkte"],
                    f_min=daten["f_min"], f_max=daten["f_max"],
                    theta_max_grad=daten["theta_max_grad"])