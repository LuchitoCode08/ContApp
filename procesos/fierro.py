"""Proceso: Interfaz Fierro.

Entrada: ZIP con CSVs adentro.
Salida: 2 archivos Excel (hojas Original + Depurado).
Reglas: leidas desde jsons/fierro/ (3 JSONs).
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd

from procesos.base import ProcesoBase, ResultadoProceso
from utils.archivos import (
    carpeta_modo_prueba,
    carpeta_resultados,
    timestamp_unico,
)
from utils.bitacora import log
from utils.json_manager import leer_json

RAIZ = Path(__file__).resolve().parent.parent


class ProcesoFierro(ProcesoBase):
    """Depura extractos: ZIP de CSVs -> 2 Excel."""

    LOG_PREFIX = "[Fierro]"

    @property
    def nombre(self) -> str:
        return "fierro"

    @property
    def descripcion(self) -> str:
        return (
            "Depura extractos bancarios. Recibe un ZIP con CSVs y produce "
            "2 Excel (hoja Original + hoja Depurado)."
        )

    @property
    def extensiones_entrada(self) -> tuple[str, ...]:
        return (".zip",)

    @property
    def extensiones_salida(self) -> tuple[str, ...]:
        return (".xlsx",)

    def validar_archivos(self, archivos: list[Path]) -> str | None:
        if not archivos:
            return "Se esperaba al menos un archivo ZIP."
        for archivo in archivos:
            if archivo.suffix.lower() not in self.extensiones_entrada:
                return (
                    f"El archivo '{archivo.name}' no es un ZIP. "
                    "Para Fierro solo se aceptan archivos .zip."
                )
            if not zipfile.is_zipfile(archivo):
                return f"El archivo '{archivo.name}' no es un ZIP valido."
        return None

    def _leer_csvs_de_zip(self, zip_path: Path) -> dict[str, pd.DataFrame]:
        resultado: dict[str, pd.DataFrame] = {}
        with zipfile.ZipFile(zip_path, "r") as zf:
            for nombre in zf.namelist():
                if not nombre.lower().endswith(".csv"):
                    continue
                with zf.open(nombre) as f:
                    try:
                        df = pd.read_csv(f, sep="|", encoding="utf-8")
                    except UnicodeDecodeError:
                        f.seek(0)
                        df = pd.read_csv(f, sep="|", encoding="latin-1")
                resultado[nombre] = df
        return resultado

    def _aplicar_reglas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica las reglas de Fierro (descripciones, auxiliares, tarjetas)."""
        reglas_dir = RAIZ / "jsons" / "fierro"

        descripciones = leer_json(reglas_dir / "descripciones.json")
        auxiliares = leer_json(reglas_dir / "auxiliares_cuentas.json")
        tarjetas_data = leer_json(reglas_dir / "tarjetas.json")
        tarjetas = tarjetas_data.get("tarjetas", [])

        df = df.copy()

        # 1) Reemplazos en columna 'Descripcion' (placeholder).
        col_desc = None
        for candidata in ("Descripcion", "Descripción", "descripcion", "DESCRIPCION"):
            if candidata in df.columns:
                col_desc = candidata
                break

        if col_desc is not None:
            for patron, valor in tarjetas:
                df[col_desc] = df[col_desc].astype(str).str.replace(
                    re.compile(patron), valor, regex=True,
                )

        # 2) Reemplazo de auxiliares por cuenta (placeholder).
        log().info(
            "%s %d descripciones, %d auxiliares, %d tarjetas",
            self.LOG_PREFIX, len(descripciones), len(auxiliares), len(tarjetas),
        )

        return df

    def _escribir_resultados(
        self,
        zip_path: Path,
        data_original: dict[str, pd.DataFrame],
        data_depurado: dict[str, pd.DataFrame],
        carpeta_destino: Path,
    ) -> tuple[Path, Path]:
        """Escribe los 2 Excel: Original y Depurado."""
        ts = timestamp_unico()
        base = zip_path.stem

        ruta_original = carpeta_destino / f"{base}_original_{ts}.xlsx"
        ruta_depurado = carpeta_destino / f"{base}_depurado_{ts}.xlsx"

        with pd.ExcelWriter(ruta_original, engine="openpyxl") as writer:
            for nombre, df in data_original.items():
                hoja = Path(nombre).stem[:31] or "Hoja1"
                df.to_excel(writer, sheet_name=hoja, index=False)

        with pd.ExcelWriter(ruta_depurado, engine="openpyxl") as writer:
            for nombre, df in data_depurado.items():
                hoja = Path(nombre).stem[:31] or "Hoja1"
                df.to_excel(writer, sheet_name=hoja, index=False)

        return ruta_original, ruta_depurado

    def ejecutar(
        self,
        archivos: list[Path],
        modo_prueba: bool = False,
    ) -> ResultadoProceso:
        log().info("%s Iniciando (modo_prueba=%s)", self.LOG_PREFIX, modo_prueba)
        zip_path = archivos[0]

        try:
            data = self._leer_csvs_de_zip(zip_path)
        except Exception as e:
            return ResultadoProceso(
                exito=False,
                mensaje=f"No se pudo leer el ZIP: {e}",
            )
        log().info("%s %d CSV(s) leido(s)", self.LOG_PREFIX, len(data))

        depurado = {nombre: self._aplicar_reglas(df) for nombre, df in data.items()}

        if modo_prueba:
            carpeta = carpeta_modo_prueba(RAIZ / "resultados", self.nombre)
        else:
            carpeta = carpeta_resultados(RAIZ / "resultados", self.nombre)

        try:
            original, depurado_xlsx = self._escribir_resultados(
                zip_path, data, depurado, carpeta,
            )
        except Exception as e:
            return ResultadoProceso(
                exito=False,
                mensaje=f"No se pudo escribir el Excel: {e}",
            )

        log().info("%s Generado: %s", self.LOG_PREFIX, original.name)
        log().info("%s Generado: %s", self.LOG_PREFIX, depurado_xlsx.name)

        return ResultadoProceso(
            exito=True,
            mensaje="Fierro ejecutado correctamente.",
            archivos_salida=[original, depurado_xlsx],
            detalles={"csv_procesados": list(data.keys())},
        )