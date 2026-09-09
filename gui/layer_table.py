"""Tabellen-Widget zur interaktiven Zusammenstellung eines Schichtstapels."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView
)
from gui.material_menu import MaterialAuswahl


class LayerTable(QWidget):
    """Bearbeitet Materialien und Dicken eines geordneten Schichtstapels.

    Aufgabe:
        Das Widget verwaltet die Reihenfolge der zu berechnenden Schichten und
        übersetzt Tabellenzeilen in fachliche Schichtmodelle.

    Wichtige Bedienelemente:
        Eine zweispaltige Tabelle enthält je Zeile eine ``MaterialAuswahl`` und
        eine editierbare Dicke. Schaltflächen fügen Zeilen hinzu oder entfernen
        die aktuell markierte Zeile.

    Datenfluss:
        Materialien stammen aus der ``MaterialBibliothek``. :meth:`zu_layern`
        liest Auswahl und Dicke und erzeugt ``FluidLayer``- oder
        ``PoroElasticLayer``-Objekte. :meth:`zeile_aus_layer` bildet den
        umgekehrten Weg beim Laden eines Projekts ab.

    Signale und Slots:
        ``add_knopf.clicked`` ruft :meth:`zeile_hinzufuegen` auf;
        ``del_knopf.clicked`` ruft :meth:`zeile_entfernen` auf.

    Modulinteraktion:
        Nutzt :class:`gui.material_menu.MaterialAuswahl`, Modelle aus
        :mod:`core.layers` und Materialien aus :mod:`core.materials`.
    """

    def __init__(self, bibliothek):
        """Initialisiert die leere Schichttabelle.

        Args:
            bibliothek: Materialquelle für die Auswahlmenüs jeder Zeile.

        Side Effects:
            Baut Tabelle, Schaltflächen und Qt-Signalverbindungen auf.
        """
        super().__init__()
        self.bibliothek = bibliothek

        self.tabelle = QTableWidget(0, 2)
        self.tabelle.setHorizontalHeaderLabels(["Material", "Dicke [m]"])

        # Die Materialauswahl erhält den variablen, die Dicke den minimalen Platz.
        header = self.tabelle.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        self.add_knopf = QPushButton("+ Schicht")
        self.del_knopf = QPushButton("– Schicht")

        knopf_reihe = QHBoxLayout()
        knopf_reihe.addWidget(self.add_knopf)
        knopf_reihe.addWidget(self.del_knopf)

        layout = QVBoxLayout()
        layout.addWidget(self.tabelle)
        layout.addLayout(knopf_reihe)
        self.setLayout(layout)

        self.add_knopf.clicked.connect(self.zeile_hinzufuegen)
        self.del_knopf.clicked.connect(self.zeile_entfernen)
        
    def zeile_hinzufuegen(self):
        """Fügt eine Schichtzeile mit Standarddicke hinzu.

        Side Effects:
            Erweitert die Tabelle und erzeugt ein Materialauswahlmenü aus dem
            aktuellen Stand der Bibliothek.
        """
        zeile = self.tabelle.rowCount()
        self.tabelle.insertRow(zeile)

        auswahl = MaterialAuswahl()
        auswahl._menu_aufbauen(self.bibliothek.materialien)
        self.tabelle.setCellWidget(zeile, 0, auswahl)
        self.tabelle.setItem(zeile, 1, QTableWidgetItem("0.1"))

    def zeile_entfernen(self):
        """Entfernt die aktuell markierte Tabellenzeile.

        Side Effects:
            Verändert die Tabelle, sofern eine Zeile ausgewählt ist.
        """
        zeile = self.tabelle.currentRow()
        if zeile >= 0:
            self.tabelle.removeRow(zeile)
            
    def zu_layern(self):
        """Erzeugt Fachmodelle aus den aktuellen Tabellenzeilen.

        Returns:
            Geordnete Liste von Fluid- und poroelastischen Schichten.

        Raises:
            ValueError: Wenn keine Schicht existiert, ein Material fehlt, eine
                Dicke ungültig ist oder ein reiner Festkörper gewählt wurde.
        """
        from core.layers import FluidLayer, PoroElasticLayer
        from core.materials import PoroElasticMat, Solid

        if self.tabelle.rowCount() == 0:
            raise ValueError("Es wurde keine Schicht hinzugefügt.")

        layers = []
        for zeile in range(self.tabelle.rowCount()):
            auswahl = self.tabelle.cellWidget(zeile, 0)
            material = auswahl.ausgewaehltes_material

            if material is None:
                raise ValueError(f"In Zeile {zeile + 1} wurde kein Material gewählt.")

            dicke = float(self.tabelle.item(zeile, 1).text())
            if isinstance(material, PoroElasticMat):
                layers.append(PoroElasticLayer(dicke, material))
            elif isinstance(material, Solid):
                raise ValueError(
                    f"In Zeile {zeile + 1}: '{material.name}' ist ein reines "
                    "Festkörper-Rahmenmaterial und kann nur als solid_mat "
                    "innerhalb eines poroelastischen Materials verwendet werden."
                )
            else:
                layers.append(FluidLayer(dicke, material))
        return layers
    
    def zeile_aus_layer(self, layer):
        """Überträgt eine bestehende Schicht in eine neue Tabellenzeile.

        Args:
            layer: Schicht mit Material und Dicke aus einem geladenen Projekt.

        Side Effects:
            Fügt der Tabelle eine vorausgefüllte Zeile hinzu.
        """
        zeile = self.tabelle.rowCount()
        self.tabelle.insertRow(zeile)

        auswahl = MaterialAuswahl()
        auswahl._menu_aufbauen(self.bibliothek.materialien)
        auswahl.ausgewaehltes_material = layer.material
        auswahl.setText(layer.material.name + " ▾")
        self.tabelle.setCellWidget(zeile, 0, auswahl)

        self.tabelle.setItem(zeile, 1, QTableWidgetItem(str(layer.dicke)))