"""Bitacora (logging) de ContApp.

Configura el logging estandar de Python para que escriba a:
- Archivo (data/bitacora/bitacora.log) con rotacion por fecha.
- Consola (stderr).

Pensada para ser llamada UNA vez al inicio del programa (configurar()).
Despues, cualquier modulo puede hacer:
    from utils.bitacora import log
    log.info("mensaje")
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from datetime import datetime
from pathlib import Path

_FORMAT_CONSOLE = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_FORMAT_ARCHIVO = (
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
_FECHA = "%Y-%m-%d %H:%M:%S"

_logger: logging.Logger | None = None


def configurar(
    ruta_bitacora: Path | str | None = None,
    nivel: int = logging.INFO,
) -> logging.Logger:
    """Inicializa la bitacora. Llamar una sola vez al inicio.

    Args:
        ruta_bitacora: ruta al archivo .log. Si es None, no se escribe a disco.
        nivel: nivel minimo de logging (default INFO).
    """
    global _logger
    logger = logging.getLogger("contapp")
    logger.setLevel(nivel)
    logger.handlers.clear()

    formatter = logging.Formatter(_FORMAT_CONSOLE, datefmt=_FECHA)

    # Consola
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Archivo
    if ruta_bitacora is not None:
        ruta = Path(ruta_bitacora)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(ruta, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(_FORMAT_ARCHIVO, datefmt=_FECHA))
        logger.addHandler(file_handler)

    logger.propagate = False
    _logger = logger
    return logger


def log() -> logging.Logger:
    """Devuelve el logger configurado. Si no se configuro, lo hace con defaults."""
    global _logger
    if _logger is None:
        configurar()
    assert _logger is not None
    return _logger


def timestamp_legible() -> str:
    """Devuelve la fecha/hora actual en formato legible."""
    return datetime.now().strftime(_FECHA)


# --- Lectura / parseo de registros (para la pantalla Configuracion) ----

# Formato del log: "YYYY-MM-DD HH:MM:SS [LEVEL] name: mensaje"
import re  # noqa: E402  (import local para no penalizar el arranque)

_RE_LINEA = re.compile(
    r"^(?P<fecha>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r"\s+\[(?P<nivel>[A-Z]+)\]"
    r"\s+(?P<modulo>\S+):\s*(?P<mensaje>.*)$"
)


def leer_registros(
    ruta_bitacora: Path | str | None = None,
    *,
    limite: int | None = None,
) -> list[dict]:
    """Lee el archivo de bitacora y devuelve una lista de registros parseados.

    Cada registro es un dict con: ``fecha`` (str), ``nivel`` (str),
    ``modulo`` (str), ``mensaje`` (str). Las lineas que no matchean
    el formato se devuelven como ``mensaje_crudo`` y se ignoran
    para los campos estructurados.

    Args:
        ruta_bitacora: ruta al .log. Si es None, usa la ruta configurada
            en el FileHandler del logger (o `data/bitacora/bitacora.log`
            como fallback).
        limite: si se pasa, devuelve solo los ultimos N registros
            (mas performante para bitacoras grandes).
    """
    ruta = _resolver_ruta_bitacora(ruta_bitacora)
    if not ruta.exists():
        return []

    registros: list[dict] = []
    with ruta.open("r", encoding="utf-8", errors="replace") as f:
        for linea in f:
            linea = linea.rstrip("\n")
            if not linea.strip():
                continue
            m = _RE_LINEA.match(linea)
            if m:
                registros.append({
                    "fecha": m.group("fecha"),
                    "nivel": m.group("nivel"),
                    "modulo": m.group("modulo"),
                    "mensaje": m.group("mensaje"),
                    "mensaje_crudo": linea,
                })
            else:
                # Linea que no matchea (p.ej. continuacion de linea anterior).
                # La anexamos al ultimo registro como "continuacion".
                if registros:
                    registros[-1]["mensaje"] += "\n" + linea
                    registros[-1]["mensaje_crudo"] += "\n" + linea

    if limite is not None and limite > 0 and len(registros) > limite:
        registros = registros[-limite:]
    # Invertimos para que el mas reciente aparezca primero.
    registros.reverse()
    return registros


# Regex para detectar si un mensaje fue logueado en modo prueba.
# Los procesos lo agregan al final del mensaje: "... [PRUEBA]".
_RE_PRUEBA = re.compile(r"\s*\[PRUEBA\]\s*$")


def es_modo_prueba(mensaje: str) -> bool | None:
    """Devuelve True/False si el mensaje indica modo_prueba, None si no sabe.

    Los procesos loguean ``... [PRUEBA]`` al final del mensaje cuando se
    ejecutan en modo prueba. Esta funcion lo detecta de forma robusta.
    """
    if _RE_PRUEBA.search(mensaje):
        return True
    return False


def quitar_marca_prueba(mensaje: str) -> str:
    """Quita la marca ``[PRUEBA]`` del final del mensaje (si la tiene)."""
    return _RE_PRUEBA.sub("", mensaje).rstrip()


def obtener_ultimo(proceso: str | None = None, ruta_bitacora: Path | str | None = None) -> dict | None:
    """Devuelve el registro del ultimo proceso ejecutado.

    Busca en la bitacora el ultimo log que indique ejecucion real de un
    proceso, ya sea:
      - ``[Nombre] Excel procesado: <archivo>`` (Fierro, Zeus)
      - ``[Nombre] Generado: <archivo>`` (Comprobante, salida principal)
      - ``[Nombre] FOAPAL generado: <archivo>`` (Comprobante, salida secundaria)

    Args:
        proceso: nombre del proceso (``comprobante``, ``fierro``, ``zeus``)
            para filtrar. Si es None, devuelve el ultimo de cualquier proceso.

    Returns:
        El registro (dict) con un campo extra ``archivos`` (lista de paths
        extraidos del mensaje) y ``proceso`` (nombre normalizado). None si
        no hay registros que matcheen.
    """
    registros = leer_registros(ruta_bitacora)
    if not registros:
        return None

    # Marcadores de "ejecucion real completada" (orden de prioridad).
    marcadores = (
        "Excel procesado",
        "Generado:",
        "FOAPAL generado",
    )

    # leer_registros() ya devuelve del mas reciente al mas viejo.
    for reg in registros:
        msg = reg["mensaje"]
        # Filtro por proceso: el modulo suele ser "contapp" y el
        # mensaje empieza con "[Nombre]".
        if proceso is not None:
            prefijo = f"[{proceso.capitalize()}]"
            if proceso == "comprobante" and not msg.startswith("[Comprobante]"):
                continue
            if proceso == "fierro" and not msg.startswith("[Fierro]"):
                continue
            if proceso == "zeus" and not msg.startswith("[Zeus]"):
                continue
        for marcador in marcadores:
            if marcador in msg:
                # Extraer archivos del mensaje (todo despues de los ":").
                archivos = _extraer_archivos(msg)
                # Determinar nombre del proceso a partir del prefijo "[X]".
                proc = _extraer_proceso(msg)
                return {**reg, "archivos": archivos, "proceso": proc}
    return None


def _extraer_proceso(mensaje: str) -> str:
    """Extrae el nombre del proceso del prefijo ``[Comprobante]`` etc."""
    m = re.match(r"\[(\w+)\]", mensaje)
    return m.group(1).lower() if m else ""


def _extraer_archivos(mensaje: str) -> list[str]:
    """Extrae las rutas de archivo que aparezcan en el mensaje."""
    # Busca patrones tipo C:\... o /home/... que terminen en .xlsx/.zip/.json/.csv
    return re.findall(r"[\w\-\.\\\/: ]+\.(?:xlsx|zip|json|csv)", mensaje)


def _resolver_ruta_bitacora(ruta_bitacora: Path | str | None) -> Path:
    """Resuelve la ruta del archivo de bitacora a leer."""
    if ruta_bitacora is not None:
        return Path(ruta_bitacora)
    # Fallback: ruta por defecto segun config del proyecto.
    try:
        from app.config import BITACORA_LOG
        return BITACORA_LOG
    except Exception:
        # Si el import falla (p.ej. en tests aislados), devolvemos
        # una ruta bajo data/bitacora/.
        return Path("data/bitacora/bitacora.log")