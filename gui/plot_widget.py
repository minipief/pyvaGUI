"""Matplotlib-Widget zur Darstellung interaktiver Absorptionskurven."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class PlotWidget(QWidget):
    """Visualisiert Absorptionsspektren mit einer Hover-Werteanzeige.

    Aufgabe:
        Das Widget bettet eine Matplotlib-Figur in Qt ein und zeigt den
        Absorptionsgrad über einer logarithmischen Frequenzachse.

    Wichtige Bedienelemente:
        ``canvas`` enthält die Figur und ihre Achse; ein roter Marker und eine
        Annotation kennzeichnen den dem Mauszeiger nächsten Datenpunkt.

    Datenfluss:
        :meth:`zeichne` übernimmt Frequenz- und Absorptionsfolgen vom Solver.
        Mausereignisse lesen diese Daten nur und aktualisieren Marker und Text.

    Signale und Slots:
        Matplotlibs ``motion_notify_event`` ist mit
        :meth:`_bei_mausbewegung` verbunden. Das Widget definiert keine
        zusätzlichen Qt-Signale.

    Modulinteraktion:
        Wird vom ``MainWindow`` mit Ergebnissen aus :mod:`core.solver` versorgt.
    """

    def __init__(self):
        """Initialisiert Figur, Canvas, Achse und Mausereignisverbindung.

        Side Effects:
            Baut das Widgetlayout auf und zeichnet ein leeres Diagramm.
        """
        super().__init__()
        
        self.frequenzen = None
        self.absorption = None
        
        self.marker = None
        self.annotation = None

        self.figur = Figure(figsize=(6, 4))
        self.canvas = FigureCanvasQTAgg(self.figur)
        self.achse = self.figur.add_subplot(111)
        
        self.canvas.mpl_connect("motion_notify_event", self._bei_mausbewegung)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self._leeren()

    def _leeren(self):
        """Setzt die Achse auf einen leeren, beschrifteten Zustand zurück.

        Side Effects:
            Löscht die Achse und zeichnet den Canvas synchron neu.
        """
        self.achse.clear()
        self.achse.set_xlabel("Frequenz [Hz]")
        self.achse.set_ylabel("Absorption")
        self.achse.set_ylim(0, 1)
        self.achse.grid(True)
        self.canvas.draw()

    def zeichne(self, frequenzen, absorption):
        """Zeichnet eine Absorptionskurve und bereitet die Hover-Anzeige vor.

        Args:
            frequenzen: Frequenzstützstellen in Hertz.
            absorption: Absorptionsgrade zu den Frequenzstützstellen.

        Side Effects:
            Ersetzt Diagrammdaten, Achseninhalt, Marker und Annotation und
            zeichnet den Canvas synchron neu.
        """
        self.frequenzen = frequenzen
        self.absorption = absorption

        self.achse.clear()
        self.achse.plot(frequenzen, absorption)
        self.achse.set_xscale("log")
        self.achse.set_xlabel("Frequenz [Hz]")
        self.achse.set_ylabel("Absorption")
        self.achse.set_ylim(0, 1)
        self.achse.grid(True)
        
        self.marker, = self.achse.plot([], [], "o", color="red")
        self.annotation = self.achse.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="yellow", alpha=0.8)
        )
        self.annotation.set_visible(False)
        
        self.figur.tight_layout()
        self.canvas.draw()
        
    def _bei_mausbewegung(self, event):
        """Aktualisiert die Werteanzeige für eine Mausbewegung.

        Args:
            event: Matplotlib-Mausereignis mit Achse und Datenkoordinaten.

        Side Effects:
            Positioniert Marker und Annotation oder blendet beide aus und stößt
            eine verzögerte Neuzeichnung des Canvas an.
        """
        if self.frequenzen is None or event.inaxes != self.achse:
            self._verstecke_hover()
            return

        maus_x = event.xdata

        import numpy as np
        index = np.argmin(np.abs(self.frequenzen - maus_x))
        x = self.frequenzen[index]
        y = self.absorption[index]
        
        # Achsenanteile erlauben eine randabhängige Platzierung der Infobox.
        x_min, x_max = self.achse.get_xlim()
        x_anteil = (np.log10(x) - np.log10(x_min)) / (np.log10(x_max) - np.log10(x_min))

        y_min, y_max = self.achse.get_ylim()
        y_anteil = (y - y_min) / (y_max - y_min)
        
        if x_anteil > 0.5:
            versatz_x = -10
            ausricht_x = "right"
        else:
            versatz_x = 10
            ausricht_x = "left"

        if y_anteil > 0.5:
            versatz_y = -10
            ausricht_y = "top"
        else:
            versatz_y = 10
            ausricht_y = "bottom"

        self.annotation.set_position((versatz_x, versatz_y))
        self.annotation.set_horizontalalignment(ausricht_x)
        self.annotation.set_verticalalignment(ausricht_y)

        self.marker.set_data([x], [y])
        self.annotation.xy = (x, y)
        self.annotation.set_text(f"{x:.0f} Hz\nα = {y:.3f}")
        self.annotation.set_visible(True)

        self.canvas.draw_idle()
        
    def _verstecke_hover(self):
        """Blendet Marker und Annotation aus.

        Side Effects:
            Ändert die Sichtbarkeit der Hover-Elemente und fordert eine
            verzögerte Neuzeichnung an.
        """
        if self.annotation is not None:
            self.annotation.set_visible(False)
            self.marker.set_data([], [])
            self.canvas.draw_idle()