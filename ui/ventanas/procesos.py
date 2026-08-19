"""Pantalla de selección y ejecución de procesos."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import DATA_DIR, get_config
from core.base import ProcesoBase, ResultadoProceso
from core.comprobante import ProcesoComprobante
from core.fierro import ProcesoFierro
from core.json_manager import escribir_json, leer_json
from core.zeus import ProcesoZeus
from ui.ventanas.dialogo_codigos_nuevos import DecisionCodigos, DialogoCodigosNuevos
from ui.widgets.drop_zone import DropZone


class WorkerEjecucion(QObject):
    """Ejecuta un proceso en un hilo secundario para no congelar la UI."""

    progreso = Signal(int, int)
    finalizado = Signal(ResultadoProceso)

    def __init__(self, proceso: ProcesoBase, archivos: list[Path], modo_prueba: bool) -> None:
        super().__init__()
        self.proceso = proceso
        self.archivos = archivos
        self.modo_prueba = modo_prueba

    def run(self) -> None:
        try:
            resultado = self.proceso.ejecutar(
                self.archivos,
                modo_prueba=self.modo_prueba,
                progreso=lambda act, tot: self.progreso.emit(act, tot),
            )
        except Exception as e:
            resultado = ResultadoProceso(exito=False, mensaje=f"Error inesperado: {e}")
        self.finalizado.emit(resultado)


class VistaProcesos(QWidget):
    """Pantalla de Procesos con sub-sidebar y área de ejecución."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = get_config()
        self._instancias_procesos: dict[str, ProcesoBase] = {
            "comprobante": ProcesoComprobante(),
            "fierro": ProcesoFierro(),
            "zeus": ProcesoZeus(),
        }
        self._proceso_activo_key = "comprobante"
        self._archivos_salida_recientes: list[Path] = []

        self._thread: QThread | None = None
        self._worker: WorkerEjecucion | None = None

        self._construir_ui()
        self._seleccionar_proceso("comprobante")

    def _construir_ui(self) -> None:
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # 1. Sub-sidebar lateral izquierdo (Selector de procesos)
        panel_lateral = self._crear_panel_lateral()
        layout_principal.addWidget(panel_lateral)

        # 2. Área principal de trabajo
        panel_principal = self._crear_panel_principal()
        layout_principal.addWidget(panel_principal, 1)

    def _crear_panel_lateral(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("sub_sidebar")
        frame.setFixedWidth(230)
        frame.setStyleSheet(
            """
            QFrame#sub_sidebar {
                background-color: #FFFFFF;
                border-right: 1px solid #E2E8F0;
            }
            """
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)

        lbl_titulo = QLabel("PROCESOS")
        lbl_titulo.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")
        layout.addWidget(lbl_titulo)

        self._btn_proc1 = QPushButton("Generar Comprobante")
        self._btn_proc1.setObjectName("btn_proc_selector")
        self._btn_proc1.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_proc1.clicked.connect(lambda: self._seleccionar_proceso("comprobante"))

        self._btn_proc2 = QPushButton("Interfaz Fierro")
        self._btn_proc2.setObjectName("btn_proc_selector")
        self._btn_proc2.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_proc2.clicked.connect(lambda: self._seleccionar_proceso("fierro"))

        self._btn_proc3 = QPushButton("Interfaz Zeus")
        self._btn_proc3.setObjectName("btn_proc_selector")
        self._btn_proc3.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_proc3.clicked.connect(lambda: self._seleccionar_proceso("zeus"))

        self._botones_procesos = {
            "comprobante": self._btn_proc1,
            "fierro": self._btn_proc2,
            "zeus": self._btn_proc3,
        }

        for btn in self._botones_procesos.values():
            btn.setStyleSheet(
                """
                QPushButton#btn_proc_selector {
                    text-align: left;
                    background-color: transparent;
                    color: #475569;
                    font-size: 13px;
                    font-weight: 600;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 14px;
                }
                QPushButton#btn_proc_selector:hover {
                    background-color: #F1F5F9;
                    color: #0F172A;
                }
                QPushButton#btn_proc_selector[active="true"] {
                    background-color: #EFF6FF;
                    color: #2563EB;
                    font-weight: 700;
                }
                """
            )
            layout.addWidget(btn)

        layout.addStretch(1)
        return frame

    def _crear_panel_principal(self) -> QWidget:
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Cabecera del proceso
        self._lbl_proceso_titulo = QLabel("Generar Comprobante")
        self._lbl_proceso_titulo.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        layout.addWidget(self._lbl_proceso_titulo)

        self._lbl_proceso_desc = QLabel("Descripción del proceso...")
        self._lbl_proceso_desc.setStyleSheet("font-size: 13px; color: #64748B;")
        self._lbl_proceso_desc.setWordWrap(True)
        layout.addWidget(self._lbl_proceso_desc)

        # DropZone & File List (más compacto y de altura controlada)
        self._drop_zone = DropZone()
        self._drop_zone.archivos_cambiados.connect(self._on_archivos_cambiados)
        layout.addWidget(self._drop_zone)

        # Fila de Botones de Acción
        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(12)

        self._lbl_conteo_archivos = QLabel("0 archivos cargados")
        self._lbl_conteo_archivos.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        fila_acciones.addWidget(self._lbl_conteo_archivos)
        fila_acciones.addStretch(1)

        # Botón Vaciar lista (Rojo)
        self._btn_vaciar = QPushButton("Vaciar lista")
        self._btn_vaciar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_vaciar.setStyleSheet(
            """
            QPushButton {
                background-color: #FEE2E2;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
                border-color: #B91C1C;
            }
            QPushButton:disabled {
                background-color: #F8FAFC;
                color: #CBD5E1;
                border-color: #E2E8F0;
            }
            """
        )
        self._btn_vaciar.clicked.connect(self._drop_zone.vaciar)
        self._btn_vaciar.setEnabled(False)
        fila_acciones.addWidget(self._btn_vaciar)

        # Botón Examinar (Añadir archivos)
        self._btn_examinar = QPushButton("Examinar archivos...")
        self._btn_examinar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_examinar.setStyleSheet(
            """
            QPushButton {
                background-color: #FFFFFF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
                border-color: #2563EB;
            }
            """
        )
        self._btn_examinar.clicked.connect(self._drop_zone.abrir_dialogo_examinar)
        fila_acciones.addWidget(self._btn_examinar)

        # Botón Ejecutar (Azul sólido)
        self._btn_ejecutar = QPushButton("Ejecutar proceso")
        self._btn_ejecutar.setObjectName("primary")
        self._btn_ejecutar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_ejecutar.clicked.connect(self._iniciar_ejecucion)
        self._btn_ejecutar.setEnabled(False)
        fila_acciones.addWidget(self._btn_ejecutar)

        layout.addLayout(fila_acciones)

        # Barra de progreso (SIEMPRE VISIBLE)
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #E2E8F0;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 4px;
            }
            """
        )
        layout.addWidget(self._progress_bar)

        # Panel de Resultados (Más grande y expandible)
        self._panel_resultados = QFrame()
        self._panel_resultados.setObjectName("panel_resultados")
        self._panel_resultados.setStyleSheet(
            """
            QFrame#panel_resultados {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                min-height: 160px;
            }
            """
        )
        layout_res = QVBoxLayout(self._panel_resultados)
        layout_res.setContentsMargins(20, 16, 20, 16)
        layout_res.setSpacing(10)

        # Cabecera de resultados con estado y botón
        res_header = QHBoxLayout()
        self._lbl_res_estado = QLabel("Resultado del Proceso")
        self._lbl_res_estado.setStyleSheet("font-weight: 700; font-size: 14px; color: #1E293B;")
        res_header.addWidget(self._lbl_res_estado)
        res_header.addStretch(1)

        self._btn_abrir_carpeta = QPushButton("Abrir ubicación →")
        self._btn_abrir_carpeta.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_abrir_carpeta.clicked.connect(self._abrir_carpeta_resultados)
        self._btn_abrir_carpeta.hide()
        res_header.addWidget(self._btn_abrir_carpeta)
        layout_res.addLayout(res_header)

        # Detalle / mensaje / archivos
        self._lbl_res_detalle = QLabel("Carga los archivos de entrada y pulsa Ejecutar para ver los resultados aquí.")
        self._lbl_res_detalle.setStyleSheet("font-size: 13px; color: #64748B;")
        self._lbl_res_detalle.setWordWrap(True)
        self._lbl_res_detalle.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout_res.addWidget(self._lbl_res_detalle, 1)

        layout.addWidget(self._panel_resultados, 1)

        return contenedor

    def _seleccionar_proceso(self, key: str) -> None:
        self._proceso_activo_key = key
        proceso = self._instancias_procesos[key]

        # Actualizar botones del sub-sidebar
        for k, btn in self._botones_procesos.items():
            activo = (k == key)
            btn.setProperty("active", "true" if activo else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Actualizar textos
        titulos = {
            "comprobante": "Generar Comprobante",
            "fierro": "Interfaz Fierro",
            "zeus": "Interfaz Zeus",
        }
        self._lbl_proceso_titulo.setText(titulos.get(key, key))
        self._lbl_proceso_desc.setText(proceso.descripcion)

        # Configurar DropZone para este proceso
        self._drop_zone.set_extensiones_aceptadas(proceso.extensiones_entrada)
        self._drop_zone.set_permitir_multiple(key == "comprobante")
        self._drop_zone.vaciar()

        # Resetear resultado
        self._lbl_res_estado.setText("Resultado del Proceso")
        self._lbl_res_estado.setStyleSheet("font-weight: 700; font-size: 14px; color: #1E293B;")
        self._lbl_res_detalle.setText("Carga los archivos de entrada y pulsa Ejecutar para ver los resultados aquí.")
        self._btn_abrir_carpeta.hide()
        self._progress_bar.setValue(0)

    def _on_archivos_cambiados(self, archivos: list[Path]) -> None:
        n = len(archivos)
        self._lbl_conteo_archivos.setText(f"{n} archivo(s) listo(s)")
        self._btn_vaciar.setEnabled(n > 0)
        self._btn_ejecutar.setEnabled(n > 0)

    def _aplicar_decision_codigos(self, decision: DecisionCodigos) -> bool:
        """Persiste la decisión del usuario haciendo backup previo.

        Retorna True si se escribieron cambios correctamente.
        """
        json_dir = self._config.ruta_json("comprobante", "foapal.json").parent
        foapal_path = json_dir / "foapal.json"
        ignorados_path = json_dir / "codigos_ignorados.json"

        backup_dir = DATA_DIR / "backups" / "comprobante"
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            if decision.agregar or decision.ignorar:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                for origen in (foapal_path, ignorados_path):
                    if origen.exists():
                        destino = backup_dir / f"{timestamp}_{origen.name}"
                        shutil.copy2(str(origen), str(destino))

            foapal = leer_json(foapal_path)
            ignorados = leer_json(ignorados_path)

            for codigo, campos in decision.agregar.items():
                dc = campos.get("D/C", "D")
                seccion = "creditos" if dc == "C" else "debitos"
                foapal.setdefault(seccion, {})[codigo] = {
                    "Fondo": campos["Fondo"],
                    "Organizacion": campos["Organizacion"],
                    "Cuenta": campos["Cuenta"],
                    "Programa": campos["Programa"],
                    "D/C": dc,
                }

            if decision.ignorar:
                ignorados.setdefault("codigos", {}).update(decision.ignorar)
                # Normalizar: ordenar por longitud y luego valor.
                ignorados["codigos"] = dict(
                    sorted(ignorados["codigos"].items(), key=lambda c: (len(c[0]), c[0]))
                )

            if decision.agregar:
                escribir_json(foapal_path, foapal)
            if decision.ignorar:
                escribir_json(ignorados_path, ignorados)

            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al guardar códigos",
                f"No se pudieron guardar los cambios en los JSONs:\n{e}",
            )
            return False

    def _iniciar_ejecucion(self) -> None:
        archivos = self._drop_zone.obtener_archivos()
        if not archivos:
            return

        proceso = self._instancias_procesos[self._proceso_activo_key]
        error = proceso.validar_archivos(archivos)
        if error:
            self._lbl_res_estado.setText("Archivos no válidos")
            self._lbl_res_estado.setStyleSheet("font-weight: 700; font-size: 13px; color: #DC2626;")
            self._lbl_res_detalle.setText(error)
            return

        # Escaneo de códigos de concepto nuevos solo para Comprobante.
        # Se ejecuta en el hilo principal para poder mostrar el diálogo modal.
        if self._proceso_activo_key == "comprobante" and isinstance(proceso, ProcesoComprobante):
            try:
                self._lbl_res_estado.setText("Revisando códigos de concepto...")
                self._lbl_res_estado.setStyleSheet(
                    "font-weight: 700; font-size: 13px; color: #2563EB;"
                )
                codigos, descripciones = proceso.obtener_codigos_desconocidos(list(archivos))
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error al escanear códigos",
                    f"No se pudieron revisar los códigos de concepto:\n{e}",
                )
                self._lbl_res_estado.setText("Resultado del Proceso")
                self._lbl_res_estado.setStyleSheet(
                    "font-weight: 700; font-size: 14px; color: #1E293B;"
                )
                return

            if codigos:
                decision = DialogoCodigosNuevos.solicitar_decision(
                    self, codigos, descripciones
                )
                if decision is None:
                    self._lbl_res_estado.setText("Ejecución cancelada")
                    self._lbl_res_estado.setStyleSheet(
                        "font-weight: 700; font-size: 13px; color: #DC2626;"
                    )
                    self._lbl_res_detalle.setText(
                        "Cancelaste la gestión de códigos nuevos. "
                        "No se ejecutó el proceso."
                    )
                    return

                if not self._aplicar_decision_codigos(decision):
                    return

                # Recrear la instancia para que cargue los JSONs actualizados.
                proceso = ProcesoComprobante()
                self._instancias_procesos["comprobante"] = proceso

        # Deshabilitar controles
        self._btn_ejecutar.setEnabled(False)
        self._btn_vaciar.setEnabled(False)
        self._btn_examinar.setEnabled(False)

        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)

        self._lbl_res_estado.setText("Ejecutando proceso...")
        self._lbl_res_estado.setStyleSheet("font-weight: 700; font-size: 13px; color: #2563EB;")
        self._lbl_res_detalle.setText("Por favor espera mientras se procesa la información.")

        modo_prueba = self._config.modo_prueba

        # Iniciar Worker en QThread
        self._thread = QThread()
        self._worker = WorkerEjecucion(proceso, archivos, modo_prueba)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progreso.connect(self._on_progreso)
        self._worker.finalizado.connect(self._on_finalizado)
        self._worker.finalizado.connect(self._thread.quit)
        self._worker.finalizado.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_progreso(self, actual: int, total: int) -> None:
        if total > 0:
            porcentaje = int((actual / total) * 100)
            self._progress_bar.setValue(porcentaje)

    def _on_finalizado(self, resultado: ResultadoProceso) -> None:
        self._btn_ejecutar.setEnabled(True)
        self._btn_vaciar.setEnabled(True)
        self._btn_examinar.setEnabled(True)

        if resultado.exito:
            self._progress_bar.setValue(100)
            self._lbl_res_estado.setText("✓ Ejecución exitosa")
            self._lbl_res_estado.setStyleSheet("font-weight: 700; font-size: 13px; color: #16A34A;")
            nombres = ", ".join(p.name for p in resultado.archivos_salida)
            self._lbl_res_detalle.setText(f"{resultado.mensaje} Archivos generados: {nombres}")
            self._archivos_salida_recientes = resultado.archivos_salida
            self._btn_abrir_carpeta.show()
        else:
            self._progress_bar.setValue(0)
            self._lbl_res_estado.setText("✕ Error en la ejecución")
            self._lbl_res_estado.setStyleSheet("font-weight: 700; font-size: 13px; color: #DC2626;")
            self._lbl_res_detalle.setText(resultado.mensaje)
            self._btn_abrir_carpeta.hide()

    def _abrir_carpeta_resultados(self) -> None:
        if not self._archivos_salida_recientes:
            return
        primero = self._archivos_salida_recientes[0]
        carpeta = primero.parent
        if sys.platform == "win32":
            os.startfile(str(carpeta))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(carpeta)], check=False)
        else:
            subprocess.run(["xdg-open", str(carpeta)], check=False)
