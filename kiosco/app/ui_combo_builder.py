from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QFileDialog, QInputDialog,
    QComboBox, QSpinBox
)

from app.services import (
    listar_combos_admin,
    listar_productos_para_combo,
    obtener_combo_definicion,
    crear_combo,
    actualizar_combo,
    eliminar_combo,
)
from app.ui_product_form import money_to_centavos


def money_str(centavos: int) -> str:
    pesos = centavos // 100
    return f"${pesos:,}".replace(",", ".")


class OpcionProductoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar opción")
        self.setMinimumWidth(420)

        self.result_data = None
        self.productos = listar_productos_para_combo()

        lay = QVBoxLayout(self)

        lay.addWidget(QLabel("Producto"))
        self.cmb_producto = QComboBox()
        for p in self.productos:
            self.cmb_producto.addItem(f"{p.nombre} ({p.categoria}) - Stock: {p.stock}", p)
        lay.addWidget(self.cmb_producto)

        lay.addWidget(QLabel("Cantidad"))
        self.spn_cantidad = QSpinBox()
        self.spn_cantidad.setRange(1, 1000)
        self.spn_cantidad.setValue(1)
        lay.addWidget(self.spn_cantidad)

        btns = QHBoxLayout()
        lay.addLayout(btns)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_ok = QPushButton("Agregar")
        btn_ok.clicked.connect(self.on_ok)
        btns.addWidget(btn_ok)

    def on_ok(self):
        prod = self.cmb_producto.currentData()
        if prod is None:
            QMessageBox.warning(self, "Atención", "Seleccioná un producto.")
            return

        self.result_data = {
            "producto_id": int(prod.id),
            "nombre": prod.nombre,
            "cantidad": int(self.spn_cantidad.value()),
            "precio_centavos": int(prod.precio_centavos),
        }
        self.accept()


class ComboBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administrar combos")
        self.setMinimumSize(1100, 600)

        self.current_combo_id: int | None = None
        self.current_grupos: list[dict] = []
        self.current_image_path: str | None = None

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        root.addLayout(left, 1)

        left.addWidget(QLabel("Combos"))

        self.list_combos = QListWidget()
        self.list_combos.itemSelectionChanged.connect(self.on_select_combo)
        left.addWidget(self.list_combos, 1)

        btn_new = QPushButton("Nuevo combo")
        btn_new.clicked.connect(self.new_combo)
        left.addWidget(btn_new)

        right = QVBoxLayout()
        root.addLayout(right, 2)

        right.addWidget(QLabel("Nombre"))
        self.in_nombre = QLineEdit()
        right.addWidget(self.in_nombre)

        right.addWidget(QLabel("Precio"))
        self.in_precio = QLineEdit()
        self.in_precio.setPlaceholderText("Ej: 4500 o 4500,00")
        right.addWidget(self.in_precio)

        img_row = QHBoxLayout()
        self.lbl_imagen = QLabel("(sin imagen)")
        btn_img = QPushButton("Elegir imagen...")
        btn_img.clicked.connect(self.pick_image)
        img_row.addWidget(self.lbl_imagen, 1)
        img_row.addWidget(btn_img)
        right.addLayout(img_row)

        center = QHBoxLayout()
        right.addLayout(center, 1)

        grupos_box = QVBoxLayout()
        center.addLayout(grupos_box, 1)

        grupos_box.addWidget(QLabel("Grupos del combo"))

        self.list_grupos = QListWidget()
        self.list_grupos.itemSelectionChanged.connect(self.on_select_group)
        grupos_box.addWidget(self.list_grupos, 1)

        grupos_btns = QHBoxLayout()
        grupos_box.addLayout(grupos_btns)

        btn_add_group = QPushButton("Agregar grupo")
        btn_add_group.clicked.connect(self.add_group)
        grupos_btns.addWidget(btn_add_group)

        btn_remove_group = QPushButton("Quitar grupo")
        btn_remove_group.clicked.connect(self.remove_group)
        grupos_btns.addWidget(btn_remove_group)

        opciones_box = QVBoxLayout()
        center.addLayout(opciones_box, 2)

        opciones_box.addWidget(QLabel("Opciones del grupo seleccionado"))

        self.table_options = QTableWidget(0, 2)
        self.table_options.setHorizontalHeaderLabels(["Producto", "Cantidad"])
        opciones_box.addWidget(self.table_options, 1)

        opciones_btns = QHBoxLayout()
        opciones_box.addLayout(opciones_btns)

        btn_add_option = QPushButton("Agregar opción")
        btn_add_option.clicked.connect(self.add_option)
        opciones_btns.addWidget(btn_add_option)

        btn_remove_option = QPushButton("Quitar opción")
        btn_remove_option.clicked.connect(self.remove_option)
        opciones_btns.addWidget(btn_remove_option)

        btns_bottom = QHBoxLayout()
        right.addLayout(btns_bottom)

        btn_save = QPushButton("Guardar combo")
        btn_save.clicked.connect(self.save_combo)
        btns_bottom.addWidget(btn_save)

        btn_delete = QPushButton("Eliminar combo")
        btn_delete.clicked.connect(self.delete_combo)
        btns_bottom.addWidget(btn_delete)

        self.refresh_combos()

    def refresh_combos(self):
        self.list_combos.clear()
        self.combos = listar_combos_admin()
        for c in self.combos:
            item = QListWidgetItem(f"{c.nombre} - {money_str(c.precio_centavos)}")
            item.setData(32, c.id)
            self.list_combos.addItem(item)

    def refresh_groups(self):
        self.list_grupos.clear()
        for g in self.current_grupos:
            item = QListWidgetItem(g["nombre"])
            self.list_grupos.addItem(item)
        self.refresh_options()

    def refresh_options(self):
        self.table_options.setRowCount(0)
        gidx = self.list_grupos.currentRow()
        if gidx < 0 or gidx >= len(self.current_grupos):
            return

        grupo = self.current_grupos[gidx]
        for op in grupo["opciones"]:
            row = self.table_options.rowCount()
            self.table_options.insertRow(row)
            self.table_options.setItem(row, 0, QTableWidgetItem(op["nombre"]))
            self.table_options.setItem(row, 1, QTableWidgetItem(str(op["cantidad"])))

        self.table_options.resizeColumnsToContents()

    def new_combo(self):
        self.current_combo_id = None
        self.current_grupos = []
        self.current_image_path = None
        self.in_nombre.clear()
        self.in_precio.clear()
        self.lbl_imagen.setText("(sin imagen)")
        self.list_combos.clearSelection()
        self.refresh_groups()

    def on_select_combo(self):
        items = self.list_combos.selectedItems()
        if not items:
            return

        combo_id = int(items[0].data(32))
        combo = next((c for c in self.combos if c.id == combo_id), None)
        if combo is None:
            return

        data = obtener_combo_definicion(combo_id)

        self.current_combo_id = combo_id
        self.in_nombre.setText(combo.nombre)
        self.in_precio.setText(str(combo.precio_centavos // 100))
        self.current_image_path = combo.imagen_path
        self.lbl_imagen.setText(Path(combo.imagen_path).name if combo.imagen_path else "(sin imagen)")

        self.current_grupos = []
        for g in data["grupos"]:
            self.current_grupos.append({
                "nombre": g["nombre"],
                "opciones": [
                    {
                        "producto_id": int(op["producto_id"]),
                        "nombre": op["nombre"],
                        "cantidad": int(op["cantidad"]),
                        "precio_centavos": int(op["precio_centavos"]),
                    }
                    for op in g["opciones"]
                ],
            })

        self.refresh_groups()

    def on_select_group(self):
        self.refresh_options()

    def pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Elegir imagen",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.current_image_path = path
            self.lbl_imagen.setText(Path(path).name)

    def add_group(self):
        text, ok = QInputDialog.getText(self, "Nuevo grupo", "Nombre del grupo:")
        if not ok or not text.strip():
            return
        self.current_grupos.append({"nombre": text.strip(), "opciones": []})
        self.refresh_groups()
        self.list_grupos.setCurrentRow(len(self.current_grupos) - 1)

    def remove_group(self):
        gidx = self.list_grupos.currentRow()
        if gidx < 0:
            QMessageBox.information(self, "Atención", "Seleccioná un grupo.")
            return
        del self.current_grupos[gidx]
        self.refresh_groups()

    def add_option(self):
        gidx = self.list_grupos.currentRow()
        if gidx < 0:
            QMessageBox.information(self, "Atención", "Seleccioná primero un grupo.")
            return

        dlg = OpcionProductoDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted or not dlg.result_data:
            return

        nuevo = dlg.result_data
        grupo = self.current_grupos[gidx]

        for op in grupo["opciones"]:
            if int(op["producto_id"]) == int(nuevo["producto_id"]):
                op["cantidad"] = int(op["cantidad"]) + int(nuevo["cantidad"])
                self.refresh_options()
                return

        grupo["opciones"].append(nuevo)
        self.refresh_options()

    def remove_option(self):
        gidx = self.list_grupos.currentRow()
        if gidx < 0:
            QMessageBox.information(self, "Atención", "Seleccioná un grupo.")
            return

        row = self.table_options.currentRow()
        if row < 0:
            QMessageBox.information(self, "Atención", "Seleccioná una opción.")
            return

        del self.current_grupos[gidx]["opciones"][row]
        self.refresh_options()

    def save_combo(self):
        try:
            nombre = self.in_nombre.text().strip()
            precio_centavos = money_to_centavos(self.in_precio.text())

            if self.current_combo_id is None:
                crear_combo(nombre, precio_centavos, self.current_grupos, self.current_image_path)
                QMessageBox.information(self, "Listo", "Combo creado.")
            else:
                actualizar_combo(self.current_combo_id, nombre, precio_centavos, self.current_grupos, self.current_image_path)
                QMessageBox.information(self, "Listo", "Combo actualizado.")

            self.refresh_combos()
            self.new_combo()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_combo(self):
        if self.current_combo_id is None:
            QMessageBox.information(self, "Atención", "Seleccioná un combo.")
            return

        confirm = QMessageBox.question(
            self,
            "Eliminar combo",
            "¿Seguro que querés eliminar este combo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            eliminar_combo(self.current_combo_id)
            QMessageBox.information(self, "Listo", "Combo eliminado.")
            self.refresh_combos()
            self.new_combo()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))