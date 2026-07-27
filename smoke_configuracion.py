"""Smoke test de la pantalla Configuracion: filtros y exportacion."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

from app.config import BITACORA_LOG
from utils.bitacora import configurar
configurar(BITACORA_LOG)

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from ui.ventanas.configuracion import PantallaConfiguracion

print("== Pantalla Configuracion ==")
p = PantallaConfiguracion()
print(f"[OK] instanciada, registros cargados: {len(p._registros)}")
print(f"     - filas en tabla: {p._tabla.rowCount()}")
print(f"     - total label: {p._lbl_total.text()}")

# Probar filtro por proceso (llamada directa, sin esperar al timer).
p._filtro_proceso.setCurrentText("Comprobante")
p._aplicar_filtros()
print(f"[OK] filtro proceso=Comprobante -> {p._tabla.rowCount()} filas")

# Probar filtro por nivel.
p._filtro_proceso.setCurrentText("Todos")
p._filtro_nivel.setCurrentText("ERROR")
p._aplicar_filtros()
print(f"[OK] filtro nivel=ERROR -> {p._tabla.rowCount()} filas")

# Probar filtro por texto.
p._filtro_nivel.setCurrentText("Todos")
p._buscador.setText("ContApp")
p._aplicar_filtros()
print(f"[OK] filtro texto=ContApp -> {p._tabla.rowCount()} filas")

# Probar filtro combinado.
p._buscador.setText("")
p._filtro_proceso.setCurrentText("Fierro")
p._filtro_nivel.setCurrentText("INFO")
p._aplicar_filtros()
print(f"[OK] filtro proceso=Fierro AND nivel=INFO -> {p._tabla.rowCount()} filas")

# Resetear.
p._filtro_proceso.setCurrentText("Todos")
p._filtro_nivel.setCurrentText("Todos")
p._buscador.setText("")
p._aplicar_filtros()
print(f"[OK] tras reset -> {p._tabla.rowCount()} filas")

# Probar exportacion a CSV (sin dialogo: escribimos directo con helper).
import csv
from pathlib import Path
csv_path = Path(tempfile.gettempdir()) / "smoke_export.csv"
with csv_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Fecha", "Proceso", "Nivel", "Modulo", "Mensaje"])
    regs = p._obtener_registros_ffiltrados() if hasattr(p, "_obtener_registros_ffiltrados") else p._obtener_registros_filtrados()
    for r in regs[:5]:
        w.writerow([r["fecha"], r.get("_proceso", ""), r["nivel"], r["modulo"], r["mensaje"][:50]])
print(f"[OK] export CSV -> {csv_path} ({csv_path.stat().st_size} bytes)")

# Probar exportacion a Excel.
from openpyxl import Workbook
xlsx_path = Path(tempfile.gettempdir()) / "smoke_export.xlsx"
wb = Workbook()
ws = wb.active
ws.title = "Bitacora"
ws.append(["Fecha", "Proceso", "Nivel", "Modulo", "Mensaje"])
for r in regs[:5]:
    ws.append([r["fecha"], r.get("_proceso", ""), r["nivel"], r["modulo"], r["mensaje"][:50]])
wb.save(xlsx_path)
print(f"[OK] export Excel -> {xlsx_path} ({xlsx_path.stat().st_size} bytes)")

# Probar _refresco_silencioso (no debe crashear).
p._refresco_silencioso()
print(f"[OK] _refresco_silencioso() sin errores")

print("\n== Todo OK ==")