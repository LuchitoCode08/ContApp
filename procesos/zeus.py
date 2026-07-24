"""Proceso: Interfaz Zeus.

Entrada: 1 archivo Excel.
Salida: mismo Excel depurado (modo produccion) o copia (modo prueba).
Reglas: leidas desde jsons/zeus/ (1 JSON con pares patron -> valor).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from procesos.base import ProcesoBase, ResultadoProceso
from utils.archivos import (
    carpeta_modo_prueba,
    carpeta_resultados,
    timestamp_unico,
)
from utils.bitacora import log
from utils.json_manager import leer_json

RAIZ = Path(__file__).resolve().parent.parent


class ProcesoZeus(ProcesoBase):
    """Depura un Excel en sitio: agrega la hoja 'Depurado'."""

    LOG_PREFIX = "[Zeus]"

    @property
    def nombre(self) -> str:
        return "zeus"

    @property
    def descripcion(self) -> str:
        return (
            "Depura un Excel en sitio. Recibe un Excel y agrega la hoja "
            "'Depurado' con las reglas aplicadas."
        )

    @property
    def extensiones_entrada(self) -> tuple[str, ...]:
        return (".xlsx", ".xls")

    @property
    def extensiones_salida(self) -> tuple[str, ...]:
        return (".xlsx",)

    def validar_archivos(self, archivos: list[Path]) -> str | None:
        if not archivos:
            return "Se esperaba al menos un archivo Excel."
        if len(archivos) > 1:
            return "Zeus procesa un solo Excel a la vez."
        archivo = archivos[0]
        if archivo.suffix.lower() not in self.extensiones_entrada:
            return (
                f"El archivo '{archivo.name}' no es un Excel. "
                f"Extensiones validas: {self.extensiones_entrada}"
            )
        return None

    def _leer_excel(self, ruta: Path) -> dict[str, pd.DataFrame]:
        return pd.read_excel(ruta, sheet_name=None)

    def _aplicar_reglas(self, df: pd.DataFrame) -> pd.DataFrame:
        reglas_data = leer_json(RAIZ / "jsons" / "zeus" / "auxiliares.json")
        auxiliares = reglas_data.get("auxiliares", [])
        log().info("%s %d pares de auxiliares cargados", self.LOG_PREFIX, len(auxiliares))

        df = df.copy()

        col_desc = None
        for candidata in ("Descripcion", "Descripción", "descripcion", "DESCRIPCION"):
            if candidata in df.columns:
                col_desc = candidata
                break

        if col_desc is not None and auxiliares:
            for patron, valor in auxiliares:
                df[col_desc] = df[col_desc].astype(str).str.replace(
                    re.compile(patron), valor, regex=True,
                )

        return df

    def ejecutar(
        self,
        archivos: list[Path],
        modo_prueba: bool = False,
    ) -> ResultadoProceso:
        log().info("%s Iniciando (modo_prueba=%s)", self.LOG_PREFIX, modo_prueba)
        excel_path = archivos[0]

        try:
            data = self._leer_excel(excel_path)
        except Exception as e:
            return ResultadoProceso(
                exito=False,
                mensaje=f"No se pudo leer el Excel: {e}",
            )
        log().info("%s %d hoja(s) leida(s)", self.LOG_PREFIX, len(data))

        # Tomar la primera hoja para la hoja 'Depurado'.
        primera_hoja = next(iter(data.values()))
        depurado = self._aplicar_reglas(primera_hoja)

        # Determinar donde escribir.
        if modo_prueba:
            carpeta = carpeta_modo_prueba(RAIZ / "resultados", self.nombre)
            ts = timestamp_unico()
            destino = carpeta / f"{excel_path.stem}_depurado_{ts}.xlsx"
        else:
            carpeta = carpeta_resultados(RAIZ / "resultados", self.nombre)
            destino = excel_path  # en sitio

        try:
            # Si es modo produccion, modificamos el archivo en sitio (mode='a').
            if not modo_prueba:
                wb = load_workbook(destino)
                with pd.ExcelWriter(destino, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                    depurado.to_excel(writer, sheet_name="Depurado", index=False)
            else:
                # Modo prueba: copia el Excel original y le agrega la hoja Depurado.
                import shutil
                shutil.copy2(excel_path, destino)
                with pd.ExcelWriter(destino, engine="openpyxl", mode="w") as writer:
                    for nombre, df in data.items():
                        df.to_excel(writer, sheet_name=nombre[:31] or "Hoja1", index=False)
                    depurado.to_excel(writer, sheet_name="Depurado", index=False)
        except Exception as e:
            return ResultadoProceso(
                exito=False,
                mensaje=f"No se pudo escribir el Excel: {e}",
            )

        log().info("%s Generado: %s", self.LOG_PREFIX, destino.name)

        return ResultadoProceso(
            exito=True,
            mensaje="Zeus ejecutado correctamente.",
            archivos_salida=[destino],
            archivos_salida_originales=[excel_path] if not modo_prueba else [],
            detalles={"hojas_procesadas": list(data.keys())},
        )