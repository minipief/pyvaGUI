from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class PlotWidget(QWidget):
    """Ein wiederverwendbares Diagramm-Widget."""

    def __init__(self):
        super().__init__()

        # figsize (6, 4) ist 3:2 – genau dein gewünschtes Seitenverhältnis
        self.figur = Figure(figsize=(6, 4))
        self.canvas = FigureCanvasQTAgg(self.figur)
        self.achse = self.figur.add_subplot(111)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self._leeren()

    def _leeren(self):
        """Zeigt ein leeres, beschriftetes Diagramm."""
        self.achse.clear()
        self.achse.set_xlabel("Frequenz [Hz]")
        self.achse.set_ylabel("Absorption")
        self.achse.set_ylim(0, 1)
        self.achse.grid(True)
        self.canvas.draw()

    def zeichne(self, frequenzen, absorption):
        """Zeichnet eine Kurve. Wird später von außen aufgerufen."""
        self.achse.clear()
        self.achse.plot(frequenzen, absorption)
        self.achse.set_xscale("log")
        self.achse.set_xlabel("Frequenz [Hz]")
        self.achse.set_ylabel("Absorption")
        self.achse.set_ylim(0, 1)
        self.achse.grid(True)
        self.figur.tight_layout()
        self.canvas.draw()