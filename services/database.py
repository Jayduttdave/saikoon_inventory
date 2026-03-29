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
                PRIMARY KEY (supplier, product)
            )
            """
        )

        self.conn.commit()

    def upsert(
        self,
        supplier,
        product,
        qty
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO orders
            (supplier, product, qty)

            VALUES (?, ?, ?)

            ON CONFLICT(supplier, product)
            DO UPDATE SET qty=excluded.qty
            """,
            (
                supplier,
                product,
                qty
            )
        )

        self.conn.commit()

    def all(self):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT supplier, product, qty
            FROM orders
            ORDER BY supplier
            """
        )

        return cursor.fetchall()

    def clear(self):

        cursor = self.conn.cursor()

        cursor.execute(
            "DELETE FROM orders"
        )

        self.conn.commit()