"""Smoke tests for the initial PyQt6 main window."""

import json

import numpy as np
import pytest
from PyQt6.QtCore import QProcess, QTimer, Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QDialog,
    QMessageBox,
    QMenuBar,
    QPlainTextEdit,
    QScrollBar,
    QSplitter,
)

from pyvagui.gui.main_window import MainWindow
from pyvagui.gui.result_tab import ResultTab
from pyvagui.gui.tree_icons import ACTION_ICONS, TREE_ICONS
from pyvagui.model.layup import LayerSpec, LayerType, Layup
from pyvagui.model.materials import EquivalentFluidSpec, FluidSpec, IsoMatSpec
from pyvagui.model.project import Project
from pyvagui.model.library import MaterialLibrary
from pyvagui.model.solvers import (
    FrequencySettings,
    SolverSpec,
    SolverType,
)


def test_main_window_has_menus_splitter_log_and_status(qtbot):
    """Create the main UI shell and verify its primary widgets."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert window.windowTitle() == "pyvaGUI - Untitled project"
    assert isinstance(window.menuBar(), QMenuBar)
    assert isinstance(window.splitter, QSplitter)
    assert not window.delete_project_item_action.icon().isNull()
    assert not window.run_calculation_action.icon().isNull()
    assert not window.cancel_calculation_action.icon().isNull()
    assert all(not icon.isNull() for icon in TREE_ICONS.values())
    assert all(not icon.isNull() for icon in ACTION_ICONS.values())
    assert window.splitter.orientation().value == 1
    assert isinstance(window.log_panel, QPlainTextEdit)
    assert window.log_panel.isReadOnly()
    assert window.statusBar().currentMessage() == "Ready"
    assert not window.progress_bar.isVisible()
    assert not window.cancel_button.isVisible()


def test_keyboard_shortcuts_trigger_save_and_current_calculation(
    qtbot, monkeypatch
):
    """Route global shortcuts through the same app actions as the menus."""
    project, solver = make_solver_project()
    calls = []
    monkeypatch.setattr(
        MainWindow,
        "save_project",
        lambda self: calls.append("save"),
    )
    monkeypatch.setattr(
        MainWindow,
        "run_solver",
        lambda self, solver_id: calls.append(solver_id),
    )
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)

    window.log_panel.setFocus()
    qtbot.keyClick(
        window.log_panel,
        Qt.Key.Key_S,
        modifier=Qt.KeyboardModifier.ControlModifier,
    )
    qtbot.keyClick(window, Qt.Key.Key_F5)

    assert calls == ["save", solver.id]
    assert window.new_project_action.shortcut().toString() == "Ctrl+N"
    assert window.open_project_action.shortcut().toString() == "Ctrl+O"
    assert window.save_project_action.shortcut().toString() == "Ctrl+S"
    assert window.save_project_as_action.shortcut().toString() == (
        "Ctrl+Shift+S"
    )
    assert window.cancel_calculation_action.shortcut().toString() == (
        "Shift+F5"
    )


def test_panels_resize_and_tree_fits_content(qtbot):
    """Give navigation its content width and let users resize both panels."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert window.model_tree.indentation() == 14
    assert window.splitter.sizes()[0] < window.width() // 4
    assert window.log_splitter.orientation() == Qt.Orientation.Vertical
    assert window.log_splitter.widget(1) is window.log_panel
    assert window.splitter.handleWidth() == 7
    assert window.log_splitter.handleWidth() == 7
    initial_width = window.splitter.sizes()[0]
    window.refresh_project_view()
    window.refresh_project_view()
    assert window.splitter.sizes()[0] == initial_width
    before = window.log_splitter.sizes()[1]
    window.log_splitter.setSizes([400, 400])
    assert window.log_splitter.sizes()[1] > before

    window.project.add_material(FluidSpec(name="A much longer material name"))
    previous_width = window.splitter.sizes()[0]
    window.refresh_project_view()
    assert window.splitter.sizes()[0] > previous_width
    window.project = Project()
    window.refresh_project_view()
    assert window.splitter.sizes()[0] == initial_width


def test_empty_tree_groups_keep_expansion_indicators(qtbot):
    """Empty folders still have a branch indicator, unlike object leaves."""
    window = MainWindow()
    qtbot.addWidget(window)
    root = window.model_tree.topLevelItem(0)
    policy = root.ChildIndicatorPolicy.ShowIndicator

    assert root.childIndicatorPolicy() == policy
    assert root.child(0).childCount() == 0
    assert root.child(0).childIndicatorPolicy() == policy
    assert window.model_tree.topLevelItem(1).childIndicatorPolicy() == policy


def test_menus_use_translucent_rounded_popups(qtbot):
    """Let every menu draw rounded corners without a square backdrop."""
    window = MainWindow()
    qtbot.addWidget(window)

    menus = [action.menu() for action in window.menuBar().actions()]

    assert [menu.title() for menu in menus][-1] == "Help"
    assert not menus[-1].isEmpty()
    for menu in menus:
        assert menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert menu.windowFlags() & Qt.WindowType.FramelessWindowHint


@pytest.mark.parametrize("orientation", [
    Qt.Orientation.Vertical, Qt.Orientation.Horizontal
])
def test_modern_scrollbars_keep_compact_size_and_scroll(qtbot, orientation):
    """Keep custom scrollbar geometry stable and preserve scrolling."""
    window = MainWindow()
    qtbot.addWidget(window)
    scrollbar = QScrollBar(orientation, window)
    scrollbar.setRange(0, 100)
    scrollbar.setPageStep(20)
    scrollbar.ensurePolished()

    if orientation == Qt.Orientation.Vertical:
        assert scrollbar.sizeHint().width() == 12
    else:
        assert scrollbar.sizeHint().height() == 12
    scrollbar.setValue(50)
    assert scrollbar.value() == 50
    scrollbar.triggerAction(scrollbar.SliderAction.SliderPageStepAdd)
    assert scrollbar.value() == 70


def test_project_tree_groups_materials_and_stores_object_ids(qtbot):
    """Group model objects and keep stable ids separate from display names."""
    air = FluidSpec(name="Air")
    fibre = EquivalentFluidSpec(name="Glass wool")
    aluminium = IsoMatSpec(name="Aluminium")
    project = Project(
        name="Absorber",
        materials=[air, fibre, aluminium],
    )
    window = MainWindow(project)
    qtbot.addWidget(window)

    materials_root = window.model_tree.topLevelItem(0)
    fluid_group = materials_root.child(0)
    equivalent_group = materials_root.child(1)
    isomat_group = materials_root.child(3)

    assert materials_root.text(0) == "Materials"
    assert fluid_group.child(0).text(0) == "Air"
    assert fluid_group.child(0).data(0, Qt.ItemDataRole.UserRole) == air.id
    assert equivalent_group.child(0).text(0) == "Glass wool"
    assert equivalent_group.child(0).data(
        0, Qt.ItemDataRole.UserRole
    ) == fibre.id
    assert (
        isomat_group.child(0).data(0, Qt.ItemDataRole.UserRole)
        == aluminium.id
    )
    assert not materials_root.flags() & Qt.ItemFlag.ItemIsEditable
    assert window.windowTitle() == "pyvaGUI - Absorber"


def test_project_tree_uses_distinct_icons_for_each_object_type(qtbot):
    """Give folders and every project object type distinct icons."""
    air = FluidSpec(name="Air")
    layup = Layup(name="Absorber")
    solver = SolverSpec(
        name="Absorption",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=20.0, f_end=20000.0, n_points=100
        ),
    )
    window = MainWindow(
        Project(materials=[air], layups=[layup], solvers=[solver])
    )
    qtbot.addWidget(window)

    materials = window.model_tree.topLevelItem(0)
    material_item = materials.child(0).child(0)
    layup_root = window.model_tree.topLevelItem(1)
    solver_root = window.model_tree.topLevelItem(2)
    layup_item = layup_root.child(0)
    solver_item = solver_root.child(0)

    assert not materials.icon(0).isNull()
    assert not layup_root.icon(0).isNull()
    assert not solver_root.icon(0).isNull()
    assert not material_item.icon(0).isNull()
    assert not layup_item.icon(0).isNull()
    assert not solver_item.icon(0).isNull()
    assert material_item.icon(0).cacheKey() != layup_item.icon(0).cacheKey()
    assert layup_item.icon(0).cacheKey() != solver_item.icon(0).cacheKey()


def test_delete_materials_from_selected_project_folder(
    qtbot, monkeypatch
):
    """Delete every material inside a selected project category folder."""
    project = Project(materials=[
        FluidSpec(name="Air"),
        FluidSpec(name="Water"),
    ])
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.model_tree.topLevelItem(0).child(0).setSelected(True)
    confirmations = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: confirmations.append(args)
        or QMessageBox.StandardButton.Yes,
    )

    deleted = window.delete_selected_project_items()

    assert deleted
    assert project.materials == []
    assert project.is_modified
    assert len(confirmations) == 1


def test_delete_selected_layup_and_solver(qtbot, monkeypatch):
    """Delete layups and their selected solver together from folders."""
    layup = Layup(name="Absorber")
    solver = SolverSpec(
        name="Absorption",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=20.0, f_end=20000.0, n_points=100
        ),
        layup_ids=[layup.id],
    )
    project = Project(layups=[layup], solvers=[solver])
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.model_tree.topLevelItem(1).setSelected(True)
    window.model_tree.topLevelItem(2).setSelected(True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    assert window.delete_selected_project_items()
    assert project.layups == []
    assert project.solvers == []


def test_delete_material_in_use_is_blocked(qtbot, monkeypatch):
    """Keep project materials that are still referenced by a layup."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Air gap",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.01,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    project = Project(materials=[air], layups=[layup])
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.model_tree.topLevelItem(0).child(0).child(0).setSelected(True)
    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: warnings.append(message),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: pytest.fail("Referenced material must not prompt"),
    )

    assert not window.delete_selected_project_items()
    assert project.materials == [air]
    assert any("Air gap" in message for message in warnings)


def test_project_tree_refresh_shows_unsaved_marker(qtbot):
    """Reflect project dirty state and new objects in the model tree."""
    project = Project(name="Absorber")
    window = MainWindow(project)
    qtbot.addWidget(window)
    material = FluidSpec(name="Water")
    project.add_material(material)

    window.refresh_project_view()

    assert window.windowTitle() == "pyvaGUI - Absorber*"
    assert (
        window.model_tree.topLevelItem(0).child(0).child(0).text(0)
        == "Water"
    )


def test_closing_library_preserves_tree_and_running_tab_state(
    qtbot, monkeypatch, tmp_path
):
    """Keep tree expansion, selection, and disabled Run after library close."""
    project, solver = make_solver_project()
    library_material = FluidSpec(name="Library fluid")
    library = MaterialLibrary(tmp_path / "library.json")
    library.materials = [library_material]
    window = MainWindow(project)
    qtbot.addWidget(window)
    materials_root = window.model_tree.topLevelItem(0)
    fluid_group = materials_root.child(0)
    solver_root = window.model_tree.topLevelItem(2)
    solver_item = solver_root.child(0)
    materials_root.setExpanded(False)
    fluid_group.setExpanded(False)
    solver_root.setExpanded(False)
    solver_item.setSelected(True)
    result_tab = window.results_tabs.widget(0)
    window._set_calculation_busy(True)

    def add_from_library(dialog):
        material = dialog.library.materials[0].copy_with_new_id()
        dialog.project.add_material(material)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(window, "_get_material_library", lambda: library)
    monkeypatch.setattr(
        "pyvagui.gui.main_window.LibraryDialog.exec",
        add_from_library,
    )

    window.open_library()

    materials_root = window.model_tree.topLevelItem(0)
    fluid_group = materials_root.child(0)
    solver_root = window.model_tree.topLevelItem(2)
    assert not materials_root.isExpanded()
    assert not fluid_group.isExpanded()
    assert not solver_root.isExpanded()
    assert solver_root.child(0).isSelected()
    assert fluid_group.childCount() == 2
    assert window.results_tabs.widget(0) is result_tab
    assert not result_tab.run_button.isEnabled()
    assert window.cancel_calculation_action.isEnabled()


def test_log_adds_timestamped_severity_and_message(qtbot):
    """Add a readable severity-tagged line to the read-only log panel."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.log("warning", "Calculation is waiting")

    entry = window.log_panel.toPlainText()
    assert "[WARNING] Calculation is waiting" in entry
    assert len(entry.split(" ", maxsplit=1)[0]) == 10


def test_log_rejects_unknown_severity(qtbot):
    """Reject misspelled log severity levels."""
    window = MainWindow()
    qtbot.addWidget(window)

    with pytest.raises(ValueError, match="TRACE"):
        window.log("TRACE", "Not supported")


def test_save_and_load_project_updates_window_state(qtbot, tmp_path):
    """Persist and reload through the same operations used by File actions."""
    project = Project(name="Saved absorber", materials=[FluidSpec(name="Air")])
    window = MainWindow(project)
    qtbot.addWidget(window)
    project.is_modified = True
    path = tmp_path / "absorber.pyvagui"

    assert window._save_project_to(path)
    assert window.windowTitle() == "pyvaGUI - absorber.pyvagui"
    assert not project.is_modified
    saved_data = json.loads(path.read_text(encoding="utf-8"))
    assert saved_data["format_version"] == 1
    assert saved_data["name"] == "Saved absorber"

    window.project = Project(name="Temporary")
    assert window._load_project(path)
    assert window.project.name == "Saved absorber"
    assert window.project.file_path == path
    assert window.windowTitle() == "pyvaGUI - absorber.pyvagui"
    assert window.model_tree.topLevelItem(0).child(0).child(0).text(0) == "Air"


def test_open_project_action_loads_selected_file(qtbot, monkeypatch, tmp_path):
    """Open the selected project through the File menu action handler."""
    path = tmp_path / "selected.pyvagui"
    Project(name="Selected", materials=[FluidSpec(name="Air")]).save(path)
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: (str(path), "pyvaGUI project (*.pyvagui)"),
    )

    window.open_project_action.trigger()

    assert window.project.name == "Selected"
    assert window.windowTitle() == "pyvaGUI - selected.pyvagui"
    assert (
        "Opened project 'selected.pyvagui'."
        in window.log_panel.toPlainText()
    )
    assert window.model_tree.topLevelItem(0).child(0).child(0).text(0) == "Air"


def test_save_as_action_adds_pyvagui_extension(qtbot, monkeypatch, tmp_path):
    """Append the project suffix when the save dialog omits one."""
    window = MainWindow(Project(name="My absorber"))
    qtbot.addWidget(window)
    path = tmp_path / "saved-project"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args: (str(path), "pyvaGUI project (*.pyvagui)"),
    )

    window.save_project_as_action.trigger()

    assert (tmp_path / "saved-project.pyvagui").exists()
    assert window.project.file_path == tmp_path / "saved-project.pyvagui"
    assert window.windowTitle() == "pyvaGUI - saved-project.pyvagui"


def test_save_as_replaces_json_suffix_with_pyvagui(
    qtbot, monkeypatch, tmp_path
):
    """Do not create new project files with the retired JSON extension."""
    window = MainWindow(Project(name="My absorber"))
    qtbot.addWidget(window)
    path = tmp_path / "legacy-name.json"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args: (str(path), "pyvaGUI project (*.pyvagui)"),
    )

    window.save_project_as_action.trigger()

    assert not path.exists()
    assert (tmp_path / "legacy-name.pyvagui").exists()


def test_new_project_action_discards_changes_when_confirmed(
    qtbot,
    monkeypatch,
):
    """Replace the project after the user confirms discard."""
    window = MainWindow(Project(name="Changed", is_modified=True))
    qtbot.addWidget(window)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Discard,
    )

    window.new_project_action.trigger()

    assert window.project.name == "Untitled project"
    assert window.project.is_modified is False
    assert window.windowTitle() == "pyvaGUI - Untitled project"


def test_new_layup_action_adds_editor_result(qtbot, monkeypatch):
    """Add a valid layup returned by the New Layup dialog."""
    air = FluidSpec(name="Air")
    project = Project(materials=[air])
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_layup(dialog):
        dialog.result_layup = Layup(
            name="Air gap",
            layers=[
                LayerSpec(
                    material_id=air.id,
                    thickness=0.02,
                    layer_type=LayerType.FLUID,
                )
            ],
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.LayupEditorDialog.exec",
        accept_layup,
    )

    window.new_layup_action.trigger()

    assert len(project.layups) == 1
    assert project.layups[0].name == "Air gap"
    assert project.is_modified
    assert window.model_tree.topLevelItem(1).child(0).text(0) == "Air gap"


def test_double_click_handler_updates_existing_layup(qtbot, monkeypatch):
    """Commit an accepted edit to an existing tree-selected layup."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Original",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    project = Project(materials=[air], layups=[layup])
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_edit(dialog):
        dialog.result_layup = Layup(
            id=dialog.layup.id,
            name="Edited",
            layers=dialog.layup.layers,
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.LayupEditorDialog.exec",
        accept_edit,
    )
    layup_item = window.model_tree.topLevelItem(1).child(0)

    window.edit_tree_item(layup_item)

    assert project.layups[0].name == "Edited"
    assert project.is_modified
    assert window.model_tree.topLevelItem(1).child(0).text(0) == "Edited"


def test_new_solver_action_adds_result_tab(qtbot, monkeypatch):
    """Add an accepted solver and create its matching placeholder tab."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Absorber",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.05,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    project = Project(materials=[air], layups=[layup])
    solver = SolverSpec(
        name="Normal absorption",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=11,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[layup.id],
    )
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_solver(dialog):
        dialog.result_solver = solver
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.SolverEditorDialog.exec",
        accept_solver,
    )

    window.new_solver_action.trigger()

    assert project.solvers == [solver]
    assert project.is_modified
    assert window.model_tree.topLevelItem(2).child(0).text(0) == solver.name
    assert window.results_tabs.count() == 1
    assert window.results_tabs.tabText(0) == solver.name
    assert window.results_tabs.widget(0).property("solver_id") == solver.id


def test_double_click_handler_updates_existing_solver(qtbot, monkeypatch):
    """Commit an accepted solver edit from its project tree item."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Absorber",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.05,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    solver = SolverSpec(
        name="Original solver",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=10000.0,
            n_points=11,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[layup.id],
    )
    project = Project(materials=[air], layups=[layup], solvers=[solver])
    window = MainWindow(project)
    qtbot.addWidget(window)

    def accept_edit(dialog):
        dialog.result_solver = SolverSpec(
            id=solver.id,
            name="Edited solver",
            solver_type=solver.solver_type,
            frequencies=solver.frequencies,
            sending_fluid_id=solver.sending_fluid_id,
            receiving_fluid_id=solver.receiving_fluid_id,
            layup_ids=solver.layup_ids,
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.SolverEditorDialog.exec",
        accept_edit,
    )
    solver_item = window.model_tree.topLevelItem(2).child(0)

    window.edit_tree_item(solver_item)

    assert project.solvers[0].name == "Edited solver"
    assert project.is_modified
    assert window.results_tabs.tabText(0) == "Edited solver"


def make_solver_project():
    """Create a valid solver project for threaded GUI tests."""
    air = FluidSpec(name="Air")
    layup = Layup(
        name="Air layer",
        layers=[
            LayerSpec(
                material_id=air.id,
                thickness=0.05,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    solver = SolverSpec(
        name="Absorption run",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=100.0,
            f_end=1000.0,
            n_points=3,
        ),
        sending_fluid_id=air.id,
        receiving_fluid_id=air.id,
        layup_ids=[layup.id],
    )
    return Project(materials=[air], layups=[layup], solvers=[solver]), solver


def test_run_solver_uses_process_and_updates_result_tab(qtbot):
    """Run pyva in a child process and pass its result back to the GUI."""
    project, solver = make_solver_project()
    window = MainWindow(project)
    qtbot.addWidget(window)

    assert window.run_solver(solver.id)
    assert isinstance(window.calculation_process, QProcess)
    qtbot.waitUntil(
        lambda: window.calculation_process is None,
        timeout=15000,
    )

    result = window.result_sets[solver.id]
    result_tab = window.results_tabs.widget(0)
    assert isinstance(result_tab, ResultTab)
    assert len(result.results) == 1
    assert result.results[0].values.shape == (3,)
    assert result_tab.result_placeholder.text() == (
        "1 layup results calculated"
    )
    assert len(result_tab.axes) == 1
    assert result_tab.axes[0].get_xscale() == "log"
    assert np.array_equal(
        result_tab.axes[0].lines[0].get_ydata(),
        result.results[0].values,
    )
    assert not window.progress_bar.isVisible()
    assert not window.cancel_button.isVisible()


def test_frozen_calculation_launches_same_executable_in_worker_mode(
    qtbot, monkeypatch, tmp_path
):
    """Pass file IPC paths to the frozen app's worker-only startup mode."""
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(
        "pyvagui.gui.main_window.sys.frozen",
        True,
        raising=False,
    )
    payload_path = tmp_path / "input.json"
    message_path = tmp_path / "messages.jsonl"

    arguments = window._calculation_process_arguments(
        payload_path,
        message_path,
    )

    assert arguments == [
        "--calculation-worker",
        str(payload_path),
        str(message_path),
    ]


def test_complex_result_round_trips_from_calculation_process(qtbot):
    """Preserve complex impedance values across the process boundary."""
    project, solver = make_solver_project()
    solver.solver_type = SolverType.IMPEDANCE
    solver.angle_deg = 30.0
    fluid = project.materials[0]
    fluid.rho0 = 1.5
    fluid.c0 = 320.0
    window = MainWindow(project)
    qtbot.addWidget(window)

    assert window.run_solver(solver.id)
    qtbot.waitUntil(
        lambda: window.calculation_process is None,
        timeout=15000,
    )

    result = window.result_sets[solver.id]
    values = result.results[0].values
    assert values.shape == (solver.frequencies.n_points,)
    assert np.iscomplexobj(values)
    assert np.all(np.isfinite(values))
    assert result.reference_impedance == 480.0
    assert result.angle_deg == 30.0
    assert "normalized_magnitude" in result.display_views()
    assert "reflection_phase" in result.display_views()


def test_real_calculation_keeps_gui_timer_responsive(qtbot):
    """Keep processing GUI events while pyva calculates in a process."""
    project, solver = make_solver_project()
    solver.frequencies.n_points = 20000
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.show()
    active_ticks = []
    timer = QTimer(window)
    timer.setInterval(1)

    def record_tick():
        process = window.calculation_process
        if (
            process is not None
            and process.state() != QProcess.ProcessState.NotRunning
        ):
            active_ticks.append(True)

    timer.timeout.connect(record_tick)
    timer.start()

    assert window.run_solver(solver.id)
    qtbot.waitUntil(
        lambda: window.calculation_process is None,
        timeout=30000,
    )
    timer.stop()

    assert active_ticks


def test_result_tab_run_button_passes_its_solver_id(qtbot, monkeypatch):
    """Use the tab's solver identifier, not the clicked(bool) signal value."""
    project, solver = make_solver_project()
    window = MainWindow(project)
    qtbot.addWidget(window)
    calls = []
    monkeypatch.setattr(
        window,
        "run_solver",
        lambda solver_id: calls.append(solver_id),
    )

    window.results_tabs.widget(0).run_button.click()

    assert calls == [solver.id]


def test_cancel_button_stops_child_process(qtbot):
    """Terminate a running calculation process without blocking the GUI."""
    project, solver = make_solver_project()
    second_layup = Layup(
        name="Second layer",
        layers=[
            LayerSpec(
                material_id=project.materials[0].id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            )
        ],
    )
    project.add_layup(second_layup)
    solver.layup_ids.append(second_layup.id)
    solver.frequencies.n_points = 200000
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.show()

    assert window.run_solver(solver.id)
    qtbot.waitUntil(
        lambda: window._calculation_metadata is not None,
        timeout=10000,
    )
    assert window.cancel_button.isVisible()
    window.cancel_button.click()
    qtbot.waitUntil(
        lambda: window.calculation_process is None,
        timeout=10000,
    )

    assert not window.cancel_button.isVisible()


def test_calculation_failure_is_reported_and_clears_busy_state(
    qtbot, monkeypatch
):
    """Report child errors and restore calculation controls."""
    window = MainWindow()
    qtbot.addWidget(window)
    errors = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, message: errors.append(message),
    )
    window._set_calculation_busy(True)

    window._on_calculation_failed("test calculation failure")
    window._finish_calculation_process()

    assert errors == ["test calculation failure"]
    assert window.result_sets == {}
    assert not window.progress_bar.isVisible()
    assert not window.cancel_button.isVisible()


def test_run_solver_validation_blocks_worker_start(qtbot, monkeypatch):
    """Show project validation errors before creating a calculation thread."""
    solver = SolverSpec(
        name=" ",
        solver_type=SolverType.ABSORPTION,
        frequencies=FrequencySettings(
            f_start=0.0,
            f_end=100.0,
            n_points=1,
        ),
    )
    project = Project(solvers=[solver])
    window = MainWindow(project)
    qtbot.addWidget(window)
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: messages.append(message),
    )

    started = window.run_solver(solver.id)

    assert started is False
    assert window.calculation_process is None
    assert len(messages) == 1
    assert "Solver name must not be empty" in messages[0]
    assert "Number of points must be an integer" in messages[0]


def test_close_during_calculation_requests_cancel_and_defers_close(
    qtbot,
):
    """Cancel a child process and leave the window alive until it exits."""
    project, solver = make_solver_project()
    solver.frequencies.n_points = 200000
    window = MainWindow(project)
    qtbot.addWidget(window)
    window.show()

    assert window.run_solver(solver.id)
    qtbot.waitUntil(
        lambda: window._calculation_metadata is not None,
        timeout=10000,
    )
    close_result = window.close()
    assert close_result is False
    assert window.isVisible()
    qtbot.waitUntil(
        lambda: window.calculation_process is None,
        timeout=10000,
    )

    assert window.isVisible()


def test_end_to_end_project_creation_to_result_curve(
    qtbot,
    monkeypatch,
    tmp_path,
):
    """Create model objects, run the worker, and plot its result."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.new_project()
    library = MaterialLibrary(tmp_path / "library.json")
    monkeypatch.setattr(window, "_get_material_library", lambda: library)
    materials_to_add = iter(
        [
            FluidSpec(name="Air"),
            EquivalentFluidSpec(name="Glass wool"),
        ]
    )

    def accept_material(dialog):
        dialog.material = next(materials_to_add)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.MaterialEditorDialog.exec",
        accept_material,
    )
    window.new_material_action.trigger()
    window.new_material_action.trigger()
    air = next(item for item in window.project.materials if item.name == "Air")
    wool = next(
        item
        for item in window.project.materials
        if item.name == "Glass wool"
    )

    def accept_layup(dialog):
        dialog.result_layup = Layup(
            name="Glass wool absorber",
            layers=[
                LayerSpec(
                    material_id=wool.id,
                    thickness=0.1,
                    layer_type=LayerType.FLUID,
                )
            ],
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.LayupEditorDialog.exec",
        accept_layup,
    )
    window.new_layup_action.trigger()
    layup = window.project.layups[0]

    def accept_solver(dialog):
        dialog.result_solver = SolverSpec(
            name="Normal absorption",
            solver_type=SolverType.ABSORPTION,
            frequencies=FrequencySettings(
                f_start=100.0,
                f_end=1000.0,
                n_points=5,
            ),
            sending_fluid_id=air.id,
            receiving_fluid_id=air.id,
            layup_ids=[layup.id],
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "pyvagui.gui.main_window.SolverEditorDialog.exec",
        accept_solver,
    )
    window.new_solver_action.trigger()
    solver = window.project.solvers[0]
    assert window.run_solver(solver.id)
    qtbot.waitUntil(
        lambda: window.calculation_process is None,
        timeout=15000,
    )

    result_tab = window.results_tabs.widget(0)
    assert isinstance(result_tab, ResultTab)
    assert len(result_tab.axes) == 1
    assert len(result_tab.axes[0].lines) == 1
    assert list(result_tab.axes[0].lines[0].get_xdata()) == list(
        solver.frequencies.frequencies()
    )
    assert len(window.result_sets[solver.id].results) == 1
    qtbot.wait(50)


def test_close_event_is_ignored_when_prompt_is_cancelled(
    qtbot,
    monkeypatch,
):
    """Keep a visible window open when the user cancels closing."""
    window = MainWindow(Project(name="Changed", is_modified=True))
    qtbot.addWidget(window)
    window.show()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Cancel,
    )

    closed = window.close()

    assert closed is False
    assert window.isVisible()


@pytest.mark.parametrize(
    ("answer", "should_continue"),
    [
        (QMessageBox.StandardButton.Discard, True),
        (QMessageBox.StandardButton.Cancel, False),
    ],
)
def test_unsaved_changes_prompt_honors_discard_and_cancel(
    qtbot,
    monkeypatch,
    answer,
    should_continue,
):
    """Only discard continues; cancellation preserves the current project."""
    project = Project(name="Changed", is_modified=True)
    window = MainWindow(project)
    qtbot.addWidget(window)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: answer)

    result = window._confirm_discard_changes()

    assert result is should_continue
    assert window.project is project
