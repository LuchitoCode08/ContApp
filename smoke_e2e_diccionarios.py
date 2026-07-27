"""Smoke test E2E: editar un JSON real, cancelar (sin dialogo), guardar con backup."""
import os
import shutil
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

from app.config import BITACORA_LOG, JSONS_DIR
from utils.bitacora import configurar
configurar(BITACORA_LOG)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

# Monkey-patch: saltamos todos los dialogos para que el test no se quede
# esperando input del usuario.
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

app = QApplication(sys.argv)

from ui.ventanas.editor_json import PantallaDiccionarios
from utils.json_manager import leer_json, escribir_json

# Archivo de prueba: mapeo_descripciones.json (Tipo A, pequenio).
target = JSONS_DIR / "fierro" / "mapeo_descripciones.json"
backup_dir = Path("data/backups")
original = leer_json(target)
print(f"Original: {len(original)} entradas")

# Cargar la pantalla.
p = PantallaDiccionarios()
target = None
for sec_i in range(p._arbol.topLevelItemCount()):
    sec = p._arbol.topLevelItem(sec_i)
    for child_i in range(sec.childCount()):
        if sec.child(child_i).text(0).startswith("Mapeo de Descripciones"):
            target = sec.child(child_i)
            break
    if target:
        break
p._arbol.setCurrentItem(target)
target_path = Path(target.data(0, Qt.ItemDataRole.UserRole))
QApplication.processEvents()

print(f"[OK] Cargado: {p._lbl_titulo.text()}, tipo {p._tipo_actual}")
print(f"     cambios: {p._lbl_cambios.text()}")

# Editar la primera fila.
tabla = p._editor_widget.tabla
print(f"[OK] Tabla tiene {tabla.rowCount()} filas")
primer_valor = tabla.item(0, 1).text()
print(f"     valor original: {primer_valor!r}")
tabla.item(0, 1).setText("VALOR DE PRUEBA EDITADO")
p._editor_widget._on_item_changed(tabla.item(0, 1))
print(f"     tras edit: cambios={p._lbl_cambios.text()}")
assert p._hay_cambios, "Deberia haber cambios"

# Cancelar (QMessageBox.question monkey-patch retorna Yes).
p._on_cancelar()
print(f"[OK] tras cancelar: cambios={p._lbl_cambios.text()}")
assert not p._hay_cambios, "Tras cancelar no deberia haber cambios"

# IMPORTANTE: tras cancelar, el editor se reconstruye con una tabla NUEVA.
tabla = p._editor_widget.tabla
print(f"     nueva tabla: {tabla.rowCount()} filas")

# Editar de nuevo y guardar.
tabla.item(0, 1).setText("VALOR E2E GUARDADO")
p._editor_widget._on_item_changed(tabla.item(0, 1))
print(f"     re-edit: cambios={p._lbl_cambios.text()}")

# Guardar (QMessageBox.question/information monkey-patch).
p._on_guardar()
print(f"[OK] guardado -> cambios={p._lbl_cambios.text()}")

# Verificar que el archivo quedo escrito.
nuevo = leer_json(target_path)
assert nuevo[next(iter(nuevo))] == "VALOR E2E GUARDADO"
print(f"[OK] contenido verificado en disco")

# Verificar que se creo un backup (escribir_json usa <directorio>/.backups por defecto).
backup_search_dir = target_path.parent / ".backups"
backups = list(backup_search_dir.glob("*mapeo_descripciones*"))
print(f"     backups en {backup_search_dir}: {[b.name for b in backups]}")
assert len(backups) > 0, "Deberia haber al menos un backup"

# Restaurar el archivo original y limpiar backups.
escribir_json(target_path, original)
print(f"[OK] archivo restaurado al estado original")
for b in backups:
    b.unlink()
print(f"[OK] backups de smoke eliminados")

print(f"\n== E2E completado OK ==")