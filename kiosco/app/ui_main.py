from __future__ import annotations

from typing import Dict
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QLineEdit, QGridLayout
)

from app.services import listar_productos_activos, CartItem, Producto
from app.services import registrar_venta
from app.ui_products import ProductsDialog
from app.ui_sales import SalesHistoryDialog


def money_str(centavos: int) -> str:
    pesos = centavos // 100
    return f"${pesos:,}".replace(",", ".")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Fondo blanco + header con logo
        logo_path = Path(__file__).resolve().parents[1] / "assets" / "logo.png"

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

QLineEdit {
    padding: 8px;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    background: white;
}

QListWidget, QTableWidget {
    background: rgba(255,255,255,0.92);
    border: 1px solid #E5E7EB;
    border-radius: 10px;
}
QHeaderView::section {
    background: #EAF6FB;
    padding: 6px;
    border: none;
    font-weight: 600;
}
""")

        self.setWindowTitle("SISTEMA KIOSCO ECEBA")
        self.setMinimumSize(900, 600)

        self.carrito: Dict[int, CartItem] = {}

        # Layout principal: header + contenido
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(8)

        # Header (franjita)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.logo_lbl = QLabel()
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            self.logo_lbl.setPixmap(pix.scaledToHeight(44, Qt.SmoothTransformation))
        header.addWidget(self.logo_lbl, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel("Sistema Kiosco ECEBA")
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        header.addWidget(self.title_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        header.addStretch(1)
        outer.addLayout(header)

        # Contenido (productos + carrito)
        root = QHBoxLayout()
        outer.addLayout(root, 1)

        # Izquierda: productos (grid de botones)
        left = QVBoxLayout()
        left.setContentsMargins(5, 5, 5, 5)
        left.setSpacing(6)
        root.addLayout(left, 3)  # le doy más peso a productos

        self.lbl_prod = QLabel("Productos")
        self.lbl_prod.setStyleSheet("font-size: 14px; font-weight: 600;")
        left.addWidget(self.lbl_prod, 0, Qt.AlignmentFlag.AlignTop)

        self.products_grid = QGridLayout()
        self.products_grid.setContentsMargins(0, 0, 0, 0)
        self.products_grid.setHorizontalSpacing(10)
        self.products_grid.setVerticalSpacing(10)
        left.addLayout(self.products_grid, 1)

        # Derecha: carrito
        right = QVBoxLayout()
        root.addLayout(right, 1)

        self.lbl_cart = QLabel("Carrito")
        self.lbl_cart.setStyleSheet("font-size: 18px; font-weight: 600;")
        right.addWidget(self.lbl_cart)

        self.cart_list = QListWidget()
        self.cart_list.itemDoubleClicked.connect(self.sub_one_from_item)
        right.addWidget(self.cart_list, 1)

        self.lbl_total = QLabel("Total: $0")
        self.lbl_total.setStyleSheet("font-size: 20px; font-weight: 700;")
        right.addWidget(self.lbl_total)

        btns = QHBoxLayout()
        right.addLayout(btns)

        self.btn_clear = QPushButton("Cancelar")
        self.btn_clear.clicked.connect(self.clear_cart)
        btns.addWidget(self.btn_clear)

        self.btn_ok = QPushButton("OK / Cobrar")
        self.btn_ok.setStyleSheet("font-size: 16px; padding: 10px;")
        self.btn_ok.clicked.connect(self.go_checkout)
        btns.addWidget(self.btn_ok)

        self.btn_admin = QPushButton("Administrar productos")
        self.btn_admin.clicked.connect(self.open_admin)
        right.addWidget(self.btn_admin)

        self.btn_sales = QPushButton("Historial de ventas")
        self.btn_sales.clicked.connect(self.open_sales_history)
        right.addWidget(self.btn_sales)

        self.load_products()

    def load_products(self):
        # Limpiar grid
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.productos = listar_productos_activos()

        cols = 3
        r = c = 0
        for p in self.productos:
            btn = QPushButton(f"{p.nombre}\n{money_str(p.precio_centavos)}\nStock: {p.stock}")
            img = getattr(p, "imagen_path", None)
            if img:
                try:
                    path = Path(img)
                    if path.exists():
                        pix = QPixmap(str(path))
                        if not pix.isNull():
                            btn.setIcon(QIcon(pix))
                            btn.setIconSize(btn.sizeHint())
                except Exception:
                    pass

            btn.setMinimumHeight(90)
            btn.setEnabled(p.stock > 0)
            btn.clicked.connect(lambda checked=False, prod=p: self.add_product(prod))
            self.products_grid.addWidget(btn, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1

        self.refresh_cart()

    def add_product(self, prod: Producto):
        if prod.stock <= 0:
            return
        if prod.id not in self.carrito:
            self.carrito[prod.id] = CartItem(producto=prod, cantidad=1)
        else:
            self.carrito[prod.id].cantidad += 1
        self.refresh_cart()

    def refresh_cart(self):
        self.cart_list.clear()
        total = 0

        for item in self.carrito.values():
            total += item.subtotal_centavos
            text = f"{item.producto.nombre} x{item.cantidad} = {money_str(item.subtotal_centavos)}"
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, item.producto.id)
            self.cart_list.addItem(it)

        self.lbl_total.setText(f"Total: {money_str(total)}")

    def sub_one_from_item(self, it: QListWidgetItem):
        pid = int(it.data(Qt.UserRole))
        if pid in self.carrito:
            self.carrito[pid].cantidad -= 1
            if self.carrito[pid].cantidad <= 0:
                del self.carrito[pid]
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

    def open_sales_history(self):
        dlg = SalesHistoryDialog(self)
        dlg.exec()