"""Bitacora (logging) de ContApp.

Configura el logging estandar de Python para que escriba a:
- Archivo (data/bitacora/bitacora.log) con rotacion por fecha.
- Consola (stderr).

Pensada para ser llamada UNA vez al inicio del programa (configurar()).
Despues, cualquier modulo puede hacer:
    from utils.bitacora import log
    log.info("mensaje")
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

_FORMAT_CONSOLE = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_FORMAT_ARCHIVO = (
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
_FECHA = "%Y-%m-%d %H:%M:%S"

_logger: logging.Logger | None = None


def configurar(
    ruta_bitacora: Path | str | None = None,
    nivel: int = logging.INFO,
) -> logging.Logger:
    """Inicializa la bitacora. Llamar una sola vez al inicio.

    Args:
        ruta_bitacora: ruta al archivo .log. Si es None, no se escribe a disco.
        nivel: nivel minimo de logging (default INFO).
    """
    global _logger
    logger = logging.getLogger("contapp")
    logger.setLevel(nivel)
    logger.handlers.clear()

    formatter = logging.Formatter(_FORMAT_CONSOLE, datefmt=_FECHA)

    # Consola
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Archivo
    if ruta_bitacora is not None:
        ruta = Path(ruta_bitacora)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(ruta, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(_FORMAT_ARCHIVO, datefmt=_FECHA))
        logger.addHandler(file_handler)

    logger.propagate = False
    _logger = logger
    return logger


def log() -> logging.Logger:
    """Devuelve el logger configurado. Si no se configuro, lo hace con defaults."""
    global _logger
    if _logger is None:
        configurar()
    assert _logger is not None
    return _logger


def timestamp_legible() -> str:
    """Devuelve la fecha/hora actual en formato legible."""
    return datetime.now().strftime(_FECHA)