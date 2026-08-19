"""Widget del logotipo de ContApp con icono 'C' vectorial."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)


class LogoIcon(QWidget):
    """Icono 'C' circular dibujado vectorialmente con antialiasing."""

    def __init__(
        self,
        size: int = 34,
        color: str = "#2563EB",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = float(min(self.width(), self.height()))
        margin = 1.0
        d_outer = s - 2.0 * margin
        r_outer = d_outer / 2.0
        cx = s / 2.0
        cy = s / 2.0

        # Grosor del anillo (proporción del radio interno)
        inner_ratio = 0.40
        r_inner = r_outer * inner_ratio
        d_inner = r_inner * 2.0

        rect_outer = QRectF(cx - r_outer, cy - r_outer, d_outer, d_outer)
        rect_inner = QRectF(cx - r_inner, cy - r_inner, d_inner, d_inner)

        # Ángulo de apertura en la derecha: de -36° a +36° (apertura de 72°)
        start_angle = 36.0
        sweep_angle = 360.0 - (2.0 * start_angle)

        path = QPainterPath()
        path.arcMoveTo(rect_outer, start_angle)
        path.arcTo(rect_outer, start_angle, sweep_angle)
        path.arcTo(rect_inner, start_angle + sweep_angle, -sweep_angle)
        path.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawPath(path)
        p.end()


class LogoContApp(QWidget):
    """Componente completo de Marca: Icono 'C' + Texto 'CONTAPP'."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._icon = LogoIcon(size=32, color="#2563EB")
        layout.addWidget(self._icon)

        self._label = QLabel("CONTAPP")
        self._label.setStyleSheet(
            """
            QLabel {
                color: #0F172A;
                font-size: 18px;
                font-weight: 800;
                letter-spacing: 1.5px;
            }
            """
        )
        layout.addWidget(self._label)
