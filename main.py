"""Punto de entrada de ContApp.

Por ahora arranca en modo CLI: lista los procesos disponibles y permite
ejecutarlos desde la terminal. Cuando este lista la UI (Fase 3), este
archivo arrancara la ventana principal.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from utils.bitacora import configurar as configurar_bitacora
from utils.bitacora import log

# Directorio del programa (donde esta main.py)
RAIZ = Path(__file__).resolve().parent


def listar_procesos() -> list[str]:
    """Devuelve los nombres de los procesos disponibles."""
    return ["comprobante", "fierro", "zeus"]


def ejecutar_cli(proceso: str, archivos: list[Path], modo_prueba: bool) -> int:
    """Ejecuta un proceso desde la terminal."""
    try:
        modulo = __import__(f"procesos.{proceso}", fromlist=[proceso])
        cls = getattr(modulo, "Proceso" + proceso.capitalize(), None)
        if cls is None:
            log().error("No se encontro la clase del proceso '%s'", proceso)
            return 1
        instancia = cls()
        error = instancia.validar_archivos(archivos)
        if error:
            log().error("Archivos invalidos: %s", error)
            return 2
        resultado = instancia.ejecutar(archivos, modo_prueba=modo_prueba)
        if resultado.exito:
            log().info(
                "[OK] %s -> %d archivo(s) generado(s)",
                proceso,
                len(resultado.archivos_salida),
            )
            for p in resultado.archivos_salida:
                log().info("  - %s", p)
            return 0
        log().error("[FAIL] %s: %s", proceso, resultado.mensaje)
        return 3
    except Exception as e:
        log().exception("Error inesperado: %s", e)
        return 99


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="contapp",
        description="Sistema de Automatizacion Contable",
    )
    parser.add_argument(
        "--proceso",
        choices=listar_procesos(),
        help="Proceso a ejecutar (modo CLI)",
    )
    parser.add_argument(
        "--archivo",
        action="append",
        type=Path,
        help="Archivo de entrada (se puede repetir)",
    )
    parser.add_argument(
        "--modo-prueba",
        action="store_true",
        help="Ejecutar en modo prueba (no toca los originales)",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista los procesos disponibles",
    )
    args = parser.parse_args()

    # Bitacora: archivo en data/bitacora/bitacora.log
    log_path = RAIZ / "data" / "bitacora" / "bitacora.log"
    configurar_bitacora(log_path)

    log().info("=" * 60)
    log().info("ContApp iniciando (modo_prueba=%s)", args.modo_prueba)

    if args.listar or (not args.proceso and not args.archivo):
        log().info("Procesos disponibles:")
        for nombre in listar_procesos():
            log().info("  - %s", nombre)
        log().info("Para ejecutar uno: python main.py --proceso <nombre> "
                   "--archivo <archivo> [--modo-prueba]")
        return 0

    if not args.proceso:
        log().error("Falta --proceso")
        return 1
    if not args.archivo:
        log().error("Falta --archivo")
        return 1

    return ejecutar_cli(args.proceso, args.archivo, args.modo_prueba)


if __name__ == "__main__":
    sys.exit(main())