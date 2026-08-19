"""Tests pytest-qt básicos del diálogo de códigos nuevos.

Cubre:
- El diálogo se construye con los códigos y descripciones dados.
- La acción "Ignorar" se refleja en la decisión.
- La acción "Agregar a FOAPAL" con campos completos se refleja en la decisión.
- Campos incompletos al agregar evitan cerrar el diálogo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

RAIZ_PROY = Path(__file__).resolve().parent.parent
if str(RAIZ_PROY) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROY))

from ui.ventanas.dialogo_codigos_nuevos import (  # noqa: E402
    ACCION_IGNORAR,
    DialogoCodigosNuevos,
)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def _desactivar_message_box(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita que QMessageBox.warning bloquee los tests offscreen."""
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)


def test_dialogo_muestra_codigos_y_descripciones(qt_app) -> None:
    """La tabla tiene una fila por código y muestra la descripción."""
    dialogo = DialogoCodigosNuevos(None, ["8888"], {"8888": "DESC NUEVA"})
    try:
        assert dialogo._tabla.rowCount() == 1
        assert dialogo._tabla.item(0, 0).text() == "8888"
        assert dialogo._tabla.item(0, 1).text() == "DESC NUEVA"
    finally:
        dialogo.deleteLater()


def test_decision_ignorar_todos(qt_app) -> None:
    """"Ignorar todos" marca todos los códigos para ignorar."""
    dialogo = DialogoCodigosNuevos(None, ["1111", "2222"], {})
    try:
        dialogo._ignorar_todos()
        dialogo._guardar()
        decision = dialogo.decision()
        assert decision.agregar == {}
        assert sorted(decision.ignorar.keys()) == ["1111", "2222"]
    finally:
        dialogo.deleteLater()


def test_decision_agregar_codigo(qt_app) -> None:
    """Un código con acción "Agregar" y campos completos se guarda en agregar."""
    dialogo = DialogoCodigosNuevos(None, ["3333"], {"3333": "DESC"})
    try:
        # Fila 0: dejar acción por defecto (Agregar) y completar campos.
        dialogo._tabla.item(0, 3).setText("FOPNAL")
        dialogo._tabla.item(0, 4).setText("13201")
        dialogo._tabla.item(0, 5).setText("530515")
        dialogo._tabla.item(0, 6).setText("999999")
        dialogo._guardar()
        decision = dialogo.decision()
        assert decision.ignorar == {}
        assert "3333" in decision.agregar
        assert decision.agregar["3333"]["D/C"] == "D"
        assert decision.agregar["3333"]["Fondo"] == "FOPNAL"
    finally:
        dialogo.deleteLater()


def test_guardar_rechaza_campos_incompletos(qt_app) -> None:
    """Si faltan campos FOAPAL, _guardar no cierra el diálogo."""
    dialogo = DialogoCodigosNuevos(None, ["4444"], {})
    try:
        dialogo._tabla.item(0, 3).setText("")  # Fondo vacío
        dialogo._guardar()
        # El diálogo sigue abierto (no se aceptó).
        assert dialogo.result() == QDialog.DialogCode.Rejected
    finally:
        dialogo.deleteLater()
