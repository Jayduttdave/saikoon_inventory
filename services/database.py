import os
import sqlite3

try:
    import psycopg2
except ImportError:
    psycopg2 = None


BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "orders.db"
)

POSTGRES_URL = (
    os.environ.get("SUPABASE_DB_URL")
    or os.environ.get("DATABASE_URL")
    or ""
).strip()


class Database:

    def __init__(self):

        self.backend = "sqlite"
        self.conn = None
        self.param = "?"

        self.connect()
        self.create_table()

    def connect(self):

        if POSTGRES_URL and psycopg2 is not None:
            try:
                connect_kwargs = {}
                if "sslmode=" not in POSTGRES_URL:
                    connect_kwargs["sslmode"] = os.environ.get(
                        "PGSSLMODE",
                        "require"
                    )

                self.conn = psycopg2.connect(
                    POSTGRES_URL,
                    **connect_kwargs
                )
                self.backend = "postgres"
                self.param = "%s"
                print("Database backend: Supabase/Postgres")
                return
            except Exception as exc:
                print(
                    "Supabase/Postgres unavailable, "
                    f"falling back to SQLite: {exc}"
                )

        elif POSTGRES_URL and psycopg2 is None:
            print(
                "psycopg2-binary not installed; "
                "falling back to SQLite."
            )

        self.conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False
        )
        print(f"Database backend: SQLite ({DB_PATH})")

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

        if self.backend == "postgres":
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'orders'
                """
            )
            columns = [row[0] for row in cursor.fetchall()]
        else:
            cursor.execute("PRAGMA table_info(orders)")
            columns = [row[1] for row in cursor.fetchall()]

        if 'unit' not in columns:
            cursor.execute(
                "ALTER TABLE orders ADD COLUMN unit TEXT DEFAULT 'Pièce'"
            )

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
            f"""
            INSERT INTO orders
            (supplier, product, qty, unit)

            VALUES ({self.param}, {self.param}, {self.param}, {self.param})

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
            ORDER BY supplier, product
            """
        )

        return cursor.fetchall()

    def delete_order(self, supplier, product):

        cursor = self.conn.cursor()

        cursor.execute(
            f"""
            DELETE FROM orders
            WHERE supplier = {self.param} AND product = {self.param}
            """,
            (supplier, product)
        )

        self.conn.commit()

    def get_custom_products(self, supplier=None):

        cursor = self.conn.cursor()

        if supplier:
            cursor.execute(
                f"""
                SELECT product, image_filename
                FROM custom_products
                WHERE supplier = {self.param}
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
            f"""
            INSERT INTO custom_products
            (supplier, product, image_filename)
            VALUES ({self.param}, {self.param}, {self.param})
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