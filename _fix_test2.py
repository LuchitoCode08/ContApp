from pathlib import Path
import re

f = Path(r'c:\Users\lfloaiza\Documents\Demo\tests\test_bitacora.py')
c = f.read_text(encoding='utf-8')

m = re.search(
    r'def test_obtener_ultimo_usa_cache_por_defecto.*?(?=\n\ndef |\nclass |\Z)',
    c, re.DOTALL,
)
if not m:
    print("NO MATCH")
else:
    NEW = '''def test_obtener_ultimo_usa_cache_por_defecto(tmp_path: Path) -> None:
    """Si creamos un archivo nuevo con un marcador y NO invalidamos el
    cache, obtener_ultimo() (sin parametros) sigue devolviendo el viejo.
    Esto valida que el cache funciona para la llamada sin filtro."""
    log = tmp_path / "x.log"
    log.write_text(
        "2026-07-28 12:00:00 [INFO] contapp: "
        "[Fierro] Excel procesado: primero.xlsx\\n",
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
                "[Zeus] Excel procesado: segundo.xlsx\\n"
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

'''
    c2 = c.replace(m.group(0), NEW)
    if c == c2:
        print("NO REPLACE")
    else:
        f.write_text(c2, encoding='utf-8')
        print("Bloque reescrito")
