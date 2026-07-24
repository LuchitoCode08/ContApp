"""Banner de modo (siempre visible, cambia color segun estado).

Cuando ``activo=True`` se muestra naranja con texto de advertencia.
Cuando ``activo=False`` se muestra verde con texto indicando modo produccion.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget


class BannerModoPrueba(QLabel):
    """Banner que indica el modo actual (siempre visible)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(36)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.setFont(font)
        # Default: modo prueba activo (la app arranca asi por seguridad).
        self.set_activo(True)

    def set_activo(self, activo: bool) -> None:
        """Cambia el texto y color del banner segun el modo."""
        if activo:
            self.setText("MODO PRUEBA  -  Los cambios no se guardaran en produccion")
            self.setStyleSheet(
                "background-color: #FF9800;"
                "color: white;"
                "padding: 4px;"
            )
        else:
            self.setText("MODO PRODUCCION  -  Los cambios se guardaran en archivos reales")
            self.setStyleSheet(
                "background-color: #4CAF50;"
                "color: white;"
                "padding: 4px;"
            )

    def set_visible(self, visible: bool) -> None:
        """Compatibilidad con la API anterior: delega en set_activo."""
        self.set_activo(visible)