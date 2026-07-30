"""Servicio de configuracion del usuario.

Lee y escribe ``data/settings.json`` (single source of truth desde el
refactor v2). Reemplaza la lectura/escritura del viejo
``data/usuario.json`` que hacia ``Config`` directamente.

Migracion: si existe el viejo ``usuario.json`` y no existe
``settings.json``, se migra automaticamente y se borra el viejo.

API:
    svc = SettingsService(settings_path=Path("data/settings.json"))
    usuario = svc.get("usuario", default=os.environ.get("USERNAME", ""))
    svc.set("modo_prueba", True)   # NO persiste todavia
    svc.save()                     # persiste todo a disco

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Nombre del archivo nuevo.
SETTINGS_FILE: str = "settings.json"

# Nombre del archivo viejo (para migracion automatica).
LEGACY_USER_FILE: str = "usuario.json"


class SettingsService:
    """Servicio de preferencias del usuario.

    Pensado para registrarlo en el contenedor de dependencias:
        container.register(
            "settings",
            lambda c: SettingsService(settings_path=Path("data") / SETTINGS_FILE),
        )
    """

    # Valores por defecto. Se usan si el archivo no existe.
    DEFAULTS: dict[str, Any] = {
        "usuario": "",
        "modo_prueba": False,
        "tema": "claro",
    }

    def __init__(self, settings_path: Path | str) -> None:
        self._path = Path(settings_path)
        self._data: dict[str, Any] = dict(self.DEFAULTS)
        self._cargar()

    # -- I/O ---------------------------------------------------------
    def _cargar(self) -> None:
        """Carga settings.json. Migra del viejo usuario.json si hace falta."""
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data.update(loaded)
            except (OSError, json.JSONDecodeError):
                # Archivo corrupto: usamos defaults.
                pass
        else:
            # Primer arranque: intentar migrar del viejo formato.
            self._intentar_migrar_legacy()

    def _intentar_migrar_legacy(self) -> None:
        """Migra ``data/usuario.json`` al nuevo ``data/settings.json``.

        Si la migracion es exitosa, borra el archivo viejo.
        """
        legacy_path = self._path.parent / LEGACY_USER_FILE
        if not legacy_path.exists():
            return
        try:
            with legacy_path.open("r", encoding="utf-8") as f:
                legacy = json.load(f)
            if isinstance(legacy, dict):
                # Solo copiamos las claves que nos interesan.
                for k in ("usuario", "modo_prueba", "tema"):
                    if k in legacy:
                        self._data[k] = legacy[k]
                # Persistimos la migracion y borramos el viejo.
                self.save()
                legacy_path.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError):
            # Si no se puede leer el legacy, no pasa nada: usamos defaults.
            pass

    def save(self) -> bool:
        """Persiste los settings a disco. Devuelve True si pudo escribir."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False

    # -- API publica -------------------------------------------------
    def get(self, clave: str, default: Any = None) -> Any:
        """Devuelve el valor de ``clave`` o ``default`` si no existe."""
        return self._data.get(clave, default)

    def set(self, clave: str, valor: Any) -> None:
        """Setea ``clave`` en memoria. NO persiste hasta llamar ``save()``."""
        self._data[clave] = valor

    def as_dict(self) -> dict[str, Any]:
        """Devuelve una copia de todos los settings (snapshot)."""
        return dict(self._data)

    # Propiedades de conveniencia (compatibilidad con codigo viejo).
    @property
    def usuario(self) -> str:
        return str(self._data.get("usuario", ""))

    @usuario.setter
    def usuario(self, valor: str) -> None:
        self._data["usuario"] = valor

    @property
    def modo_prueba(self) -> bool:
        return bool(self._data.get("modo_prueba", False))

    @modo_prueba.setter
    def modo_prueba(self, valor: bool) -> None:
        self._data["modo_prueba"] = bool(valor)

    @property
    def tema(self) -> str:
        return str(self._data.get("tema", "claro"))

    @tema.setter
    def tema(self, valor: str) -> None:
        if valor in ("claro", "oscuro"):
            self._data["tema"] = valor
