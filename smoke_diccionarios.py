"""Smoke test de la pantalla Diccionarios: cargar cada tipo de JSON."""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

from app.config import BITACORA_LOG
from utils.bitacora import configurar
configurar(BITACORA_LOG)

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from ui.ventanas.editor_json import (
    PantallaDiccionarios,
    EditorTipoA,
    EditorTipoB,
    EditorTipoC,
    EditorTipoD,
)
from utils.json_manager import detectar_tipo, leer_json
from pathlib import Path

print("== Pantalla Diccionarios ==")
p = PantallaDiccionarios()
print(f"[OK] Pantalla instanciada, items en arbol: {sum(sec.childCount() for i in range(p._arbol.topLevelItemCount()) for sec in [p._arbol.topLevelItem(i)])}")

# Recorrer cada JSON y simular seleccion.
idx = 0
for sec_i in range(p._arbol.topLevelItemCount()):
    sec = p._arbol.topLevelItem(sec_i)
    for child_i in range(sec.childCount()):
        child = sec.child(child_i)
        p._arbol.setCurrentItem(child)
        QApplication.processEvents()
        tipo = p._tipo_actual
        editor_tipo = type(p._editor_widget).__name__ if p._editor_widget else "None"
        print(f"  [{idx}] {p._lbl_titulo.text()} -> tipo {tipo} ({editor_tipo})")
        idx += 1

print("\n== Edits manuales en cada tipo ==")

# Tipo A: editar un valor.
datos_a = {"clave1": "valor1", "clave2": "valor2"}
e_a = EditorTipoA(datos_a, lambda d: None)
print(f"  [TipoA] inicial: {e_a.datos}")
e_a.tabla.item(0, 1).setText("MODIFICADO")
e_a._on_item_changed(e_a.tabla.item(0, 1))
print(f"  [TipoA] tras edit: {e_a.datos}")

# Tipo D: agregar par.
datos_d = {"tarjetas": [["^foo", "bar"]]}
e_d = EditorTipoD(datos_d, lambda d: None)
print(f"  [TipoD] inicial: {e_d.datos}")
e_d.datos.append(["^nuevo", "nuevo_valor"])
print(f"  [TipoD] tras append: {e_d.datos}")

# Tipo B: inspeccionar campos.
datos_b = {
    "creditos": {
        "1334": {"Fondo": "FOPNAL", "Organizacion": "13201", "D/C": "C"},
    },
    "debitos": {},
}
e_b = EditorTipoB(datos_b, lambda d: None)
print(f"  [TipoB] campos inferidos: {e_b._campos}")

# Tipo C: roundtrip de lista vs string.
datos_c = {
    "Intereses": {"1998": "AJUSTE"},
    "Gastos": {"480": ["COMIS"]},
}
e_c = EditorTipoC(datos_c, lambda d: None)
print(f"  [TipoC] roundtrip OK")

print("\n== Todo OK ==")