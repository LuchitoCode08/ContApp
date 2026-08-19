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
    """Excepción que cualquier subclase de ProcesoBase puede lanzar
    para abortar cooperativamente una ejecución en curso.
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
    """Molde para todos los procesos de ContApp."""

    LOG_PREFIX: ClassVar[str] = "[Proceso]"

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre corto del proceso (snake_case)."""

    @property
    @abstractmethod
    def descripcion(self) -> str:
        """Descripción legible para el usuario."""

    @property
    @abstractmethod
    def extensiones_entrada(self) -> tuple[str, ...]:
        """Extensiones válidas de los archivos de entrada (ej: ('.zip',))."""

    @property
    @abstractmethod
    def extensiones_salida(self) -> tuple[str, ...]:
        """Extensiones producidas por el proceso (ej: ('.xlsx',))."""

    @abstractmethod
    def validar_archivos(self, archivos: list[Path]) -> str | None:
        """Valida los archivos de entrada.

        Returns:
            None si todo está OK, o un mensaje de error en español.
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
        """Ejecuta el proceso."""
