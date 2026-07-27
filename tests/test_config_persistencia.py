"""Tests de persistencia de preferencias en Config."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import PREFERENCIAS, Config


@pytest.fixture
def tmp_prefs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige PREFERENCIAS a un archivo en tmp_path."""
    destino = tmp_path / "usuario.json"
    monkeypatch.setattr("app.config.PREFERENCIAS", destino)
    return destino


def test_config_default_sin_archivo(tmp_prefs: Path) -> None:
    """Sin preferencias guardadas, devuelve defaults."""
    cfg = Config()
    cfg.cargar_preferencias()
    assert cfg.usuario == ""
    assert cfg.modo_prueba is False
    assert cfg.tema == "claro"


def test_guardar_y_cargar_preferencias(tmp_prefs: Path) -> None:
    """Guarda y luego carga correctamente."""
    cfg = Config()
    cfg.usuario = "lfloaiza"
    cfg.modo_prueba = True
    cfg.tema = "oscuro"
    cfg.guardar_preferencias()

    # El archivo existe y tiene el JSON correcto.
    assert tmp_prefs.exists()
    with open(tmp_prefs, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {
        "usuario": "lfloaiza",
        "modo_prueba": True,
        "tema": "oscuro",
    }

    # Una nueva instancia debe cargar los valores guardados.
    cfg2 = Config()
    cfg2.cargar_preferencias()
    assert cfg2.usuario == "lfloaiza"
    assert cfg2.modo_prueba is True
    assert cfg2.tema == "oscuro"


def test_cargar_archivo_corrupto_no_falla(tmp_prefs: Path) -> None:
    """Un JSON invalido no rompe la carga (devuelve defaults)."""
    tmp_prefs.write_text("{ esto no es json valido", encoding="utf-8")
    cfg = Config()
    cfg.cargar_preferencias()
    # Mantiene sus defaults (no se rompio).
    assert cfg.tema == "claro"


def test_tema_invalido_se_descarta(tmp_prefs: Path) -> None:
    """Si el JSON tiene un tema no soportado, se descarta y queda el default."""
    tmp_prefs.write_text(
        json.dumps({"tema": "rosa"}), encoding="utf-8"
    )
    cfg = Config()
    cfg.cargar_preferencias()
    assert cfg.tema == "claro"  # no se aplico el valor invalido


def test_guardar_crea_directorio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si el directorio data/ no existe, guardar_preferencias lo crea."""
    fake_data = tmp_path / "data_nuevo"
    fake_prefs = fake_data / "usuario.json"
    monkeypatch.setattr("app.config.DATA_DIR", fake_data)
    monkeypatch.setattr("app.config.PREFERENCIAS", fake_prefs)

    cfg = Config()
    cfg.usuario = "test"
    cfg.guardar_preferencias()

    assert fake_prefs.exists()
    assert fake_data.is_dir()


def test_guardar_no_falla_sin_permisos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si no se puede escribir, no se lanza excepcion."""
    # Apuntamos a una ruta donde el directorio padre no existe y
    # no se puede crear (un archivo en lugar de directorio).
    archivo_padre = tmp_path / "es_un_archivo"
    archivo_padre.write_text("bloqueo")
    ruta_invalida = archivo_padre / "subdir" / "usuario.json"
    monkeypatch.setattr("app.config.DATA_DIR", archivo_padre)
    monkeypatch.setattr("app.config.PREFERENCIAS", ruta_invalida)

    cfg = Config()
    cfg.guardar_preferencias()  # no debe lanzar