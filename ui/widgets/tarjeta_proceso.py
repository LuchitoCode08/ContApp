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


class TarjetaProceso(QFrame):
    """Tarjeta clickeable con icono, nombre y descripcion de un proceso."""

    seleccionado = Signal(str)  # nombre del proceso

    COLOR_FONDO = "#FFFFFF"
    COLOR_FONDO_HOVER = "#E3F2FD"
    COLOR_FONDO_PRESIONADO = "#BBDEFB"
    COLOR_BORDE = "#BDBDBD"
    COLOR_BORDE_HOVER = "#1976D2"
    COLOR_TEXTO = "#212121"
    COLOR_TEXTO_SECUNDARIO = "#616161"

    def __init__(
        self,
        nombre: str,
        descripcion: str,
        icono: str = "▶",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.nombre = nombre
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(220, 160)
        self.setMaximumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._actualizar_estilo(hover=False, presionado=False)

        # Layout.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Icono (emoji grande).
        self._icono_label = QLabel(icono)
        font_icono = QFont()
        font_icono.setPointSize(32)
        self._icono_label.setFont(font_icono)
        self._icono_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icono_label)

        # Nombre del proceso.
        self._nombre_label = QLabel(nombre)
        font_nombre = QFont()
        font_nombre.setPointSize(13)
        font_nombre.setBold(True)
        self._nombre_label.setFont(font_nombre)
        self._nombre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._nombre_label.setStyleSheet(f"color: {self.COLOR_TEXTO};")
        layout.addWidget(self._nombre_label)

        # Descripcion (recortada).
        self._desc_label = QLabel(descripcion)
        self._desc_label.setWordWrap(True)
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setStyleSheet(f"color: {self.COLOR_TEXTO_SECUNDARIO};")
        self._desc_label.setMaximumHeight(50)
        layout.addWidget(self._desc_label, 1)

        # Eventos de mouse.
        self.setMouseTracking(True)

    # -- Estilos -----------------------------------------------------

    def _actualizar_estilo(self, hover: bool, presionado: bool) -> None:
        if presionado:
            bg = self.COLOR_FONDO_PRESIONADO
            borde = self.COLOR_BORDE_HOVER
        elif hover:
            bg = self.COLOR_FONDO_HOVER
            borde = self.COLOR_BORDE_HOVER
        else:
            bg = self.COLOR_FONDO
            borde = self.COLOR_BORDE
        self.setStyleSheet(
            f"TarjetaProceso {{ background-color: {bg}; "
            f"border: 2px solid {borde}; border-radius: 8px; }}"
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