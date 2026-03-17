from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QLabel,
    QPushButton,
    QWidget,
    QScrollArea,
    QGridLayout,
    QButtonGroup,
    QFrame,
)

from app.services import obtener_combo_definicion


def money_str(centavos: int) -> str:
    pesos = centavos // 100
    return f"${pesos:,}".replace(",", ".")


class ComboSelectorDialog(QDialog):
    def __init__(self, combo_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Elegir opciones del combo")
        self.setMinimumSize(900, 650)

        self.result_data = None
        self.combo = obtener_combo_definicion(combo_id)

        self.button_groups: list[tuple[str, QButtonGroup]] = []
        self.button_data: dict[QPushButton, dict] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Encabezado
        title = QLabel(self.combo["nombre"])
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #0B8EC5;")
        root.addWidget(title)

        price = QLabel(f"Precio del combo: {money_str(int(self.combo['precio_centavos']))}")
        price.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151;")
        root.addWidget(price)

        hint = QLabel("Elegí una opción por cada grupo")
        hint.setStyleSheet("color: #6B7280;")
        root.addWidget(hint)

        # Scroll principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Un bloque visual por cada grupo
        for grupo in self.combo["grupos"]:
            grupo_title = QLabel(grupo["nombre"])
            grupo_title.setStyleSheet(
                "font-size: 16px; font-weight: 700; color: #111827; margin-top: 8px;"
            )
            content_layout.addWidget(grupo_title)

            grid_wrap = QWidget()
            grid = QGridLayout(grid_wrap)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(12)
            content_layout.addWidget(grid_wrap)

            button_group = QButtonGroup(self)
            button_group.setExclusive(True)

            col = 0
            row = 0

            for op in grupo["opciones"]:
                btn = QPushButton()
                btn.setCheckable(True)
                btn.setMinimumSize(190, 120)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)

                texto = op["nombre"]
                if int(op.get("cantidad", 1)) > 1:
                    texto += f" x{int(op['cantidad'])}"
                texto += f"\nStock: {int(op.get('stock', 0))}"

                btn.setText(texto)
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        color: #111827;
                        border: 2px solid #D1D5DB;
                        border-radius: 12px;
                        padding: 10px;
                        text-align: left;
                        font-size: 12px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        border: 2px solid #0B8EC5;
                        background: #F8FBFD;
                    }
                    QPushButton:checked {
                        border: 2px solid #0B8EC5;
                        background: #EAF6FB;
                    }
                    QPushButton:disabled {
                        background: #F3F4F6;
                        color: #9CA3AF;
                        border: 2px solid #E5E7EB;
                    }
                """)

                img = op.get("imagen_path")
                if img:
                    try:
                        path = Path(img)
                        if path.exists():
                            pix = QPixmap(str(path))
                            if not pix.isNull():
                                btn.setIcon(QIcon(pix))
                                btn.setIconSize(QSize(56, 56))
                    except Exception:
                        pass

                if int(op.get("stock", 0)) < int(op.get("cantidad", 1)):
                    btn.setDisabled(True)

                button_group.addButton(btn)
                self.button_data[btn] = op

                grid.addWidget(btn, row, col)

                col += 1
                if col >= 3:
                    col = 0
                    row += 1

            self.button_groups.append((grupo["nombre"], button_group))

        content_layout.addStretch(1)

        # Botones finales
        btns = QHBoxLayout()
        root.addLayout(btns)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #E5E7EB;
                color: #111827;
                border: none;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #D1D5DB;
            }
        """)
        btns.addWidget(btn_cancel)

        btns.addStretch(1)

        btn_ok = QPushButton("Agregar combo")
        btn_ok.clicked.connect(self.on_ok)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0B8EC5;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #0A7FB1;
            }
        """)
        btns.addWidget(btn_ok)

    def on_ok(self):
        componentes = []
        partes_desc = []

        for grupo_nombre, button_group in self.button_groups:
            btn = button_group.checkedButton()
            if btn is None:
                QMessageBox.warning(
                    self,
                    "Atención",
                    f"Tenés que elegir una opción para: {grupo_nombre}",
                )
                return

            op = self.button_data[btn]

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