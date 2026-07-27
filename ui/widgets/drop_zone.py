"""Zona de drag & drop para archivos."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont
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
        self.setObjectName("DropZone")
        self.setMinimumHeight(140)
        self._actualizar_estilo(activo=False)

        # Icono grande + etiqueta principal + sub-texto + boton.
        self._icono = QLabel("⤓")
        font_icono = QFont()
        font_icono.setPointSize(40)
        font_icono.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._icono.setFont(font_icono)
        self._icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icono.setStyleSheet("color: #5B6473; background: transparent;")

        self._label = QLabel(mensaje)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            "color: #1A1F2C; font-size: 13px; font-weight: 500;"
            " background: transparent;"
        )

        self._sub = QLabel("o usa el botón para explorar")
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setStyleSheet(
            "color: #5B6473; font-size: 11px; background: transparent;"
        )

        self._boton = QPushButton("Examinar archivos...")
        self._boton.setObjectName("primary")
        self._boton.setCursor(Qt.CursorShape.PointingHandCursor)
        self._boton.clicked.connect(self._abrir_dialogo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)
        layout.addWidget(self._icono)
        layout.addWidget(self._label)
        layout.addWidget(self._sub)
        layout.addSpacing(6)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._boton)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def set_extensiones_aceptadas(self, extensiones: tuple[str, ...]) -> None:
        """Actualiza las extensiones aceptadas."""
        self.extensiones_aceptadas = tuple(
            e.lower() for e in extensiones
        )

    def set_mensaje(self, mensaje: str) -> None:
        """Cambia el mensaje central."""
        self._label.setText(mensaje)

    # -- Drag & drop --------------------------------------------------

    def _actualizar_estilo(self, activo: bool) -> None:
        """Cambia el estilo segun haya drag activo encima o no."""
        from ui.recursos.tema import _paleta
        p = _paleta()
        if activo:
            self.setStyleSheet(
                f"""
                DropZone {{
                    background-color: {p.surface_alt};
                    border: 2px dashed {p.primary};
                    border-radius: 12px;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                DropZone {{
                    background-color: {p.surface};
                    border: 2px dashed {p.border};
                    border-radius: 12px;
                }}
                DropZone:hover {{
                    background-color: {p.surface_alt};
                    border-color: {p.primary};
                }}
                """
            )

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica el fondo de la zona y los textos."""
        self._actualizar_estilo(activo=False)
        self._icono.setStyleSheet(
            f"color: {paleta.fg_muted}; background: transparent;"
        )
        self._label.setStyleSheet(
            f"color: {paleta.fg}; font-size: 13px; font-weight: 500;"
            " background: transparent;"
        )
        self._sub.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 11px;"
            " background: transparent;"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._actualizar_estilo(activo=True)

    def dragLeaveEvent(self, event) -> None:
        self._actualizar_estilo(activo=False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._actualizar_estilo(activo=False)
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