from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QLabel,
)

from app.services import obtener_combo_definicion


class ComboSelectorDialog(QDialog):
    def __init__(self, combo_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Elegir opciones del combo")
        self.setMinimumWidth(460)

        self.result_data = None
        self.combo = obtener_combo_definicion(combo_id)

        lay = QVBoxLayout(self)

        title = QLabel(self.combo["nombre"])
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        lay.addWidget(title)

        price = QLabel(f"Precio del combo: ${self.combo['precio_centavos'] // 100:,}".replace(",", "."))
        price.setStyleSheet("color: #555;")
        lay.addWidget(price)

        form = QFormLayout()
        lay.addLayout(form)

        self.selectores = []

        for grupo in self.combo["grupos"]:
            cmb = QComboBox()
            for op in grupo["opciones"]:
                texto = op["nombre"]
                if int(op.get("cantidad", 1)) > 1:
                    texto += f" x{int(op['cantidad'])}"
                texto += f" (Stock: {int(op.get('stock', 0))})"
                cmb.addItem(texto, op)
            form.addRow(grupo["nombre"], cmb)
            self.selectores.append((grupo["nombre"], cmb))

        btns = QHBoxLayout()
        lay.addLayout(btns)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_ok = QPushButton("Agregar")
        btn_ok.clicked.connect(self.on_ok)
        btns.addWidget(btn_ok)

    def on_ok(self):
        componentes = []
        partes_desc = []

        for grupo_nombre, cmb in self.selectores:
            op = cmb.currentData()
            if not op:
                QMessageBox.warning(self, "Atención", f"Falta elegir una opción para {grupo_nombre}.")
                return

            if int(op.get("stock", 0)) < int(op.get("cantidad", 1)):
                QMessageBox.warning(
                    self,
                    "Sin stock",
                    f"No hay stock suficiente para {op['nombre']}.",
                )
                return

            componentes.append({
                "producto_id": int(op["producto_id"]),
                "nombre": op["nombre"],
                "cantidad": int(op.get("cantidad", 1)),
                "precio_centavos": int(op["precio_centavos"]),
            })
            partes_desc.append(f"{grupo_nombre}: {op['nombre']}")

        self.result_data = {
            "componentes": componentes,
            "descripcion": " | ".join(partes_desc),
        }
        self.accept()