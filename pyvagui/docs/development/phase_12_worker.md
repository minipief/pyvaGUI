# Phase 12 - Calculation Worker

## Goal

Run solver calculations without freezing the interface and report progress,
results, cancellation, and failures through Qt signals.

## What was built

- `pyvagui/services/worker.py`: `CalculationWorker` with progress,
  per-layup messages, finished results, failure text, and cancellation.
- `pyvagui/gui/main_window.py`: QThread startup/cleanup, Run and Cancel
  controls, status progress, result storage, and error reporting.
- `tests/model/test_worker.py` and `tests/gui/test_main_window.py`:
  worker signal behavior and threaded UI integration.
- Expanded the worker-object explanation in `pyqt_primer.md`; updated
  decisions and changelog.

## How it works

Before starting, the main window validates the whole project and selected
solver, then gives the worker copied solver, layup, and material data. The
worker QObject is moved to a QThread. It runs one layup at a time and emits
progress and status signals. The GUI receives those signals on its own
thread, updates the status bar and log, and stores the final ResultSet.
Cancel sets a flag; the active pyva call finishes, then the worker stops
before beginning the next layup.

```text
Run -> validate -> QThread starts CalculationWorker
    -> progress/log signals -> ResultSet or error signal
Cancel -> request flag -> finish current layup -> stop before next layup
```

## Concepts used

See `pyqt_primer.md`: QThread, worker-object pattern, queued signals,
thread ownership, and the GUI-thread rule for widget access.

## Decisions

- D-023: use a worker QObject moved to QThread; cancellation is checked
  between layups.

## Tests

- Worker unit tests: 3 passed.
- Main-window run/cancel tests use a mocked calculation with a real QThread.
- Full `python -m pytest`: 141 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

The cancellation flag cannot interrupt a running pyva method safely, so
the worker completes the current layup and checks for cancellation before
starting the next one. All widgets remain owned and updated by the GUI
thread.

## How to verify manually

Run `python -m pyvagui`, select a valid solver tab, and press Run. Observe
the status progress and log updates. Press Cancel during a multi-layup
calculation; the active layup completes and later layups do not start.

## Comprehension questions

1. Why must calculation work not run in the GUI thread?
2. Why is Cancel checked between layups instead of inside `SolverSpec.run`?
