"""Pantalla Procesos: ejecutar cualquiera de los 3 procesos desde la UI.

Flujo:
    1. Vista GRID: muestra tarjetas con los procesos disponibles.
       El usuario hace click en una tarjeta para elegir.
    2. Vista EJECUCION: aparece el DropZone + lista + ejecutar +
       resultados, todo para el proceso elegido.
       Boton "Volver" regresa al grid.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import get_config
from procesos.base import ProcesoBase, ResultadoProceso
from ui.widgets.drop_zone import DropZone
from ui.widgets.tabla_resultados import TablaResultados
from ui.widgets.tarjeta_proceso import TarjetaProceso
from utils.bitacora import log


# Iconos por proceso (emojis simples).
ICONOS: dict[str, str] = {
    "comprobante": "📋",
    "fierro": "🔥",
    "zeus": "⚡",
}


class WorkerEjecucion(QThread):
    """Hilo que ejecuta un proceso sin bloquear la UI."""

    terminado = Signal(object)  # ResultadoProceso
    error = Signal(str)

    def __init__(
        self,
        proceso: ProcesoBase,
        archivos: list[Path],
        modo_prueba: bool,
    ) -> None:
        super().__init__()
        self.proceso = proceso
        self.archivos = archivos
        self.modo_prueba = modo_prueba

    def run(self) -> None:
        try:
            resultado = self.proceso.ejecutar(
                self.archivos, modo_prueba=self.modo_prueba,
            )
            self.terminado.emit(resultado)
        except Exception as e:
            log().exception("Error en worker: %s", e)
            self.error.emit(str(e))


class VistaEjecucion(QWidget):
    """Sub-vista que muestra el DropZone + ejecutar para UN proceso."""

    proceso_cambiado = Signal()  # para volver al grid

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = get_config()
        self._archivos: list[Path] = []
        self._worker: WorkerEjecucion | None = None
        self._nombre_proceso: str = ""
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # --- Header con boton "Volver" + nombre del proceso ---------
        self.btn_volver = QPushButton("←  Procesos")
        self.btn_volver.setObjectName("ghost")
        self.btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver.clicked.connect(self.proceso_cambiado.emit)
        layout.addWidget(self.btn_volver)

        titulo_row = QHBoxLayout()
        self._icono_label = QLabel("▶")
        self._icono_label.setStyleSheet(
            "font-size: 32px; background: transparent;"
        )
        titulo_row.addWidget(self._icono_label)
        self._titulo = QLabel("")
        self._titulo.setStyleSheet(
            "font-size: 22px; font-weight: 700; padding-left: 8px;"
        )
        titulo_row.addWidget(self._titulo)
        titulo_row.addStretch()
        layout.addLayout(titulo_row)

        # Descripcion.
        self._desc = QLabel("")
        self._desc.setWordWrap(True)
        layout.addWidget(self._desc)

        # --- DropZone -------------------------------------------------
        self.drop_zone = DropZone(
            mensaje="Arrastra el archivo aquí o haz clic en Examinar",
        )
        self.drop_zone.archivos_seleccionados.connect(self._agregar_archivos)
        layout.addWidget(self.drop_zone)

        # --- Lista de archivos ---------------------------------------
        self._lbl_archivos = QLabel("ARCHIVOS CARGADOS")
        layout.addWidget(self._lbl_archivos)
        self.lista = QListWidget()
        self.lista.setMaximumHeight(120)
        layout.addWidget(self.lista)

        # --- Botones ------------------------------------------------
        btn_row = QHBoxLayout()
        self.btn_quitar = QPushButton("Quitar último")
        self.btn_quitar.clicked.connect(self._quitar_ultimo)
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_limpiar.clicked.connect(self._limpiar_archivos)
        self.btn_ejecutar = QPushButton("▶  Ejecutar proceso")
        self.btn_ejecutar.setObjectName("primary")
        self.btn_ejecutar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ejecutar.clicked.connect(self._ejecutar)
        btn_row.addWidget(self.btn_quitar)
        btn_row.addWidget(self.btn_limpiar)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_ejecutar)
        layout.addLayout(btn_row)

        # --- Progreso / estado --------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.estado = QLabel("")
        layout.addWidget(self.estado)

        # Separador.
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # --- Tabla de resultados -------------------------------------
        self._lbl_result = QLabel("ARCHIVOS GENERADOS")
        layout.addWidget(self._lbl_result)
        self.resultados = TablaResultados()
        layout.addWidget(self.resultados, 1)

        self._actualizar_estado()
        self._aplicar_tema(self._tema_actual())  # aplica colores iniciales

    def _tema_actual(self):
        from ui.recursos.tema import _paleta
        return _paleta()

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica estilos al cambiar de tema."""
        self._desc.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 13px; line-height: 1.4;"
        )
        self._lbl_archivos.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 11px; font-weight: 700;"
            " letter-spacing: 1.5px; margin-top: 4px;"
        )
        self.lista.setStyleSheet(
            f"QListWidget {{ background-color: {paleta.surface};"
            f" border: 1px solid {paleta.border}; border-radius: 8px; }}"
        )
        self.estado.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 12px;"
        )
        self.sep.setStyleSheet(
            f"color: {paleta.border}; background: {paleta.border};"
        )
        self._lbl_result.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 11px; font-weight: 700;"
            " letter-spacing: 1.5px;"
        )
        # Si hay un proceso configurado, reaplicar el acento del titulo.
        if self._nombre_proceso:
            from ui.recursos.tema import color_proceso
            self._titulo.setStyleSheet(
                f"font-size: 22px; font-weight: 700; padding-left: 8px;"
                f" color: {color_proceso(self._nombre_proceso)};"
            )
        else:
            self._titulo.setStyleSheet(
                f"font-size: 22px; font-weight: 700; padding-left: 8px;"
                f" color: {paleta.fg};"
            )

    # -- API publica -------------------------------------------------

    def configurar(self, nombre: str) -> None:
        """Configura esta vista para el proceso dado."""
        self._nombre_proceso = nombre
        cls = self._cfg.procesos[nombre]
        instancia = cls()
        icono = ICONOS.get(nombre, "▶")
        self._icono_label.setText(icono)
        self._titulo.setText(nombre.upper())
        self._desc.setText(instancia.descripcion)
        self.drop_zone.set_extensiones_aceptadas(
            instancia.extensiones_entrada
        )
        self._limpiar_archivos()
        # Reaplicar tema con el nuevo proceso (para acento).
        self._aplicar_tema(self._tema_actual())

    # -- Manejo de archivos -----------------------------------------

    def _agregar_archivos(self, archivos: list[Path]) -> None:
        cls = self._cfg.procesos[self._nombre_proceso]
        instancia = cls()
        error = instancia.validar_archivos(archivos)
        if error:
            QMessageBox.warning(self, "Archivos invalidos", error)
            return
        for a in archivos:
            if a not in self._archivos:
                self._archivos.append(a)
                item = QListWidgetItem(str(a))
                item.setData(Qt.ItemDataRole.UserRole, str(a))
                self.lista.addItem(item)
        self._actualizar_estado()

    def _quitar_ultimo(self) -> None:
        if self._archivos:
            self._archivos.pop()
            self.lista.takeItem(self.lista.count() - 1)
            self._actualizar_estado()

    def _limpiar_archivos(self) -> None:
        self._archivos.clear()
        self.lista.clear()
        self.resultados.limpiar()
        self._actualizar_estado()

    def _actualizar_estado(self) -> None:
        n = len(self._archivos)
        self.btn_ejecutar.setEnabled(n > 0)
        self.estado.setText(
            f"{n} archivo(s) listo(s) para procesar."
            if n else "Arrastra archivos para empezar."
        )

    # -- Ejecucion ---------------------------------------------------

    def _ejecutar(self) -> None:
        if not self._archivos:
            QMessageBox.information(
                self, "Sin archivos", "Agrega al menos un archivo."
            )
            return
        if self._worker is not None and self._worker.isRunning():
            return

        cls = self._cfg.procesos[self._nombre_proceso]
        proceso = cls()

        error = proceso.validar_archivos(self._archivos)
        if error:
            QMessageBox.warning(self, "Archivos invalidos", error)
            return

        self.btn_ejecutar.setEnabled(False)
        self.progress.show()
        self.estado.setText(f"Ejecutando {self._nombre_proceso}...")

        self._worker = WorkerEjecucion(
            proceso, list(self._archivos), self._cfg.modo_prueba,
        )
        self._worker.terminado.connect(self._on_terminado)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_terminado(self, resultado: ResultadoProceso) -> None:
        self.progress.hide()
        self.btn_ejecutar.setEnabled(True)

        if resultado.exito:
            archivos = resultado.archivos_salida
            self.resultados.mostrar_archivos(archivos)
            self.estado.setText(
                f"[OK] {len(archivos)} archivo(s) generado(s)."
            )
            QMessageBox.information(
                self,
                "Proceso completado",
                f"Se generaron {len(archivos)} archivo(s).\n\n"
                + "\n".join(str(p) for p in archivos),
            )
        else:
            self.estado.setText(f"[FAIL] {resultado.mensaje}")
            QMessageBox.critical(
                self, "Error", f"El proceso fallo:\n{resultado.mensaje}"
            )

    def _on_error(self, msg: str) -> None:
        self.progress.hide()
        self.btn_ejecutar.setEnabled(True)
        self.estado.setText(f"[ERROR] {msg}")
        QMessageBox.critical(self, "Error inesperado", msg)


class VistaGridProcesos(QWidget):
    """Sub-vista que muestra tarjetas con los procesos disponibles."""

    proceso_seleccionado = Signal(str)  # nombre del proceso

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = get_config()
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        self._titulo = QLabel("¿Qué proceso querés ejecutar?")
        self._titulo.setStyleSheet(
            "font-size: 22px; font-weight: 700; padding-bottom: 4px;"
        )
        layout.addWidget(self._titulo)

        self._sub = QLabel(
            "Elegí una opción para ver qué tipo de archivo necesita."
        )
        self._sub.setWordWrap(True)
        layout.addWidget(self._sub)

        # Grid de tarjetas (2 columnas).
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(0, 12, 0, 0)
        grid.setSpacing(18)

        nombres = self._cfg.nombres_procesos()
        self._columnas = 2
        for i, nombre in enumerate(nombres):
            cls = self._cfg.procesos[nombre]
            icono = ICONOS.get(nombre, "▶")
            tarjeta = TarjetaProceso(
                nombre=nombre,
                descripcion=cls().descripcion,
                icono=icono,
                en_desarrollo=getattr(cls, "EN_DESARROLLO", False),
            )
            tarjeta.seleccionado.connect(self.proceso_seleccionado.emit)
            fila = i // self._columnas
            col = i % self._columnas
            grid.addWidget(tarjeta, fila, col)
            grid.setColumnStretch(col, 1)

        # Si hay menos de `columnas * filas` tarjetas, centramos.
        if len(nombres) < self._columnas:
            grid.setColumnStretch(self._columnas, 1)

        layout.addWidget(grid_container)
        layout.addStretch()

        # Pie: cantidad de procesos.
        self._pie = QLabel(f"  {len(nombres)} procesos disponibles")
        layout.addWidget(self._pie)
        self._aplicar_tema(self._tema_actual())

    def _tema_actual(self):
        from ui.recursos.tema import _paleta
        return _paleta()

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica estilos al cambiar de tema."""
        self._sub.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 13px;"
        )
        self._pie.setStyleSheet(
            f"color: {paleta.fg_muted}; font-size: 11px; padding: 8px 0;"
        )


class PantallaProcesos(QWidget):
    """Pantalla principal de Procesos con flujo de 2 vistas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = get_config()

        # Grid de seleccion.
        self.vista_grid = VistaGridProcesos()
        self.vista_grid.proceso_seleccionado.connect(self._ir_a_ejecucion)

        # Vista de ejecucion (siempre existe, se reconfigura al cambiar).
        self.vista_ejecucion = VistaEjecucion()
        self.vista_ejecucion.proceso_cambiado.connect(self._ir_a_grid)

        # Stack que alterna entre las dos vistas.
        self.stack = QStackedWidget()
        self.stack.addWidget(self.vista_grid)   # index 0
        self.stack.addWidget(self.vista_ejecucion)  # index 1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def _ir_a_ejecucion(self, nombre: str) -> None:
        self.vista_ejecucion.configurar(nombre)
        self.stack.setCurrentIndex(1)

    def _ir_a_grid(self) -> None:
        self.stack.setCurrentIndex(0)

    # -- API publica -------------------------------------------------

    def seleccionar_proceso(self, nombre: str) -> None:
        """Salta directo a la vista de ejecucion con un proceso pre-cargado.

        Pensado para que la Pantalla Inicio pueda navegar aca cuando el
        usuario hace click en una tarjeta del dashboard.
        """
        if nombre not in self._cfg.procesos:
            return
        self._ir_a_ejecucion(nombre)