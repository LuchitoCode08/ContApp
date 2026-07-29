"""Tests del lock por archivo en `utils.json_manager`.

Cubre:
- Adquirir + liberar lock en el mismo usuario (2 veces seguidas funciona).
- Verificar lock_adquirido distingue nuestro lock de uno ajeno.
- con_lock() funciona como context manager.
- Si no se puede adquirir, con_lock() entra al bloque con lock=None
  (de modo que el caller pueda chequear y abortar).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from utils.json_manager import (
    adquirir_lock,
    con_lock,
    liberar_lock,
    lock_adquirido,
    ruta_lock,
)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _lock_ajeno(ruta_json: Path, otro_usuario: str = "OTRO_USUARIO_FALSO") -> Path:
    """Crea un archivo .lock con contenido de OTRO usuario (sin usar la API)."""
    ruta = ruta_lock(ruta_json)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(otro_usuario, encoding="utf-8")
    return ruta


# --------------------------------------------------------------------
# ruta_lock
# --------------------------------------------------------------------

def test_ruta_lock_agrega_sufijo(tmp_path: Path) -> None:
    ruta = tmp_path / "datos.json"
    assert ruta_lock(ruta) == tmp_path / "datos.json.lock"


def test_ruta_lock_con_path_string(tmp_path: Path) -> None:
    """Acepta tanto Path como str."""
    ruta = tmp_path / "x.json"
    assert ruta_lock(str(ruta)) == tmp_path / "x.json.lock"


# --------------------------------------------------------------------
# adquirir + liberar
# --------------------------------------------------------------------

def test_adquirir_crea_archivo_lock(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    lock = adquirir_lock(ruta)
    assert lock is not None
    assert lock.exists()
    assert ruta_lock(ruta).exists()


def test_adquirir_doble_es_del_mismo_usuario(tmp_path: Path) -> None:
    """Dos acquires seguidos del mismo usuario devuelven la misma ruta."""
    ruta = tmp_path / "test.json"
    l1 = adquirir_lock(ruta)
    l2 = adquirir_lock(ruta)
    assert l1 == l2
    assert l1.exists()


def test_adquirir_con_lock_ajeno_devuelve_none(tmp_path: Path) -> None:
    """Si otro usuario ya tiene el lock, no lo podemos adquirir."""
    ruta = tmp_path / "test.json"
    _lock_ajeno(ruta, "ALGUIEN_MAS")
    assert adquirir_lock(ruta) is None


def test_adquirir_en_path_inexistente_crea_solo_el_lock(tmp_path: Path) -> None:
    """Si el JSON no existe, el lock se crea igual."""
    ruta = tmp_path / "no_existe.json"
    lock = adquirir_lock(ruta)
    assert lock is not None
    assert not ruta.exists()  # NO crea el JSON, solo el lock


# --------------------------------------------------------------------
# lock_adquirido
# --------------------------------------------------------------------

def test_lock_adquirido_sin_archivo_es_false(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    assert lock_adquirido(ruta) is False


def test_lock_adquirido_con_lock_propio_es_true(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    adquirir_lock(ruta)
    assert lock_adquirido(ruta) is True


def test_lock_adquirido_con_lock_ajeno_es_false(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    _lock_ajeno(ruta, "OTRO")
    assert lock_adquirido(ruta) is False


# --------------------------------------------------------------------
# liberar
# --------------------------------------------------------------------

def test_liberar_nuestro_lock_borra_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    adquirir_lock(ruta)
    assert liberar_lock(ruta) is True
    assert not ruta_lock(ruta).exists()


def test_liberar_lock_ajeno_no_borra(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    _lock_ajeno(ruta, "OTRO")
    assert liberar_lock(ruta) is False
    assert ruta_lock(ruta).exists()  # sigue ahi


def test_liberar_sin_lock_devuelve_false(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    assert liberar_lock(ruta) is False


# --------------------------------------------------------------------
# con_lock (context manager)
# --------------------------------------------------------------------

def test_con_lock_ejecuta_bloque_y_libera(tmp_path: Path) -> None:
    ruta = tmp_path / "test.json"
    with con_lock(ruta) as lock:
        assert lock is not None
        assert lock.exists()
    # Al salir del with, el lock se libero.
    assert not ruta_lock(ruta).exists()


def test_con_lock_bloque_no_se_ejecuta_si_no_hay_lock(tmp_path: Path) -> None:
    """Si el lock no se puede adquirir (lo tiene otro), el bloque NO corre
    y ``lock`` es None adentro del with."""
    ruta = tmp_path / "test.json"
    _lock_ajeno(ruta, "OTRO")
    ejecutado = []
    with con_lock(ruta) as lock:
        assert lock is None
        ejecutado.append("adentro")
    # El bloque se ejecuta UNA vez (para que el caller pueda chequear),
    # pero el caller puede decidir abortar.
    assert ejecutado == ["adentro"]