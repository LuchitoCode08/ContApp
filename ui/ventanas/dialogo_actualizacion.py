"""Dialogo modal que muestra info de una actualizacion disponible.

Permite al usuario:
    - Ver las notas de la version (markdown -> texto plano).
    - Iniciar la descarga (con barra de progreso).
    - Cancelar la descarga en curso.
    - Abrir la pagina del release en GitHub.

Emite ``descarga_iniciada`` cuando arranca.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.version import __version__
from app.updater.downloader import UpdaterDownloader
from app.updater.version_utils import ReleaseInfo

if TYPE_CHECKING:
    pass


class DialogoActualizacion(QDialog):
    """Modal que muestra info de un release y maneja la descarga."""

    descarga_iniciada = Signal()

    def __init__(
        self,
        release: ReleaseInfo,
        destino: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._release = release
        self._destino = destino
        self._downloader: UpdaterDownloader | None = None

        self.setWindowTitle(f"Actualizacion disponible · v{release['version']}")
        self.setModal(True)
        self.resize(540, 480)

        self._build_ui()
        self._aplicar_estilo()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Encabezado: version actual -> version nueva.
        self._lbl_titulo = QLabel(
            f"<b>Hay una nueva version de ContApp</b><br>"
            f"<span style='color:#666'>Tu version: v{__version__} → "
            f"Nueva version: <b>v{self._release['version']}</b></span>"
        )
        self._lbl_titulo.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._lbl_titulo)

        # Link a la pagina del release.
        self._lbl_link = QLabel(
            f'<a href="{self._release["html_url"]}">Ver release en GitHub</a>'
        )
        self._lbl_link.setTextFormat(Qt.TextFormat.RichText)
        self._lbl_link.setOpenExternalLinks(True)
        layout.addWidget(self._lbl_link)

        # Notas de la version (markdown -> html basico).
        layout.addWidget(QLabel("Notas de la version:"))
        self._notas = QTextBrowser()
        self._notas.setOpenExternalLinks(True)
        self._notas.setHtml(self._markdown_a_html(self._release["body"]))
        layout.addWidget(self._notas, 1)

        # Barra de progreso (oculta hasta que arranca la descarga).
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._lbl_estado = QLabel("")
        layout.addWidget(self._lbl_estado)

        # Botones.
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_cancelar_dialogo = QPushButton("Mas tarde")
        self._btn_cancelar_dialogo.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_cancelar_dialogo)

        btn_row.addStretch()

        self._btn_cancelar_descarga = QPushButton("Cancelar descarga")
        self._btn_cancelar_descarga.clicked.connect(self._cancelar_descarga)
        self._btn_cancelar_descarga.hide()
        btn_row.addWidget(self._btn_cancelar_descarga)

        self._btn_descargar = QPushButton("Descargar e instalar")
        self._btn_descargar.setObjectName("primary")
        self._btn_descargar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_descargar.clicked.connect(self._iniciar_descarga)
        btn_row.addWidget(self._btn_descargar)

        layout.addLayout(btn_row)

    def _aplicar_estilo(self) -> None:
        """Aplica estilos minimos (los colores vienen del tema global)."""
        self._lbl_estado.setStyleSheet("color: #666; font-size: 11px;")

    # ------------------------------------------------------------------
    # Markdown basico -> HTML
    # ------------------------------------------------------------------

    @staticmethod
    def _markdown_a_html(texto: str) -> str:
        """Markdown muy basico -> HTML para QTextBrowser.

        Soporta: # titulos, - listas, ``code``, **bold**, links [t](u).
        Para releases cortos alcanza; no es un renderer completo.
        """
        if not texto:
            return "<i>(sin notas)</i>"
        out: list[str] = []
        in_list = False
        for ln in texto.splitlines():
            ln_stripped = ln.strip()
            if ln_stripped.startswith("# "):
                if in_list:
                    out.append("</ul>"); in_list = False
                out.append(f"<h3>{_esc(ln_stripped[2:])}</h3>")
            elif ln_stripped.startswith("## "):
                if in_list:
                    out.append("</ul>"); in_list = False
                out.append(f"<h4>{_esc(ln_stripped[3:])}</h4>")
            elif ln_stripped.startswith("- "):
                if not in_list:
                    out.append("<ul>"); in_list = True
                out.append(f"<li>{_esc(ln_stripped[2:])}</li>")
            elif ln_stripped == "":
                if in_list:
                    out.append("</ul>"); in_list = False
                out.append("<br>")
            else:
                if in_list:
                    out.append("</ul>"); in_list = False
                out.append(f"<p>{_esc(ln_stripped)}</p>")
        if in_list:
            out.append("</ul>")
        return "\n".join(out)

    # ------------------------------------------------------------------
    # Descarga
    # ------------------------------------------------------------------

    def _iniciar_descarga(self) -> None:
        """Arranca el UpdaterDownloader y conecta las senales."""
        self._btn_descargar.hide()
        self._btn_cancelar_dialogo.hide()
        self._btn_cancelar_descarga.show()
        self._progress.show()
        self._lbl_estado.setText("Iniciando descarga...")

        self._downloader = UpdaterDownloader(
            url=self._release["asset_url"],
            destino=self._destino,
        )
        self._downloader.progreso.connect(self._on_progreso)
        self._downloader.terminado.connect(self._on_terminado)
        self._downloader.error.connect(self._on_error)
        self._downloader.start()
        self.descarga_iniciada.emit()

    def _cancelar_descarga(self) -> None:
        if self._downloader is not None:
            self._downloader.cancelar()

    def _on_progreso(self, pct: int) -> None:
        self._progress.setValue(pct)
        self._lbl_estado.setText(f"Descargando... {pct}%")

    def _on_terminado(self, ruta: Path) -> None:
        self._lbl_estado.setText(f"[OK] Descargado: {ruta.name}")
        self._btn_cancelar_descarga.hide()
        # Ofrecer abrir el archivo.
        self._btn_descargar.setText("Abrir instalador")
        self._btn_descargar.clicked.disconnect()
        self._btn_descargar.clicked.connect(lambda: self._abrir_instalador(ruta))
        self._btn_descargar.show()
        self._btn_cancelar_dialogo.setText("Cerrar")
        self._btn_cancelar_dialogo.show()

    def _on_error(self, msg: str) -> None:
        self._lbl_estado.setText(f"[FAIL] {msg}")
        self._btn_cancelar_descarga.hide()
        self._btn_descargar.setText("Reintentar")
        self._btn_descargar.show()
        self._btn_cancelar_dialogo.show()

    def _abrir_instalador(self, ruta: Path) -> None:
        """Abre el archivo .zip con la app por defecto del SO."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))
        self.accept()


def _esc(s: str) -> str:
    """Escape HTML basico."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )