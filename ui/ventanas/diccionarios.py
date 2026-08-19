"""Pantalla Diccionarios: editor visual tipo tabla de Excel para los JSONs del sistema."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import DATA_DIR, JSONS_DIR

# Estructura organizada de los JSONs del sistema
DICCIONARIOS_SISTEMA: dict[str, list[tuple[str, str]]] = {
    "Comprobante": [
        ("Códigos de Conceptos", "comprobante/codigos_conceptos.json"),
        ("Códigos Contables", "comprobante/codigos_contables.json"),
        ("FOAPAL", "comprobante/foapal.json"),
        ("NIT Bancolombia", "comprobante/nit_bancolombia.json"),
        ("Códigos Ignorados", "comprobante/codigos_ignorados.json"),
    ],
    "Fierro": [
        ("Mapeo de Auxiliares", "fierro/mapeo_auxiliares.json"),
        ("Mapeo de Descripciones", "fierro/mapeo_descripciones.json"),
        ("Mapeo de Tarjetas", "fierro/mapeo_tarjetas.json"),
    ],
    "Zeus": [
        ("Auxiliares Zeus", "zeus/auxiliares_zeus.json"),
    ],
}


class TablaExcel(QTableWidget):
    """Tabla estilizada con apariencia de hoja de cálculo / Excel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.verticalHeader().setDefaultSectionSize(32)
        self.verticalHeader().setMinimumSectionSize(28)

        self.setStyleSheet(
            """
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                gridline-color: #E2E8F0;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                color: #0F172A;
                font-size: 13px;
                selection-background-color: #DBEAFE;
                selection-color: #1E3A8A;
            }
            QHeaderView::section:horizontal {
                background-color: #F1F5F9;
                color: #334155;
                font-weight: 700;
                font-size: 12px;
                padding: 6px 10px;
                border: none;
                border-right: 1px solid #E2E8F0;
                border-bottom: 2px solid #CBD5E1;
            }
            QHeaderView::section:vertical {
                background-color: #F8FAFC;
                color: #64748B;
                font-size: 11px;
                font-weight: 600;
                padding: 0 6px;
                border: none;
                border-right: 1px solid #E2E8F0;
                border-bottom: 1px solid #E2E8F0;
            }
            QTableWidget::item {
                padding: 4px 8px;
                border: none;
            }
            QTableWidget::item:focus {
                background-color: #EFF6FF;
                border: 2px solid #2563EB;
            }
            """
        )


class VistaDiccionarios(QWidget):
    """Pantalla de Diccionarios con sub-sidebar lateral y editor tabular tipo Excel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._archivo_activo_rel = "comprobante/codigos_conceptos.json"
        self._titulo_activo = "Códigos de Conceptos"
        self._botones_archivos: dict[str, QPushButton] = {}
        
        # Gestión de categorías para JSONs anidados (FOAPAL y Códigos Conceptos)
        self._categoria_activa: str = ""
        self._cache_categorias: dict[str, list[list[str]]] = {}
        self._botones_categorias: dict[str, QPushButton] = {}

        self._construir_ui()
        self._seleccionar_archivo("comprobante/codigos_conceptos.json", "Códigos de Conceptos")

    def _construir_ui(self) -> None:
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # 1. Sub-sidebar lateral izquierdo (Listado de diccionarios)
        panel_lateral = self._crear_panel_lateral()
        layout_principal.addWidget(panel_lateral)

        # 2. Área principal de trabajo (Tabla Excel)
        panel_principal = self._crear_panel_principal()
        layout_principal.addWidget(panel_principal, 1)

    def _crear_panel_lateral(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("sub_sidebar")
        frame.setFixedWidth(230)
        frame.setStyleSheet(
            """
            QFrame#sub_sidebar {
                background-color: #FFFFFF;
                border-right: 1px solid #E2E8F0;
            }
            """
        )

        scroll = QScrollArea(frame)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        contenedor_scroll = QWidget()
        layout_scroll = QVBoxLayout(contenedor_scroll)
        layout_scroll.setContentsMargins(16, 20, 16, 20)
        layout_scroll.setSpacing(16)

        for grupo, archivos in DICCIONARIOS_SISTEMA.items():
            lbl_grupo = QLabel(grupo.upper())
            lbl_grupo.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")
            layout_scroll.addWidget(lbl_grupo)

            for nombre_legible, ruta_rel in archivos:
                btn = QPushButton(nombre_legible)
                btn.setObjectName("btn_json_selector")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(
                    """
                    QPushButton#btn_json_selector {
                        text-align: left;
                        background-color: transparent;
                        color: #475569;
                        font-size: 13px;
                        font-weight: 600;
                        border: none;
                        border-radius: 8px;
                        padding: 8px 12px;
                    }
                    QPushButton#btn_json_selector:hover {
                        background-color: #F1F5F9;
                        color: #0F172A;
                    }
                    QPushButton#btn_json_selector[active="true"] {
                        background-color: #EFF6FF;
                        color: #2563EB;
                        font-weight: 700;
                    }
                    """
                )
                btn.clicked.connect(
                    lambda _, r=ruta_rel, n=nombre_legible: self._seleccionar_archivo(r, n)
                )
                self._botones_archivos[ruta_rel] = btn
                layout_scroll.addWidget(btn)

        layout_scroll.addStretch(1)
        scroll.setWidget(contenedor_scroll)

        layout_lateral = QVBoxLayout(frame)
        layout_lateral.setContentsMargins(0, 0, 0, 0)
        layout_lateral.addWidget(scroll)

        return frame

    def _crear_panel_principal(self) -> QWidget:
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        # Cabecera superior con título y buscador
        cabecera_top = QHBoxLayout()
        cabecera_top.setSpacing(16)

        box_titulos = QVBoxLayout()
        box_titulos.setSpacing(2)
        self._lbl_titulo = QLabel("Códigos de Conceptos")
        self._lbl_titulo.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        self._lbl_ruta = QLabel("jsons/comprobante/codigos_conceptos.json")
        self._lbl_ruta.setStyleSheet("font-size: 12px; color: #64748B; font-family: monospace;")
        box_titulos.addWidget(self._lbl_titulo)
        box_titulos.addWidget(self._lbl_ruta)
        cabecera_top.addLayout(box_titulos)

        cabecera_top.addStretch(1)

        # Barra de búsqueda / filtro estilo Excel
        self._txt_filtro = QLineEdit()
        self._txt_filtro.setPlaceholderText("🔍 Filtrar registros...")
        self._txt_filtro.setFixedWidth(220)
        self._txt_filtro.setStyleSheet(
            """
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
            """
        )
        self._txt_filtro.textChanged.connect(self._filtrar_tabla)
        cabecera_top.addWidget(self._txt_filtro)

        layout.addLayout(cabecera_top)

        # Barra de categorías (pestañas / pills) para FOAPAL y Códigos Conceptos
        self._frame_categorias = QFrame()
        self._frame_categorias.setStyleSheet("background: transparent; border: none;")
        self._layout_categorias = QHBoxLayout(self._frame_categorias)
        self._layout_categorias.setContentsMargins(0, 4, 0, 4)
        self._layout_categorias.setSpacing(8)
        self._layout_categorias.addStretch(1)
        layout.addWidget(self._frame_categorias)

        # Tabla Excel
        self._tabla = TablaExcel()
        layout.addWidget(self._tabla, 1)

        # Fila de Botones de Acción
        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(10)

        # Botón + Agregar fila
        self._btn_agregar_fila = QPushButton("+ Agregar fila")
        self._btn_agregar_fila.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_agregar_fila.setStyleSheet(
            """
            QPushButton {
                background-color: #FFFFFF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
                border-color: #2563EB;
            }
            """
        )
        self._btn_agregar_fila.clicked.connect(self._agregar_fila)
        fila_acciones.addWidget(self._btn_agregar_fila)

        # Botón ✕ Eliminar fila
        self._btn_eliminar_fila = QPushButton("✕ Eliminar fila")
        self._btn_eliminar_fila.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_eliminar_fila.setStyleSheet(
            """
            QPushButton {
                background-color: #FFFFFF;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                border-color: #DC2626;
            }
            """
        )
        self._btn_eliminar_fila.clicked.connect(self._eliminar_fila)
        fila_acciones.addWidget(self._btn_eliminar_fila)

        self._lbl_conteo_filas = QLabel("0 filas")
        self._lbl_conteo_filas.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500; margin-left: 8px;")
        fila_acciones.addWidget(self._lbl_conteo_filas)

        fila_acciones.addStretch(1)

        # Botón Descartar cambios
        self._btn_descartar = QPushButton("Descartar cambios")
        self._btn_descartar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_descartar.setStyleSheet(
            """
            QPushButton {
                background-color: #FEE2E2;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
                border-color: #B91C1C;
            }
            """
        )
        self._btn_descartar.clicked.connect(self._recargar_archivo)
        fila_acciones.addWidget(self._btn_descartar)

        # Botón Restaurar último backup
        self._btn_restaurar_backup = QPushButton("Restaurar último backup")
        self._btn_restaurar_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_restaurar_backup.setStyleSheet(
            """
            QPushButton {
                background-color: #FEF3C7;
                color: #B45309;
                border: 1px solid #FDE68A;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F59E0B;
                color: #FFFFFF;
                border-color: #D97706;
            }
            """
        )
        self._btn_restaurar_backup.clicked.connect(self._restaurar_ultimo_backup)
        fila_acciones.addWidget(self._btn_restaurar_backup)

        # Botón Guardar (Azul primario)
        self._btn_guardar = QPushButton("Guardar cambios")
        self._btn_guardar.setObjectName("primary")
        self._btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_guardar.clicked.connect(self._guardar_archivo)
        fila_acciones.addWidget(self._btn_guardar)

        layout.addLayout(fila_acciones)

        # Panel de Notificación / Feedback inferior
        self._panel_feedback = QFrame()
        self._panel_feedback.setObjectName("panel_feedback")
        self._panel_feedback.setStyleSheet(
            """
            QFrame#panel_feedback {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                min-height: 44px;
                max-height: 44px;
            }
            """
        )
        layout_fb = QHBoxLayout(self._panel_feedback)
        layout_fb.setContentsMargins(16, 8, 16, 8)
        self._lbl_feedback = QLabel("Edita las celdas directamente en la tabla y haz clic en 'Guardar cambios'.")
        self._lbl_feedback.setStyleSheet("font-size: 13px; color: #64748B;")
        layout_fb.addWidget(self._lbl_feedback)
        layout.addWidget(self._panel_feedback)

        return contenedor

    def _seleccionar_archivo(self, ruta_rel: str, nombre_legible: str) -> None:
        self._archivo_activo_rel = ruta_rel
        self._titulo_activo = nombre_legible

        # Actualizar resaltado en sub-sidebar
        for r, btn in self._botones_archivos.items():
            activo = (r == ruta_rel)
            btn.setProperty("active", "true" if activo else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._lbl_titulo.setText(nombre_legible)
        self._lbl_ruta.setText(f"jsons/{ruta_rel}")
        self._txt_filtro.clear()
        self._recargar_archivo()

    # --- Carga y Conversión ---

    def _recargar_archivo(self) -> None:
        ruta_absoluta = JSONS_DIR / self._archivo_activo_rel
        if not ruta_absoluta.exists():
            self._tabla.setRowCount(0)
            self._tabla.setColumnCount(0)
            self._frame_categorias.hide()
            self._mostrar_feedback("El archivo aún no existe en disco.", es_error=True)
            return

        try:
            with open(ruta_absoluta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            self._cargar_datos_en_tabla(datos)
            n_filas = self._tabla.rowCount()
            self._lbl_conteo_filas.setText(f"{n_filas} filas")
            self._mostrar_feedback(f"Archivo cargado: {n_filas} registros en '{ruta_absoluta.name}'.", es_error=False)
        except Exception as e:
            self._mostrar_feedback(f"Error al leer el archivo: {e}", es_error=True)

    def _cargar_datos_en_tabla(self, datos: Any) -> None:
        rel = self._archivo_activo_rel.lower()
        self._cache_categorias.clear()
        self._limpiar_barra_categorias()

        # 1. FOAPAL (Separado en pestañas: Créditos / Débitos)
        if "foapal.json" in rel:
            columnas = ["Código", "Fondo", "Organización", "Cuenta", "Programa", "D/C"]
            self._tabla.setColumnCount(len(columnas))
            self._tabla.setHorizontalHeaderLabels(columnas)

            categorias = ["creditos", "debitos"]
            for cat in categorias:
                filas_cat = []
                sub_dict = datos.get(cat, {}) if isinstance(datos, dict) else {}
                if isinstance(sub_dict, dict):
                    for cod, obj in sub_dict.items():
                        if isinstance(obj, dict):
                            filas_cat.append([
                                str(cod),
                                str(obj.get("Fondo", "")),
                                str(obj.get("Organizacion", "")),
                                str(obj.get("Cuenta", "")),
                                str(obj.get("Programa", "")),
                                str(obj.get("D/C", "")),
                            ])
                self._cache_categorias[cat] = filas_cat

            self._construir_barra_categorias({"creditos": "Créditos", "debitos": "Débitos"})
            self._cambiar_categoria("creditos")

        # 2. Códigos de Conceptos (Separado en pestañas: Intereses / Gastos bancarios)
        elif "codigos_conceptos.json" in rel:
            columnas = ["Código Concepto", "Descripción / Concepto"]
            self._tabla.setColumnCount(len(columnas))
            self._tabla.setHorizontalHeaderLabels(columnas)

            cat_map = {}
            if isinstance(datos, dict):
                for cat, items in datos.items():
                    cat_map[cat] = cat
                    filas_cat = []
                    if isinstance(items, dict):
                        for cod, desc in items.items():
                            desc_str = ", ".join(desc) if isinstance(desc, list) else str(desc)
                            filas_cat.append([str(cod), desc_str])
                    self._cache_categorias[cat] = filas_cat

            if not cat_map:
                cat_map = {"Intereses": "Intereses", "Gastos bancarios": "Gastos bancarios"}
                self._cache_categorias = {"Intereses": [], "Gastos bancarios": []}

            primera_cat = list(cat_map.keys())[0]
            self._construir_barra_categorias(cat_map)
            self._cambiar_categoria(primera_cat)

        # 3. Archivos sin categorías (Mapeos planos)
        else:
            self._frame_categorias.hide()
            self._tabla.setRowCount(0)

            if "codigos_ignorados.json" in rel:
                columnas = ["Código Ignorado", "Descripción / Concepto"]
                self._tabla.setColumnCount(len(columnas))
                self._tabla.setHorizontalHeaderLabels(columnas)
                if isinstance(datos, dict):
                    items = datos.get("codigos", {})
                    if isinstance(items, dict):
                        for cod, desc in items.items():
                            self._insertar_fila_valores([str(cod), str(desc)])
                    elif isinstance(items, list):
                        for cod in items:
                            self._insertar_fila_valores([str(cod), ""])
                else:
                    for cod in (datos if isinstance(datos, list) else []):
                        self._insertar_fila_valores([str(cod), ""])

            elif "mapeo_tarjetas.json" in rel:
                columnas = ["Patrón Expresión Regular", "Descripción Reemplazo"]
                self._tabla.setColumnCount(len(columnas))
                self._tabla.setHorizontalHeaderLabels(columnas)
                lista = datos.get("tarjetas", []) if isinstance(datos, dict) else (datos if isinstance(datos, list) else [])
                for item in lista:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        self._insertar_fila_valores([str(item[0]), str(item[1])])

            elif "auxiliares_zeus.json" in rel:
                columnas = ["Patrón Expresión Regular", "Auxiliar Destino Zeus"]
                self._tabla.setColumnCount(len(columnas))
                self._tabla.setHorizontalHeaderLabels(columnas)
                lista = datos.get("auxiliares", []) if isinstance(datos, dict) else (datos if isinstance(datos, list) else [])
                for item in lista:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        self._insertar_fila_valores([str(item[0]), str(item[1])])

            else:
                if "codigos_contables.json" in rel:
                    columnas = ["Cuenta Bancaria", "Código Contable"]
                elif "nit_bancolombia.json" in rel:
                    columnas = ["Cuenta / Código", "NIT Bancolombia"]
                elif "mapeo_auxiliares.json" in rel:
                    columnas = ["Auxiliar Origen", "Auxiliar Destino"]
                elif "mapeo_descripciones.json" in rel:
                    columnas = ["Cuenta Auxiliar", "Descripción Personalizada"]
                else:
                    columnas = ["Clave", "Valor"]

                self._tabla.setColumnCount(len(columnas))
                self._tabla.setHorizontalHeaderLabels(columnas)
                if isinstance(datos, dict):
                    for k, v in datos.items():
                        self._insertar_fila_valores([str(k), str(v)])

    # --- Barra de Categorías ---

    def _limpiar_barra_categorias(self) -> None:
        self._botones_categorias.clear()
        while self._layout_categorias.count() > 0:
            item = self._layout_categorias.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._layout_categorias.addStretch(1)

    def _construir_barra_categorias(self, categorias: dict[str, str]) -> None:
        self._limpiar_barra_categorias()
        self._frame_categorias.show()

        # Re-insertar antes del stretch
        count = 0
        for key, label in categorias.items():
            btn = QPushButton(label)
            btn.setObjectName("btn_cat_pill")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                """
                QPushButton#btn_cat_pill {
                    background-color: #F1F5F9;
                    color: #475569;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton#btn_cat_pill:hover {
                    background-color: #E2E8F0;
                    color: #0F172A;
                }
                QPushButton#btn_cat_pill[active="true"] {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    border-color: #1D4ED8;
                }
                """
            )
            btn.clicked.connect(lambda _, k=key: self._cambiar_categoria(k))
            self._botones_categorias[key] = btn
            self._layout_categorias.insertWidget(count, btn)
            count += 1

    def _cambiar_categoria(self, nueva_cat: str) -> None:
        # 1. Guardar contenido actual en la categoría que dejamos
        if self._categoria_activa and self._categoria_activa in self._cache_categorias:
            self._cache_categorias[self._categoria_activa] = self._extraer_filas_actuales_tabla()

        self._categoria_activa = nueva_cat

        # 2. Actualizar botones visualmente
        for k, btn in self._botones_categorias.items():
            activo = (k == nueva_cat)
            btn.setProperty("active", "true" if activo else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # 3. Cargar filas de la nueva categoría en la tabla
        self._tabla.setRowCount(0)
        filas = self._cache_categorias.get(nueva_cat, [])
        for f in filas:
            self._insertar_fila_valores(f)

        n_filas = len(filas)
        self._lbl_conteo_filas.setText(f"{n_filas} filas")
        self._txt_filtro.clear()

    def _extraer_filas_actuales_tabla(self) -> list[list[str]]:
        filas = []
        n_filas = self._tabla.rowCount()
        n_cols = self._tabla.columnCount()
        for r in range(n_filas):
            fila = [self._obtener_texto_celda(r, c) for c in range(n_cols)]
            if any(cell.strip() for cell in fila):
                filas.append(fila)
        return filas

    def _insertar_fila_valores(self, valores: list[str]) -> None:
        fila = self._tabla.rowCount()
        self._tabla.insertRow(fila)
        for col, val in enumerate(valores):
            item = QTableWidgetItem(val)
            self._tabla.setItem(fila, col, item)

    def _serializar_tabla_a_json(self) -> Any:
        rel = self._archivo_activo_rel.lower()

        # Si usa categorías, sincronizar la categoría activa en caché primero
        if self._categoria_activa and self._categoria_activa in self._cache_categorias:
            self._cache_categorias[self._categoria_activa] = self._extraer_filas_actuales_tabla()

        # 1. FOAPAL
        if "foapal.json" in rel:
            resultado_foapal: dict[str, dict[str, dict[str, str]]] = {}
            for cat, filas in self._cache_categorias.items():
                resultado_foapal[cat] = {}
                for r in filas:
                    cod = r[0].strip()
                    if not cod:
                        continue
                    resultado_foapal[cat][cod] = {
                        "Fondo": r[1].strip() if len(r) > 1 else "",
                        "Organizacion": r[2].strip() if len(r) > 2 else "",
                        "Cuenta": r[3].strip() if len(r) > 3 else "",
                        "Programa": r[4].strip() if len(r) > 4 else "",
                        "D/C": r[5].strip() if len(r) > 5 else "",
                    }
            return resultado_foapal

        # 2. Códigos de Conceptos
        elif "codigos_conceptos.json" in rel:
            resultado_conceptos: dict[str, dict[str, Any]] = {}
            for cat, filas in self._cache_categorias.items():
                resultado_conceptos[cat] = {}
                for r in filas:
                    cod = r[0].strip()
                    desc = r[1].strip() if len(r) > 1 else ""
                    if not cod:
                        continue
                    if cat.lower().startswith("gastos"):
                        resultado_conceptos[cat][cod] = [d.strip() for d in desc.split(",") if d.strip()]
                    else:
                        resultado_conceptos[cat][cod] = desc
            return resultado_conceptos

        # 3. Códigos Ignorados
        elif "codigos_ignorados.json" in rel:
            codigos: dict[str, str] = {}
            for r in range(self._tabla.rowCount()):
                cod = self._obtener_texto_celda(r, 0).strip()
                desc = self._obtener_texto_celda(r, 1).strip()
                if cod:
                    codigos[cod] = desc
            return {"codigos": codigos}

        # 4. Mapeo de Tarjetas
        elif "mapeo_tarjetas.json" in rel:
            tarjetas = []
            for r in range(self._tabla.rowCount()):
                patron = self._obtener_texto_celda(r, 0).strip()
                desc = self._obtener_texto_celda(r, 1).strip()
                if patron:
                    tarjetas.append([patron, desc])
            return {"tarjetas": tarjetas}

        # 5. Auxiliares Zeus
        elif "auxiliares_zeus.json" in rel:
            auxiliares = []
            for r in range(self._tabla.rowCount()):
                patron = self._obtener_texto_celda(r, 0).strip()
                dest = self._obtener_texto_celda(r, 1).strip()
                if patron:
                    auxiliares.append([patron, dest])
            return {"auxiliares": auxiliares}

        # 6. Mappings 1-a-1
        else:
            resultado_dict = {}
            for r in range(self._tabla.rowCount()):
                k = self._obtener_texto_celda(r, 0).strip()
                v = self._obtener_texto_celda(r, 1).strip()
                if k:
                    resultado_dict[k] = v
            return resultado_dict

    def _obtener_texto_celda(self, fila: int, col: int) -> str:
        item = self._tabla.item(fila, col)
        return item.text() if item else ""

    # --- Acciones de la Tabla ---

    def _agregar_fila(self) -> None:
        fila = self._tabla.rowCount()
        self._tabla.insertRow(fila)
        for col in range(self._tabla.columnCount()):
            self._tabla.setItem(fila, col, QTableWidgetItem(""))

        self._tabla.selectRow(fila)
        self._tabla.editItem(self._tabla.item(fila, 0))
        n_filas = self._tabla.rowCount()
        self._lbl_conteo_filas.setText(f"{n_filas} filas")
        self._mostrar_feedback(f"Nueva fila agregada (fila {n_filas}).", es_error=False)

    def _eliminar_fila(self) -> None:
        fila = self._tabla.currentRow()
        if fila >= 0:
            self._tabla.removeRow(fila)
            n_filas = self._tabla.rowCount()
            self._lbl_conteo_filas.setText(f"{n_filas} filas")
            self._mostrar_feedback("Fila eliminada de la tabla.", es_error=False)
        else:
            self._mostrar_feedback("Selecciona primero una fila para eliminar.", es_error=True)

    def _filtrar_tabla(self, texto: str) -> None:
        query = texto.strip().lower()
        num_filas = self._tabla.rowCount()
        num_cols = self._tabla.columnCount()

        visibles = 0
        for r in range(num_filas):
            if not query:
                self._tabla.setRowHidden(r, False)
                visibles += 1
                continue

            coincide = False
            for c in range(num_cols):
                val = self._obtener_texto_celda(r, c).lower()
                if query in val:
                    coincide = True
                    break

            self._tabla.setRowHidden(r, not coincide)
            if coincide:
                visibles += 1

        self._lbl_conteo_filas.setText(f"{visibles} de {num_filas} filas")

    def _guardar_archivo(self) -> None:
        try:
            datos = self._serializar_tabla_a_json()
        except Exception as e:
            self._mostrar_feedback(f"✕ Error al procesar los datos de la tabla: {e}", es_error=True)
            return

        ruta_absoluta = JSONS_DIR / self._archivo_activo_rel
        try:
            ruta_absoluta.parent.mkdir(parents=True, exist_ok=True)
            with open(ruta_absoluta, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)

            total_items = 0
            if isinstance(datos, dict):
                for v in datos.values():
                    if isinstance(v, dict):
                        total_items += len(v)
                    elif isinstance(v, list):
                        total_items += len(v)
                    else:
                        total_items += 1
            else:
                total_items = self._tabla.rowCount()

            self._mostrar_feedback(f"✓ Guardado exitoso: {total_items} registros actualizados en '{ruta_absoluta.name}'.", es_error=False)
        except Exception as e:
            self._mostrar_feedback(f"✕ Error al escribir en disco: {e}", es_error=True)

    def _restaurar_ultimo_backup(self) -> None:
        """Restaura el archivo activo desde su backup más reciente."""
        ruta_absoluta = JSONS_DIR / self._archivo_activo_rel
        backup_dir = DATA_DIR / "backups" / "comprobante"

        if not backup_dir.exists():
            self._mostrar_feedback("No existen backups para restaurar.", es_error=True)
            return

        nombre_archivo = ruta_absoluta.name
        backups = sorted(
            [p for p in backup_dir.iterdir() if p.is_file() and p.name.endswith(f"_{nombre_archivo}")],
            key=lambda p: p.name,
            reverse=True,
        )

        if not backups:
            self._mostrar_feedback(f"No se encontró backup para '{nombre_archivo}'.", es_error=True)
            return

        ultimo_backup = backups[0]

        from PySide6.QtWidgets import QMessageBox
        respuesta = QMessageBox.question(
            self,
            "Restaurar backup",
            f"Se va a restaurar '{nombre_archivo}' desde el backup:\n\n{ultimo_backup.name}\n\n"
            "Esta acción reemplazará el archivo actual. ¿Continuar?",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        try:
            shutil.copy2(str(ultimo_backup), str(ruta_absoluta))
            self._recargar_archivo()
            self._mostrar_feedback(
                f"✓ Restaurado desde backup: {ultimo_backup.name}", es_error=False
            )
        except Exception as e:
            self._mostrar_feedback(f"✕ Error al restaurar backup: {e}", es_error=True)

    def _mostrar_feedback(self, mensaje: str, es_error: bool = False) -> None:
        if es_error:
            self._lbl_feedback.setText(mensaje)
            self._lbl_feedback.setStyleSheet("font-size: 13px; font-weight: 600; color: #DC2626;")
            self._panel_feedback.setStyleSheet(
                """
                QFrame#panel_feedback {
                    background-color: #FEF2F2;
                    border: 1px solid #FECACA;
                    border-radius: 8px;
                }
                """
            )
        else:
            self._lbl_feedback.setText(mensaje)
            self._lbl_feedback.setStyleSheet("font-size: 13px; font-weight: 600; color: #16A34A;")
            self._panel_feedback.setStyleSheet(
                """
                QFrame#panel_feedback {
                    background-color: #F0FDF4;
                    border: 1px solid #BBF7D0;
                    border-radius: 8px;
                }
                """
            )
