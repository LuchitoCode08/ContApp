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

from pathlib import Path

from utils.json_manager import escribir_json


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

    def limpiar_antiguos(self, mantener: int = 20) -> int:
        """Con la politica actual no aplica: solo hay un backup por archivo.

        Se conserva el metodo por compatibilidad, pero no borra nada.

        Args:
            mantener: ignorado en la politica ``uno_por_archivo``.

        Returns:
            Siempre 0.
        """
        return 0
