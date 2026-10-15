# PyQt Primer

This glossary grows as GUI concepts are introduced. It describes the Qt
building blocks used by pyvaGUI and includes small examples from the code.

## Glossary

### QApplication and event loop

`QApplication` holds application-wide state and must exist before widgets
are shown. Its `exec()` call starts the event loop, which waits for input
and dispatches events such as clicks and repaint requests. It returns an
exit status when the application closes.

```python
application = QApplication(sys.argv)
window.show()
return application.exec()
```

### Widgets and parent-child ownership

A widget is a visible interface element, such as a window, label, or text
editor. Giving a widget a parent makes it part of the parent's object
tree; Qt then manages its lifetime with that parent. The central widget
and its child panels are owned by `MainWindow`.

```python
central_widget = QWidget(self)
self.log_panel = QPlainTextEdit(self)
```

### QMainWindow

`QMainWindow` is Qt's top-level application-window widget. It provides
dedicated areas for a menu bar, central widget, and status bar. The
application subclasses it so those areas can be assembled in one place.

```python
class MainWindow(QMainWindow):
 self.setCentralWidget(central_widget)
```

### Layouts

A layout calculates the size and position of its child widgets whenever
the window changes size. `QVBoxLayout` stacks the work area and log panel
vertically; it avoids manual pixel coordinates and works when resized.

```python
layout = QVBoxLayout(central_widget)
layout.addWidget(splitter, stretch=3)
layout.addWidget(self.log_panel, stretch=1)
```

### QSplitter

`QSplitter` places widgets side by side and lets the user drag the divider
to resize them. Its orientation selects horizontal or vertical placement.
The main window uses it for the model and results panels.

```python
splitter = QSplitter(Qt.Orientation.Horizontal, central_widget)
splitter.addWidget(self.model_panel)
splitter.addWidget(self.results_panel)
```

### Signals and slots

A signal announces that an event happened; a slot is the method that
responds. `.connect(...)` links them without polling. Here `triggered`
closes the window, and `toggled` shows or hides the log panel.

```python
exit_action.triggered.connect(self.close)
show_log_action.toggled.connect(self.log_panel.setVisible)
```

### QAction

`QAction` represents a command that can appear in a menu or toolbar.
It can also be checkable, which gives a menu command a visible on/off
state. The log visibility action is checked while the panel is visible.

```python
show_log_action = QAction("Show log", self)
show_log_action.setCheckable(True)
```

### QPlainTextEdit

`QPlainTextEdit` displays and edits plain multiline text. Setting it to
read-only makes it suitable for an application log. `appendPlainText`
adds a new message without interpreting it as markup.

```python
self.log_panel.setReadOnly(True)
self.log_panel.appendPlainText("[INFO] Ready")
```

### QStatusBar and status widgets

`QStatusBar` is the narrow area at the bottom of a `QMainWindow` for
short status messages. It can also hold permanent widgets, such as a
progress indicator or a button, which are hidden until needed.

```python
self.statusBar().showMessage("Ready")
self.statusBar().addPermanentWidget(self.progress_bar)
```

### QProgressBar and QPushButton

`QProgressBar` visualizes numeric progress; setting a range defines its
minimum and maximum. `QPushButton` is a clickable command. Both are
created in Phase 6 but remain hidden until calculation controls exist.

```python
self.progress_bar.setRange(0, 100)
self.cancel_button = QPushButton("Cancel", self)
```

### QTreeWidget and QTreeWidgetItem

`QTreeWidget` displays rows with parent-child groups without defining a
separate tree data model. `QTreeWidgetItem` is one row; adding a child
places an object inside a visible group. The project tree is rebuilt from
the project lists whenever the project changes.

```python
materials_root = self._add_group("Materials")
self._add_object_item(materials_root, material.name, material.id)
```

### Qt UserRole data

`Qt.ItemDataRole.UserRole` is a storage slot for application data attached
to a tree row. It keeps a stable object ID separate from the editable or
changeable display name. Later actions can resolve the selected model
object by ID instead of parsing its visible text.

```python
item.setData(0, Qt.ItemDataRole.UserRole, object_id)
```

### QFileDialog

`QFileDialog` is Qt's standard open/save chooser. It returns the selected
path and the selected filter; an empty path means the user cancelled.
The project window uses it for opening and saving JSON files.

```python
path, _ = QFileDialog.getOpenFileName(
  self, "Open project", "", "pyvaGUI project (*.pyvagui)"
)
if path:
 self._load_project(Path(path))
```

### QMessageBox and closeEvent

`QMessageBox` presents a standard decision or error dialog. `closeEvent`
is the callback Qt invokes when a window is about to close; accepting the
event closes it, while ignoring it keeps the current project open. The
same unsaved-change decision is used for New, Open, and window close.

```python
answer = QMessageBox.question(self, "Unsaved changes", "Save changes?")
event.ignore()  # keep the window open after Cancel
```

### QDialog

`QDialog` is a secondary window for one focused task, such as editing a
material. Calling `exec()` opens it modally, so the user completes or
cancels that task before returning to the main window. `accept()` and
`reject()` communicate the outcome.

```python
if dialog.exec() == QDialog.DialogCode.Accepted:
 project.add_material(dialog.material)
```

### Dataclass field-driven forms

Python's `dataclasses.fields()` returns the declared fields of a dataclass.
The material editor uses that list to create its inputs, so related
material types share one form-building path while showing only their own
fields.

```python
for material_field in fields(self.material_spec):
 if material_field.name not in ("name", "id"):
  self._create_field_widget(material_field)
```

### QLineEdit

`QLineEdit` is a one-line text input. It is used for material names and
floating-point parameters; the application parses the text only when the
user saves, so invalid values can be reported together.

```python
line_edit = QLineEdit(str(value), self.properties_group)
value = parse_float(line_edit.text())
```

### QCheckBox

`QCheckBox` represents a true/false value with a familiar checked state.
Its `isChecked()` method returns a Python boolean for fields such as the
limp-frame and Miki-model options.

```python
checkbox = QCheckBox(self.properties_group)
checkbox.setChecked(value)
```

### QComboBox

`QComboBox` presents a compact list of choices. Each displayed item can
carry separate data, which is useful when a frame material is displayed
by name but stored as an ID.

```python
combo.addItem(project_material.name, project_material.id)
frame_id = combo.currentData()
```

### QGroupBox and QGridLayout

`QGroupBox` visually and semantically groups related controls under a
title. `QGridLayout` places those controls into rows and columns; the
material editor fills the grid from the active spec's dataclass fields.

```python
self.properties_group = QGroupBox(self)
self.properties_layout = QGridLayout(self.properties_group)
```

### QDialogButtonBox

`QDialogButtonBox` supplies standard dialog buttons with consistent
labels and behavior. Its `accepted` and `rejected` signals connect Save
and Cancel to the dialog's validation and close operations.

```python
self.button_box.accepted.connect(self.save_material)
self.button_box.rejected.connect(self.reject)
```

### QListWidget

`QListWidget` displays a simple list without a custom item model. Its
extended-selection mode lets a user choose several library materials;
each row stores its material ID in `UserRole` data.

```python
self.material_list.setSelectionMode(
 QListWidget.SelectionMode.ExtendedSelection
)
```

### QTableWidget and cell widgets

`QTableWidget` provides a beginner-friendly grid when the data model is
small and fixed. `setCellWidget` places a real input, such as a combo box
or button, inside one cell. Qt moves table items during its default row
drag, but embedded widgets stay in their old cells, so the layup table
reorders its model and rebuilds every row instead.

```python
self.layer_table.setCellWidget(row, 1, material_combo)
self.layer_table.setCellWidget(row, 2, thickness_edit)
```

### QAbstractItemView drag-and-drop modes

`QAbstractItemView` supplies common selection and drag/drop settings for
Qt item views. `InternalMove` limits a drag to reordering rows in the same
table. The layup table overrides `dropEvent` to translate the drop into
source and destination row indices.

```python
self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
self.setDropIndicatorShown(True)
```

### QFormLayout

`QFormLayout` arranges a descriptive label beside each form input. It is
useful when there are only a few related values, such as hole radius and
hole spacing; longer dynamic material forms use a grid instead.

```python
layout = QFormLayout(self)
layout.addRow("Hole radius [mm]", self.radius_edit)
```

### QPainter and paintEvent

`paintEvent` is the QWidget callback Qt invokes when a region needs to be
redrawn. `QPainter` draws shapes, fills, and text into that widget during
the callback. The layup preview computes rectangles from the current
model and paints them from the incident side downward.

```python
def paintEvent(self, event):
  painter = QPainter(self)
  painter.fillRect(rectangle, color)
```

### QTabWidget

`QTabWidget` holds several pages and shows one at a time using tabs. The
main window creates one placeholder page per solver, so later phases can
replace each page's prompt with a calculation result and graph.

```python
self.results_tabs.addTab(page, solver.name)
```

### FigureCanvasQTAgg and Matplotlib

`FigureCanvasQTAgg` embeds a Matplotlib `Figure` inside a Qt widget. The
figure owns its axes and plotted lines; calling `canvas.draw()` redraws
it within the Qt layout. The result tab clears and rebuilds its axes when
new results or complex-view selections arrive.

```python
self.figure = Figure(tight_layout=True)
self.canvas = FigureCanvasQTAgg(self.figure)
self.canvas.draw()
```

### Logarithmic plot axes

Matplotlib axes can use logarithmic x coordinates with `set_xscale("log")`.
This is appropriate for acoustic frequency ranges spanning many orders
of magnitude. Values and labels still come from the same frequency array
used by the solver.

```python
axis.plot(result_set.frequencies, values, label=layup_name)
axis.set_xscale("log")
```

### QThread and the worker-object pattern

Long calculations on the GUI thread block Qt's event loop, so repaint and
input events cannot run and the window appears frozen. `QThread` provides
a separate execution thread; a worker `QObject` is moved to it and runs
only model calculations. The worker must not touch widgets because
widgets belong to the GUI thread.

```python
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.progress.connect(self._on_calculation_progress)
```

The worker reports progress and results through signals. Queued signal
connections deliver those updates to GUI slots on the main thread.
Cancellation is a flag checked between layups; a currently running pyva
call finishes before the worker stops.

```python
worker.finished.connect(self._on_calculation_finished)
worker.failed.connect(self._on_calculation_failed)
```
