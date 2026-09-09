"""Projektmodell und JSON-Persistenz für vollständige Absorberaufbauten."""

import json

from core.layers import layer_from_dict
from core.environment import Umgebung, umgebung_from_dict

class Projekt:
    """Fasst Projektname, Schichtstapel und Berechnungsumgebung zusammen."""
    
    def __init__(self, name="Neues Projekt", layers=None, umgebung=None):
        """Initialisiert ein Projekt.

        Args:
            name: Anzeigename des Projekts.
            layers: Optionale Ausgangsliste von Schichten.
            umgebung: Optionale Berechnungsumgebung.
        """
        self.name = name
        self.layers = layers if layers is not None else []
        self.umgebung = umgebung if umgebung is not None else Umgebung()
        
    def layer_hinzufügen(self, layer):
        """Fügt dem Schichtstapel eine Schicht hinzu.

        Args:
            layer: Anzuhängende Schicht.

        Side Effects:
            Verändert den Schichtstapel des Projekts.
        """
        self.layers.append(layer)
        
    def layer_entfernen(self, index):
        """Entfernt eine Schicht anhand ihrer Position.

        Args:
            index: Nullbasierter Index der Schicht.

        Raises:
            IndexError: Wenn ``index`` außerhalb des Schichtstapels liegt.

        Side Effects:
            Verändert den Schichtstapel des Projekts.
        """
        del self.layers[index]
        
    def to_dict(self):
        """Serialisiert das vollständige Projekt.

        Returns:
            JSON-kompatibles Dictionary mit Umgebung und Schichten.
        """
        return{
            "name": self.name,
            "umgebung": self.umgebung.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers]
        }
    
    def speichern(self, pfad):
        """Schreibt das Projekt als UTF-8-kodierte JSON-Datei.

        Args:
            pfad: Zielpfad der Projektdatei.

        Raises:
            OSError: Wenn die Datei nicht geschrieben werden kann.
            TypeError: Wenn Projektdaten nicht JSON-serialisierbar sind.

        Side Effects:
            Erstellt oder überschreibt die Datei unter ``pfad``.
        """
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def laden(pfad):
        """Lädt ein Projekt aus einer JSON-Datei.

        Args:
            pfad: Pfad der Projektdatei.

        Returns:
            Rekonstruiertes Projekt.

        Raises:
            OSError: Wenn die Datei nicht gelesen werden kann.
            json.JSONDecodeError: Wenn die Datei kein gültiges JSON enthält.
            KeyError: Wenn erforderliche Projektdaten fehlen.
            ValueError: Wenn ein Material- oder Schichttyp unbekannt ist.

        Side Effects:
            Liest die Datei unter ``pfad``.
        """
        with open(pfad, "r", encoding="utf-8") as f:
            return projekt_from_dict(json.load(f))
    
def projekt_from_dict(daten):
    """Rekonstruiert ein Projekt aus serialisierten Daten.

    Args:
        daten: Dictionary mit Projektname, Umgebung und Schichten.

    Returns:
        Rekonstruiertes Projektmodell.

    Raises:
        KeyError: Wenn ein erforderlicher Eintrag fehlt.
        ValueError: Wenn ein Material- oder Schichttyp unbekannt ist.
    """
    umgebung = umgebung_from_dict(daten["umgebung"])
    layers = [layer_from_dict(layer) for layer in daten["layers"]]
    return Projekt(name=daten["name"], layers=layers, umgebung=umgebung)