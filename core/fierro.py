"""Proceso: Interfaz Fierro.

Entrada: Excel del estilo 'Interfaz Final Fierro Junio 2026.xlsx'
        (con la hoja 'Diario 2026').
Salida: mismo Excel con 2 hojas agregadas:
        - 'Diario 2026 - Copia' (copia de los datos originales).
        - 'Comprobante' (datos depurados siguiendo el instructivo
          KM5: filtros por tipo, agrupaciones por Cuenta/D-C,
          descripciones dinámicas, regex de tarjetas, etc.).
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd
from dateutil.relativedelta import relativedelta

from app.config import JSONS_DIR, RESULTADOS_DIR
from core.archivos import carpeta_modo_prueba
from core.base import ProcesoBase, ProcesoCancelado, ResultadoProceso
from core.json_manager import leer_json

NIT_UNIVERSIDAD = "890101681"


class ProcesoFierro(ProcesoBase):
    """Depura el Excel de Fierro siguiendo el instructivo KM5."""

    LOG_PREFIX = "[Fierro]"

    def __init__(self) -> None:
        super().__init__()
        json_dir = JSONS_DIR / "fierro"
        self.codigos_auxiliares: dict[str, str] = leer_json(json_dir / "mapeo_auxiliares.json")

        self.mes_anio: str = (datetime.now() - relativedelta(months=1)).strftime("%B-%Y")

        descripciones_raw = leer_json(json_dir / "mapeo_descripciones.json")
        self.dicts_desc: dict[str, str] = {
            cuenta: texto if texto == "Redondeo" else f"{texto} {self.mes_anio}"
            for cuenta, texto in descripciones_raw.items()
        }

        tarjetas_data = leer_json(json_dir / "mapeo_tarjetas.json")
        self.dicts_tarjetas: list[tuple[str, str]] = [
            (item[0], item[1]) for item in tarjetas_data["tarjetas"]
        ]

    @property
    def nombre(self) -> str:
        return "fierro"

    @property
    def descripcion(self) -> str:
        return (
            "Depura el Excel de Fierro (hoja 'Diario 2026') y agrega la "
            "hoja 'Comprobante' con los datos agrupados y mapeados."
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
            return "Fierro procesa un solo Excel a la vez."
        archivo = archivos[0]
        if archivo.suffix.lower() not in self.extensiones_entrada:
            return (
                f"El archivo '{archivo.name}' no es un Excel. "
                f"Extensiones válidas: {self.extensiones_entrada}"
            )
        return None

    def copy_data(self, archivo: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        df = pd.read_excel(archivo, sheet_name="Diario 2026", dtype=str)
        data_frame_copy = df.copy()
        data_frame_copy["Valor"] = pd.to_numeric(
            data_frame_copy["Valor"], errors="coerce",
        )
        data_frame_copy["Valor Abs"] = data_frame_copy["Valor"].abs()
        data_frame_copy["Cuenta"] = data_frame_copy["Cuenta"].replace(self.codigos_auxiliares)
        copia = data_frame_copy.copy()

        cuentasCyC = ["143508", "613528"]
        patronCyC = r"^(Mercadería FC|Costo FC)"
        maskCyC = (
            data_frame_copy["Descripción"].str.match(patronCyC, na=False)
            & data_frame_copy["Cuenta"].isin(cuentasCyC)
        )
        costeoYCosto = data_frame_copy[maskCyC].copy()
        data_frame_copy = data_frame_copy.drop(costeoYCosto.index)
        costeoYCosto["Valor"] = costeoYCosto.groupby("Cuenta")["Valor"].transform("sum")
        costeoYCosto = costeoYCosto.drop_duplicates(subset="Cuenta", keep="first")
        costeoYCosto["Descripción"] = f"Costo de ventas {self.mes_anio}"

        cuentasVentas = ["119002", "280505", "429505", "429567", "530519"]
        tipoVentas = "FC"
        patronVentas = r"^(Venta)"
        maskVentas = (
            data_frame_copy["Desc.Asiento"].str.match(patronVentas, na=False)
            & data_frame_copy["Cuenta"].isin(cuentasVentas)
            & (data_frame_copy["Tipo"].str.strip() == tipoVentas)
        )
        ventas = data_frame_copy[maskVentas].copy()
        data_frame_copy = data_frame_copy.drop(ventas.index)
        cambioDescripcion = ["119002", "280505", "429505", "530519"]
        maskDesc = ventas["Cuenta"].isin(cambioDescripcion)
        ventas.loc[maskDesc, "Descripción"] = ventas.loc[maskDesc, "Cuenta"].map(self.dicts_desc)
        ventasAgrupadas = ventas.loc[maskDesc]
        ventas = ventas.drop(ventasAgrupadas.index, errors="ignore")
        ventasAgrupadas["Valor"] = ventasAgrupadas.groupby(
            ["Cuenta", "D/C"]
        )["Valor"].transform("sum")
        ventasAgrupadas = ventasAgrupadas.drop_duplicates(
            subset=["Cuenta", "D/C"], keep="first",
        )
        ventas = pd.concat([ventas, ventasAgrupadas], ignore_index=True)

        tipoConsignaciones = "BD"
        maskConsignaciones = data_frame_copy["Tipo"].str.strip() == tipoConsignaciones
        consignaciones = data_frame_copy[maskConsignaciones].copy()
        data_frame_copy = data_frame_copy.drop(consignaciones.index)
        cuentaConsignaciones = ["119002"]
        maskExcp = consignaciones["Cuenta"].isin(cuentaConsignaciones)
        consignaciones119002 = consignaciones.loc[maskExcp].copy()
        consignaciones = consignaciones.drop(consignaciones119002.index)
        consignaciones119002["Valor"] = consignaciones119002.groupby(
            ["Cuenta", "D/C"]
        )["Valor"].transform("sum")
        consignaciones119002 = consignaciones119002.drop_duplicates(
            subset=["Cuenta", "D/C"], keep="first",
        )
        consignaciones119002["Descripción"] = f"Consignación caja venta {self.mes_anio}"
        consignaciones = pd.concat(
            [consignaciones, consignaciones119002], ignore_index=True,
        )
        maskBD = consignaciones["Tipo"].str.strip().eq("BD")
        patronEliminacion = re.compile(
            r"\(BANCOLOMBIA - CUENTA[^)]*\)", flags=re.IGNORECASE,
        )
        consignaciones.loc[maskBD, "Descripción"] = (
            consignaciones.loc[maskBD, "Descripción"]
            .astype(str)
            .apply(lambda x: patronEliminacion.sub("", x).strip())
        )

        patronCompra = r"^(Compra FC)"
        maskCompra = data_frame_copy["Desc.Asiento"].str.match(patronCompra, na=False)
        compra = data_frame_copy.loc[maskCompra].copy()
        data_frame_copy = data_frame_copy.drop(compra.index)

        tipoDiferenciaCaja = "CC"
        maskDiferencia = data_frame_copy["Tipo"].str.strip() == tipoDiferenciaCaja
        diferenciaCaja = data_frame_copy.loc[maskDiferencia].copy()
        data_frame_copy = data_frame_copy.drop(diferenciaCaja.index)
        diferenciaCaja["Valor"] = diferenciaCaja.groupby(
            ["Cuenta", "D/C"]
        )["Valor"].transform("sum")
        diferenciaCaja = diferenciaCaja.drop_duplicates(
            subset=["Cuenta", "D/C"], keep="first",
        )
        diferenciaCaja["Descripción"] = "Diferencia de caja Consolidación"

        tiposOpNc = ["OP", "NC"]
        maskOpNc = data_frame_copy["Tipo"].str.strip().isin(tiposOpNc)
        datosOpNc = data_frame_copy[maskOpNc].copy()
        data_frame_copy = data_frame_copy.drop(datosOpNc.index)
        maskOP = datosOpNc["Tipo"].str.strip() == "OP"
        patronPrograma = re.compile(r"Programación", flags=re.IGNORECASE)
        patronTransferencia = re.compile(r"Transferencia", flags=re.IGNORECASE)
        datosOpNc.loc[maskOP, "Descripción"] = (
            datosOpNc.loc[maskOP, "Descripción"]
            .astype(str)
            .apply(lambda x: patronPrograma.sub("Prog", x).strip())
        )
        datosOpNc.loc[maskOP, "Descripción"] = (
            datosOpNc.loc[maskOP, "Descripción"]
            .astype(str)
            .apply(lambda x: patronTransferencia.sub("Trans", x).strip())
        )

        tipoSeSgSt = ["SE", "SG", "ST"]
        maskSeSgSt = data_frame_copy["Tipo"].str.strip().isin(tipoSeSgSt)
        datosSeSgSt = data_frame_copy[maskSeSgSt].copy()
        data_frame_copy = data_frame_copy.drop(datosSeSgSt.index)
        mask280505 = datosSeSgSt["Cuenta"] == "280505"
        datosSeSgSt.loc[mask280505, "NIT"] = NIT_UNIVERSIDAD

        tipoTC = "TC"
        maskTC = data_frame_copy["Tipo"].str.strip() == tipoTC
        datosTC = data_frame_copy[maskTC].copy()
        data_frame_copy = data_frame_copy.drop(datosTC.index)

        cuentasDescripcion = [
            "134595", "136598", "220503",
            "513535", "513560", "519510",
            "519530", "519581", "531510",
            "539599",
        ]
        maskCuentasDescripcion = data_frame_copy["Cuenta"].isin(cuentasDescripcion)
        data_frame_copy.loc[maskCuentasDescripcion, "Descripción"] = (
            data_frame_copy.loc[maskCuentasDescripcion, "Desc.Asiento"]
        )

        comprobante = pd.concat([
            data_frame_copy, costeoYCosto, ventas, consignaciones,
            compra, diferenciaCaja, datosOpNc, datosSeSgSt,
        ])

        for patron, reemplazo in self.dicts_tarjetas:
            comprobante["Descripción"] = comprobante["Descripción"].str.replace(
                patron, reemplazo, regex=True,
            )

        comprobante["Fecha"] = pd.to_datetime(
            comprobante["Fecha"], format="%d/%m/%Y",
            errors="coerce", dayfirst=True,
        ).dt.date

        comprobante = comprobante[[
            "Tipo", "Comprobante", "Número", "NIT", "Descripción",
            "Valor Abs", "Fecha", "Fondo", "Centro de costos", "Cuenta",
            "Programa", "D/C", "Valor", "Base Retención", "Tip. cruce",
            "Com. cruce", "Nro. cruce", "Nombre de la cuenta",
            "Nombre de la entidad", "Desc.Asiento",
        ]]

        return copia, comprobante

    def writer_excel(self, archivo: Path, df: pd.DataFrame, hoja: str) -> None:
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

    def ejecutar(
        self,
        archivos: list[Path],
        modo_prueba: bool = False,
        *,
        progreso: Callable[[int, int], None] | None = None,
        cancelado: Callable[[], bool] | None = None,
    ) -> ResultadoProceso:
        excel_path = archivos[0]

        if cancelado and cancelado():
            raise ProcesoCancelado()

        try:
            copia, comprobante = self.copy_data(excel_path)
        except Exception as e:
            return ResultadoProceso(exito=False, mensaje=f"Error al procesar: {e}")

        if modo_prueba:
            carpeta = carpeta_modo_prueba(RESULTADOS_DIR, self.nombre)
            destino = carpeta / excel_path.name
            shutil.copy2(excel_path, destino)
            archivo_trabajo = destino
            archivos_originales: list[Path] = []
        else:
            archivo_trabajo = excel_path
            archivos_originales = [excel_path]

        if progreso:
            progreso(1, 4)

        try:
            self.writer_excel(archivo_trabajo, copia, "Diario 2026 - Copia")
            if cancelado and cancelado():
                raise ProcesoCancelado()
            if progreso:
                progreso(2, 4)
            self.writer_excel(archivo_trabajo, comprobante, "Comprobante")
            if progreso:
                progreso(4, 4)
        except ProcesoCancelado:
            raise
        except Exception as e:
            return ResultadoProceso(
                exito=False, mensaje=f"No se pudo escribir el Excel: {e}",
            )

        return ResultadoProceso(
            exito=True,
            mensaje="Fierro ejecutado correctamente.",
            archivos_salida=[archivo_trabajo],
            archivos_salida_originales=archivos_originales,
            detalles={"filas_originales": len(copia), "filas_comprobante": len(comprobante)},
        )
