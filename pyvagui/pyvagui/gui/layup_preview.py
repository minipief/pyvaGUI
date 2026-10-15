"""QPainter-based cross-section preview for an ordered layup."""

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from pyvagui.gui.perforation_dialog import m_to_mm
from pyvagui.model.layup import LayerSpec, Layup
from pyvagui.model.materials import (
    DelanyBazleySpec,
    EquivalentFluidSpec,
    FluidSpec,
    IsoMatSpec,
    MaterialSpec,
    PoroElasticMatSpec,
)


MINIMUM_LAYER_HEIGHT = 20
MINIMUM_LABEL_HEIGHT = 38
MATERIAL_COLORS = {
    FluidSpec: QColor("#91b9dc"),
    EquivalentFluidSpec: QColor("#e2bd72"),
    DelanyBazleySpec: QColor("#d5a978"),
    IsoMatSpec: QColor("#afa9c9"),
    PoroElasticMatSpec: QColor("#a9c7b5"),
}


class LayupPreview(QWidget):
    """Draw layer thicknesses as a labeled vertical stack.

    Parameters
    ----------
    layup : Layup
        Ordered layers, with the incident side at index zero.
    materials : dict of str to MaterialSpec
        Project materials indexed by their identifiers.
    parent : QWidget or None, optional
        Parent widget that owns the preview.
    """

    def __init__(
        self,
        layup: Layup,
        materials: dict[str, MaterialSpec],
        parent: QWidget | None = None,
    ):
        """Create an empty preview and set its initial model data."""
        super().__init__(parent)
        self.layup = layup
        self.materials = materials
        self._thin_layer_labels: list[str] = []
        self.setMinimumSize(220, 300)

    def set_data(
        self,
        layup: Layup,
        materials: dict[str, MaterialSpec],
    ) -> None:
        """Replace preview data and schedule a repaint.

        Parameters
        ----------
        layup : Layup
            Current layer stack to draw.
        materials : dict of str to MaterialSpec
            Current project materials, indexed by id.
        """
        self.layup = layup
        self.materials = materials
        self.update()

    def _layout_stack_rects(self, area: QRect) -> list[QRect]:
        """Return top-to-bottom rectangles with a minimum visible height.

        Parameters
        ----------
        area : QRect
            Available drawing area for all layers.

        Returns
        -------
        list of QRect
            One rectangle per layer, in incident-to-receiving order.
        """
        layer_count = len(self.layup.layers)
        if layer_count == 0 or area.height() <= 0:
            return []

        minimum_height = min(
            MINIMUM_LAYER_HEIGHT,
            max(1, area.height() // layer_count),
        )
        remaining_height = area.height() - minimum_height * layer_count
        total_thickness = sum(
            max(layer.thickness, 0.0) for layer in self.layup.layers
        )
        if total_thickness <= 0:
            total_thickness = float(layer_count)

        rectangles = []
        y_position = area.top()
        for index, layer in enumerate(self.layup.layers):
            if index == layer_count - 1:
                height = area.bottom() + 1 - y_position
            else:
                thickness = max(layer.thickness, 0.0)
                if thickness == 0:
                    thickness = 1.0
                extra_height = round(
                    remaining_height * thickness / total_thickness
                )
                height = minimum_height + extra_height
            height = max(1, min(height, area.bottom() + 1 - y_position))
            rectangles.append(
                QRect(area.left(), y_position, area.width(), height)
            )
            y_position += height
        return rectangles

    def _labels_below_stack(self, rectangles: list[QRect]) -> list[str]:
        """Return labels for layers too short to hold their own text.

        Parameters
        ----------
        rectangles : list of QRect
            Layer rectangles corresponding to ``layup.layers``.

        Returns
        -------
        list of str
            Labels for thin layers, preserving their layer order.
        """
        labels = []
        for layer, rectangle in zip(self.layup.layers, rectangles):
            if rectangle.height() < MINIMUM_LABEL_HEIGHT:
                labels.append(self._layer_label(layer))
        return labels

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the preview panel, incident marker, and layer stack.

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event for the widget.
        """
        # QPainter redraws this widget whenever Qt requests a paint event.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        panel_rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QPen(QColor("#d6dde3"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(panel_rect, 10, 10)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        title_font = painter.font()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#1f2a33"))
        painter.drawText(16, 25, "Stack preview")
        title_font.setBold(False)
        painter.setFont(title_font)
        painter.setPen(QColor("#66737e"))
        painter.drawText(16, 48, "Incident side (first layer at top)")

        stack_top = 64
        labels_reserve = min(72, max(0, self.height() // 4))
        stack_bottom = max(stack_top, self.height() - labels_reserve - 12)
        stack_area = QRect(
            14,
            stack_top,
            max(1, self.width() - 28),
            max(0, stack_bottom - stack_top),
        )
        rectangles = self._layout_stack_rects(stack_area)
        self._thin_layer_labels = self._labels_below_stack(rectangles)

        for layer, rectangle in zip(self.layup.layers, rectangles):
            self._draw_layer(painter, layer, rectangle)

        if self._thin_layer_labels:
            painter.setPen(QColor("#697386"))
            text_rect = QRect(
                14,
                stack_bottom + 3,
                max(1, self.width() - 28),
                max(1, self.height() - stack_bottom - 6),
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                "Thin layers: " + " | ".join(self._thin_layer_labels),
            )
        elif not self.layup.layers:
            painter.setPen(QColor("#697386"))
            painter.drawText(
                stack_area,
                Qt.AlignmentFlag.AlignCenter,
                "No layers",
            )
        painter.end()

    def _draw_layer(
        self,
        painter: QPainter,
        layer: LayerSpec,
        rectangle: QRect,
    ) -> None:
        """Draw one colored layer and its label when the layer is tall enough.

        Parameters
        ----------
        painter : QPainter
            Active painter for this widget.
        layer : LayerSpec
            Layer model represented by this rectangle.
        rectangle : QRect
            Layer's position and size in the preview.
        """
        material = self.materials.get(layer.material_id)
        color = self._material_color(material)
        painter.fillRect(rectangle, color)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawRect(rectangle)

        if rectangle.height() < MINIMUM_LABEL_HEIGHT:
            return
        painter.setPen(QColor("#202938"))
        name = "Unknown material" if material is None else material.name
        label_rect = rectangle.adjusted(8, 4, -6, -4)
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{name}\n{m_to_mm(layer.thickness):g} mm",
        )

    @staticmethod
    def _material_color(material: MaterialSpec | None) -> QColor:
        """Return the established preview color for a material family.

        Parameters
        ----------
        material : MaterialSpec or None
            Material displayed in the layer.

        Returns
        -------
        QColor
            Fill color for the layer rectangle.
        """
        if material is None:
            return QColor("#d9dee7")
        for material_type, color in MATERIAL_COLORS.items():
            if isinstance(material, material_type):
                return QColor(color)
        return QColor("#d9dee7")

    def _layer_label(self, layer: LayerSpec) -> str:
        """Return a concise material-and-thickness label.

        Parameters
        ----------
        layer : LayerSpec
            Layer to label.

        Returns
        -------
        str
            Material name and displayed thickness.
        """
        material = self.materials.get(layer.material_id)
        name = "Unknown material" if material is None else material.name
        return f"{name} - {m_to_mm(layer.thickness):g} mm"
