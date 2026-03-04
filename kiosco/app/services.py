from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import shutil
import sys
import uuid

from app.db import get_conn


# -----------------------------
# Modelos
# -----------------------------
@dataclass(frozen=True)
class Producto:
    id: int
    nombre: str
    precio_centavos: int
    stock: int
    activo: int
    imagen_path: str | None = None


@dataclass
class CartItem:
    producto: Producto
    cantidad: int

    @property
    def subtotal_centavos(self) -> int:
        return self.producto.precio_centavos * self.cantidad


# -----------------------------
# Paths portables (DEV y EXE)
# -----------------------------
def app_base_dir() -> Path:
    """
    EXE (PyInstaller): carpeta donde está el .exe
    DEV: carpeta kiosco/ (services.py está en kiosco/app/services.py)
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]  # kiosco/


def images_dir() -> Path:
    p = app_base_dir() / "images"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _to_rel_images_path(p: Path) -> str:
    """
    Convierte un path absoluto dentro de images_dir() a 'images/archivo.ext'
    """
    try:
        rel = p.resolve().relative_to(images_dir().resolve())
        return f"images/{rel.as_posix()}"
    except Exception:
        # No está dentro de images_dir()
        return p.as_posix()


def resolver_imagen_path(rel_o_abs: str | None) -> str | None:
    """
    Lo que está en BD puede ser:
      - None
      - 'images/xxx.png' (relativo)
      - o (viejo) una ruta absoluta.
    Devuelve siempre un path absoluto usable por QPixmap, o None.
    """
    if not rel_o_abs:
        return None

    p = Path(rel_o_abs)

    if p.is_absolute():
        return str(p)

    # relativo => relativo al base_dir (kiosco/ o carpeta del exe)
    abs_path = app_base_dir() / rel_o_abs
    return str(abs_path)


def _guardar_imagen_en_sistema(origen_path: str) -> str:
    """
    Copia la imagen a /images con nombre único.
    Devuelve la ruta RELATIVA 'images/xxxx.ext' para guardar en la BD.
    """
    src = Path(origen_path)
    if not src.exists():
        raise FileNotFoundError(f"No existe la imagen: {origen_path}")

    ext = (src.suffix or ".png").lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    dst = images_dir() / filename

    shutil.copy2(src, dst)

    return f"images/{filename}"


def normalizar_imagen_para_db(imagen_path: str | None) -> str | None:
    """
    Regla:
      - None => None
      - Si ya viene como 'images/...' => se guarda igual
      - Si es absoluta dentro de images_dir => se convierte a 'images/...'
      - Si es absoluta fuera => se copia a images_dir y se guarda 'images/...'
    """
    if not imagen_path:
        return None

    # ya en formato relativo correcto
    if imagen_path.replace("\\", "/").startswith("images/"):
        return imagen_path.replace("\\", "/")

    p = Path(imagen_path)

    # Si es absoluta y está dentro de images_dir => guardo relativo
    if p.is_absolute():
        try:
            return _to_rel_images_path(p)
        except Exception:
            pass

    # Si no está en images_dir => copiar y guardar nuevo relativo
    return _guardar_imagen_en_sistema(str(p))


# -----------------------------
# Productos
# -----------------------------
def listar_productos_activos() -> List[Producto]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, nombre, precio_centavos, stock, activo, imagen_path
            FROM productos
            WHERE activo=1
            ORDER BY nombre
            """
        ).fetchall()

    productos: List[Producto] = []
    for r in rows:
        d = dict(r)
        # convertir a absoluto para UI
        d["imagen_path"] = resolver_imagen_path(d.get("imagen_path"))
        productos.append(Producto(**d))
    return productos


def buscar_productos(query: str = "", incluir_inactivos: bool = True) -> List[Producto]:
    q = f"%{query.strip()}%"
    sql = """
        SELECT id, nombre, precio_centavos, stock, activo, imagen_path
        FROM productos
        WHERE nombre LIKE ?
    """
    params = [q]
    if not incluir_inactivos:
        sql += " AND activo=1"
    sql += " ORDER BY nombre"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    productos: List[Producto] = []
    for r in rows:
        d = dict(r)
        d["imagen_path"] = resolver_imagen_path(d.get("imagen_path"))
        productos.append(Producto(**d))
    return productos


def crear_producto(nombre: str, precio_centavos: int, stock: int, imagen_path: str | None = None) -> int:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if precio_centavos < 0:
        raise ValueError("El precio no puede ser negativo.")
    if stock < 0:
        raise ValueError("El stock no puede ser negativo.")

    img_db = normalizar_imagen_para_db(imagen_path)

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO productos (nombre, precio_centavos, stock, activo, imagen_path)
            VALUES (?, ?, ?, 1, ?)
            """,
            (nombre, precio_centavos, stock, img_db),
        )
        return int(cur.lastrowid)


def actualizar_producto(
    producto_id: int,
    nombre: str,
    precio_centavos: int,
    stock: int,
    activo: int,
    imagen_path: str | None,
) -> None:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if precio_centavos < 0:
        raise ValueError("El precio no puede ser negativo.")
    if stock < 0:
        raise ValueError("El stock no puede ser negativo.")
    if activo not in (0, 1):
        raise ValueError("Activo inválido.")

    # Si imagen_path viene:
    # - None => NO tocamos la imagen (mantenemos la existente)
    # - viene algo => lo normalizamos (copiamos si hace falta)
    with get_conn() as conn:
        if imagen_path is None:
            conn.execute(
                """
                UPDATE productos
                SET nombre=?, precio_centavos=?, stock=?, activo=?
                WHERE id=?
                """,
                (nombre, precio_centavos, stock, activo, producto_id),
            )
        else:
            img_db = normalizar_imagen_para_db(imagen_path)
            conn.execute(
                """
                UPDATE productos
                SET nombre=?, precio_centavos=?, stock=?, activo=?, imagen_path=?
                WHERE id=?
                """,
                (nombre, precio_centavos, stock, activo, img_db, producto_id),
            )


def set_activo(producto_id: int, activo: int) -> None:
    if activo not in (0, 1):
        raise ValueError("Activo inválido.")
    with get_conn() as conn:
        conn.execute("UPDATE productos SET activo=? WHERE id=?", (activo, producto_id))


def eliminar_producto(producto_id: int) -> str:
    """
    Si el producto tiene ventas: lo archiva (activo=0).
    Si no tiene ventas: lo borra.
    Devuelve 'archivado' o 'eliminado'.
    """
    with get_conn() as conn:
        usado = conn.execute(
            "SELECT COUNT(*) AS n FROM venta_items WHERE producto_id=?",
            (producto_id,),
        ).fetchone()["n"]

        if usado > 0:
            conn.execute("UPDATE productos SET activo=0 WHERE id=?", (producto_id,))
            return "archivado"

        conn.execute("DELETE FROM productos WHERE id=?", (producto_id,))
        return "eliminado"


# -----------------------------
# Ventas
# -----------------------------
def registrar_venta(carrito: Dict[int, CartItem], pago_centavos: int) -> int:
    """
    Valida stock, inserta venta + items, descuenta stock.
    Devuelve venta_id.
    """
    if not carrito:
        raise ValueError("El carrito está vacío.")

    total = sum(item.subtotal_centavos for item in carrito.values())
    if pago_centavos < total:
        raise ValueError("El pago es menor al total.")

    with get_conn() as conn:
        # validar stock actual
        for item in carrito.values():
            row = conn.execute(
                "SELECT stock FROM productos WHERE id=? AND activo=1",
                (item.producto.id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Producto inválido o inactivo: {item.producto.nombre}")
            if row["stock"] < item.cantidad:
                raise ValueError(f"Stock insuficiente para {item.producto.nombre}")

        fecha_hora = datetime.now().isoformat(timespec="seconds")
        vuelto = pago_centavos - total

        cur = conn.execute(
            """
            INSERT INTO ventas (fecha_hora, total_centavos, pago_centavos, vuelto_centavos)
            VALUES (?, ?, ?, ?)
            """,
            (fecha_hora, total, pago_centavos, vuelto),
        )
        venta_id = int(cur.lastrowid)

        for item in carrito.values():
            conn.execute(
                """
                INSERT INTO venta_items
                (venta_id, producto_id, cantidad, precio_unitario_centavos, subtotal_centavos)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    venta_id,
                    item.producto.id,
                    item.cantidad,
                    item.producto.precio_centavos,
                    item.subtotal_centavos,
                ),
            )
            conn.execute(
                "UPDATE productos SET stock = stock - ? WHERE id=?",
                (item.cantidad, item.producto.id),
            )

        return venta_id


def listar_ventas(fecha_desde: str, fecha_hasta: str):
    """
    fecha_desde / fecha_hasta en formato 'YYYY-MM-DD'
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, fecha_hora, total_centavos, pago_centavos, vuelto_centavos
            FROM ventas
            WHERE date(fecha_hora) BETWEEN date(?) AND date(?)
            ORDER BY datetime(fecha_hora) DESC
            """,
            (fecha_desde, fecha_hasta),
        ).fetchall()
    return [dict(r) for r in rows]


def detalle_venta(venta_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.nombre as producto, vi.cantidad, vi.precio_unitario_centavos, vi.subtotal_centavos
            FROM venta_items vi
            JOIN productos p ON p.id = vi.producto_id
            WHERE vi.venta_id = ?
            ORDER BY vi.id
            """,
            (venta_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# -----------------------------
# Seed (si lo usás para test)
# -----------------------------
def seed_productos_si_vacio() -> None:
    """Para probar rápido."""
    with get_conn() as conn:
        c = conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
        if c > 0:
            return
        conn.executemany(
            "INSERT INTO productos (nombre, precio_centavos, stock, activo) VALUES (?, ?, ?, 1)",
            [
                ("Alfajor", 800, 50),
                ("Gaseosa lata", 1500, 40),
                ("Agua", 1000, 30),
                ("Chicle", 200, 200),
            ],
        )
def rollback_venta(venta_id: int) -> None:
    """
    Anula una venta:
    - repone stock de los productos vendidos
    - elimina venta y sus items
    """
    if not isinstance(venta_id, int) or venta_id <= 0:
        raise ValueError("ID de venta inválido.")

    with get_conn() as conn:
        # verificar que exista la venta
        v = conn.execute("SELECT id FROM ventas WHERE id=?", (venta_id,)).fetchone()
        if v is None:
            raise ValueError("La venta no existe.")

        # traer items
        items = conn.execute(
            """
            SELECT producto_id, cantidad
            FROM venta_items
            WHERE venta_id=?
            """,
            (venta_id,),
        ).fetchall()

        # reponer stock
        for it in items:
            conn.execute(
                "UPDATE productos SET stock = stock + ? WHERE id=?",
                (int(it["cantidad"]), int(it["producto_id"])),
            )

        # borrar venta (si tenés ON DELETE CASCADE, borra items también)
        conn.execute("DELETE FROM ventas WHERE id=?", (venta_id,))

        conn.commit()