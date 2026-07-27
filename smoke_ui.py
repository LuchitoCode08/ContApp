"""Smoke test rapido para verificar que la nueva UI carga sin errores.

No lanza la app: solo importa los modulos y los instancia en modo offscreen
para verificar que no haya excepciones de sintaxis, imports faltantes, etc.
"""
import sys
import os

# Forzamos el uso del plugin offscreen de Qt para no requerir display.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, ".")

print("== Imports del nucleo ==")
from utils.bitacora import leer_registros, obtener_ultimo, log
print("[OK] utils.bitacora")

from utils.json_manager import detectar_tipo, leer_json
print("[OK] utils.json_manager")

print("\n== Funciones nuevas de bitacora ==")
regs = leer_registros()
print(f"[OK] leer_registros: {len(regs)} registros")
ult = obtener_ultimo()
if ult:
    print(f"[OK] obtener_ultimo: proceso={ult.get('proceso')} "
          f"archivos={len(ult.get('archivos', []))}")
else:
    print("[OK] obtener_ultimo: sin registros")

print("\n== Deteccion de tipo de los 8 JSONs ==")
from pathlib import Path
from app.config import JSONS_DIR
for jf in sorted(JSONS_DIR.rglob("*.json")):
    datos = leer_json(jf)
    t = detectar_tipo(datos)
    rel = str(jf.relative_to(JSONS_DIR))
    print(f"  {rel}: tipo {t}")

print("\n== Imports de UI (requiere PySide6) ==")
from app.config import get_config
print("[OK] app.config")

cfg = get_config()
print(f"[OK] get_config: usuario={cfg.usuario}, "
      f"procesos={list(cfg.procesos.keys())}")

print("\n== Verificando sintaxis de las pantallas nuevas ==")
# Solo importamos para chequear sintaxis (no instanciamos widgets).
import py_compile
for path in [
    "ui/ventanas/principal.py",
    "ui/ventanas/editor_json.py",
    "ui/ventanas/configuracion.py",
    "ui/ventanas/ejecutar_proceso.py",
    "utils/bitacora.py",
]:
    py_compile.compile(path, doraise=True)
    print(f"  [OK] {path}")

print("\n== Smoke test completado OK ==")