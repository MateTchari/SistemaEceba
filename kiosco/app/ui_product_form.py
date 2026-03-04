from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QPushButton, QHBoxLayout, QFileDialog, QMessageBox, QCheckBox, QLabel
)


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


class ProductFormDialog(QDialog):
    def __init__(self, parent=None, *, title="Producto", initial=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        self.result_data = None
        self._picked_image_path: str | None = None  # ✅ solo si elige una nueva

        lay = QVBoxLayout(self)
        form = QFormLayout()
        lay.addLayout(form)

        self.in_nombre = QLineEdit()
        form.addRow("Nombre", self.in_nombre)

        self.in_precio = QLineEdit()
        self.in_precio.setPlaceholderText("Ej: 1500 o 1500,00")
        form.addRow("Precio", self.in_precio)

        self.in_stock = QSpinBox()
        self.in_stock.setRange(0, 10_000_000)
        form.addRow("Stock", self.in_stock)

        self.chk_activo = QCheckBox("Activo")
        self.chk_activo.setChecked(True)
        form.addRow("", self.chk_activo)

        # Imagen (solo seleccionar, NO copiar acá)
        img_row = QHBoxLayout()
        self.lbl_imagen = QLabel("(sin imagen)")
        self.lbl_imagen.setStyleSheet("color:#374151;")
        self.btn_browse = QPushButton("Elegir imagen...")
        self.btn_browse.clicked.connect(self.pick_image)
        img_row.addWidget(self.lbl_imagen, 1)
        img_row.addWidget(self.btn_browse)
        form.addRow("Imagen", img_row)

        # Botones
        btns = QHBoxLayout()
        lay.addLayout(btns)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("Guardar")
        self.btn_ok.clicked.connect(self.on_ok)
        btns.addWidget(self.btn_ok)

        # Cargar datos iniciales si es edición
        self._initial_imagen_path = None
        if initial:
            self.in_nombre.setText(initial.get("nombre", ""))
            self.in_precio.setText(centavos_to_money_str(initial.get("precio_centavos", 0)))
            self.in_stock.setValue(int(initial.get("stock", 0)))
            self.chk_activo.setChecked(bool(initial.get("activo", 1)))

            self._initial_imagen_path = initial.get("imagen_path")
            if self._initial_imagen_path:
                self.lbl_imagen.setText(Path(self._initial_imagen_path).name)

    def pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Elegir imagen",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._picked_image_path = path
            self.lbl_imagen.setText(Path(path).name)

    def on_ok(self):
        try:
            nombre = self.in_nombre.text().strip()
            if not nombre:
                raise ValueError("Nombre vacío.")
            precio_centavos = money_to_centavos(self.in_precio.text())
            stock = int(self.in_stock.value())
            activo = 1 if self.chk_activo.isChecked() else 0

            # ✅ clave:
            # - si eligió imagen nueva => mandamos esa ruta (services la copia a images/)
            # - si NO eligió => mandamos None para NO pisar la imagen existente
            imagen_path = self._picked_image_path

            self.result_data = {
                "nombre": nombre,
                "precio_centavos": precio_centavos,
                "stock": stock,
                "activo": activo,
                "imagen_path": imagen_path,
            }
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Atención", str(e))