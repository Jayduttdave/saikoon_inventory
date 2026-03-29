import sys

from PySide6.QtWidgets import QApplication

from ui.order_window import OrderWindow
from ui.owner_window import OwnerWindow


app = QApplication(sys.argv)

app.setStyleSheet("""

QWidget {
    font-family: Segoe UI;
    background-color: #f3f4f6;
}

QListWidget {
    background: white;
    border-radius: 10px;
    padding: 6px;
}

QListWidget::item {
    padding: 14px;
    border-radius: 8px;
}

QListWidget::item:selected {
    background: #2563eb;
    color: white;
}

QLineEdit {
    padding: 10px;
    font-size: 16px;
    border-radius: 8px;
    border: 1px solid #d1d5db;
}

QPushButton {
    padding: 14px;
    font-size: 16px;
    border-radius: 10px;
    background: #dc2626;
    color: white;
}

QPushButton:hover {
    background: #b91c1c;
}

""")

kitchen = OrderWindow()

owner = OwnerWindow()

kitchen.show()

owner.show()

sys.exit(app.exec())