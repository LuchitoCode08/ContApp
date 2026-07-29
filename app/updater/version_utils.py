"""Utilidades para comparar versiones y parsear releases de GitHub.

Funciones puras (sin I/O, sin UI). Ideales para testear.
"""
from __future__ import annotations

import re
from typing import TypedDict


class ReleaseInfo(TypedDict):
    """Informacion minima de un release de GitHub que nos interesa."""

    tag: str               # ej: "v1.0.1" (sin normalizar; respetar lo de GitHub)
    version: str           # ej: "1.0.1" (sin prefijo "v")
    name: str              # ej: "ContApp 1.0.1"
    body: str              # Notas de la version (markdown)
    published_at: str      # ISO 8601
    html_url: str          # Link al release en GitHub
    asset_name: str        # Nombre del .zip de instalacion
    asset_url: str         # URL para descargar el .zip
    asset_size: int        # Tamano en bytes


# Regex para semver estricto: 1.2.3, con prefijo "v" opcional.
_RE_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

# Regex para encontrar el asset del instalador (.zip).
# Prioriza nombres que contengan "setup" o "installer".
_RE_ASSET_PRIORIDAD = re.compile(r"(setup|installer)", re.IGNORECASE)


def parsear_version(texto: str) -> tuple[int, int, int] | None:
    """Parsea un string semver a una tupla (major, minor, patch).

    Acepta con o sin prefijo "v". Devuelve None si no es semver valido.

    Ejemplos:
        "1.0.0"   -> (1, 0, 0)
        "v1.0.1"  -> (1, 0, 1)
        "1.2"     -> None
        "1.0.0-rc1" -> None (pre-releases no soportados todavia)
    """
    if texto is None:
        return None
    m = _RE_VERSION.match(texto.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def comparar(actual: str, disponible: str) -> int:
    """Compara dos versiones semver.

    Devuelve:
        -1 si ``actual`` < ``disponible`` (hay update disponible)
         0 si son iguales
         1 si ``actual`` > ``disponible`` (caso raro, reloj desincronizado)

    Si alguna version no se puede parsear, devuelve 0 (no sabemos).
    """
    a = parsear_version(actual)
    b = parsear_version(disponible)
    if a is None or b is None:
        return 0
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def hay_actualizacion(version_actual: str, version_remota: str) -> bool:
    """True si ``version_remota`` es estrictamente mayor que ``version_actual``."""
    return comparar(version_actual, version_remota) < 0


def parsear_release(json_data: dict, nombre_preferido: str | None = None) -> ReleaseInfo | None:
    """Extrae la info relevante del JSON de un release de GitHub.

    ``json_data`` es el dict que devuelve ``GET /repos/{owner}/{repo}/releases/latest``.

    ``nombre_preferido`` permite filtrar el asset por nombre (ej: "ContApp_Setup.exe.zip").
    Si no se pasa, prioriza assets que contengan "setup" o "installer" en el nombre.

    Devuelve None si el JSON no tiene lo minimo necesario (tag, sin assets).
    """
    if not isinstance(json_data, dict):
        return None
    tag = json_data.get("tag_name")
    if not isinstance(tag, str):
        return None
    parsed = parsear_version(tag)
    if parsed is None:
        return None
    version = f"{parsed[0]}.{parsed[1]}.{parsed[2]}"

    assets = json_data.get("assets") or []
    asset = _elegir_asset(assets, nombre_preferido)
    if asset is None:
        # Sin asset descargable -> no podemos actualizar.
        return None

    return ReleaseInfo(
        tag=tag,
        version=version,
        name=str(json_data.get("name") or tag),
        body=str(json_data.get("body") or ""),
        published_at=str(json_data.get("published_at") or ""),
        html_url=str(json_data.get("html_url") or ""),
        asset_name=str(asset.get("name") or ""),
        asset_url=str(asset.get("browser_download_url") or ""),
        asset_size=int(asset.get("size") or 0),
    )


def _elegir_asset(assets: list, nombre_preferido: str | None) -> dict | None:
    """Elige el mejor asset para descargar de una lista de assets."""
    if not assets:
        return None
    # 1) Si nos pasan un nombre preferido, buscar exacto.
    if nombre_preferido:
        for a in assets:
            if isinstance(a, dict) and a.get("name") == nombre_preferido:
                return a
    # 2) Priorizar los que digan setup/installer.
    for a in assets:
        if isinstance(a, dict):
            name = str(a.get("name") or "")
            if _RE_ASSET_PRIORIDAD.search(name):
                return a
    # 3) Primer asset que sea .zip o .exe.
    for a in assets:
        if isinstance(a, dict):
            name = str(a.get("name") or "").lower()
            if name.endswith(".zip") or name.endswith(".exe"):
                return a
    # 4) Cualquier asset.
    for a in assets:
        if isinstance(a, dict):
            return a
    return None
