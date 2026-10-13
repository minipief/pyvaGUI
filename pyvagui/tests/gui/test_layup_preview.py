"""Tests for the QPainter layup stack preview."""

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage

from pyvagui.gui.layup_preview import (
    MINIMUM_LAYER_HEIGHT,
    LayupPreview,
)
from pyvagui.model.layup import LayerSpec, LayerType, Layup
from pyvagui.model.materials import EquivalentFluidSpec, FluidSpec


def make_preview(layers):
    """Build a preview and its material lookup for the supplied layers."""
    materials = [
        EquivalentFluidSpec(name="Glass wool"),
        FluidSpec(name="Air"),
    ]
    material_lookup = {material.id: material for material in materials}
    layup = Layup(layers=layers(materials))
    preview = LayupPreview(layup, material_lookup)
    return preview, materials


def test_stack_rectangles_stay_inside_area_in_incident_order(qtbot):
    """Give every layer visible height and keep all rows inside the area."""
    preview, materials = make_preview(
        lambda materials: [
            LayerSpec(
                material_id=materials[0].id,
                thickness=0.04,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id=materials[1].id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            ),
        ]
    )
    qtbot.addWidget(preview)
    area = QRect(10, 15, 100, 120)

    rectangles = preview._layout_stack_rects(area)

    assert len(rectangles) == 2
    assert rectangles[0].top() == area.top()
    assert rectangles[0].height() >= MINIMUM_LAYER_HEIGHT
    assert rectangles[0].bottom() + 1 == rectangles[1].top()
    assert rectangles[-1].bottom() == area.bottom()
    assert rectangles[0].height() > rectangles[1].height()
    assert materials[0].name == "Glass wool"


def test_thin_layers_get_minimum_height_and_below_stack_labels(qtbot):
    """Keep thin layers visible and list their labels beneath the stack."""
    preview, materials = make_preview(
        lambda items: [
            LayerSpec(
                material_id=items[0].id,
                thickness=0.001,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id=items[1].id,
                thickness=0.002,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id=items[0].id,
                thickness=0.003,
                layer_type=LayerType.FLUID,
            ),
        ]
    )
    qtbot.addWidget(preview)
    area = QRect(0, 0, 160, 60)

    rectangles = preview._layout_stack_rects(area)
    labels = preview._labels_below_stack(rectangles)

    assert all(
        rectangle.height() >= MINIMUM_LAYER_HEIGHT
        for rectangle in rectangles
    )
    assert all(rectangle.bottom() <= area.bottom() for rectangle in rectangles)
    assert labels == [
        "Glass wool - 1 mm",
        "Air - 2 mm",
        "Glass wool - 3 mm",
    ]
    assert len(materials) == 2


def test_rendered_preview_paints_material_color_and_labels(qtbot):
    """Render the widget and inspect a pixel inside the top material layer."""
    preview, materials = make_preview(
        lambda items: [
            LayerSpec(
                material_id=items[0].id,
                thickness=0.04,
                layer_type=LayerType.FLUID,
            ),
            LayerSpec(
                material_id=items[1].id,
                thickness=0.02,
                layer_type=LayerType.FLUID,
            ),
        ]
    )
    qtbot.addWidget(preview)
    preview.resize(280, 360)
    preview.show()
    qtbot.wait(30)
    image = QImage(
        preview.size(),
        QImage.Format.Format_ARGB32,
    )
    image.fill(Qt.GlobalColor.transparent)
    preview.render(image)

    color = LayupPreview._material_color(materials[0])
    rectangles = preview._layout_stack_rects(QRect(14, 64, 252, 194))
    sample_point = rectangles[0].center()

    assert image.pixelColor(sample_point) == color
    assert image.pixelColor(0, 0).alpha() > 0
    assert preview._thin_layer_labels == []
