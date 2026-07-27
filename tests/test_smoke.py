"""Smoke tests: imports + instanciacion basica de los modulos principales.

Estos tests verifican que el codigo compila e instancia sin errores.
Son la primera red de seguridad: si fallan, el resto de los tests
no tiene sentido correrlos.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Aseguramos que el directorio raiz este en sys.path para los imports.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def test_imports_principales() -> None:
    """Todos los modulos del nucleo importan sin error."""
    # Nucleo.
    import procesos.base  # noqa: F401
    import procesos.comprobante  # noqa: F401
    import procesos.fierro  # noqa: F401
    import procesos.zeus  # noqa: F401

    # Utils.
    import utils.archivos  # noqa: F401
    import utils.bitacora  # noqa: F401
    import utils.json_manager  # noqa: F401

    # App / config.
    import app.config  # noqa: F401


def test_app_config_singleton() -> None:
    """get_config() devuelve siempre la misma instancia."""
    from app.config import get_config

    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2
    assert cfg1.modo_prueba is False  # default seguro


def test_app_config_procesos_registrados() -> None:
    """Los 3 procesos estan registrados."""
    from app.config import get_config

    cfg = get_config()
    assert set(cfg.nombres_procesos()) == {"comprobante", "fierro", "zeus"}


def test_instanciar_procesos() -> None:
    """Las 3 clases de proceso instancian y exponen las propiedades abstractas."""
    from procesos.comprobante import ProcesoComprobante
    from procesos.fierro import ProcesoFierro
    from procesos.zeus import ProcesoZeus

    for cls in (ProcesoComprobante, ProcesoFierro, ProcesoZeus):
        inst = cls()
        # Propiedades requeridas por ProcesoBase.
        assert isinstance(inst.nombre, str) and len(inst.nombre) > 0
        assert isinstance(inst.descripcion, str) and len(inst.descripcion) > 0
        assert isinstance(inst.extensiones_entrada, tuple)
        assert isinstance(inst.extensiones_salida, tuple)
        assert len(inst.extensiones_entrada) > 0
        assert len(inst.extensiones_salida) > 0
        # Metodos abstractos implementados.
        assert hasattr(inst, "validar_archivos")
        assert hasattr(inst, "ejecutar")


def test_resultado_proceso_dataclass() -> None:
    """ResultadoProceso se puede instanciar vacio y con datos."""
    from procesos.base import ResultadoProceso

    vacio = ResultadoProceso(exito=True)
    assert vacio.exito is True
    assert vacio.mensaje == ""
    assert vacio.archivos_salida == []
    assert vacio.archivos_salida_originales == []
    assert vacio.detalles == {}

    lleno = ResultadoProceso(
        exito=False,
        mensaje="algo fallo",
        archivos_salida=[Path("/tmp/a.xlsx")],
        detalles={"filas": 42},
    )
    assert lleno.exito is False
    assert lleno.mensaje == "algo fallo"
    assert len(lleno.archivos_salida) == 1
    assert lleno.detalles["filas"] == 42


def test_compilacion_archivos_ui() -> None:
    """Los archivos de UI compilan sin errores de sintaxis."""
    import py_compile

    for rel in (
        "ui/ventanas/principal.py",
        "ui/ventanas/ejecutar_proceso.py",
        "ui/ventanas/editor_json.py",
        "ui/ventanas/configuracion.py",
        "main.py",
        "procesos/base.py",
        "procesos/comprobante.py",
        "procesos/fierro.py",
        "procesos/zeus.py",
        "utils/archivos.py",
        "utils/bitacora.py",
        "utils/json_manager.py",
    ):
        py_compile.compile(rel, doraise=True)