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

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.config import get_config
from ui.widgets.banner_modo_prueba import BannerModoPrueba
from ui.widgets.switch_modo_prueba import SwitchModoPrueba


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
        self.stack = QStackedWidget()
        self._pantallas = [
            self._crear_pantalla_inicio(),
            self._crear_pantalla_procesos(),
            self._crear_pantalla_diccionarios(),
            self._crear_pantalla_configuracion(),
        ]
        for p in self._pantallas:
            self.stack.addWidget(p)

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

    # -- Manejo de pantallas ------------------------------------------

    def _cambiar_pantalla(self, idx: int) -> None:
        if 0 <= idx < self.stack.count():
            self.stack.setCurrentIndex(idx)

    # -- Pantallas (stubs por ahora) ----------------------------------

    def _crear_pantalla_inicio(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        titulo = QLabel("Bienvenido a ContApp")
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        titulo.setFont(f)
        layout.addWidget(titulo)
        layout.addSpacing(20)
        sub = QLabel(
            "Sistema de Automatizacion Contable.\n\n"
            "Usa el panel izquierdo para navegar entre las secciones."
        )
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addStretch()
        return w

    def _crear_pantalla_procesos(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<h2>Procesos</h2>"))
        layout.addWidget(QLabel(
            "Aqui podras ejecutar los 3 procesos (Comprobante, Fierro, Zeus)."
        ))
        layout.addStretch()
        return w

    def _crear_pantalla_diccionarios(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<h2>Diccionarios</h2>"))
        layout.addWidget(QLabel(
            "Editor inteligente de los 8 JSONs del sistema."
        ))
        layout.addStretch()
        return w

    def _crear_pantalla_configuracion(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<h2>Configuracion</h2>"))
        layout.addWidget(QLabel(
            "Aqui se mostrara la bitacora de actividad."
        ))
        layout.addStretch()
        return w

    # -- Modo prueba --------------------------------------------------

    def _on_modo_prueba(self, activo: bool) -> None:
        self._cfg.modo_prueba = activo
        self.banner.set_activo(activo)
        self.statusBar().showMessage(
            "Modo prueba activado" if activo else "Modo produccion",
            3000,
        )