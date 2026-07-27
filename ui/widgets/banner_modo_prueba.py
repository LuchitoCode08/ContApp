"""Banner siempre visible arriba de la app: indica modo (prueba/produccion)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget


class BannerModoPrueba(QLabel):
    """Banner con icono + texto del modo activo. Siempre visible."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(40)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.setFont(font)
        self.set_activo(False)

    def set_activo(self, activo: bool) -> None:
        """Cambia icono + texto + color segun el modo."""
        self._activo = activo
        if activo:
            self.setText("⚠  MODO PRUEBA   ·   Los cambios no se guardan en producción")
            self.setStyleSheet(
                "background-color: #F59E0B;"
                "color: #1A1F2C;"
                "padding: 0 16px;"
                "border: none;"
            )
        else:
            self.setText("●  MODO PRODUCCIÓN   ·   Los cambios se guardan en archivos reales")
            self.setStyleSheet(
                "background-color: #16A34A;"
                "color: #FFFFFF;"
                "padding: 0 16px;"
                "border: none;"
            )

    def set_visible(self, visible: bool) -> None:  # noqa: D401  # compat
        """Compatibilidad con API anterior."""
        self.set_activo(visible)

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica colores al cambiar de tema (los del banner no dependen del tema)."""
        self.set_activo(self._activo)