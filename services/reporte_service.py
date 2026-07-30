"""Servicio de generacion de reportes de ejecucion.

Hoy el reporte es trivial: una linea en la bitacora + el resultado
devuelto por el proceso. En el futuro este servicio podria:
- Generar un PDF con el resumen.
- Calcular estadisticas (filas procesadas, tiempo total, etc).
- Subir el reporte a un servidor.

API:
    svc = ReporteService(bitacora=log, carpeta_reportes=Path("data/reportes"))
    reporte = svc.generar(resultado, proceso="fierro")

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from procesos.base import ResultadoProceso


class ReporteService:
    """Servicio que genera el reporte de una ejecucion."""

    def __init__(
        self,
        bitacora: logging.Logger,
        carpeta_reportes: Path | str | None = None,
    ) -> None:
        """
        Args:
            bitacora: logger para registrar el reporte.
            carpeta_reportes: donde guardar archivos de reporte (opcional).
        """
        self._log = bitacora
        self._carpeta = Path(carpeta_reportes) if carpeta_reportes else None

    @property
    def carpeta_reportes(self) -> Path | None:
        return self._carpeta

    def generar(
        self,
        resultado: "ResultadoProceso",
        *,
        proceso: str,
        usuario: str = "",
    ) -> dict:
        """Genera un reporte resumido a partir de un ``ResultadoProceso``.

        Returns:
            Diccionario con: ``proceso``, ``usuario``, ``exito``,
            ``mensaje``, ``archivos_salida`` (lista de strings),
            ``timestamp``.
        """
        from datetime import datetime

        reporte = {
            "proceso": proceso,
            "usuario": usuario,
            "exito": resultado.exito,
            "mensaje": resultado.mensaje,
            "archivos_salida": [str(p) for p in resultado.archivos_salida],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        # Loggearlo (esto se ve en PantallaConfiguracion).
        prefix = "[OK]" if resultado.exito else "[FAIL]"
        archivos = len(resultado.archivos_salida)
        self._log.info(
            "%s %s -> %d archivo(s) generado(s) (usuario=%s)",
            prefix,
            proceso,
            archivos,
            usuario or "anonimo",
        )
        for p in resultado.archivos_salida:
            self._log.info("  - %s", p)
        return reporte
