from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

app = QApplication([])
fenster = MainWindow()
fenster.show()
app.exec()