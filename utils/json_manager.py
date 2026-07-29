"""Gestion de archivos JSON de ContApp.

Responsabilidades:
- Leer y escribir JSONs.
- Hacer backup automatico antes de cada escritura (con timestamp).
- Detectar la estructura (Tipo A/B/C/D) para que el editor muestre la vista adecuada.
- Locks por archivo para evitar race conditions entre el editor y los
  procesos en runtime.
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



# ====================================================================
# Locks por archivo (proteccion contra race conditions)
# ====================================================================
# Cuando el usuario edita un JSON mientras un proceso esta corriendo,
# podemos evitar pisar el archivo. Los procesos mismos cargan los JSONs
# en memoria en su __init__, asi que NO usan locks.
#
# Mecanismo: archivo .lock al lado del JSON. Si el archivo .lock existe
# y es nuestro -> podemos escribir. Si no existe -> alguien mas tiene
# el lock y debemos esperar o rechazar.
# ====================================================================

# Prefijo para los archivos de lock.
LOCK_SUFIJO = ".lock"


def ruta_lock(ruta_json: Path | str) -> Path:
    """Devuelve la ruta del archivo .lock asociado al JSON."""
    ruta = Path(ruta_json)
    return ruta.with_name(ruta.name + LOCK_SUFIJO)


def lock_adquirido(ruta_json: Path | str) -> bool:
    """True si el archivo .lock existe Y somos duenos."""
    ruta_lock_ = ruta_lock(ruta_json)
    if not ruta_lock_.exists():
        return False
    # Si somos duenos, podemos sobrescribir nuestro propio lock.
    # Para mantenerlo simple, devolvemos True solo si somos duenos.
    try:
        contenido = ruta_lock_.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    import getpass
    import os
    usuario = os.environ.get("USERNAME") or getpass.getuser()
    return contenido == usuario


def adquirir_lock(ruta_json: Path | str) -> Path | None:
    """Intenta adquirir el lock sobre el JSON.

    Devuelve la ruta del .lock si lo adquirimos. None si ya estaba
    tomado por otro usuario/proceso.

    El lock se crea con el nombre del usuario actual adentro, asi
    procesos paralelos del mismo usuario pueden compartirlo.
    """
    ruta_lock_ = ruta_lock(ruta_json)
    import getpass
    import os
    usuario = os.environ.get("USERNAME") or getpass.getuser()
    try:
        # Crear exclusivamente (falla si ya existe).
        with ruta_lock_.open("x", encoding="utf-8") as f:
            f.write(usuario)
        return ruta_lock_
    except FileExistsError:
        # Ya existe. Ver si es nuestro.
        if lock_adquirido(ruta_json):
            return ruta_lock_
        return None
    except OSError:
        return None


def liberar_lock(ruta_o_lock: Path | str) -> bool:
    """Libera el lock. Devuelve True si se libero, False si no estaba nuestro."""
    ruta_lock_ = Path(ruta_o_lock)
    if not ruta_lock_.name.endswith(LOCK_SUFIJO):
        # Si nos pasaron la ruta del JSON, derivar la del lock.
        ruta_lock_ = ruta_lock(ruta_o_lock)
    try:
        # lock_adquirido espera la ruta del JSON, no la del .lock.
        ruta_json = ruta_lock_.with_name(ruta_lock_.name[: -len(LOCK_SUFIJO)])
        if lock_adquirido(ruta_json):
            ruta_lock_.unlink()
            return True
    except OSError:
        pass
    return False


def con_lock(ruta_json: Path | str):
    """Context manager que adquiere lock, ejecuta el bloque, libera.

    Ejemplo:
        with con_lock("data/jsons/fierro/mapeo.json") as lock_path:
            if lock_path is None:
                raise RuntimeError("No se pudo obtener el lock")
            escribir_json(ruta_json, datos)

    Si no se pudo adquirir el lock, ``lock_path`` es None y NO se
    ejecuta el bloque.
    """
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        lock = adquirir_lock(ruta_json)
        try:
            yield lock
        finally:
            if lock is not None:
                liberar_lock(lock)

    return _ctx()
