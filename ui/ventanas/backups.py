"""Pantalla Copias de seguridad: listar y restaurar backups de JSONs.

Muestra todos los backups existentes agrupados por proceso, permite
restaurar el seleccionado y abrir la carpeta donde se guardan.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import DATA_DIR, JSONS_DIR, get_config
from services.backup_service import BackupService
from utils.bitacora import log
from utils.json_manager import con_lock, leer_json


# Nombres legibles para los procesos.
NOMBRES_PROCESO: dict[str, str] = {
    "comprobante": "Comprobante",
    "fierro": "Fierro",
    "zeus": "Zeus",
}


def _nombre_proceso(codigo: str) -> str:
    return NOMBRES_PROCESO.get(codigo, codigo.capitalize())


def _formatear_fecha(path: Path) -> str:
    """Devuelve la fecha de modificacion legible."""
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return "—"


def _ruta_original_desde_backup(backup: Path) -> Path | None:
    """Deriva la ruta del JSON original a partir de la ruta del backup.

    Los backups se organizan como ``data/backups/<proceso>/<archivo>.json``
    y los originales como ``jsons/<proceso>/<archivo>.json``.
    """
    try:
        rel = backup.relative_to(DATA_DIR / "backups")
        partes = rel.parts
        if len(partes) < 2:
            return None
        proceso = partes[0]
        archivo = partes[1]
        return JSONS_DIR / proceso / archivo
    except ValueError:
        return None


class PantallaBackups(QWidget):
    """Gestor de copias de seguridad de los JSONs del sistema."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = get_config()
        self._svc = BackupService(carpeta_backups=DATA_DIR / "backups")
        self._items: list[tuple[QTreeWidgetItem, Path, Path | None]] = []
        self._construir_ui()
        self.refrescar()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        titulo = QLabel("🛡  Copias de seguridad")
        titulo.setStyleSheet(
            "font-size: 22px; font-weight: 700; padding-bottom: 4px;"
        )
        layout.addWidget(titulo)

        sub = QLabel(
            "Aca podes ver los backups automaticos de los JSONs y restaurar"
            " cualquiera a su estado anterior."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #5B6473; font-size: 13px;")
        layout.addWidget(sub)

        # --- Arbol de backups ----------------------------------------
        self._arbol = QTreeWidget()
        self._arbol.setHeaderLabels(["Proceso", "Archivo", "Fecha del backup"])
        self._arbol.setColumnWidth(0, 140)
        self._arbol.setColumnWidth(1, 320)
        self._arbol.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._arbol.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._arbol.setAlternatingRowColors(True)
        self._arbol.itemSelectionChanged.connect(self._on_seleccion_cambiada)
        self._arbol.itemExpanded.connect(self._on_expandir_seccion)
        layout.addWidget(self._arbol, 1)

        # --- Footer de acciones --------------------------------------
        footer = QHBoxLayout()
        self._lbl_total = QLabel("0 copias de seguridad")
        footer.addWidget(self._lbl_total)
        footer.addStretch()

        self.btn_abrir_carpeta = QPushButton("📂  Abrir carpeta")
        self.btn_abrir_carpeta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abrir_carpeta.clicked.connect(self._abrir_carpeta)
        footer.addWidget(self.btn_abrir_carpeta)

        self.btn_restaurar = QPushButton("↩  Restaurar seleccionado")
        self.btn_restaurar.setObjectName("primary")
        self.btn_restaurar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restaurar.clicked.connect(self._restaurar_seleccionado)
        self.btn_restaurar.setEnabled(False)
        footer.addWidget(self.btn_restaurar)

        layout.addLayout(footer)

        self._aplicar_tema(self._tema_actual())

    def _tema_actual(self):
        from ui.recursos.tema import _paleta
        return _paleta()

    def _aplicar_tema(self, paleta) -> None:
        """Reaplica estilos al cambiar de tema."""
        if hasattr(self, "_arbol") and self._arbol is not None:
            self._arbol.setStyleSheet(
                f"QTreeWidget {{ background-color: {paleta.surface};"
                f" alternate-background-color: {paleta.surface_alt};"
                f" color: {paleta.fg};"
                f" gridline-color: {paleta.border};"
                f" border: 1px solid {paleta.border};"
                f" border-radius: 10px; }}"
            )
            from PySide6.QtGui import QColor
            sec_bg = QColor(paleta.surface_alt)
            fg = QColor(paleta.fg)
            for i in range(self._arbol.topLevelItemCount()):
                sec = self._arbol.topLevelItem(i)
                sec.setBackground(0, sec_bg)
                sec.setForeground(0, fg)
                for j in range(sec.childCount()):
                    child = sec.child(j)
                    for c in range(child.columnCount()):
                        child.setForeground(c, fg)

    def refrescar(self) -> None:
        """Recarga la lista de backups desde disco."""
        self._arbol.clear()
        self._items.clear()

        backups = self._svc.listar_backups()
        if not backups:
            self._lbl_total.setText("Sin copias de seguridad")
            return

        # Agrupar por proceso.
        agrupados: dict[str, list[Path]] = {}
        for b in backups:
            try:
                rel = b.relative_to(self._svc.carpeta_backups)
                proceso = rel.parts[0] if rel.parts else "otros"
            except ValueError:
                proceso = "otros"
            agrupados.setdefault(proceso, []).append(b)

        total = 0
        for proceso in sorted(agrupados.keys()):
            seccion = QTreeWidgetItem([_nombre_proceso(proceso), "", ""])
            font = QFont()
            font.setBold(True)
            seccion.setFont(0, font)
            seccion.setData(0, Qt.ItemDataRole.UserRole, proceso)
            # Seccion no seleccionable.
            seccion.setFlags(seccion.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._arbol.addTopLevelItem(seccion)

            for backup in sorted(agrupados[proceso], key=lambda p: p.name):
                ruta_original = _ruta_original_desde_backup(backup)
                item = QTreeWidgetItem([
                    "",
                    backup.name,
                    _formatear_fecha(backup),
                ])
                item.setData(0, Qt.ItemDataRole.UserRole, str(backup))
                item.setData(
                    1, Qt.ItemDataRole.UserRole,
                    str(ruta_original) if ruta_original else "",
                )
                item.setToolTip(
                    1,
                    f"Original: {ruta_original}\nBackup: {backup}"
                    if ruta_original
                    else f"Backup: {backup}",
                )
                seccion.addChild(item)
                self._items.append((item, backup, ruta_original))
                total += 1

            seccion.setExpanded(True)

        self._lbl_total.setText(f"{total} copia(s) de seguridad")
        self._on_seleccion_cambiada()

    def _on_expandir_seccion(self, item: QTreeWidgetItem) -> None:
        """Reaplica color de seccion al expandir."""
        from ui.recursos.tema import _paleta
        p = _paleta()
        item.setBackground(0, QColor(p.surface_alt))
        item.setForeground(0, QColor(p.fg))

    def _on_seleccion_cambiada(self) -> None:
        items = self._arbol.selectedItems()
        if not items:
            self.btn_restaurar.setEnabled(False)
            return
        item = items[0]
        # Solo habilitar si es un item hoja (no seccion).
        habilitar = item.parent() is not None
        self.btn_restaurar.setEnabled(habilitar)

    def _backup_seleccionado(self) -> tuple[Path, Path | None] | None:
        items = self._arbol.selectedItems()
        if not items:
            return None
        item = items[0]
        if item.parent() is None:
            return None
        backup_str = item.data(0, Qt.ItemDataRole.UserRole)
        original_str = item.data(1, Qt.ItemDataRole.UserRole)
        if not backup_str:
            return None
        return Path(backup_str), Path(original_str) if original_str else None

    def _abrir_carpeta(self) -> None:
        """Abre la carpeta de backups en el explorador."""
        carpeta = self._svc.carpeta_backups
        if not carpeta.exists():
            QMessageBox.information(
                self,
                "Sin backups",
                "Todavia no hay copias de seguridad generadas.",
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
            log().exception("No se pudo abrir la carpeta de backups: %s", e)
            QMessageBox.warning(
                self, "Error", f"No se pudo abrir la carpeta:\n{e}"
            )

    def _restaurar_seleccionado(self) -> None:
        seleccion = self._backup_seleccionado()
        if seleccion is None:
            return
        backup_path, ruta_original = seleccion
        if ruta_original is None:
            QMessageBox.warning(
                self,
                "No se puede restaurar",
                "No se pudo determinar el archivo original para este backup.",
            )
            return

        # Doble confirmacion.
        resp = QMessageBox.warning(
            self,
            "Confirmar restauracion",
            f"Vas a restaurar:\n\n"
            f"  Archivo: {ruta_original.name}\n"
            f"  Proceso: {ruta_original.parent.name}\n\n"
            f"El contenido actual se SOBRESCRIBIRA con la copia de seguridad.\n"
            f"Esta accion no se puede deshacer.\n\n"
            f"¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        # Confirmacion adicional para evitar accidentes.
        resp2 = QMessageBox.question(
            self,
            "Ultima confirmacion",
            f"¿Estas seguro de que queres reemplazar {ruta_original.name} "
            f"por su copia de seguridad?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp2 != QMessageBox.StandardButton.Yes:
            return

        with con_lock(ruta_original) as lock:
            if lock is None:
                QMessageBox.warning(
                    self,
                    "JSON bloqueado",
                    f"Otro proceso esta usando este JSON.\n\n"
                    f"{ruta_original.name}\n\n"
                    "Cierra los procesos que lo esten usando e intenta de nuevo.",
                )
                log().warning(
                    "Backups: lock no adquirido para %s", ruta_original
                )
                return
            try:
                # Validamos que el backup sea JSON valido antes de escribir.
                leer_json(backup_path)
                self._svc.restaurar_backup(
                    ruta_original,
                    proceso=ruta_original.parent.name,
                )
                log().info(
                    "Backups: restaurado %s desde %s",
                    ruta_original.name,
                    backup_path.name,
                )
                QMessageBox.information(
                    self,
                    "Restauracion completada",
                    f"Se restauro correctamente:\n\n{ruta_original}",
                )
                self.refrescar()
            except Exception as e:
                log().exception("Error al restaurar backup: %s", e)
                QMessageBox.critical(
                    self, "Error", f"No se pudo restaurar el backup:\n{e}"
                )
