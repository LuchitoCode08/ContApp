"""Proceso: Interfaz Zeus.

Entrada: Excel 'Interfaz Final Zeus.xlsx' (con la hoja 'Exportar').
Salida: mismo Excel con 2 hojas agregadas:
        - 'Exportar - Copia' (datos originales con 'Cuenta1' depurada).
        - 'Comprobante' (datos con Valor2, BaseAbs, Tarifa y las
          agrupaciones por Nit/Cuenta1/Fecha aplicadas).

Adaptado desde ``zeus.py``:
- lee el Excel que se le pasa como parametro (antes usaba uno fijo en
  ~/Downloads);
- respeta el modo_prueba: en modo prueba copia el Excel a la carpeta
  temporal en vez de modificar el original;
- lee los auxiliares desde ``jsons/zeus/auxiliares_zeus.json``;
- utiliza ``pd.ExcelWriter`` con ``mode='a'`` para conservar la
  informacion del workbook original.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from app.config import RESULTADOS_DIR
from procesos.base import ProcesoBase, ProcesoCancelado, ResultadoProceso
from utils.archivos import carpeta_modo_prueba
from utils.bitacora import log
from utils.json_manager import leer_json

RAIZ = Path(__file__).resolve().parent.parent
NIT_UNIVERSIDAD = "890101681"


class ProcesoZeus(ProcesoBase):
    """Depura el Excel de Zeus: auxiliares de 8 digitos a 6 digitos,
    calcula Valor2/BaseAbs/Tarifa y agrupa por Nit/Cuenta1/Fecha.
    """

    LOG_PREFIX = "[Zeus]"

    # Bandera global que la UI consulta para mostrar el aviso y bloquear
    # la ejecucion. Cambiar a True si se necesita volver a deshabilitar.
    EN_DESARROLLO = False

    MENSAJE_EN_DESARROLLO = (
        "El proceso de Zeus esta en desarrollo y aun no esta disponible "
        "para uso en produccion. Contacta al equipo de contabilidad "
        "cuando este listo."
    )

    def __init__(self) -> None:
        super().__init__()
        json_dir = RAIZ / "jsons" / "zeus"
        aux_data = leer_json(json_dir / "auxiliares_zeus.json")
        self.codigos_auxiliares: dict[str, str] = {
            patron: reemplazo for patron, reemplazo in aux_data["auxiliares"]
        }

    @property
    def nombre(self) -> str:
        return "zeus"

    @property
    def descripcion(self) -> str:
        return (
            "Depura el Excel de Zeus (hoja 'Exportar'): auxiliares de 8 "
            "digitos a 6 digitos, Valor2, BaseAbs, Tarifa y agrupacion "
            "por Nit/Cuenta1/Fecha. Agrega las hojas 'Exportar - Copia' "
            "y 'Comprobante'."
        )

    @property
    def extensiones_entrada(self) -> tuple[str, ...]:
        return (".xlsx", ".xls")

    @property
    def extensiones_salida(self) -> tuple[str, ...]:
        return (".xlsx",)

    def validar_archivos(self, archivos: list[Path]) -> str | None:
        if self.EN_DESARROLLO:
            return self.MENSAJE_EN_DESARROLLO
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

    # ------------------------------------------------------------------
    # Depuracion: adaptacion literal de zeus.py
    # ------------------------------------------------------------------
    def copy_data(self, archivo: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Prepara los datos depurados del Excel de Zeus."""
        xls = pd.ExcelFile(archivo)
        if "Exportar" not in xls.sheet_names:
            raise ValueError(
                f"No se encontro la hoja 'Exportar' en {archivo.name}. "
                f"Hojas disponibles: {xls.sheet_names}"
            )
        comprobante = pd.read_excel(
            archivo, sheet_name="Exportar", dtype=str,
        )
        comprobante["Cuenta1"] = comprobante["Cuenta1"].replace(
            self.codigos_auxiliares, regex=True,
        )
        copia = comprobante.copy()

        # Convertir columnas a tipos numericos y fecha.
        numericos = ["valor", "Base"]
        for col in numericos:
            comprobante[col] = pd.to_numeric(comprobante[col], errors="coerce")
        comprobante["Fecha"] = pd.to_datetime(
            comprobante["Fecha"], errors="coerce",
        ).dt.date

        # Adicionar una nueva columna llamada Valor2.
        maskC = comprobante["Tipo_Movto"].str.strip() == "C"
        comprobante["Valor2"] = np.where(
            maskC, -comprobante["valor"], comprobante["valor"],
        )
        comprobante["BaseAbs"] = comprobante["Base"].abs()

        # Base de retenciones.
        cuentasRetenciones = re.compile(r"(?:2365|2367|2368)")
        maskRetenciones = comprobante["Cuenta1"].str.match(cuentasRetenciones)
        comprobante["Tarifa"] = np.where(
            maskRetenciones & (comprobante["BaseAbs"] != 0),
            (comprobante["valor"] / comprobante["BaseAbs"]) * 100,
            np.nan,
        ).round(2)
        comprobante.loc[maskRetenciones, "Concepto"] = comprobante.loc[
            maskRetenciones, "BaseAbs"
        ].astype(str)

        # Agrupar Cuentas y terceros por Nit y Fecha.
        comprobante["Cuenta1"] = comprobante["Cuenta1"].str.strip()
        cuentasPorAgrupar = [
            "7101", "7105", "119006", "134597", "134598", "143507",
            "280505", "280523", "423575", "530519", "613528",
        ]
        maskAgrupar = comprobante["Cuenta1"].isin(cuentasPorAgrupar)
        agrupar = comprobante[maskAgrupar].copy()
        comprobante = comprobante.drop(agrupar.index)
        agrupar[["valor", "Valor2"]] = agrupar.groupby(
            ["Nit", "Cuenta1", "Fecha", "Tipo_Movto"],
        )[["valor", "Valor2"]].transform("sum")
        agrupar = agrupar.drop_duplicates(
            subset=["Nit", "Cuenta1", "Fecha", "Tipo_Movto"],
        )
        comprobante = pd.concat([comprobante, agrupar], ignore_index=True)

        return copia, comprobante

    # ------------------------------------------------------------------
    # Escritura en Excel (misma estrategia de zeus.py)
    # ------------------------------------------------------------------
    def writer_excel(self, archivo: Path, df: pd.DataFrame, hoja: str) -> None:
        """Escribe un DataFrame en una hoja del archivo Excel.

        Utiliza ``pd.ExcelWriter`` con ``mode='a'`` para conservar las
        hojas originales del workbook y solo reemplazar/agregar la
        hoja indicada. Ademas ajusta el formato de la columna ``Fecha``
        y el ancho de las columnas.
        """
        with pd.ExcelWriter(
            archivo, engine="openpyxl", mode="a", if_sheet_exists="replace",
        ) as writer:
            df.to_excel(writer, sheet_name=hoja, index=False)

            ws = writer.sheets[hoja]
            for col in ws.iter_cols(1, ws.max_column):
                if col[0].value == "Fecha":
                    for cell in col[1:]:
                        cell.number_format = "D-MM-YYYY"

            for nombre_hoja, hoja_nativa in writer.sheets.items():
                for columna in hoja_nativa.columns:
                    max_len = max(
                        len(str(celda.value or "")) for celda in columna
                    )
                    letra_columna = columna[0].column_letter
                    hoja_nativa.column_dimensions[letra_columna].width = max(
                        max_len + 1, 10,
                    )

    # ------------------------------------------------------------------
    # Ejecucion
    # ------------------------------------------------------------------
    def ejecutar(
        self,
        archivos: list[Path],
        modo_prueba: bool = False,
        *,
        progreso: Callable[[int, int], None] | None = None,
        cancelado: Callable[[], bool] | None = None,
    ) -> ResultadoProceso:
        log().info(
            "%s Iniciando (modo_prueba=%s)",
            self.LOG_PREFIX, modo_prueba,
        )
        excel_path = archivos[0]

        if cancelado and cancelado():
            log().info("%s Cancelado antes de procesar.", self.LOG_PREFIX)
            raise ProcesoCancelado()

        try:
            copia, comprobante = self.copy_data(excel_path)
        except Exception as e:
            return ResultadoProceso(exito=False, mensaje=f"Error al procesar: {e}")

        if modo_prueba:
            carpeta = carpeta_modo_prueba(RESULTADOS_DIR, self.nombre)
            import shutil
            destino = carpeta / excel_path.name
            shutil.copy2(excel_path, destino)
            archivo_trabajo = destino
            archivos_originales: list[Path] = []
        else:
            archivo_trabajo = excel_path
            archivos_originales = [excel_path]

        try:
            self.writer_excel(archivo_trabajo, copia, hoja="Exportar - Copia")
            self.writer_excel(archivo_trabajo, comprobante, hoja="Comprobante")
        except ProcesoCancelado:
            raise
        except Exception as e:
            return ResultadoProceso(
                exito=False, mensaje=f"No se pudo escribir el Excel: {e}",
            )

        sufijo = " [PRUEBA]" if modo_prueba else ""
        log().info(
            "%s Excel procesado: %s%s",
            self.LOG_PREFIX, archivo_trabajo.name, sufijo,
        )

        return ResultadoProceso(
            exito=True,
            mensaje="Zeus ejecutado correctamente.",
            archivos_salida=[archivo_trabajo],
            archivos_salida_originales=archivos_originales,
            detalles={
                "filas_originales": len(copia),
                "filas_comprobante": len(comprobante),
            },
        )
