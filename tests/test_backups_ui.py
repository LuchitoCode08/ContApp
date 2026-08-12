"""Tests pytest-qt de ``PantallaBackups``.

Estrategia:
    - Monkey-patchear ``ui.ventanas.backups.DATA_DIR`` para apuntar a un
      tmp_path con backups sinteticos.
    - Verificar que la pantalla lista backups y permite seleccionarlos.
"""
from __future__ import annotations

import copy
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
def data_dir_tmp(tmp_path, monkeypatch) -> Path:
    """Crea backups sinteticos organizados por proceso."""
    backups_dir = tmp_path / "backups"
    (backups_dir / "comprobante").mkdir(parents=True)
    (backups_dir / "fierro").mkdir(parents=True)
    (backups_dir / "comprobante" / "codigos_conceptos.json").write_text(
        '{"codigo": "valor"}', encoding="utf-8"
    )
    (backups_dir / "fierro" / "mapeo_auxiliares.json").write_text(
        '{"aux": "123"}', encoding="utf-8"
    )

    import ui.ventanas.backups as backups_mod
    monkeypatch.setattr(backups_mod, "DATA_DIR", tmp_path)
    # JSONS_DIR se usa para derivar la ruta original; apuntamos a tmp.
    jsons_dir = tmp_path / "jsons"
    (jsons_dir / "comprobante").mkdir(parents=True)
    (jsons_dir / "fierro").mkdir(parents=True)
    monkeypatch.setattr(backups_mod, "JSONS_DIR", jsons_dir)
    return tmp_path


def test_arranca_con_mensaje_sin_backups(qt_app, tmp_path, monkeypatch) -> None:
    """Si no hay backups, el contador indica que no hay copias."""
    import ui.ventanas.backups as backups_mod
    monkeypatch.setattr(backups_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(backups_mod, "JSONS_DIR", tmp_path / "jsons")

    from ui.ventanas.backups import PantallaBackups
    v = PantallaBackups()
    try:
        assert "Sin copias de seguridad" in v._lbl_total.text()
        assert v.btn_restaurar.isEnabled() is False
    finally:
        v.deleteLater()


def test_lista_backups_por_proceso(qt_app, data_dir_tmp) -> None:
    """La pantalla muestra backups agrupados por proceso."""
    from ui.ventanas.backups import PantallaBackups
    v = PantallaBackups()
    try:
        assert v._arbol.topLevelItemCount() == 2  # comprobante, fierro
        # Comprobante tiene 1 backup.
        comprobante = v._arbol.topLevelItem(0)
        assert comprobante.text(0) == "Comprobante"
        assert comprobante.childCount() == 1
        # Fierro tiene 1 backup.
        fierro = v._arbol.topLevelItem(1)
        assert fierro.text(0) == "Fierro"
        assert fierro.childCount() == 1
        assert "2 copia(s)" in v._lbl_total.text()
    finally:
        v.deleteLater()


def test_seleccionar_backup_habilita_restaurar(qt_app, data_dir_tmp) -> None:
    """Al seleccionar un item hoja, el boton Restaurar se habilita."""
    from ui.ventanas.backups import PantallaBackups
    from PySide6.QtCore import Qt
    v = PantallaBackups()
    try:
        comprobante = v._arbol.topLevelItem(0)
        item = comprobante.child(0)
        v._arbol.setCurrentItem(item)
        assert v.btn_restaurar.isEnabled() is True
    finally:
        v.deleteLater()


def test_guardar_desde_editor_crea_backup_visible(qt_app, tmp_path, monkeypatch) -> None:
    """Guardar un JSON desde el editor debe dejar el backup en data/backups/."""
    import ui.ventanas.editor_json as editor_mod
    from PySide6.QtWidgets import QMessageBox as MB

    # Estructura temporal de jsons y data.
    jsons_dir = tmp_path / "jsons"
    data_dir = tmp_path / "data"
    (jsons_dir / "comprobante").mkdir(parents=True)
    ruta_json = jsons_dir / "comprobante" / "test.json"
    ruta_json.write_text('{"a": "1"}', encoding="utf-8")

    monkeypatch.setattr(editor_mod, "JSONS_DIR", jsons_dir)
    monkeypatch.setattr(editor_mod, "DATA_DIR", data_dir)

    # Silenciar dialogos del editor.
    monkeypatch.setattr(MB, "question", staticmethod(
        lambda *a, **k: MB.StandardButton.Yes,
    ))
    monkeypatch.setattr(MB, "information", staticmethod(
        lambda *a, **k: MB.StandardButton.Ok,
    ))

    from ui.ventanas.editor_json import PantallaDiccionarios

    v = PantallaDiccionarios()
    try:
        # Expandir Comprobante y seleccionar test.json.
        sec = None
        for i in range(v._arbol.topLevelItemCount()):
            if v._arbol.topLevelItem(i).text(0) == "Comprobante":
                sec = v._arbol.topLevelItem(i)
                break
        assert sec is not None
        sec.setExpanded(True)
        item = None
        for j in range(sec.childCount()):
            if sec.child(j).text(0) == "Test":
                item = sec.child(j)
                break
        assert item is not None
        v._arbol.setCurrentItem(item)

        # Modificar y guardar.
        v._datos_actuales = copy.deepcopy({"a": "2"})
        v._on_guardar()

        # El backup debe existir en data/backups/comprobante/.
        backup_esperado = data_dir / "backups" / "comprobante" / "test.json"
        assert backup_esperado.exists(), (
            f"Backup no encontrado en {backup_esperado}"
        )
        assert backup_esperado.read_text(encoding="utf-8") == '{"a": "1"}'

        # La pantalla de backups debe listarlo.
        import ui.ventanas.backups as backups_mod
        monkeypatch.setattr(backups_mod, "DATA_DIR", data_dir)
        monkeypatch.setattr(backups_mod, "JSONS_DIR", jsons_dir)

        from ui.ventanas.backups import PantallaBackups
        pb = PantallaBackups()
        try:
            assert pb._arbol.topLevelItemCount() == 1
            sec_b = pb._arbol.topLevelItem(0)
            assert sec_b.text(0) == "Comprobante"
            assert sec_b.childCount() == 1
            assert sec_b.child(0).text(1) == "test.json"
        finally:
            pb.deleteLater()
    finally:
        v.deleteLater()
