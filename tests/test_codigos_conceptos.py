"""Tests para la detección y gestión de códigos de concepto nuevos.

Cubre ``ProcesoComprobante.verificar_codigos_conceptos`` y
``ProcesoComprobante.obtener_codigos_desconocidos``.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd
import pytest

from procesos.comprobante import (
    COL_CODIGO_CONCEPTO,
    COL_CONCEPTO,
    ProcesoComprobante,
)


def _df_con_codigos(codigos: list[tuple[str, str]]) -> pd.DataFrame:
    """Crea un DataFrame con las columnas mínimas necesarias."""
    data: list[list[str]] = []
    for codigo, descripcion in codigos:
        fila = [""] * 10
        fila[COL_CODIGO_CONCEPTO] = codigo
        fila[COL_CONCEPTO] = descripcion
        data.append(fila)
    return pd.DataFrame(data)


@pytest.fixture
def proceso() -> ProcesoComprobante:
    return ProcesoComprobante()


def test_verificar_sin_codigos_desconocidos(proceso: ProcesoComprobante) -> None:
    """Un DataFrame vacío no devuelve códigos desconocidos."""
    assert proceso.verificar_codigos_conceptos(pd.DataFrame()) == []


def test_detecta_codigo_no_mapeado(proceso: ProcesoComprobante) -> None:
    """Detecta un código que no está en ningún JSON del proceso."""
    df = _df_con_codigos([("9999", "CONCEPTO DESCONOCIDO")])
    desconocidos = proceso.verificar_codigos_conceptos(df)
    assert desconocidos == ["9999"]


def test_no_detecta_codigo_en_codigos_conceptos(proceso: ProcesoComprobante) -> None:
    """No alerta códigos que ya existen en codigos_conceptos.json."""
    codigo_conocido = next(iter(proceso.clasificador_conceptos["Gastos bancarios"]))
    df = _df_con_codigos([(codigo_conocido, "CONOCIDO")])
    assert proceso.verificar_codigos_conceptos(df) == []


def test_no_detecta_codigo_en_foapal(proceso: ProcesoComprobante) -> None:
    """No alerta códigos que ya existen en foapal.json."""
    codigo_foapal = next(iter(proceso.foapal_config["debitos"]))
    # Lo sacamos de codigos_conceptos para asegurar que el crédito es de foapal.
    df = _df_con_codigos([(codigo_foapal, "EN FOAPAL")])
    assert proceso.verificar_codigos_conceptos(df) == []


def test_no_detecta_codigo_ignorado(proceso: ProcesoComprobante) -> None:
    """No alerta códigos que están en codigos_ignorados.json."""
    proceso.codigos_ignorados["codigos"] = ["7777"]
    df = _df_con_codigos([("7777", "IGNORADO")])
    assert proceso.verificar_codigos_conceptos(df) == []


def test_descarta_codigo_vacio(proceso: ProcesoComprobante) -> None:
    """Un código vacío en el CSV no se considera desconocido."""
    df = _df_con_codigos([("", "SIN CODIGO")])
    assert proceso.verificar_codigos_conceptos(df) == []


def test_obtener_codigos_desconocidos_desde_zip(
    proceso: ProcesoComprobante, tmp_path: Path,
) -> None:
    """Lee un ZIP y detecta códigos desconocidos con sus descripciones."""
    # El CSV real tiene 10 campos separados por coma, pero se lee con sep="|"
    # para evitar problemas con comas en la descripción.
    linea = (
        "47789085868,PREF,AHORRO,15072026,ID,1234.56,8888,CONCEPTO NUEVO,0,9999"
    )
    zip_path = tmp_path / "movimientos.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("mov.csv", linea.encode("utf-8"))

    codigos, descripciones = proceso.obtener_codigos_desconocidos([zip_path])

    assert codigos == ["8888"]
    assert descripciones.get("8888") == "CONCEPTO NUEVO"


def test_obtener_codigos_desconocidos_sin_novedades(
    proceso: ProcesoComprobante, tmp_path: Path,
) -> None:
    """Si todos los códigos están mapeados, la lista de desconocidos está vacía."""
    codigo_conocido = next(iter(proceso.foapal_config["debitos"]))
    linea = (
        f"47789085868,PREF,AHORRO,15072026,ID,1234.56,"
        f"{codigo_conocido},CONOCIDO,0,9999"
    )
    zip_path = tmp_path / "movimientos.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("mov.csv", linea.encode("utf-8"))

    codigos, descripciones = proceso.obtener_codigos_desconocidos([zip_path])

    assert codigos == []
    assert descripciones == {}
