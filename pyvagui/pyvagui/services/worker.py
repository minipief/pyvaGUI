"""Background worker for running selected layup calculations."""

from copy import deepcopy

from PyQt6.QtCore import QObject, pyqtSignal

from pyvagui.model.layup import Layup
from pyvagui.model.materials import MaterialSpec
from pyvagui.model.results import LayupResult, ResultSet
from pyvagui.model.solvers import SolverSpec


class CalculationWorker(QObject):
    """Calculate one solver for multiple layups outside the GUI thread.

    Parameters
    ----------
    solver : SolverSpec
        Solver configuration to execute.
    layups : list of Layup
        Selected layups in project order.
    materials : dict of str to MaterialSpec
        Material snapshot indexed by material ID.

    Notes
    -----
    A long calculation in the GUI thread prevents Qt from processing
    repaint and input events, which makes the window appear frozen. The
    worker-object pattern keeps this work in a QObject and moves that
    object to a QThread. MainWindow connects worker signals to slots that
    update the interface on the GUI thread. The worker only receives
    model data and never reads or changes widgets. Cancellation is checked
    between layups because one active pyva call cannot be interrupted
    safely by this simple design.
    """

    progress = pyqtSignal(int, int)
    layup_finished = pyqtSignal(str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        solver: SolverSpec,
        layups: list[Layup],
        materials: dict[str, MaterialSpec],
    ):
        """Copy model inputs so the worker never mutates project state."""
        super().__init__()
        self.solver = deepcopy(solver)
        self.layups = deepcopy(layups)
        self.materials = deepcopy(materials)
        self.cancel_requested = False

    def run(self) -> None:
        """Calculate selected layups and emit progress/results or an error."""
        total = len(self.layups)
        results = []
        frequencies = self.solver.frequencies.frequencies()
        labels = self.solver.frequencies.labels()
        try:
            for index, layup in enumerate(self.layups):
                # Finish the active SolverSpec.run before honoring a cancel.
                if self.cancel_requested:
                    break
                values = self.solver.run(layup, self.materials)
                results.append(
                    LayupResult(
                        layup_id=layup.id,
                        layup_name=layup.name,
                        values=values,
                    )
                )
                self.layup_finished.emit(
                    f"Finished '{layup.name}' ({index + 1}/{total})."
                )
                self.progress.emit(index + 1, total)
        except Exception as error:
            self.failed.emit(str(error))
            return

        result_set = ResultSet(
            solver_id=self.solver.id,
            solver_name=self.solver.name,
            solver_type=self.solver.solver_type,
            frequencies=frequencies,
            labels=labels,
            results=results,
        )
        self.finished.emit(result_set)

    def request_cancel(self) -> None:
        """Request cancellation before the next layup starts."""
        self.cancel_requested = True
