"""Ventana principal de ContApp con Topbar fija y navegación por pestañas."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import get_config
from app.version import __version__
from ui.ventanas.diccionarios import VistaDiccionarios
from ui.ventanas.inicio import VistaInicio
from ui.ventanas.procesos import VistaProcesos
from ui.widgets.logo import LogoContApp
from ui.widgets.switch_modo_prueba import SwitchModoPrueba


class VentanaPrincipal(QMainWindow):
    """Ventana principal con Topbar de navegación."""

    def __init__(self) -> None:
        super().__init__()
        self._config = get_config()
        self.setWindowTitle("ContApp")
        self.resize(1080, 680)
        self.setMinimumSize(920, 580)

        self._construir_ui()

    def _construir_ui(self) -> None:
        # Widget contenedor central
        contenedor = QWidget()
        layout_principal = QVBoxLayout(contenedor)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # 1. Topbar
        topbar = self._crear_topbar()
        layout_principal.addWidget(topbar)

        # 2. Área de contenido dinámico (QStackedWidget)
        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")

        # Páginas
        self._pag_inicio = VistaInicio()
        self._pag_inicio.ir_a_proceso.connect(self._navegar_a_proceso)
        self._pag_inicio.ir_a_diccionarios.connect(lambda: self._seleccionar_tab(2))

        self._pag_procesos = VistaProcesos()
        self._pag_diccionarios = VistaDiccionarios()

        self._stack.addWidget(self._pag_inicio)
        self._stack.addWidget(self._pag_procesos)
        self._stack.addWidget(self._pag_diccionarios)

        layout_principal.addWidget(self._stack)
        self.setCentralWidget(contenedor)

        # Seleccionar Inicio por defecto
        self._seleccionar_tab(0)

    def _navegar_a_proceso(self, key: str) -> None:
        self._seleccionar_tab(1)
        self._pag_procesos._seleccionar_proceso(key)

    def _crear_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("topbar")

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(16)

        # --- Izquierda: Logo y Nombre ---
        self._logo = LogoContApp()
        layout.addWidget(self._logo)
        layout.addStretch(1)

        # --- Centro: Pestañas de Navegación ---
        box_tabs = QHBoxLayout()
        box_tabs.setSpacing(8)

        self._btn_inicio = QPushButton("INICIO")
        self._btn_inicio.setObjectName("tab_btn")
        self._btn_inicio.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_inicio.clicked.connect(lambda: self._seleccionar_tab(0))

        self._btn_procesos = QPushButton("PROCESOS")
        self._btn_procesos.setObjectName("tab_btn")
        self._btn_procesos.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_procesos.clicked.connect(lambda: self._seleccionar_tab(1))

        self._btn_diccionarios = QPushButton("DICCIONARIOS")
        self._btn_diccionarios.setObjectName("tab_btn")
        self._btn_diccionarios.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_diccionarios.clicked.connect(lambda: self._seleccionar_tab(2))

        self._tab_buttons = [self._btn_inicio, self._btn_procesos, self._btn_diccionarios]

        for btn in self._tab_buttons:
            box_tabs.addWidget(btn)

        layout.addLayout(box_tabs)
        layout.addStretch(1)

        # --- Derecha: Switch Modo Prueba ---
        self._switch_modo_prueba = SwitchModoPrueba()
        self._switch_modo_prueba.set_activo(self._config.modo_prueba)
        self._switch_modo_prueba.modo_prueba_cambiado.connect(self._on_modo_prueba_cambiado)
        layout.addWidget(self._switch_modo_prueba)

        return topbar

    def _seleccionar_tab(self, indice: int) -> None:
        self._stack.setCurrentIndex(indice)
        for i, btn in enumerate(self._tab_buttons):
            activo = (i == indice)
            btn.setProperty("active", "true" if activo else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_modo_prueba_cambiado(self, activo: bool) -> None:
        self._config.modo_prueba = activo
        self._config.guardar_preferencias()


