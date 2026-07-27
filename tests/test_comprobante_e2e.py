"""Test end-to-end del proceso Comprobante.

Genera un ZIP sintetico con CSVs en el formato esperado por Bancolombia,
ejecuta ProcesoComprobante y verifica los Excels de salida.
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.config import RAIZ as APP_RAIZ
from procesos.comprobante import ProcesoComprobante


# Linea CSV sintetica con el formato real de Bancolombia:
# 47789085868,DESCRIPCION,1234.56,15072026,FOPNAL,13201,530515,9999,ABONO,0
# (NOTA: el CSV se lee con sep="|" primero, por lo que el archivo es
# UNA sola columna con valores separados por coma. Ver
# ``_read_csv_bytes`` en comprobante.py.)
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
    """Crea un ZIP sintetico en tmp_path y devuelve la ruta."""
    zip_path = tmp_path / "sintetico.zip"
    _crear_zip_sintetico(zip_path)
    return zip_path


@pytest.fixture
def proceso() -> ProcesoComprobante:
    return ProcesoComprobante()


def test_validar_archivos_zip_valido(
    proceso: ProcesoComprobante, zip_sintetico: Path,
) -> None:
    """Un ZIP valido pasa la validacion."""
    assert proceso.validar_archivos([zip_sintetico]) is None


def test_validar_archivos_no_zip(tmp_path: Path, proceso: ProcesoComprobante) -> None:
    """Un archivo que no es ZIP es rechazado con mensaje en espanol."""
    txt = tmp_path / "fake.zip"
    txt.write_text("no soy zip")
    error = proceso.validar_archivos([txt])
    assert error is not None
    assert "ZIP" in error


def test_validar_archivos_vacio(proceso: ProcesoComprobante) -> None:
    """Lista vacia devuelve error."""
    error = proceso.validar_archivos([])
    assert error is not None
    assert "ZIP" in error or "archivo" in error.lower()


def test_ejecutar_en_modo_prueba_genera_archivos(
    proceso: ProcesoComprobante,
    zip_sintetico: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """En modo prueba, ejecutar() genera 1 o 2 archivos Excel en /resultados/_prueba_*/."""
    # Redirigimos RAIZ para que los resultados vayan a tmp_path en vez del repo.
    monkeypatch.setattr("procesos.comprobante.RAIZ", tmp_path)

    resultado = proceso.ejecutar([zip_sintetico], modo_prueba=True)

    assert resultado.exito, f"Fallo: {resultado.mensaje}"
    # Debe haber generado al menos 1 archivo (el Excel principal).
    assert len(resultado.archivos_salida) >= 1
    # Y cada archivo debe existir.
    for p in resultado.archivos_salida:
        assert p.exists()
        assert p.stat().st_size > 0
    # La carpeta debe tener el prefijo _prueba_.
    carpeta = resultado.archivos_salida[0].parent
    assert "_prueba_" in carpeta.name

    # Limpieza: borrar el backup generado en JSON.
    for jf in (APP_RAIZ / "jsons").rglob(".backups/*"):
        if jf.is_file():
            jf.unlink()


def test_ejecutar_en_modo_produccion_genera_archivos(
    proceso: ProcesoComprobante,
    zip_sintetico: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """En modo produccion, ejecutar() genera archivos en /resultados/<proceso>/YYYY-MM/."""
    monkeypatch.setattr("procesos.comprobante.RAIZ", tmp_path)

    resultado = proceso.ejecutar([zip_sintetico], modo_prueba=False)

    assert resultado.exito, f"Fallo: {resultado.mensaje}"
    assert len(resultado.archivos_salida) >= 1
    carpeta = resultado.archivos_salida[0].parent
    # Sin prefijo _prueba_.
    assert "_prueba_" not in carpeta.name


def test_ejecutar_genera_foapal(
    proceso: ProcesoComprobante,
    zip_sintetico: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El proceso Comprobante genera el archivo fzrcoco.xlsx (FOAPAL)."""
    monkeypatch.setattr("procesos.comprobante.RAIZ", tmp_path)

    resultado = proceso.ejecutar([zip_sintetico], modo_prueba=True)

    assert resultado.exito
    nombres = [p.name for p in resultado.archivos_salida]
    assert "fzrcoco.xlsx" in nombres, f"Nombres: {nombres}"


def test_extensiones_salida_son_xlsx(proceso: ProcesoComprobante) -> None:
    """El proceso declara que produce .xlsx."""
    assert proceso.extensiones_salida == (".xlsx",)
    assert ".zip" in proceso.extensiones_entrada


def test_ejecutar_zip_sin_csvs(
    proceso: ProcesoComprobante, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un ZIP sin CSVs no falla: procesa 0 filas y genera Excels vacios."""
    monkeypatch.setattr("procesos.comprobante.RAIZ", tmp_path)
    zip_vacio = tmp_path / "vacio.zip"
    with zipfile.ZipFile(zip_vacio, "w") as zf:
        zf.writestr("README.txt", "no hay csvs")

    resultado = proceso.ejecutar([zip_vacio], modo_prueba=True)

    assert resultado.exito  # exito con DataFrame vacio


def test_ejecutar_zip_solo_campos_basicos(
    proceso: ProcesoComprobante, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un CSV con solo los campos basicos que el script
    necesita para construir las hojas (cuenta, concepto, valor).
    Esta es la situacion minima viable para verificar que el
    proceso termina con exito y genera archivos."""
    monkeypatch.setattr("procesos.comprobante.RAIZ", tmp_path)
    # CSV valido con 9 campos (cuenta, desc, valor, fecha, fondo,
    # organizacion, codigo_contable, identificador, concepto, valor_num)
    linea = (
        "47789085868,DESCRIPCION BASICA,1234.56,15072026,FOPNAL,13201,"
        "530515,9999,ABONO,0"
    )
    zip_min = tmp_path / "minimo.zip"
    with zipfile.ZipFile(zip_min, "w") as zf:
        zf.writestr("datos.csv", linea.encode("utf-8"))

    resultado = proceso.ejecutar([zip_min], modo_prueba=True)

    assert resultado.exito
    assert len(resultado.archivos_salida) >= 1




def test_log_prefix_es_el_del_proceso(proceso: ProcesoComprobante) -> None:
    """El prefijo de log sigue el patron [Nombre]."""
    assert proceso.LOG_PREFIX == "[Comprobante]"