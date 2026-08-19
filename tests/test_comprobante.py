"""Test end-to-end del proceso Comprobante."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.comprobante import ProcesoComprobante

LINEA_VALIDA = (
    "47789085868,DESCRIPCION PRUEBA,1234.56,15072026,FOPNAL,13201,"
    "530515,9999,ABONO,0"
)
LINEA_FIDUCIARIA = (
    "4023464839,DESC FIDUCIARIA,500.00,15072026,FOPNAL,13201,"
    "530515,9999,ABONO,0"
)


def _crear_zip_sintetico(ruta_zip: Path) -> None:
    """Crea un ZIP con dos CSVs."""
    contenido_csv1 = LINEA_VALIDA + "\n" + LINEA_FIDUCIARIA + "\n"
    contenido_csv2 = LINEA_VALIDA + "\n"

    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("movimientos1.csv", contenido_csv1.encode("utf-8"))
        zf.writestr("movimientos2.csv", contenido_csv2.encode("utf-8"))


@pytest.fixture
def zip_sintetico(tmp_path: Path) -> Path:
    zip_path = tmp_path / "sintetico.zip"
    _crear_zip_sintetico(zip_path)
    return zip_path


@pytest.fixture
def proceso() -> ProcesoComprobante:
    return ProcesoComprobante()


def test_validar_archivos_zip_valido(
    proceso: ProcesoComprobante, zip_sintetico: Path,
) -> None:
    assert proceso.validar_archivos([zip_sintetico]) is None


def test_validar_archivos_no_zip(tmp_path: Path, proceso: ProcesoComprobante) -> None:
    txt = tmp_path / "fake.zip"
    txt.write_text("no soy zip")
    error = proceso.validar_archivos([txt])
    assert error is not None
    assert "ZIP" in error


def test_validar_archivos_vacio(proceso: ProcesoComprobante) -> None:
    error = proceso.validar_archivos([])
    assert error is not None
    assert "ZIP" in error or "archivo" in error.lower()


def test_ejecutar_en_modo_prueba_genera_archivos(
    proceso: ProcesoComprobante,
    zip_sintetico: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.comprobante.RESULTADOS_DIR", tmp_path)

    resultado = proceso.ejecutar([zip_sintetico], modo_prueba=True)

    assert resultado.exito, f"Fallo: {resultado.mensaje}"
    assert len(resultado.archivos_salida) >= 1
    for p in resultado.archivos_salida:
        assert p.exists()
        assert p.stat().st_size > 0
    carpeta = resultado.archivos_salida[0].parent
    assert "_prueba_" in carpeta.name


def test_ejecutar_en_modo_produccion_genera_archivos(
    proceso: ProcesoComprobante,
    zip_sintetico: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.comprobante.RESULTADOS_DIR", tmp_path)

    resultado = proceso.ejecutar([zip_sintetico], modo_prueba=False)

    assert resultado.exito, f"Fallo: {resultado.mensaje}"
    assert len(resultado.archivos_salida) >= 1
    carpeta = resultado.archivos_salida[0].parent
    assert "_prueba_" not in carpeta.name


def test_ejecutar_genera_foapal(
    proceso: ProcesoComprobante,
    zip_sintetico: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.comprobante.RESULTADOS_DIR", tmp_path)

    resultado = proceso.ejecutar([zip_sintetico], modo_prueba=True)

    assert resultado.exito
    nombres = [p.name for p in resultado.archivos_salida]
    assert "fzrcoco.xlsx" in nombres, f"Nombres: {nombres}"


def test_extensiones_salida_son_xlsx(proceso: ProcesoComprobante) -> None:
    assert proceso.extensiones_salida == (".xlsx",)
    assert ".zip" in proceso.extensiones_entrada


def test_ejecutar_zip_sin_csvs(
    proceso: ProcesoComprobante, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.comprobante.RESULTADOS_DIR", tmp_path)
    zip_vacio = tmp_path / "vacio.zip"
    with zipfile.ZipFile(zip_vacio, "w") as zf:
        zf.writestr("README.txt", "no hay csvs")

    resultado = proceso.ejecutar([zip_vacio], modo_prueba=True)
    assert resultado.exito


def test_ejecutar_procesa_todos_los_zips(
    proceso: ProcesoComprobante,
    zip_sintetico: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.comprobante.RESULTADOS_DIR", tmp_path)
    segundo_zip = tmp_path / "segundo.zip"
    _crear_zip_sintetico(segundo_zip)

    resultado = proceso.ejecutar([zip_sintetico, segundo_zip], modo_prueba=True)

    assert resultado.exito, f"Fallo: {resultado.mensaje}"
    assert resultado.detalles["filas_origen"] == 6
