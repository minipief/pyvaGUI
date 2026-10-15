"""Application entry point for launching the pyvaGUI desktop interface."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from pyvagui.gui.main_window import MainWindow
from pyvagui.gui.theme import apply_theme


CALCULATION_WORKER_FLAG = "--calculation-worker"


def project_path_argument(arguments: list[str]) -> Path | None:
    """Return a .pyvagui path supplied on the command line, if present."""
    for argument in arguments:
        candidate = Path(argument)
        if candidate.suffix.lower() == ".pyvagui":
            return candidate
    return None


def main(arguments: list[str] | None = None) -> int:
    """Create the application, show its main window, and run Qt's event loop.

    Returns
    -------
    int
        Exit status returned by the Qt event loop.
    """
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments and arguments[0] == CALCULATION_WORKER_FLAG:
        if len(arguments) != 3:
            return 2
        from pyvagui.services.calculation_process import main as run_worker

        return run_worker(arguments[1], arguments[2])

    project_path = project_path_argument(arguments)
    application = QApplication(sys.argv[:1])
    apply_theme(application)
    window = MainWindow()
    if project_path is not None:
        window._load_project(project_path)
    window.show()
    # The event loop keeps the window responsive until the user closes it.
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
