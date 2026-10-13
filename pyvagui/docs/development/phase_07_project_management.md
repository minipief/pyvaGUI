# Phase 07 - Project Management

## Goal

Show real project objects in the main window and let users create, open,
and save project files without losing unsaved work accidentally.

## What was built

- `pyvagui/gui/main_window.py`: grouped model tree, file actions, project
  title state, save/open error reporting, and unsaved-change prompts.
- `tests/gui/test_main_window.py`: project-tree and menu-workflow tests.
- Expanded `pyqt_primer.md` with tree, user data, file dialogs, message
  boxes, and close-event concepts.
- Updated decisions and changelog.

## How it works

The tree is rebuilt from the `Project` collections. Materials are grouped
by type, with separate Layups and Solvers roots. Object rows store their
ID in `Qt.ItemDataRole.UserRole`, so later editors can resolve an object
without relying on its display name. New, Open, Save, Save As, and window
close all update or consult the project's saved/modified state.

```text
File > Open -> confirm pending changes -> choose JSON
            -> Project.load -> refresh tree/title
File > Save -> Project.save -> clear modified marker -> refresh title
```

The left tree, right results area, and lower log follow the attached
mockup's main window arrangement. The results placeholder remains empty
until result tabs and plotting are implemented in Phase 13.

## Concepts used

See `pyqt_primer.md`: QTreeWidget/QTreeWidgetItem, UserRole data,
QFileDialog, QMessageBox, and closeEvent.

## Decisions

- D-012: store model identifiers separately from tree labels.
- D-013: rebuild the tree from the Project model after project changes.

## Tests

- `python -m pytest tests/gui/test_main_window.py`: 12 passed.
- Full `python -m pytest`: 91 passed; 19 pyva deprecation warnings.
- Full `flake8`: passed with no findings.

## Problems and solutions

The Phase 6 smoke test expected the old title without a project name. It
was updated to the required `pyvaGUI - <project name>` title. Tests patch
standard dialogs so no interactive windows or user files are involved.

## How to verify manually

Run `python -m pyvagui`. Create a project, save it as JSON, open it again,
and inspect the grouped tree. Mark it modified through a project change
and try New, Open, or closing; Save, Discard, and Cancel should behave
consistently.

## Comprehension questions

1. Why does a tree row store an ID as well as showing a name?
2. Which actions use the same unsaved-change check, and what does Cancel do?
