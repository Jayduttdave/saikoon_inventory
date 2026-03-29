import os

from PySide6.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QWidget
)

from PySide6.QtGui import QPixmap


def create_header():

    header = QWidget()

    layout = QHBoxLayout(header)

    logo = QLabel()

    base_dir = os.path.dirname(
        os.path.dirname(__file__)
    )

    logo_path = os.path.join(
        base_dir,
        "assets",
        "images",
        "logo.png"
    )

    pixmap = QPixmap(logo_path)

    if not pixmap.isNull():
        logo.setPixmap(
            pixmap.scaled(
                40,
                40
            )
        )

    title = QLabel(
        "Saikoon Kitchen System"
    )

    title.setStyleSheet(
        "font-size:18px;font-weight:bold;"
    )

    layout.addWidget(logo)

    layout.addWidget(title)

    layout.addStretch()

    return header