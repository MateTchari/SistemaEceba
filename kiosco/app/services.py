from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from app.db import get_conn


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


def listar_productos_activos() -> List[Producto]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nombre, precio_centavos, stock, activo, imagen_path FROM productos WHERE activo=1 ORDER BY nombre"
        ).fetchall()
    return [Producto(**dict(r)) for r in rows]


def seed_productos_si_vacio() -> None:
    """Para probar rápido (después lo sacamos y hacemos ABM)."""
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


def registrar_venta(carrito: Dict[int, CartItem], pago_centavos: int) -> int:
    """
    carrito: dict {producto_id: CartItem}
    Valida stock, inserta venta + items, descuenta stock.
    Devuelve venta_id.
    """
    if not carrito:
        raise ValueError("El carrito está vacío.")

    total = sum(item.subtotal_centavos for item in carrito.values())
    if pago_centavos < total:
        raise ValueError("El pago es menor al total.")

    # Validación de stock en DB (evita vender con stock viejo)
    with get_conn() as conn:
        for item in carrito.values():
            row = conn.execute(
                "SELECT stock FROM productos WHERE id=? AND activo=1", (item.producto.id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Producto inválido o inactivo: {item.producto.nombre}")
            if row["stock"] < item.cantidad:
                raise ValueError(f"Stock insuficiente para {item.producto.nombre}")

        fecha_hora = datetime.now().isoformat(timespec="seconds")
        vuelto = pago_centavos - total

        cur = conn.execute(
            "INSERT INTO ventas (fecha_hora, total_centavos, pago_centavos, vuelto_centavos) VALUES (?, ?, ?, ?)",
            (fecha_hora, total, pago_centavos, vuelto),
        )
        venta_id = cur.lastrowid

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

        return int(venta_id)
    
from typing import Optional

def buscar_productos(query: str = "", incluir_inactivos: bool = True):
    q = f"%{query.strip()}%"
    sql = sql = """
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

    return [Producto(**dict(r)) for r in rows]


def crear_producto(nombre: str, precio_centavos: int, stock: int, imagen_path: str | None = None) -> int:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if precio_centavos < 0:
        raise ValueError("El precio no puede ser negativo.")
    if stock < 0:
        raise ValueError("El stock no puede ser negativo.")

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO productos (nombre, precio_centavos, stock, activo, imagen_path) VALUES (?, ?, ?, 1, ?)",
            (nombre, precio_centavos, stock, imagen_path),
        )
        return int(cur.lastrowid)


def actualizar_producto(producto_id: int, nombre: str, precio_centavos: int, stock: int, activo: int, imagen_path: str | None):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if precio_centavos < 0:
        raise ValueError("El precio no puede ser negativo.")
    if stock < 0:
        raise ValueError("El stock no puede ser negativo.")
    if activo not in (0, 1):
        raise ValueError("Activo inválido.")

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE productos
            SET nombre=?, precio_centavos=?, stock=?, activo=?, imagen_path=?
            WHERE id=?
            """,
            (nombre, precio_centavos, stock, activo, imagen_path, producto_id),
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

from typing import List, Dict, Any, Optional

def listar_ventas(fecha_desde: str, fecha_hasta: str):
    """
    fecha_desde / fecha_hasta en formato 'YYYY-MM-DD'
    Trae ventas cuya fecha_hora cae dentro del rango.
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