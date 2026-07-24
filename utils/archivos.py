"""Utilidades para manejo de archivos y carpetas.

Funciones pensadas para:
- Generar timestamps sin colision (microsegundos).
- Crear/leer carpetas mensuales (resultados/<proceso>/YYYY-MM/).
- Mover/copiar archivos preservando el nombre.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def timestamp_unico() -> str:
    """Devuelve un timestamp con microsegundos para nombres de archivo.

    Ej: '20260724_153012_847293'
    Importante: usar microsegundos evita colisiones cuando se generan
    varios archivos en el mismo segundo.
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def carpeta_resultados(
    ruta_base: Path | str,
    proceso: str,
    fecha: datetime | None = None,
) -> Path:
    """Crea (si hace falta) y devuelve la carpeta de resultados del mes.

    Estructura: <ruta_base>/<proceso>/YYYY-MM/
    """
    fecha = fecha or datetime.now()
    sub = fecha.strftime("%Y-%m")
    carpeta = Path(ruta_base) / proceso / sub
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def carpeta_modo_prueba(
    ruta_base: Path | str,
    proceso: str,
) -> Path:
    """Crea y devuelve una carpeta temporal para modo prueba.

    Estructura: <ruta_base>/<proceso>/_prueba_YYYY-MM/
    """
    fecha = datetime.now()
    sub = f"_prueba_{fecha.strftime('%Y-%m')}"
    carpeta = Path(ruta_base) / proceso / sub
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def copiar_a_carpeta(
    archivo: Path,
    carpeta_destino: Path,
    sufijo: str = "",
) -> Path:
    """Copia un archivo a la carpeta destino (crea el nombre con sufijo opcional).

    Si el archivo ya existe en destino, agrega un contador (_1, _2, ...).
    Devuelve la ruta final del archivo copiado.
    """
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    nombre = archivo.stem + sufijo + archivo.suffix
    destino = carpeta_destino / nombre
    contador = 1
    while destino.exists():
        nombre = f"{archivo.stem}{sufijo}_{contador}{archivo.suffix}"
        destino = carpeta_destino / nombre
        contador += 1
    shutil.copy2(archivo, destino)
    return destino


def mover_a_carpeta(
    archivo: Path,
    carpeta_destino: Path,
    sufijo: str = "",
) -> Path:
    """Mueve un archivo a la carpeta destino (crea el nombre con sufijo opcional).

    A diferencia de copiar_a_carpeta, aqui se elimina el origen.
    """
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    nombre = archivo.stem + sufijo + archivo.suffix
    destino = carpeta_destino / nombre
    contador = 1
    while destino.exists():
        nombre = f"{archivo.stem}{sufijo}_{contador}{archivo.suffix}"
        destino = carpeta_destino / nombre
        contador += 1
    shutil.move(str(archivo), str(destino))
    return destino


def listar_archivos(
    carpeta: Path | str,
    extensiones: tuple[str, ...] | None = None,
) -> list[Path]:
    """Lista archivos en una carpeta, opcionalmente filtrando por extension."""
    carpeta = Path(carpeta)
    if not carpeta.exists():
        return []
    archivos = [p for p in carpeta.iterdir() if p.is_file()]
    if extensiones:
        extensiones_lower = tuple(e.lower() for e in extensiones)
        archivos = [
            p for p in archivos if p.suffix.lower() in extensiones_lower
        ]
    return sorted(archivos)