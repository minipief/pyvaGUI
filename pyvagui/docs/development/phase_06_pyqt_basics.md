# Phase 06 - PyQt Basics

## Goal

Start the desktop application and create the main-window frame that later
phases will fill with project and calculation features.

## What was built

- `pyvagui/__main__.py`: creates `QApplication`, shows `MainWindow`, and
  enters Qt's event loop.
- `pyvagui/gui/main_window.py`: menu headings, horizontal splitter,
  model/results placeholders, read-only log, status bar, and initial log
  visibility/exit actions.
- `tests/gui/test_main_window.py`: pytest-qt smoke checks for the window,
  its primary widgets, and log validation.
- `docs/development/pyqt_primer.md`: first glossary entries with examples.
- Updated design decisions and changelog.

## How it works

`main()` creates one `QApplication`, constructs and shows the main window,
then calls `application.exec()`. The event loop dispatches UI events
until the window closes. `MainWindow` arranges its child widgets with
layouts; Qt's parent-child ownership keeps their lifetimes tied to the
window. A horizontal `QSplitter` makes the model and result areas
resizable, while the log sits beneath them.

```text
python -m pyvagui -> QApplication -> MainWindow.show()
                                -> application.exec() -> close -> exit
```

Menu interaction uses signals and slots: the Exit action closes the
window, and the checkable Show log action controls log visibility.

## Concepts used

See `pyqt_primer.md`: QApplication, event loop, widgets, parent-child
ownership, QMainWindow, layouts, QSplitter, signals/slots, QAction,
QPlainTextEdit, QStatusBar, QProgressBar, and QPushButton.

## Decisions

- D-011: use a horizontal splitter with the log below the work areas.

## Tests

- `python -m pytest tests/gui/test_main_window.py`: 3 passed.
- Full `python -m pytest`: 82 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

The GUI package contained only a misspelled `__inti__.py` placeholder.
It was left untouched; a correctly named `gui/__init__.py` was added so
the package can be imported normally.

## How to verify manually

Run `python -m pyvagui`. Confirm the window opens, resize the divider
between Model tree and Results, toggle View > Show log, and choose
File > Exit.

## Comprehension questions

1. What work does `QApplication.exec()` perform while the window is open?
2. How do parent-child ownership and layouts solve different problems?
