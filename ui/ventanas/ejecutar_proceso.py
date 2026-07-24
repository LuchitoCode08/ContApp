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

        # --- Header con boton "Volver" + nombre del proceso ---------
        header = QHBoxLayout()
        self.btn_volver = QPushButton("← Cambiar proceso")
        self.btn_volver.clicked.connect(self.proceso_cambiado.emit)
        header.addWidget(self.btn_volver)
        self._titulo = QLabel("")
        self._titulo.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(self._titulo)
        header.addStretch()
        layout.addLayout(header)

        # Descripcion.
        self._desc = QLabel("")
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("color: #555; padding: 4px;")
        layout.addWidget(self._desc)

        # --- DropZone -------------------------------------------------
        self.drop_zone = DropZone(
            mensaje="Arrastra el archivo aqui o haz clic en Examinar",
        )
        self.drop_zone.archivos_seleccionados.connect(self._agregar_archivos)
        layout.addWidget(self.drop_zone)

        # --- Lista de archivos ---------------------------------------
        layout.addWidget(QLabel("Archivos cargados:"))
        self.lista = QListWidget()
        self.lista.setMaximumHeight(120)
        layout.addWidget(self.lista)

        # --- Botones ------------------------------------------------
        btn_row = QHBoxLayout()
        self.btn_quitar = QPushButton("Quitar ultimo")
        self.btn_quitar.clicked.connect(self._quitar_ultimo)
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_limpiar.clicked.connect(self._limpiar_archivos)
        self.btn_ejecutar = QPushButton("Ejecutar")
        self.btn_ejecutar.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "padding: 8px 16px; font-weight: bold; }"
        )
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
        self.estado.setStyleSheet("color: #555;")
        layout.addWidget(self.estado)

        # Separador.
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # --- Tabla de resultados -------------------------------------
        layout.addWidget(QLabel("Archivos generados:"))
        self.resultados = TablaResultados()
        layout.addWidget(self.resultados, 1)

        self._actualizar_estado()

    # -- API publica -------------------------------------------------

    def configurar(self, nombre: str) -> None:
        """Configura esta vista para el proceso dado."""
        self._nombre_proceso = nombre
        cls = self._cfg.procesos[nombre]
        instancia = cls()
        icono = ICONOS.get(nombre, "▶")
        self._titulo.setText(f"{icono} {nombre}")
        self._desc.setText(
            f"<b>{nombre}</b>: {instancia.descripcion}"
        )
        self.drop_zone.set_extensiones_aceptadas(
            instancia.extensiones_entrada
        )
        self._limpiar_archivos()

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

        titulo = QLabel("¿Que proceso queres ejecutar?")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titulo)

        sub = QLabel(
            "Elegi una opcion para ver que tipo de archivo necesita."
        )
        sub.setStyleSheet("color: #555;")
        layout.addWidget(sub)

        layout.addSpacing(12)

        # Grid de tarjetas (2 columnas).
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

        nombres = self._cfg.nombres_procesos()
        columnas = 2
        for i, nombre in enumerate(nombres):
            cls = self._cfg.procesos[nombre]
            icono = ICONOS.get(nombre, "▶")
            tarjeta = TarjetaProceso(
                nombre=nombre,
                descripcion=cls().descripcion,
                icono=icono,
            )
            tarjeta.seleccionado.connect(self.proceso_seleccionado.emit)
            fila = i // columnas
            col = i % columnas
            grid.addWidget(tarjeta, fila, col)
            grid.setColumnStretch(col, 1)

        # Si hay menos de `columnas * filas` tarjetas, centramos.
        if len(nombres) < columnas:
            grid.setColumnStretch(columnas, 1)

        layout.addWidget(grid_container)
        layout.addStretch()

        # Pie: cantidad de procesos.
        pie = QLabel(f"{len(nombres)} procesos disponibles.")
        pie.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(pie)


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