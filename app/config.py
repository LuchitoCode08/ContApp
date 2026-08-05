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
- usuario, modo_prueba y tema se guardan en ``data/settings.json``.
- Al arrancar se cargan; al cambiar el modo_prueba o el tema, se
  guardan inmediatamente.
- ``SettingsService`` se encarga de la lectura/escritura y de la
  migracion automatica desde el viejo ``data/usuario.json``.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from services.settings_service import SettingsService


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
PREFERENCIAS: Path = DATA_DIR / "settings.json"


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

    def _settings(self) -> SettingsService:
        """Devuelve un SettingsService apuntando a ``PREFERENCIAS``."""
        return SettingsService(settings_path=PREFERENCIAS)

    def cargar_preferencias(self) -> None:
        """Carga preferencias desde ``data/settings.json`` (si existe).

        ``SettingsService`` migra automaticamente desde el viejo
        ``data/usuario.json`` si es la primera vez.
        """
        try:
            svc = self._settings()
        except OSError:
            return  # no se puede acceder al archivo: no rompe el arranque
        if svc.usuario:
            self.usuario = svc.usuario
        self.modo_prueba = svc.modo_prueba
        if svc.tema in ("claro", "oscuro"):
            self.tema = svc.tema

    def guardar_preferencias(self) -> None:
        """Guarda preferencias en ``data/settings.json``.

        No lanza excepciones: si no se puede escribir, la app sigue
        funcionando, solo no se persiste entre sesiones.

        Usa ``PREFERENCIAS`` (no la constante ``DATA_DIR``) para que
        monkey-patching de ``PREFERENCIAS`` en tests funcione correctamente.
        """
        try:
            svc = self._settings()
            svc.usuario = self.usuario
            svc.modo_prueba = self.modo_prueba
            svc.tema = self.tema
            svc.save()
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
