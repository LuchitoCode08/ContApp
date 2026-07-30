"""Definicion de los eventos que viajan por el EventBus.

Estos dataclasses ``frozen=True`` son los mensajes que emiten los
procesos / servicios y consumen la UI / bitacora / plugins futuros.

Por que ``frozen=True``: los eventos pueden cruzar threads (QThread del
worker al main thread de la UI). Usar dataclasses inmutables evita
condiciones de carrera silenciosas.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from events.bus import EventoBase


@dataclass(frozen=True)
class ProcesoIniciado(EventoBase):
    """Una ejecucion de proceso empezo."""
    proceso: str           # "comprobante", "fierro", "zeus"
    archivos: tuple[Path, ...]
    modo_prueba: bool


@dataclass(frozen=True)
class ProgresoProceso(EventoBase):
    """Actualizacion de progreso durante una ejecucion.

    Refleja el ``callback progreso(actual, total)`` que los procesos
    invocan. La UI ya recibe esto via el Signal Qt ``progreso`` del
    WorkerEjecucion; este evento es para consumidores no-UI (bitacora,
    plugins futuros).
    """
    proceso: str
    actual: int
    total: int


@dataclass(frozen=True)
class ProcesoFinalizado(EventoBase):
    """Una ejecucion de proceso termino (con exito o con error)."""
    proceso: str
    exito: bool
    mensaje: str
    archivos_salida: tuple[Path, ...]


@dataclass(frozen=True)
class ProcesoCancelado(EventoBase):
    """El usuario pidio cancelar y la ejecucion aborto cooperativamente."""
    proceso: str


@dataclass(frozen=True)
class JsonEditado(EventoBase):
    """El usuario edito un JSON desde el editor de Diccionarios."""
    ruta: Path
    cantidad_cambios: int


@dataclass(frozen=True)
class TemaCambiado(EventoBase):
    """El usuario cambio el tema visual (claro/oscuro)."""
    nuevo_tema: str  # "claro" o "oscuro"
