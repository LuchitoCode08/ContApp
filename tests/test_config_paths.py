"""Tests de las rutas resueltas por `app.config` segun el contexto.

Cubre:
- En desarrollo: RAIZ apunta a la raiz del repo.
- Empaquetado (sys.frozen): RAIZ apunta al directorio del ejecutable.
- JSONS_DIR siempre relativo a RAIZ.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ_TEST = Path(__file__).resolve().parent.parent
if str(RAIZ_TEST) not in sys.path:
    sys.path.insert(0, str(RAIZ_TEST))


def test_raiz_en_desarrollo_apunta_al_repo() -> None:
    """Sin ``sys.frozen``, RAIZ = directorio donde esta main.py."""
    # Importamos en este punto (no antes) para que ``sys.frozen`` refleje
    # el contexto real del test runner.
    from app.config import RAIZ
    # La raiz debe ser 2 niveles arriba de app/config.py.
    expected = Path(__file__).resolve().parent.parent
    assert RAIZ == expected


def test_raiz_en_empaquetado_apunta_al_ejecutable(monkeypatch) -> None:
    """Con ``sys.frozen=True``, RAIZ = directorio del ejecutable."""
    import importlib
    fake_exe_dir = Path(r"C:\fake\ContApp")
    fake_exe = fake_exe_dir / "ContApp.exe"

    # Simulamos PyInstaller seteando frozen.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)

    # Reimportamos el modulo para que _detectar_raiz() corra de nuevo.
    if "app.config" in sys.modules:
        importlib.reload(sys.modules["app.config"])
    from app.config import RAIZ
    assert RAIZ == fake_exe_dir
    assert RAIZ != Path(__file__).resolve().parent.parent


def test_jsons_dir_siempre_relativo_a_raiz(monkeypatch) -> None:
    """JSONS_DIR siempre = RAIZ/jsons (en dev y en frozen)."""
    import importlib
    fake_exe = Path(r"D:\otra\ubicacion\App.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)

    if "app.config" in sys.modules:
        importlib.reload(sys.modules["app.config"])
    from app.config import JSONS_DIR, RAIZ
    assert JSONS_DIR == RAIZ / "jsons"
    assert JSONS_DIR == fake_exe.parent / "jsons"


def test_data_y_log_siempre_relativos_a_raiz() -> None:
    """data/, log/, usuario.json viven al lado del ejecutable en frozen."""
    from app.config import DATA_DIR, LOG_DIR, PREFERENCIAS, RAIZ
    assert DATA_DIR == RAIZ / "data"
    assert LOG_DIR == RAIZ / "log"
    assert PREFERENCIAS == RAIZ / "data" / "settings.json"


def test_resultados_siempre_en_documents() -> None:
    """RESULTADOS_DIR vive en Documents/ContApp_Resultados, NO al lado del exe."""
    from app.config import RESULTADOS_DIR, DOCUMENTS
    assert RESULTADOS_DIR == DOCUMENTS / "ContApp_Resultados"
    # Esta ruta NO cambia con frozen.
    assert "ContApp_Resultados" in str(RESULTADOS_DIR)