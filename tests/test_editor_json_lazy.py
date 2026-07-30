"""Tests del lazy load del arbol de JSONs en PantallaDiccionarios.

Estrategia:
    - Monkey-patchear ``ui.ventanas.editor_json.JSONS_DIR`` para apuntar
      a un tmp_path con sub-carpetas de procesos y JSONs sinteticos.
    - Crear la pantalla y verificar:
        * Inicialmente solo hay secciones (procesos), no items.
        * Items cargados = 0.
        * Expandir una seccion dispara la carga de sus JSONs.
        * Re-expandir es idempotente (no duplica items).
        * Directorio inexistente -> mensaje amigable.
        * Directorio vacio -> "(sin archivos JSON)".
        * Seleccionar un item carga el JSON (verifica que _on_seleccionar_json
          sigue funcionando tras el refactor).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Forzar offscreen ANTES de cualquier import Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

# sys.path para que los imports del paquete funcionen.
RAIZ_PROY = Path(__file__).resolve().parent.parent
if str(RAIZ_PROY) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROY))


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def jsons_dir_tmp(tmp_path, monkeypatch) -> Path:
    """Crea un directorio temporal con 3 procesos y varios JSONs sinteticos.

    Estructura:
        tmp_path/
            comprobante/uno.json      {}
            comprobante/dos.json      {}
            fierro/uno.json           {}
            zeus/vacio/               (directorio sin JSONs)
            _basura/                  (NO es un proceso -> debe ignorarse)
    """
    # Crear estructura.
    (tmp_path / "comprobante").mkdir()
    (tmp_path / "comprobante" / "uno.json").write_text("{}", encoding="utf-8")
    (tmp_path / "comprobante" / "dos.json").write_text("{}", encoding="utf-8")
    (tmp_path / "fierro").mkdir()
    (tmp_path / "fierro" / "uno.json").write_text("{}", encoding="utf-8")
    (tmp_path / "zeus").mkdir()
    # "zeus" queda sin archivos -> prueba el caso vacio.
    # Una carpeta que NO es un proceso (no es directorio de proceso valido).
    (tmp_path / "_basura").mkdir()
    (tmp_path / "_basura" / "no.json").write_text("{}", encoding="utf-8")

    # Monkey-patch del JSONS_DIR para que la UI use nuestro tmp.
    import ui.ventanas.editor_json as editor_mod
    monkeypatch.setattr(editor_mod, "JSONS_DIR", tmp_path)
    return tmp_path


# ============================================================
# Estado inicial (lazy)
# ============================================================

def test_inicial_no_carga_items(qt_app, jsons_dir_tmp) -> None:
    """Al abrir la pantalla, NO se debe haber listado ningun archivo JSON."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        assert v._arbol.topLevelItemCount() == 3  # comprobante, fierro, zeus
        assert len(v._items) == 0, (
            "Lazy load fallo: se cargaron items al abrir. "
            "Esperaba 0 hasta que el usuario expanda."
        )
        # Todas las secciones deben tener UN SOLO hijo (el placeholder).
        for i in range(v._arbol.topLevelItemCount()):
            sec = v._arbol.topLevelItem(i)
            assert sec.childCount() == 1
            assert sec.child(0).text(0) == "Cargando..."
    finally:
        v.deleteLater()


def test_basura_no_crea_seccion(qt_app, jsons_dir_tmp) -> None:
    """Carpetas que no son procesos (ej: _basura) NO deben aparecer."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        secciones = []
        for i in range(v._arbol.topLevelItemCount()):
            secciones.append(v._arbol.topLevelItem(i).text(0))
        assert "_Basura" not in secciones, (
            f"La carpeta _basura no debe aparecer como seccion. Vistas: {secciones}"
        )
        assert "Comprobante" in secciones
        assert "Fierro" in secciones
        assert "Zeus" in secciones
    finally:
        v.deleteLater()


# ============================================================
# Expansion: carga lazy
# ============================================================

def test_expandir_seccion_carga_hijos(qt_app, jsons_dir_tmp) -> None:
    """Expandir una seccion debe listar sus JSONs."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        sec = None
        for i in range(v._arbol.topLevelItemCount()):
            if v._arbol.topLevelItem(i).text(0) == "Comprobante":
                sec = v._arbol.topLevelItem(i)
                break
        assert sec is not None
        assert sec.childCount() == 1  # placeholder
        assert len(v._items) == 0

        sec.setExpanded(True)

        # Ahora debe haber 2 hijos (uno.json, dos.json) y 2 items.
        assert sec.childCount() == 2
        assert len(v._items) == 2
        nombres = [sec.child(i).text(0) for i in range(sec.childCount())]
        assert "Uno" in nombres
        assert "Dos" in nombres
    finally:
        v.deleteLater()


def test_expandir_es_idempotente(qt_app, jsons_dir_tmp) -> None:
    """Re-expandir una seccion ya cargada NO debe duplicar items."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        sec = None
        for i in range(v._arbol.topLevelItemCount()):
            if v._arbol.topLevelItem(i).text(0) == "Comprobante":
                sec = v._arbol.topLevelItem(i)
                break
        assert sec is not None

        sec.setExpanded(True)
        hijos_primera = sec.childCount()
        items_primera = len(v._items)
        assert hijos_primera == 2
        assert items_primera == 2

        sec.setExpanded(False)
        sec.setExpanded(True)

        assert sec.childCount() == hijos_primera, (
            "Re-expandir duplico hijos."
        )
        assert len(v._items) == items_primera, (
            "Re-expandir duplico items en self._items."
        )
    finally:
        v.deleteLater()


def test_seccion_vacia_muestra_placeholder_amigable(qt_app, jsons_dir_tmp) -> None:
    """Si un directorio de proceso no tiene JSONs, mostrar mensaje claro."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        sec_zeus = None
        for i in range(v._arbol.topLevelItemCount()):
            if v._arbol.topLevelItem(i).text(0) == "Zeus":
                sec_zeus = v._arbol.topLevelItem(i)
                break
        assert sec_zeus is not None

        sec_zeus.setExpanded(True)

        # Debe mostrar el placeholder "(sin archivos JSON)".
        assert sec_zeus.childCount() == 1
        texto = sec_zeus.child(0).text(0)
        assert "sin archivos" in texto.lower()
    finally:
        v.deleteLater()


# ============================================================
# Directorio JSONS_DIR inexistente
# ============================================================

def test_jsons_dir_inexistente_no_falla(qt_app, tmp_path, monkeypatch) -> None:
    """Si JSONS_DIR no existe, la UI debe abrir sin crashear."""
    import ui.ventanas.editor_json as editor_mod
    monkeypatch.setattr(editor_mod, "JSONS_DIR", tmp_path / "no_existe")
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        assert v._arbol.topLevelItemCount() == 0
        assert len(v._items) == 0
    finally:
        v.deleteLater()


def test_proceso_dir_desaparecido_muestra_error(
    qt_app, jsons_dir_tmp, monkeypatch,
) -> None:
    """Si el directorio de un proceso desaparece tras la carga inicial,
    expandir debe mostrar un mensaje y NO crashear."""
    import ui.ventanas.editor_json as editor_mod
    # Cargar primero con todos los dirs.
    from ui.ventanas.editor_json import PantallaDiccionarios
    v = PantallaDiccionarios()
    try:
        # Ahora borramos el directorio de "fierro".
        import shutil
        shutil.rmtree(jsons_dir_tmp / "fierro")
        # Expandimos la seccion Fierro.
        sec_fierro = None
        for i in range(v._arbol.topLevelItemCount()):
            if v._arbol.topLevelItem(i).text(0) == "Fierro":
                sec_fierro = v._arbol.topLevelItem(i)
                break
        assert sec_fierro is not None
        sec_fierro.setExpanded(True)
        # Debe mostrar "(directorio no disponible)" o similar.
        assert sec_fierro.childCount() == 1
        texto = sec_fierro.child(0).text(0).lower()
        assert "no disponible" in texto or "error" in texto
    finally:
        v.deleteLater()


# ============================================================
# Seleccion de items (compatibilidad con flujo existente)
# ============================================================

def test_seleccion_de_item_carga_json(
    qt_app, jsons_dir_tmp, monkeypatch,
) -> None:
    """Tras expandir, seleccionar un item debe seguir funcionando (carga el JSON)."""
    from ui.ventanas.editor_json import PantallaDiccionarios
    # Silenciar el QMessageBox de "cambios sin guardar" por si se dispara.
    from PySide6.QtWidgets import QMessageBox as MB
    monkeypatch.setattr(MB, "question", staticmethod(
        lambda *a, **k: MB.StandardButton.Discard,
    ))
    # Silenciar el QMessageBox.critical que aparece si leer_json falla
    # (en este test NO deberia fallar, pero parchamos por higiene).
    monkeypatch.setattr(MB, "critical", staticmethod(
        lambda *a, **k: MB.StandardButton.Ok,
    ))

    v = PantallaDiccionarios()
    try:
        # Expandir Comprobante.
        sec = None
        for i in range(v._arbol.topLevelItemCount()):
            if v._arbol.topLevelItem(i).text(0) == "Comprobante":
                sec = v._arbol.topLevelItem(i)
                break
        sec.setExpanded(True)

        # Seleccionar el primer item. Orden alfabetico de los archivos
        # del fixture: "dos.json", "uno.json" -> "Dos" es el primero.
        item = sec.child(0)
        assert item.text(0) == "Dos"  # 'd' < 'u' en ASCII
        v._arbol.setCurrentItem(item)
        QApplication.processEvents()

        # _ruta_actual debe apuntar al archivo correspondiente.
        assert v._ruta_actual is not None, (
            "_on_seleccionar_json no se ejecuto. Esperaba que "
            "itemSelectionChanged disparara la carga."
        )
        assert v._ruta_actual.name == "dos.json"
        assert v._ruta_actual.parent.name == "comprobante"
    finally:
        v.deleteLater()