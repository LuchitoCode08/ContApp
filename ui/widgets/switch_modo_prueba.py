"""Switch visual para activar/desactivar el modo prueba.

Usa un QCheckBox con stylesheet custom (no la libreria nativa fea).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class SwitchModoPrueba(QWidget):
    """Toggle visual que activa/desactiva el modo prueba global.

    Emite ``modo_prueba_cambiado(bool)`` cuando el usuario cambia el estado.
    """

    modo_prueba_cambiado = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._label = QLabel("Modo prueba")
        self._label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self._label)

        self._checkbox = QCheckBox()
        self._checkbox.setObjectName("switch")
        self._checkbox.setToolTip(
            "Cuando está activo, los resultados se guardan en una carpeta "
            "temporal y los originales NO se tocan."
        )
        self._checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checkbox.stateChanged.connect(self._on_change)
        layout.addWidget(self._checkbox)

        self._estado = QLabel("OFF")
        self._estado.setStyleSheet(
            "color: #5B6473; font-size: 11px; font-weight: 600;"
            " min-width: 28px;"
        )
        layout.addWidget(self._estado)

        self._aplicar_estilo_switch(activo=False)

    def _on_change(self, state: int) -> None:
        activo = state == Qt.CheckState.Checked.value
        self._aplicar_estilo_switch(activo)
        self._estado.setText("ON" if activo else "OFF")
        self._estado.setStyleSheet(
            f"color: {'#16A34A' if activo else '#5B6473'}; "
            "font-size: 11px; font-weight: 600; min-width: 28px;"
        )
        self.modo_prueba_cambiado.emit(activo)

    def _aplicar_estilo_switch(self, activo: bool) -> None:
        """Pinta el checkbox como un switch deslizante."""
        bg = "#16A34A" if activo else "#A8AEBA"
        self._checkbox.setStyleSheet(
            f"""
            QCheckBox#switch {{
                background-color: {bg};
                border-radius: 14px;
                min-width: 44px;
                max-width: 44px;
                min-height: 26px;
                max-height: 26px;
            }}
            QCheckBox#switch::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                background-color: white;
                margin: 3px;
            }}
            QCheckBox#switch::indicator:unchecked {{
                subcontrol-position: left center;
            }}
            QCheckBox#switch::indicator:checked {{
                subcontrol-position: right center;
            }}
            """
        )

    def esta_activo(self) -> bool:
        return self._checkbox.isChecked()

    def set_activo(self, activo: bool) -> None:
        self._checkbox.setChecked(activo)

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica colores del label y del indicador ON/OFF."""
        self._label.setStyleSheet(
            f"color: {paleta.fg}; font-size: 12px;"
        )
        activo = self.esta_activo()
        self._estado.setStyleSheet(
            f"color: {'#16A34A' if activo else paleta.fg_muted}; "
            "font-size: 11px; font-weight: 600; min-width: 28px;"
        )
        # El switch en si no cambia (verde/blanco universales).