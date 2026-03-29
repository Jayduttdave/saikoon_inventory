import os
from services.supplier_loader import normalize_name
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap, QPainter


BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

IMAGE_DIRS = [
    os.path.join(BASE_DIR, "images"),
    os.path.join(BASE_DIR, "assets", "images")
]

DEFAULT_IMAGE = os.path.join(
    IMAGE_DIRS[0],
    "no_image.png"
)

def find_image_path(filename):

    for image_dir in IMAGE_DIRS:

        path = os.path.join(
            image_dir,
            filename
        )

        if os.path.exists(path):
            return path

    return None


def create_placeholder_pixmap(size=60):

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#e5e7eb"))
    return pixmap


def center_pixmap(pixmap, size):

    if pixmap.isNull():
        return create_placeholder_pixmap(size)

    return center_pixmap(pixmap, size)

    canvas = QPixmap(size, size)
    canvas.fill(Qt.transparent)

    painter = QPainter(canvas)
    x = (size - inner.width()) // 2
    y = (size - inner.height()) // 2
    painter.drawPixmap(x, y, inner)
    painter.end()

    return canvas


def get_product_image(product, size=60):

    if not os.path.exists(IMAGE_DIRS[0]):
        os.makedirs(IMAGE_DIRS[0], exist_ok=True)

    filename = normalize_name(product).strip() + ".png"

    path = find_image_path(filename)

    if not path:
        path = find_image_path("no_image.png")

    pixmap = QPixmap(path) if path else QPixmap()

    if pixmap.isNull():
        return create_placeholder_pixmap(size)

    return pixmap.scaled(
        size,
        size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )