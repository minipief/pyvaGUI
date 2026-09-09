"""Formular zur Erfassung der akustischen Berechnungsumgebung."""

from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit

from core.materials import Fluid


class UmgebungPanel(QWidget):
    """Erfasst Frequenzraster und maximalen Einfallswinkel.

    Aufgabe:
        Das Widget stellt die skalaren Randbedingungen einer Berechnung bereit.

    Wichtige Bedienelemente:
        Vier Textfelder erfassen untere und obere Frequenz, Anzahl der
        Stützstellen und maximalen Einfallswinkel.

    Datenfluss:
        :meth:`zu_umgebung` liest die Textfelder, validiert sie durch numerische
        Konvertierung und erzeugt ein :class:`core.environment.Umgebung`-Objekt.

    Signale und Slots:
        Das Panel definiert keine eigenen Verbindungen. Das Hauptfenster liest
        seine Werte beim Berechnen und Speichern aus.

    Modulinteraktion:
        Erzeugt das Umgebungsmodell für :mod:`core.project` und
        :mod:`core.solver`; gespeicherte Werte werden von ``MainWindow`` wieder
        in die Felder geschrieben.
    """

    def __init__(self):
        """Erzeugt die Eingabefelder mit praxisnahen Standardwerten.

        Side Effects:
            Baut das Formularlayout des Widgets auf.
        """
        super().__init__()

        self.f_min_feld = QLineEdit("50")
        self.f_max_feld = QLineEdit("10000")
        self.punkte_feld = QLineEdit("100")
        self.theta_feld = QLineEdit("90")
        # self.rho0_feld = QLineEdit("1,23")

        layout = QFormLayout()
        layout.addRow("Frequenz von ", self.f_min_feld)
        layout.addRow("Frequenz bis ", self.f_max_feld)
        layout.addRow("Anzahl Punkte:",     self.punkte_feld)
        layout.addRow("θ max [°]:",         self.theta_feld)
        # layout.addRow("Luftdichte:", self.rho0_feld)
        self.setLayout(layout)
        
    def zu_umgebung(self):
        """Konvertiert die aktuellen Formulareingaben in ein Umgebungsmodell.

        Returns:
            Umgebung mit den im Formular angegebenen Berechnungsparametern.

        Raises:
            ValueError: Wenn mindestens ein Feld nicht numerisch interpretierbar
                ist.
        """
        from core.environment import Umgebung
        
        # fluid = Fluid("Luft", rho0=self.rho0_feld.text())
        
        try:
            umgebung = Umgebung(
                f_min=float(self.f_min_feld.text()),
                f_max=float(self.f_max_feld.text()),
                anzahl_punkte=int(self.punkte_feld.text()),
                theta_max_grad=float(self.theta_feld.text()),
                # fluid=fluid
            )
        except ValueError:
            raise ValueError("Falsche Umgebungsvariablen angegeben")
        
        return umgebung