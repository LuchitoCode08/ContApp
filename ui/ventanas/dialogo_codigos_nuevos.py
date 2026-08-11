"""Diálogo para gestionar códigos de concepto nuevos en Comprobante.

Aparece cuando el proceso detecta códigos en los CSVs de Bancolombia que
no están mapeados en ``codigos_conceptos.json``, ``foapal.json`` ni en el
JSON de códigos ignorados. El usuario puede:

- Ignorar los códigos (se guardan en ``codigos_ignorados.json``).
- Agregarlos a ``foapal.json`` completando los campos FOAPAL.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.recursos.tema import _paleta


# Acciones disponibles por fila.
ACCION_AGREGAR = "Agregar a FOAPAL"
ACCION_IGNORAR = "Ignorar"

# Valores D/C.
VALORES_DC = ["D", "C"]

# Valores por defecto sugeridos para nuevos códigos.
DEFAULT_FOAPAL = {
    "Fondo": "FOPNAL",
    "Organizacion": "13201",
    "Cuenta": "530515",
    "Programa": "999999",
    "D/C": "D",
}


@dataclass
class DecisionCodigos:
    """Decisión del usuario sobre los códigos nuevos."""

    # código -> campos FOAPAL completos
    agregar: dict[str, dict[str, str]] = field(default_factory=dict)
    # códigos que se ignoran / descartan
    ignorar: list[str] = field(default_factory=list)


class DialogoCodigosNuevos(QDialog):
    """Diálogo modal para decidir el destino de códigos de concepto nuevos."""

    def __init__(
        self,
        parent: QWidget | None,
        codigos: list[str],
        descripciones: dict[str, str],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nuevos códigos de concepto")
        self.setMinimumWidth(880)
        self.setMinimumHeight(360)
        self._codigos = codigos
        self._descripciones = descripciones
        self._decision = DecisionCodigos()

        self._construir_ui()
        self._aplicar_tema(_paleta())
        self._llenar_tabla()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Explicación.
        self._lbl_info = QLabel(
            f"Se encontraron {len(self._codigos)} códigos de concepto no mapeados "
            "en los JSONs del proceso.\n"
            "Podés agregarlos a FOAPAL o ignorarlos para que no vuelvan a aparecer."
        )
        self._lbl_info.setWordWrap(True)
        layout.addWidget(self._lbl_info)

        # Tabla.
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(8)
        self._tabla.setHorizontalHeaderLabels([
            "Código", "Descripción", "Acción", "Fondo", "Organización",
            "Cuenta", "Programa", "D/C",
        ])
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tabla.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._tabla)

        # Footer con botón "Ignorar todos" + botones estándar.
        footer = QHBoxLayout()
        self._btn_ignorar_todos = QPushButton("Ignorar todos")
        self._btn_ignorar_todos.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_ignorar_todos.clicked.connect(self._ignorar_todos)
        footer.addWidget(self._btn_ignorar_todos)
        footer.addStretch()

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save,
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Save).setText(
            "Guardar y continuar"
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Cancelar ejecución"
        )
        self._button_box.accepted.connect(self._guardar)
        self._button_box.rejected.connect(self.reject)
        footer.addWidget(self._button_box)
        layout.addLayout(footer)

    def _aplicar_tema(self, paleta) -> None:
        """Aplica la paleta actual al diálogo."""
        self.setStyleSheet(
            f"QDialog {{ background-color: {paleta.bg}; color: {paleta.fg}; }}"
            f" QLabel {{ color: {paleta.fg}; }}"
            f" QTableWidget {{"
            f"   background-color: {paleta.surface};"
            f"   alternate-background-color: {paleta.surface_alt};"
            f"   color: {paleta.fg};"
            f"   gridline-color: {paleta.border};"
            f"   border: 1px solid {paleta.border};"
            f"   border-radius: 8px;"
            f" }}"
            f" QHeaderView::section {{"
            f"   background-color: {paleta.surface_alt};"
            f"   color: {paleta.fg};"
            f"   padding: 6px;"
            f"   border: none;"
            f"   border-bottom: 1px solid {paleta.border};"
            f" }}"
            f" QPushButton {{"
            f"   background-color: {paleta.surface};"
            f"   color: {paleta.fg};"
            f"   border: 1px solid {paleta.border};"
            f"   border-radius: 6px;"
            f"   padding: 6px 14px;"
            f" }}"
            f" QPushButton:hover {{ background-color: {paleta.surface_alt}; }}"
            f" QComboBox {{"
            f"   background-color: {paleta.surface};"
            f"   color: {paleta.fg};"
            f"   border: 1px solid {paleta.border};"
            f"   border-radius: 4px;"
            f"   padding: 4px;"
            f" }}"
        )

    def _llenar_tabla(self) -> None:
        """Llena la tabla con los códigos detectados."""
        self._tabla.setRowCount(len(self._codigos))
        for i, codigo in enumerate(self._codigos):
            item_codigo = QTableWidgetItem(codigo)
            item_codigo.setFlags(item_codigo.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._tabla.setItem(i, 0, item_codigo)

            desc = self._descripciones.get(codigo, "")
            item_desc = QTableWidgetItem(desc)
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._tabla.setItem(i, 1, item_desc)

            combo_accion = QComboBox()
            combo_accion.addItems([ACCION_AGREGAR, ACCION_IGNORAR])
            combo_accion.setProperty("fila", i)
            combo_accion.currentIndexChanged.connect(self._on_accion_cambiada)
            self._tabla.setCellWidget(i, 2, combo_accion)

            for j, campo in enumerate(["Fondo", "Organizacion", "Cuenta", "Programa"], start=3):
                item = QTableWidgetItem(DEFAULT_FOAPAL[campo])
                self._tabla.setItem(i, j, item)

            combo_dc = QComboBox()
            combo_dc.addItems(VALORES_DC)
            combo_dc.setCurrentText(DEFAULT_FOAPAL["D/C"])
            self._tabla.setCellWidget(i, 7, combo_dc)

        self._actualizar_estado_filas()

    def _on_accion_cambiada(self) -> None:
        """Habilita/deshabilita campos FOAPAL según la acción elegida."""
        self._actualizar_estado_filas()

    def _actualizar_estado_filas(self) -> None:
        """Ajusta editabilidad de celdas FOAPAL según la acción de cada fila."""
        for i in range(self._tabla.rowCount()):
            combo = self._tabla.cellWidget(i, 2)
            if combo is None:
                continue
            agregar = combo.currentText() == ACCION_AGREGAR
            for col in range(3, 8):
                if col == 7:
                    combo_dc = self._tabla.cellWidget(i, col)
                    if combo_dc is not None:
                        combo_dc.setEnabled(agregar)
                else:
                    item = self._tabla.item(i, col)
                    if item is not None:
                        flags = item.flags()
                        if agregar:
                            item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
                        else:
                            item.setFlags(flags & ~Qt.ItemFlag.ItemIsEditable)

    def _ignorar_todos(self) -> None:
        """Cambia todas las filas a la acción "Ignorar"."""
        for i in range(self._tabla.rowCount()):
            combo = self._tabla.cellWidget(i, 2)
            if combo is not None:
                combo.setCurrentText(ACCION_IGNORAR)
        self._actualizar_estado_filas()

    def _guardar(self) -> None:
        """Construye la decisión y cierra el diálogo con accept."""
        decision = DecisionCodigos()
        for i in range(self._tabla.rowCount()):
            codigo = self._tabla.item(i, 0).text()
            combo = self._tabla.cellWidget(i, 2)
            if combo.currentText() == ACCION_IGNORAR:
                decision.ignorar.append(codigo)
                continue

            valores: dict[str, Any] = {}
            campos = ["Fondo", "Organizacion", "Cuenta", "Programa"]
            valido = True
            for j, campo in enumerate(campos, start=3):
                texto = self._tabla.item(i, j).text().strip()
                if not texto:
                    valido = False
                    break
                valores[campo] = texto

            combo_dc = self._tabla.cellWidget(i, 7)
            valores["D/C"] = combo_dc.currentText() if combo_dc else DEFAULT_FOAPAL["D/C"]

            if not valido:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Campos incompletos",
                    f"El código {codigo} está marcado para agregar a FOAPAL pero "
                    "tiene campos vacíos. Completá Fondo, Organización, Cuenta y Programa.",
                )
                return

            decision.agregar[codigo] = valores

        self._decision = decision
        self.accept()

    def decision(self) -> DecisionCodigos:
        """Devuelve la decisión tomada por el usuario."""
        return self._decision

    @staticmethod
    def solicitar_decision(
        parent: QWidget | None,
        codigos: list[str],
        descripciones: dict[str, str],
    ) -> DecisionCodigos | None:
        """Muestra el diálogo y devuelve la decisión, o None si cancela."""
        dialogo = DialogoCodigosNuevos(parent, codigos, descripciones)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            return dialogo.decision()
        return None
