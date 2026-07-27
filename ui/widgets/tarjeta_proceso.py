"""Tarjeta clickeable que representa un proceso disponible.

Se muestra en el grid inicial de la pantalla Procesos. Al hacer click
(el usuario la "elige"), emite ``seleccionado``.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.recursos.tema import color_proceso


class TarjetaProceso(QFrame):
    """Tarjeta clickeable con icono, nombre y descripcion de un proceso.

    Tiene una franja de color arriba segun el proceso:
    - comprobante: sky
    - fierro: orange
    - zeus: purple
    """

    seleccionado = Signal(str)  # nombre del proceso

    def __init__(
        self,
        nombre: str,
        descripcion: str,
        icono: str = "▶",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.nombre = nombre
        self._acento = color_proceso(nombre)
        self.setObjectName("TarjetaProceso")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(220, 170)
        self.setMaximumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._actualizar_estilo(hover=False, presionado=False)

        # Layout.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(6)

        # Icono (emoji grande).
        self._icono_label = QLabel(icono)
        font_icono = QFont()
        font_icono.setPointSize(36)
        font_icono.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._icono_label.setFont(font_icono)
        self._icono_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icono_label)

        # Nombre del proceso (caps + bold).
        self._nombre_label = QLabel(nombre.upper())
        font_nombre = QFont()
        font_nombre.setPointSize(13)
        font_nombre.setBold(True)
        font_nombre.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._nombre_label.setFont(font_nombre)
        self._nombre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._nombre_label.setStyleSheet(
            "color: #1A1F2C; letter-spacing: 1px;"
        )
        layout.addWidget(self._nombre_label)

        # Descripcion (recortada).
        self._desc_label = QLabel(descripcion)
        self._desc_label.setWordWrap(True)
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setStyleSheet(
            "color: #5B6473; font-size: 12px; line-height: 1.3;"
        )
        self._desc_label.setMaximumHeight(60)
        layout.addWidget(self._desc_label, 1)

        # Eventos de mouse.
        self.setMouseTracking(True)

    # -- Estilos -----------------------------------------------------

    def _actualizar_estilo(self, hover: bool, presionado: bool) -> None:
        """Pinta la tarjeta segun el estado y el tema actual."""
        from ui.recursos.tema import _paleta
        p = _paleta()
        if presionado:
            bg = p.surface_alt
            borde = self._acento
            ancho = 2
        elif hover:
            # En hover usamos un tinte derivado del acento.
            bg = p.surface_alt
            borde = self._acento
            ancho = 2
        else:
            bg = p.surface
            borde = p.border
            ancho = 1
        # Borde superior coloreado (identidad del proceso).
        self.setStyleSheet(
            f"""
            TarjetaProceso {{
                background-color: {bg};
                border: {ancho}px solid {borde};
                border-top: 4px solid {self._acento};
                border-radius: 10px;
            }}
            """
        )

    # -- Eventos de mouse --------------------------------------------

    def enterEvent(self, event) -> None:
        self._actualizar_estilo(hover=True, presionado=False)

    def leaveEvent(self, event) -> None:
        self._actualizar_estilo(hover=False, presionado=False)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._actualizar_estilo(hover=True, presionado=True)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._actualizar_estilo(hover=self.underMouse(), presionado=False)
            self.seleccionado.emit(self.nombre)

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica el estilo al cambiar de tema."""
        self._actualizar_estilo(hover=self.underMouse(), presionado=False)
        self._nombre_label.setStyleSheet(
            f"color: {paleta.fg}; letter-spacing: 1px;"
        )
        self._desc_label.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 12px; line-height: 1.3;"
        )