"""Smoke test profundo: instancia la VentanaPrincipal y las 4 pantallas.

Usa el plugin offscreen de Qt para no requerir display.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

# Configurar bitacora antes de instanciar widgets (los widgets la usan).
from app.config import BITACORA_LOG
from utils.bitacora import configurar
configurar(BITACORA_LOG)

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
print("[OK] QApplication creada")

# Importar y construir VentanaPrincipal.
from ui.ventanas.principal import VentanaPrincipal
v = VentanaPrincipal()
print("[OK] VentanaPrincipal instanciada")
print(f"     - titulo: {v.windowTitle()}")
print(f"     - tamano: {v.size().width()}x{v.size().height()}")
print(f"     - sidebar items: {v.sidebar.count()}")
print(f"     - stack count: {v.stack.count()}")

# Verificar que las 4 pantallas se instanciaron.
for i in range(v.stack.count()):
    w = v.stack.widget(i)
    print(f"     - pantalla {i}: {type(w).__name__}")

# Probar navegacion entre pantallas.
for i in range(4):
    v.sidebar.setCurrentRow(i)
    QApplication.processEvents()
    idx = v.stack.currentIndex()
    print(f"     - sidebar row {i} -> stack idx {idx}")

# Probar pre-seleccionar un proceso desde Inicio.
v._ir_a_procesos_preseleccionado("comprobante")
QApplication.processEvents()
print(f"[OK] _ir_a_procesos_preseleccionado -> "
      f"sidebar={v.sidebar.currentRow()}, stack={v.stack.currentIndex()}")

# Probar el panel de ultimo ejecutado.
v.pantalla_inicio.refrescar_ultimo()
print("[OK] refrescar_ultimo() sin errores")

# Volver a Inicio y refrescar.
v.sidebar.setCurrentRow(0)
QApplication.processEvents()
print(f"[OK] volver a Inicio -> stack={v.stack.currentIndex()}")

print("\n== Todas las pantallas funcionan ==")