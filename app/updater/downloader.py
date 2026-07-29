"""UpdaterDownloader: QThread que descarga el instalador de una actualizacion.

Emite:
    progreso(int)      - 0 a 100 (% descargado).
    terminado(Path)    - Ruta al archivo descargado (listo para instalar).
    error(str)         - Mensaje de error.

Caracteristicas:
    - Descarga por chunks (no carga todo en memoria).
    - Guarda a un .partial + renombra al terminar (atomicidad).
    - Si el servidor reporta Content-Length, valida que coincida al final.
    - Cancelable: si recibe `cancelar()`, aborta limpiamente.
"""
from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

from app.version import user_agent
from app.updater.checker import UpdaterError


class UpdaterDownloader(QThread):
    """Descarga un instalador con reporte de progreso."""

    progreso = Signal(int)        # 0..100
    terminado = Signal(object)    # Path
    error = Signal(str)

    # Tamano del chunk al leer (64 KB).
    _CHUNK = 64 * 1024

    def __init__(
        self,
        url: str,
        destino: Path,
        timeout: float = 30.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._destino = Path(destino)
        self._timeout = timeout
        self._cancelado = False

    def cancelar(self) -> None:
        """Marca la descarga como cancelada. El QThread se detiene en el
        proximo chunk."""
        self._cancelado = True

    def run(self) -> None:
        """Descarga el archivo."""
        parcial = self._destino.with_suffix(self._destino.suffix + ".partial")
        try:
            self._destino.parent.mkdir(parents=True, exist_ok=True)
            self._descargar_a(parcial)
        except UpdaterError as e:
            # Limpiar parcial en caso de error.
            try:
                if parcial.exists():
                    parcial.unlink()
            except OSError:
                pass
            self.error.emit(str(e))
            return

        if self._cancelado:
            try:
                if parcial.exists():
                    parcial.unlink()
            except OSError:
                pass
            self.error.emit("Descarga cancelada por el usuario")
            return

        # Atomicidad: rename parcial -> destino.
        try:
            parcial.replace(self._destino)
        except OSError as e:
            self.error.emit(f"No se pudo finalizar el archivo: {e}")
            return
        self.terminado.emit(self._destino)

    # -- Internos ----------------------------------------------------

    def _descargar_a(self, parcial: Path) -> None:
        """Hace el GET y va escribiendo el .partial. Levanta UpdaterError."""
        try:
            req = Request(self._url, headers={
                "User-Agent": user_agent(),
                "Accept": "application/octet-stream",
            })
            with urlopen(req, timeout=self._timeout) as resp:
                content_length = resp.headers.get("Content-Length")
                total = int(content_length) if content_length else None
                downloaded = 0
                last_pct = -1
                with open(parcial, "wb") as f:
                    while True:
                        if self._cancelado:
                            return
                        chunk = resp.read(self._CHUNK)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = int(downloaded * 100 / total)
                            if pct != last_pct:
                                self.progreso.emit(pct)
                                last_pct = pct
                # Si tenemos Content-Length, validar.
                if total is not None and downloaded != total:
                    raise UpdaterError(
                        f"Descarga incompleta: {downloaded} de {total} bytes"
                    )
                # Asegurar 100% al final.
                self.progreso.emit(100)
        except HTTPError as e:
            raise UpdaterError(f"HTTP {e.code}: {e.reason}") from e
        except (URLError, TimeoutError, OSError) as e:
            raise UpdaterError(f"Error de red: {e}") from e