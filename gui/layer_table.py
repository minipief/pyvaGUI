from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout
)
from gui.material_menu import MaterialAuswahl


class LayerTable(QWidget):
    """Tabelle zum Zusammenstellen der Schichten."""

    def __init__(self, bibliothek):
        super().__init__()
        self.bibliothek = bibliothek

        self.tabelle = QTableWidget(0, 2)
        self.tabelle.setHorizontalHeaderLabels(["Material", "Dicke [m]"])

        self.add_knopf = QPushButton("+ Schicht")
        self.del_knopf = QPushButton("– Schicht")

        knopf_reihe = QHBoxLayout()          # Knöpfe nebeneinander
        knopf_reihe.addWidget(self.add_knopf)
        knopf_reihe.addWidget(self.del_knopf)

        layout = QVBoxLayout()
        layout.addWidget(self.tabelle)
        layout.addLayout(knopf_reihe)        # ein Layout IN ein Layout!
        self.setLayout(layout)

        # Signale
        self.add_knopf.clicked.connect(self.zeile_hinzufuegen)
        self.del_knopf.clicked.connect(self.zeile_entfernen)
        
    def zeile_hinzufuegen(self):
        zeile = self.tabelle.rowCount()          # aktuelle Zeilenzahl = neuer Index
        self.tabelle.insertRow(zeile)            # leere Zeile anhängen

        auswahl = MaterialAuswahl()
        auswahl._menu_aufbauen(self.bibliothek.materialien)
        self.tabelle.setCellWidget(zeile, 0, auswahl)
        # Spalte 1: Dicke
        self.tabelle.setItem(zeile, 1, QTableWidgetItem("0.1"))

    def zeile_entfernen(self):
        zeile = self.tabelle.currentRow()        # aktuell markierte Zeile
        if zeile >= 0:                           # -1 heißt "nichts markiert"
            self.tabelle.removeRow(zeile)
            
    def zu_layern(self):
        from core.layers import FluidLayer

        if self.tabelle.rowCount() == 0:
            raise ValueError("Es wurde keine Schicht hinzugefügt.")

        layers = []
        for zeile in range(self.tabelle.rowCount()):
            auswahl = self.tabelle.cellWidget(zeile, 0)
            material = auswahl.ausgewaehltes_material

            if material is None:
                raise ValueError(f"In Zeile {zeile + 1} wurde kein Material gewählt.")

            dicke = float(self.tabelle.item(zeile, 1).text())
            layers.append(FluidLayer(dicke, material))
        return layers