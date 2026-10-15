"""Shared light appearance for the desktop workspace and its dialogs."""

from string import Template

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QMenu

from pyvagui.gui.tree_icons import RESOURCE_PATH

COLORS = {
    "background": "#f3f5f7",
    "surface": "#ffffff",
    "surface_alt": "#f7f9fa",
    "border": "#d6dde3",
    "border_strong": "#c3ccd4",
    "text": "#1f2a33",
    "text_muted": "#66737e",
    "accent": "#167d70",
    "accent_hover": "#116a5f",
    "accent_pressed": "#0d574e",
    "accent_soft": "#dcefeb",
    "accent_faint": "#eef6f4",
    "accent_text": "#0f4d45",
    "hover": "#e9eef2",
    "handle": "#b4c0c9",
    "danger": "#b3372b",
    "danger_soft": "#fdecea",
    "danger_border": "#f1c4be",
    "success_text": "#1e6b3a",
    "success_soft": "#e7f4eb",
    "success_border": "#bfe0c9",
}

_STYLE_TEMPLATE = Template("""
* {
    font-family: "Segoe UI Variable Text", "Segoe UI";
    font-size: 10pt;
    color: $text;
}
QMainWindow, QDialog { background-color: $background; }
QLabel { background: transparent; }
QLabel#titleLabel { font-size: 13pt; font-weight: 600; }
QLabel#mutedLabel, QLabel#emptyState { color: $text_muted; }
QLabel#emptyState { font-size: 11pt; }
QLabel#errorBanner {
    background-color: $danger_soft;
    border: 1px solid $danger_border;
    border-radius: 8px;
    color: $danger;
    padding: 8px 10px;
}
QLabel#successBanner {
    background-color: $success_soft;
    border: 1px solid $success_border;
    border-radius: 8px;
    color: $success_text;
    padding: 8px 10px;
}

QTreeWidget, QListWidget, QTableWidget, QPlainTextEdit {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: 10px;
    padding: 4px;
    outline: 0;
}
QTreeWidget::item, QListWidget::item {
    padding: 5px 4px;
    border-radius: 6px;
}
QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: $accent_faint;
}
QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: $accent_soft;
    color: $accent_text;
}
QTableWidget {
    gridline-color: $border;
    selection-background-color: $accent_soft;
    selection-color: $accent_text;
}
QTableWidget QLineEdit, QTableWidget QComboBox, QTableWidget QPushButton {
    margin: 3px;
}
QHeaderView { background: transparent; }
QHeaderView::section {
    background-color: $surface;
    color: $text_muted;
    border: none;
    border-bottom: 1px solid $border;
    padding: 6px 8px;
    font-weight: 600;
}
QTableCornerButton::section { background: $surface; border: none; }
QPlainTextEdit {
    font-family: "Cascadia Mono", "Consolas";
    font-size: 9pt;
    padding: 6px;
}

QLineEdit, QComboBox, QAbstractSpinBox {
    background-color: $surface;
    border: 1px solid $border_strong;
    border-radius: 8px;
    padding: 5px 8px;
    min-height: 18px;
    selection-background-color: $accent_soft;
    selection-color: $accent_text;
}
QLineEdit:hover, QComboBox:hover, QAbstractSpinBox:hover {
    border-color: $accent;
}
QLineEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {
    border: 1px solid $accent;
    background-color: $accent_faint;
}
QLineEdit:disabled, QComboBox:disabled, QAbstractSpinBox:disabled {
    background-color: $surface_alt;
    color: $text_muted;
    border-color: $border;
}
QComboBox { padding-right: 28px; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 26px;
    border: none;
}
QComboBox::down-arrow {
    image: url("$chevron");
    width: 12px;
    height: 12px;
}
QComboBox QAbstractItemView {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 4px;
    outline: 0;
    selection-background-color: $accent_soft;
    selection-color: $accent_text;
}

QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator, QAbstractItemView::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $border_strong;
    border-radius: 5px;
    background-color: $surface;
}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover {
    border-color: $accent;
}
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {
    background-color: $accent;
    border-color: $accent;
    image: url("$check");
}
QCheckBox::indicator:disabled { background-color: $surface_alt; }

QPushButton, QToolButton {
    background-color: $surface;
    border: 1px solid $border_strong;
    border-radius: 8px;
    padding: 6px 14px;
    min-height: 18px;
}
QPushButton:hover, QToolButton:hover {
    background-color: $accent_faint;
    border-color: $accent;
}
QPushButton:pressed, QToolButton:pressed { background-color: $accent_soft; }
QPushButton:focus, QToolButton:focus { border-color: $accent; }
QPushButton#primaryButton {
    background-color: $accent;
    border-color: $accent;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: $accent_hover;
    border-color: $accent_hover;
}
QPushButton#primaryButton:pressed { background-color: $accent_pressed; }
QPushButton#dangerButton { color: $danger; border-color: $danger_border; }
QPushButton#dangerButton:hover {
    background-color: $danger_soft;
    border-color: $danger;
}
QPushButton:disabled, QToolButton:disabled,
QPushButton#primaryButton:disabled, QPushButton#dangerButton:disabled {
    color: $text_muted;
    background-color: $surface_alt;
    border-color: $border;
    font-weight: normal;
}

QGroupBox {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px 10px 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}
QGroupBox QLabel, QGroupBox QCheckBox, QGroupBox QLineEdit,
QGroupBox QComboBox, QGroupBox QListWidget { font-weight: normal; }

QTabWidget::pane {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: $text_muted;
    padding: 7px 16px;
    margin: 0 4px 6px 0;
    border-radius: 8px;
}
QTabBar::tab:hover { background-color: $hover; color: $text; }
QTabBar::tab:selected {
    background-color: $accent_soft;
    color: $accent_text;
    font-weight: 600;
}

QMenuBar {
    background-color: $surface;
    border-bottom: 1px solid $border;
    padding: 2px 4px;
}
QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 6px;
}
QMenuBar::item:selected { background-color: $hover; }
QMenuBar::item:pressed { background-color: $accent_soft; }
QMenu {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    background: transparent;
    padding: 6px 28px 6px 14px;
    border-radius: 6px;
}
QMenu::item:selected { background-color: $accent_soft; color: $accent_text; }
QMenu::item:disabled { color: $text_muted; }
QMenu::separator { height: 1px; background: $border; margin: 5px 8px; }

QStatusBar {
    background-color: $surface;
    border-top: 1px solid $border;
    color: $text_muted;
}
QStatusBar::item { border: none; }

QSplitter::handle {
    background-color: $handle;
    border-radius: 2px;
    margin: 0;
}
QSplitter::handle:hover, QSplitter::handle:pressed {
    background-color: $accent;
}

QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle { background-color: $handle; border-radius: 4px; }
QScrollBar::handle:vertical { min-height: 32px; }
QScrollBar::handle:horizontal { min-width: 32px; }
QScrollBar::handle:hover { background-color: #8fa0ac; }
QScrollBar::handle:pressed { background-color: $accent; }
QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
    border: none;
    width: 0;
    height: 0;
}
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QAbstractScrollArea::corner { background: transparent; }

QProgressBar {
    background-color: $hover;
    border: none;
    border-radius: 7px;
    min-height: 14px;
    max-height: 14px;
    min-width: 160px;
    text-align: center;
    font-size: 8pt;
}
QProgressBar::chunk { background-color: $accent; border-radius: 7px; }

QToolTip {
    background-color: $text;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 8px;
}
""")

STYLE_SHEET = _STYLE_TEMPLATE.substitute(
    COLORS,
    chevron=(RESOURCE_PATH / "chevron-down.svg").as_posix(),
    check=(RESOURCE_PATH / "check.svg").as_posix(),
)


def light_palette() -> QPalette:
    """Return a light palette independent of the operating-system theme."""
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: COLORS["background"],
        QPalette.ColorRole.WindowText: COLORS["text"],
        QPalette.ColorRole.Base: COLORS["surface"],
        QPalette.ColorRole.AlternateBase: COLORS["surface_alt"],
        QPalette.ColorRole.Text: COLORS["text"],
        QPalette.ColorRole.Button: COLORS["surface"],
        QPalette.ColorRole.ButtonText: COLORS["text"],
        QPalette.ColorRole.Highlight: COLORS["accent_soft"],
        QPalette.ColorRole.HighlightedText: COLORS["accent_text"],
        QPalette.ColorRole.ToolTipBase: COLORS["text"],
        QPalette.ColorRole.ToolTipText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: COLORS["text_muted"],
        QPalette.ColorRole.Link: COLORS["accent"],
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(
            QPalette.ColorGroup.Disabled, role, QColor(COLORS["text_muted"])
        )
    return palette


def apply_theme(application: QApplication) -> None:
    """Apply the light theme to every window of the application.

    Parameters
    ----------
    application : QApplication
        Running Qt application.
    """
    application.setStyle("Fusion")
    application.setPalette(light_palette())
    application.setStyleSheet(STYLE_SHEET)


def make_rounded_popup(menu: QMenu) -> None:
    """Let a popup menu show its rounded border without square corners.

    Parameters
    ----------
    menu : QMenu
        Menu whose window background should be transparent.
    """
    menu.setWindowFlags(
        menu.windowFlags()
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
