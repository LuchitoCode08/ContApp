"""Bootstrap del contenedor de dependencias.

Registra las factories que producen los servicios y repositorios del
proyecto. Pensado para llamarse UNA vez al arrancar la app, antes de
que ningun modulo pida una dependencia.

Uso:
    from app.bootstrap import bootstrap
    from app.container import container

    bootstrap(container)
    settings = container.get_singleton("settings")

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.config import DATA_DIR, JSONS_DIR, LOG_DIR
from app.container import Container
from services.backup_service import BackupService
from services.reporte_service import ReporteService
from services.settings_service import SETTINGS_FILE, SettingsService


def _settings_factory(c: Container) -> SettingsService:
    return SettingsService(settings_path=DATA_DIR / SETTINGS_FILE)


def _bitacora_factory(c: Container) -> logging.Logger:
    """Carga la bitacora solo si no esta ya configurada."""
    from utils.bitacora import configurar
    return configurar(ruta_bitacora=LOG_DIR / "bitacora.log")


def _backup_factory(c: Container) -> BackupService:
    return BackupService(carpeta_backups=DATA_DIR / "backups")


def _reporte_factory(c: Container) -> ReporteService:
    return ReporteService(
        bitacora=c.get_singleton("bitacora"),
        carpeta_reportes=DATA_DIR / "reportes",
    )


def bootstrap(c: Container) -> None:
    """Registra todas las dependencias por defecto en ``c``.

    Idempotente: si las factories ya estan registradas, las reemplaza.
    """
    c.register("settings", _settings_factory)
    c.register("bitacora", _bitacora_factory)
    c.register("backup_service", _backup_factory)
    c.register("reporte_service", _reporte_factory)

    # Migrar backups huérfanos generados por versiones anteriores del
    # editor (que guardaban en jsons/<proceso>/.backups/) hacia la
    # carpeta central data/backups/ donde los lista la UI.
    try:
        svc = c.get_singleton("backup_service")
        svc.migrar_backups_huerfanos(JSONS_DIR)
    except Exception:
        # Nunca debe impedir el arranque de la app.
        logging.getLogger(__name__).exception(
            "Fallo la migracion de backups huérfanos"
        )
