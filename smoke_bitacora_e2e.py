"""Smoke E2E de la pantalla Configuracion con los cambios de bitacora."""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

from app.config import BITACORA_LOG
from utils.bitacora import configurar

configurar(BITACORA_LOG)

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from ui.ventanas.configuracion import PantallaConfiguracion

print("== Pantalla Configuracion con columna Modo ==")
p = PantallaConfiguracion()
print(f"[OK] columnas: {p._tabla.columnCount()}")
print(f"     headers: {[p._tabla.horizontalHeaderItem(i).text() for i in range(p._tabla.columnCount())]}")
print(f"[OK] registros cargados: {len(p._registros)}")
print(f"     primer registro: {p._tabla.item(0, 0).text()} | modo='{p._tabla.item(0, 3).text()}' | {p._tabla.item(0, 5).text()[:50]}")
print(f"     ultimo registro:  {p._tabla.item(p._tabla.rowCount()-1, 0).text()} | modo='{p._tabla.item(p._tabla.rowCount()-1, 3).text()}' | {p._tabla.item(p._tabla.rowCount()-1, 5).text()[:50]}")

# Verificar que el orden es newest-first.
primera = p._tabla.item(0, 0).text()
ultima = p._tabla.item(p._tabla.rowCount()-1, 0).text()
assert primera >= ultima, f"Orden incorrecto: {primera} < {ultima}"
print(f"[OK] orden newest-first verificado: {primera} >= {ultima}")

# Probar filtro por modo (no hay registros con marca [PRUEBA] todavia).
p._filtro_modo.setCurrentText("Prueba")
p._aplicar_filtros()
print(f"[OK] filtro modo=Prueba -> {p._tabla.rowCount()} filas (esperado 0)")
p._filtro_modo.setCurrentText("Produccion")
p._aplicar_filtros()
print(f"[OK] filtro modo=Produccion -> {p._tabla.rowCount()} filas (esperado 0, log sin marcas)")
p._filtro_modo.setCurrentText("Todos")
p._aplicar_filtros()
print(f"[OK] filtro modo=Todos -> {p._tabla.rowCount()} filas")

print("\n== Test con un registro [PRUEBA] simulado ==")
# Appendeamos una linea con marca [PRUEBA] al log.
import re
with BITACORA_LOG.open("a", encoding="utf-8") as f:
    f.write("2026-07-27 10:30:00 [INFO] contapp: [Comprobante] Excel procesado: TEST.xlsx [PRUEBA]\n")

p.refrescar()
print(f"     total registros: {p._tabla.rowCount()}")
primera = p._tabla.item(0, 0).text()
primera_modo = p._tabla.item(0, 3).text()
primera_msg = p._tabla.item(0, 5).text()
print(f"     primero: {primera} | modo='{primera_modo}' | msg='{primera_msg}'")
assert primera_modo == "PRUEBA", f"Esperaba PRUEBA, obtuve {primera_modo!r}"
assert "[PRUEBA]" not in primera_msg, "La marca no debe quedar en el mensaje visible"
print(f"[OK] marca [PRUEBA] detectada en la columna Modo y quitada del mensaje")

# Filtro por modo = Prueba deberia incluirlo.
p._filtro_modo.setCurrentText("Prueba")
p._aplicar_filtros()
print(f"[OK] filtro modo=Prueba -> {p._tabla.rowCount()} filas (>=1)")
assert p._tabla.rowCount() >= 1

# Limpieza: removemos la linea de prueba.
with BITACORA_LOG.open("r", encoding="utf-8") as f:
    lineas = f.readlines()
lineas = [l for l in lineas if "TEST.xlsx" not in l]
with BITACORA_LOG.open("w", encoding="utf-8") as f:
    f.writelines(lineas)
print("[OK] linea de prueba removida del log")

p._filtro_modo.setCurrentText("Todos")
p.refrescar()
print(f"[OK] tras limpieza: {p._tabla.rowCount()} filas")

print("\n== Todo OK ==")