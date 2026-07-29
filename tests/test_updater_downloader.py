"""Tests del UpdaterDownloader (descarga de instalador).

Los tests mockean `urlopen` para no hacer requests reales a GitHub.
"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pytest

from app.updater.downloader import UpdaterDownloader


# --------------------------------------------------------------------
# Helpers de mock
# --------------------------------------------------------------------

class FakeHTTPResponse:
    """Simula un HTTPResponse para el downloader."""

    def __init__(self, body: bytes, content_length: int | None = None,
                 chunk_size: int = 8):
        self._stream = BytesIO(body)
        self._body = body
        self._chunk_size = chunk_size
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def read(self, n: int = -1) -> bytes:
        return self._stream.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _patch_urlopen(monkeypatch, response=None, error=None):
    """Mockea urlopen."""
    def fake_urlopen(req, timeout=None):
        if error is not None:
            raise error
        return response

    monkeypatch.setattr("app.updater.downloader.urlopen", fake_urlopen)


def _run_downloader(d: UpdaterDownloader) -> tuple[list, list, list]:
    """Ejecuta el downloader y devuelve (progresos, terminados, errores)."""
    progresos: list[int] = []
    terminados: list = []
    errores: list[str] = []
    d.progreso.connect(progresos.append)
    d.terminado.connect(terminados.append)
    d.error.connect(errores.append)
    d.run()  # sincronico para tests
    return progresos, terminados, errores


# --------------------------------------------------------------------
# Descarga exitosa
# --------------------------------------------------------------------

def test_descarga_exitosa_escribe_archivo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Descarga un cuerpo de 1 KB y verifica que el archivo final tiene el contenido."""
    body = b"A" * 1024
    _patch_urlopen(monkeypatch, response=FakeHTTPResponse(body, content_length=len(body)))
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    progresos, terminados, errores = _run_downloader(d)
    assert errores == []
    assert len(terminados) == 1
    assert terminados[0] == destino
    assert destino.exists()
    assert destino.read_bytes() == body


def test_descarga_emite_progreso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Emite multiples eventos de progreso durante la descarga."""
    body = b"B" * 1024
    _patch_urlopen(monkeypatch, response=FakeHTTPResponse(body, content_length=len(body)))
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    progresos, _, _ = _run_downloader(d)
    # Debe emitir al menos el 100% final.
    assert 100 in progresos
    # Y algun progreso intermedio (no solo el 100%).
    assert len(progresos) >= 2


def test_descarga_emitte_100_al_final(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """El ultimo evento de progreso SIEMPRE es 100."""
    body = b"C" * 100
    _patch_urlopen(monkeypatch, response=FakeHTTPResponse(body, content_length=100))
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    progresos, _, _ = _run_downloader(d)
    assert progresos[-1] == 100


def test_descarga_sin_content_length(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si el servidor no manda Content-Length, descarga igual y emite 100 al final."""
    body = b"D" * 100
    _patch_urlopen(monkeypatch, response=FakeHTTPResponse(body, content_length=None))
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    progresos, terminados, errores = _run_downloader(d)
    assert errores == []
    assert len(terminados) == 1
    assert progresos[-1] == 100


def test_descarga_incompleta_reporta_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si el servidor dice Content-Length=1000 pero corta a los 500 -> error."""
    # Enviamos solo 500 bytes pero mentimos diciendo 1000.
    _patch_urlopen(
        monkeypatch,
        response=FakeHTTPResponse(b"X" * 500, content_length=1000),
    )
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    progresos, terminados, errores = _run_downloader(d)
    assert terminados == []
    assert len(errores) == 1
    assert "incompleta" in errores[0].lower()


# --------------------------------------------------------------------
# Errores
# --------------------------------------------------------------------

def test_error_http_se_reporta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 404 -> error reportado, NO terminado."""
    _patch_urlopen(
        monkeypatch,
        error=HTTPError(url="http://x", code=404, msg="Not Found", hdrs=None, fp=None),
    )
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    _, terminados, errores = _run_downloader(d)
    assert terminados == []
    assert len(errores) == 1
    assert "404" in errores[0]


def test_error_red_se_reporta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """URLError -> error."""
    _patch_urlopen(monkeypatch, error=URLError("no internet"))
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    _, terminados, errores = _run_downloader(d)
    assert terminados == []
    assert len(errores) == 1
    assert "red" in errores[0].lower()


def test_error_limpia_archivo_parcial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si falla la descarga, NO debe quedar archivo .partial suelto."""
    _patch_urlopen(monkeypatch, error=URLError("fail"))
    destino = tmp_path / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    _run_downloader(d)
    parcial = destino.with_suffix(destino.suffix + ".partial")
    assert not parcial.exists()
    assert not destino.exists()


# --------------------------------------------------------------------
# Cancelacion
# --------------------------------------------------------------------

def test_cancelar_aborta_descarga(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si llamamos cancelar() durante la descarga, se aborta limpiamente."""

    class CancelableResponse(FakeHTTPResponse):
        def __init__(self, body, **kw):
            super().__init__(body, **kw)
            self._canceled = False

        def read(self, n: int = -1) -> bytes:
            # Disparar cancel despues del primer chunk.
            if self._stream.tell() == 0:
                self._canceled_after = True
            return super().read(n)

    body = b"E" * 1024
    resp = FakeHTTPResponse(body, content_length=len(body))
    _patch_urlopen(monkeypatch, response=resp)
    destino = tmp_path / "installer.zip"

    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    # Conectar cancelar al primer progreso emitido.
    d.progreso.connect(lambda pct: d.cancelar() if pct >= 0 else None)
    _, terminados, errores = _run_downloader(d)
    assert terminados == []
    assert len(errores) == 1
    assert "cancelada" in errores[0].lower()
    # Y NO debe haber archivo final ni parcial.
    assert not destino.exists()


# --------------------------------------------------------------------
# Atomicidad
# --------------------------------------------------------------------

def test_archivo_final_no_existe_hasta_terminar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Durante la descarga solo existe .partial; el rename a final es al final."""
    body = b"F" * 100
    _patch_urlopen(monkeypatch, response=FakeHTTPResponse(body, content_length=100))
    destino = tmp_path / "installer.zip"
    parcial = destino.with_suffix(destino.suffix + ".partial")
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    _run_downloader(d)
    # Despues de terminar: existe destino, NO existe parcial.
    assert destino.exists()
    assert not parcial.exists()


def test_crea_directorio_destino_si_no_existe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si el directorio destino no existe, lo crea."""
    body = b"G" * 50
    _patch_urlopen(monkeypatch, response=FakeHTTPResponse(body, content_length=50))
    destino = tmp_path / "subdir" / "nested" / "installer.zip"
    d = UpdaterDownloader(url="http://x/setup.zip", destino=destino)
    _, terminados, _ = _run_downloader(d)
    assert len(terminados) == 1
    assert destino.exists()