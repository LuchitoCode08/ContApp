"""Sistema de diseño y tema visual de ContApp (Modo Claro)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class Paleta:
    bg: str            # Fondo de ventana
    surface: str       # Superficies / tarjetas / topbar
    surface_alt: str   # Hover suave / filas alternas
    border: str        # Bordes sutiles
    border_strong: str # Bordes destacados / foco

    fg: str            # Texto principal
    fg_muted: str      # Texto secundario
    fg_disabled: str   # Texto deshabilitado

    primary: str       # Color primario / de marca
    primary_hover: str
    primary_pressed: str
    on_primary: str    # Texto sobre color primario

    success: str
    on_success: str
    warning: str
    on_warning: str
    danger: str
    on_danger: str


CLARO = Paleta(
    bg="#F8FAFC",
    surface="#FFFFFF",
    surface_alt="#F1F5F9",
    border="#E2E8F0",
    border_strong="#2563EB",

    fg="#0F172A",
    fg_muted="#64748B",
    fg_disabled="#94A3B8",

    primary="#2563EB",
    primary_hover="#1D4ED8",
    primary_pressed="#1E40AF",
    on_primary="#FFFFFF",

    success="#16A34A",
    on_success="#FFFFFF",
    warning="#F59E0B",
    on_warning="#0F172A",
    danger="#DC2626",
    on_danger="#FFFFFF",
)

FUENTE_FAMILIA = '"Segoe UI Variable", "Segoe UI", "Inter", system-ui, sans-serif'
FUENTE_MONO = '"Cascadia Mono", "Consolas", "JetBrains Mono", monospace'


def _paleta() -> Paleta:
    return CLARO


def _qss_global(p: Paleta) -> str:
    return f"""
    /* ------- Base ------- */
    QWidget {{
        background-color: {p.bg};
        color: {p.fg};
        font-family: {FUENTE_FAMILIA};
        font-size: 13px;
    }}

    QFrame {{
        background-color: transparent;
    }}

    /* ------- Topbar ------- */
    QFrame#topbar {{
        background-color: {p.surface};
        border-bottom: 1px solid {p.border};
        min-height: 58px;
        max-height: 58px;
    }}

    /* ------- Tabs de Navegación en Topbar ------- */
    QPushButton#tab_btn {{
        background-color: transparent;
        color: {p.fg_muted};
        border: none;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 8px 18px;
        min-height: 20px;
    }}
    QPushButton#tab_btn:hover {{
        background-color: {p.surface_alt};
        color: {p.fg};
    }}
    QPushButton#tab_btn[active="true"] {{
        background-color: {p.primary};
        color: {p.on_primary};
    }}

    /* ------- Logo y Título ------- */
    QLabel#app_title {{
        color: {p.fg};
        font-size: 16px;
        font-weight: 800;
        letter-spacing: 1px;
    }}
    QLabel#app_badge {{
        background-color: {p.primary};
        color: {p.on_primary};
        font-size: 12px;
        font-weight: 800;
        border-radius: 6px;
        padding: 4px 8px;
    }}

    /* ------- Tipografía ------- */
    QLabel#h1 {{
        font-size: 22px;
        font-weight: 700;
        color: {p.fg};
    }}
    QLabel#h2 {{
        font-size: 17px;
        font-weight: 600;
        color: {p.fg};
    }}
    QLabel#muted {{
        color: {p.fg_muted};
        font-size: 13px;
    }}

    /* ------- Botones ------- */
    QPushButton {{
        background-color: {p.surface};
        color: {p.fg};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {p.surface_alt};
        border-color: {p.border_strong};
    }}
    QPushButton:pressed {{
        background-color: {p.border};
    }}
    QPushButton:disabled {{
        background-color: {p.surface_alt};
        color: {p.fg_disabled};
        border-color: {p.border};
    }}

    QPushButton#primary {{
        background-color: {p.primary};
        color: {p.on_primary};
        border: 1px solid {p.primary};
    }}
    QPushButton#primary:hover {{
        background-color: {p.primary_hover};
        border-color: {p.primary_hover};
    }}
    QPushButton#primary:pressed {{
        background-color: {p.primary_pressed};
        border-color: {p.primary_pressed};
    }}

    /* ------- Tarjetas y Paneles ------- */
    QFrame#card {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 12px;
    }}

    /* ------- Scrollbars ------- */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.fg_disabled};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """


def aplicar_tema(app: QApplication, modo: Literal["claro"] = "claro") -> None:
    """Aplica el tema claro global."""
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    p = _paleta()
    app.setStyleSheet(_qss_global(p))