"""Persistente Verwaltung der in pyvaGUI verfügbaren Materialien."""

import json
import os
from core.materials import material_from_dict


class MaterialBibliothek:
    """Verwaltet Materialien und ihre referenzielle Konsistenz."""

    def __init__(self, materialien=None):
        """Initialisiert die Bibliothek.

        Args:
            materialien: Optionale Ausgangsliste von Materialien.
        """
        self.materialien = materialien if materialien is not None else []

    def hinzufuegen(self, material):
        """Fügt ein Material am Ende der Bibliothek ein.

        Args:
            material: Hinzuzufügendes Material.

        Side Effects:
            Verändert die Materialliste der Bibliothek.
        """
        self.materialien.append(material)

    def entfernen(self, name):
        """Entfernt alle Materialien mit dem angegebenen Namen.

        Args:
            name: Name der zu entfernenden Materialien.

        Side Effects:
            Ersetzt die interne Materialliste durch eine gefilterte Liste.
        """
        self.materialien = [m for m in self.materialien if m.name != name]

    def aktualisieren(self, alter_name, neues_material):
        """Ersetzt ein Material unter Beibehaltung der Objektidentität.

        So bleiben Referenzen anderer Materialien (z.B. solid_mat in
        PoroElasticMat) auch nach dem Bearbeiten gültig.

        Args:
            alter_name: Bisheriger Name des Materials.
            neues_material: Material mit den neuen Typ- und Attributwerten.

        Returns:
            Das in der Bibliothek aktualisierte Materialobjekt.

        Raises:
            ValueError: Wenn kein Material mit ``alter_name`` existiert.

        Side Effects:
            Ändert Klasse und Attribute des vorhandenen Objekts direkt.
        """
        vorhandenes = self.finde(alter_name)
        if vorhandenes is None:
            raise ValueError(f"Material '{alter_name}' nicht gefunden.")
        vorhandenes.__class__ = neues_material.__class__
        vorhandenes.__dict__ = neues_material.__dict__
        return vorhandenes

    def finde(self, name):
        """Sucht ein Material anhand seines Namens.

        Args:
            name: Exakt zu vergleichender Materialname.

        Returns:
            Das erste passende Material oder ``None``.
        """
        for m in self.materialien:
            if m.name == name:
                return m
        return None
    
    def to_dict(self):
        """Serialisiert alle Materialien.

        Returns:
            JSON-kompatibles Dictionary der Bibliothek.
        """
        return {"materialien": [m.to_dict() for m in self.materialien]}

    def speichern(self, pfad):
        """Schreibt die Bibliothek als UTF-8-kodierte JSON-Datei.

        Args:
            pfad: Zielpfad der Bibliotheksdatei.

        Raises:
            OSError: Wenn die Datei nicht geschrieben werden kann.
            TypeError: Wenn Materialdaten nicht JSON-serialisierbar sind.

        Side Effects:
            Erstellt oder überschreibt die Datei unter ``pfad``.
        """
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def laden(pfad):
        """Lädt eine Materialbibliothek aus einer JSON-Datei.

        Args:
            pfad: Pfad der einzulesenden Bibliotheksdatei.

        Returns:
            Rekonstruierte Bibliothek mit vereinheitlichten Referenzen.

        Raises:
            OSError: Wenn die Datei nicht gelesen werden kann.
            json.JSONDecodeError: Wenn die Datei kein gültiges JSON enthält.
            KeyError: Wenn erforderliche Daten fehlen.
            ValueError: Wenn ein Materialtyp unbekannt ist.

        Side Effects:
            Liest die Datei unter ``pfad``.
        """
        with open(pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)
        materialien = [material_from_dict(m) for m in daten["materialien"]]
        bibliothek = MaterialBibliothek(materialien)
        bibliothek._solid_referenzen_vereinheitlichen()
        return bibliothek

    def _solid_referenzen_vereinheitlichen(self):
        """Lässt PoroElasticMat.solid_mat auf das gleichnamige Bibliotheksmaterial zeigen.

        Beim Laden aus JSON wird solid_mat als eingebettete Kopie rekonstruiert.
        Damit das Bearbeiten eines Solid-Materials auch nach dem Neuladen bei
        allen darauf verweisenden PoroElasticMat-Materialien ankommt, wird hier
        auf die kanonische Instanz aus der Bibliothek umgehängt.

        Side Effects:
            Ersetzt eingebettete Rahmenmaterialien durch Bibliotheksobjekte.
        """
        from core.materials import PoroElasticMat
        for material in self.materialien:
            if isinstance(material, PoroElasticMat):
                kanonisch = self.finde(material.solid_mat.name)
                if kanonisch is not None:
                    material.solid_mat = kanonisch


def bibliothek_laden(pfad):
    """Lädt die Bibliothek oder legt eine Standardbibliothek an.

    Args:
        pfad: Pfad der persistenten Bibliotheksdatei.

    Returns:
        Geladene oder neu erzeugte Materialbibliothek.

    Raises:
        OSError: Wenn die Bibliotheksdatei nicht gelesen oder angelegt werden kann.
        json.JSONDecodeError: Wenn eine vorhandene Datei ungültiges JSON enthält.
        KeyError: Wenn erforderliche Materialdaten fehlen.
        ValueError: Wenn ein gespeicherter Materialtyp unbekannt ist.

    Side Effects:
        Erstellt bei fehlender Datei eine JSON-Bibliothek mit Standardmaterialien.
    """
    if os.path.exists(pfad):
        return MaterialBibliothek.laden(pfad)

    from core.materials import Fluid, EquivalentFluid, DelanyBazley, Solid, PoroElasticMat
    bib = MaterialBibliothek()
    bib.hinzufuegen(Fluid("Luft"))
    bib.hinzufuegen(EquivalentFluid("Faser 30kg", porosity=0.98,
                                    flow_res=25000, tortuosity=1.02))
    bib.hinzufuegen(DelanyBazley("Faser (Delany-Bazley)", flow_res=25000))
    aluminium = Solid("Aluminium")
    bib.hinzufuegen(aluminium)
    bib.hinzufuegen(PoroElasticMat("Schaum (poroelastisch)", solid_mat=aluminium,
                                   flow_res=25000, porosity=0.98, tortuosity=1.02,
                                   length_visc=90e-6, length_therm=180e-6))
    bib.speichern(pfad)
    return bib