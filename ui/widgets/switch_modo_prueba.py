"""Switch visual para activar/desactivar el modo prueba en la topbar."""
from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class ToggleSwitch(QAbstractButton):
    """Control de switch deslizante tipo píldora 100% redondeado con animación suave."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(46, 24)

        self._thumb_position: float = 0.0
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(130)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.toggled.connect(self._on_toggled)

    def get_thumb_position(self) -> float:
        return self._thumb_position

    def set_thumb_position(self, pos: float) -> None:
        self._thumb_position = pos
        self.update()

    thumb_position = Property(float, get_thumb_position, set_thumb_position)

    def _on_toggled(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def set_checked_instant(self, checked: bool) -> None:
        """Establece el estado sin animación (para inicialización)."""
        self.setChecked(checked)
        self._thumb_position = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = h / 2.0

        # Color de fondo según el estado
        # Activo: Azul (#2563EB), Inactivo: Gris suave (#CBD5E1)
        if self.isChecked():
            track_color = QColor("#2563EB")
        else:
            track_color = QColor("#CBD5E1")

        # Dibujar píldora redondeada de fondo
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Círculo deslizante blanco (Thumb)
        margin = 2.5
        thumb_diameter = h - 2 * margin
        max_travel = w - 2 * margin - thumb_diameter
        thumb_x = margin + (self._thumb_position * max_travel)
        thumb_y = margin

        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(thumb_x, thumb_y, thumb_diameter, thumb_diameter))
        p.end()


class SwitchModoPrueba(QWidget):
    """Contenedor con label y toggle switch para el Modo Prueba."""

    modo_prueba_cambiado = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._label = QLabel("Modo prueba")
        self._label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        layout.addWidget(self._label)

        self._switch = ToggleSwitch()
        self._switch.setToolTip(
            "Cuando está activo, los resultados se guardan en una carpeta "
            "temporal y los archivos originales NO se modifican."
        )
        self._switch.toggled.connect(self.modo_prueba_cambiado.emit)
        layout.addWidget(self._switch)

    def esta_activo(self) -> bool:
        return self._switch.isChecked()

    def set_activo(self, activo: bool) -> None:
        self._switch.set_checked_instant(activo)