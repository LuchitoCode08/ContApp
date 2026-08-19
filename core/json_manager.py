"""Lectura y escritura simple de archivos JSON."""
from __future__ import annotations

import json
from pathlib import Path


def leer_json(ruta: Path | str) -> dict:
    """Lee un JSON y devuelve su contenido como dict."""
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8") as f:
        return json.load(f)


def escribir_json(ruta: Path | str, datos: dict) -> None:
    """Escribe datos a un JSON con indentación y UTF-8."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def listar_jsons(carpeta_jsons: Path | str) -> dict[str, list[Path]]:
    """Lista todos los archivos JSON organizados por subcarpeta/proceso."""
    carpeta_jsons = Path(carpeta_jsons)
    if not carpeta_jsons.exists():
        return {}
    resultado: dict[str, list[Path]] = {}
    for sub in sorted(carpeta_jsons.iterdir()):
        if sub.is_dir():
            jsons = sorted(sub.glob("*.json"))
            if jsons:
                resultado[sub.name] = jsons
    return resultado
