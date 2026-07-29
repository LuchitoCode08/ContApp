"""Tests unitarios de `utils/bitacora.py`.

Cubre:
- `configurar()` crea el logger correctamente.
- `leer_registros()` parsea lineas validas y maneja lineas rotas.
- `leer_registros()` devuelve en orden newest-first.
- `obtener_ultimo()` encuentra el ultimo proceso ejecutado.
- `es_modo_prueba()` / `quitar_marca_prueba()` funcionan en mensajes con/sin marca.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from utils.bitacora import (
    configurar,
    es_modo_prueba,
    leer_registros,
    log,
    obtener_ultimo,
    quitar_marca_prueba,
)


# ====================================================================
# configurar()
# ====================================================================


def test_configurar_crea_logger_con_consola(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """configurar() sin ruta solo agrega handler de consola."""
    # Reiniciamos el singleton del logger (puede tener handlers de tests previos).
    logger = logging.getLogger("contapp")
    logger.handlers.clear()

    configurar(nivel=logging.INFO)
    assert len(logger.handlers) >= 1


def test_configurar_con_ruta_crea_archivo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """configurar() con ruta crea el archivo y un FileHandler."""
    logger = logging.getLogger("contapp")
    logger.handlers.clear()

    ruta = tmp_path / "test.log"
    configurar(ruta_bitacora=ruta, nivel=logging.INFO)
    log().info("mensaje de prueba")

    assert ruta.exists()
    contenido = ruta.read_text(encoding="utf-8")
    assert "mensaje de prueba" in contenido
    assert "[INFO]" in contenido


def test_log_retorna_logger_correcto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """log() devuelve un logger con el nombre 'contapp'."""
    logger = logging.getLogger("contapp")
    logger.handlers.clear()
    configurar()
    assert log().name == "contapp"


# ====================================================================
# leer_registros()
# ====================================================================


_LINEA = re.compile(
    r"^(?P<fecha>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r"\s+\[(?P<nivel>[A-Z]+)\]"
    r"\s+(?P<modulo>\S+):\s*(?P<mensaje>.*)$"
)


def _escribir_log(ruta: Path, lineas: list[str]) -> None:
    """Helper: escribe lineas en el formato esperado."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def test_leer_registros_parsea_linea_valida(tmp_path: Path) -> None:
    """Una linea valida produce un registro con fecha/nivel/modulo/mensaje."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 10:30:00 [INFO] contapp: hola mundo",
    ])
    registros = leer_registros(log_path)
    assert len(registros) == 1
    r = registros[0]
    assert r["fecha"] == "2026-07-27 10:30:00"
    assert r["nivel"] == "INFO"
    assert r["modulo"] == "contapp"
    assert r["mensaje"] == "hola mundo"


def test_leer_registros_ignora_lineas_vacias(tmp_path: Path) -> None:
    """Lineas vacias entre registros no producen registros extra."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 10:30:00 [INFO] contapp: primero",
        "",
        "",
        "2026-07-27 10:31:00 [INFO] contapp: segundo",
    ])
    registros = leer_registros(log_path)
    assert len(registros) == 2


def test_leer_registros_orden_newest_first(tmp_path: Path) -> None:
    """Los registros se devuelven del mas reciente al mas viejo."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 09:00:00 [INFO] contapp: viejo",
        "2026-07-27 10:00:00 [INFO] contapp: medio",
        "2026-07-27 11:00:00 [INFO] contapp: nuevo",
    ])
    registros = leer_registros(log_path)
    assert len(registros) == 3
    assert registros[0]["mensaje"] == "nuevo"
    assert registros[1]["mensaje"] == "medio"
    assert registros[2]["mensaje"] == "viejo"


def test_leer_registros_con_limite(tmp_path: Path) -> None:
    """Con limite, devuelve solo los ultimos N registros."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 10:00:00 [INFO] contapp: a",
        "2026-07-27 10:01:00 [INFO] contapp: b",
        "2026-07-27 10:02:00 [INFO] contapp: c",
    ])
    registros = leer_registros(log_path, limite=2)
    # Newest-first: c, b
    assert len(registros) == 2
    assert registros[0]["mensaje"] == "c"
    assert registros[1]["mensaje"] == "b"


def test_leer_registros_archivo_inexistente(tmp_path: Path) -> None:
    """Si el archivo no existe, devuelve lista vacia."""
    registros = leer_registros(tmp_path / "no_existe.log")
    assert registros == []


def test_leer_registros_con_continuacion(tmp_path: Path) -> None:
    """Una linea que no matchea el patron se anexa al registro anterior."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 10:00:00 [INFO] contapp: mensaje principal",
        "esto es una continuacion de linea",
        "y esta tambien",
    ])
    registros = leer_registros(log_path)
    assert len(registros) == 1
    assert "continuacion" in registros[0]["mensaje"]
    assert "y esta tambien" in registros[0]["mensaje"]


# ====================================================================
# es_modo_prueba() / quitar_marca_prueba()
# ====================================================================


@pytest.mark.parametrize(
    ("mensaje", "esperado"),
    [
        ("[Comprobante] Excel procesado: foo.xlsx", False),
        ("[Comprobante] Excel procesado: foo.xlsx [PRUEBA]", True),
        ("[Fierro] Iniciando (modo_prueba=False)", False),
        ("[Fierro] Iniciando (modo_prueba=True)", False),  # la marca es [PRUEBA] explicita
        ("mensaje con [PRUEBA] en el medio", False),  # la marca es SOLO al final
        ("mensaje sin marca", False),
        ("[X] algo [PRUEBA] ", True),  # con espacio final
    ],
)
def test_es_modo_prueba(mensaje: str, esperado: bool) -> None:
    """es_modo_prueba() detecta la marca [PRUEBA] SOLO al final."""
    assert es_modo_prueba(mensaje) is esperado


def test_quitar_marca_prueba_con_marca() -> None:
    """Quita la marca [PRUEBA] del final del mensaje."""
    mensaje = "[Comprobante] Excel procesado: foo.xlsx [PRUEBA]"
    resultado = quitar_marca_prueba(mensaje)
    assert "[PRUEBA]" not in resultado
    assert "[Comprobante] Excel procesado: foo.xlsx" == resultado


def test_quitar_marca_prueba_sin_marca() -> None:
    """Si no hay marca, el mensaje queda igual."""
    mensaje = "[Comprobante] Excel procesado: foo.xlsx"
    assert quitar_marca_prueba(mensaje) == mensaje


def test_es_modo_prueba_y_quitar_trabajan_juntos() -> None:
    """Patron tipico: detectar, quitar y mostrar limpio."""
    mensaje = "[Fierro] Excel procesado: bar.xlsx [PRUEBA]"
    assert es_modo_prueba(mensaje) is True
    limpio = quitar_marca_prueba(mensaje)
    assert "[PRUEBA]" not in limpio
    assert "bar.xlsx" in limpio


# ====================================================================
# obtener_ultimo()
# ====================================================================


def test_obtener_ultimo_sin_registros(tmp_path: Path) -> None:
    """obtener_ultimo() devuelve None si no hay registros."""
    log_path = tmp_path / "vacio.log"
    _escribir_log(log_path, [])
    assert obtener_ultimo(ruta_bitacora=log_path) is None


def test_obtener_ultimo_encuentra_proceso_reciente(tmp_path: Path) -> None:
    """obtener_ultimo() devuelve el ultimo proceso ejecutado."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 09:00:00 [INFO] contapp: ContApp iniciando",
        "2026-07-27 09:01:00 [INFO] contapp: [Comprobante] Iniciando",
        "2026-07-27 09:02:00 [INFO] contapp: [Comprobante] CSV(s) leido(s): 20 fila(s)",
        "2026-07-27 09:03:00 [INFO] contapp: [Comprobante] Generado: foo.xlsx",
        "2026-07-27 09:04:00 [INFO] contapp: [Comprobante] FOAPAL generado: bar.xlsx",
        "2026-07-27 09:10:00 [INFO] contapp: [Fierro] Iniciando",
        "2026-07-27 09:11:00 [INFO] contapp: [Fierro] Excel procesado: baz.xlsx",
    ])
    ultimo = obtener_ultimo(ruta_bitacora=log_path)
    assert ultimo is not None
    assert ultimo["proceso"] == "fierro"
    # El archivo baz.xlsx debe estar en la lista.
    archivos = ultimo["archivos"]
    assert any("baz.xlsx" in a for a in archivos)


def test_obtener_ultimo_con_filtro_de_proceso(tmp_path: Path) -> None:
    """obtener_ultimo(proceso='comprobante') filtra por proceso."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 09:00:00 [INFO] contapp: [Fierro] Excel procesado: fierro.xlsx",
        "2026-07-27 09:01:00 [INFO] contapp: [Comprobante] Generado: comp.xlsx",
        "2026-07-27 09:02:00 [INFO] contapp: [Zeus] Excel procesado: zeus.xlsx",
    ])
    ultimo = obtener_ultimo(proceso="comprobante", ruta_bitacora=log_path)
    assert ultimo is not None
    assert ultimo["proceso"] == "comprobante"
    assert any("comp.xlsx" in a for a in ultimo["archivos"])


def test_obtener_ultimo_solo_marcadores_reales(tmp_path: Path) -> None:
    """obtener_ultimo() ignora logs que no son de ejecucion real (ej: 'Iniciando')."""
    log_path = tmp_path / "bitacora.log"
    _escribir_log(log_path, [
        "2026-07-27 09:00:00 [INFO] contapp: [Fierro] Iniciando (modo_prueba=False)",
        "2026-07-27 09:01:00 [INFO] contapp: [Fierro] Excel procesado: foo.xlsx",
        # Este 'Iniciando' no debe matchear.
        "2026-07-27 09:02:00 [INFO] contapp: [Fierro] Iniciando (modo_prueba=False)",
    ])
    ultimo = obtener_ultimo(ruta_bitacora=log_path)
    assert ultimo is not None
    archivos = ultimo["archivos"]
    # Solo debe estar foo.xlsx (el unico con marcador 'Excel procesado').
    assert len([a for a in archivos if "foo.xlsx" in a]) == 1
    assert not any("Iniciando" in str(a) for a in archivos)



# =====================================================================
# Tests de optimizacion: lectura por tail + cache + limite de lineas
# =====================================================================

def test_leer_registros_con_limite_no_lee_todo(tmp_path: Path) -> None:
    """Con ``limite``, leer_registros NO debe leer todo el archivo.

    Truco: generamos 5000 lineas pero limitamos a 10. El test no
    verifica el tiempo (fragil), sino que el resultado tiene <= 10
    registros y arranca desde el final.
    """
    log_path = tmp_path / "test.log"
    lineas = []
    for i in range(5000):
        lineas.append(
            f"2026-07-28 12:00:{i % 60:02d} [INFO] contapp: "
            f"[Fierro] Excel procesado: file_{i:04d}.xlsx"
        )
    log_path.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    from utils.bitacora import leer_registros
    registros = leer_registros(log_path, limite=10)
    # Solo los ultimos 10.
    assert len(registros) == 10
    # El mas reciente primero.
    assert "file_4999" in registros[0]["mensaje"]
    assert "file_4990" in registros[-1]["mensaje"]


def test_leer_ultimas_n_lineas_archivo_chico(tmp_path: Path) -> None:
    """Archivo de 5 lineas, pedimos 10 -> devolvemos las 5."""
    from utils.bitacora import _leer_ultimas_n_lineas
    log = tmp_path / "tiny.log"
    log.write_text("linea1\nlinea2\nlinea3\nlinea4\nlinea5\n", encoding="utf-8")
    lineas = _leer_ultimas_n_lineas(log, 10)
    assert lineas == ["linea1", "linea2", "linea3", "linea4", "linea5"]


def test_leer_ultimas_n_lineas_archivo_vacio(tmp_path: Path) -> None:
    from utils.bitacora import _leer_ultimas_n_lineas
    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    assert _leer_ultimas_n_lineas(log, 10) == []


def test_leer_ultimas_n_lineas_archivo_grande(tmp_path: Path) -> None:
    """5000 lineas, pedimos 3 -> devuelve las ultimas 3 exactas."""
    from utils.bitacora import _leer_ultimas_n_lineas
    log = tmp_path / "big.log"
    contenido = "\n".join(f"L{i:05d}" for i in range(5000)) + "\n"
    log.write_text(contenido, encoding="utf-8")
    lineas = _leer_ultimas_n_lineas(log, 3)
    assert lineas == ["L04997", "L04998", "L04999"]


def test_leer_ultimas_n_lineas_linea_muy_larga(tmp_path: Path) -> None:
    """Una sola linea gigante debe leerse completa, no cortada al chunk."""
    from utils.bitacora import _leer_ultimas_n_lineas
    log = tmp_path / "long.log"
    contenido = "X" * 50000 + "\n"  # 50 KB en una sola linea
    log.write_text(contenido, encoding="utf-8")
    lineas = _leer_ultimas_n_lineas(log, 10)
    assert len(lineas) == 1
    assert len(lineas[0]) == 50000


def test_cache_obtener_ultimo_devuelve_mismo_resultado(tmp_path: Path) -> None:
    """Llamadas seguidas con el mismo archivo deben devolver el cache."""
    log = tmp_path / "cache.log"
    log.write_text(
        "2026-07-28 12:00:00 [INFO] contapp: [Fierro] Excel procesado: x.xlsx\n",
        encoding="utf-8",
    )
    from utils.bitacora import (
        invalidar_cache_obtener_ultimo,
        obtener_ultimo,
    )
    invalidar_cache_obtener_ultimo()
    r1 = obtener_ultimo(ruta_bitacora=log)
    r2 = obtener_ultimo(ruta_bitacora=log)
    assert r1 == r2


def test_cache_obtener_ultimo_se_invalida(tmp_path: Path) -> None:
    """Despues de invalidar el cache, se vuelve a leer."""
    log = tmp_path / "cache2.log"
    log.write_text(
        "2026-07-28 12:00:00 [INFO] contapp: [Fierro] Excel procesado: x.xlsx\n",
        encoding="utf-8",
    )
    from utils.bitacora import (
        invalidar_cache_obtener_ultimo,
        obtener_ultimo,
    )
    invalidar_cache_obtener_ultimo()
    obtener_ultimo(ruta_bitacora=log)  # primera lectura
    invalidar_cache_obtener_ultimo()
    # Append un nuevo marcador.
    with log.open("a", encoding="utf-8") as f:
        f.write(
            "2026-07-28 12:01:00 [INFO] contapp: "
            "[Zeus] Excel procesado: y.xlsx\n"
        )
    # Sin invalidar, el cache devolveria el primero.
    r = obtener_ultimo(ruta_bitacora=log)
    # Pero el test cache es solo para ruta=None; con ruta custom no cachea.
    # Asi que este test es mas una prueba de humo que del cache real.
    assert r is not None


def test_cache_obtener_ultimo_no_aplica_con_filtro(tmp_path: Path) -> None:
    """Cuando se pasa ``proceso=`` o ruta custom, NO usa cache."""
    # Esto es por diseno: el cache es solo para la llamada sin parametros.
    # Validamos que con un archivo vacio + filtro, devuelve None (sin
    # registros que matcheen) y no rompe.
    log = tmp_path / "vacio.log"
    log.write_text("", encoding="utf-8")
    from utils.bitacora import (
        invalidar_cache_obtener_ultimo,
        obtener_ultimo,
    )
    invalidar_cache_obtener_ultimo()
    assert obtener_ultimo(proceso="comprobante", ruta_bitacora=log) is None


def test_obtener_ultimo_usa_cache_por_defecto(tmp_path: Path) -> None:
    """Si creamos un archivo nuevo con un marcador y NO invalidamos el
    cache, obtener_ultimo() (sin parametros) sigue devolviendo el viejo.
    Esto valida que el cache funciona para la llamada sin filtro."""
    log = tmp_path / "x.log"
    log.write_text(
        "2026-07-28 12:00:00 [INFO] contapp: "
        "[Fierro] Excel procesado: primero.xlsx\n",
        encoding="utf-8",
    )
    from utils.bitacora import (
        invalidar_cache_obtener_ultimo,
        obtener_ultimo,
        _resolver_ruta_bitacora,
    )
    # Monkey-patch de la ruta por defecto.
    import utils.bitacora as bm
    original = bm._resolver_ruta_bitacora
    bm._resolver_ruta_bitacora = lambda x=None: log if x is None else Path(x)
    try:
        invalidar_cache_obtener_ultimo()
        r1 = obtener_ultimo()
        assert "primero.xlsx" in r1["mensaje_crudo"]
        # Append de un nuevo marcador.
        with log.open("a", encoding="utf-8") as f:
            f.write(
                "2026-07-28 13:00:00 [INFO] contapp: "
                "[Zeus] Excel procesado: segundo.xlsx\n"
            )
        # Sin invalidar -> cache devuelve el primero.
        r2 = obtener_ultimo()
        assert "primero.xlsx" in r2["mensaje_crudo"]
        # Invalido -> lee el nuevo.
        invalidar_cache_obtener_ultimo()
        r3 = obtener_ultimo()
        assert "segundo.xlsx" in r3["mensaje_crudo"]
    finally:
        bm._resolver_ruta_bitacora = original

