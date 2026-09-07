import pyva.systems.infiniteLayers as iL

from core.materials import material_from_dict

class Layer:
    """Basisklasse für alle Schichten"""
    
    def __init__(self, material):
        self.material = material
        
class FluidLayer(Layer):
    """Eine Fluid-/Absorberschicht mit einer Dicke"""
    
    def __init__(self, dicke, material):
        super().__init__(material)
        self.dicke = dicke
        
    def to_pyva(self):
        pyva_material = self.material.to_pyva()
        return iL.FluidLayer(self.dicke, pyva_material)
    
    def to_dict(self):
        return{
            "typ": "FluidLayer",
            "dicke": self.dicke,
            "material": self.material.to_dict()
        }

def layer_from_dict(daten):
    """Baut das richtige Layer-Objekt (inkl. eingebettetem Material)."""
    typ = daten["typ"]

    # Zuerst das eingebettete Material bauen (Factory aus materials.py!)
    material = material_from_dict(daten["material"])

    if typ == "FluidLayer":
        return FluidLayer(dicke=daten["dicke"], material=material)
    else:
        raise ValueError(f"Unbekannter Layertyp: {typ}")