from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout
)

def money_str(centavos: int) -> str:
    return f"${centavos/100:.2f}".replace(".", ",")


class CheckoutDialog(QDialog):
    def __init__(self, total_centavos: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cobro")
        self.total_centavos = total_centavos
        self.pago_centavos = 0

        lay = QVBoxLayout(self)

        self.lbl_total = QLabel(f"TOTAL: {money_str(total_centavos)}")
        self.lbl_total.setStyleSheet("font-size: 28px; font-weight: 800;")
        lay.addWidget(self.lbl_total)

        self.input_pago = QLineEdit()
        self.input_pago.setPlaceholderText("Paga con (ej: 2000 o 2000.00)")
        self.input_pago.setStyleSheet("font-size: 18px; padding: 10px;")
        self.input_pago.textChanged.connect(self.recalc)
        lay.addWidget(self.input_pago)

        self.lbl_result = QLabel("Vuelto: $0,00")
        self.lbl_result.setStyleSheet("font-size: 22px; font-weight: 700;")
        lay.addWidget(self.lbl_result)

        btns = QHBoxLayout()
        lay.addLayout(btns)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("Confirmar")
        self.btn_ok.setStyleSheet("font-size: 16px; padding: 10px;")
        self.btn_ok.clicked.connect(self.confirm)
        btns.addWidget(self.btn_ok)

    def parse_centavos(self, s: str) -> int:
        s = s.strip().replace(",", ".")
        if not s:
            return 0
        if "." in s:
            parts = s.split(".")
            if len(parts) != 2:
                raise ValueError("Formato inválido.")
            pesos = int(parts[0]) if parts[0] else 0
            cent = parts[1].ljust(2, "0")[:2]
            return pesos * 100 + int(cent)
        return int(s) * 100

    def recalc(self):
        try:
            pago = self.parse_centavos(self.input_pago.text())
            self.pago_centavos = pago
            diff = pago - self.total_centavos
            if diff >= 0:
                self.lbl_result.setText(f"VUELTO: {money_str(diff)}")
            else:
                self.lbl_result.setText(f"FALTA: {money_str(-diff)}")
        except Exception:
            self.lbl_result.setText("Ingrese un monto válido")

    def confirm(self):
        try:
            pago = self.parse_centavos(self.input_pago.text())
        except Exception:
            QMessageBox.warning(self, "Atención", "Monto inválido.")
            return

        if pago < self.total_centavos:
            QMessageBox.warning(self, "Atención", "El pago es menor al total.")
            return

        self.pago_centavos = pago
        self.accept()