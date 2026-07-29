"""Punto de entrada de ContApp.

Por defecto arranca la UI (Fase 3).
Con ``--cli`` arranca en modo terminal (compatible con la version inicial).
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


def arrancar_ui() -> int:
    """Arranca la ventana principal de ContApp."""
    from PySide6.QtWidgets import QApplication

    from app.config import get_config
    from ui.recursos.tema import aplicar_tema
    from ui.ventanas import VentanaPrincipal

    cfg = get_config()
    app = QApplication(sys.argv)
    app.setApplicationName("ContApp")
    # Aplica el tema que el usuario eligio la ultima vez (persiste en
    # ``data/usuario.json``). Default: claro.
    aplicar_tema(app, cfg.tema)
    ventana = VentanaPrincipal()
    ventana.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="contapp",
        description="Sistema de Automatizacion Contable",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Arrancar en modo terminal (sin UI)",
    )
    parser.add_argument(
        "--proceso",
        choices=listar_procesos(),
        help="Proceso a ejecutar (solo CLI)",
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

    # Bitacora: ruta resuelta por config (respeta frozen/onedir).
    from app.config import BITACORA_LOG
    configurar_bitacora(BITACORA_LOG)

    if args.cli:
        # Modo CLI.
        log().info(
            "Para ejecutar uno: python main.py --cli --proceso <nombre> "
            "--archivo <archivo> [--modo-prueba]"
        )

        if args.listar or (not args.proceso and not args.archivo):
            # Modo solo listado: no dejamos ruido en la bitacora.
            for nombre in listar_procesos():
                print(f"  - {nombre}")
            return 0

        if not args.proceso:
            log().error("Falta --proceso")
            return 1
        if not args.archivo:
            log().error("Falta --archivo")
            return 1

        return ejecutar_cli(args.proceso, args.archivo, args.modo_prueba)

    # Modo UI.
    return arrancar_ui()


if __name__ == "__main__":
    sys.exit(main())