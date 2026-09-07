import json
import os
from core.materials import material_from_dict


class MaterialBibliothek:
    """Eine persistente Sammlung von Materialien."""

    def __init__(self, materialien=None):
        self.materialien = materialien if materialien is not None else []

    def hinzufuegen(self, material):
        self.materialien.append(material)

    def entfernen(self, name):
        self.materialien = [m for m in self.materialien if m.name != name]

    def finde(self, name):
        """Gibt das Material mit diesem Namen zurück (oder None)."""
        for m in self.materialien:
            if m.name == name:
                return m
        return None
    
    def to_dict(self):
        return {"materialien": [m.to_dict() for m in self.materialien]}

    def speichern(self, pfad):
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def laden(pfad):
        with open(pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)
        materialien = [material_from_dict(m) for m in daten["materialien"]]
        return MaterialBibliothek(materialien)
    
    import os

def bibliothek_laden(pfad):
    """Lädt die Bibliothek, oder erstellt eine neue mit Standard-Materialien."""
    if os.path.exists(pfad):
        return MaterialBibliothek.laden(pfad)

    from core.materials import Fluid, EquivalentFluid
    bib = MaterialBibliothek()
    bib.hinzufuegen(Fluid("Luft"))
    bib.hinzufuegen(EquivalentFluid("Faser 30kg", porosity=0.98,
                                    flow_res=25000, tortuosity=1.02))
    bib.speichern(pfad)
    return bib