from PyQt6.QtWidgets import QMainWindow, QWidget, QSplitter, QLabel, QVBoxLayout, QPushButton, QMessageBox
from PyQt6.QtCore import Qt

from gui.plot_widget import PlotWidget
from gui.layer_table import LayerTable
from gui.material_menu import MaterialAuswahl
from gui.environment_panel import UmgebungPanel

from core.materials import EquivalentFluid
from core.layers import FluidLayer
from core.project import Projekt
from core.solver import rechne
from core.library import bibliothek_laden

class MainWindow(QMainWindow):
    """Haupfenster"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pyvaGUI")
        self.resize(1000, 600)
        
        self.bibliothek = bibliothek_laden("data/library.json")
        
        # ------ Linke Seite (Eingaben) -------
        self.linke_seite = QWidget()
        links_layout = QVBoxLayout()
        
        self.umgebung_panel = UmgebungPanel()
        links_layout.addWidget(self.umgebung_panel)
        
        links_layout.addWidget(QLabel("Absorber-Berechnung"))
        
        self.layer_tabelle = LayerTable(self.bibliothek)
        links_layout.addWidget(self.layer_tabelle)
        
        self.berechnen_knopf = QPushButton("Berechnen")
        links_layout.addWidget(self.berechnen_knopf)
        
        links_layout.addStretch()
        self.linke_seite.setLayout(links_layout)
        
        self.berechnen_knopf.clicked.connect(self.on_berechnen)
        
        # ------ Rechte Seite (Diagramm) ------
        self.plot = PlotWidget()
        
        # ------ Splitter ---------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.linke_seite)
        splitter.addWidget(self.plot)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        
        self.setCentralWidget(splitter)
        
        self.plot.zeichne([100, 1000, 10000], [0.2, 0.8, 0.6])
        
    def on_berechnen(self):
        try:
            projekt = Projekt(name="GUI-Projekt")
            projekt.layers = self.layer_tabelle.zu_layern()
            projekt.umgebung = self.umgebung_panel.zu_umgebung()

            frequenzen, absorption = rechne(projekt)
            self.plot.zeichne(frequenzen, absorption)

        except ValueError as fehler:
            QMessageBox.warning(self, "Ungültige Eingabe", str(fehler))

        except Exception as fehler:
            QMessageBox.critical(self, "Fehler bei der Berechnung",
                f"Es ist ein Fehler aufgetreten:\n{fehler}")