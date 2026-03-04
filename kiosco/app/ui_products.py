from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QCheckBox, QInputDialog
)

from app.services import buscar_productos, crear_producto, actualizar_producto, set_activo, eliminar_producto
from app.ui_product_form import ProductFormDialog


def money_to_centavos(text: str) -> int:
    s = text.strip().replace(",", ".")
    if not s:
        return 0
    if "." in s:
        a, b = s.split(".", 1)
        a = a or "0"
        b = (b + "00")[:2]
        return int(a) * 100 + int(b)
    return int(s) * 100


def centavos_to_money_str(c: int) -> str:
    return f"{c/100:.2f}".replace(".", ",")


class ProductsDialog(QDialog):
    ADMIN_PASSWORD = "ECEBAADMIN123"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administrar productos")
        self.setMinimumSize(950, 550)

        self._is_admin = False  # ✅ importante: sesión admin

        root = QVBoxLayout(self)

        # Top bar
        top = QHBoxLayout()
        root.addLayout(top)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por nombre...")
        self.search.textChanged.connect(self.refresh)
        top.addWidget(self.search, 1)

        self.chk_inactivos = QCheckBox("Mostrar inactivos")
        self.chk_inactivos.setChecked(True)
        self.chk_inactivos.stateChanged.connect(self.refresh)
        top.addWidget(self.chk_inactivos)

        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.clicked.connect(self.refresh)
        top.addWidget(self.btn_refresh)

        # Tabla
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Precio", "Stock", "Activo", "Imagen"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, 1)

        # Botones
        btns = QHBoxLayout()
        root.addLayout(btns)

        self.btn_add = QPushButton("Agregar")
        self.btn_add.clicked.connect(self.add_product)
        btns.addWidget(self.btn_add)

        self.btn_edit = QPushButton("Editar")
        self.btn_edit.clicked.connect(self.edit_product)
        btns.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.clicked.connect(self.delete_product)
        btns.addWidget(self.btn_delete)


        btns.addStretch(1)

        self.refresh()

    def require_admin(self) -> bool:
        """Pide contraseña una vez por sesión de esta ventana."""
        if self._is_admin:
            return True

        text, ok = QInputDialog.getText(
            self,
            "Acceso de administrador",
            "Ingresá la contraseña para administrar productos:",
            QLineEdit.EchoMode.Password,
        )

        if not ok:
            return False

        if text == self.ADMIN_PASSWORD:
            self._is_admin = True
            return True

        QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña ingresada no es válida.")
        return False

    def selected_product_row(self):
        items = self.table.selectedItems()
        if not items:
            return None
        return items[0].row()

    def selected_product_id(self):
        row = self.selected_product_row()
        if row is None:
            return None
        return int(self.table.item(row, 0).text())

    def refresh(self):
        q = self.search.text()
        incluir = self.chk_inactivos.isChecked()
        productos = buscar_productos(q, incluir_inactivos=incluir)

        # Orden: verdes, naranjas, rojos, inactivos
        def prioridad(p):
            if p.activo == 0:
                return (3, 0)
            if p.stock >= 20:
                return (0, -p.stock)
            elif p.stock >= 10:
                return (1, -p.stock)
            else:
                return (2, -p.stock)

        productos.sort(key=prioridad)

        self.table.setRowCount(0)
        for p in productos:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self.table.setItem(row, 1, QTableWidgetItem(p.nombre))
            self.table.setItem(row, 2, QTableWidgetItem(centavos_to_money_str(p.precio_centavos)))
            self.table.setItem(row, 3, QTableWidgetItem(str(p.stock)))
            self.table.setItem(row, 4, QTableWidgetItem("Sí" if p.activo == 1 else "No"))
            self.table.setItem(row, 5, QTableWidgetItem("Sí" if getattr(p, "imagen_path", None) else "No"))

            # Colores (inactivo > stock)
            if p.activo == 0:
                bg = QColor(210, 210, 210)
                fg = QColor(110, 110, 110)
                for col in range(self.table.columnCount()):
                    self.table.item(row, col).setBackground(bg)
                    self.table.item(row, col).setForeground(fg)
            else:
                if p.stock < 10:
                    bg = QColor(255, 120, 120)  # rojo
                elif p.stock < 20:
                    bg = QColor(255, 200, 120)  # naranja
                else:
                    bg = QColor(170, 235, 170)  # verde
                for col in range(self.table.columnCount()):
                    self.table.item(row, col).setBackground(bg)

        self.table.resizeColumnsToContents()

    def add_product(self):
        if not self.require_admin():
            return

        dlg = ProductFormDialog(self, title="Agregar producto")
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            d = dlg.result_data
            try:
                crear_producto(d["nombre"], d["precio_centavos"], d["stock"], d.get("imagen_path"))
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_product(self):
        if not self.require_admin():
            return

        pid = self.selected_product_id()
        row = self.selected_product_row()
        if pid is None or row is None:
            QMessageBox.information(self, "Atención", "Seleccioná un producto.")
            return

        initial = {
            "nombre": self.table.item(row, 1).text(),
            "precio_centavos": money_to_centavos(self.table.item(row, 2).text()),
            "stock": int(self.table.item(row, 3).text()),
            "activo": 1 if self.table.item(row, 4).text() == "Sí" else 0,
            "imagen_path": None,
        }

        dlg = ProductFormDialog(self, title=f"Editar producto #{pid}", initial=initial)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            d = dlg.result_data
            try:
                actualizar_producto(pid, d["nombre"], d["precio_centavos"], d["stock"], d["activo"], d.get("imagen_path"))
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


    def delete_product(self):
        if not self.require_admin():
            return

        pid = self.selected_product_id()
        row = self.selected_product_row()
        if pid is None or row is None:
            QMessageBox.information(self, "Atención", "Seleccioná un producto.")
            return

        nombre = self.table.item(row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar '{nombre}' (ID {pid})?\n\nSi el producto ya tiene ventas, se archivará (quedará inactivo).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            res = eliminar_producto(pid)
            if res == "archivado":
                QMessageBox.information(self, "Listo", "El producto tenía ventas, así que se archivó (quedó inactivo).")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))