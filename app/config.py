"""Configuración global de ContApp (singleton).

Centraliza:
- rutas del proyecto (raiz, jsons, resultados, data)
- modo_prueba (True/False)
- tema (claro)
- procesos disponibles
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _detectar_raiz() -> Path:
    """Devuelve la raíz del proyecto según el contexto de ejecución."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


RAIZ: Path = _detectar_raiz()


def _detectar_jsons_dir() -> Path:
    """Devuelve la carpeta jsons/ del proyecto."""
    lado_exe = RAIZ / "jsons"
    if lado_exe.exists():
        return lado_exe
    interno = RAIZ / "_internal" / "jsons"
    if interno.exists():
        return interno
    return lado_exe


DOCUMENTS: Path = Path.home() / "Documents"
JSONS_DIR: Path = _detectar_jsons_dir()
RESULTADOS_DIR: Path = DOCUMENTS / "ContApp_Resultados"
DATA_DIR: Path = RAIZ / "data"
PREFERENCIAS: Path = DATA_DIR / "settings.json"


@dataclass
class Config:
    """Estado global de la aplicación."""

    usuario: str = ""
    modo_prueba: bool = False
    tema: str = "claro"
    procesos: dict = field(default_factory=dict)

    def ruta_json(self, proceso: str, archivo: str) -> Path:
        return JSONS_DIR / proceso / archivo

    def nombres_procesos(self) -> list[str]:
        return list(self.procesos.keys())

    def cargar_preferencias(self) -> None:
        """Carga preferencias desde data/settings.json."""
        if not PREFERENCIAS.exists():
            return
        try:
            with PREFERENCIAS.open("r", encoding="utf-8") as f:
                datos = json.load(f)
            if isinstance(datos, dict):
                self.usuario = datos.get("usuario", self.usuario)
                self.modo_prueba = bool(datos.get("modo_prueba", False))
                self.tema = datos.get("tema", "claro")
        except (OSError, json.JSONDecodeError):
            pass

    def guardar_preferencias(self) -> None:
        """Guarda preferencias en data/settings.json."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            datos = {
                "usuario": self.usuario,
                "modo_prueba": self.modo_prueba,
                "tema": self.tema,
            }
            with PREFERENCIAS.open("w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except OSError:
            pass


_config: Config | None = None


def get_config() -> Config:
    """Devuelve la instancia singleton de Config."""
    global _config
    if _config is None:
        _config = Config()
        inicializar_procesos(_config)
        _config.cargar_preferencias()
        if not _config.usuario:
            _config.usuario = os.environ.get("USERNAME", "usuario")
    return _config


def inicializar_procesos(cfg: Config) -> None:
    """Registra los 3 procesos disponibles en cfg.procesos."""
    from core.comprobante import ProcesoComprobante
    from core.fierro import ProcesoFierro
    from core.zeus import ProcesoZeus

    cfg.procesos = {
        "comprobante": ProcesoComprobante,
        "fierro": ProcesoFierro,
        "zeus": ProcesoZeus,
    }
