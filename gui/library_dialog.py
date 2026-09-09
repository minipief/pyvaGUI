"""Dialog zur Anzeige und persistenten Pflege der Materialbibliothek."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt

from gui.material_dialog import MaterialDialog


class LibraryDialog(QDialog):
    """Verwaltet Materialien in einem modalen Bibliotheksdialog.

    Aufgabe:
        Der Dialog bietet Anlegen, Bearbeiten, Suchen und Löschen persistenter
        Materialien und schützt verwendete Rahmenmaterialien vor dem Löschen.

    Wichtige Bedienelemente:
        Ein Suchfeld filtert einen nach Materialtyp gruppierten Baum. Vier
        Schaltflächen öffnen den Materialdialog, ändern oder löschen die
        Auswahl beziehungsweise schließen den Dialog.

    Datenfluss:
        Der Baum referenziert die Objekte der ``MaterialBibliothek`` direkt über
        ``Qt.UserRole``. Erfolgreiche Änderungen werden in der Bibliothek
        ausgeführt, als JSON gespeichert und anschließend neu dargestellt.

    Signale und Slots:
        ``textChanged`` aktualisiert den Baum. Schaltflächen und Doppelklick
        rufen die CRUD-Slots auf. ``itemCollapsed`` und ``itemExpanded`` halten
        den Aufklappzustand der Typgruppen nach einem Neuaufbau stabil.

    Modulinteraktion:
        Nutzt :class:`gui.material_dialog.MaterialDialog` zur Dateneingabe und
        die Persistenzmethoden aus :mod:`core.library`. Das ``MainWindow``
        übergibt Bibliothek und Dateipfad.
    """

    def __init__(self, bibliothek, pfad, parent=None):
        """Initialisiert den Bibliotheksdialog.

        Args:
            bibliothek: Veränderbare Materialbibliothek.
            pfad: Pfad der zu aktualisierenden JSON-Datei.
            parent: Optionales übergeordnetes Qt-Widget.

        Side Effects:
            Baut den Dialog auf, füllt den Materialbaum und verbindet Signale.
        """
        super().__init__(parent)
        self.bibliothek = bibliothek
        self.pfad = pfad
        self._eingeklappte_typen = set()

        self.setWindowTitle("Materialbibliothek verwalten")
        self.resize(450, 400)

        self.such_feld = QLineEdit()
        self.such_feld.setPlaceholderText("Suchen...")

        self.baum = QTreeWidget()
        self.baum.setHeaderHidden(True)
        self._liste_aktualisieren()

        self.neu_knopf = QPushButton("Neu...")
        self.bearbeiten_knopf = QPushButton("Bearbeiten...")
        self.loeschen_knopf = QPushButton("Löschen")
        self.schliessen_knopf = QPushButton("Schließen")

        knopf_reihe = QHBoxLayout()
        knopf_reihe.addWidget(self.neu_knopf)
        knopf_reihe.addWidget(self.bearbeiten_knopf)
        knopf_reihe.addWidget(self.loeschen_knopf)
        knopf_reihe.addStretch()
        knopf_reihe.addWidget(self.schliessen_knopf)

        layout = QVBoxLayout()
        layout.addWidget(self.such_feld)
        layout.addWidget(self.baum)
        layout.addLayout(knopf_reihe)
        self.setLayout(layout)

        self.such_feld.textChanged.connect(self._liste_aktualisieren)
        self.neu_knopf.clicked.connect(self.on_neu)
        self.bearbeiten_knopf.clicked.connect(self.on_bearbeiten)
        self.loeschen_knopf.clicked.connect(self.on_loeschen)
        self.baum.itemDoubleClicked.connect(lambda item, spalte: self.on_bearbeiten())
        self.baum.itemCollapsed.connect(lambda item: self._eingeklappte_typen.add(item.text(0)))
        self.baum.itemExpanded.connect(lambda item: self._eingeklappte_typen.discard(item.text(0)))
        self.schliessen_knopf.clicked.connect(self.accept)

    def _liste_aktualisieren(self):
        """Baut den gefilterten und gruppierten Materialbaum neu auf.

        Side Effects:
            Ersetzt alle Baumeinträge und stellt den gespeicherten
            Aufklappzustand der Typgruppen wieder her.
        """
        self.baum.clear()
        suchtext = self.such_feld.text().strip().lower()

        gruppen = {}
        for material in self.bibliothek.materialien:
            if suchtext and suchtext not in material.name.lower():
                continue
            gruppen.setdefault(type(material).__name__, []).append(material)

        for typ in sorted(gruppen):
            kopf = QTreeWidgetItem([typ])
            # Typknoten bleiben aufklappbar, liefern aber kein Materialobjekt.
            kopf.setFlags(Qt.ItemFlag.ItemIsEnabled)
            schrift = kopf.font(0)
            schrift.setBold(True)
            kopf.setFont(0, schrift)
            self.baum.addTopLevelItem(kopf)

            for material in sorted(gruppen[typ], key=lambda m: m.name.lower()):
                eintrag = QTreeWidgetItem([material.name])
                eintrag.setData(0, Qt.ItemDataRole.UserRole, material)
                kopf.addChild(eintrag)

            kopf.setExpanded(typ not in self._eingeklappte_typen)

    def _ausgewaehltes_material(self):
        """Liest das Material des aktuell ausgewählten Baumeintrags.

        Returns:
            Ausgewähltes Material oder ``None`` bei fehlender Auswahl oder
            einem Typknoten.
        """
        eintrag = self.baum.currentItem()
        if eintrag is None:
            return None
        return eintrag.data(0, Qt.ItemDataRole.UserRole)

    def _speichern(self):
        """Persistiert den aktuellen Stand der Materialbibliothek.

        Side Effects:
            Überschreibt die Bibliotheksdatei. Bei Fehlern wird eine modale
            Warnmeldung angezeigt.
        """
        try:
            self.bibliothek.speichern(self.pfad)
        except Exception as fehler:
            QMessageBox.warning(self, "Speichern fehlgeschlagen", str(fehler))

    def on_neu(self):
        """Öffnet den Materialdialog zum Anlegen eines Materials.

        Side Effects:
            Startet einen modalen Dialog und fügt bei Bestätigung ein Material
            hinzu, speichert die Bibliothek und aktualisiert den Baum.
        """
        dialog = MaterialDialog(self.bibliothek, self)
        if dialog.exec():
            self.bibliothek.hinzufuegen(dialog.material())
            self._speichern()
            self._liste_aktualisieren()

    def on_bearbeiten(self):
        """Öffnet das ausgewählte Material zur Bearbeitung.

        Side Effects:
            Zeigt gegebenenfalls einen Hinweisdialog. Bei Bestätigung werden das
            Material objektidentisch aktualisiert, die Datei gespeichert und
            der Baum neu aufgebaut.
        """
        material = self._ausgewaehltes_material()
        if material is None:
            QMessageBox.information(self, "Kein Material gewählt",
                                    "Bitte zuerst ein Material in der Liste auswählen.")
            return

        dialog = MaterialDialog(self.bibliothek, self, material=material)
        if dialog.exec():
            self.bibliothek.aktualisieren(material.name, dialog.material())
            self._speichern()
            self._liste_aktualisieren()

    def on_loeschen(self):
        """Löscht das ausgewählte, nicht referenzierte Material nach Rückfrage.

        Side Effects:
            Zeigt Informations-, Warn- oder Bestätigungsdialoge. Bei bestätigter
            Löschung werden Bibliothek, JSON-Datei und Baum aktualisiert.
        """
        material = self._ausgewaehltes_material()
        if material is None:
            QMessageBox.information(self, "Kein Material gewählt",
                                    "Bitte zuerst ein Material in der Liste auswählen.")
            return

        # Objektidentität verhindert das Entfernen eines noch genutzten Rahmens.
        verwendet_von = [m.name for m in self.bibliothek.materialien
                         if getattr(m, "solid_mat", None) is material]
        if verwendet_von:
            QMessageBox.warning(
                self, "Löschen nicht möglich",
                f"'{material.name}' wird als Rahmenmaterial von "
                f"{', '.join(verwendet_von)} verwendet und kann daher nicht "
                "gelöscht werden."
            )
            return

        antwort = QMessageBox.question(
            self, "Material löschen",
            f"Soll '{material.name}' wirklich gelöscht werden?"
        )
        if antwort == QMessageBox.StandardButton.Yes:
            self.bibliothek.entfernen(material.name)
            self._speichern()
            self._liste_aktualisieren()
