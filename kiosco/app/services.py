from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union
import shutil
import sys
import uuid

from app.db import get_conn


@dataclass(frozen=True)
class Producto:
    id: int
    nombre: str
    precio_centavos: int
    stock: int
    activo: int
    imagen_path: str | None = None
    categoria: str = "Comidas"


@dataclass(frozen=True)
class Combo:
    id: int
    nombre: str
    precio_centavos: int
    activo: int
    imagen_path: str | None = None


@dataclass
class CartItem:
    producto: Union[Producto, Combo]
    cantidad: int
    combo_componentes: list[dict] | None = None
    combo_descripcion: str | None = None

    @property
    def subtotal_centavos(self) -> int:
        return self.producto.precio_centavos * self.cantidad


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]  # kiosco/


def images_dir() -> Path:
    p = app_base_dir() / "images"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _to_rel_images_path(p: Path) -> str:
    try:
        rel = p.resolve().relative_to(images_dir().resolve())
        return f"images/{rel.as_posix()}"
    except Exception:
        return p.as_posix()


def resolver_imagen_path(rel_o_abs: str | None) -> str | None:
    if not rel_o_abs:
        return None

    p = Path(rel_o_abs)
    if p.is_absolute():
        return str(p)

    return str(app_base_dir() / rel_o_abs)


def _guardar_imagen_en_sistema(origen_path: str) -> str:
    src = Path(origen_path)
    if not src.exists():
        raise FileNotFoundError(f"No existe la imagen: {origen_path}")

    ext = (src.suffix or ".png").lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    dst = images_dir() / filename

    shutil.copy2(src, dst)
    return f"images/{filename}"


def normalizar_imagen_para_db(imagen_path: str | None) -> str | None:
    if not imagen_path:
        return None

    if imagen_path.replace("\\", "/").startswith("images/"):
        return imagen_path.replace("\\", "/")

    p = Path(imagen_path)

    if p.is_absolute():
        try:
            return _to_rel_images_path(p)
        except Exception:
            pass

    return _guardar_imagen_en_sistema(str(p))


# -----------------------------
# Productos
# -----------------------------
def listar_productos_activos() -> List[Producto]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, nombre, precio_centavos, stock, activo, imagen_path, categoria
            FROM productos
            WHERE activo=1
            ORDER BY categoria, nombre
            """
        ).fetchall()

    out: List[Producto] = []
    for r in rows:
        d = dict(r)
        d["imagen_path"] = resolver_imagen_path(d.get("imagen_path"))
        out.append(Producto(**d))
    return out


def listar_productos_para_combo() -> List[Producto]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, nombre, precio_centavos, stock, activo, imagen_path, categoria
            FROM productos
            WHERE activo=1 AND categoria IN ('Bebidas', 'Comidas')
            ORDER BY categoria, nombre
            """
        ).fetchall()

    out: List[Producto] = []
    for r in rows:
        d = dict(r)
        d["imagen_path"] = resolver_imagen_path(d.get("imagen_path"))
        out.append(Producto(**d))
    return out


def buscar_productos(query: str = "", incluir_inactivos: bool = True) -> List[Producto]:
    q = f"%{query.strip()}%"
    sql = """
        SELECT id, nombre, precio_centavos, stock, activo, imagen_path, categoria
        FROM productos
        WHERE nombre LIKE ?
    """
    params = [q]
    if not incluir_inactivos:
        sql += " AND activo=1"
    sql += " ORDER BY categoria, nombre"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    out: List[Producto] = []
    for r in rows:
        d = dict(r)
        d["imagen_path"] = resolver_imagen_path(d.get("imagen_path"))
        out.append(Producto(**d))
    return out


def crear_producto(
    nombre: str,
    precio_centavos: int,
    stock: int,
    imagen_path: str | None = None,
    categoria: str = "Comidas",
) -> int:
    nombre = nombre.strip()
    categoria = categoria.strip() or "Comidas"

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
            INSERT INTO productos (nombre, precio_centavos, stock, activo, imagen_path, categoria)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (nombre, precio_centavos, stock, img_db, categoria),
        )
        conn.commit()
        return int(cur.lastrowid)


def actualizar_producto(
    producto_id: int,
    nombre: str,
    precio_centavos: int,
    stock: int,
    activo: int,
    imagen_path: str | None,
    categoria: str,
) -> None:
    nombre = nombre.strip()
    categoria = categoria.strip() or "Comidas"

    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if precio_centavos < 0:
        raise ValueError("El precio no puede ser negativo.")
    if stock < 0:
        raise ValueError("El stock no puede ser negativo.")
    if activo not in (0, 1):
        raise ValueError("Activo inválido.")

    with get_conn() as conn:
        if imagen_path is None:
            conn.execute(
                """
                UPDATE productos
                SET nombre=?, precio_centavos=?, stock=?, activo=?, categoria=?
                WHERE id=?
                """,
                (nombre, precio_centavos, stock, activo, categoria, producto_id),
            )
        else:
            img_db = normalizar_imagen_para_db(imagen_path)
            conn.execute(
                """
                UPDATE productos
                SET nombre=?, precio_centavos=?, stock=?, activo=?, imagen_path=?, categoria=?
                WHERE id=?
                """,
                (nombre, precio_centavos, stock, activo, img_db, categoria, producto_id),
            )
        conn.commit()


def eliminar_producto(producto_id: int) -> str:
    with get_conn() as conn:
        usado = conn.execute(
            "SELECT COUNT(*) AS n FROM venta_items WHERE producto_id=?",
            (producto_id,),
        ).fetchone()["n"]

        if usado > 0:
            conn.execute("UPDATE productos SET activo=0 WHERE id=?", (producto_id,))
            conn.commit()
            return "archivado"

        conn.execute("DELETE FROM productos WHERE id=?", (producto_id,))
        conn.commit()
        return "eliminado"


# -----------------------------
# Combos con variantes
# -----------------------------
def listar_combos_activos() -> List[Combo]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, nombre, precio_centavos, activo, imagen_path
            FROM combos
            WHERE activo=1
            ORDER BY nombre
            """
        ).fetchall()

    out: List[Combo] = []
    for r in rows:
        d = dict(r)
        d["imagen_path"] = resolver_imagen_path(d.get("imagen_path"))
        out.append(Combo(**d))
    return out


def listar_combos_admin() -> List[Combo]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, nombre, precio_centavos, activo, imagen_path
            FROM combos
            ORDER BY nombre
            """
        ).fetchall()

    out: List[Combo] = []
    for r in rows:
        d = dict(r)
        d["imagen_path"] = resolver_imagen_path(d.get("imagen_path"))
        out.append(Combo(**d))
    return out


def obtener_combo_definicion(combo_id: int) -> dict:
    with get_conn() as conn:
        combo = conn.execute(
            """
            SELECT id, nombre, precio_centavos, activo, imagen_path
            FROM combos
            WHERE id=?
            """,
            (combo_id,),
        ).fetchone()

        if combo is None:
            raise ValueError("El combo no existe.")

        grupos_rows = conn.execute(
            """
            SELECT id, nombre, orden
            FROM combo_grupos
            WHERE combo_id=?
            ORDER BY orden, id
            """,
            (combo_id,),
        ).fetchall()

        grupos = []
        for g in grupos_rows:
            opciones_rows = conn.execute(
                """
                SELECT co.id, co.producto_id, co.cantidad, p.nombre, p.precio_centavos, p.stock
                FROM combo_opciones co
                JOIN productos p ON p.id = co.producto_id
                WHERE co.grupo_id=? AND p.activo=1
                ORDER BY p.nombre
                """,
                (g["id"],),
            ).fetchall()

            grupos.append({
                "id": int(g["id"]),
                "nombre": g["nombre"],
                "orden": int(g["orden"]),
                "opciones": [dict(r) for r in opciones_rows],
            })

        combo_dict = dict(combo)
        combo_dict["imagen_path"] = resolver_imagen_path(combo_dict.get("imagen_path"))
        combo_dict["grupos"] = grupos
        return combo_dict


def listar_grupos_combo(combo_id: int) -> list[dict]:
    return obtener_combo_definicion(combo_id)["grupos"]


def crear_combo(nombre: str, precio_centavos: int, grupos: list[dict], imagen_path: str | None = None) -> int:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del combo no puede estar vacío.")
    if precio_centavos < 0:
        raise ValueError("El precio del combo no puede ser negativo.")
    if not grupos:
        raise ValueError("El combo debe tener al menos un grupo.")
    for g in grupos:
        if not g.get("nombre", "").strip():
            raise ValueError("Todos los grupos del combo deben tener nombre.")
        if not g.get("opciones"):
            raise ValueError(f"El grupo '{g.get('nombre', '')}' no tiene opciones.")

    img_db = normalizar_imagen_para_db(imagen_path)

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO combos (nombre, precio_centavos, activo, imagen_path)
            VALUES (?, ?, 1, ?)
            """,
            (nombre, precio_centavos, img_db),
        )
        combo_id = int(cur.lastrowid)

        for idx, grupo in enumerate(grupos):
            curg = conn.execute(
                """
                INSERT INTO combo_grupos (combo_id, nombre, orden)
                VALUES (?, ?, ?)
                """,
                (combo_id, grupo["nombre"].strip(), idx),
            )
            grupo_id = int(curg.lastrowid)

            for op in grupo["opciones"]:
                conn.execute(
                    """
                    INSERT INTO combo_opciones (grupo_id, producto_id, cantidad)
                    VALUES (?, ?, ?)
                    """,
                    (grupo_id, int(op["producto_id"]), int(op.get("cantidad", 1))),
                )

        conn.commit()
        return combo_id


def actualizar_combo(combo_id: int, nombre: str, precio_centavos: int, grupos: list[dict], imagen_path: str | None = None) -> None:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del combo no puede estar vacío.")
    if precio_centavos < 0:
        raise ValueError("El precio del combo no puede ser negativo.")
    if not grupos:
        raise ValueError("El combo debe tener al menos un grupo.")
    for g in grupos:
        if not g.get("nombre", "").strip():
            raise ValueError("Todos los grupos del combo deben tener nombre.")
        if not g.get("opciones"):
            raise ValueError(f"El grupo '{g.get('nombre', '')}' no tiene opciones.")

    with get_conn() as conn:
        if imagen_path is None:
            conn.execute(
                """
                UPDATE combos
                SET nombre=?, precio_centavos=?
                WHERE id=?
                """,
                (nombre, precio_centavos, combo_id),
            )
        else:
            img_db = normalizar_imagen_para_db(imagen_path)
            conn.execute(
                """
                UPDATE combos
                SET nombre=?, precio_centavos=?, imagen_path=?
                WHERE id=?
                """,
                (nombre, precio_centavos, img_db, combo_id),
            )

        conn.execute("DELETE FROM combo_grupos WHERE combo_id=?", (combo_id,))

        for idx, grupo in enumerate(grupos):
            curg = conn.execute(
                """
                INSERT INTO combo_grupos (combo_id, nombre, orden)
                VALUES (?, ?, ?)
                """,
                (combo_id, grupo["nombre"].strip(), idx),
            )
            grupo_id = int(curg.lastrowid)

            for op in grupo["opciones"]:
                conn.execute(
                    """
                    INSERT INTO combo_opciones (grupo_id, producto_id, cantidad)
                    VALUES (?, ?, ?)
                    """,
                    (grupo_id, int(op["producto_id"]), int(op.get("cantidad", 1))),
                )

        conn.commit()


def eliminar_combo(combo_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM combos WHERE id=?", (combo_id,))
        conn.commit()


# -----------------------------
# Ventas
# -----------------------------
def registrar_venta(carrito: Dict[str, CartItem], pago_centavos: int) -> int:
    if not carrito:
        raise ValueError("El carrito está vacío.")

    total = sum(item.subtotal_centavos for item in carrito.values())
    if pago_centavos < total:
        raise ValueError("El pago es menor al total.")

    with get_conn() as conn:
        requeridos: Dict[int, int] = {}

        for item in carrito.values():
            if isinstance(item.producto, Producto):
                requeridos[item.producto.id] = requeridos.get(item.producto.id, 0) + item.cantidad
            else:
                if not item.combo_componentes:
                    raise ValueError(f"El combo '{item.producto.nombre}' no tiene selección de opciones.")
                for cp in item.combo_componentes:
                    pid = int(cp["producto_id"])
                    cant = int(cp["cantidad"]) * item.cantidad
                    requeridos[pid] = requeridos.get(pid, 0) + cant

        for pid, cant_req in requeridos.items():
            row = conn.execute(
                "SELECT stock, nombre FROM productos WHERE id=? AND activo=1",
                (pid,),
            ).fetchone()

            if row is None:
                raise ValueError("Uno de los productos del carrito ya no existe o está inactivo.")

            if row["stock"] < cant_req:
                raise ValueError(f"Stock insuficiente para {row['nombre']}")

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
            if isinstance(item.producto, Producto):
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
            else:
                for cp in item.combo_componentes or []:
                    producto_id = int(cp["producto_id"])
                    cantidad_total = int(cp["cantidad"]) * item.cantidad
                    precio_unit = int(cp["precio_centavos"])
                    subtotal = precio_unit * cantidad_total

                    conn.execute(
                        """
                        INSERT INTO venta_items
                        (venta_id, producto_id, cantidad, precio_unitario_centavos, subtotal_centavos)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            venta_id,
                            producto_id,
                            cantidad_total,
                            precio_unit,
                            subtotal,
                        ),
                    )
                    conn.execute(
                        "UPDATE productos SET stock = stock - ? WHERE id=?",
                        (cantidad_total, producto_id),
                    )

        conn.commit()
        return venta_id


def listar_ventas(fecha_desde: str, fecha_hasta: str):
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


def rollback_venta(venta_id: int) -> None:
    if not isinstance(venta_id, int) or venta_id <= 0:
        raise ValueError("ID de venta inválido.")

    with get_conn() as conn:
        v = conn.execute("SELECT id FROM ventas WHERE id=?", (venta_id,)).fetchone()
        if v is None:
            raise ValueError("La venta no existe.")

        items = conn.execute(
            """
            SELECT producto_id, cantidad
            FROM venta_items
            WHERE venta_id=?
            """,
            (venta_id,),
        ).fetchall()

        for it in items:
            conn.execute(
                "UPDATE productos SET stock = stock + ? WHERE id=?",
                (int(it["cantidad"]), int(it["producto_id"])),
            )

        conn.execute("DELETE FROM ventas WHERE id=?", (venta_id,))
        conn.commit()