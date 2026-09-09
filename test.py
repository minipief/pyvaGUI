"""Demonstriert Laden, Erweitern und Speichern einer Materialbibliothek.

Das manuell ausführbare Testskript legt bei Bedarf ``bibliothek.json`` an,
gibt die vorhandenen Materialnamen aus und ergänzt ein äquivalentes Fluid.

Side Effects:
    Liest, erstellt oder überschreibt ``bibliothek.json`` und schreibt die
    Materialnamen auf die Standardausgabe.
"""

from core.library import bibliothek_laden
from core.materials import EquivalentFluid

# 1. Lauf: legt die Datei an
bib = bibliothek_laden("bibliothek.json")
print("Materialien:", [m.name for m in bib.materialien])

# Ein neues Material dazu und speichern
bib.hinzufuegen(EquivalentFluid("Schaum", porosity=0.95,
                                flow_res=12000, tortuosity=1.1))
bib.speichern("bibliothek.json")