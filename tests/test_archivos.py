"""Tests unitarios de `utils/archivos.py`.

Cubre:
- `timestamp_unico()` no produce colisiones.
- `carpeta_resultados()` crea la estructura esperada.
- `carpeta_modo_prueba()` crea la carpeta con prefijo `_prueba_`.
- `copiar_a_carpeta()` y `mover_a_carpeta()` crean nombres sin colision.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Aseguramos sys.path.
import sys
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from utils.archivos import (
    carpeta_modo_prueba,
    carpeta_resultados,
    copiar_a_carpeta,
    listar_archivos,
    mover_a_carpeta,
    timestamp_unico,
)


PATRON_TS = re.compile(r"^\d{8}_\d{6}_\d{6}$")


def test_timestamp_unico_formato() -> None:
    """El timestamp tiene el formato YYYYMMDD_HHMMSS_microsegundos."""
    ts = timestamp_unico()
    assert PATRON_TS.match(ts), f"Formato invalido: {ts}"


def test_timestamp_unico_sin_colisiones_en_rapida_sucesion() -> None:
    """1000 timestamps consecutivos no deben colisionar."""
    timestamps = {timestamp_unico() for _ in range(1000)}
    assert len(timestamps) == 1000


def test_carpeta_resultados_crea_estructura(tmp_path: Path) -> None:
    """carpeta_resultados crea <base>/<proceso>/YYYY-MM/."""
    base = tmp_path / "resultados"
    carpeta = carpeta_resultados(base, "comprobante")
    assert carpeta.exists()
    assert carpeta.is_dir()
    # Formato YYYY-MM (10 chars).
    assert re.match(r"^\d{4}-\d{2}$", carpeta.name), f"Nombre invalido: {carpeta.name}"
    # El proceso debe estar en el path.
    assert "comprobante" in carpeta.parts


def test_carpeta_resultados_idempotente(tmp_path: Path) -> None:
    """Llamar dos veces devuelve la misma carpeta (no falla)."""
    base = tmp_path / "resultados"
    c1 = carpeta_resultados(base, "fierro")
    c2 = carpeta_resultados(base, "fierro")
    assert c1 == c2
    assert c1.exists()


def test_carpeta_modo_prueba_prefijo(tmp_path: Path) -> None:
    """carpeta_modo_prueba usa prefijo _prueba_YYYY-MM."""
    base = tmp_path / "resultados"
    carpeta = carpeta_modo_prueba(base, "zeus")
    assert carpeta.exists()
    assert carpeta.name.startswith("_prueba_")
    assert re.match(r"^_prueba_\d{4}-\d{2}$", carpeta.name)


def test_copiar_a_carpeta_basico(tmp_path: Path) -> None:
    """copiar_a_carpeta copia el archivo manteniendo nombre."""
    origen = tmp_path / "origen"
    origen.mkdir()
    src = origen / "test.xlsx"
    src.write_bytes(b"hola")

    destino = tmp_path / "destino"
    destino.mkdir()
    resultado = copiar_a_carpeta(src, destino)

    assert resultado.exists()
    assert resultado.name == "test.xlsx"
    assert resultado.read_bytes() == b"hola"
    # El original sigue existiendo (es copia, no move).
    assert src.exists()


def test_copiar_a_carpeta_con_sufijo(tmp_path: Path) -> None:
    """copiar_a_carpeta agrega sufijo cuando se especifica."""
    origen = tmp_path / "origen"
    origen.mkdir()
    src = origen / "test.xlsx"
    src.write_bytes(b"x")

    destino = tmp_path / "destino"
    destino.mkdir()
    resultado = copiar_a_carpeta(src, destino, sufijo="_v2")

    assert resultado.name == "test_v2.xlsx"


def test_copiar_a_carpeta_evita_colision(tmp_path: Path) -> None:
    """Si el destino ya existe, agregar contador (_1, _2, ...)."""
    origen = tmp_path / "origen"
    origen.mkdir()
    src = origen / "dato.txt"
    src.write_bytes(b"1")

    destino = tmp_path / "destino"
    destino.mkdir()
    # Pre-llenamos el destino con el mismo nombre.
    (destino / "dato.txt").write_bytes(b"ya existe")

    resultado = copiar_a_carpeta(src, destino)
    assert resultado.name == "dato_1.txt"
    assert resultado.read_bytes() == b"1"


def test_mover_a_carpeta_elimina_origen(tmp_path: Path) -> None:
    """mover_a_carpeta mueve el archivo (origen ya no existe)."""
    origen = tmp_path / "origen"
    origen.mkdir()
    src = origen / "test.xlsx"
    src.write_bytes(b"hola")

    destino = tmp_path / "destino"
    destino.mkdir()
    resultado = mover_a_carpeta(src, destino)

    assert resultado.exists()
    assert resultado.name == "test.xlsx"
    assert not src.exists()  # fue movido


def test_listar_archivos_sin_filtro(tmp_path: Path) -> None:
    """listar_archivos devuelve todos los archivos ordenados."""
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.json").write_text("b")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("c")

    archivos = listar_archivos(tmp_path)
    nombres = [p.name for p in archivos]
    assert nombres == ["a.txt", "b.json"]  # ordenado, sin subcarpetas


def test_listar_archivos_con_filtro(tmp_path: Path) -> None:
    """listar_archivos filtra por extension."""
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.json").write_text("b")
    (tmp_path / "c.JSON").write_text("c")

    archivos = listar_archivos(tmp_path, extensiones=(".json",))
    nombres = sorted(p.name for p in archivos)
    assert nombres == ["b.json", "c.JSON"]


def test_listar_archivos_carpeta_inexistente(tmp_path: Path) -> None:
    """listar_archivos devuelve lista vacia si la carpeta no existe."""
    assert listar_archivos(tmp_path / "no_existe") == []