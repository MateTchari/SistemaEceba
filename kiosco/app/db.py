from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def app_base_dir() -> Path:
    """
    EXE (PyInstaller): carpeta donde está el .exe (portátil)
    Dev: carpeta kiosco/ (porque db.py está en kiosco/app/db.py)
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]  # kiosco/


def db_path() -> Path:
    base = app_base_dir()
    p = base / "data" / "kiosco.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ✅ Compatibilidad con tu código existente (backup.py importaba DB_PATH)
DB_PATH = db_path()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """
    Crea tablas si no existen y aplica migración simple (imagen_path).
    Llamar 1 vez al inicio del programa.
    """
    with get_conn() as conn:
        # productos
        conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio_centavos INTEGER NOT NULL CHECK(precio_centavos >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1))
        );
        """)

        # migración: imagen_path
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(productos);").fetchall()]
        if "imagen_path" not in cols:
            conn.execute("ALTER TABLE productos ADD COLUMN imagen_path TEXT;")

        # ventas
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            total_centavos INTEGER NOT NULL CHECK(total_centavos >= 0),
            pago_centavos INTEGER NOT NULL CHECK(pago_centavos >= 0),
            vuelto_centavos INTEGER NOT NULL
        );
        """)

        # items
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

        conn.commit()