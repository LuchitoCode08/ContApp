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

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
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
from app.version import __version__
from app.updater.checker import UpdaterChecker
from ui.recursos.tema import (
    CLARO,
    ESPACIO_MD,
    ESPACIO_LG,
    ESPACIO_SM,
    OSCURO,
    _build_palette,
    _paleta,
    _qss_global,
    aplicar_tema,
    tema_actual,
)
from ui.ventanas.dialogo_actualizacion import DialogoActualizacion
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
        self._btn_refrescar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_refrescar.clicked.connect(self.refrescar)
        btn_row.addWidget(self._btn_refrescar)
        self._btn_ver = QPushButton("Abrir carpeta →")
        self._btn_ver.setObjectName("primary")
        self._btn_ver.setCursor(Qt.CursorShape.PointingHandCursor)
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
        """Abre la carpeta del primer archivo generado en el explorador."""
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
                en_desarrollo=getattr(cls, "EN_DESARROLLO", False),
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
        self.sidebar.setMouseTracking(True)
        for sec in self.SECCIONES:
            icono = ICONOS_SECCION.get(sec, "")
            it = QListWidgetItem(f"  {icono}   {sec}")
            self.sidebar.addItem(it)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._cambiar_pantalla)
        # Cursor "mano" al pasar por encima de cada item.
        self.sidebar.viewport().setMouseTracking(True)
        self.sidebar.viewport().installEventFilter(self)
        sidebar_layout.addWidget(self.sidebar, 1)

        # Versión abajo del sidebar.
        version_lbl = QLabel(f"v{__version__}")
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
        footer.addSpacing(12)
        # Boton "Buscar actualizacion" (icono + tooltip).
        self.btn_actualizar = QPushButton("🔄  Actualizar")
        self.btn_actualizar.setObjectName("ghost")
        self.btn_actualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_actualizar.setToolTip("Buscar nueva version en GitHub")
        self.btn_actualizar.clicked.connect(self._chequear_actualizacion_manual)
        footer.addWidget(self.btn_actualizar)
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

        # Chequeo de actualizacion al iniciar (silencioso).
        self._updater_checker: UpdaterChecker | None = None
        self._updater_dialogo: DialogoActualizacion | None = None
        QTimer.singleShot(1500, self._chequear_actualizacion_al_inicio)

    # -- Tema ---------------------------------------------------------

    def _toggle_tema(self) -> None:
        """Cambia entre tema claro y oscuro (con debounce).

        En vez de aplicar el tema inmediatamente, agendamos la aplicacion
        con un QTimer de 100ms. Si el usuario togglea el tema varias veces
        seguidas (caso comun: doble click accidental o spam), las llamadas
        se acumulan en un solo repaint al final del debounce. Esto evita
        que ``aplicar_tema()`` (que recorre TODOS los widgets de la app)
        se ejecute multiples veces en pocos milisegundos.
        """
        nuevo = "oscuro" if tema_actual() == "claro" else "claro"
        # Persistir INMEDIATAMENTE para no perder el cambio si la app
        # se cierra dentro de la ventana del debounce.
        self._cfg.tema = nuevo
        self._cfg.guardar_preferencias()
        # Bumping ``_tema_version`` invalida cualquier chunk pendiente
        # del toggle anterior (asi no procesa widgets con la paleta
        # equivocada si el usuario spammea el toggle).
        self._tema_version = getattr(self, "_tema_version", 0) + 1
        # Agendar la aplicacion visual con debounce.
        if not hasattr(self, "_tema_timer") or self._tema_timer is None:
            self._tema_timer = QTimer(self)
            self._tema_timer.setSingleShot(True)
            self._tema_timer.setInterval(100)
            self._tema_timer.timeout.connect(self._aplicar_tema_diferido)
        self._tema_modo_pendiente = nuevo
        self._tema_timer.start()  # Reinicia si ya estaba corriendo.

    def _aplicar_tema_diferido(self) -> None:
        """Ejecutado por ``_tema_timer.timeout``: aplica el tema pendiente."""
        nuevo = getattr(self, "_tema_modo_pendiente", None)
        if nuevo is None:
            return
        # Actualizar el singleton global ANTES de leer la paleta, asi
        # ``_paleta()`` y ``_qss_global()`` devuelven el tema NUEVO.
        import ui.recursos.tema as tema_mod
        tema_mod._MODO = nuevo
        p = tema_mod._paleta()
        app = QApplication.instance()
        # Fase 1: QSS global + paleta (instantaneo para el usuario).
        app.setStyleSheet(_qss_global(p))
        app.setPalette(_build_palette(p))
        # Fase 2: widget-level en chunks.
        widgets_con_tema = [
            w for w in app.allWidgets()
            if callable(getattr(w, "_aplicar_tema", None))
        ]
        self._tema_widgets_pendientes = widgets_con_tema
        self._tema_chunk_size = 8
        self._tema_chunk_paleta = p
        # Capturar la version actual para que el chunk pueda detectar
        # si fue invalidado por un toggle posterior.
        self._tema_version_pendiente = getattr(self, "_tema_version", 0)
        if widgets_con_tema:
            self._aplicar_tema_siguiente_chunk()
        else:
            self._tema_chunk_paleta = None
        # Boton + status bar: instantaneo.
        self._actualizar_btn_tema()
        self.statusBar().showMessage(
            f"Tema {nuevo} activado", 2000,
        )

    def _aplicar_tema_siguiente_chunk(self) -> None:
        """Aplica el siguiente chunk de widgets con ``_aplicar_tema``.

        Si ``_tema_version`` cambio desde que se inicio este chunk,
        el toggle anterior fue reemplazado por uno nuevo: dejamos
        de procesar para no aplicar la paleta equivocada.
        """
        widgets = getattr(self, "_tema_widgets_pendientes", [])
        chunk_size = getattr(self, "_tema_chunk_size", 8)
        p = getattr(self, "_tema_chunk_paleta", None)
        # Si hubo un nuevo toggle, _tema_version incremento.
        version_actual = getattr(self, "_tema_version", 0)
        version_pendiente = getattr(self, "_tema_version_pendiente", 0)
        if version_actual != version_pendiente:
            # Cancelar: el toggle nuevo se hara cargo.
            self._tema_widgets_pendientes = []
            self._tema_chunk_paleta = None
            return
        if not widgets or p is None:
            self._tema_widgets_pendientes = []
            self._tema_chunk_paleta = None
            return
        chunk = widgets[:chunk_size]
        self._tema_widgets_pendientes = widgets[chunk_size:]
        for w in chunk:
            try:
                w._aplicar_tema(p)
            except Exception:
                pass
        if self._tema_widgets_pendientes:
            QTimer.singleShot(0, self._aplicar_tema_siguiente_chunk)
        else:
            self._tema_chunk_paleta = None

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

    def eventFilter(self, obj, event) -> bool:
        """Cambia el cursor a "mano" cuando el mouse pasa por encima
        de un item del sidebar (y vuelve a flecha cuando esta en un
        area vacia)."""
        if obj is self.sidebar.viewport():
            if event.type() == QEvent.Type.MouseMove:
                item = self.sidebar.itemAt(event.pos())
                if item is not None:
                    self.sidebar.viewport().setCursor(
                        Qt.CursorShape.PointingHandCursor
                    )
                else:
                    self.sidebar.viewport().setCursor(
                        Qt.CursorShape.ArrowCursor
                    )
            elif event.type() == QEvent.Type.Leave:
                self.sidebar.viewport().setCursor(
                    Qt.CursorShape.ArrowCursor
                )
        return super().eventFilter(obj, event)

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

    # -- Actualizacion ------------------------------------------------

    def _chequear_actualizacion_al_inicio(self) -> None:
        """Lanza un UpdaterChecker en background al arrancar la app.

        Es silencioso: si NO hay update, no pasa nada visible.
        Si hay update, muestra un dialogo modal.
        Si falla la red, no muestra nada (la app sigue funcionando).
        """
        self._lanzar_checker(mostrar_si_no_hay=False)

    def _chequear_actualizacion_manual(self) -> None:
        """Handler del boton 'Actualizar' del footer."""
        self.btn_actualizar.setEnabled(False)
        self.statusBar().showMessage("Buscando actualizaciones...", 0)
        self._lanzar_checker(mostrar_si_no_hay=True)

    def _lanzar_checker(self, mostrar_si_no_hay: bool) -> None:
        """Arranca el UpdaterChecker conectando las senales."""
        # Si ya hay uno corriendo, ignorar.
        if self._updater_checker is not None and self._updater_checker.isRunning():
            return
        self._updater_checker = UpdaterChecker(version_actual=__version__)
        self._updater_checker.terminado.connect(self._on_checker_terminado)
        self._updater_checker.error.connect(self._on_checker_error)
        self._updater_checker._mostrar_si_no_hay = mostrar_si_no_hay  # type: ignore[attr-defined]
        self._updater_checker.start()

    def _on_checker_terminado(self, release) -> None:
        self.btn_actualizar.setEnabled(True)
        self.statusBar().clearMessage()
        if release is None:
            mostrar = getattr(self._updater_checker, "_mostrar_si_no_hay", False)
            if mostrar:
                QMessageBox.information(
                    self,
                    "Sin actualizaciones",
                    f"Estas al dia. Version actual: v{__version__}",
                )
            return
        # Hay update -> abrir dialogo.
        from app.version import APP_NAME
        destino = Path.home() / "Downloads" / f"{APP_NAME}-setup.zip"
        self._updater_dialogo = DialogoActualizacion(release, destino, parent=self)
        self._updater_dialogo.show()

    def _on_checker_error(self, msg: str) -> None:
        log().warning("Updater: %s", msg)
        self.btn_actualizar.setEnabled(True)
        self.statusBar().clearMessage()
        mostrar = getattr(self._updater_checker, "_mostrar_si_no_hay", False)
        if mostrar:
            QMessageBox.warning(
                self,
                "No se pudo verificar",
                f"No se pudo consultar GitHub:\n{msg}",
            )
