import os
import sqlite3
from threading import RLock

try:
    import psycopg2
except ImportError:
    psycopg2 = None


PSYCOPG_CONNECTION_ERRORS = (
    (psycopg2.InterfaceError, psycopg2.OperationalError)
    if psycopg2 is not None
    else tuple()
)


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
        self.lock = RLock()

        self.connect(force=True)
        self.create_table()

    def close(self):

        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass

        self.conn = None

    def connect(self, force=False):

        with self.lock:

            if not force and self.conn is not None:
                if self.backend == "postgres":
                    try:
                        if self.conn.closed == 0:
                            return
                    except Exception:
                        pass
                else:
                    return

            self.close()

            if POSTGRES_URL and psycopg2 is not None:
                try:
                    if "sslmode=" not in POSTGRES_URL:
                        self.conn = psycopg2.connect(
                            POSTGRES_URL,
                            connect_timeout=10,
                            sslmode=os.environ.get(
                                "PGSSLMODE",
                                "require"
                            )
                        )
                    else:
                        self.conn = psycopg2.connect(
                            POSTGRES_URL,
                            connect_timeout=10,
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
            self.backend = "sqlite"
            self.param = "?"
            print(f"Database backend: SQLite ({DB_PATH})")

    def ensure_connection(self):

        if self.conn is None:
            self.connect(force=True)
            return

        if self.backend != "postgres":
            return

        try:
            if self.conn.closed != 0:
                self.connect(force=True)
                return

            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            self.conn.rollback()
        except Exception:
            self.connect(force=True)

    def rollback_quietly(self):

        try:
            if self.conn is not None:
                self.conn.rollback()
        except Exception:
            pass

    def run_query(self, query, params=(), fetch=False):

        with self.lock:
            last_exc = None

            for attempt in range(2):
                self.ensure_connection()
                cursor = None

                try:
                    cursor = self.conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall() if fetch else None
                    self.conn.commit()
                    return rows
                except PSYCOPG_CONNECTION_ERRORS + (sqlite3.Error,) as exc:
                    last_exc = exc
                    self.rollback_quietly()

                    if attempt == 0:
                        print(f"Database connection issue, retrying once: {exc}")
                        self.connect(force=True)
                        continue

                    raise
                except Exception:
                    self.rollback_quietly()
                    raise
                finally:
                    try:
                        if cursor is not None:
                            cursor.close()
                    except Exception:
                        pass

            if last_exc:
                raise last_exc

            return [] if fetch else None

    def create_table(self):

        self.run_query(
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

        self.run_query(
            """
            CREATE TABLE IF NOT EXISTS custom_products (
                supplier TEXT,
                product TEXT,
                image_filename TEXT,
                PRIMARY KEY (supplier, product)
            )
            """
        )

        self.ensure_schema()

    def ensure_schema(self):

        if self.backend == "postgres":
            columns = [
                row[0]
                for row in (self.run_query(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'orders'
                    """,
                    fetch=True,
                ) or [])
            ]
        else:
            columns = [
                row[1]
                for row in (self.run_query(
                    "PRAGMA table_info(orders)",
                    fetch=True,
                ) or [])
            ]

        if 'unit' not in columns:
            self.run_query(
                "ALTER TABLE orders ADD COLUMN unit TEXT DEFAULT 'Pièce'"
            )

        self.run_query("DROP TABLE IF EXISTS stock")

    def upsert(
        self,
        supplier,
        product,
        qty,
        unit='Pièce'
    ):

        self.run_query(
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

    def all(self):

        return self.run_query(
            """
            SELECT supplier, product, qty, unit
            FROM orders
            ORDER BY supplier, product
            """,
            fetch=True,
        )

    def delete_order(self, supplier, product):

        self.run_query(
            f"""
            DELETE FROM orders
            WHERE supplier = {self.param} AND product = {self.param}
            """,
            (supplier, product)
        )

    def get_custom_products(self, supplier=None):

        if supplier:
            rows = self.run_query(
                f"""
                SELECT product, image_filename
                FROM custom_products
                WHERE supplier = {self.param}
                ORDER BY product
                """,
                (supplier,),
                fetch=True,
            )
        else:
            rows = self.run_query(
                """
                SELECT supplier, product, image_filename
                FROM custom_products
                ORDER BY supplier, product
                """,
                fetch=True,
            )

        if supplier:
            return [
                {
                    'product': row[0],
                    'image_filename': row[1]
                }
                for row in (rows or [])
            ]

        return [
            {
                'supplier': row[0],
                'product': row[1],
                'image_filename': row[2]
            }
            for row in (rows or [])
        ]

    def add_custom_product(self, supplier, product, image_filename=None):

        self.run_query(
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

    def clear(self):

        self.run_query(
            "DELETE FROM orders"
        )