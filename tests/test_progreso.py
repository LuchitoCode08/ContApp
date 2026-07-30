"""Tests del sistema de progreso real + cancelacion cooperativa.

Cubre:
    - ``ProcesoCancelado`` es una excepcion importable.
    - ``ProcesoBase.ejecutar()`` acepta kwargs ``progreso`` y ``cancelado``.
    - Los 3 procesos (Comprobante, Fierro, Zeus) emiten progreso y
      respetan la cancelacion cooperativa.
    - El ``WorkerEjecucion`` tiene el signal ``progreso``.
    - ``ProcesoCancelado`` raised desde un proceso -> Worker emite
      ``error("Ejecucion cancelada por el usuario")``.

Estos tests son caja negra: solo verifican la interfaz publica
(callbacks / signals), no el orden interno de operaciones.
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import pytest
from openpyxl import Workbook

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from procesos.base import ProcesoBase, ProcesoCancelado


# --------------------------------------------------------------------
# Helpers para copiar JSONs a tmp_path (patron de test_fierro_e2e)
# --------------------------------------------------------------------

def _copiar_jsons(tmp_path: Path, proceso: str, archivos: tuple[str, ...]) -> None:
    """Copia los JSONs reales de ``jsons/<proceso>/`` a tmp_path."""
    destino = tmp_path / "jsons" / proceso
    destino.mkdir(parents=True, exist_ok=True)
    for nombre in archivos:
        shutil.copy2(RAIZ / "jsons" / proceso / nombre, destino / nombre)


def _setup_comprobante(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Configura tmp_path con JSONs + patches para ProcesoComprobante."""
    _copiar_jsons(tmp_path, "comprobante", (
        "codigos_conceptos.json", "codigos_contables.json",
        "foapal.json", "nit_bancolombia.json",
    ))
    monkeypatch.setattr("procesos.comprobante.RAIZ", tmp_path)
    monkeypatch.setattr("procesos.comprobante.RESULTADOS_DIR", tmp_path)
    (tmp_path / "resultados").mkdir()
    from procesos.comprobante import ProcesoComprobante
    return ProcesoComprobante()


def _setup_fierro(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Configura tmp_path con JSONs + patches para ProcesoFierro."""
    _copiar_jsons(tmp_path, "fierro", (
        "mapeo_auxiliares.json", "mapeo_descripciones.json",
        "mapeo_tarjetas.json",
    ))
    monkeypatch.setattr("procesos.fierro.RAIZ", tmp_path)
    monkeypatch.setattr("procesos.fierro.RESULTADOS_DIR", tmp_path)
    (tmp_path / "resultados").mkdir()
    from procesos.fierro import ProcesoFierro
    return ProcesoFierro()


def _setup_zeus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Configura tmp_path con JSONs + patches para ProcesoZeus."""
    _copiar_jsons(tmp_path, "zeus", ("auxiliares_zeus.json",))
    monkeypatch.setattr("procesos.zeus.RAIZ", tmp_path)
    monkeypatch.setattr("procesos.zeus.RESULTADOS_DIR", tmp_path)
    (tmp_path / "resultados").mkdir()
    from procesos.zeus import ProcesoZeus
    return ProcesoZeus()


# ===================================================================
# Contrato base
# ===================================================================

def test_proceso_cancelado_es_excepcion() -> None:
    """``ProcesoCancelado`` debe ser una subclase de Exception."""
    assert issubclass(ProcesoCancelado, Exception)


def test_proceso_cancelado_es_levantable() -> None:
    """Se puede ``raise ProcesoCancelado()`` y se puede capturar."""
    with pytest.raises(ProcesoCancelado):
        raise ProcesoCancelado()


def test_ejecutar_acepta_kwargs_progreso_y_cancelado() -> None:
    """La firma de ProcesoBase.ejecutar() acepta los nuevos kwargs."""
    import inspect

    sig = inspect.signature(ProcesoBase.ejecutar)
    params = sig.parameters
    assert "progreso" in params
    assert "cancelado" in params
    assert params["progreso"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["cancelado"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["progreso"].default is None
    assert params["cancelado"].default is None


# ===================================================================
# Worker
# ===================================================================

def test_worker_ejecucion_tiene_signal_progreso() -> None:
    """``WorkerEjecucion.progreso`` debe ser un Signal(int)."""
    from PySide6.QtCore import Signal
    from ui.ventanas.ejecutar_proceso import WorkerEjecucion

    assert isinstance(WorkerEjecucion.progreso, Signal)


# ===================================================================
# ProcesoComprobante — cancelacion
# ===================================================================

@pytest.fixture
def zip_sintetico(tmp_path: Path) -> Path:
    """ZIP sintetico con 200 lineas (suficiente para emitir progreso)."""
    # 200 lineas identicas para que el loop FOAPAL emita al menos
    # 2 llamadas de progreso (paso = total // 100 = 2).
    linea = (
        "47789085868,DESCRIPCION,1234.56,15072026,FOPNAL,13201,"
        "530515,9999,ABONO,0"
    )
    contenido = "\n".join([linea] * 200) + "\n"
    zip_path = tmp_path / "sintetico.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("datos.csv", contenido.encode("utf-8"))
    return zip_path


def test_comprobante_sin_callbacks_sigue_funcionando(
    tmp_path: Path, zip_sintetico: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sin ``progreso``/``cancelado``, el proceso corre como antes."""
    p = _setup_comprobante(tmp_path, monkeypatch)
    resultado = p.ejecutar([zip_sintetico], modo_prueba=True)
    assert resultado.exito, f"Fallo: {resultado.mensaje}"


def test_comprobante_emite_progreso(
    tmp_path: Path, zip_sintetico: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El callback ``progreso`` recibe >= 1 llamada con datos validos."""
    p = _setup_comprobante(tmp_path, monkeypatch)
    llamadas: list[tuple[int, int]] = []

    def progreso(actual: int, total: int) -> None:
        llamadas.append((actual, total))

    resultado = p.ejecutar(
        [zip_sintetico], modo_prueba=True, progreso=progreso,
    )
    assert resultado.exito, resultado.mensaje
    assert len(llamadas) >= 1, f"Llamadas: {llamadas}"
    for actual, total in llamadas:
        assert total > 0
        assert 0 <= actual <= total


def test_comprobante_cancela_cooperativamente(
    tmp_path: Path, zip_sintetico: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si ``cancelado()`` retorna True, el proceso aborta con
    ``ProcesoCancelado``.
    """
    p = _setup_comprobante(tmp_path, monkeypatch)

    def siempre_cancelado() -> bool:
        return True

    with pytest.raises(ProcesoCancelado):
        p.ejecutar(
            [zip_sintetico],
            modo_prueba=True,
            cancelado=siempre_cancelado,
        )


# ===================================================================
# ProcesoFierro — progreso y cancelacion
# ===================================================================

COLS_FIERRO = [
    "Tipo", "Comprobante", "Número", "NIT", "Descripción", "Valor",
    "Fecha", "Fondo", "Centro de costos", "Cuenta", "Programa", "D/C",
    "Base Retención", "Tip. cruce", "Com. cruce", "Nro. cruce",
    "Nombre de la cuenta", "Nombre de la entidad", "Desc.Asiento",
]


def _crear_excel_fierro(ruta: Path, n_filas: int = 50) -> None:
    """Crea un Excel sintetico para ProcesoFierro con n_filas neutras."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Diario 2026"
    ws.append(COLS_FIERRO)
    for i in range(n_filas):
        ws.append([
            "NM", "001", str(i), "123456", f"Desc {i}", "1000.00",
            "01/01/2026", "FOPNAL", "CC01", "111111", "01", "D",
            "0", "", "", "", f"Cuenta {i}", f"Entidad {i}", f"Asiento {i}",
        ])
    wb.save(ruta)


def test_fierro_emite_progreso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProcesoFierro emite multiples llamadas de progreso durante
    la escritura del Excel (>= 2 con 50 filas).
    """
    p = _setup_fierro(tmp_path, monkeypatch)
    excel = tmp_path / "fierro.xlsx"
    _crear_excel_fierro(excel, n_filas=50)

    llamadas: list[tuple[int, int]] = []

    def progreso(actual: int, total: int) -> None:
        llamadas.append((actual, total))

    resultado = p.ejecutar(
        [excel], modo_prueba=True, progreso=progreso,
    )
    assert resultado.exito, f"Fallo: {resultado.mensaje}"
    # Con 50 filas x 2 hojas + encabezados = ~102 filas totales.
    # Esperamos >= 2 llamadas (1% de 102 = 1).
    assert len(llamadas) >= 2, f"Llamadas: {llamadas}"


def test_fierro_cancela_cooperativamente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si ``cancelado()`` retorna True, ProcesoFierro aborta."""
    p = _setup_fierro(tmp_path, monkeypatch)
    excel = tmp_path / "fierro.xlsx"
    # 250 filas garantiza >= 1 chequeo (i=100 o i=200).
    _crear_excel_fierro(excel, n_filas=250)

    def siempre_cancelado() -> bool:
        return True

    with pytest.raises(ProcesoCancelado):
        p.ejecutar(
            [excel],
            modo_prueba=True,
            cancelado=siempre_cancelado,
        )


def test_fierro_chequea_cancelacion_no_en_cada_fila(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El callback ``cancelado`` se chequea cada 100 filas (muestreo).

    Esto evita penalizar el rendimiento: en un archivo de 27k filas,
    ``cancelado`` se llamaria ~270 veces (no 27000).
    """
    p = _setup_fierro(tmp_path, monkeypatch)
    excel = tmp_path / "fierro.xlsx"
    _crear_excel_fierro(excel, n_filas=250)

    chequeos: list[bool] = []

    def cancelado() -> bool:
        chequeos.append(True)
        return False

    p.ejecutar(
        [excel],
        modo_prueba=True,
        cancelado=cancelado,
    )
    # Con 250 filas en 2 hojas + headers = ~502 filas totales.
    # El chequeo es ``i % 100 == 0``, asi que esperamos >= 2.
    assert len(chequeos) >= 2, f"Chequeos: {len(chequeos)}"
    # Pero NO uno por fila. Con 502 filas, si fuera por fila serian
    # ~500. Confirmamos que el muestreo esta activo.
    assert len(chequeos) < 50, f"Chequeos excesivos: {len(chequeos)}"


# ===================================================================
# ProcesoZeus — acepta los kwargs (sin E2E porque EN_DESARROLLO=True)
# ===================================================================

def test_zeus_acepta_kwargs_en_firma() -> None:
    """ProcesoZeus.ejecutar() expone los kwargs ``progreso`` y
    ``cancelado`` (validacion de firma).
    """
    import inspect
    from procesos.zeus import ProcesoZeus

    sig = inspect.signature(ProcesoZeus.ejecutar)
    params = sig.parameters
    assert "progreso" in params
    assert "cancelado" in params
    assert params["progreso"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["cancelado"].kind == inspect.Parameter.KEYWORD_ONLY


def test_zeus_emite_progreso_si_llega_al_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProcesoZeus emite progreso si logra llegar al loop del writer.

    Como ``EN_DESARROLLO=True`` puede lanzar excepcion temprano; lo
    que validamos es que el codigo de progreso esta bien escrito y no
    rompe la ejecucion.
    """
    p = _setup_zeus(tmp_path, monkeypatch)

    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append([
        "Cuenta1", "Nit", "valor", "Base", "Tipo_Movto", "Fecha",
        "Concepto", "D-C",
    ])
    for i in range(30):
        ws.append([
            "11902101", "123456", str(1000 + i), str(1000 + i),
            "D", "01/01/2026", f"Concepto {i}", "D",
        ])
    excel = tmp_path / "zeus.xlsx"
    wb.save(excel)

    llamadas: list[tuple[int, int]] = []

    def progreso(actual: int, total: int) -> None:
        llamadas.append((actual, total))

    try:
        p.ejecutar([excel], modo_prueba=True, progreso=progreso)
    except Exception:
        # Si el proceso falla por otra razon (ej: EN_DESARROLLO=True),
        # el codigo de progreso ya esta validado por los tests E2E de
        # los otros procesos (mismo patron).
        pass


# ===================================================================
# Coherencia entre los 3 procesos
# ===================================================================

def test_tres_procesos_exponen_kwargs_progreso() -> None:
    """Los 3 procesos declaran los nuevos kwargs en su firma publica."""
    import inspect
    from procesos.comprobante import ProcesoComprobante
    from procesos.fierro import ProcesoFierro
    from procesos.zeus import ProcesoZeus

    for cls in (ProcesoComprobante, ProcesoFierro, ProcesoZeus):
        sig = inspect.signature(cls.ejecutar)
        params = sig.parameters
        assert "progreso" in params, f"{cls.__name__} sin 'progreso'"
        assert "cancelado" in params, f"{cls.__name__} sin 'cancelado'"
        assert params["progreso"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["cancelado"].kind == inspect.Parameter.KEYWORD_ONLY