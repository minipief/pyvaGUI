"""Dialog for entering or removing a plate/mass perforation."""

import copy

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

from pyvagui.gui.material_editor import parse_float
from pyvagui.model.layup import PerforationSpec


def mm_to_m(value: float) -> float:
    """Convert millimeters to meters for model storage.

    Parameters
    ----------
    value : float
        Length in millimeters.

    Returns
    -------
    float
        Length in meters.
    """
    return value / 1000.0


def m_to_mm(value: float) -> float:
    """Convert meters from the model to millimeters for display.

    Parameters
    ----------
    value : float
        Length in meters.

    Returns
    -------
    float
        Length in millimeters.
    """
    return value * 1000.0


class PerforationDialog(QDialog):
    """Edit the radius and spacing of a perforation pattern.

    Parameters
    ----------
    perforation : PerforationSpec or None
        Existing perforation, or None to create a new one.
    parent : QWidget or None, optional
        Parent widget that owns the dialog.
    """

    def __init__(
        self,
        perforation: PerforationSpec | None,
        parent: QWidget | None = None,
    ):
        """Build the form and keep the input separate until Save."""
        super().__init__(parent)
        self.perforation = (
            None if perforation is None else copy.deepcopy(perforation)
        )
        self.result_perforation: PerforationSpec | None = None
        self.setWindowTitle("Perforation")

        # QFormLayout places one descriptive label beside each input field.
        layout = QFormLayout(self)
        radius_mm = 1.0
        distance_mm = 20.0
        if self.perforation is not None:
            radius_mm = m_to_mm(self.perforation.hole_radius)
            distance_mm = m_to_mm(self.perforation.distance)
        self.radius_edit = QLineEdit(f"{radius_mm:g}", self)
        self.distance_edit = QLineEdit(f"{distance_mm:g}", self)
        layout.addRow("Hole radius [mm]", self.radius_edit)
        layout.addRow("Hole distance [mm]", self.distance_edit)

        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addRow(self.error_label)

        buttons = QHBoxLayout()
        self.remove_button = QPushButton("Remove perforation", self)
        self.remove_button.setVisible(self.perforation is not None)
        self.remove_button.clicked.connect(self.remove_perforation)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save,
            parent=self,
        )
        self.button_box.accepted.connect(self.save_perforation)
        self.button_box.rejected.connect(self.reject)
        buttons.addWidget(self.button_box)
        layout.addRow(buttons)

    def save_perforation(self) -> None:
        """Parse millimeter inputs, validate, and accept valid values."""
        radius_mm = parse_float(self.radius_edit.text())
        distance_mm = parse_float(self.distance_edit.text())
        errors = []
        if radius_mm is None:
            errors.append("Hole radius must be a finite number.")
        if distance_mm is None:
            errors.append("Hole distance must be a finite number.")
        if errors:
            self._show_errors(errors)
            return

        perforation = PerforationSpec(
            hole_radius=mm_to_m(radius_mm),
            distance=mm_to_m(distance_mm),
        )
        errors = perforation.validate()
        if errors:
            self._show_errors(errors)
            return
        self.result_perforation = perforation
        self.accept()

    def remove_perforation(self) -> None:
        """Accept the dialog with no perforation attached."""
        self.result_perforation = None
        self.accept()

    def _show_errors(self, errors: list[str]) -> None:
        """Display all input and geometry errors without closing the dialog.

        Parameters
        ----------
        errors : list of str
            Messages explaining why the perforation cannot be saved.
        """
        self.error_label.setText("\n".join(errors))
        self.error_label.show()
        QMessageBox.warning(self, "Invalid perforation", "\n".join(errors))
