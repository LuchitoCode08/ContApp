"""Configuracion global de ContApp (singleton).

Centraliza:
- rutas del proyecto (raiz, jsons, resultados, bitacora)
- usuario activo
- modo_prueba (True/False)
- procesos disponibles

La UI y los modulos de ``core`` leen esta config; nadie lee rutas
ni constantes del entorno directamente.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Raiz del proyecto (donde esta main.py).
RAIZ: Path = Path(__file__).resolve().parent.parent

# Carpetas importantes (relativas a la raiz).
DATA_DIR: Path = RAIZ / "data"
JSONS_DIR: Path = RAIZ / "jsons"
RESULTADOS_DIR: Path = RAIZ / "resultados"
BITACORA_DIR: Path = DATA_DIR / "bitacora"
BITACORA_LOG: Path = BITACORA_DIR / "bitacora.log"


@dataclass
class Config:
    """Estado global de la app."""

    usuario: str = ""
    modo_prueba: bool = True

    # Procesos disponibles: nombre -> clase.
    # Se llena en ``inicializar_procesos()``.
    procesos: dict = field(default_factory=dict)

    def ruta_json(self, proceso: str, archivo: str) -> Path:
        """Devuelve la ruta a un JSON de un proceso."""
        return JSONS_DIR / proceso / archivo

    def nombres_procesos(self) -> list[str]:
        """Lista los nombres de procesos disponibles."""
        return list(self.procesos.keys())


_config: Config | None = None


def get_config() -> Config:
    """Devuelve la instancia singleton de Config."""
    global _config
    if _config is None:
        _config = Config()
        inicializar_procesos(_config)
        _config.usuario = os.environ.get("USERNAME", "usuario")
    return _config


def inicializar_procesos(cfg: Config) -> None:
    """Carga las clases de los 3 procesos en ``cfg.procesos``."""
    # Import lazy para no romper imports circulares.
    from procesos.comprobante import ProcesoComprobante
    from procesos.fierro import ProcesoFierro
    from procesos.zeus import ProcesoZeus

    cfg.procesos = {
        "comprobante": ProcesoComprobante,
        "fierro": ProcesoFierro,
        "zeus": ProcesoZeus,
    }