import sqlite3
from pathlib import Path

# Si tu estructura es: SistemaEceba/kiosco/app/db.py
# y querés DB en: SistemaEceba/kiosco/data/kiosco.db  -> parents[1]
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "kiosco.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.touch(exist_ok=True)  # fuerza a que exista el archivo
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio_centavos INTEGER NOT NULL CHECK(precio_centavos >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1))
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            total_centavos INTEGER NOT NULL CHECK(total_centavos >= 0),
            pago_centavos INTEGER NOT NULL CHECK(pago_centavos >= 0),
            vuelto_centavos INTEGER NOT NULL
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS venta_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL CHECK(cantidad > 0),
            precio_unitario_centavos INTEGER NOT NULL CHECK(precio_unitario_centavos >= 0),
            subtotal_centavos INTEGER NOT NULL CHECK(subtotal_centavos >= 0),
            FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        );
        """)
        
def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio_centavos INTEGER NOT NULL CHECK(precio_centavos >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1))
        );
        """)

        # ---- MIGRACIÓN SIMPLE: agregar imagen_path si falta ----
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(productos);").fetchall()]
        if "imagen_path" not in cols:
            conn.execute("ALTER TABLE productos ADD COLUMN imagen_path TEXT;")

        # ... (ventas y venta_items igual que antes)