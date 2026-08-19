"""Zona de carga de archivos (DropZone) con lista interactiva y eliminación individual."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.item_archivo import ItemArchivo


class DropZone(QFrame):
    """Contenedor de archivos con soporte Drag & Drop y lista con botón de eliminar por ítem."""

    archivos_cambiados = Signal(list)

    def __init__(
        self,
        extensiones_aceptadas: tuple[str, ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.extensiones_aceptadas = tuple(e.lower() for e in extensiones_aceptadas)
        self._permitir_multiple = True
        self._archivos: list[Path] = []

        self.setAcceptDrops(True)
        self.setObjectName("DropZoneBox")
        self.setFixedHeight(140)

        self._construir_ui()
        self._actualizar_estado()

    def _construir_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(1, 1, 1, 1)
        layout_principal.setSpacing(0)

        self._stack = QStackedWidget()

        # Vista 0: Vacía (Placeholder de Drag & Drop)
        self._vista_vacia = QWidget()
        layout_vacia = QVBoxLayout(self._vista_vacia)
        layout_vacia.setContentsMargins(24, 28, 24, 28)
        layout_vacia.setSpacing(10)
        layout_vacia.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl_icono = QLabel("📁")
        self._lbl_icono.setStyleSheet("font-size: 38px; background: transparent;")
        self._lbl_icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_vacia.addWidget(self._lbl_icono)

        self._lbl_mensaje = QLabel("Arrastra tus archivos aquí o haz clic en Examinar")
        self._lbl_mensaje.setStyleSheet("font-weight: 600; font-size: 14px; color: #1E293B; background: transparent;")
        self._lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_vacia.addWidget(self._lbl_mensaje)

        self._lbl_hint = QLabel("Formatos permitidos")
        self._lbl_hint.setStyleSheet("font-size: 12px; color: #64748B; background: transparent;")
        self._lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_vacia.addWidget(self._lbl_hint)

        self._stack.addWidget(self._vista_vacia)

        # Vista 1: Lista de archivos cargados
        self._vista_lista = QWidget()
        layout_lista = QVBoxLayout(self._vista_lista)
        layout_lista.setContentsMargins(8, 8, 8, 8)
        layout_lista.setSpacing(6)

        self._list_widget = QListWidget()
        self._list_widget.setObjectName("archivos_list")
        self._list_widget.setStyleSheet(
            """
            QListWidget#archivos_list {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget#archivos_list::item {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                margin-bottom: 6px;
            }
            QListWidget#archivos_list::item:hover {
                border-color: #93C5FD;
                background-color: #F8FAFC;
            }
            """
        )
        layout_lista.addWidget(self._list_widget)

        self._stack.addWidget(self._vista_lista)
        layout_principal.addWidget(self._stack)

        self._aplicar_borde(activo=False)

    def set_extensiones_aceptadas(self, extensiones: tuple[str, ...]) -> None:
        self.extensiones_aceptadas = tuple(e.lower() for e in extensiones)
        exts_str = ", ".join(self.extensiones_aceptadas)
        self._lbl_hint.setText(f"Formatos aceptados: {exts_str}")

    def set_permitir_multiple(self, permitir: bool) -> None:
        self._permitir_multiple = permitir

    def agregar_archivos(self, rutas: list[Path]) -> None:
        nuevos = []
        for r in rutas:
            p = Path(r)
            if self.extensiones_aceptadas and p.suffix.lower() not in self.extensiones_aceptadas:
                continue
            if not self._permitir_multiple:
                self._archivos = [p]
                break
            if p not in self._archivos:
                self._archivos.append(p)
                nuevos.append(p)

        self._refrescar_lista()
        self.archivos_cambiados.emit(self._archivos)

    def eliminar_archivo(self, ruta: Path) -> None:
        if ruta in self._archivos:
            self._archivos.remove(ruta)
            self._refrescar_lista()
            self.archivos_cambiados.emit(self._archivos)

    def vaciar(self) -> None:
        self._archivos.clear()
        self._refrescar_lista()
        self.archivos_cambiados.emit(self._archivos)

    def obtener_archivos(self) -> list[Path]:
        return list(self._archivos)

    def _refrescar_lista(self) -> None:
        self._list_widget.clear()
        for ruta in self._archivos:
            item = QListWidgetItem(self._list_widget)
            item_widget = ItemArchivo(ruta)
            item_widget.eliminar_solicitado.connect(self.eliminar_archivo)
            item.setSizeHint(item_widget.sizeHint())
            self._list_widget.addItem(item)
            self._list_widget.setItemWidget(item, item_widget)

        self._actualizar_estado()

    def _actualizar_estado(self) -> None:
        if self._archivos:
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)

    def _aplicar_borde(self, activo: bool) -> None:
        borde = "2px dashed #2563EB" if activo else "1px solid #CBD5E1"
        bg = "#EFF6FF" if activo else "#FFFFFF"
        self.setStyleSheet(
            f"""
            QFrame#DropZoneBox {{
                background-color: {bg};
                border: {borde};
                border-radius: 10px;
            }}
            """
        )

    # --- Drag & Drop ---

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._aplicar_borde(activo=True)

    def dragLeaveEvent(self, event) -> None:
        self._aplicar_borde(activo=False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._aplicar_borde(activo=False)
        urls = event.mimeData().urls()
        archivos = []
        for url in urls:
            if url.isLocalFile():
                archivos.append(Path(url.toLocalFile()))
        if archivos:
            self.agregar_archivos(archivos)

    # --- Diálogo de Archivos ---

    def abrir_dialogo_examinar(self) -> None:
        exts = " ".join(f"*{e}" for e in self.extensiones_aceptadas) if self.extensiones_aceptadas else "*.*"
        filtro = f"Archivos ({exts})" if self.extensiones_aceptadas else "Todos los archivos (*.*)"

        if self._permitir_multiple:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Seleccionar archivos", str(Path.home() / "Downloads"), filtro,
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar archivo", str(Path.home() / "Downloads"), filtro,
            )
            paths = [path] if path else []

        if paths:
            self.agregar_archivos([Path(p) for p in paths])