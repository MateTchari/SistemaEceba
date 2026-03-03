from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QPushButton, QHBoxLayout, QFileDialog, QMessageBox, QCheckBox
)
from pathlib import Path
from uuid import uuid4
import shutil

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

def project_root() -> Path:
    # ui_product_form.py está en kiosco/app/
    # parents[1] => kiosco/
    return Path(__file__).resolve().parents[1]


def copy_image_to_project(original_path: str) -> str:
    src = Path(original_path)
    if not src.exists():
        raise ValueError("La imagen seleccionada no existe.")

    images_dir = project_root() / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    ext = src.suffix.lower() if src.suffix else ".png"
    new_name = f"prod_{uuid4().hex}{ext}"
    dst = images_dir / new_name

    shutil.copy2(src, dst)
    return str(dst)

class ProductFormDialog(QDialog):
    def __init__(self, parent=None, *, title="Producto", initial=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        self.result_data = None  # dict con campos

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

        # Imagen
        img_row = QHBoxLayout()
        self.in_imagen = QLineEdit()
        self.in_imagen.setPlaceholderText("Ruta de imagen (opcional)")
        self.btn_browse = QPushButton("Elegir...")
        self.btn_browse.clicked.connect(self.pick_image)
        img_row.addWidget(self.in_imagen, 1)
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
        if initial:
            self.in_nombre.setText(initial.get("nombre", ""))
            self.in_precio.setText(centavos_to_money_str(initial.get("precio_centavos", 0)))
            self.in_stock.setValue(int(initial.get("stock", 0)))
            self.chk_activo.setChecked(bool(initial.get("activo", 1)))
            self.in_imagen.setText(initial.get("imagen_path") or "")

    def pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Elegir imagen",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            try:
                new_path = copy_image_to_project(path)
                self.in_imagen.setText(new_path)
            except Exception as e:
                QMessageBox.warning(self, "Atención", str(e))

    def on_ok(self):
        try:
            nombre = self.in_nombre.text().strip()
            if not nombre:
                raise ValueError("Nombre vacío.")
            precio_centavos = money_to_centavos(self.in_precio.text())
            stock = int(self.in_stock.value())
            activo = 1 if self.chk_activo.isChecked() else 0
            imagen_path = self.in_imagen.text().strip() or None

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