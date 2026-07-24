"""Zona de drag & drop para archivos."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DropZone(QFrame):
    """Zona donde el usuario arrastra archivos o los selecciona con boton.

    Extensiones aceptadas: configurable (``extensiones_aceptadas``).

    Emite ``archivos_seleccionados(list[Path])`` cuando se agregan archivos.
    """

    archivos_seleccionados = Signal(list)

    def __init__(
        self,
        extensiones_aceptadas: tuple[str, ...] = (),
        mensaje: str = "Arrastra archivos aqui o haz clic para seleccionar",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.extensiones_aceptadas = tuple(
            e.lower() for e in extensiones_aceptadas
        )
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(120)
        self._actualizar_estilo(normal=True)

        # Etiqueta principal.
        self._label = QLabel(mensaje)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)

        # Boton examinar.
        self._boton = QPushButton("Examinar...")
        self._boton.clicked.connect(self._abrir_dialogo)

        layout = QVBoxLayout(self)
        layout.addWidget(self._label)
        layout_row = QHBoxLayout()
        layout_row.addStretch()
        layout_row.addWidget(self._boton)
        layout_row.addStretch()
        layout.addLayout(layout_row)

    def set_extensiones_aceptadas(self, extensiones: tuple[str, ...]) -> None:
        """Actualiza las extensiones aceptadas."""
        self.extensiones_aceptadas = tuple(
            e.lower() for e in extensiones
        )

    def set_mensaje(self, mensaje: str) -> None:
        """Cambia el mensaje central."""
        self._label.setText(mensaje)

    # -- Drag & drop --------------------------------------------------

    def _actualizar_estilo(self, normal: bool) -> None:
        if normal:
            self.setStyleSheet(
                "DropZone { background-color: #F5F5F5; border: 2px dashed #BDBDBD; }"
                "DropZone:hover { border: 2px dashed #1976D2; }"
            )
        else:
            self.setStyleSheet(
                "DropZone { background-color: #E3F2FD; border: 2px solid #1976D2; }"
            )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._actualizar_estilo(normal=False)

    def dragLeaveEvent(self, event) -> None:
        self._actualizar_estilo(normal=True)

    def dropEvent(self, event: QDropEvent) -> None:
        self._actualizar_estilo(normal=True)
        urls = event.mimeData().urls()
        archivos = []
        for url in urls:
            if url.isLocalFile():
                archivos.append(Path(url.toLocalFile()))
        if archivos:
            self._emitir(archivos)

    # -- Boton examinar -----------------------------------------------

    def _abrir_dialogo(self) -> None:
        filtro = self._filtro_dialogo()
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar archivos",
            str(Path.home() / "Downloads"),
            filtro,
        )
        if paths:
            self._emitir([Path(p) for p in paths])

    def _filtro_dialogo(self) -> str:
        if not self.extensiones_aceptadas:
            return "Todos los archivos (*)"
        exts = " ".join(f"*{e}" for e in self.extensiones_aceptadas)
        return f"Archivos ({exts}) ({exts})"

    # -- Emision ------------------------------------------------------

    def _emitir(self, archivos: list[Path]) -> None:
        # Filtrar por extension si corresponde.
        if self.extensiones_aceptadas:
            archivos = [
                a for a in archivos
                if a.suffix.lower() in self.extensiones_aceptadas
            ]
        if archivos:
            self.archivos_seleccionados.emit(archivos)