from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox
)

from PySide6.QtCore import QTimer, Qt, QUrl

from PySide6.QtGui import QDesktopServices

from services.database import Database
from services.pdf_report import generate_pdf_report
from services.image_loader import get_product_image
from ui.header import create_header


class OwnerWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.db = Database()

        self.setWindowTitle(
            "Tableau du propriétaire"
        )

        self.resize(
            520,
            750
        )

        self.build_ui()

        self.refresh()

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.refresh
        )

        self.timer.start(2000)

    # -----------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.addWidget(
            create_header()
        )

        title = QLabel(
            "Commandes en direct"
        )

        title.setStyleSheet(
            "font-size:20px;font-weight:bold;"
        )

        layout.addWidget(title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Rechercher dans les commandes..."
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            "padding: 12px; border-radius: 12px; "
            "border: 1px solid #d1d5db; background: white;"
        )
        self.search_input.textChanged.connect(
            self.refresh
        )

        layout.addWidget(self.search_input)

        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(True)

        self.container = QWidget()

        self.orders_layout = QVBoxLayout(
            self.container
        )

        self.scroll.setWidget(
            self.container
        )

        layout.addWidget(self.scroll)

        btn_row = QHBoxLayout()

        pdf_btn = QPushButton(
            "Télécharger PDF"
        )

        pdf_btn.clicked.connect(
            self.download_pdf
        )

        btn_row.addWidget(pdf_btn)

        clear_btn = QPushButton(
            "Effacer les commandes"
        )

        clear_btn.clicked.connect(
            self.clear_orders
        )

        btn_row.addWidget(clear_btn)

        layout.addLayout(btn_row)

        self.orders_layout.setSpacing(14)

    # -----------------

    def refresh(self):

        while self.orders_layout.count():

            item = self.orders_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

        grouped = {}

        for supplier, product, qty in self.db.all():

            if qty <= 0:
                continue

            grouped.setdefault(
                supplier,
                []
            ).append(
                (product, qty)
            )

        query = self.search_input.text().strip().lower()

        for supplier, items in grouped.items():

            card = QFrame()
            card.setStyleSheet(
                "background: white; border: 1px solid #e5e7eb; "
                "border-radius: 14px; padding: 12px;"
            )

            v = QVBoxLayout(card)

            supplier_label = QLabel(supplier)

            supplier_label.setStyleSheet(
                "font-size:18px;font-weight:bold;color:#1565c0;"
            )

            v.addWidget(supplier_label)

            grid = QGridLayout()

            row_index = 0

            if query:
                items = [
                    (product, qty)
                    for product, qty in items
                    if query in product.lower()
                ]

            if not items:
                continue

            for product, qty in items:

                img = QLabel()
                img.setFixedSize(44, 44)
                img.setAlignment(Qt.AlignCenter)
                img.setScaledContents(False)
                img.setStyleSheet(
                    "background: #f8fafc; border-radius: 10px;"
                )
                img.setPixmap(
                    get_product_image(product, 36)
                )

                name = QLabel(product)

                qty_label = QLabel(str(qty))

                grid.addWidget(img, row_index, 0)
                grid.addWidget(name, row_index, 1)
                grid.addWidget(qty_label, row_index, 2)

                row_index += 1

            v.addLayout(grid)

            self.orders_layout.addWidget(card)

        if not self.orders_layout.count():
            empty_label = QLabel(
                "Aucune commande correspondante."
            )
            empty_label.setStyleSheet(
                "color: #6b7280; font-size: 16px;"
            )
            empty_label.setAlignment(Qt.AlignCenter)
            self.orders_layout.addWidget(empty_label)

    # -----------------

    def download_pdf(self):

        orders = {}

        for supplier, product, qty in self.db.all():

            if qty > 0:

                orders.setdefault(
                    supplier,
                    []
                ).append(
                    (product, qty)
                )

        if not orders:
            QMessageBox.information(
                self,
                "PDF Report",
                "There are no active orders to export."
            )
            return

        file_path = generate_pdf_report(orders)

        if file_path:
            QMessageBox.information(
                self,
                "PDF saved",
                f"PDF report successfully saved:\n{file_path}"
            )

            QDesktopServices.openUrl(
                QUrl.fromLocalFile(file_path)
            )
        else:
            QMessageBox.critical(
                self,
                "PDF error",
                "Unable to generate the PDF report."
            )

    # -----------------

    def clear_orders(self):

        try:

            self.download_pdf()

        except:

            pass

        self.db.clear()

        self.refresh()