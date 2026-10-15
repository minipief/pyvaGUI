"""Shared monochrome icons for project and material-library trees."""

from pathlib import Path

from PyQt6.QtGui import QIcon

RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources" / "icons"
TREE_ICONS = {
    name: QIcon(str(RESOURCE_PATH / f"tree-{name}.svg"))
    for name in ("folder", "material", "layup", "solver")
}

ACTION_ICONS = {
    name: QIcon(str(RESOURCE_PATH / f"action-{name}.svg"))
    for name in (
        "close",
        "down",
        "export",
        "import",
        "new",
        "open",
        "play",
        "play-white",
        "plus",
        "plus-white",
        "save",
        "stop",
        "trash",
        "up",
    )
}
