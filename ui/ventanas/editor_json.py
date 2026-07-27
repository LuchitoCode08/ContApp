"""Pantalla Diccionarios: editor inteligente de los 8 JSONs del sistema.

Estructura visual:
+------+---------------------------------------------+
| List |  [Titulo del JSON]    tipo: B              |
| JSON |  badges: Modificado / Nuevo                |
|  ◯   |                                             |
|  ◯   |  Editor (segun tipo A/B/C/D)               |
|  ◯   |                                             |
|  ◯   |                                             |
|      |  [X cambios] [+ Agregar] [Cancelar] [Guardar] |
+------+---------------------------------------------+
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import JSONS_DIR, get_config
from utils.bitacora import log
from utils.json_manager import (
    TIPO_A,
    TIPO_B,
    TIPO_C,
    TIPO_D,
    detectar_tipo,
    escribir_json,
    leer_json,
)


# Paleta para badges de cambios.
COLOR_FONDO_NUEVO = "#E8F5E9"   # verde suave (alta confianza)
COLOR_FONDO_MODIF = "#FFF8E1"   # amarillo suave (cambio pendiente)
COLOR_BORDE = "#BDBDBD"

# Nombres legibles para los 8 JSONs del sistema (lo que ve el usuario).
# Si se agrega un JSON nuevo, el fallback usa el nombre del archivo
# formateado (sin extension, con palabras capitalizadas).
NOMBRES_JSON: dict[str, dict[str, str]] = {
    "comprobante": {
        "codigos_conceptos.json": "Códigos de Conceptos",
        "codigos_contables.json": "Códigos Contables",
        "foapal.json": "FOAPAL",
        "nit_bancolombia.json": "NIT Bancolombia",
    },
    "fierro": {
        "mapeo_auxiliares.json": "Mapeo de Auxiliares",
        "mapeo_descripciones.json": "Mapeo de Descripciones",
        "mapeo_tarjetas.json": "Mapeo de Tarjetas",
    },
    "zeus": {
        "auxiliares_zeus.json": "Auxiliares Zeus",
    },
}

# Nombres legibles para los procesos (titulos de las secciones del tree).
NOMBRES_PROCESO: dict[str, str] = {
    "comprobante": "Comprobante",
    "fierro": "Fierro",
    "zeus": "Zeus",
}


def _nombre_proceso(codigo: str) -> str:
    """Devuelve el nombre legible del proceso."""
    return NOMBRES_PROCESO.get(codigo, codigo.capitalize())


def _nombre_json_legible(proceso: str, archivo: str) -> str:
    """Devuelve el nombre legible del JSON para mostrar en la lista.

    Si no esta en el mapeo, formatea el nombre del archivo
    (ej: 'datos_extra.json' -> 'Datos Extra').
    """
    stem = Path(archivo).name
    if proceso in NOMBRES_JSON and stem in NOMBRES_JSON[proceso]:
        return NOMBRES_JSON[proceso][stem]
    return Path(archivo).stem.replace("_", " ").title()


# ====================================================================
# Pantalla principal
# ====================================================================


class PantallaDiccionarios(QWidget):
    """Editor inteligente de los JSONs del sistema."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = get_config()
        self._items: list[tuple[Path, str]] = []  # (ruta, proceso)
        self._ruta_actual: Path | None = None
        self._datos_originales: dict | None = None
        self._datos_actuales: dict | None = None
        self._tipo_actual: str = ""
        self._editor_widget: QWidget | None = None
        self._hay_cambios = False
        self._construir_ui()
        self._cargar_lista_jsons()

    def _construir_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Panel izquierdo: lista de JSONs ----------------------
        panel_izq = QWidget()
        izq_layout = QVBoxLayout(panel_izq)
        izq_layout.setContentsMargins(8, 8, 8, 8)
        izq_layout.addWidget(QLabel("<b>Archivos JSON</b>"))
        self._arbol = QTreeWidget()
        self._arbol.setHeaderHidden(True)
        self._arbol.setIndentation(16)
        self._arbol.setExpandsOnDoubleClick(True)
        self._arbol.itemSelectionChanged.connect(self._on_seleccionar_json)
        izq_layout.addWidget(self._arbol, 1)
        splitter.addWidget(panel_izq)

        # --- Panel derecho: editor -------------------------------
        panel_der = QWidget()
        der_layout = QVBoxLayout(panel_der)
        der_layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        self._lbl_titulo = QLabel("Selecciona un JSON de la izquierda")
        self._lbl_titulo.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(self._lbl_titulo)
        header.addStretch()
        der_layout.addLayout(header)

        self._lbl_ruta = QLabel("")
        self._lbl_ruta.setStyleSheet("color: #888; font-size: 11px;")
        der_layout.addWidget(self._lbl_ruta)

        # Contenedor del editor (cambia segun tipo).
        self._editor_container = QVBoxLayout()
        self._editor_container.setContentsMargins(0, 0, 0, 0)
        cont = QWidget()
        cont.setLayout(self._editor_container)
        der_layout.addWidget(cont, 1)

        # Footer con estado + botones.
        footer = QFrame()
        footer.setFrameShape(QFrame.Shape.StyledPanel)
        footer.setStyleSheet(
            "QFrame { background-color: #FAFAFA; border: 1px solid #E0E0E0;"
            " border-radius: 4px; padding: 8px; }"
        )
        flayout = QHBoxLayout(footer)
        self._lbl_cambios = QLabel("0 cambios sin guardar")
        self._lbl_cambios.setStyleSheet("font-weight: bold;")
        flayout.addWidget(self._lbl_cambios)
        flayout.addStretch()

        self.btn_agregar = QPushButton("+ Agregar")
        self.btn_agregar.clicked.connect(self._on_agregar)
        self.btn_agregar.setEnabled(False)
        flayout.addWidget(self.btn_agregar)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self._on_cancelar)
        self.btn_cancelar.setEnabled(False)
        flayout.addWidget(self.btn_cancelar)

        self.btn_guardar = QPushButton("Guardar cambios")
        self.btn_guardar.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white;"
            " padding: 6px 14px; font-weight: bold; }"
        )
        self.btn_guardar.clicked.connect(self._on_guardar)
        self.btn_guardar.setEnabled(False)
        flayout.addWidget(self.btn_guardar)

        der_layout.addWidget(footer)

        splitter.addWidget(panel_der)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 800])
        layout.addWidget(splitter)

    def _cargar_lista_jsons(self) -> None:
        """Descubre todos los JSONs bajo JSONS_DIR y los agrupa por proceso."""
        self._items.clear()
        self._arbol.clear()
        if not JSONS_DIR.exists():
            return

        # Agrupamos por proceso: {proceso_codigo: [(ruta, nombre_legible), ...]}
        grupos = {}
        for proc_dir in sorted(JSONS_DIR.iterdir()):
            if not proc_dir.is_dir():
                continue
            archivos = []
            for jf in sorted(proc_dir.glob("*.json")):
                nombre_legible = _nombre_json_legible(proc_dir.name, jf.name)
                archivos.append((jf, nombre_legible))
            if archivos:
                grupos[proc_dir.name] = archivos

        # Construimos el tree con una seccion por proceso.
        for proceso_codigo, archivos in grupos.items():
            seccion = QTreeWidgetItem([_nombre_proceso(proceso_codigo)])
            font = QFont()
            font.setBold(True)
            seccion.setFont(0, font)
            seccion.setBackground(0, QColor("#E3F2FD"))
            seccion.setFlags(seccion.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._arbol.addTopLevelItem(seccion)
            for ruta, nombre_legible in archivos:
                item = QTreeWidgetItem([nombre_legible])
                item.setData(0, Qt.ItemDataRole.UserRole, str(ruta))
                seccion.addChild(item)
                self._items.append((ruta, proceso_codigo))
            seccion.setExpanded(True)


    def _item_seleccionado(self) -> tuple[Path, str] | None:
        """Devuelve (ruta, proceso) del item hoja actualmente seleccionado.

        Si no hay item seleccionado, o es una seccion, devuelve None.
        """
        items = self._arbol.selectedItems()
        if not items:
            return None
        item = items[0]
        ruta_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta_str:
            return None
        ruta = Path(ruta_str)
        for p, proc in self._items:
            if p == ruta:
                return (p, proc)
        return None

    def _on_seleccionar_json(self) -> None:
        sel = self._item_seleccionado()
        if sel is None:
            return
        ruta, proceso = sel

        # Si hay cambios pendientes, preguntamos.
        if self._hay_cambios:
            resp = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "Hay cambios sin guardar en el JSON actual."
                " ¿Descartarlos y abrir otro?",
                QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if resp != QMessageBox.StandardButton.Discard:
                # Re-seleccionamos el item anterior.
                self._arbol.blockSignals(True)
                for i in range(self._arbol.topLevelItemCount()):
                    sec = self._arbol.topLevelItem(i)
                    for j in range(sec.childCount()):
                        child = sec.child(j)
                        if child.data(0, Qt.ItemDataRole.UserRole) == str(self._ruta_actual):
                            self._arbol.setCurrentItem(child)
                            break
                self._arbol.blockSignals(False)
                return

        self._cargar_json(ruta, proceso)

    def _cargar_json(self, ruta: Path, proceso: str) -> None:
        try:
            datos = leer_json(ruta)
        except Exception as e:
            QMessageBox.critical(
                self, "Error al leer", f"No se pudo leer {ruta}:\n{e}"
            )
            return
        self._ruta_actual = ruta
        self._datos_originales = copy.deepcopy(datos)
        self._datos_actuales = copy.deepcopy(datos)
        self._tipo_actual = detectar_tipo(datos)

        nombre_legible = _nombre_json_legible(proceso, ruta.name)
        self._lbl_titulo.setText(f"{_nombre_proceso(proceso)} / {nombre_legible}")
        self._lbl_ruta.setText(str(ruta))

        # Reconstruimos el editor.
        self._limpiar_editor()
        editor = self._crear_editor(self._tipo_actual, self._datos_actuales)
        self._editor_container.addWidget(editor)
        self._editor_widget = editor
        self.btn_agregar.setEnabled(True)
        self._actualizar_contador_cambios()

    def _limpiar_editor(self) -> None:
        # Quitamos todos los widgets del container.
        while self._editor_container.count():
            item = self._editor_container.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._editor_widget = None

    def _crear_editor(self, tipo: str, datos: dict) -> QWidget:
        if tipo == TIPO_A:
            return EditorTipoA(datos, self._on_cambio)
        if tipo == TIPO_B:
            return EditorTipoB(datos, self._on_cambio)
        if tipo == TIPO_C:
            return EditorTipoC(datos, self._on_cambio)
        if tipo == TIPO_D:
            return EditorTipoD(datos, self._on_cambio)
        return QLabel(f"Tipo desconocido: {tipo}")

    # -- Callbacks del editor ----------------------------------------

    def _on_cambio(self, datos_nuevos: dict) -> None:
        self._datos_actuales = datos_nuevos
        self._actualizar_contador_cambios()

    def _actualizar_contador_cambios(self) -> None:
        if self._datos_originales is None or self._datos_actuales is None:
            return
        cambios = _contar_diferencias(self._datos_originales, self._datos_actuales)
        self._hay_cambios = cambios > 0
        self._lbl_cambios.setText(
            f"{cambios} cambio(s) sin guardar"
            if cambios else "Sin cambios pendientes"
        )
        self.btn_cancelar.setEnabled(self._hay_cambios)
        self.btn_guardar.setEnabled(self._hay_cambios)
        # Color del contador.
        if cambios:
            self._lbl_cambios.setStyleSheet(
                "font-weight: bold; color: #E65100;"
            )
        else:
            self._lbl_cambios.setStyleSheet("font-weight: bold; color: #555;")

    # -- Botones globales --------------------------------------------

    def _on_agregar(self) -> None:
        if self._editor_widget is None:
            return
        self._editor_widget.agregar()
        # Forzamos recalculo.
        if hasattr(self._editor_widget, "datos"):
            self._datos_actuales = copy.deepcopy(self._editor_widget.datos)
            self._actualizar_contador_cambios()

    def _on_cancelar(self) -> None:
        if self._datos_originales is None:
            return
        resp = QMessageBox.question(
            self,
            "Cancelar cambios",
            "¿Descartar todos los cambios no guardados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        self._datos_actuales = copy.deepcopy(self._datos_originales)
        # Reconstruimos el editor con los datos originales.
        self._limpiar_editor()
        editor = self._crear_editor(
            self._tipo_actual, self._datos_actuales
        )
        self._editor_container.addWidget(editor)
        self._editor_widget = editor
        self._actualizar_contador_cambios()

    def _on_guardar(self) -> None:
        if self._ruta_actual is None or self._datos_actuales is None:
            return
        resp = QMessageBox.question(
            self,
            "Guardar cambios",
            f"Se hara un backup automatico de:\n{self._ruta_actual.name}\n\n"
            "¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        try:
            backup = escribir_json(self._ruta_actual, self._datos_actuales)
            cfg = get_config()
            sufijo = " [PRUEBA]" if cfg.modo_prueba else ""
            log().info(
                "Diccionarios: guardado %s (backup=%s)%s",
                self._ruta_actual.name,
                backup.name if backup else "ninguno",
                sufijo,
            )
            QMessageBox.information(
                self,
                "Guardado",
                f"Cambios guardados correctamente.\n\n"
                f"Backup: {backup.name if backup else '(no se creo)'}",
            )
            # Actualizamos el snapshot.
            self._datos_originales = copy.deepcopy(self._datos_actuales)
            self._actualizar_contador_cambios()
        except Exception as e:
            log().exception("Error al guardar JSON: %s", e)
            QMessageBox.critical(
                self, "Error al guardar", f"No se pudo guardar:\n{e}"
            )


# ====================================================================
# Contador de diferencias (recursivo)
# ====================================================================


def _contar_diferencias(a: Any, b: Any) -> int:
    """Cuenta cuantos valores difieren entre dos estructuras."""
    if isinstance(a, dict) and isinstance(b, dict):
        claves = set(a.keys()) | set(b.keys())
        total = 0
        for k in claves:
            if k not in a or k not in b:
                total += 1
            else:
                total += _contar_diferencias(a[k], b[k])
        return total
    if isinstance(a, list) and isinstance(b, list):
        total = abs(len(a) - len(b))
        for x, y in zip(a, b):
            total += _contar_diferencias(x, y)
        return total
    return 0 if a == b else 1


# ====================================================================
# Helpers de estilo para celdas modificadas/nuevas
# ====================================================================


def _estilo_celda(item: QTableWidgetItem | None, modificado: bool, nuevo: bool) -> None:
    if item is None:
        return
    if nuevo:
        item.setBackground(QColor(COLOR_FONDO_NUEVO))
        item.setToolTip("Nueva entrada (aun no guardada)")
    elif modificado:
        item.setBackground(QColor(COLOR_FONDO_MODIF))
        item.setToolTip("Valor modificado (aun no guardado)")
    else:
        item.setBackground(QColor("white"))
        item.setToolTip("")


# ====================================================================
# Editor Tipo A - plano clave/valor
# ====================================================================


class EditorTipoA(QWidget):
    """Editor para JSONs tipo A: {clave: valor} plano."""

    def __init__(self, datos: dict, on_change: Signal) -> None:
        super().__init__()
        self._on_change = on_change
        self.datos: dict = copy.deepcopy(datos)
        self._construir_ui()
        self._cargar_tabla()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Clave", "Valor", ""])
        self.tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.tabla.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.tabla.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tabla.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tabla)

    def _cargar_tabla(self) -> None:
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self.datos))
        for i, (k, v) in enumerate(self.datos.items()):
            item_k = QTableWidgetItem(str(k))
            item_v = QTableWidgetItem(str(v))
            item_k.setData(Qt.ItemDataRole.UserRole, k)
            self.tabla.setItem(i, 0, item_k)
            self.tabla.setItem(i, 1, item_v)
            self._agregar_boton_eliminar(i, k)
            _estilo_celda(item_k, False, False)
            _estilo_celda(item_v, False, False)
        self.tabla.blockSignals(False)

    def _agregar_boton_eliminar(self, fila: int, clave: str) -> None:
        btn = QToolButton()
        btn.setText("🗑")
        btn.setToolTip(f"Eliminar clave '{clave}'")
        btn.clicked.connect(lambda checked=False, c=clave: self._eliminar(c))
        # Lo metemos en un widget contenedor para centrarlo.
        cont = QWidget()
        lay = QHBoxLayout(cont)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch()
        lay.addWidget(btn)
        lay.addStretch()
        self.tabla.setCellWidget(fila, 2, cont)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        fila = item.row()
        col = item.column()
        if col not in (0, 1):
            return
        # Obtenemos clave y valor actuales de la fila.
        k_item = self.tabla.item(fila, 0)
        v_item = self.tabla.item(fila, 1)
        if k_item is None or not k_item.text().strip():
            return
        nueva_clave = k_item.text().strip()
        nuevo_valor = v_item.text() if v_item else ""
        # Reconstruimos self.datos preservando el orden visible.
        # (leemos en orden de filas)
        self.tabla.blockSignals(True)
        nuevos: dict[str, str] = {}
        claves_vistas: set[str] = set()
        for i in range(self.tabla.rowCount()):
            ki = self.tabla.item(i, 0)
            vi = self.tabla.item(i, 1)
            if ki is None or not ki.text().strip():
                continue
            c = ki.text().strip()
            if c in claves_vistas:
                # Duplicado: lo saltamos para no perder datos.
                continue
            claves_vistas.add(c)
            v = vi.text() if vi else ""
            nuevos[c] = v
            # Marcar como modificado.
            old_key = ki.data(Qt.ItemDataRole.UserRole)
            es_nuevo = old_key not in self.datos
            es_modif = (
                not es_nuevo
                and (
                    old_key != c
                    or str(self.datos.get(old_key, "")) != v
                )
            )
            _estilo_celda(ki, es_modif, es_nuevo)
            _estilo_celda(vi, es_modif, es_nuevo)
        self.datos = nuevos
        self.tabla.blockSignals(False)
        self._on_change(self.datos)

    def _eliminar(self, clave: str) -> None:
        if clave in self.datos:
            del self.datos[clave]
            self._cargar_tabla()
            self._on_change(self.datos)

    def agregar(self) -> None:
        clave, ok = QInputDialog.getText(
            self, "Nueva clave", "Nombre de la nueva clave:"
        )
        if not ok or not clave.strip():
            return
        clave = clave.strip()
        if clave in self.datos:
            QMessageBox.warning(
                self, "Clave duplicada", f"'{clave}' ya existe."
            )
            return
        valor, ok = QInputDialog.getText(
            self, "Valor", f"Valor para '{clave}':"
        )
        if not ok:
            return
        self.datos[clave] = valor
        self._cargar_tabla()
        self._on_change(self.datos)


# ====================================================================
# Editor Tipo D - lista de pares
# ====================================================================


class EditorTipoD(QWidget):
    """Editor para JSONs tipo D: {clave_unica: [[patron, reemplazo], ...]}."""

    def __init__(self, datos: dict, on_change: Signal) -> None:
        super().__init__()
        self._on_change = on_change
        # Los datos tipo D tienen UNA sola clave; sacamos la lista de ahi.
        self._clave_envoltorio = next(iter(datos.keys())) if datos else "items"
        self.datos: list[list[str]] = list(datos.get(self._clave_envoltorio, []))
        self._construir_ui()
        self._cargar_tabla()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)

        layout.addWidget(QLabel(
            f"<i>Estructura: <code>{self._clave_envoltorio}: [[patron, reemplazo], ...]</code></i>"
        ))

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Patron", "Reemplazo", ""])
        self.tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.tabla.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.tabla.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tabla.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tabla)

    def _cargar_tabla(self) -> None:
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self.datos))
        for i, par in enumerate(self.datos):
            item_a = QTableWidgetItem(str(par[0]) if len(par) > 0 else "")
            item_b = QTableWidgetItem(str(par[1]) if len(par) > 1 else "")
            item_a.setData(Qt.ItemDataRole.UserRole, par[0] if par else "")
            self.tabla.setItem(i, 0, item_a)
            self.tabla.setItem(i, 1, item_b)
            self._agregar_boton_eliminar(i)
            _estilo_celda(item_a, False, False)
            _estilo_celda(item_b, False, False)
        self.tabla.blockSignals(False)

    def _agregar_boton_eliminar(self, fila: int) -> None:
        btn = QToolButton()
        btn.setText("🗑")
        btn.setToolTip("Eliminar este par")
        btn.clicked.connect(lambda checked=False, f=fila: self._eliminar(f))
        cont = QWidget()
        lay = QHBoxLayout(cont)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch()
        lay.addWidget(btn)
        lay.addStretch()
        self.tabla.setCellWidget(fila, 2, cont)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        self.tabla.blockSignals(True)
        nuevos: list[list[str]] = []
        for i in range(self.tabla.rowCount()):
            a = self.tabla.item(i, 0)
            b = self.tabla.item(i, 1)
            a_txt = a.text() if a else ""
            b_txt = b.text() if b else ""
            nuevos.append([a_txt, b_txt])
            old_a = a.data(Qt.ItemDataRole.UserRole) if a else ""
            old_b = self.datos[i][1] if i < len(self.datos) and len(self.datos[i]) > 1 else ""
            es_nuevo = i >= len(self.datos)
            es_modif = not es_nuevo and (old_a != a_txt or old_b != b_txt)
            _estilo_celda(a, es_modif, es_nuevo)
            _estilo_celda(b, es_modif, es_nuevo)
        self.datos = nuevos
        self.tabla.blockSignals(False)
        self._on_change({self._clave_envoltorio: self.datos})

    def _eliminar(self, fila: int) -> None:
        if 0 <= fila < len(self.datos):
            del self.datos[fila]
            self._cargar_tabla()
            self._on_change({self._clave_envoltorio: self.datos})

    def agregar(self) -> None:
        # Pedimos patron y reemplazo en secuencia.
        patron, ok = QInputDialog.getText(
            self, "Nuevo par", "Patron (regex o texto):"
        )
        if not ok or not patron.strip():
            return
        reemplazo, ok = QInputDialog.getText(
            self, "Nuevo par", f"Reemplazo para '{patron}':"
        )
        if not ok:
            return
        self.datos.append([patron.strip(), reemplazo])
        self._cargar_tabla()
        self._on_change({self._clave_envoltorio: self.datos})


# ====================================================================
# Editor Tipo B - secciones con sub-objetos
# ====================================================================


class EditorTipoB(QWidget):
    """Editor para JSONs tipo B: {seccion: {clave: {campo: valor, ...}}}."""

    def __init__(self, datos: dict, on_change: Signal) -> None:
        super().__init__()
        self._on_change = on_change
        self.datos: dict = copy.deepcopy(datos)
        # Inferimos el esquema a partir del primer sub-objeto del primer item.
        self._campos: list[str] = []
        for sec, contenido in self.datos.items():
            if isinstance(contenido, dict):
                for v in contenido.values():
                    if isinstance(v, dict) and v:
                        self._campos = list(v.keys())
                        break
            if self._campos:
                break
        self._construir_ui()
        self._cargar_arbol()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)

        self._arbol = QTreeWidget()
        self._arbol.setColumnCount(max(2, len(self._campos) + 1))
        headers = ["Clave"] + self._campos + [""]
        self._arbol.setHeaderLabels(headers)
        self._arbol.setRootIsDecorated(True)
        self._arbol.setAlternatingRowColors(True)
        self._arbol.itemChanged.connect(self._on_item_changed)
        # Header resize.
        hdr = self._arbol.header()
        for i in range(self._arbol.columnCount()):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._arbol)

    def _cargar_arbol(self) -> None:
        self._arbol.blockSignals(True)
        self._arbol.clear()
        for sec, contenido in self.datos.items():
            sec_item = QTreeWidgetItem([sec])
            sec_item.setData(0, Qt.ItemDataRole.UserRole, ("seccion", sec))
            sec_item.setBackground(0, QColor("#E3F2FD"))
            self._arbol.addTopLevelItem(sec_item)
            if isinstance(contenido, dict):
                for k, v in contenido.items():
                    fields = [
                        k,
                    ] + [str(v.get(c, "")) for c in self._campos]
                    child = QTreeWidgetItem(fields)
                    child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable)
                    child.setData(0, Qt.ItemDataRole.UserRole, ("item", sec, k))
                    # Marcamos con fondo los datos originales.
                    sec_item.addChild(child)
            sec_item.setExpanded(True)
        self._arbol.blockSignals(False)

    def _on_item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        if col == 0:
            return  # la clave no se edita directamente
        # Determinamos que nodo se edito.
        info = item.data(0, Qt.ItemDataRole.UserRole)
        if not info or info[0] != "item":
            return
        _, sec, k = info
        if sec not in self.datos or k not in self.datos[sec]:
            return
        campo = self._campos[col - 1]
        self.datos[sec][k][campo] = item.text(col)
        item.setBackground(col, QColor(COLOR_FONDO_MODIF))
        self._on_change(self.datos)

    def agregar(self) -> None:
        nombre_seccion, ok = QInputDialog.getItem(
            self,
            "Agregar entrada",
            "Seccion:",
            list(self.datos.keys()) + ["<nueva>"],
            0,
            editable=False,
        )
        if not ok:
            return

        if nombre_seccion == "<nueva>":
            nombre_seccion, ok = QInputDialog.getText(
                self, "Nueva seccion", "Nombre de la nueva seccion:"
            )
            if not ok or not nombre_seccion.strip():
                return
            nombre_seccion = nombre_seccion.strip()
            if nombre_seccion in self.datos:
                QMessageBox.warning(
                    self, "Duplicado", f"La seccion '{nombre_seccion}' ya existe."
                )
                return
            # Creamos la seccion con un item vacio para definir el esquema.
            self.datos[nombre_seccion] = {}
            self._crear_item_en_seccion(nombre_seccion)
        else:
            self._crear_item_en_seccion(nombre_seccion)
        self._cargar_arbol()
        self._on_change(self.datos)

    def _crear_item_en_seccion(self, seccion: str) -> None:
        clave, ok = QInputDialog.getText(
            self, "Nueva clave", f"Clave dentro de '{seccion}':"
        )
        if not ok or not clave.strip():
            return
        clave = clave.strip()
        if clave in self.datos.get(seccion, {}):
            QMessageBox.warning(
                self, "Duplicado", f"La clave '{clave}' ya existe en '{seccion}'."
            )
            return
        # Pedimos cada campo en un mini-dialogo.
        valores: dict[str, str] = {}
        for campo in self._campos:
            v, ok = QInputDialog.getText(
                self, f"Valor para {campo}", f"{campo} de '{clave}':"
            )
            if not ok:
                return
            valores[campo] = v
        self.datos[seccion][clave] = valores


# ====================================================================
# Editor Tipo C - secciones con valores string o list[string]
# ====================================================================


class EditorTipoC(QWidget):
    """Editor para JSONs tipo C: {seccion: {clave: string | list[string]}}."""

    def __init__(self, datos: dict, on_change: Signal) -> None:
        super().__init__()
        self._on_change = on_change
        self.datos: dict = copy.deepcopy(datos)
        self._construir_ui()
        self._cargar_arbol()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        self._arbol = QTreeWidget()
        self._arbol.setColumnCount(2)
        self._arbol.setHeaderLabels(["Clave", "Valor(es)"])
        self._arbol.itemChanged.connect(self._on_item_changed)
        hdr = self._arbol.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._arbol)

    def _cargar_arbol(self) -> None:
        self._arbol.blockSignals(True)
        self._arbol.clear()
        for sec, contenido in self.datos.items():
            sec_item = QTreeWidgetItem([sec])
            sec_item.setBackground(0, QColor("#E3F2FD"))
            sec_item.setData(0, Qt.ItemDataRole.UserRole, ("seccion", sec))
            self._arbol.addTopLevelItem(sec_item)
            if isinstance(contenido, dict):
                for k, v in contenido.items():
                    if isinstance(v, list):
                        valor_str = " | ".join(str(x) for x in v)
                    else:
                        valor_str = str(v)
                    child = QTreeWidgetItem([k, valor_str])
                    child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable)
                    child.setData(0, Qt.ItemDataRole.UserRole, ("item", sec, k))
                    sec_item.addChild(child)
            sec_item.setExpanded(True)
        self._arbol.blockSignals(False)

    def _on_item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        info = item.data(0, Qt.ItemDataRole.UserRole)
        if not info or info[0] != "item" or col != 1:
            return
        _, sec, k = info
        if sec not in self.datos or k not in self.datos[sec]:
            return
        texto = item.text(1)
        # Si contiene " | " lo tratamos como lista; si no, como string.
        if " | " in texto:
            self.datos[sec][k] = [s.strip() for s in texto.split("|")]
        else:
            self.datos[sec][k] = texto.strip()
        item.setBackground(1, QColor(COLOR_FONDO_MODIF))
        self._on_change(self.datos)

    def agregar(self) -> None:
        nombre_seccion, ok = QInputDialog.getItem(
            self,
            "Agregar entrada",
            "Seccion:",
            list(self.datos.keys()) + ["<nueva>"],
            0,
            editable=False,
        )
        if not ok:
            return

        if nombre_seccion == "<nueva>":
            nombre_seccion, ok = QInputDialog.getText(
                self, "Nueva seccion", "Nombre de la nueva seccion:"
            )
            if not ok or not nombre_seccion.strip():
                return
            nombre_seccion = nombre_seccion.strip()
            if nombre_seccion in self.datos:
                QMessageBox.warning(
                    self, "Duplicado", f"La seccion '{nombre_seccion}' ya existe."
                )
                return
            self.datos[nombre_seccion] = {}

        clave, ok = QInputDialog.getText(
            self, "Nueva clave", f"Clave dentro de '{nombre_seccion}':"
        )
        if not ok or not clave.strip():
            return
        clave = clave.strip()
        if clave in self.datos.get(nombre_seccion, {}):
            QMessageBox.warning(
                self, "Duplicado", f"La clave '{clave}' ya existe."
            )
            return
        # string o lista?
        tipo, ok = QInputDialog.getItem(
            self, "Tipo de valor", "¿El valor es:",
            ["Un solo texto", "Una lista (separar con |)"],
            0, False,
        )
        if not ok:
            return
        if tipo.startswith("Un solo"):
            valor, ok = QInputDialog.getText(
                self, "Valor", f"Valor de '{clave}':"
            )
            if not ok:
                return
            self.datos[nombre_seccion][clave] = valor
        else:
            valor, ok = QInputDialog.getText(
                self, "Valor", f"Lista de valores para '{clave}' (separar con |):"
            )
            if not ok:
                return
            self.datos[nombre_seccion][clave] = [s.strip() for s in valor.split("|")]
        self._cargar_arbol()
        self._on_change(self.datos)