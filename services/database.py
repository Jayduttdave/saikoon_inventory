import sqlite3
import os


BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "orders.db"
)


class Database:

    def __init__(self):

        self.conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False
        )

        self.create_table()

    def create_table(self):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                supplier TEXT,
                product TEXT,
                qty INTEGER,
                unit TEXT DEFAULT 'Pièce',
                PRIMARY KEY (supplier, product)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS custom_products (
                supplier TEXT,
                product TEXT,
                image_filename TEXT,
                PRIMARY KEY (supplier, product)
            )
            """
        )

        self.conn.commit()
        self.ensure_schema()

    def ensure_schema(self):

        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'unit' not in columns:
            cursor.execute(
                "ALTER TABLE orders ADD COLUMN unit TEXT DEFAULT 'Pièce'"
            )

        # Legacy cleanup: this app is commandes-only now.
        cursor.execute("DROP TABLE IF EXISTS stock")

        self.conn.commit()

    def upsert(
        self,
        supplier,
        product,
        qty,
        unit='Pièce'
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO orders
            (supplier, product, qty, unit)

            VALUES (?, ?, ?, ?)

            ON CONFLICT(supplier, product)
            DO UPDATE SET qty=excluded.qty, unit=excluded.unit
            """,
            (
                supplier,
                product,
                qty,
                unit
            )
        )

        self.conn.commit()

    def all(self):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT supplier, product, qty, unit
            FROM orders
            ORDER BY supplier
            """
        )

        return cursor.fetchall()

    def delete_order(self, supplier, product):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            DELETE FROM orders
            WHERE supplier = ? AND product = ?
            """,
            (supplier, product)
        )

        self.conn.commit()

    def get_custom_products(self, supplier=None):

        cursor = self.conn.cursor()

        if supplier:
            cursor.execute(
                """
                SELECT product, image_filename
                FROM custom_products
                WHERE supplier = ?
                ORDER BY product
                """,
                (supplier,)
            )
        else:
            cursor.execute(
                """
                SELECT supplier, product, image_filename
                FROM custom_products
                ORDER BY supplier, product
                """
            )

        rows = cursor.fetchall()

        if supplier:
            return [
                {
                    'product': row[0],
                    'image_filename': row[1]
                }
                for row in rows
            ]

        return [
            {
                'supplier': row[0],
                'product': row[1],
                'image_filename': row[2]
            }
            for row in rows
        ]

    def add_custom_product(self, supplier, product, image_filename=None):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO custom_products
            (supplier, product, image_filename)
            VALUES (?, ?, ?)
            ON CONFLICT(supplier, product)
            DO UPDATE SET image_filename=excluded.image_filename
            """,
            (
                supplier,
                product,
                image_filename
            )
        )

        self.conn.commit()

    def clear(self):

        cursor = self.conn.cursor()

        cursor.execute(
            "DELETE FROM orders"
        )

        self.conn.commit()