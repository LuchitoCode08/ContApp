"""Sistema de diseño central de ContApp.

Define:
- Paleta clara y oscura (colores base, marca, semantica, escala neutra).
- Escala tipografica (Segoe UI Variable con fallbacks).
- Espaciado, radios, elevacion.
- Funcion ``aplicar_tema(app, modo)`` que setea un QSS global coherente.
- Funcion ``tema_actual()`` para consultar el modo activo.

Pensado para que TODA la UI use estos tokens en lugar de hardcodear
colores / fonts / espacios. Asi un cambio de tema se propaga en un solo
lugar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QApplication

# ============================================================
# Paletas
# ============================================================

@dataclass(frozen=True)
class Paleta:
    bg: str            # fondo de la ventana
    surface: str       # cards, paneles
    surface_alt: str   # filas alternadas en tablas, hover suave
    border: str        # bordes sutiles
    border_strong: str # bordes de foco / hover

    fg: str            # texto principal
    fg_muted: str      # texto secundario
    fg_disabled: str   # texto deshabilitado

    primary: str       # color de marca
    primary_hover: str
    primary_pressed: str
    on_primary: str    # texto sobre primary

    success: str
    on_success: str
    warning: str
    on_warning: str
    danger: str
    on_danger: str

    accent_comprobante: str
    accent_fierro: str
    accent_zeus: str


CLARO = Paleta(
    bg="#F6F7FB",
    surface="#FFFFFF",
    surface_alt="#F2F4F8",
    border="#E1E5EC",
    border_strong="#1976D2",

    fg="#1A1F2C",
    fg_muted="#5B6473",
    fg_disabled="#A8AEBA",

    primary="#2563EB",          # azul moderno
    primary_hover="#1D4FD7",
    primary_pressed="#1740B5",
    on_primary="#FFFFFF",

    success="#16A34A",
    on_success="#FFFFFF",
    warning="#F59E0B",
    on_warning="#1A1F2C",
    danger="#DC2626",
    on_danger="#FFFFFF",

    accent_comprobante="#0EA5E9",  # sky
    accent_fierro="#F97316",       # orange
    accent_zeus="#A855F7",         # purple
)


OSCURO = Paleta(
    bg="#0F1320",
    surface="#171C2C",
    surface_alt="#1F2638",
    border="#2A3146",
    border_strong="#60A5FA",

    fg="#E7EBF3",
    fg_muted="#9AA4B5",
    fg_disabled="#525B6E",

    primary="#3B82F6",
    primary_hover="#60A5FA",
    primary_pressed="#1D4FD7",
    on_primary="#FFFFFF",

    success="#22C55E",
    on_success="#0F1320",
    warning="#FBBF24",
    on_warning="#0F1320",
    danger="#EF4444",
    on_danger="#0F1320",

    accent_comprobante="#38BDF8",
    accent_fierro="#FB923C",
    accent_zeus="#C084FC",
)


# ============================================================
# Tokens adicionales
# ============================================================

ESPACIO_XS = 4
ESPACIO_SM = 8
ESPACIO_MD = 12
ESPACIO_LG = 16
ESPACIO_XL = 24
ESPACIO_XXL = 32

RADIO_SM = 6
RADIO_MD = 10
RADIO_LG = 14

FUENTE_FAMILIA = '"Segoe UI Variable", "Segoe UI", "Inter", system-ui, sans-serif'
FUENTE_MONO = '"Cascadia Mono", "Consolas", "JetBrains Mono", monospace'


# Pesos y tamanos (escala tipografica).
TIPO_H1 = 22
TIPO_H2 = 16
TIPO_H3 = 14
TIPO_BODY = 13
TIPO_CAPTION = 11
TIPO_BTN = 13


# ============================================================
# Estado del tema (singleton)
# ============================================================

_MODO: Literal["claro", "oscuro"] = "claro"


def tema_actual() -> Literal["claro", "oscuro"]:
    """Devuelve el modo de tema actualmente aplicado."""
    return _MODO


def _paleta() -> Paleta:
    return CLARO if _MODO == "claro" else OSCURO


# ============================================================
# QSS global
# ============================================================

def _qss_global(p: Paleta) -> str:
    """Devuelve la hoja de estilos global (QApplication)."""
    return f"""
    /* ------- Base ------- */
    QWidget {{
        background-color: {p.bg};
        color: {p.fg};
        font-family: {FUENTE_FAMILIA};
        font-size: {TIPO_BODY}px;
    }}

    QFrame {{
        background-color: transparent;
    }}

    /* ------- Sidebar (panel) ------- */
    QListWidget#sidebar {{
        background-color: {p.surface};
        border: none;
        border-right: 1px solid {p.border};
        outline: 0;
        padding: {ESPACIO_SM}px 0;
    }}
    QListWidget#sidebar::item {{
        height: 44px;
        padding: 0 {ESPACIO_LG}px;
        margin: 2px {ESPACIO_SM}px;
        border-radius: {RADIO_MD}px;
        color: {p.fg_muted};
        font-size: {TIPO_BODY}px;
    }}
    QListWidget#sidebar::item:hover {{
        background-color: {p.surface_alt};
        color: {p.fg};
    }}
    QListWidget#sidebar::item:selected {{
        background-color: {p.primary};
        color: {p.on_primary};
        font-weight: 600;
    }}

    /* ------- Labels ------- */
    QLabel#h1 {{
        font-size: {TIPO_H1}px;
        font-weight: 700;
        color: {p.fg};
    }}
    QLabel#h2 {{
        font-size: {TIPO_H2}px;
        font-weight: 600;
        color: {p.fg};
    }}
    QLabel#h3 {{
        font-size: {TIPO_H3}px;
        font-weight: 600;
        color: {p.fg};
    }}
    QLabel#muted {{
        color: {p.fg_muted};
        font-size: {TIPO_BODY}px;
    }}
    QLabel#caption {{
        color: {p.fg_muted};
        font-size: {TIPO_CAPTION}px;
    }}
    QLabel#mono {{
        font-family: {FUENTE_MONO};
        font-size: {TIPO_CAPTION}px;
        color: {p.fg};
    }}

    /* ------- Botones ------- */
    QPushButton {{
        background-color: {p.surface};
        color: {p.fg};
        border: 1px solid {p.border};
        border-radius: {RADIO_MD}px;
        padding: 8px {ESPACIO_LG}px;
        font-weight: 500;
        min-height: 18px;
    }}
    QPushButton:hover {{
        background-color: {p.surface_alt};
        border-color: {p.border_strong};
    }}
    QPushButton:pressed {{
        background-color: {p.border};
    }}
    QPushButton:disabled {{
        color: {p.fg_disabled};
        background-color: {p.surface};
    }}
    QPushButton#primary {{
        background-color: {p.primary};
        color: {p.on_primary};
        border: none;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{
        background-color: {p.primary_hover};
    }}
    QPushButton#primary:pressed {{
        background-color: {p.primary_pressed};
    }}
    QPushButton#ghost {{
        background-color: transparent;
        border: none;
        color: {p.fg_muted};
    }}
    QPushButton#ghost:hover {{
        background-color: {p.surface_alt};
        color: {p.fg};
    }}
    QPushButton#secondary {{
        background-color: {p.surface_alt};
        color: {p.primary};
        border: 1px solid {p.primary};
        border-radius: {RADIO_MD}px;
        padding: 6px {ESPACIO_MD}px;
        font-weight: 600;
    }}
    QPushButton#secondary:hover {{
        background-color: {p.primary};
        color: {p.on_primary};
    }}
    QPushButton#secondary:pressed {{
        background-color: {p.primary_pressed};
        color: {p.on_primary};
    }}

    /* ------- Inputs ------- */
    QLineEdit, QComboBox, QDateEdit, QSpinBox {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: {RADIO_MD}px;
        padding: 6px {ESPACIO_MD}px;
        color: {p.fg};
        selection-background-color: {p.primary};
        selection-color: {p.on_primary};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {{
        border-color: {p.primary};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    /* ------- Tablas ------- */
    QTableWidget, QTableView, QTreeWidget {{
        background-color: {p.surface};
        alternate-background-color: {p.surface_alt};
        gridline-color: {p.border};
        border: 1px solid {p.border};
        border-radius: {RADIO_MD}px;
        selection-background-color: {p.primary};
        selection-color: {p.on_primary};
        outline: 0;
    }}
    QHeaderView::section {{
        background-color: {p.surface_alt};
        color: {p.fg};
        padding: {ESPACIO_SM}px {ESPACIO_MD}px;
        border: none;
        border-right: 1px solid {p.border};
        border-bottom: 1px solid {p.border};
        font-weight: 600;
    }}

    /* ------- ProgressBar ------- */
    QProgressBar {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: {RADIO_MD}px;
        text-align: center;
        color: {p.fg};
        min-height: 18px;
    }}
    QProgressBar::chunk {{
        background-color: {p.primary};
        border-radius: {RADIO_MD}px;
    }}

    /* ------- StatusBar ------- */
    QStatusBar {{
        background-color: {p.surface};
        color: {p.fg_muted};
        border-top: 1px solid {p.border};
    }}

    /* ------- Splitter ------- */
    QSplitter::handle {{
        background-color: {p.border};
    }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical {{ height: 1px; }}

    /* ------- ScrollBar (delgada y discreta) ------- */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.fg_disabled};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.border};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {p.fg_disabled};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ------- Tooltips ------- */
    QToolTip {{
        background-color: {p.surface};
        color: {p.fg};
        border: 1px solid {p.border};
        border-radius: {RADIO_SM}px;
        padding: 6px {ESPACIO_SM}px;
    }}
    """


# ============================================================
# API publica
# ============================================================

def aplicar_tema(app: QApplication, modo: Literal["claro", "oscuro"]) -> None:
    """Aplica el tema a toda la aplicacion (QSS + fuente + repintado)."""
    global _MODO
    _MODO = modo

    p = _paleta()
    app.setStyleSheet(_qss_global(p))

    # Fuente default (Segoe UI Variable con fallback).
    familia = FUENTE_FAMILIA.strip('"')
    base_font = QFont(familia.split(",")[0].strip().strip('"'))
    base_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    base_font.setPointSize(TIPO_BODY)
    app.setFont(base_font)

    # Paleta Qt (afecta dialogos nativos y QMessageBox).
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, _color(p.bg))
    pal.setColor(QPalette.ColorRole.WindowText, _color(p.fg))
    pal.setColor(QPalette.ColorRole.Base, _color(p.surface))
    pal.setColor(QPalette.ColorRole.AlternateBase, _color(p.surface_alt))
    pal.setColor(QPalette.ColorRole.Text, _color(p.fg))
    pal.setColor(QPalette.ColorRole.Button, _color(p.surface))
    pal.setColor(QPalette.ColorRole.ButtonText, _color(p.fg))
    pal.setColor(QPalette.ColorRole.Highlight, _color(p.primary))
    pal.setColor(QPalette.ColorRole.HighlightedText, _color(p.on_primary))
    pal.setColor(QPalette.ColorRole.PlaceholderText, _color(p.fg_disabled))
    app.setPalette(pal)

    # Repintar todos los widgets que tengan un metodo _aplicar_tema(p).
    for w in app.allWidgets():
        aplicar_a_widget(w, p)


def aplicar_a_widget(widget, p: Paleta) -> None:
    """Si el widget expone ``_aplicar_tema(paleta)``, lo invoca recursivamente.

    Patron de uso: cualquier widget que tenga colores hardcoded en su
    ``setStyleSheet`` debe implementar ``_aplicar_tema(self, paleta)`` para
    actualizarse al cambiar de tema. Los colores que dependen del proceso
    deben pasarse por parametro (ej: ``color_proceso(nombre)``).
    """
    fn = getattr(widget, "_aplicar_tema", None)
    if callable(fn):
        try:
            fn(p)
        except Exception:
            pass
    # Recursion a hijos.
    for child in widget.findChildren(object):
        fn2 = getattr(child, "_aplicar_tema", None)
        if callable(fn2):
            try:
                fn2(p)
            except Exception:
                pass


def _color(hex_str: str):
    """Convierte un hex (#RRGGBB) a QColor."""
    from PySide6.QtGui import QColor
    return QColor(hex_str)


def color_proceso(nombre: str) -> str:
    """Devuelve el color de acento para un proceso (claro u oscuro)."""
    p = _paleta()
    return {
        "comprobante": p.accent_comprobante,
        "fierro": p.accent_fierro,
        "zeus": p.accent_zeus,
    }.get(nombre, p.primary)