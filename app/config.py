"""Configuracion global de ContApp (singleton).

Centraliza:
- rutas del proyecto (raiz, jsons, resultados, log)
- usuario activo
- modo_prueba (True/False)
- tema (claro / oscuro)
- procesos disponibles

La UI y los modulos de ``core`` leen esta config; nadie lee rutas
ni constantes del entorno directamente.

Persistencia:
- usuario, modo_prueba y tema se guardan en ``data/usuario.json``.
- Al arrancar se cargan; al cambiar el modo_prueba o el tema, se
  guardan inmediatamente.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _detectar_raiz() -> Path:
    """Devuelve la raiz del proyecto según el contexto de ejecucion.

    - En desarrollo (corriendo ``python main.py``): directorio donde esta
      ``main.py`` (2 niveles arriba de ``app/config.py``).
    - Empaquetado con PyInstaller (``--onedir`` o ``--onefile``): directorio
      donde esta el ejecutable. Asi ``jsons/`` queda al lado del .exe,
      que es lo que queremos para que el usuario pueda editar las reglas
      sin recompilar.

    Detecta el caso empaquetado con ``getattr(sys, "frozen", False)``,
    que PyInstaller setea automaticamente.
    """
    if getattr(sys, "frozen", False):
        # Ejecutandose como .exe -> el "raiz" es donde esta el binario.
        return Path(sys.executable).resolve().parent
    # Desarrollo: 2 niveles arriba de app/config.py -> raiz del proyecto.
    return Path(__file__).resolve().parent.parent


# Raiz del proyecto.
RAIZ: Path = _detectar_raiz()

# Carpetas importantes (relativas a la raiz).
DOCUMENTS: Path = Path.home() / "Documents"
JSONS_DIR: Path = RAIZ / "jsons"
RESULTADOS_DIR: Path = DOCUMENTS / "ContApp_Resultados"


def _data_dir() -> Path:
    """Directorio de estado (data/). Tests pueden monkey-patchear esta funcion."""
    return RAIZ / "data"


def _log_dir() -> Path:
    """Directorio de logs (log/). Tests pueden monkey-patchear esta funcion."""
    return RAIZ / "log"


# Aliases para compatibilidad con el codigo existente.
DATA_DIR: Path = _data_dir()
LOG_DIR: Path = _log_dir()
BITACORA_DIR: Path = LOG_DIR
BITACORA_LOG: Path = LOG_DIR / "bitacora.log"

# Archivo donde se persisten las preferencias del usuario.
PREFERENCIAS: Path = DATA_DIR / "usuario.json"


@dataclass
class Config:
    """Estado global de la app."""

    usuario: str = ""
    # Por default la app arranca en modo produccion.
    # El usuario debe activar explicitamente el modo prueba.
    modo_prueba: bool = False
    # Tema visual: "claro" (default) o "oscuro".
    tema: str = "claro"

    # Procesos disponibles: nombre -> clase.
    # Se llena en ``inicializar_procesos()``.
    procesos: dict = field(default_factory=dict)

    def ruta_json(self, proceso: str, archivo: str) -> Path:
        """Devuelve la ruta a un JSON de un proceso."""
        return JSONS_DIR / proceso / archivo

    def nombres_procesos(self) -> list[str]:
        """Lista los nombres de procesos disponibles."""
        return list(self.procesos.keys())

    # -- Persistencia ------------------------------------------------

    def cargar_preferencias(self) -> None:
        """Carga preferencias desde ``data/usuario.json`` (si existe)."""
        if not PREFERENCIAS.exists():
            return
        try:
            with open(PREFERENCIAS, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return  # archivo corrupto: silencioso, no rompe el arranque
        self.usuario = str(data.get("usuario", self.usuario)) or self.usuario
        self.modo_prueba = bool(data.get("modo_prueba", self.modo_prueba))
        tema = data.get("tema", self.tema)
        if tema in ("claro", "oscuro"):
            self.tema = tema

    def guardar_preferencias(self) -> None:
        """Guarda preferencias en ``data/usuario.json``.

        No lanza excepciones: si no se puede escribir, la app sigue
        funcionando, solo no se persiste entre sesiones.

        Usa ``PREFERENCIAS.parent`` (no la constante ``DATA_DIR``) para que
        monkey-patching de ``PREFERENCIAS`` en tests funcione correctamente.
        """
        try:
            PREFERENCIAS.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "usuario": self.usuario,
                "modo_prueba": self.modo_prueba,
                "tema": self.tema,
            }
            with open(PREFERENCIAS, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass


_config: Config | None = None


def get_config() -> Config:
    """Devuelve la instancia singleton de Config."""
    global _config
    if _config is None:
        _config = Config()
        inicializar_procesos(_config)
        # Primero cargamos preferencias (usuario, modo_prueba, tema).
        _config.cargar_preferencias()
        # Si no hay preferencias guardadas, usamos el USERNAME del SO.
        if not _config.usuario:
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