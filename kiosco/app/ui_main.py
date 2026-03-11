from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QGridLayout
)

from app.services import (
    listar_productos_activos,
    listar_combos_activos,
    CartItem,
    Producto,
    Combo,
    registrar_venta,
)
from app.ui_products import ProductsDialog
from app.ui_sales import SalesHistoryDialog
from app.ui_combo_builder import ComboBuilderDialog
from app.ui_combo_selector import ComboSelectorDialog


def money_str(centavos: int) -> str:
    pesos = centavos // 100
    return f"${pesos:,}".replace(",", ".")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        print(">>> MAINWINDOW REAL CARGADA <<<")

        logo_path = Path(__file__).resolve().parents[1] / "assets" / "logo.png"

        self.setWindowTitle("SISTEMA KIOSCO ECEBA")
        self.resize(1200, 750)

        self.setStyleSheet("""
QWidget { background: white; font-family: Segoe UI; font-size: 12px; }
QPushButton {
    background: #0B8EC5;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px;
}
QPushButton:hover { background: #0A7FB1; }
QPushButton:disabled { background: #9CA3AF; color: #F3F4F6; }

QListWidget, QTableWidget {
    background: rgba(255,255,255,0.95);
    border: 1px solid #E5E7EB;
    border-radius: 10px;
}
""")

        self.carrito: Dict[str, CartItem] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(10)

        # HEADER
        header = QHBoxLayout()

        self.logo_lbl = QLabel()
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            self.logo_lbl.setPixmap(pix.scaledToHeight(50, Qt.SmoothTransformation))
        header.addWidget(self.logo_lbl, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel("Sistema Kiosco ECEBA")
        self.title_lbl.setStyleSheet("font-size: 18px; font-weight: 700;")
        header.addWidget(self.title_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        header.addStretch(1)
        outer.addLayout(header)

        # CUERPO
        body = QHBoxLayout()
        outer.addLayout(body, 1)

        # IZQUIERDA
        left = QVBoxLayout()
        body.addLayout(left, 3)

        self.lbl_prod = QLabel("Productos")
        self.lbl_prod.setStyleSheet("font-size: 15px; font-weight: 600;")
        left.addWidget(self.lbl_prod)

        self.products_grid = QGridLayout()
        self.products_grid.setHorizontalSpacing(10)
        self.products_grid.setVerticalSpacing(10)
        left.addLayout(self.products_grid, 1)

        # DERECHA
        right = QVBoxLayout()
        body.addLayout(right, 1)

        self.lbl_cart = QLabel("Carrito")
        self.lbl_cart.setStyleSheet("font-size: 18px; font-weight: 700;")
        right.addWidget(self.lbl_cart)

        self.cart_list = QListWidget()
        self.cart_list.itemDoubleClicked.connect(self.sub_one_from_item)
        right.addWidget(self.cart_list, 1)

        self.lbl_total = QLabel("Total: $0")
        self.lbl_total.setStyleSheet("font-size: 22px; font-weight: 700;")
        right.addWidget(self.lbl_total)

        row_btns = QHBoxLayout()
        right.addLayout(row_btns)

        self.btn_clear = QPushButton("Cancelar")
        self.btn_clear.clicked.connect(self.clear_cart)
        row_btns.addWidget(self.btn_clear)

        self.btn_ok = QPushButton("OK / Cobrar")
        self.btn_ok.clicked.connect(self.go_checkout)
        row_btns.addWidget(self.btn_ok)

        self.btn_admin = QPushButton("Administrar productos")
        self.btn_admin.clicked.connect(self.open_admin)
        right.addWidget(self.btn_admin)

        self.btn_combo_admin = QPushButton("Administrar combos")
        self.btn_combo_admin.clicked.connect(self.open_combo_admin)
        right.addWidget(self.btn_combo_admin)

        self.btn_sales = QPushButton("Historial de ventas")
        self.btn_sales.clicked.connect(self.open_sales_history)
        right.addWidget(self.btn_sales)

        self.load_products()

    def _build_combo_key(self, combo: Combo, componentes: list[dict]) -> str:
        partes = [f"{c['producto_id']}x{c['cantidad']}" for c in componentes]
        return f"combo:{combo.id}:{'|'.join(partes)}"

    def load_products(self):
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        productos = listar_productos_activos()
        combos = listar_combos_activos()

        productos_por_categoria = defaultdict(list)
        for p in productos:
            productos_por_categoria[p.categoria].append(p)

        orden = ["Bebidas", "Comidas"]

        row = 0
        for categoria in orden:
            items = productos_por_categoria.get(categoria, [])
            if not items:
                continue

            lbl = QLabel(categoria.upper())
            lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0B8EC5; margin-top: 8px;")
            self.products_grid.addWidget(lbl, row, 0, 1, 3)
            row += 1

            col = 0
            for p in items:
                btn = QPushButton(f"{p.nombre}\n{money_str(p.precio_centavos)}\nStock: {p.stock}")

                if p.imagen_path:
                    try:
                        path = Path(p.imagen_path)
                        if path.exists():
                            pix = QPixmap(str(path))
                            if not pix.isNull():
                                btn.setIcon(QIcon(pix))
                                btn.setIconSize(QSize(64, 64))
                    except Exception:
                        pass

                btn.setMinimumHeight(90)
                btn.setEnabled(p.stock > 0)
                btn.clicked.connect(lambda checked=False, prod=p: self.add_product(prod))
                self.products_grid.addWidget(btn, row, col)

                col += 1
                if col >= 3:
                    col = 0
                    row += 1

            if col != 0:
                row += 1

        if combos:
            lbl = QLabel("COMBOS")
            lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0B8EC5; margin-top: 8px;")
            self.products_grid.addWidget(lbl, row, 0, 1, 3)
            row += 1

            col = 0
            for c in combos:
                btn = QPushButton(f"{c.nombre}\n{money_str(c.precio_centavos)}")

                if c.imagen_path:
                    try:
                        path = Path(c.imagen_path)
                        if path.exists():
                            pix = QPixmap(str(path))
                            if not pix.isNull():
                                btn.setIcon(QIcon(pix))
                                btn.setIconSize(QSize(64, 64))
                    except Exception:
                        pass

                btn.setMinimumHeight(90)
                btn.clicked.connect(lambda checked=False, combo=c: self.add_product(combo))
                self.products_grid.addWidget(btn, row, col)

                col += 1
                if col >= 3:
                    col = 0
                    row += 1

        self.refresh_cart()

    def add_product(self, prod: Producto | Combo):
        if isinstance(prod, Combo):
            dlg = ComboSelectorDialog(prod.id, self)
            if dlg.exec() != dlg.DialogCode.Accepted or not dlg.result_data:
                return

            componentes = dlg.result_data["componentes"]
            descripcion = dlg.result_data["descripcion"]
            key = self._build_combo_key(prod, componentes)

            if key not in self.carrito:
                self.carrito[key] = CartItem(
                    producto=prod,
                    cantidad=1,
                    combo_componentes=componentes,
                    combo_descripcion=descripcion,
                )
            else:
                self.carrito[key].cantidad += 1
        else:
            if prod.stock <= 0:
                return

            key = f"prod:{prod.id}"
            if key not in self.carrito:
                self.carrito[key] = CartItem(producto=prod, cantidad=1)
            else:
                self.carrito[key].cantidad += 1

        self.refresh_cart()

    def refresh_cart(self):
        self.cart_list.clear()
        total = 0

        for key, item in self.carrito.items():
            total += item.subtotal_centavos

            if isinstance(item.producto, Combo) and item.combo_descripcion:
                text = f"{item.producto.nombre} [{item.combo_descripcion}] x{item.cantidad} = {money_str(item.subtotal_centavos)}"
            else:
                text = f"{item.producto.nombre} x{item.cantidad} = {money_str(item.subtotal_centavos)}"

            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, key)
            self.cart_list.addItem(it)

        self.lbl_total.setText(f"Total: {money_str(total)}")

    def sub_one_from_item(self, it: QListWidgetItem):
        key = str(it.data(Qt.UserRole))
        if key in self.carrito:
            self.carrito[key].cantidad -= 1
            if self.carrito[key].cantidad <= 0:
                del self.carrito[key]
        self.refresh_cart()

    def clear_cart(self):
        self.carrito = {}
        self.refresh_cart()

    def go_checkout(self):
        total = sum(i.subtotal_centavos for i in self.carrito.values())
        if total <= 0:
            QMessageBox.information(self, "Atención", "No hay productos en el carrito.")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar cobro")
        msg.setText("TOTAL A COBRAR")
        msg.setInformativeText(f"<h1 style='font-size:48px; text-align:center;'>{money_str(total)}</h1>")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.button(QMessageBox.StandardButton.Ok).setText("Cobrar")
        msg.button(QMessageBox.StandardButton.Cancel).setText("Cancelar")

        resp = msg.exec()
        if resp != QMessageBox.StandardButton.Ok:
            return

        try:
            registrar_venta(self.carrito, pago_centavos=total)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        QMessageBox.information(self, "Listo", "Venta registrada.")
        self.clear_cart()
        self.load_products()

    def open_admin(self):
        dlg = ProductsDialog(self)
        dlg.exec()
        self.load_products()

    def open_combo_admin(self):
        dlg = ComboBuilderDialog(self)
        dlg.exec()
        self.load_products()

    def open_sales_history(self):
        dlg = SalesHistoryDialog(self)
        dlg.exec()