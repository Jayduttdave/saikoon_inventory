from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QScrollArea,
    QLineEdit
)

from services.database import Database
from services.supplier_loader import load_suppliers
from services.image_loader import get_product_image
from ui.header import create_header


class OrderWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.db = Database()

        self.setWindowTitle(
            "Commandes Cuisine"
        )

        self.resize(
            1300,
            750
        )

        self.build_ui()

    # -----------------

    def build_ui(self):

        main_layout = QVBoxLayout(self)

        main_layout.addWidget(
            create_header()
        )

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Rechercher un produit..."
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            "padding: 12px; border-radius: 12px; "
            "border: 1px solid #d1d5db; background: white;"
        )
        self.search_input.textChanged.connect(
            self.filter_products
        )

        search_row.addWidget(self.search_input)

        main_layout.addLayout(search_row)

        layout = QHBoxLayout()

        main_layout.addLayout(layout)

        self.list = QListWidget()

        layout.addWidget(
            self.list,
            1
        )

        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(True)

        self.container = QWidget()

        self.products_layout = QVBoxLayout(
            self.container
        )

        self.scroll.setWidget(
            self.container
        )

        layout.addWidget(
            self.scroll,
            3
        )

        self.products_layout.setSpacing(12)

        self.suppliers = load_suppliers()

        for supplier in self.suppliers:

            self.list.addItem(
                supplier
            )

        self.list.currentTextChanged.connect(
            self.show_products
        )

        self.current_supplier = None

    # -----------------

    def show_products(
        self,
        supplier
    ):

        while self.products_layout.count():

            item = self.products_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

        self.current_supplier = supplier
        products = self.suppliers.get(
            supplier,
            []
        )
        products = self.filter_product_list(products)

        for product in products:

            row_widget = QWidget()
            row_widget.setStyleSheet(
                "background: white; border: 1px solid #e5e7eb; "
                "border-radius: 14px; padding: 12px;"
            )
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 8, 8, 8)
            row_layout.setSpacing(16)
            row_layout.setAlignment(Qt.AlignVCenter)

            img = QLabel()
            img.setFixedSize(64, 64)
            img.setAlignment(Qt.AlignCenter)
            img.setScaledContents(False)
            img.setStyleSheet(
                "background: #f8fafc; border-radius: 12px;"
            )
            img.setPixmap(
                get_product_image(product, 52)
            )
            row_layout.addWidget(img)

            name = QLabel(product)
            name.setMinimumWidth(320)
            name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            row_layout.addWidget(name)

            qty = QLineEdit()
            qty.setPlaceholderText("0")
            qty.setFixedWidth(70)
            qty.setFixedHeight(36)
            qty.setAlignment(Qt.AlignCenter)
            qty.setStyleSheet(
                "border-radius: 10px; border: 1px solid #d1d5db; "
                "padding: 8px; background: #f9fafb;"
            )
            qty.textChanged.connect(
                lambda value,
                s=supplier,
                p=product:
                self.update_order(
                    s,
                    p,
                    value
                )
            )
            row_layout.addWidget(qty)
            row_layout.addStretch()

            self.products_layout.addWidget(row_widget)

    # -----------------

    def filter_product_list(self, products):

        query = self.search_input.text().strip().lower()

        if not query:
            return products

        return [
            p for p in products
            if query in str(p).lower()
        ]

    # -----------------

    def filter_products(self, _value):

        if self.current_supplier:
            self.show_products(self.current_supplier)

    # -----------------

    def update_order(
        self,
        supplier,
        product,
        value
    ):

        try:

            qty = int(value)

        except:

            qty = 0

        self.db.upsert(
            supplier,
            product,
            qty
        )