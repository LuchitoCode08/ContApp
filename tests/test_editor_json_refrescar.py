"""Tests del metodo ``refrescar()`` de PantallaDiccionarios.

El refresh se dispara al entrar a la seccion Diccionarios (ver
``VentanaPrincipal._cambiar_pantalla``) y debe:

    - Releer de disco el JSON abierto (cambios hechos en el IDE).
    - Mostrar JSONs nuevos creados fuera de la app.
    - NO pisar el editor si hay cambios sin guardar.
    - Limpiar el editor si el archivo abierto desaparecio de disco.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Forzar offscreen ANTES de cualquier import Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

RAIZ_PROY = Path(__file__).resolve().parent.parent
if str(RAIZ_PROY) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROY))


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def jsons_dir_tmp(tmp_path, monkeypatch) -> Path:
    """Directorio temporal con un proceso y dos JSONs sinteticos."""
    (tmp_path / "comprobante").mkdir()
    (tmp_path / "comprobante" / "uno.json").write_text(
        '{"a": 1}', encoding="utf-8"
    )
    (tmp_path / "comprobante" / "dos.json").write_text(
        '{"b": 2}', encoding="utf-8"
    )

    import ui.ventanas.editor_json as editor_mod
    monkeypatch.setattr(editor_mod, "JSONS_DIR", tmp_path)
    return tmp_path


def _expandir_comprobante(v):
    from PySide6.QtCore import Qt
    rol = Qt.ItemDataRole.UserRole
    for i in range(v._arbol.topLevelItemCount()):
        sec = v._arbol.topLevelItem(i)
        if sec.data(0, rol) == "comprobante":
            sec.setExpanded(True)
            return sec
    raise AssertionError("No se encontro la seccion comprobante")


def _seleccionar_json(v, ruta: Path) -> None:
    from PySide6.QtCore import Qt
    rol = Qt.ItemDataRole.UserRole
    for i in range(v._arbol.topLevelItemCount()):
        sec = v._arbol.topLevelItem(i)
        for j in range(sec.childCount()):
            child = sec.child(j)
            if child.data(0, rol) == str(ruta):
                v._arbol.setCurrentItem(child)
                return
    raise AssertionError(f"No se encontro el item {ruta}")


def test_refrescar_relee_json_abierto(qt_app, jsons_dir_tmp) -> None:
    """Si el JSON abierto cambio en disco, refrescar() lo relee."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        sec = _expandir_comprobante(v)
        ruta = jsons_dir_tmp / "comprobante" / "uno.json"
        _seleccionar_json(v, ruta)
        assert v._datos_actuales == {"a": 1}

        # Simular edicion externa (IDE).
        ruta.write_text('{"a": 99}', encoding="utf-8")
        v.refrescar()

        assert v._datos_actuales == {"a": 99}
        assert v._datos_originales == {"a": 99}
        # La seccion sigue expandida y cargada tras el refresh (el arbol
        # se reconstruye, asi que buscamos la seccion nueva).
        sec_nueva = None
        for i in range(v._arbol.topLevelItemCount()):
            it = v._arbol.topLevelItem(i)
            from PySide6.QtCore import Qt
            if it.data(0, Qt.ItemDataRole.UserRole) == "comprobante":
                sec_nueva = it
        assert sec_nueva is not None
        assert sec_nueva.isExpanded()
        assert sec_nueva.childCount() == 2
    finally:
        v.deleteLater()


def test_refrescar_muestra_json_nuevo(qt_app, jsons_dir_tmp) -> None:
    """Un JSON creado fuera de la app debe aparecer tras refrescar()."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        _expandir_comprobante(v)
        assert len(v._items) == 2

        (jsons_dir_tmp / "comprobante" / "tres.json").write_text(
            '{"c": 3}', encoding="utf-8"
        )
        v.refrescar()

        rutas = [p.name for p, _ in v._items]
        assert "tres.json" in rutas
        assert len(v._items) == 3
    finally:
        v.deleteLater()


def test_refrescar_no_pisa_cambios_sin_guardar(qt_app, jsons_dir_tmp) -> None:
    """Con cambios pendientes, refrescar() no debe tocar el editor."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        _expandir_comprobante(v)
        ruta = jsons_dir_tmp / "comprobante" / "uno.json"
        _seleccionar_json(v, ruta)

        # Simular edicion del usuario en el editor (sin guardar).
        v._datos_actuales = {"a": 1234}
        v._hay_cambios = True

        # Simular edicion externa.
        ruta.write_text('{"a": 99}', encoding="utf-8")
        v.refrescar()

        assert v._datos_actuales == {"a": 1234}, (
            "refrescar() piso los cambios sin guardar del usuario."
        )
        assert v._hay_cambios is True
    finally:
        v.deleteLater()


def test_refrescar_archivo_eliminado_limpia_editor(
    qt_app, jsons_dir_tmp
) -> None:
    """Si el JSON abierto desaparecio de disco, el editor se limpia."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        _expandir_comprobante(v)
        ruta = jsons_dir_tmp / "comprobante" / "uno.json"
        _seleccionar_json(v, ruta)
        assert v._ruta_actual is not None

        ruta.unlink()
        v.refrescar()

        assert v._ruta_actual is None
        assert v._datos_actuales is None
        assert v._editor_widget is None
    finally:
        v.deleteLater()
