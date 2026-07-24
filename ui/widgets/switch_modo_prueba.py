"""Switch (toggle) para activar/desactivar el modo prueba."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class SwitchModoPrueba(QWidget):
    """Toggle que activa/desactiva el modo prueba global.

    Emite ``modo_prueba_cambiado(bool)`` cuando el usuario cambia el estado.
    """

    modo_prueba_cambiado = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checkbox = QCheckBox("Modo prueba")
        self._checkbox.setToolTip(
            "Cuando esta activo, los resultados se guardan en una carpeta "
            "temporal y los originales NO se tocan."
        )
        self._checkbox.stateChanged.connect(self._on_change)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._checkbox)

    def _on_change(self, state: int) -> None:
        activo = state == Qt.CheckState.Checked.value
        self.modo_prueba_cambiado.emit(activo)

    def esta_activo(self) -> bool:
        return self._checkbox.isChecked()

    def set_activo(self, activo: bool) -> None:
        self._checkbox.setChecked(activo)