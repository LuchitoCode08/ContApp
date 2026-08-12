"""Tests de los botones eliminar en los editores tipo B y C."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

# Forzar offscreen ANTES de cualquier import Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox as MB  # noqa: E402

RAIZ_PROY = Path(__file__).resolve().parent.parent
if str(RAIZ_PROY) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROY))


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ============================================================
# Editor Tipo C
# ============================================================


def test_editor_tipo_c_tiene_columna_eliminar(qt_app) -> None:
    """El editor tipo C debe tener 3 columnas (clave, valor, eliminar)."""
    from ui.ventanas.editor_json import EditorTipoC

    datos = {"Intereses": {"1998": "AJUSTE", "2999": "ABONO"}}
    editor = EditorTipoC(datos, lambda d: None)
    try:
        assert editor._arbol.columnCount() == 3
    finally:
        editor.deleteLater()


def test_editor_tipo_c_eliminar_borra_entrada(qt_app) -> None:
    """Eliminar una entrada tipo C la quita del diccionario y dispara on_change."""
    from ui.ventanas.editor_json import EditorTipoC

    datos = {"Intereses": {"1998": "AJUSTE", "2999": "ABONO"}}
    cambios: list[dict] = []
    editor = EditorTipoC(datos, lambda d: cambios.append(copy.deepcopy(d)))
    try:
        editor._eliminar("Intereses", "1998")
        assert "1998" not in editor.datos["Intereses"]
        assert "2999" in editor.datos["Intereses"]
        assert cambios
        assert "1998" not in cambios[-1]["Intereses"]
    finally:
        editor.deleteLater()


def test_editor_tipo_c_eliminar_ultima_entrada_borra_seccion(qt_app, monkeypatch) -> None:
    """Si al eliminar queda la seccion vacia, se elimina tambien (respuesta Yes)."""
    from ui.ventanas.editor_json import EditorTipoC

    monkeypatch.setattr(MB, "question", staticmethod(
        lambda *a, **k: MB.StandardButton.Yes,
    ))

    datos = {"Intereses": {"1998": "AJUSTE"}}
    cambios: list[dict] = []
    editor = EditorTipoC(datos, lambda d: cambios.append(copy.deepcopy(d)))
    try:
        editor._eliminar("Intereses", "1998")
        assert "Intereses" not in editor.datos
        assert cambios
        assert "Intereses" not in cambios[-1]
    finally:
        editor.deleteLater()


def test_editor_tipo_c_eliminar_ultima_entrada_mantiene_seccion(qt_app, monkeypatch) -> None:
    """Si al eliminar queda la seccion vacia, se puede conservar (respuesta No)."""
    from ui.ventanas.editor_json import EditorTipoC

    monkeypatch.setattr(MB, "question", staticmethod(
        lambda *a, **k: MB.StandardButton.No,
    ))

    datos = {"Intereses": {"1998": "AJUSTE"}}
    cambios: list[dict] = []
    editor = EditorTipoC(datos, lambda d: cambios.append(copy.deepcopy(d)))
    try:
        editor._eliminar("Intereses", "1998")
        assert "Intereses" in editor.datos
        assert editor.datos["Intereses"] == {}
        assert cambios
        assert cambios[-1]["Intereses"] == {}
    finally:
        editor.deleteLater()


# ============================================================
# Editor Tipo B
# ============================================================


def test_editor_tipo_b_tiene_columna_eliminar(qt_app) -> None:
    """El editor tipo B debe tener una columna extra para eliminar."""
    from ui.ventanas.editor_json import EditorTipoB

    datos = {
        "creditos": {
            "1334": {"Fondo": "FOPNAL", "Cuenta": "530515"},
        }
    }
    editor = EditorTipoB(datos, lambda d: None)
    try:
        # Clave + campos + columna eliminar.
        assert editor._arbol.columnCount() == 1 + len(editor._campos) + 1
    finally:
        editor.deleteLater()


def test_editor_tipo_b_eliminar_borra_entrada(qt_app) -> None:
    """Eliminar una entrada tipo B la quita del diccionario y dispara on_change."""
    from ui.ventanas.editor_json import EditorTipoB

    datos = {
        "creditos": {
            "1334": {"Fondo": "FOPNAL", "Cuenta": "530515"},
            "2999": {"Fondo": "FOPNAL", "Cuenta": "421010"},
        }
    }
    cambios: list[dict] = []
    editor = EditorTipoB(datos, lambda d: cambios.append(copy.deepcopy(d)))
    try:
        editor._eliminar("creditos", "1334")
        assert "1334" not in editor.datos["creditos"]
        assert "2999" in editor.datos["creditos"]
        assert cambios
        assert "1334" not in cambios[-1]["creditos"]
    finally:
        editor.deleteLater()


def test_editor_tipo_b_eliminar_ultima_entrada_borra_seccion(qt_app, monkeypatch) -> None:
    """Si al eliminar queda la seccion vacia, se elimina tambien (respuesta Yes)."""
    from ui.ventanas.editor_json import EditorTipoB

    monkeypatch.setattr(MB, "question", staticmethod(
        lambda *a, **k: MB.StandardButton.Yes,
    ))

    datos = {
        "creditos": {
            "1334": {"Fondo": "FOPNAL", "Cuenta": "530515"},
        }
    }
    cambios: list[dict] = []
    editor = EditorTipoB(datos, lambda d: cambios.append(copy.deepcopy(d)))
    try:
        editor._eliminar("creditos", "1334")
        assert "creditos" not in editor.datos
        assert cambios
        assert "creditos" not in cambios[-1]
    finally:
        editor.deleteLater()
