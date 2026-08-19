"""Tests unitarios de `core/json_manager.py`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.json_manager import escribir_json, leer_json, listar_jsons


def test_leer_escribir_roundtrip(tmp_path: Path) -> None:
    """Lo que escribimos se puede leer de vuelta idéntico."""
    ruta = tmp_path / "test.json"
    datos = {"clave1": "valor1", "lista": [1, 2, 3], "anidado": {"k": "v"}}

    escribir_json(ruta, datos)
    leido = leer_json(ruta)

    assert leido == datos


def test_escribir_json_preserva_unicode(tmp_path: Path) -> None:
    """Los caracteres acentuados y especiales se preservan (ensure_ascii=False)."""
    ruta = tmp_path / "test.json"
    datos = {"texto": "Códigos Contables - NIT Bancolombia", "símbolo": "→"}

    escribir_json(ruta, datos)
    contenido = ruta.read_text(encoding="utf-8")

    assert "Códigos" in contenido
    assert "→" in contenido
    assert "C\\u00f3digos" not in contenido


def test_escribir_json_indent_2(tmp_path: Path) -> None:
    """El JSON se escribe con indent=2."""
    ruta = tmp_path / "test.json"
    escribir_json(ruta, {"k": "v"})
    contenido = ruta.read_text(encoding="utf-8")
    assert '  "k"' in contenido


def test_listar_jsons(tmp_path: Path) -> None:
    """listar_jsons agrupa los JSON por subcarpeta."""
    (tmp_path / "comprobante").mkdir()
    (tmp_path / "comprobante" / "c1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "comprobante" / "c2.json").write_text("{}", encoding="utf-8")
    (tmp_path / "fierro").mkdir()
    (tmp_path / "fierro" / "f1.json").write_text("{}", encoding="utf-8")

    res = listar_jsons(tmp_path)
    assert "comprobante" in res
    assert "fierro" in res
    assert len(res["comprobante"]) == 2
    assert len(res["fierro"]) == 1