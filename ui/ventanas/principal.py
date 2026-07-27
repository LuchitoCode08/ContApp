"""Ventana principal de ContApp.

Estructura:
+----------------------------------------+
| Banner naranja/verde (modo prueba)     |
+------+---------------------------------+
| Logo |                                 |
| Side | Pantalla activa                 |
| bar  | (Inicio / Procesos / ...)       |
|      |                                 |
+------+---------------------------------+
| Switch modo prueba | usuario | tema   |
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
    QApplication,
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
from ui.recursos.tema import (
    CLARO,
    ESPACIO_MD,
    ESPACIO_LG,
    ESPACIO_SM,
    OSCURO,
    _paleta,
    aplicar_tema,
    tema_actual,
)
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

# Iconos para las secciones del sidebar.
ICONOS_SECCION: dict[str, str] = {
    "Inicio": "🏠",
    "Procesos": "▶",
    "Diccionarios": "📚",
    "Configuracion": "⚙",
}


class PanelUltimoEjecutado(QFrame):
    """Panel que muestra info del ultimo proceso ejecutado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelUltimoEjecutado")
        self._ultimo: dict | None = None
        self._construir_ui()

    def _construir_ui(self) -> None:
        from ui.recursos.tema import _paleta
        p = _paleta()
        self.setStyleSheet(
            f"""
            PanelUltimoEjecutado {{
                background-color: {p.surface};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        self._titulo = QLabel("⏱  Último proceso ejecutado")
        f = QFont()
        f.setBold(True)
        f.setPointSize(13)
        f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._titulo.setFont(f)
        header_row.addWidget(self._titulo)
        header_row.addStretch()
        self._badge = QLabel("")
        header_row.addWidget(self._badge)
        layout.addLayout(header_row)

        self._proceso = QLabel("—")
        layout.addWidget(self._proceso)

        self._fecha = QLabel("")
        layout.addWidget(self._fecha)

        self._archivos_lbl = QLabel("Archivos generados:")
        layout.addWidget(self._archivos_lbl)

        self._archivos_box = QLabel("")
        self._archivos_box.setWordWrap(True)
        self._archivos_box.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._archivos_box.setMinimumHeight(60)
        layout.addWidget(self._archivos_box)

        # Botones: actualizar + ver reporte.
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_refrescar = QPushButton("↻ Refrescar")
        self._btn_refrescar.setObjectName("ghost")
        self._btn_refrescar.clicked.connect(self.refrescar)
        btn_row.addWidget(self._btn_refrescar)
        self._btn_ver = QPushButton("Ver reporte →")
        self._btn_ver.setObjectName("primary")
        self._btn_ver.clicked.connect(self._abrir_reporte)
        btn_row.addWidget(self._btn_ver)
        layout.addLayout(btn_row)

        self.refrescar()
        self._aplicar_estilos_internos()

    def _aplicar_estilos_internos(self) -> None:
        """Aplica los estilos que dependen del tema (labels internos)."""
        from ui.recursos.tema import _paleta
        p = _paleta()
        self._proceso.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {p.fg};"
        )
        self._fecha.setStyleSheet(
            f"color: {p.fg_muted}; font-size: 12px;"
        )
        self._archivos_lbl.setStyleSheet(
            f"color: {p.fg_muted}; font-size: 11px; margin-top: 12px;"
            " font-weight: 600; letter-spacing: 0.5px;"
        )
        self._archivos_box.setStyleSheet(
            f"font-family: 'Cascadia Mono', 'Consolas', monospace;"
            f" font-size: 11px; color: {p.fg};"
            f" background-color: {p.surface_alt};"
            f" border: 1px solid {p.border};"
            " border-radius: 6px; padding: 10px;"
        )
        # Reaplicar el badge actual (PRUEBA/PROD).
        if self._ultimo:
            from utils.bitacora import es_modo_prueba
            es_prueba = es_modo_prueba(self._ultimo.get("mensaje", ""))
            self._set_badge(prueba=es_prueba)

    def _set_badge(self, prueba: bool) -> None:
        if prueba:
            self._badge.setText("PRUEBA")
            self._badge.setStyleSheet(
                "background-color: #FEF3C7; color: #92400E;"
                " padding: 4px 10px; border-radius: 10px;"
                " font-size: 10px; font-weight: 700; letter-spacing: 0.5px;"
            )
        else:
            self._badge.setText("PROD")
            self._badge.setStyleSheet(
                "background-color: #DCFCE7; color: #166534;"
                " padding: 4px 10px; border-radius: 10px;"
                " font-size: 10px; font-weight: 700; letter-spacing: 0.5px;"
            )

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica estilos al cambiar de tema."""
        self.setStyleSheet(
            f"""
            PanelUltimoEjecutado {{
                background-color: {paleta.surface};
                border: 1px solid {paleta.border};
                border-radius: 12px;
            }}
            """
        )
        self._aplicar_estilos_internos()

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
            self._badge.setText("")
            self._btn_ver.setEnabled(False)
            return

        proc = self._ultimo.get("proceso", "")
        icono = ICONOS.get(proc, "▶")
        self._proceso.setText(f"{icono} {proc or '(proceso)'}")
        self._fecha.setText(f"Fecha: {self._ultimo['fecha']}")
        # Badge de modo (PRUEBA / PROD).
        from utils.bitacora import es_modo_prueba
        es_prueba = es_modo_prueba(self._ultimo.get("mensaje", ""))
        self._set_badge(prueba=es_prueba)
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
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # --- Encabezado de bienvenida ------------------------------
        titulo = QLabel(f"👋  Hola, {self._cfg.usuario or 'usuario'}")
        f = QFont()
        f.setPointSize(24)
        f.setBold(True)
        f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        titulo.setFont(f)
        layout.addWidget(titulo)

        sub = QLabel(
            "Sistema de Automatización Contable. "
            "Elegí un proceso para empezar o revisá el último que ejecutaste."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #5B6473; font-size: 13px; line-height: 1.4;")
        layout.addWidget(sub)

        # --- Grid de tarjetas --------------------------------------
        grid_lbl = QLabel("PROCESOS DISPONIBLES")
        grid_lbl.setStyleSheet(
            "color: #5B6473; font-size: 11px; font-weight: 700;"
            " letter-spacing: 1.5px; margin-top: 8px;"
        )
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
        self.setWindowTitle("ContApp · Sistema de Automatización Contable")
        self.resize(1180, 760)
        self._cfg = get_config()

        # Banner modo prueba.
        self.banner = BannerModoPrueba()

        # --- Sidebar --------------------------------------------------
        sidebar_container = QWidget()
        sidebar_container.setObjectName("sidebar_container")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Brand arriba del sidebar.
        from ui.recursos.tema import _paleta as _p
        _p_inicial = _p()
        brand = QLabel("ContApp")
        brand.setObjectName("brand_label")
        brand.setStyleSheet(
            f"font-size: 18px; font-weight: 800; letter-spacing: 1px;"
            f" padding: 18px 16px 14px 16px; color: {_p_inicial.fg};"
            f" background-color: {_p_inicial.surface};"
        )
        sidebar_layout.addWidget(brand)

        # Lista de secciones.
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        for sec in self.SECCIONES:
            icono = ICONOS_SECCION.get(sec, "")
            it = QListWidgetItem(f"  {icono}   {sec}")
            self.sidebar.addItem(it)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._cambiar_pantalla)
        sidebar_layout.addWidget(self.sidebar, 1)

        # Versión abajo del sidebar.
        version_lbl = QLabel("v1.0 · Fase 4")
        version_lbl.setObjectName("version_label")
        version_lbl.setStyleSheet(
            f"color: {_p_inicial.fg_muted}; font-size: 10px;"
            f" padding: 12px 16px; background-color: {_p_inicial.surface};"
        )
        sidebar_layout.addWidget(version_lbl)

        # --- Stack de pantallas -------------------------------------
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

        # Toggle de tema (claro/oscuro).
        self.btn_tema = QPushButton()
        self.btn_tema.setObjectName("ghost")
        self.btn_tema.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tema.setToolTip("Cambiar tema claro / oscuro")
        self.btn_tema.clicked.connect(self._toggle_tema)
        self._actualizar_btn_tema()

        # Layout central.
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.banner)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar_container)
        body.addWidget(self.stack, 1)
        layout.addLayout(body, 1)

        # Footer con separador.
        footer_container = QWidget()
        footer_container.setObjectName("footer_container")
        footer_container.setStyleSheet(
            f"background-color: {_p_inicial.surface};"
            f" border-top: 1px solid {_p_inicial.border};"
        )
        footer = QHBoxLayout(footer_container)
        footer.setContentsMargins(16, 8, 16, 8)
        footer.addWidget(self.switch)
        footer.addStretch()
        self._usuario_label = QLabel(f"  👤  {self._cfg.usuario}")
        self._usuario_label.setStyleSheet(
            f"color: {_p_inicial.fg_muted}; font-size: 12px;"
            f" padding: 0 8px; background-color: {_p_inicial.surface};"
        )
        footer.addWidget(self._usuario_label)
        footer.addSpacing(12)
        footer.addWidget(self.btn_tema)
        layout.addWidget(footer_container)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        # Guardar referencias para reaplicar tema.
        self._sidebar_container = sidebar_container
        self._footer_container = footer_container
        self._brand = brand
        self._version_lbl = version_lbl

        # FIX bug de persistencia: aplicar el tema actual al final del __init__
        # para que los containers (sidebar/footer/brand/version) tengan los
        # estilos correctos desde el primer arranque, no solo desde el primer
        # toggle. Sin esto, si el usuario persistio un tema oscuro y lo
        # reabre, el sidebar_container queda con stylesheet vacio (fondo
        # heredado del sistema = blanco/claro).
        self._aplicar_tema(_paleta())

    # -- Tema ---------------------------------------------------------

    def _toggle_tema(self) -> None:
        """Cambia entre tema claro y oscuro."""
        nuevo = "oscuro" if tema_actual() == "claro" else "claro"
        aplicar_tema(QApplication.instance(), nuevo)
        self._actualizar_btn_tema()
        # Persistir el tema elegido en disco.
        self._cfg.tema = nuevo
        self._cfg.guardar_preferencias()
        self.statusBar().showMessage(
            f"Tema {nuevo} activado", 2000,
        )

    def _actualizar_btn_tema(self) -> None:
        """Pone el icono del boton segun el modo actual."""
        if tema_actual() == "claro":
            self.btn_tema.setText("🌙  Oscuro")
        else:
            self.btn_tema.setText("☀  Claro")

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica los containers que tienen fondo hardcoded."""
        # Sidebar container.
        if hasattr(self, "_sidebar_container"):
            self._sidebar_container.setStyleSheet(
                f"background-color: {paleta.surface};"
            )
        # Footer container.
        if hasattr(self, "_footer_container"):
            self._footer_container.setStyleSheet(
                f"background-color: {paleta.surface};"
                f" border-top: 1px solid {paleta.border};"
            )
        # Brand.
        if hasattr(self, "_brand"):
            self._brand.setStyleSheet(
                f"font-size: 18px; font-weight: 800; letter-spacing: 1px;"
                f" padding: 18px 16px 14px 16px; color: {paleta.fg};"
                f" background-color: {paleta.surface};"
            )
        # Version.
        if hasattr(self, "_version_lbl"):
            self._version_lbl.setStyleSheet(
                f"color: {paleta.fg_muted}; font-size: 10px;"
                f" padding: 12px 16px; background-color: {paleta.surface};"
            )
        # Usuario label.
        if hasattr(self, "_usuario_label"):
            self._usuario_label.setStyleSheet(
                f"color: {paleta.fg_muted}; font-size: 12px;"
                f" padding: 0 8px; background-color: {paleta.surface};"
            )
        # Procesar hijos (tarjetas, dropzones, etc.).
        for w in self.findChildren(object):
            fn = getattr(w, "_aplicar_tema", None)
            if callable(fn) and w is not self:
                try:
                    fn(paleta)
                except Exception:
                    pass

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
        # Persistir el modo_prueba en disco.
        self._cfg.guardar_preferencias()
        self.statusBar().showMessage(
            "Modo prueba activado" if activo else "Modo produccion",
            3000,
        )