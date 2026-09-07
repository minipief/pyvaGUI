import json

from core.layers import layer_from_dict
from core.environment import Umgebung, umgebung_from_dict

class Projekt:
    """Ein komplettes Projekt: Schichtstapel + Umgebung"""
    
    def __init__(self, name="Neues Projekt", layers=None, umgebung=None):
        self.name = name
        self.layers = layers if layers is not None else []
        self.umgebung = umgebung if umgebung is not None else Umgebung()
        
    def layer_hinzufügen(self, layer):
        self.layers.append(layer)
        
    def layer_entfernen(self, index):
        del self.layers[index]
        
    def to_dict(self):
        return{
            "name": self.name,
            "umgebung": self.umgebung.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers]
        }
    
    def speichern(self, pfad):
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def laden(pfad):
        with open(pfad, "r", encoding="utf-8") as f:
            return projekt_from_dict(json.load(f))
    
def projekt_from_dict(daten):
    umgebung = umgebung_from_dict(daten["umgebung"])
    layers = [layer_from_dict(layer) for layer in daten["layers"]]
    return Projekt(name=daten["name"], layers=layers, umgebung=umgebung)