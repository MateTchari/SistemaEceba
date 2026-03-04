from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QDateEdit
)
from PySide6.QtCore import QDate

from app.services import listar_ventas, detalle_venta, rollback_venta


def money_str(centavos: int) -> str:
    pesos = centavos // 100
    return f"${pesos:,}".replace(",", ".")


class SalesHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historial de ventas")
        self.setMinimumSize(900, 550)

        root = QVBoxLayout(self)

        # Filtros
        top = QHBoxLayout()
        root.addLayout(top)

        top.addWidget(QLabel("Desde:"))
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate.currentDate())
        top.addWidget(self.dt_from)

        top.addWidget(QLabel("Hasta:"))
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        top.addWidget(self.dt_to)

        self.btn_search = QPushButton("Buscar")
        self.btn_search.clicked.connect(self.refresh)
        top.addWidget(self.btn_search)

        # Botón anular venta
        self.btn_rollback = QPushButton("Anular venta")
        self.btn_rollback.clicked.connect(self.on_rollback)
        top.addWidget(self.btn_rollback)

        top.addStretch(1)

        self.lbl_total = QLabel("Total del período: $0")
        self.lbl_total.setStyleSheet("font-size: 14px; font-weight: 700;")
        top.addWidget(self.lbl_total)

        # Tabla ventas
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Fecha/Hora", "Total", "Pago", "Vuelto"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.open_detail)
        root.addWidget(self.table, 1)

        self.refresh()

    def refresh(self):
        f_from = self.dt_from.date().toString("yyyy-MM-dd")
        f_to = self.dt_to.date().toString("yyyy-MM-dd")

        ventas = listar_ventas(f_from, f_to)

        self.table.setRowCount(0)
        total_periodo = 0

        for v in ventas:
            row = self.table.rowCount()
            self.table.insertRow(row)

            total_periodo += int(v["total_centavos"])

            self.table.setItem(row, 0, QTableWidgetItem(str(v["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(v["fecha_hora"]))
            self.table.setItem(row, 2, QTableWidgetItem(money_str(int(v["total_centavos"]))))
            self.table.setItem(row, 3, QTableWidgetItem(money_str(int(v["pago_centavos"]))))
            self.table.setItem(row, 4, QTableWidgetItem(money_str(int(v["vuelto_centavos"]))))

        self.table.resizeColumnsToContents()
        self.lbl_total.setText(f"Total del período: {money_str(total_periodo)}")

    def selected_venta_id(self) -> int | None:
        items = self.table.selectedItems()
        if not items:
            return None
        row = items[0].row()
        return int(self.table.item(row, 0).text())

    def on_rollback(self):
        venta_id = self.selected_venta_id()
        if venta_id is None:
            QMessageBox.information(self, "Atención", "Seleccioná una venta para anular.")
            return

        confirm = QMessageBox.question(
            self,
            "Anular venta",
            f"¿Seguro que querés anular la venta #{venta_id}?\n\nEsto devolverá el stock.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            rollback_venta(venta_id)
            QMessageBox.information(self, "Listo", "Venta anulada y stock repuesto.")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def open_detail(self, _item):
        venta_id = self.selected_venta_id()
        if venta_id is None:
            return

        det = detalle_venta(venta_id)
        if not det:
            QMessageBox.information(self, "Detalle", "No hay items.")
            return

        lines = []
        for it in det:
            lines.append(
                f"- {it['producto']} x{it['cantidad']} @ {money_str(int(it['precio_unitario_centavos']))}"
                f" = {money_str(int(it['subtotal_centavos']))}"
            )

        QMessageBox.information(self, f"Venta #{venta_id}", "\n".join(lines))