"""UpdaterChecker: QThread que consulta si hay una version nueva en GitHub.

Solo consulta y parsea (no descarga). Es rapido (~1 request HTTP).
Pensado para correr al iniciar la app, sin bloquear la UI.

Senales:
    terminado(dict | None) - ReleaseInfo parseada, o None si no hay update.
                             None tambien se emite si la respuesta no tiene
                             assets o si la version remota no es mayor.
    error(str)             - Mensaje de error si la consulta fallo.

Uso:
    checker = UpdaterChecker(version_actual="1.0.0", repo="owner/repo")
    checker.terminado.connect(on_resultado)
    checker.error.connect(on_error)
    checker.start()
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

from app.version import GITHUB_API_BASE, GITHUB_REPO, user_agent
from app.updater.version_utils import (
    ReleaseInfo,
    hay_actualizacion,
    parsear_release,
)


class UpdaterError(Exception):
    """Error al consultar GitHub. Distinguible de \"no hay update\"."""
    pass


def _descargar_release_json(repo: str | None, timeout: float) -> dict:
    """Hace el GET a GitHub y devuelve el JSON del release.

    Levanta ``UpdaterError`` si falla la red o si la respuesta es 4xx/5xx.
    Monkey-patcheable: los tests pueden reemplazar ``urlopen`` en el modulo
    ``app.updater.checker`` y el cambio se ve aqui.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo or GITHUB_REPO}/releases/latest"
    try:
        req = Request(url, headers={
            "User-Agent": user_agent(),
            "Accept": "application/vnd.github+json",
        })
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise UpdaterError(f"HTTP {e.code}: {e.reason}") from e
    except (URLError, TimeoutError, OSError) as e:
        raise UpdaterError(f"Error de red: {e}") from e


class UpdaterChecker(QThread):
    """Consulta el ultimo release de GitHub y emite si hay update."""

    terminado = Signal(object)   # ReleaseInfo | None
    error = Signal(str)

    def __init__(
        self,
        version_actual: str,
        repo: str | None = None,
        timeout: float = 5.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._version_actual = version_actual
        self._repo = repo or GITHUB_REPO
        self._timeout = timeout

    def run(self) -> None:
        """Consulta la API y emite el resultado.

        Distingue 3 casos:
            - hay update        -> terminado(release)
            - no hay update     -> terminado(None)
            - error de red/etc  -> error(mensaje)
        """
        try:
            data = _descargar_release_json(self._repo, self._timeout)
        except UpdaterError as e:
            self.error.emit(str(e))
            return
        except json.JSONDecodeError as e:
            self.error.emit(f"Respuesta invalida: {e}")
            return

        release = parsear_release(data)
        if release is None:
            self.terminado.emit(None)
            return
        if hay_actualizacion(self._version_actual, release["version"]):
            self.terminado.emit(release)
        else:
            self.terminado.emit(None)


def chequear_actualizacion_bloqueante(
    version_actual: str,
    repo: str | None = None,
    timeout: float = 5.0,
) -> ReleaseInfo | None:
    """Version bloqueante del checker (sin QThread).

    Util para tests y para CLI. Devuelve ``ReleaseInfo`` si hay update,
    None en caso contrario (o si hubo error, en cuyo caso imprime a stderr).
    """
    try:
        data = _descargar_release_json(repo, timeout)
    except UpdaterError as e:
        print(f"[updater] {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[updater] Respuesta invalida: {e}")
        return None

    release = parsear_release(data)
    if release is None:
        return None
    if hay_actualizacion(version_actual, release["version"]):
        return release
    return None