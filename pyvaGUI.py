"""Startet die grafische pyvaGUI-Anwendung.

Beim Import als Anwendungsskript werden eine ``QApplication`` und das
Hauptfenster erzeugt, angezeigt und die Qt-Ereignisschleife gestartet.

Side Effects:
	Öffnet das Hauptfenster und blockiert bis zum Ende der Qt-Ereignisschleife.
"""

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


if __name__ == "__main__":
	app = QApplication([])
	fenster = MainWindow()
	fenster.show()
	app.exec()