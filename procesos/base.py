"""Receta base para todos los procesos de ContApp.

Define el contrato que cada proceso debe cumplir:
- nombre, descripcion
- tipos de archivo de entrada y salida
- metodo ejecutar(archivos, modo_prueba)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, ClassVar


class ProcesoCancelado(Exception):
    """Excepcion que cualquier subclase de ProcesoBase puede ``raise``
    para abortar cooperativamente una ejecucion larga.

    El ``WorkerEjecucion`` la captura y emite ``error("Ejecucion
    cancelada por el usuario")`` + la loggea. Se lanza en cualquier
    loop interno del proceso cuando el callback ``cancelado`` retorna
    True.
    """


@dataclass
class ResultadoProceso:
    """Resultado devuelto por Proceso.ejecutar()."""

    exito: bool
    mensaje: str = ""
    archivos_salida: list[Path] = field(default_factory=list)
    archivos_salida_originales: list[Path] = field(default_factory=list)
    detalles: dict = field(default_factory=dict)


class ProcesoBase(ABC):
    """Molde para todos los procesos de ContApp.

    Cada subclase concreta debe definir:
        - nombre, descripcion
        - extensiones_entrada (tupla de extensiones validas, ej: ('.zip',))
        - extensiones_salida (tupla de extensiones producidas)
        - ejecutar(archivos, modo_prueba) -> ResultadoProceso
        - validar_archivos(archivos) -> str | None (mensaje de error o None si OK)

    Atributos:
        LOG_PREFIX: prefijo para mensajes de bitacora.
    """

    LOG_PREFIX: ClassVar[str] = "[Proceso]"

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre corto del proceso (snake_case)."""

    @property
    @abstractmethod
    def descripcion(self) -> str:
        """Descripcion legible para el usuario."""

    @property
    @abstractmethod
    def extensiones_entrada(self) -> tuple[str, ...]:
        """Extensiones validas de los archivos de entrada (ej: ('.zip',))."""

    @property
    @abstractmethod
    def extensiones_salida(self) -> tuple[str, ...]:
        """Extensiones producidas por el proceso (ej: ('.xlsx',))."""

    @abstractmethod
    def validar_archivos(self, archivos: list[Path]) -> str | None:
        """Valida los archivos de entrada.

        Args:
            archivos: lista de rutas a validar.

        Returns:
            None si todo esta OK, o un mensaje de error en espanol.
        """

    @abstractmethod
    def ejecutar(
        self,
        archivos: list[Path],
        modo_prueba: bool = False,
        *,
        progreso: Callable[[int, int], None] | None = None,
        cancelado: Callable[[], bool] | None = None,
    ) -> ResultadoProceso:
        """Ejecuta el proceso.

        Args:
            archivos: archivos validados que serviran de entrada.
            modo_prueba: si True, escribe a carpetas temporales sin tocar
                los originales.
            progreso: callback opcional ``(actual, total)`` para reportar
                avance al UI. Si se provee, el proceso lo llama cuando
                completa unidades de trabajo (filas procesadas, chunks
                escritos, etc.). Los argumentos son enteros >= 0.
                Si ``progreso`` es ``None`` (caso tests / CLI), se ignora
                y el proceso corre como antes.
            cancelado: callback opcional ``() -> bool`` que el proceso
                chequea periodicamente en loops largos. Si retorna
                ``True``, el proceso debe ``raise ProcesoCancelado()``
                para abortar la ejecucion.

        Returns:
            ResultadoProceso con el resultado de la ejecucion.
        """