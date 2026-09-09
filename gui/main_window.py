"""Hauptfenster und zentrale Ablaufsteuerung der pyvaGUI-Anwendung."""

from PyQt6.QtWidgets import QMainWindow, QWidget, QSplitter, QLabel, QVBoxLayout, QPushButton, QMessageBox, QFileDialog
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from gui.plot_widget import PlotWidget
from gui.layer_table import LayerTable
from gui.material_menu import MaterialAuswahl
from gui.environment_panel import UmgebungPanel
from gui.library_dialog import LibraryDialog

from core.materials import EquivalentFluid
from core.layers import FluidLayer
from core.project import Projekt
from core.solver import rechne
from core.library import bibliothek_laden

class MainWindow(QMainWindow):
    """Orchestriert Projekteingabe, Berechnung, Persistenz und Visualisierung.

    Aufgabe:
        Das Hauptfenster ist die zentrale Integrationsschicht zwischen den
        Eingabe-Widgets, den Core-Modellen, dem Solver und der Ergebnisgrafik.

    Wichtige Bedienelemente:
        Links erfassen ``UmgebungPanel`` und ``LayerTable`` die Berechnung; der
        Berechnen-Knopf startet den Solver. Rechts zeigt ``PlotWidget`` das
        Spektrum. Die Menüs Datei und Bibliothek steuern Projektpersistenz,
        Programmende und Materialverwaltung.

    Datenfluss:
        Formulardaten werden in ein :class:`core.project.Projekt` übertragen und
        an :func:`core.solver.rechne` gereicht. Dessen Frequenz- und
        Absorptionswerte fließen in das Plot-Widget. Beim Öffnen läuft der Weg
        von der JSON-Datei über das Projektmodell zurück in die Eingabefelder.

    Signale und Slots:
        Der Berechnen-Knopf ruft :meth:`on_berechnen` auf. Menüaktionen sind mit
        :meth:`on_oeffnen`, :meth:`on_speichern`,
        :meth:`on_bibliothek_verwalten` und ``close`` verbunden.

    Modulinteraktion:
        Verwendet alle zentralen GUI-Widgets sowie Projekt-, Solver- und
        Bibliotheksfunktionen aus :mod:`core`.
    """
    
    def __init__(self):
        """Initialisiert Bibliothek, Menüs, Eingabebereich und Diagramm.

        Raises:
            OSError: Wenn die Materialbibliothek nicht geladen oder angelegt
                werden kann.

        Side Effects:
            Liest oder erstellt ``data/library.json``, baut das Fenster auf,
            verbindet Signale und zeichnet eine initiale Beispielkurve.
        """
        super().__init__()
        self.setWindowTitle("pyvaGUI")
        self.resize(1200, 800)
        
        self.bibliothek_pfad = "data/library.json"
        self.bibliothek = bibliothek_laden(self.bibliothek_pfad)
        
        self._menu_aufbauen()
        
        self.linke_seite = QWidget()
        links_layout = QVBoxLayout()
        
        self.umgebung_panel = UmgebungPanel()
        links_layout.addWidget(self.umgebung_panel)
        
        links_layout.addWidget(QLabel("Absorber-Berechnung"))
        
        self.layer_tabelle = LayerTable(self.bibliothek)
        links_layout.addWidget(self.layer_tabelle, stretch=1)
        
        self.berechnen_knopf = QPushButton("Berechnen")
        links_layout.addWidget(self.berechnen_knopf)
        
        links_layout.addStretch()
        self.linke_seite.setLayout(links_layout)
        
        self.berechnen_knopf.clicked.connect(self.on_berechnen)
        
        self.plot = PlotWidget()
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.linke_seite)
        splitter.addWidget(self.plot)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        
        self.setCentralWidget(splitter)
        
        self.plot.zeichne([100, 1000, 10000], [0.2, 0.8, 0.6])
        
    def on_berechnen(self):
        """Berechnet und zeichnet das aktuell eingegebene Absorberprojekt.

        Side Effects:
            Liest die Eingabe-Widgets, führt eine pyva-Berechnung aus und ersetzt
            die dargestellte Kurve. Eingabe- und Berechnungsfehler werden in
            modalen Meldungsfenstern angezeigt.
        """
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

    def _menu_aufbauen(self):
        """Erzeugt die Datei- und Bibliotheksmenüs.

        Side Effects:
            Fügt der Menüleiste Aktionen hinzu und verbindet ihre
            ``triggered``-Signale mit den zuständigen Slots.
        """
        menueleiste = self.menuBar()
        datei_menue = menueleiste.addMenu("Datei")

        oeffnen_aktion = QAction("Öffnen", self)
        speichern_aktion = QAction("Speichern", self)
        beenden_aktion = QAction("Beenden", self)

        datei_menue.addAction(oeffnen_aktion)
        datei_menue.addAction(speichern_aktion)
        datei_menue.addSeparator()
        datei_menue.addAction(beenden_aktion)

        oeffnen_aktion.triggered.connect(self.on_oeffnen)
        speichern_aktion.triggered.connect(self.on_speichern)
        beenden_aktion.triggered.connect(self.close)

        bibliothek_menue = menueleiste.addMenu("Bibliothek")
        material_verwalten_aktion = QAction("Materialien verwalten...", self)
        bibliothek_menue.addAction(material_verwalten_aktion)
        material_verwalten_aktion.triggered.connect(self.on_bibliothek_verwalten)

    def on_bibliothek_verwalten(self):
        """Öffnet die gemeinsame Materialbibliothek zur Bearbeitung.

        Side Effects:
            Startet einen modalen :class:`gui.library_dialog.LibraryDialog`.
        """
        dialog = LibraryDialog(self.bibliothek, self.bibliothek_pfad, self)
        dialog.exec()

    def on_oeffnen(self):
        """Wählt eine Projektdatei und lädt sie in die Oberfläche.

        Side Effects:
            Öffnet einen Dateiauswahldialog, liest gegebenenfalls eine
            JSON-Datei und ersetzt die Werte der Eingabe-Widgets. Ladefehler
            werden als Warnmeldung angezeigt.
        """
        dateipfad, _ = QFileDialog.getOpenFileName(self, "Projekt öffnen", "", "JSON-Dateien (*.json)")
        if dateipfad:
            try:
                projekt = Projekt.laden(dateipfad)
                self._projekt_in_gui_laden(projekt)
            except Exception as fehler:
                QMessageBox.warning(self, "Öffnen fehlgeschlagen", str(fehler))

    def on_speichern(self):
        """Speichert die aktuelle Oberflächeneingabe als Projektdatei.

        Side Effects:
            Öffnet einen Dateiauswahldialog und schreibt gegebenenfalls eine
            JSON-Datei. Eingabe- und Schreibfehler erscheinen als Warnmeldung.
        """
        dateipfad, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", "", "JSON-Dateien (*.json)")
        if dateipfad:
            try:
                projekt = Projekt(name="GUI-Projekt")
                projekt.layers = self.layer_tabelle.zu_layern()
                projekt.umgebung = self.umgebung_panel.zu_umgebung()
                
                projekt.speichern(pfad=dateipfad)
            except Exception as fehler:
                QMessageBox.warning(self, "Speichern fehlgeschlagen", str(fehler))
                
    def _projekt_in_gui_laden(self, projekt):
        """Überträgt ein Projektmodell in die Eingabe-Widgets.

        Args:
            projekt: Geladenes Projekt mit Umgebung und Schichtstapel.

        Side Effects:
            Überschreibt alle Umgebungsfelder und baut die Schichttabelle neu
            auf.
        """
        umg = projekt.umgebung
        self.umgebung_panel.f_min_feld.setText(str(umg.f_min))
        self.umgebung_panel.f_max_feld.setText(str(umg.f_max))
        self.umgebung_panel.punkte_feld.setText(str(umg.anzahl_punkte))
        self.umgebung_panel.theta_feld.setText(str(umg.theta_max_grad))

        self.layer_tabelle.tabelle.setRowCount(0)
        for layer in projekt.layers:
            self.layer_tabelle.zeile_aus_layer(layer)