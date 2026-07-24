"""Pantalla Procesos: ejecutar cualquiera de los 3 procesos desde la UI.

Estructura:
+--------------------------------------------------+
| Selector de proceso (Combobox)                  |
+--------------------------------------------------+
| Descripcion del proceso seleccionado             |
+--------------------------------------------------+
| DropZone (arrastrar archivos / examinar)        |
+--------------------------------------------------+
| Lista de archivos cargados                       |
+--------------------------------------------------+
| [Quitar ultimo] [Limpiar] [Ejecutar]             |
+--------------------------------------------------+
| Barra de progreso + label de estado              |
+--------------------------------------------------+
| Tabla con los archivos generados                 |
+--------------------------------------------------+
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import get_config
from procesos.base import ProcesoBase, ResultadoProceso
from ui.widgets.drop_zone import DropZone
from ui.widgets.tabla_resultados import TablaResultados
from utils.bitacora import log


class WorkerEjecucion(QThread):
    """Hilo que ejecuta un proceso sin bloquear la UI."""

    terminado = Signal(object)  # ResultadoProceso
    error = Signal(str)

    def __init__(self, proceso: ProcesoBase, archivos: list[Path],
                 modo_prueba: bool) -> None:
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


class PantallaProcesos(QWidget):
    """Pantalla para seleccionar proceso y ejecutarlo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = get_config()
        self._archivos: list[Path] = []
        self._worker: WorkerEjecucion | None = None

        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Selector de proceso -------------------------------------
        layout.addWidget(QLabel("<h2>Ejecutar proceso</h2>"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Proceso:"))
        self.combo = QComboBox()
        # Cargar nombres y descripciones desde la config.
        for nombre in self._cfg.nombres_procesos():
            cls = self._cfg.procesos[nombre]
            self.combo.addItem(nombre)
            # Guardamos la descripcion en user data para mostrarla.
            self.combo.setItemData(self.combo.count() - 1, cls().descripcion)
        self.combo.currentIndexChanged.connect(self._on_cambio_proceso)
        row.addWidget(self.combo, 1)
        layout.addLayout(row)

        # Descripcion del proceso.
        self._desc_label = QLabel("")
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: #555; padding: 4px;")
        layout.addWidget(self._desc_label)

        # --- DropZone -----------------------------------------------
        self.drop_zone = DropZone(
            mensaje="Arrastra el archivo aqui o haz clic en Examinar",
        )
        self.drop_zone.archivos_seleccionados.connect(self._agregar_archivos)
        layout.addWidget(self.drop_zone)

        # --- Lista de archivos --------------------------------------
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
        self.progress.setRange(0, 0)  # Indeterminado.
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

        # Estado inicial.
        self._on_cambio_proceso(0)

    # -- Manejo de archivos -----------------------------------------

    def _agregar_archivos(self, archivos: list[Path]) -> None:
        # Validar extensiones.
        proceso_cls = self._cfg.procesos[self.combo.currentText()]
        instancia = proceso_cls()
        error = instancia.validar_archivos(archivos)
        if error:
            QMessageBox.warning(self, "Archivos invalidos", error)
            return
        # Agregar evitando duplicados.
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

    # -- Cambio de proceso ------------------------------------------

    def _on_cambio_proceso(self, idx: int) -> None:
        nombre = self.combo.itemText(idx)
        desc = self.combo.itemData(idx) or ""
        self._desc_label.setText(f"<b>{nombre}</b>: {desc}")
        # Actualizar extensiones aceptadas del drop zone.
        cls = self._cfg.procesos[nombre]
        self.drop_zone.set_extensiones_aceptadas(cls().extensiones_entrada)
        # Limpiar archivos y resultados al cambiar de proceso.
        self._limpiar_archivos()

    # -- Ejecucion ---------------------------------------------------

    def _ejecutar(self) -> None:
        if not self._archivos:
            QMessageBox.information(
                self, "Sin archivos", "Agrega al menos un archivo."
            )
            return
        if self._worker is not None and self._worker.isRunning():
            return

        nombre = self.combo.currentText()
        proceso_cls = self._cfg.procesos[nombre]
        proceso = proceso_cls()

        # Validar antes de ejecutar.
        error = proceso.validar_archivos(self._archivos)
        if error:
            QMessageBox.warning(self, "Archivos invalidos", error)
            return

        # Deshabilitar UI.
        self.btn_ejecutar.setEnabled(False)
        self.combo.setEnabled(False)
        self.progress.show()
        self.estado.setText(f"Ejecutando {nombre}...")

        # Lanzar worker.
        self._worker = WorkerEjecucion(
            proceso, list(self._archivos), self._cfg.modo_prueba,
        )
        self._worker.terminado.connect(self._on_terminado)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_terminado(self, resultado: ResultadoProceso) -> None:
        self.progress.hide()
        self.btn_ejecutar.setEnabled(True)
        self.combo.setEnabled(True)

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
        self.combo.setEnabled(True)
        self.estado.setText(f"[ERROR] {msg}")
        QMessageBox.critical(self, "Error inesperado", msg)