"""Tests del UpdaterChecker y la version bloqueante.

Los tests que tocan red usan `monkeypatch` para mockear `urlopen`.
No hacemos requests reales a GitHub en CI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pytest

from app.updater.checker import (
    UpdaterChecker,
    chequear_actualizacion_bloqueante,
)


# --------------------------------------------------------------------
# Helpers de mock
# --------------------------------------------------------------------

class FakeResponse:
    """Simula una respuesta de urlopen para tests."""

    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _release_json(
    tag: str = "v1.0.1",
    assets: list | None = None,
) -> dict:
    if assets is None:
        assets = [
            {
                "name": "ContApp_Setup.zip",
                "browser_download_url": "https://example.com/setup.zip",
                "size": 1024,
            }
        ]
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "Cambios",
        "html_url": "https://example.com",
        "published_at": "2026-07-28T10:00:00Z",
        "assets": assets,
    }


def _patch_urlopen(monkeypatch, payload, error=None):
    """Mockea urlopen. Si error no es None, lo lanza en vez de devolver."""
    def fake_urlopen(req, timeout=None):
        if error is not None:
            raise error
        return FakeResponse(json.dumps(payload))

    monkeypatch.setattr("app.updater.checker.urlopen", fake_urlopen)


# --------------------------------------------------------------------
# UpdaterChecker (QThread)
# --------------------------------------------------------------------

def _run_checker(checker: UpdaterChecker) -> tuple[list, list]:
    """Ejecuta el checker y devuelve (terminados, errores) capturados."""
    terminados: list = []
    errores: list = []
    checker.terminado.connect(terminados.append)
    checker.error.connect(errores.append)
    checker.run()  # sincronico para tests
    return terminados, errores


def test_checker_encuentra_actualizacion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Version actual 1.0.0, remote 1.0.1 -> debe emitir ReleaseInfo."""
    _patch_urlopen(monkeypatch, _release_json("v1.0.1"))
    checker = UpdaterChecker(version_actual="1.0.0")
    terminados, errores = _run_checker(checker)
    assert errores == []
    assert len(terminados) == 1
    assert terminados[0]["version"] == "1.0.1"


def test_checker_no_hay_actualizacion_si_iguales(monkeypatch: pytest.MonkeyPatch) -> None:
    """Version actual = remota -> emite None (no hay update)."""
    _patch_urlopen(monkeypatch, _release_json("v1.0.0"))
    checker = UpdaterChecker(version_actual="1.0.0")
    terminados, errores = _run_checker(checker)
    assert errores == []
    assert terminados == [None]


def test_checker_no_hay_actualizacion_si_remota_menor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si el reloj del server esta atras -> emite None."""
    _patch_urlopen(monkeypatch, _release_json("v0.9.0"))
    checker = UpdaterChecker(version_actual="1.0.0")
    terminados, errores = _run_checker(checker)
    assert errores == []
    assert terminados == [None]


def test_checker_404_es_error_reportado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un 404 (repo sin releases) se reporta como error y NO emite terminado."""
    _patch_urlopen(
        monkeypatch,
        payload={},
        error=HTTPError(url="http://x", code=404, msg="Not Found", hdrs=None, fp=None),
    )
    checker = UpdaterChecker(version_actual="1.0.0")
    terminados, errores = _run_checker(checker)
    assert terminados == []
    assert len(errores) == 1
    assert "404" in errores[0]



def test_checker_error_de_red_se_reporta(monkeypatch: pytest.MonkeyPatch) -> None:
    """URLError -> emite error y NO terminado."""
    _patch_urlopen(
        monkeypatch,
        payload={},
        error=URLError("no internet"),
    )
    checker = UpdaterChecker(version_actual="1.0.0")
    terminados, errores = _run_checker(checker)
    assert terminados == []
    assert len(errores) == 1
    assert "red" in errores[0].lower()


def test_checker_respuesta_invalida_reporta_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON invalido -> emite error."""
    _patch_urlopen(monkeypatch, payload=None)  # None -> json.JSONDecodeError
    # Mejor: pasar un string que no es JSON
    def fake_urlopen(req, timeout=None):
        return FakeResponse("esto no es json")
    monkeypatch.setattr("app.updater.checker.urlopen", fake_urlopen)

    checker = UpdaterChecker(version_actual="1.0.0")
    terminados, errores = _run_checker(checker)
    assert terminados == []
    assert len(errores) == 1


def test_checker_release_sin_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Release existe pero sin assets -> emite None (no podemos descargar)."""
    _patch_urlopen(monkeypatch, _release_json("v1.0.1", assets=[]))
    checker = UpdaterChecker(version_actual="1.0.0")
    terminados, errores = _run_checker(checker)
    assert errores == []
    assert terminados == [None]


def test_checker_usa_repo_personalizado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si pasamos repo, lo usa en la URL."""

    captured_urls: list[str] = []

    def fake_urlopen(req, timeout=None):
        captured_urls.append(req.full_url)
        return FakeResponse(json.dumps(_release_json("v1.0.1")))

    monkeypatch.setattr("app.updater.checker.urlopen", fake_urlopen)
    checker = UpdaterChecker(version_actual="1.0.0", repo="otro/repo")
    checker.run()
    assert "otro/repo" in captured_urls[0]


def test_checker_incluye_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica que mandamos User-Agent para evitar rate limit."""

    captured_headers: list[dict] = []

    def fake_urlopen(req, timeout=None):
        captured_headers.append(dict(req.headers))
        return FakeResponse(json.dumps(_release_json("v1.0.1")))

    monkeypatch.setattr("app.updater.checker.urlopen", fake_urlopen)
    checker = UpdaterChecker(version_actual="1.0.0")
    checker.run()
    ua = captured_headers[0].get("User-agent") or captured_headers[0].get("User-Agent")
    assert ua is not None
    assert "ContApp" in ua


# --------------------------------------------------------------------
# chequear_actualizacion_bloqueante (sin QThread)
# --------------------------------------------------------------------

def test_chequear_bloqueante_encuentra_update(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_urlopen(monkeypatch, _release_json("v1.0.1"))
    r = chequear_actualizacion_bloqueante("1.0.0")
    assert r is not None
    assert r["version"] == "1.0.1"


def test_chequear_bloqueante_sin_update(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_urlopen(monkeypatch, _release_json("v1.0.0"))
    assert chequear_actualizacion_bloqueante("1.0.0") is None


def test_chequear_bloqueante_error_devuelve_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """En modo bloqueante, un error de red devuelve None (no rompe)."""
    _patch_urlopen(monkeypatch, payload={}, error=URLError("fail"))
    assert chequear_actualizacion_bloqueante("1.0.0") is None