"""Tests unitarios de `utils/json_manager.py`.

Cubre:
- `leer_json()` / `escribir_json()` roundtrip.
- `escribir_json()` crea backup automatico.
- `detectar_tipo()` clasifica los 4 patrones A/B/C/D correctamente.
- Carpeta de backups personalizada.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from utils.json_manager import (
    TIPO_A,
    TIPO_B,
    TIPO_C,
    TIPO_D,
    detectar_tipo,
    escribir_json,
    leer_json,
)


# ====================================================================
# detectar_tipo
# ====================================================================


def test_detectar_tipo_a_plano() -> None:
    """Tipo A: {clave: valor} plano con escalares."""
    datos = {"47789085868": "890903938", "47777828641": "890903938"}
    assert detectar_tipo(datos) == TIPO_A


def test_detectar_tipo_b_secciones_subobjetos() -> None:
    """Tipo B: {seccion: {clave: {campo: valor, ...}}}.

    El formato real del FOAPAL cae en Tipo B porque cada seccion tiene
    >1 items (la heuristica de `detectar_tipo` verifica que
    cada seccion tenga mas de 1 sub-objeto para clasificar como B).
    El contenido de los sub-objetos son strings, pero la heuristica
    no inspecciona los campos internos (solo cuenta items por seccion).

    NOTA: esto significa que un JSON con secciones de 1 solo item
    se clasifica como C en vez de B. Es un caso limite conocido.
"""
    datos = {
        "creditos": {
            "1334": {
                "Fondo": "FOPNAL",
                "Organizacion": "13201",
                "Cuenta": "530515",
                "Programa": "999999",
                "D/C": "C",
            },
            "2999": {
                "Fondo": "FOPNAL",
                "Organizacion": "999999",
                "Cuenta": "421010",
                "Programa": "999999",
                "D/C": "D",
            },
            "4449": {
                "Fondo": "FOPNAL",
                "Organizacion": "13201",
                "Cuenta": "511560",
                "Programa": "999999",
                "D/C": "C",
            },
        },
        "debitos": {
            "480": {
                "Fondo": "FOPNAL",
                "Organizacion": "13201",
                "Cuenta": "529510",
                "Programa": "999999",
                "D/C": "D",
            },
            "609": {
                "Fondo": "FOPNAL",
                "Organizacion": "13201",
                "Cuenta": "529515",
                "Programa": "999999",
                "D/C": "D",
            },
        },
    }
    assert detectar_tipo(datos) == TIPO_B


def test_detectar_tipo_c_secciones_valores_mixtos() -> None:
    """Tipo C: {seccion: {clave: string | list[string]}}."""
    datos = {
        "Intereses": {"1998": "AJUSTE INTERESES AHORROS DB"},
        "Gastos bancarios": {
            "480": ["COMIS CONSIGNACION SUCURSAL"],
            "5386": ["REV COMISION DOBLE", "REV IVA COMISION DOBLE"],
        },
    }
    assert detectar_tipo(datos) == TIPO_C


def test_detectar_tipo_d_lista_de_pares() -> None:
    """Tipo D: {clave_unica: [[patron, reemplazo], ...]}."""
    datos = {
        "tarjetas": [
            ["^Comision Tarjeta CR AMEX", "Comision T CR AMEX"],
            ["^Comision Tarjeta DB MasterCard", "Comision T DB MC"],
        ]
    }
    assert detectar_tipo(datos) == TIPO_D


def test_detectar_tipo_vacio_es_a() -> None:
    """Un dict vacio se trata como Tipo A (default conservador)."""
    assert detectar_tipo({}) == TIPO_A


# ====================================================================
# leer_json / escribir_json roundtrip
# ====================================================================


def test_leer_escribir_roundtrip(tmp_path: Path) -> None:
    """Lo que escribimos se puede leer de vuelta identico."""
    ruta = tmp_path / "test.json"
    datos = {"clave1": "valor1", "lista": [1, 2, 3], "anidado": {"k": "v"}}

    escribir_json(ruta, datos, hacer_backup=False)
    leido = leer_json(ruta)

    assert leido == datos


def test_escribir_json_crea_backup(tmp_path: Path) -> None:
    """escribir_json deja una copia del archivo original en .backups/."""
    ruta = tmp_path / "datos.json"
    ruta.write_text(json.dumps({"original": True}), encoding="utf-8")

    backup = escribir_json(ruta, {"nuevo": True})

    assert backup is not None
    assert backup.exists()
    assert backup.parent == tmp_path / ".backups"
    # El backup usa el mismo nombre del archivo original (sin timestamp).
    assert backup.name == "datos.json"
    # No debe haber backups con timestamp adicionales.
    assert list((tmp_path / ".backups").glob("*.json")) == [backup]
    # El backup tiene el contenido viejo.
    assert json.loads(backup.read_text(encoding="utf-8")) == {"original": True}
    # El archivo actual tiene el contenido nuevo.
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"nuevo": True}


def test_escribir_json_sobrescribe_backup_unico(tmp_path: Path) -> None:
    """Solo debe existir un backup por archivo, con la ultima version anterior."""
    ruta = tmp_path / "datos.json"
    ruta.write_text(json.dumps({"v1": True}), encoding="utf-8")

    backup1 = escribir_json(ruta, {"v2": True})
    assert backup1 is not None
    assert json.loads(backup1.read_text(encoding="utf-8")) == {"v1": True}

    # Editar de nuevo: el backup debe sobrescribirse con la v2.
    backup2 = escribir_json(ruta, {"v3": True})
    assert backup2 == backup1
    assert backup2.exists()
    # Solo hay un archivo de backup en la carpeta.
    assert list((tmp_path / ".backups").glob("*.json")) == [backup2]
    # El backup ahora guarda la v2 (la ultima version anterior).
    assert json.loads(backup2.read_text(encoding="utf-8")) == {"v2": True}
    # El archivo actual tiene la v3.
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"v3": True}


def test_escribir_json_sin_backup(tmp_path: Path) -> None:
    """Si hacer_backup=False, no se crea backup."""
    ruta = tmp_path / "datos.json"
    ruta.write_text("{}", encoding="utf-8")

    backup = escribir_json(ruta, {"a": 1}, hacer_backup=False)

    assert backup is None
    assert not (tmp_path / ".backups").exists()


def test_escribir_json_carpeta_backups_personalizada(tmp_path: Path) -> None:
    """carpeta_backups permite elegir donde guardar el backup."""
    ruta = tmp_path / "datos.json"
    ruta.write_text("{}", encoding="utf-8")

    carpeta_custom = tmp_path / "mis_backups"
    backup = escribir_json(ruta, {"x": 1}, carpeta_backups=carpeta_custom)

    assert backup is not None
    assert backup.parent == carpeta_custom
    assert backup.name == "datos.json"


def test_escribir_json_sin_archivo_previo_no_hace_backup(tmp_path: Path) -> None:
    """Si el archivo no existe, no hay nada que respaldar."""
    ruta = tmp_path / "inexistente.json"

    backup = escribir_json(ruta, {"nuevo": True})

    assert backup is None  # nada que respaldar


def test_escribir_json_preserva_unicode(tmp_path: Path) -> None:
    """Los caracteres acentuados y especiales se preservan (ensure_ascii=False)."""
    ruta = tmp_path / "test.json"
    datos = {"texto": "Códigos Contables - NIT Bancolombia", "simbolo": "→"}

    escribir_json(ruta, datos, hacer_backup=False)
    contenido = ruta.read_text(encoding="utf-8")

    assert "Códigos" in contenido
    assert "→" in contenido
    # No debe escapar como \uXXXX.
    assert "C\\u00f3digos" not in contenido


def test_escribir_json_indent_2(tmp_path: Path) -> None:
    """El JSON se escribe con indent=2."""
    ruta = tmp_path / "test.json"
    escribir_json(ruta, {"k": "v"}, hacer_backup=False)
    contenido = ruta.read_text(encoding="utf-8")
    # 2 espacios de indentacion.
    assert '  "k"' in contenido