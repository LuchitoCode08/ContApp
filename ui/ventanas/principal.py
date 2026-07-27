"""Ventana principal de ContApp.

Estructura:
+----------------------------------------+
| Banner naranja (modo prueba)           |
+------+---------------------------------+
|      |                                 |
| Side | Pantalla activa                 |
| bar  | (Inicio / Procesos / ...)       |
|      |                                 |
+------+---------------------------------+
| Switch modo prueba                     |
+----------------------------------------+
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.config import get_config
from ui.widgets.banner_modo_prueba import BannerModoPrueba
from ui.widgets.switch_modo_prueba import SwitchModoPrueba
from ui.widgets.tarjeta_proceso import TarjetaProceso
from utils.bitacora import log, obtener_ultimo


# Iconos por proceso (consistente con ejecutar_proceso.py).
ICONOS: dict[str, str] = {
    "comprobante": "📋",
    "fierro": "🔥",
    "zeus": "⚡",
}


class PanelUltimoEjecutado(QFrame):
    """Panel que muestra info del ultimo proceso ejecutado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "PanelUltimoEjecutado {"
            " background-color: #FAFAFA;"
            " border: 1px solid #E0E0E0;"
            " border-radius: 6px;"
            "}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        self._titulo = QLabel("Ultimo proceso ejecutado")
        f = QFont()
        f.setBold(True)
        f.setPointSize(12)
        self._titulo.setFont(f)
        layout.addWidget(self._titulo)

        self._proceso = QLabel("—")
        self._proceso.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self._proceso)

        self._fecha = QLabel("")
        self._fecha.setStyleSheet("color: #616161;")
        layout.addWidget(self._fecha)

        self._archivos_lbl = QLabel("Archivos generados:")
        self._archivos_lbl.setStyleSheet("color: #616161; margin-top: 8px;")
        layout.addWidget(self._archivos_lbl)

        self._archivos_box = QLabel("")
        self._archivos_box.setWordWrap(True)
        self._archivos_box.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._archivos_box.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 11px;"
            " color: #212121; background-color: #FFFFFF;"
            " border: 1px solid #E0E0E0; border-radius: 4px;"
            " padding: 6px;"
        )
        self._archivos_box.setMinimumHeight(60)
        layout.addWidget(self._archivos_box)

        # Botones: actualizar + ver reporte.
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_refrescar = QPushButton("Refrescar")
        self._btn_refrescar.clicked.connect(self.refrescar)
        btn_row.addWidget(self._btn_refrescar)
        self._btn_ver = QPushButton("Ver reporte")
        self._btn_ver.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "padding: 6px 14px; }"
        )
        self._btn_ver.clicked.connect(self._abrir_reporte)
        btn_row.addWidget(self._btn_ver)
        layout.addLayout(btn_row)

        self._ultimo: dict | None = None
        self.refrescar()

    def refrescar(self) -> None:
        """Recarga la info desde la bitacora."""
        self._ultimo = obtener_ultimo()
        if not self._ultimo:
            self._proceso.setText("Sin ejecuciones registradas")
            self._fecha.setText("")
            self._archivos_box.setText(
                "Aun no se ejecuto ningun proceso."
                " Usa la pantalla Procesos para arrancar."
            )
            self._btn_ver.setEnabled(False)
            return

        proc = self._ultimo.get("proceso", "")
        icono = ICONOS.get(proc, "▶")
        self._proceso.setText(f"{icono} {proc or '(proceso)'}")
        self._fecha.setText(f"Fecha: {self._ultimo['fecha']}")
        archivos = self._ultimo.get("archivos", [])
        if archivos:
            self._archivos_box.setText("\n".join(archivos))
            self._btn_ver.setEnabled(True)
        else:
            self._archivos_box.setText("(sin archivos)")
            self._btn_ver.setEnabled(False)

    def _abrir_reporte(self) -> None:
        """Abre la carpeta del archivo mas reciente en el explorador."""
        archivos = self._ultimo.get("archivos", []) if self._ultimo else []
        if not archivos:
            return
        # Tomamos el directorio del primer archivo.
        carpeta = Path(archivos[0]).parent
        if not carpeta.exists():
            QMessageBox.warning(
                self,
                "Carpeta no encontrada",
                f"La carpeta ya no existe:\n{carpeta}",
            )
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(carpeta))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(carpeta)])
            else:
                subprocess.Popen(["xdg-open", str(carpeta)])
        except Exception as e:
            log().exception("No se pudo abrir la carpeta: %s", e)
            QMessageBox.warning(
                self, "Error", f"No se pudo abrir la carpeta:\n{e}"
            )


class PantallaInicio(QWidget):
    """Dashboard de Inicio con tarjetas de procesos + ultimo ejecutado."""

    proceso_solicitado = Signal(str)  # cuando se hace click en una tarjeta

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = get_config()
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Encabezado de bienvenida ------------------------------
        titulo = QLabel(f"Hola, {self._cfg.usuario or 'usuario'}")
        f = QFont()
        f.setPointSize(22)
        f.setBold(True)
        titulo.setFont(f)
        layout.addWidget(titulo)

        sub = QLabel(
            "Sistema de Automatizacion Contable. "
            "Elegi un proceso para empezar o revisa el ultimo que ejecutaste."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #616161;")
        layout.addWidget(sub)

        layout.addSpacing(12)

        # --- Grid de tarjetas --------------------------------------
        grid_lbl = QLabel("Procesos disponibles")
        grid_lbl.setStyleSheet("font-weight: bold; color: #424242;")
        layout.addWidget(grid_lbl)

        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

        nombres = self._cfg.nombres_procesos()
        columnas = 3
        for i, nombre in enumerate(nombres):
            cls = self._cfg.procesos[nombre]
            icono = ICONOS.get(nombre, "▶")
            tarjeta = TarjetaProceso(
                nombre=nombre,
                descripcion=cls().descripcion,
                icono=icono,
            )
            tarjeta.seleccionado.connect(self.proceso_solicitado.emit)
            fila = i // columnas
            col = i % columnas
            grid.addWidget(tarjeta, fila, col)
            grid.setColumnStretch(col, 1)

        layout.addWidget(grid_container)

        layout.addSpacing(8)

        # --- Panel "Ultimo ejecutado" ------------------------------
        self.panel_ultimo = PanelUltimoEjecutado()
        layout.addWidget(self.panel_ultimo)

        layout.addStretch()

    def refrescar_ultimo(self) -> None:
        """Lo llama VentanaPrincipal cuando vuelve a la pantalla Inicio."""
        self.panel_ultimo.refrescar()


class VentanaPrincipal(QMainWindow):
    """Ventana principal con sidebar y 4 pantallas."""

    SECCIONES = ["Inicio", "Procesos", "Diccionarios", "Configuracion"]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ContApp")
        self.resize(1100, 720)
        self._cfg = get_config()

        # Banner modo prueba.
        self.banner = BannerModoPrueba()

        # Sidebar.
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        for sec in self.SECCIONES:
            it = QListWidgetItem(sec)
            self.sidebar.addItem(it)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._cambiar_pantalla)

        # Stack de pantallas.
        self.pantalla_inicio = PantallaInicio()
        self.pantalla_procesos = self._crear_pantalla_procesos()
        self.pantalla_diccionarios = self._crear_pantalla_diccionarios()
        self.pantalla_configuracion = self._crear_pantalla_configuracion()

        self.stack = QStackedWidget()
        for p in (
            self.pantalla_inicio,
            self.pantalla_procesos,
            self.pantalla_diccionarios,
            self.pantalla_configuracion,
        ):
            self.stack.addWidget(p)

        # Conexion: click en tarjeta de Inicio -> ir a Procesos pre-selec.
        self.pantalla_inicio.proceso_solicitado.connect(
            self._ir_a_procesos_preseleccionado
        )

        # Switch modo prueba.
        self.switch = SwitchModoPrueba()
        self.switch.set_activo(self._cfg.modo_prueba)
        self.switch.modo_prueba_cambiado.connect(self._on_modo_prueba)
        self._on_modo_prueba(self._cfg.modo_prueba)

        # Layout central.
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.banner)

        body = QHBoxLayout()
        body.addWidget(self.sidebar)
        body.addWidget(self.stack, 1)
        layout.addLayout(body, 1)

        footer = QHBoxLayout()
        footer.addWidget(self.switch)
        footer.addStretch()
        self._usuario_label = QLabel(f"Usuario: {self._cfg.usuario}")
        footer.addWidget(self._usuario_label)
        layout.addLayout(footer)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

    # -- Navegacion -------------------------------------------------

    def _cambiar_pantalla(self, idx: int) -> None:
        if 0 <= idx < self.stack.count():
            self.stack.setCurrentIndex(idx)
            # Si volvemos a Inicio, refrescamos el panel de ultimo ejecutado.
            if idx == 0:
                self.pantalla_inicio.refrescar_ultimo()

    def _ir_a_procesos_preseleccionado(self, nombre: str) -> None:
        """Click en tarjeta del dashboard: salta a Procesos con ese proceso."""
        self.sidebar.setCurrentRow(1)  # indice de "Procesos" en el sidebar
        self.pantalla_procesos.seleccionar_proceso(nombre)

    # -- Pantallas --------------------------------------------------

    def _crear_pantalla_procesos(self) -> QWidget:
        from ui.ventanas.ejecutar_proceso import PantallaProcesos
        return PantallaProcesos()

    def _crear_pantalla_diccionarios(self) -> QWidget:
        from ui.ventanas.editor_json import PantallaDiccionarios
        return PantallaDiccionarios()

    def _crear_pantalla_configuracion(self) -> QWidget:
        from ui.ventanas.configuracion import PantallaConfiguracion
        return PantallaConfiguracion()

    # -- Modo prueba --------------------------------------------------

    def _on_modo_prueba(self, activo: bool) -> None:
        self._cfg.modo_prueba = activo
        self.banner.set_activo(activo)
        self.statusBar().showMessage(
            "Modo prueba activado" if activo else "Modo produccion",
            3000,
        )