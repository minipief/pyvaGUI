"""Aufklappbare, nach Materialtyp gruppierte Materialauswahl."""

from PyQt6.QtWidgets import QToolButton, QMenu


class MaterialAuswahl(QToolButton):
    """Stellt ein hierarchisches Auswahlmenü für Bibliotheksmaterialien bereit.

    Aufgabe:
        Der Werkzeugknopf hält die aktuelle Materialauswahl einer Schichtzeile.

    Wichtige Bedienelemente:
        Ein sofort aufklappendes Menü gruppiert Aktionen nach Materialklasse und
        sortiert Materialnamen alphabetisch.

    Datenfluss:
        Materialobjekte werden als ``QAction``-Daten hinterlegt. Eine Auswahl
        gelangt in ``ausgewaehltes_material`` und wird im Knopftext angezeigt.

    Signale und Slots:
        ``QMenu.triggered`` ist mit :meth:`_material_gewaehlt` verbunden.

    Modulinteraktion:
        Wird von :class:`gui.layer_table.LayerTable` erzeugt und mit den
        Objekten einer ``MaterialBibliothek`` befüllt.
    """

    def __init__(self):
        """Initialisiert einen Materialknopf ohne aktive Auswahl.

        Side Effects:
            Konfiguriert den Knopf für das sofortige Öffnen seines Menüs.
        """
        super().__init__()
        self.setText("Material wählen ▾")

        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.ausgewaehltes_material = None

    def _menu_aufbauen(self, materialien):
        """Baut das Menü aus Materialobjekten neu auf.

        Args:
            materialien: Materialien, gruppiert nach konkreter Klasse.

        Side Effects:
            Ersetzt das Menü des Werkzeugknopfs und verbindet dessen
            ``triggered``-Signal mit :meth:`_material_gewaehlt`.
        """
        menu = QMenu(self)

        gruppen = {}
        for m in materialien:
            typ = type(m).__name__
            gruppen.setdefault(typ, []).append(m)

        for typ in sorted(gruppen):
            untermenu = menu.addMenu(typ)
            for m in sorted(gruppen[typ], key=lambda m: m.name.lower()):
                aktion = untermenu.addAction(m.name)
                # Die Aktion transportiert die Objektidentität bis zum Slot.
                aktion.setData(m)

        menu.triggered.connect(self._material_gewaehlt)
        self.setMenu(menu)

    def _material_gewaehlt(self, action):
        """Übernimmt das Material einer ausgelösten Menüaktion.

        Args:
            action: Ausgelöste ``QAction`` mit einem Material als Nutzdaten.

        Side Effects:
            Aktualisiert die aktive Materialreferenz und den sichtbaren Text.
        """
        material = action.data()
        self.ausgewaehltes_material = material
        self.setText(material.name + " ▾")