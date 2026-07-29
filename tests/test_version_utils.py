"""Tests unitarios de `app.updater.version_utils`.

Cubre:
- parsear_version (con/sin prefijo "v", casos invalidos)
- comparar (mayor, menor, igual, error)
- hay_actualizacion (atajo sobre comparar)
- parsear_release (release valido, sin assets, JSON invalido)
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pytest

from app.updater.version_utils import (
    ReleaseInfo,
    comparar,
    hay_actualizacion,
    parsear_release,
    parsear_version,
)


# --------------------------------------------------------------------
# parsear_version
# --------------------------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("1.0.0", (1, 0, 0)),
    ("v1.0.0", (1, 0, 0)),
    ("  v1.2.3  ", (1, 2, 3)),
    ("10.20.30", (10, 20, 30)),
    ("0.0.1", (0, 0, 1)),
])
def test_parsear_version_validos(texto: str, esperado: tuple[int, int, int]) -> None:
    assert parsear_version(texto) == esperado


@pytest.mark.parametrize("texto", [
    "",                 # vacio
    "1",                # solo major
    "1.2",              # falta patch
    "1.2.3.4",          # de mas
    "1.2.3-rc1",        # pre-release no soportado
    "1.2.3+build",      # build metadata no soportado
    "v",                # solo prefijo
    "abc",              # no es numero
    "1.2.x",            # wildcard
    None,               # None
])
def test_parsear_version_invalidos(texto) -> None:
    assert parsear_version(texto) is None


# --------------------------------------------------------------------
# comparar
# --------------------------------------------------------------------

@pytest.mark.parametrize("actual,remota,esperado", [
    ("1.0.0", "1.0.0", 0),       # igual
    ("1.0.0", "1.0.1", -1),      # patch update
    ("1.0.0", "1.1.0", -1),      # minor update
    ("1.0.0", "2.0.0", -1),      # major update
    ("1.0.1", "1.0.0", 1),       # reloj desincronizado
    ("2.0.0", "1.9.9", 1),       # major mayor
    ("v1.0.0", "v1.0.1", -1),    # con prefijo v
])
def test_comparar(actual: str, remota: str, esperado: int) -> None:
    assert comparar(actual, remota) == esperado


def test_comparar_con_version_invalida_devuelve_0() -> None:
    """Si no podemos parsear una de las dos, devolvemos 0 (no sabemos)."""
    assert comparar("invalida", "1.0.0") == 0
    assert comparar("1.0.0", "invalida") == 0
    assert comparar("invalida", "tambien invalida") == 0


# --------------------------------------------------------------------
# hay_actualizacion
# --------------------------------------------------------------------

def test_hay_actualizacion_true_si_remota_mayor() -> None:
    assert hay_actualizacion("1.0.0", "1.0.1") is True
    assert hay_actualizacion("1.0.0", "2.0.0") is True


def test_hay_actualizacion_false_si_iguales() -> None:
    assert hay_actualizacion("1.0.0", "1.0.0") is False


def test_hay_actualizacion_false_si_remota_menor() -> None:
    assert hay_actualizacion("1.0.1", "1.0.0") is False


# --------------------------------------------------------------------
# parsear_release
# --------------------------------------------------------------------

def _release_json(
    tag: str = "v1.0.1",
    name: str = "ContApp 1.0.1",
    body: str = "## Cambios\n- Fix bug X",
    assets: list | None = None,
    html_url: str = "https://github.com/owner/repo/releases/tag/v1.0.1",
    published_at: str = "2026-07-28T10:00:00Z",
) -> dict:
    """Helper para armar un JSON estilo GitHub Releases."""
    if assets is None:
        assets = [
            {
                "name": "ContApp_Setup-1.0.1.zip",
                "browser_download_url": "https://github.com/dl/setup.zip",
                "size": 1024000,
            },
        ]
    return {
        "tag_name": tag,
        "name": name,
        "body": body,
        "html_url": html_url,
        "published_at": published_at,
        "assets": assets,
    }


def test_parsear_release_completo() -> None:
    """Release valido con asset: devuelve ReleaseInfo con todos los campos."""
    data = _release_json()
    r = parsear_release(data)
    assert r is not None
    assert r["tag"] == "v1.0.1"
    assert r["version"] == "1.0.1"
    assert r["name"] == "ContApp 1.0.1"
    assert "Fix bug X" in r["body"]
    assert r["asset_name"] == "ContApp_Setup-1.0.1.zip"
    assert r["asset_url"] == "https://github.com/dl/setup.zip"
    assert r["asset_size"] == 1024000
    assert r["published_at"] == "2026-07-28T10:00:00Z"


def test_parsear_release_sin_assets_devuelve_none() -> None:
    """Si el release no tiene assets, no podemos actualizar -> None."""
    data = _release_json(assets=[])
    assert parsear_release(data) is None


def test_parsear_release_sin_tag_devuelve_none() -> None:
    data = _release_json()
    data["tag_name"] = None
    assert parsear_release(data) is None


def test_parsear_release_tag_invalido_devuelve_none() -> None:
    data = _release_json(tag="no-es-semver")
    assert parsear_release(data) is None


def test_parsear_release_json_vacio_devuelve_none() -> None:
    assert parsear_release({}) is None


def test_parsear_release_no_es_dict_devuelve_none() -> None:
    assert parsear_release([]) is None
    assert parsear_release("hola") is None
    assert parsear_release(None) is None


def test_parsear_release_elige_asset_con_setup() -> None:
    """Si hay varios assets, prioriza los que digan 'setup' o 'installer'."""
    data = _release_json(assets=[
        {"name": "source.zip", "browser_download_url": "u1", "size": 100},
        {"name": "ContApp_Setup.zip", "browser_download_url": "u2", "size": 200},
        {"name": "checksums.txt", "browser_download_url": "u3", "size": 50},
    ])
    r = parsear_release(data)
    assert r is not None
    assert r["asset_name"] == "ContApp_Setup.zip"


def test_parsear_release_con_nombre_preferido() -> None:
    """Si pasamos nombre_preferido, lo busca exacto primero."""
    data = _release_json(assets=[
        {"name": "foo.zip", "browser_download_url": "u1", "size": 100},
        {"name": "bar.zip", "browser_download_url": "u2", "size": 200},
    ])
    r = parsear_release(data, nombre_preferido="bar.zip")
    assert r is not None
    assert r["asset_name"] == "bar.zip"


def test_parsear_release_cae_a_zip_si_no_hay_setup() -> None:
    """Si no hay 'setup', prioriza .zip o .exe."""
    data = _release_json(assets=[
        {"name": "README.md", "browser_download_url": "u1", "size": 100},
        {"name": "installer.zip", "browser_download_url": "u2", "size": 200},
    ])
    r = parsear_release(data)
    assert r is not None
    assert r["asset_name"] == "installer.zip"