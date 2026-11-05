"""Tests for the background calculation worker signals and behavior."""

import numpy as np

from pyvagui.model.layup import Layup
from pyvagui.model.materials import FluidSpec
from pyvagui.model.solvers import (
    FrequencySettings,
    SolverSpec,
    SolverType,
)
from pyvagui.services.worker import CalculationWorker


def make_solver_and_layups():
    """Build a solver and two named layups for worker tests."""
    solver = SolverSpec(
        name="Test solver",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=1000.0,
            n_points=3,
        ),
    )
    layups = [Layup(name="First"), Layup(name="Second")]
    materials = {material.id: material for material in [FluidSpec(name="Air")]}
    return solver, layups, materials


def test_worker_emits_results_progress_and_layup_messages(monkeypatch):
    """Collect one result per layup and emit ordered progress signals."""
    solver, layups, materials = make_solver_and_layups()
    fluid = next(iter(materials.values()))
    fluid.rho0 = 2.0
    fluid.c0 = 300.0
    solver.sending_fluid_id = fluid.id
    solver.angle_deg = 35.0
    monkeypatch.setattr(
        solver,
        "run",
        lambda layup, material_map: np.array([0.1, 0.2, 0.3]),
    )
    worker = CalculationWorker(solver, layups, materials)
    progress = []
    messages = []
    results = []
    errors = []
    worker.progress.connect(lambda done, total: progress.append((done, total)))
    worker.layup_finished.connect(messages.append)
    worker.finished.connect(results.append)
    worker.failed.connect(errors.append)

    worker.run()

    assert progress == [(1, 2), (2, 2)]
    assert messages == [
        "Finished 'First' (1/2).",
        "Finished 'Second' (2/2).",
    ]
    assert errors == []
    assert len(results) == 1
    assert [result.layup_name for result in results[0].results] == [
        "First",
        "Second",
    ]
    assert np.allclose(results[0].frequencies, [100.0, 316.227766, 1000.0])
    assert results[0].reference_impedance == 600.0
    assert results[0].angle_deg == 35.0


def test_worker_checks_cancel_between_layups(monkeypatch):
    """Finish the active layup then stop before starting the next one."""
    solver, layups, materials = make_solver_and_layups()
    worker = CalculationWorker(solver, layups, materials)
    monkeypatch.setattr(
        worker.solver,
        "run",
        lambda layup, material_map: (
            worker.request_cancel() or np.array([0.1, 0.2, 0.3])
        ),
    )
    progress = []
    results = []
    worker.progress.connect(lambda done, total: progress.append((done, total)))
    worker.finished.connect(results.append)

    worker.run()

    assert progress == [(1, 2)]
    assert [result.layup_name for result in results[0].results] == ["First"]


def test_worker_emits_failure_and_does_not_emit_results(monkeypatch):
    """Send calculation exceptions to the GUI through the failed signal."""
    solver, layups, materials = make_solver_and_layups()
    monkeypatch.setattr(
        solver,
        "run",
        lambda layup, material_map: (_ for _ in ()).throw(
            RuntimeError("pyva calculation failed")
        ),
    )
    worker = CalculationWorker(solver, layups, materials)
    errors = []
    results = []
    worker.failed.connect(errors.append)
    worker.finished.connect(results.append)

    worker.run()

    assert errors == ["pyva calculation failed"]
    assert results == []
