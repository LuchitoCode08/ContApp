"""Smoke test rapido para los cambios de bitacora."""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

from app.config import BITACORA_LOG
from utils.bitacora import (
    configurar,
    es_modo_prueba,
    leer_registros,
    obtener_ultimo,
    quitar_marca_prueba,
)

configurar(BITACORA_LOG)

print("== Orden newest-first ==")
regs = leer_registros()
print(f"  Registros: {len(regs)}")
print(f"  Primero (mas reciente): {regs[0]['fecha']} | {regs[0]['mensaje'][:50]}")
print(f"  Ultimo (mas viejo):     {regs[-1]['fecha']} | {regs[-1]['mensaje'][:50]}")
assert regs[0]["fecha"] >= regs[-1]["fecha"], "El primero debe ser mas reciente"

print("\n== Deteccion de modo_prueba ==")
casos = [
    ("[X] Foo", False),  # sin marca -> False (no es prueba)
    ("[X] Foo [PRUEBA]", True),
    ("[X] Foo [PRUEBA] ", True),
    ("[X] Foo [PRODUCCION]", False),  # marca incorrecta
    ("Esto es [PRUEBA] en el medio", False),  # marca solo al final cuenta
]
for msg, esperado in casos:
    res = es_modo_prueba(msg)
    marca = "OK" if res == esperado else "FAIL"
    print(f"  [{marca}] {msg!r} -> {res} (esperado {esperado})")

print("\n== Quitar marca ==")
print(f"  antes:  '[X] Foo [PRUEBA]'")
print(f"  despues: '{quitar_marca_prueba('[X] Foo [PRUEBA]')}'")
print(f"  antes:  '[X] Foo'")
print(f"  despues: '{quitar_marca_prueba('[X] Foo')}'")

print("\n== obtener_ultimo ==")
ult = obtener_ultimo()
if ult:
    print(f"  proceso: {ult.get('proceso')}")
    print(f"  fecha:   {ult.get('fecha')}")
    print(f"  msg:     {ult.get('mensaje')[:60]}")
else:
    print("  (sin registros)")

print("\n== Todo OK ==")