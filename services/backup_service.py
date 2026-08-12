"""Servicio de backups automaticos.

Encapsula la politica de backups: cuando hacer uno, donde guardar,
cuantos retener. Hoy delega en ``utils/json_manager.escribir_json``
(misma logica que ya esta probada). La politica actual mantiene
**un solo backup por archivo JSON**: cada edicion sobrescribe la
version anterior guardada en ``data/backups/``.

API:
    svc = BackupService(carpeta_backups=Path("data/backups"))
    backup_path = svc.backup_antes_de_escribir(Path("jsons/foo.json"), datos)

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from utils.json_manager import escribir_json, restaurar_json


logger = logging.getLogger(__name__)


class BackupService:
    """Servicio de backups automaticos."""

    def __init__(
        self,
        carpeta_backups: Path | str,
        *,
        politica: str = "uno_por_archivo",
    ) -> None:
        """
        Args:
            carpeta_backups: raiz donde se guardan los backups.
            politica: ``"uno_por_archivo"`` (default) mantiene un solo
                backup por JSON, sobrescrito en cada escritura. Es decir,
                siempre se conserva la ultima version anterior del archivo.
        """
        self._raiz = Path(carpeta_backups)
        self._politica = politica

    @property
    def carpeta_backups(self) -> Path:
        return self._raiz

    def backup_antes_de_escribir(
        self,
        ruta_json: Path | str,
        contenido: dict,
        *,
        proceso: str | None = None,
    ) -> Path | None:
        """Hace backup del JSON existente (si hay) y luego lo escribe.

        Args:
            ruta_json: ruta al JSON destino.
            contenido: diccionario a serializar.
            proceso: nombre del proceso (para organizar backups por
                proceso, ej: ``data/backups/comprobante/foo.json``).
                Si es None, los backups van todos al mismo nivel.

        Returns:
            Ruta del backup si se creo, None si no.
        """
        ruta = Path(ruta_json)
        carpeta = self._raiz
        if proceso is not None:
            carpeta = carpeta / proceso
        return escribir_json(
            ruta,
            contenido,
            hacer_backup=True,
            carpeta_backups=carpeta,
        )

    def listar_backups(self, proceso: str | None = None) -> list[Path]:
        """Lista todos los backups (ordenados por fecha, mas reciente primero)."""
        carpeta = self._raiz / proceso if proceso else self._raiz
        if not carpeta.exists():
            return []
        return sorted(
            carpeta.rglob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def ruta_backup(
        self,
        ruta_json: Path | str,
        *,
        proceso: str | None = None,
    ) -> Path | None:
        """Devuelve la ruta del backup de un JSON si existe.

        Args:
            ruta_json: ruta del JSON original.
            proceso: nombre del proceso (para ubicar la carpeta de backups).

        Returns:
            Ruta del backup si existe, None si no.
        """
        ruta = Path(ruta_json)
        carpeta = self._raiz / proceso if proceso else self._raiz
        backup = carpeta / ruta.name
        return backup if backup.exists() else None

    def tiene_backup(
        self,
        ruta_json: Path | str,
        *,
        proceso: str | None = None,
    ) -> bool:
        """True si existe un backup para el JSON indicado."""
        return self.ruta_backup(ruta_json, proceso=proceso) is not None

    def restaurar_backup(
        self,
        ruta_json: Path | str,
        *,
        proceso: str | None = None,
    ) -> Path:
        """Restaura el backup asociado a un JSON.

        Args:
            ruta_json: ruta del JSON destino.
            proceso: nombre del proceso para ubicar la carpeta de backups.

        Returns:
            Ruta del JSON restaurado.

        Raises:
            FileNotFoundError: si no existe backup para el archivo.
        """
        ruta = Path(ruta_json)
        carpeta = self._raiz / proceso if proceso else self._raiz
        backup = carpeta / ruta.name
        if not backup.exists():
            raise FileNotFoundError(f"No hay backup para {ruta.name}")
        return restaurar_json(ruta, backup)

    def limpiar_antiguos(self, mantener: int = 20) -> int:
        """Con la politica actual no aplica: solo hay un backup por archivo.

        Se conserva el metodo por compatibilidad, pero no borra nada.

        Args:
            mantener: ignorado en la politica ``uno_por_archivo``.

        Returns:
            Siempre 0.
        """
        return 0

    def migrar_backups_huerfanos(
        self,
        jsons_dir: Path | str,
    ) -> dict[str, int]:
        """Mueve backups de ``jsons/<proceso>/.backups/`` a ``data/backups/<proceso>/``.

        Durante el refactor v2 el editor escribia backups en
        ``jsons/<proceso>/.backups/`` en lugar de ``data/backups/<proceso>/``.
        Este metodo migra esos backups huérfanos para que aparezcan en la
        pantalla de copias de seguridad.

        Si ya existe un backup en destino, se conserva el mas reciente
        (por fecha de modificacion) y se descarta el mas viejo.

        Args:
            jsons_dir: raiz donde estan los JSONs editables (``jsons/``).

        Returns:
            Diccionario con contadores: ``{"movidos": N, "omitidos": N,
            "errores": N, "dirs_limpios": N}``.
        """
        jsons_dir = Path(jsons_dir)
        stats = {"movidos": 0, "omitidos": 0, "errores": 0, "dirs_limpios": 0}

        if not jsons_dir.exists():
            return stats

        for proc_dir in jsons_dir.iterdir():
            if not proc_dir.is_dir():
                continue
            backups_legacy = proc_dir / ".backups"
            if not backups_legacy.exists() or not backups_legacy.is_dir():
                continue

            destino_proc = self._raiz / proc_dir.name
            destino_proc.mkdir(parents=True, exist_ok=True)

            for backup in sorted(backups_legacy.glob("*.json")):
                destino = destino_proc / backup.name
                try:
                    if destino.exists():
                        # Conservar el mas reciente.
                        if backup.stat().st_mtime > destino.stat().st_mtime:
                            shutil.move(str(backup), str(destino))
                            stats["movidos"] += 1
                        else:
                            backup.unlink()
                            stats["omitidos"] += 1
                    else:
                        shutil.move(str(backup), str(destino))
                        stats["movidos"] += 1
                except OSError as exc:
                    logger.warning(
                        "No se pudo migrar backup %s: %s", backup, exc
                    )
                    stats["errores"] += 1

            # Si el directorio legacy quedo vacio, lo borramos.
            try:
                if backups_legacy.exists() and not any(backups_legacy.iterdir()):
                    backups_legacy.rmdir()
                    stats["dirs_limpios"] += 1
            except OSError as exc:
                logger.warning(
                    "No se pudo borrar carpeta vacia %s: %s",
                    backups_legacy,
                    exc,
                )

        total = stats["movidos"] + stats["omitidos"]
        if total:
            logger.info(
                "Migracion de backups: %d movidos, %d omitidos, "
                "%d errores, %d dirs limpiados",
                stats["movidos"],
                stats["omitidos"],
                stats["errores"],
                stats["dirs_limpios"],
            )
        return stats
