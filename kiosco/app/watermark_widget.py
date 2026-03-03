from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtCore import Qt


class WatermarkWidget(QWidget):
    def __init__(self, watermark_path: Path, parent=None, opacity: float = 0.06, veil: float = 0.18):
        super().__init__(parent)
        self.opacity = opacity      # opacidad del logo (0.04 - 0.10)
        self.veil = veil            # velo blanco para legibilidad (0.10 - 0.30)

        self._pix = QPixmap(str(watermark_path)) if watermark_path.exists() else QPixmap()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pix.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 1) Velo blanco (fondo limpio)
        if self.veil > 0:
            painter.setOpacity(self.veil)
            painter.fillRect(self.rect(), QColor(255, 255, 255))

        # 2) Logo como watermark (grande pero sutil)
        painter.setOpacity(self.opacity)

        # Escala grande, pero no “full wallpaper”: ocupa ~70% del alto
        target_h = int(self.height() * 0.70)
        scaled = self._pix.scaledToHeight(target_h, Qt.SmoothTransformation)

        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        painter.end()