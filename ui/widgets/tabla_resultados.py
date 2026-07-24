"""Tabla generica para mostrar resultados (clave/valor, pares, archivos).

Modos:
- ``clave_valor``: 2 columnas (Clave | Valor)
- ``pares``: 2 columnas (Patron | Reemplazo)
- ``archivos``: 1 columna (Archivo generado)
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class TablaResultados(QWidget):
    """Tabla que muestra los resultados de una operacion."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tabla = QTableWidget()
        self._tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabla.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabla)

    # -- API publica --------------------------------------------------

    def mostrar_archivos(self, archivos: list[Path]) -> None:
        """Muestra una lista de archivos generados."""
        self._tabla.setColumnCount(1)
        self._tabla.setHorizontalHeaderLabels(["Archivo"])
        self._tabla.setRowCount(len(archivos))
        for i, p in enumerate(archivos):
            item = QTableWidgetItem(f"{p.name}  ({p.stat().st_size:,} bytes)")
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self._tabla.setItem(i, 0, item)

    def mostrar_clave_valor(self, datos: dict) -> None:
        """Muestra un diccionario como tabla clave/valor."""
        self._tabla.setColumnCount(2)
        self._tabla.setHorizontalHeaderLabels(["Clave", "Valor"])
        self._tabla.setRowCount(len(datos))
        for i, (k, v) in enumerate(datos.items()):
            self._tabla.setItem(i, 0, QTableWidgetItem(str(k)))
            self._tabla.setItem(i, 1, QTableWidgetItem(str(v)))

    def mostrar_pares(self, pares: list[tuple]) -> None:
        """Muestra una lista de tuplas (patron, reemplazo)."""
        self._tabla.setColumnCount(2)
        self._tabla.setHorizontalHeaderLabels(["Patron", "Reemplazo"])
        self._tabla.setRowCount(len(pares))
        for i, (a, b) in enumerate(pares):
            self._tabla.setItem(i, 0, QTableWidgetItem(str(a)))
            self._tabla.setItem(i, 1, QTableWidgetItem(str(b)))

    def limpiar(self) -> None:
        """Limpia la tabla."""
        self._tabla.setRowCount(0)