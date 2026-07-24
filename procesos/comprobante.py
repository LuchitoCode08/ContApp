"""Proceso: Generar Comprobante.

Entrada: ZIP que viene del banco, contiene CSVs adentro.
Salida: 2 archivos Excel (comprobante y FOAPAL).
Reglas: leidas desde jsons/comprobante/ (4 JSONs).
"""
from __future__ import annotations

import zipfile
from datetime import datetime
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


class ProcesoComprobante(ProcesoBase):
    """Genera un comprobante contable a partir de un ZIP del banco."""

    LOG_PREFIX = "[Comprobante]"

    @property
    def nombre(self) -> str:
        return "comprobante"

    @property
    def descripcion(self) -> str:
        return (
            "Genera un comprobante contable (2 Excel) a partir de un ZIP "
            "con extractos bancarios del banco."
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
                    "Para comprobante solo se aceptan archivos .zip."
                )
            if not zipfile.is_zipfile(archivo):
                return f"El archivo '{archivo.name}' no es un ZIP valido."
        return None

    def _leer_csvs_de_zip(self, zip_path: Path) -> dict[str, pd.DataFrame]:
        """Lee todos los CSVs dentro de un ZIP y los devuelve por nombre."""
        resultado: dict[str, pd.DataFrame] = {}
        with zipfile.ZipFile(zip_path, "r") as zf:
            for nombre in zf.namelist():
                if not nombre.lower().endswith(".csv"):
                    continue
                with zf.open(nombre) as f:
                    try:
                        df = pd.read_csv(f, sep="|", encoding="utf-8")
                    except Exception:
                        f.seek(0)
                        df = pd.read_csv(f, sep="|", encoding="latin-1")
                resultado[nombre] = df
        return resultado

    def _aplicar_reglas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica las reglas de los 4 JSONs al dataframe (placeholder)."""
        cuentas = leer_json(RAIZ / "jsons" / "comprobante" / "cuentas_bancarias.json")
        log().info("%s %d cuentas bancarias cargadas", self.LOG_PREFIX, len(cuentas))

        # Placeholder: filtra filas cuya columna 'Cuenta' (si existe) este
        # en cuentas. La logica real viene despues.
        return df

    def _escribir_resultados(
        self,
        zip_path: Path,
        data: dict[str, pd.DataFrame],
        carpeta_destino: Path,
    ) -> tuple[Path, Path]:
        """Escribe los 2 Excel de salida."""
        ts = timestamp_unico()
        base = zip_path.stem
        ruta_comprobante = carpeta_destino / f"{base}_comprobante_{ts}.xlsx"
        ruta_foapal = carpeta_destino / f"{base}_foapal_{ts}.xlsx"

        with pd.ExcelWriter(ruta_comprobante, engine="openpyxl") as writer:
            for nombre, df in data.items():
                hoja = Path(nombre).stem[:31] or "Hoja1"
                df.to_excel(writer, sheet_name=hoja, index=False)

        # FOAPAL: Excel con info contable (placeholder).
        df_foapal = pd.DataFrame({
            "Fondo": ["FOPNAL"],
            "Organizacion": ["13201"],
            "Cuenta": ["530515"],
            "Programa": ["999999"],
        })
        df_foapal.to_excel(ruta_foapal, index=False)

        return ruta_comprobante, ruta_foapal

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

        data_limpio = {nombre: self._aplicar_reglas(df) for nombre, df in data.items()}

        if modo_prueba:
            carpeta = carpeta_modo_prueba(RAIZ / "resultados", self.nombre)
        else:
            carpeta = carpeta_resultados(RAIZ / "resultados", self.nombre)

        try:
            comprobante, foapal = self._escribir_resultados(
                zip_path, data_limpio, carpeta,
            )
        except Exception as e:
            return ResultadoProceso(
                exito=False,
                mensaje=f"No se pudo escribir el Excel: {e}",
            )

        log().info("%s Generado: %s", self.LOG_PREFIX, comprobante.name)
        log().info("%s Generado: %s", self.LOG_PREFIX, foapal.name)

        return ResultadoProceso(
            exito=True,
            mensaje="Comprobante generado correctamente.",
            archivos_salida=[comprobante, foapal],
            detalles={"csv_procesados": list(data.keys())},
        )