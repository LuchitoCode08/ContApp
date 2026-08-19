"""Pantalla de Inicio (Dashboard): bienvenida, accesos directos a procesos y estado del sistema."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import get_config
from app.version import __version__


class TarjetaProceso(QFrame):
    """Tarjeta compacta e interactiva para iniciar un proceso contable."""

    iniciar_solicitado = Signal(str)

    def __init__(
        self,
        key: str,
        icono: str,
        titulo: str,
        descripcion: str,
        extensiones: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._key = key

        self.setObjectName("card_proceso")
        self.setStyleSheet(
            """
            QFrame#card_proceso {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#card_proceso:hover {
                border-color: #93C5FD;
                background-color: #F8FAFC;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Encabezado con Icono y Tag
        header = QHBoxLayout()
        lbl_icono = QLabel(icono)
        lbl_icono.setStyleSheet("font-size: 20px; background: transparent;")
        header.addWidget(lbl_icono)

        header.addStretch(1)

        lbl_ext = QLabel(extensiones)
        lbl_ext.setStyleSheet(
            """
            background-color: #EFF6FF;
            color: #2563EB;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            """
        )
        header.addWidget(lbl_ext)
        layout.addLayout(header)

        # Título
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A; background: transparent;")
        layout.addWidget(lbl_titulo)

        # Descripción
        lbl_desc = QLabel(descripcion)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 11px; color: #64748B; background: transparent; line-height: 1.3;")
        layout.addWidget(lbl_desc, 1)

        # Botón de acción
        btn = QPushButton("Iniciar proceso →")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #F1F5F9;
                color: #2563EB;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2563EB;
                color: #FFFFFF;
                border-color: #2563EB;
            }
            """
        )
        btn.clicked.connect(lambda: self.iniciar_solicitado.emit(self._key))
        layout.addWidget(btn)


class VistaInicio(QWidget):
    """Pantalla de Inicio con panel de bienvenida, accesos directos y estado sin scroll."""

    ir_a_proceso = Signal(str)
    ir_a_diccionarios = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = get_config()

        self._construir_ui()

    def _construir_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(32, 16, 32, 16)
        layout_principal.setSpacing(14)

        # 1. Banner Hero de Bienvenida (Compacto)
        hero = self._crear_banner_hero()
        layout_principal.addWidget(hero)

        # 2. Sección: Procesos Contables
        lbl_sec_proc = QLabel("PROCESOS DISPONIBLES")
        lbl_sec_proc.setStyleSheet("font-size: 11px; font-weight: 800; color: #94A3B8; letter-spacing: 0.5px;")
        layout_principal.addWidget(lbl_sec_proc)

        grid_procesos = QGridLayout()
        grid_procesos.setSpacing(12)

        tarjeta_comprobante = TarjetaProceso(
            key="comprobante",
            icono="💳",
            titulo="Comprobante Bancolombia",
            descripcion="Procesa extractos y archivos ZIP para generar comprobantes y archivo FOAPAL consolidado.",
            extensiones=".ZIP",
        )
        tarjeta_comprobante.iniciar_solicitado.connect(self.ir_a_proceso.emit)
        grid_procesos.addWidget(tarjeta_comprobante, 0, 0)

        tarjeta_fierro = TarjetaProceso(
            key="fierro",
            icono="📊",
            titulo="Interfaz Fierro",
            descripcion="Estandarización y mapeo de auxiliares, tarjetas de crédito y descripciones contables.",
            extensiones=".XLSX / .XLS",
        )
        tarjeta_fierro.iniciar_solicitado.connect(self.ir_a_proceso.emit)
        grid_procesos.addWidget(tarjeta_fierro, 0, 1)

        tarjeta_zeus = TarjetaProceso(
            key="zeus",
            icono="⚡",
            titulo="Interfaz Zeus",
            descripcion="Depuración de cuentas de 8 a 6 dígitos y generación de archivo compatible con Zeus.",
            extensiones=".XLSX / .XLS",
        )
        tarjeta_zeus.iniciar_solicitado.connect(self.ir_a_proceso.emit)
        grid_procesos.addWidget(tarjeta_zeus, 0, 2)

        layout_principal.addLayout(grid_procesos, 1)

        # 3. Sección inferior: Acceso a Diccionarios e Información
        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(12)

        card_dicc = self._crear_tarjeta_diccionarios()
        fila_inferior.addWidget(card_dicc, 1)

        card_info = self._crear_tarjeta_info()
        fila_inferior.addWidget(card_info, 1)

        layout_principal.addLayout(fila_inferior)

    def _crear_banner_hero(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("banner_hero")
        frame.setStyleSheet(
            """
            QFrame#banner_hero {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB);
                border-radius: 12px;
            }
            """
        )

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)

        box_textos = QVBoxLayout()
        box_textos.setSpacing(2)

        lbl_saludo = QLabel("Bienvenido a ContApp")
        lbl_saludo.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF; background: transparent;")
        box_textos.addWidget(lbl_saludo)

        lbl_sub = QLabel("Automatización y procesamiento contable rápido, confiable y seguro.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #DBEAFE; background: transparent;")
        box_textos.addWidget(lbl_sub)

        layout.addLayout(box_textos, 1)

        lbl_badge = QLabel(f"Versión {__version__}")
        lbl_badge.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 0.2);
            color: #FFFFFF;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            """
        )
        layout.addWidget(lbl_badge)

        return frame

    def _crear_tarjeta_diccionarios(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card_sec")
        frame.setStyleSheet(
            """
            QFrame#card_sec {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            """
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        box_info = QVBoxLayout()
        box_info.setSpacing(2)

        lbl_titulo = QLabel("📚 Reglas y Diccionarios")
        lbl_titulo.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
        box_info.addWidget(lbl_titulo)

        lbl_desc = QLabel("Consulta o edita mapeos de cuentas, FOAPAL y reglas de integración.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 11px; color: #64748B;")
        box_info.addWidget(lbl_desc)

        layout.addLayout(box_info, 1)

        btn = QPushButton("Abrir editor →")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #FFFFFF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
                border-color: #2563EB;
            }
            """
        )
        btn.clicked.connect(self.ir_a_diccionarios.emit)
        layout.addWidget(btn)

        return frame

    def _crear_tarjeta_info(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card_sec")
        frame.setStyleSheet(
            """
            QFrame#card_sec {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            """
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        box_info = QVBoxLayout()
        box_info.setSpacing(2)

        lbl_titulo = QLabel("⚙️ Configuración del Sistema")
        lbl_titulo.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
        box_info.addWidget(lbl_titulo)

        lbl_desc = QLabel("Los resultados generados se organizan automáticamente por fecha.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 11px; color: #64748B;")
        box_info.addWidget(lbl_desc)

        layout.addLayout(box_info, 1)

        lbl_estado = QLabel("● Listo")
        lbl_estado.setStyleSheet(
            """
            background-color: #F0FDF4;
            color: #16A34A;
            border: 1px solid #BBF7D0;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 6px;
            """
        )
        layout.addWidget(lbl_estado)

        return frame
