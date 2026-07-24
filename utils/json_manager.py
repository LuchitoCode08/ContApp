"""Gestion de archivos JSON de ContApp.

Responsabilidades:
- Leer y escribir JSONs.
- Hacer backup automatico antes de cada escritura (con timestamp).
- Detectar la estructura (Tipo A/B/C/D) para que el editor muestre la vista adecuada.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from utils.archivos import timestamp_unico


# Tipos de estructura detectados
TIPO_A = "A"  # plano: { "clave": "valor" }
TIPO_B = "B"  # secciones con sub-objetos
TIPO_C = "C"  # secciones con valores string o list[string]
TIPO_D = "D"  # lista de pares patron -> valor


def leer_json(ruta: Path | str) -> dict:
    """Lee un JSON. Lanza excepcion si no existe o esta malformado."""
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8") as f:
        return json.load(f)


def escribir_json(
    ruta: Path | str,
    datos: dict,
    *,
    hacer_backup: bool = True,
    carpeta_backups: Path | str | None = None,
) -> Path | None:
    """Escribe un JSON creando backup automatico previo.

    Args:
        ruta: ruta del JSON destino.
        datos: diccionario a serializar.
        hacer_backup: si True (default), copia el archivo actual a
            <carpeta_backups>/<nombre>_<timestamp>.json antes de escribir.
        carpeta_backups: donde guardar el backup. Si es None y hacer_backup=True,
            se usa <directorio_del_json>/.backups/.

    Returns:
        Ruta del backup si se hizo, None si no.
    """
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    backup_path: Path | None = None
    if hacer_backup and ruta.exists():
        if carpeta_backups is None:
            carpeta_backups = ruta.parent / ".backups"
        carpeta_backups = Path(carpeta_backups)
        carpeta_backups.mkdir(parents=True, exist_ok=True)
        backup_path = carpeta_backups / f"{ruta.stem}_{timestamp_unico()}.json"
        shutil.copy2(ruta, backup_path)

    with ruta.open("w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    return backup_path


def detectar_tipo(datos: dict) -> str:
    """Detecta la estructura de un JSON cargado.

    Returns:
        TIPO_A, TIPO_B, TIPO_C o TIPO_D.
    """
    if not datos:
        return TIPO_A

    valores = list(datos.values())

    # Tipo D: una sola clave cuyo valor es lista de listas de 2 elementos.
    if (
        len(datos) == 1
        and isinstance(valores[0], list)
        and all(
            isinstance(item, list) and len(item) == 2
            for item in valores[0]
        )
    ):
        return TIPO_D

    # Tipos B/C: los valores son dicts.
    if all(isinstance(v, dict) for v in valores):
        # Tipo C: valores son dicts de strings o listas de strings.
        if all(
            isinstance(sv, (str, list))
            for v in valores
            for sv in v.values()
        ):
            return TIPO_C
        # Tipo B: sub-objetos con multiples claves.
        if all(
            isinstance(v, dict) and len(v) > 1
            for v in valores
        ):
            return TIPO_B
        # Si no encaja, tratamos como C.
        return TIPO_C

    # Tipo A: valores son escalares.
    if all(isinstance(v, (str, int, float)) for v in valores):
        return TIPO_A

    # Default conservador.
    return TIPO_A