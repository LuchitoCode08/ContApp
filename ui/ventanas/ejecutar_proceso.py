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
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import get_config
from procesos.base import ProcesoBase, ProcesoCancelado, ResultadoProceso
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
    """Hilo que ejecuta un proceso sin bloquear la UI.

    Robustez:
        - Captura BaseException (no solo Exception) para que la app nunca
          se cierre por un error inesperado en el worker.
        - Loggea con traceback completo antes de emitir la senal ``error``.
        - Si el usuario pidio ``cancelar()`` (vuelve False en ``isRunning``)
          se aborta el QThread antes de empezar.

    Signals:
        terminado: emite ``ResultadoProceso`` al terminar OK.
        error: emite un mensaje de error al fallar.
        progreso: emite el porcentaje (0..100) en cada avance.
    """

    terminado = Signal(object)  # ResultadoProceso
    error = Signal(str)
    progreso = Signal(int)       # 0..100

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
        self._cancelado = False
        # Dedup del signal progreso: solo emitimos si el pct cambia.
        self._ultimo_pct = -1

    def cancelar(self) -> None:
        """Marca el worker como cancelado. El run() lo chequea al inicio."""
        self._cancelado = True

    def _emit_progreso_cb(self, actual: int, total: int) -> None:
        """Callback que el worker pasa al proceso como ``progreso``.

        Convierte ``(actual, total)`` a un porcentaje 0..100 y emite
        ``self.progreso(pct)`` solo si cambio (dedup). El proceso
        recibe siempre la misma funcion; el worker decide si emitir
        segun el flag ``_ultimo_pct``.
        """
        if total <= 0:
            return
        pct = int(actual * 100 / total)
        if pct < 0:
            pct = 0
        elif pct > 100:
            pct = 100
        if pct == self._ultimo_pct:
            return
        self._ultimo_pct = pct
        try:
            self.progreso.emit(pct)
        except Exception as e:  # noqa: BLE001
            log().warning(
                "%s fallo emitiendo progreso (%d%%): %s",
                self.proceso.LOG_PREFIX, pct, e,
            )

    def run(self) -> None:
        if self._cancelado:
            self.error.emit("Ejecucion cancelada antes de iniciar")
            return
        try:
            # NO emitimos progreso(0) explicito aca: la barra empieza
            # en 0% por defecto y se actualiza cuando el proceso reporta
            # su primer avance via ``_emit_progreso_cb``. Emitir 0%
            # manualmente puede causar race conditions con Qt en Windows.
            resultado = self.proceso.ejecutar(
                self.archivos,
                modo_prueba=self.modo_prueba,
                progreso=self._emit_progreso_cb,
                cancelado=lambda: self._cancelado,
            )
            if self._cancelado:
                # El proceso termino pero el usuario ya pidio cancelar.
                return
            self.terminado.emit(resultado)
        except ProcesoCancelado:
            # El proceso aborto cooperativamente. Log info + signal error
            # (la UI muestra un mensaje amigable).
            log().info(
                "%s Ejecucion cancelada por el usuario.",
                self.proceso.LOG_PREFIX,
            )
            try:
                self.error.emit("Ejecucion cancelada por el usuario")
            except Exception:
                pass
        except BaseException as e:  # noqa: BLE001 - captura defensiva
            # Loggear con traceback completo a la bitacora.
            try:
                log().exception("Error en worker: %s", e)
            except Exception:
                pass  # Si el log falla, NO propagar.
            # Mensaje seguro para la UI.
            msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            try:
                self.error.emit(msg)
            except Exception:
                pass


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
        # Layout principal: SOLO aloja al QScrollArea (sin margenes).
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Contenedor scrollable: todo el contenido vive aca adentro.
        self.contenedor = QWidget()
        self.contenedor.setObjectName("VistaEjecucionContenedor")
        self.contenedor.setMinimumWidth(560)
        cont_layout = QVBoxLayout(self.contenedor)
        cont_layout.setContentsMargins(24, 20, 24, 20)
        cont_layout.setSpacing(14)

        # --- Header con boton "Volver" + nombre del proceso ---------
        volver_row = QHBoxLayout()
        volver_row.setContentsMargins(0, 0, 0, 0)
        volver_row.setSpacing(0)
        self.btn_volver = QPushButton("←  Procesos")
        self.btn_volver.setObjectName("secondary")
        self.btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver.setMinimumWidth(140)
        self.btn_volver.setMaximumWidth(180)
        self.btn_volver.clicked.connect(self.proceso_cambiado.emit)
        volver_row.addWidget(self.btn_volver)
        volver_row.addStretch()
        cont_layout.addLayout(volver_row)

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
        cont_layout.addLayout(titulo_row)

        self._desc = QLabel("")
        self._desc.setWordWrap(True)
        cont_layout.addWidget(self._desc)

        self.drop_zone = DropZone(
            mensaje="Arrastra el archivo aqui o haz clic en Examinar",
        )
        self.drop_zone.archivos_seleccionados.connect(self._agregar_archivos)
        cont_layout.addWidget(self.drop_zone)

        self._lbl_archivos = QLabel("ARCHIVOS CARGADOS")
        cont_layout.addWidget(self._lbl_archivos)
        self.lista = QListWidget()
        self.lista.setMaximumHeight(100)
        cont_layout.addWidget(self.lista)

        btn_row = QHBoxLayout()
        self.btn_quitar = QPushButton("Quitar último")
        self.btn_quitar.clicked.connect(self._quitar_ultimo)
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_limpiar.clicked.connect(self._limpiar_archivos)
        self.btn_ejecutar = QPushButton("▶  Ejecutar proceso")
        self.btn_ejecutar.setObjectName("primary")
        self.btn_ejecutar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ejecutar.clicked.connect(self._ejecutar)
        # Boton "Cancelar ejecucion". Empieza oculto; aparece cuando
        # arranca el worker y se oculta cuando termina.
        self.btn_cancelar = QPushButton("✕  Cancelar")
        self.btn_cancelar.setObjectName("danger")
        self.btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self._cancelar_ejecucion)
        self.btn_cancelar.hide()
        btn_row.addWidget(self.btn_quitar)
        btn_row.addWidget(self.btn_limpiar)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancelar)
        btn_row.addWidget(self.btn_ejecutar)
        cont_layout.addLayout(btn_row)

        self.progress = QProgressBar()
        # Arrancamos en modo indeterminate (spinner). Cuando llegue el
        # PRIMER progreso real desde el worker, _on_progreso cambia a
        # modo determinado (setRange(0, 100) + setValue). Asi, durante
        # el I/O inicial (lectura del ZIP/Excel + copy_data) el usuario
        # ve el spinner en vez de una barra estancada en 0% -> no da
        # sensacion de cuelgue. NO emite signals extra desde el worker.
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        self.progress.hide()
        cont_layout.addWidget(self.progress)
        self._progreso_iniciado = False  # Para alternar indeterminate -> determinado.
        self.estado = QLabel("")
        cont_layout.addWidget(self.estado)

        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        cont_layout.addWidget(self.sep)

        self._lbl_result = QLabel("ARCHIVOS GENERADOS")
        cont_layout.addWidget(self._lbl_result)
        self.resultados = TablaResultados()
        cont_layout.addWidget(self.resultados)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("VistaEjecucionScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(self.contenedor)
        layout.addWidget(self.scroll)

        self._actualizar_estado()
        self._aplicar_tema(self._tema_actual())

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
        self.scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {paleta.bg};"
            f" border: none; }}"
            f" QScrollArea > QWidget > QWidget"
            f" {{ background-color: transparent; }}"
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
        self.btn_cancelar.show()
        self.progress.show()
        self.estado.setText(f"Ejecutando {self._nombre_proceso}...")

        self._worker = WorkerEjecucion(
            proceso, list(self._archivos), self._cfg.modo_prueba,
        )
        # Forzar ``Qt.QueuedConnection`` para que los slots se ejecuten
        # SIEMPRE en el thread del receptor (main thread). Sin esto, Qt
        # decide el tipo de conexion segun los threads al momento del
        # connect, lo cual puede causar que ``_on_progreso`` se ejecute
        # en el thread del worker y toque widgets de UI -> crash
        # silencioso en Windows + PySide6.
        self._worker.terminado.connect(
            self._on_terminado, Qt.ConnectionType.QueuedConnection,
        )
        self._worker.error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection,
        )
        self._worker.progreso.connect(
            self._on_progreso, Qt.ConnectionType.QueuedConnection,
        )
        # Resetear el flag para que el primer emit cambie el modo
        # del QProgressBar de indeterminate a determinado.
        self._progreso_iniciado = False
        self.progress.setRange(0, 0)  # indeterminate mientras esperamos el 1er emit.
        self.progress.setValue(0)
        self._worker.start()

    def _on_progreso(self, pct: int) -> None:
        """Handler del signal ``progreso`` del worker (0..100).

        La primera vez que llega progreso real, cambia el QProgressBar
        de modo indeterminate (spinner) a modo determinado (% real).
        Asi durante el I/O inicial el usuario ve el spinner, no una
        barra estancada en 0%.
        """
        if not self._progreso_iniciado:
            # Primer progreso real: pasamos a modo determinado.
            self._progreso_iniciado = True
            self.progress.setRange(0, 100)
        self.progress.setValue(pct)
        # Actualizar el label con el % para feedback textual.
        self.estado.setText(
            f"Ejecutando {self._nombre_proceso}... {pct}%"
        )

    def _cancelar_ejecucion(self) -> None:
        """Handler del boton 'Cancelar'. Pregunta confirmacion y avisa al worker."""
        if self._worker is None or not self._worker.isRunning():
            return
        resp = QMessageBox.question(
            self,
            "Cancelar ejecucion",
            f"¿Cancelar la ejecucion de {self._nombre_proceso}?\n\n"
            "Los archivos parciales no se guardaran. Esta accion no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,  # default = No (es la opcion segura)
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        # Marcar el worker para que termine ASAP. El run() chequea
        # self._cancelado y emite error si estaba marcado al inicio,
        # o ignora la emision de terminado si se marco durante el run.
        self._worker.cancelar()
        self.btn_cancelar.setEnabled(False)
        self.estado.setText(f"Cancelando {self._nombre_proceso}...")
        log().info("%s cancelacion solicitada por el usuario", self._worker.proceso.LOG_PREFIX)

    def _on_terminado(self, resultado: ResultadoProceso) -> None:
        self.progress.hide()
        # Resetear el flag para la proxima ejecucion (vuelve a indeterminate).
        self._progreso_iniciado = False
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        self.btn_ejecutar.setEnabled(True)
        self.btn_cancelar.hide()
        self.btn_cancelar.setEnabled(True)

        if resultado.exito:
            # Invalidar el cache de "ultimo ejecutado" para que el panel
            # de Inicio muestre el resultado nuevo al volver.
            try:
                from utils.bitacora import invalidar_cache_obtener_ultimo
                invalidar_cache_obtener_ultimo()
            except Exception:
                pass

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
        # Resetear el flag para la proxima ejecucion (vuelve a indeterminate).
        self._progreso_iniciado = False
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        self.btn_ejecutar.setEnabled(True)
        self.btn_cancelar.hide()
        self.btn_cancelar.setEnabled(True)
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