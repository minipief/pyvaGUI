from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit

from core.materials import Fluid


class UmgebungPanel(QWidget):
    """Eingabefelder für die Berechnungseinstellungen."""

    def __init__(self):
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