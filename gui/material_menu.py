from PyQt6.QtWidgets import QToolButton, QMenu


class MaterialAuswahl(QToolButton):
    """Ein Knopf mit aufklappbarem Menü zur Materialauswahl (mit Untermenüs)."""

    def __init__(self):
        super().__init__()
        self.setText("Material wählen ▾")

        # Damit ein Klick sofort das Menü öffnet:
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.ausgewaehltes_material = None    # hier merken wir die Wahl

    def _menu_aufbauen(self, materialien):
        """Baut das Menü dynamisch aus einer Liste von Material-Objekten."""
        menu = QMenu(self)

        # Materialien nach ihrem Klassennamen (Typ) gruppieren
        gruppen = {}
        for m in materialien:
            typ = type(m).__name__            # z. B. "Fluid", "EquivalentFluid"
            gruppen.setdefault(typ, []).append(m)

        # Pro Typ ein Untermenü, pro Material einen Eintrag
        for typ, mats in gruppen.items():
            untermenu = menu.addMenu(typ)
            for m in mats:
                aktion = untermenu.addAction(m.name)
                aktion.setData(m)             # das ECHTE Objekt an die Aktion hängen!

        menu.triggered.connect(self._material_gewaehlt)
        self.setMenu(menu)

    def _material_gewaehlt(self, action):
        """Wird aufgerufen, wenn irgendein Menü-Eintrag geklickt wird."""
        material = action.data()
        self.ausgewaehltes_material = material
        self.setText(material.name + " ▾")        # Knopfbeschriftung = gewählte Wahl