"""Application entry point for launching the pyvaGUI desktop interface."""

import sys

from PyQt6.QtWidgets import QApplication

from pyvagui.gui.main_window import MainWindow


def main() -> int:
    """Create the application, show its main window, and run Qt's event loop.

    Returns
    -------
    int
        Exit status returned by the Qt event loop.
    """
    # QApplication owns application-wide state and dispatches UI events.
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # The event loop keeps the window responsive until the user closes it.
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
