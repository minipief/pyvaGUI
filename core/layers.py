"""Schichtmodelle für akustische Transfermatrix-Berechnungen.

Das Modul kapselt Fluid- und poroelastische Schichten, deren Umwandlung in
pyva-Objekte sowie ihre JSON-kompatible Serialisierung.
"""

import pyva.systems.infiniteLayers as iL

from core.materials import material_from_dict

class Layer:
    """Basisklasse einer Materialschicht im Absorberaufbau."""
    
    def __init__(self, material):
        """Speichert das Material der Schicht.

        Args:
            material: Akustisches Material der Schicht.
        """
        self.material = material
        
class FluidLayer(Layer):
    """Repräsentiert eine homogene Fluid- oder Absorberschicht."""
    
    def __init__(self, dicke, material):
        """Initialisiert eine Fluidschicht.

        Args:
            dicke: Schichtdicke in Metern.
            material: Fluides oder äquivalent-fluides Material.
        """
        super().__init__(material)
        self.dicke = dicke
        
    def to_pyva(self):
        """Erzeugt die entsprechende pyva-Schicht.

        Returns:
            Eine für das Transfermatrixmodell nutzbare pyva-Fluidschicht.
        """
        pyva_material = self.material.to_pyva()
        return iL.FluidLayer(self.dicke, pyva_material)
    
    def to_dict(self):
        """Serialisiert die Schicht einschließlich ihres Materials.

        Returns:
            JSON-kompatibles Dictionary der Fluidschicht.
        """
        return{
            "typ": "FluidLayer",
            "dicke": self.dicke,
            "material": self.material.to_dict()
        }

class PoroElasticLayer(Layer):
    """Repräsentiert eine poroelastische Schicht nach der Biot-Theorie."""

    def __init__(self, dicke, material):
        """Initialisiert eine poroelastische Schicht.

        Args:
            dicke: Schichtdicke in Metern.
            material: Poroelastisches Material der Schicht.
        """
        super().__init__(material)
        self.dicke = dicke

    def to_pyva(self):
        """Erzeugt die entsprechende pyva-Schicht.

        Returns:
            Eine für das Transfermatrixmodell nutzbare pyva-Schicht.
        """
        pyva_material = self.material.to_pyva()
        return iL.PoroElasticLayer(pyva_material, self.dicke)

    def to_dict(self):
        """Serialisiert die Schicht einschließlich ihres Materials.

        Returns:
            JSON-kompatibles Dictionary der poroelastischen Schicht.
        """
        return{
            "typ": "PoroElasticLayer",
            "dicke": self.dicke,
            "material": self.material.to_dict()
        }

def layer_from_dict(daten):
    """Rekonstruiert eine Schicht einschließlich ihres Materials.

    Args:
        daten: Serialisierte Schichtdaten mit Typ, Dicke und Material.

    Returns:
        Eine Fluid- oder poroelastische Schicht.

    Raises:
        KeyError: Wenn ein erforderlicher Eintrag fehlt.
        ValueError: Wenn der Schicht- oder Materialtyp unbekannt ist.
    """
    typ = daten["typ"]

    # Das eingebettete Material muss vor der typabhängigen Schicht entstehen.
    material = material_from_dict(daten["material"])

    if typ == "FluidLayer":
        return FluidLayer(dicke=daten["dicke"], material=material)
    elif typ == "PoroElasticLayer":
        return PoroElasticLayer(dicke=daten["dicke"], material=material)
    else:
        raise ValueError(f"Unbekannter Layertyp: {typ}")