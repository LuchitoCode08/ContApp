"""Widget para cada elemento de archivo en la lista de ejecución con botón de eliminar individual."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


def _formatear_tamano(tamano_bytes: int) -> str:
    """Convierte bytes a formato legible (KB, MB)."""
    if tamano_bytes < 1024:
        return f"{tamano_bytes} B"
    elif tamano_bytes < 1024 * 1024:
        return f"{tamano_bytes / 1024:.1f} KB"
    else:
        return f"{tamano_bytes / (1024 * 1024):.2f} MB"


class ItemArchivo(QWidget):
    """Fila de archivo con nombre, tamaño y botón de eliminar individual."""

    eliminar_solicitado = Signal(Path)

    def __init__(self, ruta: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ruta = Path(ruta)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Icono según extensión
        ext = self.ruta.suffix.lower()
        icono_texto = "📦" if ext == ".zip" else ("📊" if ext in (".xlsx", ".xls") else "📄")
        lbl_icono = QLabel(icono_texto)
        lbl_icono.setStyleSheet("font-size: 16px; background: transparent;")
        layout.addWidget(lbl_icono)

        # Nombre del archivo
        lbl_nombre = QLabel(self.ruta.name)
        lbl_nombre.setStyleSheet("font-weight: 600; font-size: 13px; color: #0F172A; background: transparent;")
        layout.addWidget(lbl_nombre)

        layout.addStretch(1)

        # Tamaño del archivo
        try:
            tamano_str = _formatear_tamano(self.ruta.stat().st_size)
        except OSError:
            tamano_str = ""

        lbl_tamano = QLabel(tamano_str)
        lbl_tamano.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        layout.addWidget(lbl_tamano)

        # Botón individual de eliminar (✕)
        self._btn_eliminar = QPushButton("✕")
        self._btn_eliminar.setToolTip(f"Quitar '{self.ruta.name}' de la lista")
        self._btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_eliminar.setFixedSize(26, 26)
        self._btn_eliminar.setStyleSheet(
            """
            QPushButton {
                background-color: #F1F5F9;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 13px;
                font-weight: bold;
                font-size: 12px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: #FFFFFF;
                border-color: #DC2626;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
            """
        )
        self._btn_eliminar.clicked.connect(lambda: self.eliminar_solicitado.emit(self.ruta))
        layout.addWidget(self._btn_eliminar)
