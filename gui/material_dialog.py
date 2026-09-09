"""Dynamischer Eingabedialog zum Erstellen und Bearbeiten von Materialien."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QDialogButtonBox, QWidget, QStackedWidget, QMessageBox
)

from core.materials import Fluid, EquivalentFluid, DelanyBazley, Solid, PoroElasticMat


class MaterialDialog(QDialog):
    """Erfasst und validiert die Parameter eines Materials.

    Aufgabe:
        Der modale Dialog unterstützt das Anlegen aller verfügbaren
        Materialtypen und das Bearbeiten eines bestehenden Materials.

    Wichtige Bedienelemente:
        Name und Typ stehen in einem Kopfformular. Ein ``QStackedWidget`` zeigt
        die typabhängigen Zahlenfelder, Kontrollkästchen und gegebenenfalls die
        Auswahl des Festkörperrahmens. OK und Abbrechen steuern das Ergebnis.

    Datenfluss:
        Formularwerte werden in :meth:`_material_bauen` numerisch ausgewertet
        und in ein Modell aus :mod:`core.materials` überführt. Nach erfolgreicher
        Annahme liefert :meth:`material` dieses Objekt an den ``LibraryDialog``.
        Beim Bearbeiten fließen die Werte des Ausgangsmaterials in die Felder.

    Signale und Slots:
        ``currentIndexChanged`` schaltet die Formularseite. Die Standardsignale
        ``accepted`` und ``rejected`` der Dialogknöpfe rufen :meth:`accept`
        beziehungsweise ``reject`` auf; :meth:`accept` führt die Validierung aus.

    Modulinteraktion:
        Liest Festkörper aus der ``MaterialBibliothek``, erzeugt Modelle aus
        :mod:`core.materials` und wird vom ``LibraryDialog`` modal ausgeführt.
    """

    def __init__(self, bibliothek, parent=None, material=None):
        """Initialisiert den Dialog zum Anlegen oder Bearbeiten.

        Args:
            bibliothek: Bibliothek für Namensprüfung und Rahmenmaterialien.
            parent: Optionales übergeordnetes Qt-Widget.
            material: Optionales Material, dessen Werte bearbeitet werden.

        Side Effects:
            Baut alle typabhängigen Formularseiten auf und verbindet die
            Dialogsignale. Bei Bearbeitung werden Felder vorausgefüllt.
        """
        super().__init__(parent)
        self.bibliothek = bibliothek
        self._material = None
        self._bearbeitetes_material = material

        self.setWindowTitle("Material bearbeiten" if material else "Neues Material")

        self.name_feld = QLineEdit()

        self.typ_auswahl = QComboBox()
        self.typ_auswahl.addItems(
            ["Fluid", "EquivalentFluid", "DelanyBazley", "Solid", "PoroElasticMat"]
        )

        self.seiten = QStackedWidget()
        self._felder = {}
        for typ in ["Fluid", "EquivalentFluid", "DelanyBazley", "Solid", "PoroElasticMat"]:
            seite, felder = self._seite_erstellen(typ)
            self._felder[typ] = felder
            self.seiten.addWidget(seite)

        self.typ_auswahl.currentIndexChanged.connect(self.seiten.setCurrentIndex)

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        kopf_layout = QFormLayout()
        kopf_layout.addRow("Name:", self.name_feld)
        kopf_layout.addRow("Typ:", self.typ_auswahl)

        layout = QVBoxLayout()
        layout.addLayout(kopf_layout)
        layout.addWidget(self.seiten)
        layout.addWidget(knoepfe)
        self.setLayout(layout)

        if material is not None:
            self._fuer_bearbeitung_vorbelegen(material)

    def _fuer_bearbeitung_vorbelegen(self, material):
        """Befüllt die Oberfläche mit einem vorhandenen Material.

        Args:
            material: Zu bearbeitendes Materialmodell.

        Side Effects:
            Schreibt Modellwerte in die zugehörigen Felder und sperrt die
            Typauswahl. Die Rahmenauswahl wird erst in :meth:`showEvent` gesetzt.
        """
        self.name_feld.setText(material.name)

        typ = type(material).__name__
        self.typ_auswahl.setCurrentText(typ)
        # Ein Typwechsel würde einen inkompatiblen Satz von Feldern aktivieren.
        self.typ_auswahl.setEnabled(False)

        for schluessel, feld in self._felder[typ].items():
            if schluessel == "solid_mat":
                continue
            wert = getattr(material, schluessel, None)
            if wert is None:
                continue
            if isinstance(feld, QCheckBox):
                feld.setChecked(bool(wert))
            else:
                feld.setText(str(wert))

    def _seite_erstellen(self, typ):
        """Baut die Formularseite eines Materialtyps.

        Args:
            typ: Name einer unterstützten Materialklasse.

        Returns:
            Tupel aus Formular-Widget und Zuordnung der Attributnamen zu ihren
            Eingabe-Widgets.

        Side Effects:
            Erzeugt neue Qt-Widgets, ohne sie bereits in den Seitenstapel
            einzufügen.
        """
        seite = QWidget()
        layout = QFormLayout()
        felder = {}

        def zeile(schluessel, beschriftung, standard=""):
            """Fügt ein beschriftetes Textfeld zur aktuellen Seite hinzu.

            Args:
                schluessel: Materialattribut für die Feldzuordnung.
                beschriftung: Sichtbare Formularbeschriftung.
                standard: Anfangswert des Textfelds.

            Side Effects:
                Ergänzt Layout und Feldzuordnung der Formularseite.
            """
            feld = QLineEdit(str(standard))
            layout.addRow(beschriftung, feld)
            felder[schluessel] = feld

        def thermo_felder(eta_standard):
            """Ergänzt gemeinsame Dämpfungs- und Thermofelder eines Fluids.

            Args:
                eta_standard: Standardwert des Verlustfaktors.

            Side Effects:
                Ergänzt die aktuelle Formularseite um fünf Textfelder.
            """
            zeile("eta", "Dämpfungsverlust:", eta_standard)
            zeile("dynamic_viscosity", "Dyn. Viskosität [Pa·s]:", 1.84e-5)
            zeile("kappa", "Kappa (cp/cv):", 1.4)
            zeile("Cp", "Cp [J/(kg·K)]:", 1005.1)
            zeile("heat_conductivity", "Wärmeleitfähigkeit [W/(m·K)]:", 0.0257673)

        if typ == "Fluid":
            zeile("c0", "c0 [m/s]:", 343.0)
            zeile("rho0", "rho0 [kg/m³]:", 1.23)
            thermo_felder(0.01)

        elif typ == "EquivalentFluid":
            zeile("porosity", "Porosität:", 0.98)
            zeile("flow_res", "Strömungswiderstand:", 25000)
            zeile("tortuosity", "Tortuosität:", 1.02)
            zeile("rho_bulk", "rho_bulk [kg/m³]:", 30.0)
            zeile("length_visc", "Viskose Länge [m]:", 90e-6)
            zeile("length_therm", "Thermische Länge [m]:", 180e-6)
            limp_feld = QCheckBox()
            limp_feld.setChecked(True)
            layout.addRow("Limp-Modell:", limp_feld)
            felder["limp"] = limp_feld
            zeile("c0", "c0 [m/s]:", 343.0)
            zeile("rho0", "rho0 [kg/m³]:", 1.23)
            thermo_felder(0.0)

        elif typ == "DelanyBazley":
            zeile("flow_res", "Strömungswiderstand:", 25000)
            miki_feld = QCheckBox()
            layout.addRow("Miki-Modell:", miki_feld)
            felder["miki"] = miki_feld
            zeile("c0", "c0 [m/s]:", 343.0)
            zeile("rho0", "rho0 [kg/m³]:", 1.23)
            thermo_felder(0.0)

        elif typ == "Solid":
            zeile("E", "E-Modul [Pa]:", 7.1e10)
            zeile("rho0", "rho0 [kg/m³]:", 2700.0)
            zeile("nu", "Querkontraktionszahl:", 0.34)
            zeile("eta", "Dämpfungsverlust:", 0.01)

        elif typ == "PoroElasticMat":
            solid_auswahl = QComboBox()
            layout.addRow("Rahmenmaterial:", solid_auswahl)
            felder["solid_mat"] = solid_auswahl
            zeile("porosity", "Porosität:", 0.98)
            zeile("flow_res", "Strömungswiderstand:", 25000)
            zeile("tortuosity", "Tortuosität:", 1.02)
            zeile("length_visc", "Viskose Länge [m]:", 90e-6)
            zeile("length_therm", "Thermische Länge [m]:", 180e-6)
            limp_feld = QCheckBox()
            layout.addRow("Limp-Modell:", limp_feld)
            felder["limp"] = limp_feld
            zeile("c0", "c0 [m/s]:", 343.0)
            zeile("rho0", "rho0 [kg/m³]:", 1.23)
            zeile("dynamic_viscosity", "Dyn. Viskosität [Pa·s]:", 1.84e-5)
            zeile("kappa", "Kappa (cp/cv):", 1.4)
            zeile("Cp", "Cp [J/(kg·K)]:", 1005.1)
            zeile("heat_conductivity", "Wärmeleitfähigkeit [W/(m·K)]:", 0.0257673)

        seite.setLayout(layout)
        return seite, felder

    def _festkoerper_materialien(self):
        """Filtert die Bibliothek auf mögliche Rahmenmaterialien.

        Returns:
            Liste aller Festkörpermaterialien der Bibliothek.
        """
        return [m for m in self.bibliothek.materialien if isinstance(m, Solid)]

    def showEvent(self, event):
        """Aktualisiert die Rahmenauswahl unmittelbar vor der Anzeige.

        Args:
            event: Qt-Ereignis für das Anzeigen des Dialogs.

        Side Effects:
            Befüllt die Rahmen-Combobox aus dem aktuellen Bibliotheksstand,
            stellt beim Bearbeiten die Auswahl wieder her und leitet das Ereignis
            an ``QDialog`` weiter.
        """
        solid_auswahl = self._felder["PoroElasticMat"]["solid_mat"]
        solid_auswahl.clear()
        for solid in self._festkoerper_materialien():
            solid_auswahl.addItem(solid.name, solid)
        if isinstance(self._bearbeitetes_material, PoroElasticMat):
            index = solid_auswahl.findText(self._bearbeitetes_material.solid_mat.name)
            if index >= 0:
                solid_auswahl.setCurrentIndex(index)
        super().showEvent(event)

    def accept(self):
        """Validiert die Eingaben und nimmt den Dialog bei Erfolg an.

        Side Effects:
            Speichert das erzeugte Material in ``_material`` und schließt den
            Dialog. Bei ungültigen Werten bleibt er offen und zeigt eine Warnung.
        """
        try:
            self._material = self._material_bauen()
        except ValueError as fehler:
            QMessageBox.warning(self, "Ungültige Eingabe", str(fehler))
            return
        super().accept()

    def _material_bauen(self):
        """Erzeugt das ausgewählte Material aus den Formulareingaben.

        Returns:
            Neu konstruiertes Material der ausgewählten Klasse.

        Raises:
            ValueError: Wenn Name, Zahlenfelder, Materialtyp oder erforderliches
                Rahmenmaterial ungültig sind oder der Name bereits existiert.
        """
        name = self.name_feld.text().strip()
        if not name:
            raise ValueError("Bitte einen Namen für das Material angeben.")
        vorhandenes = self.bibliothek.finde(name)
        if vorhandenes is not None and vorhandenes is not self._bearbeitetes_material:
            raise ValueError(f"Es existiert bereits ein Material mit dem Namen '{name}'.")

        typ = self.typ_auswahl.currentText()
        felder = self._felder[typ]

        def thermo_kwargs(mit_eta=True):
            """Liest gemeinsame Fluidparameter aus der aktiven Formularseite.

            Args:
                mit_eta: Nimmt den Verlustfaktor in das Ergebnis auf.

            Returns:
                Schlüsselwortargumente für einen Fluidkonstruktor.

            Raises:
                ValueError: Wenn ein Feld keinen gültigen Zahlenwert enthält.
            """
            kwargs = {
                "dynamic_viscosity": float(felder["dynamic_viscosity"].text()),
                "kappa": float(felder["kappa"].text()),
                "Cp": float(felder["Cp"].text()),
                "heat_conductivity": float(felder["heat_conductivity"].text()),
            }
            if mit_eta:
                kwargs["eta"] = float(felder["eta"].text())
            return kwargs

        try:
            if typ == "Fluid":
                return Fluid(name=name,
                            c0=float(felder["c0"].text()),
                            rho0=float(felder["rho0"].text()),
                            **thermo_kwargs())

            elif typ == "EquivalentFluid":
                return EquivalentFluid(name=name,
                                       porosity=float(felder["porosity"].text()),
                                       flow_res=float(felder["flow_res"].text()),
                                       tortuosity=float(felder["tortuosity"].text()),
                                       rho_bulk=float(felder["rho_bulk"].text()),
                                       length_visc=float(felder["length_visc"].text()),
                                       length_therm=float(felder["length_therm"].text()),
                                       limp=felder["limp"].isChecked(),
                                       c0=float(felder["c0"].text()),
                                       rho0=float(felder["rho0"].text()),
                                       **thermo_kwargs())

            elif typ == "DelanyBazley":
                return DelanyBazley(name=name,
                                    flow_res=float(felder["flow_res"].text()),
                                    miki=felder["miki"].isChecked(),
                                    c0=float(felder["c0"].text()),
                                    rho0=float(felder["rho0"].text()),
                                    **thermo_kwargs())

            elif typ == "Solid":
                return Solid(name=name,
                            E=float(felder["E"].text()),
                            rho0=float(felder["rho0"].text()),
                            nu=float(felder["nu"].text()),
                            eta=float(felder["eta"].text()))

            elif typ == "PoroElasticMat":
                solid_mat = felder["solid_mat"].currentData()
                if solid_mat is None:
                    raise ValueError(
                        "Es ist kein Festkörper-Rahmenmaterial vorhanden. "
                        "Bitte zuerst ein Material vom Typ 'Solid' anlegen."
                    )
                return PoroElasticMat(name=name,
                                      solid_mat=solid_mat,
                                      flow_res=float(felder["flow_res"].text()),
                                      porosity=float(felder["porosity"].text()),
                                      tortuosity=float(felder["tortuosity"].text()),
                                      length_visc=float(felder["length_visc"].text()),
                                      length_therm=float(felder["length_therm"].text()),
                                      limp=felder["limp"].isChecked(),
                                      c0=float(felder["c0"].text()),
                                      rho0=float(felder["rho0"].text()),
                                      **thermo_kwargs(mit_eta=False))
        except ValueError as fehler:
            if str(fehler).startswith("could not convert"):
                raise ValueError("Bitte für alle Felder gültige Zahlen angeben.")
            raise

        raise ValueError(f"Unbekannter Materialtyp: {typ}")

    def material(self):
        """Gibt das erfolgreich erstellte Material zurück.

        Returns:
            Erzeugtes Material oder ``None``, solange der Dialog nicht
            erfolgreich angenommen wurde.
        """
        return self._material
