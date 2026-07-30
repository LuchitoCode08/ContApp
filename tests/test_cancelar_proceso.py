"""Tests del flujo "Cancelar ejecucion" en VistaEjecucion.

Cubre:
    - Estado inicial del boton (oculto).
    - Click sin worker: no-op.
    - Confirmacion Yes -> worker.cancelar() llamado, boton deshabilitado, estado.
    - Confirmacion No -> worker NO cancelado, boton sigue habilitado.
    - _on_terminado / _on_error ocultan y resetean el boton.

Usa QT_QPA_PLATFORM=offscreen (no abre ventana). Mockea QMessageBox.question.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Forzar offscreen ANTES de importar Qt (clave para CI).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

# sys.path para que los imports del paquete funcionen desde pytest rootdir.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    """Una sola QApplication por modulo (Qt no permite mas de una)."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def vista(qt_app):
    """VistaEjecucion sin auto-mockear nada (los tests especificos lo hacen)."""
    from ui.ventanas.ejecutar_proceso import VistaEjecucion

    v = VistaEjecucion()
    # Necesario para que _cancelar_ejecucion sepa que proceso cancelar.
    v._nombre_proceso = "fierro"
    yield v
    # Liberar el widget al final del test para no leakear entre casos.
    # Nunca creamos QThreads reales en estos tests, asi que NO bloquear.
    v.deleteLater()


# ============================================================
# Estado inicial
# ============================================================

def test_btn_cancelar_arranca_oculto(vista: "VistaEjecucion") -> None:
    """El boton de cancelar NO debe ser visible al inicio (no hay job)."""
    assert vista.btn_cancelar.isVisible() is False


def test_btn_cancelar_es_danger(vista: "VistaEjecucion") -> None:
    """QSS rule: el objectName debe ser 'danger' (tema lo pinta rojo)."""
    assert vista.btn_cancelar.objectName() == "danger"


def test_btn_cancelar_arranca_habilitado(vista: "VistaEjecucion") -> None:
    """Aunque este oculto, debe estar enabled para cuando aparezca."""
    assert vista.btn_cancelar.isEnabled() is True


# ============================================================
# Click sin worker (no-op seguro)
# ============================================================

def test_cancelar_sin_worker_es_noop(vista: "VistaEjecucion", monkeypatch) -> None:
    """Si no hay worker corriendo, el handler debe salir sin mostrar dialog."""
    llamado = {"count": 0}

    def fake_question(*args, **kwargs):
        llamado["count"] += 1
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))

    # Estado inicial: sin worker.
    assert vista._worker is None
    vista._cancelar_ejecucion()

    assert llamado["count"] == 0, (
        "No se debe mostrar el dialog si no hay worker corriendo."
    )


def test_cancelar_con_worker_detenido_es_noop(
    vista: "VistaEjecucion", monkeypatch,
) -> None:
    """Si existe _worker pero NO esta corriendo, tambien es no-op."""
    from ui.ventanas.ejecutar_proceso import WorkerEjecucion
    from procesos.fierro import ProcesoFierro

    llamado = {"count": 0}

    def fake_question(*args, **kwargs):
        llamado["count"] += 1
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))

    vista._worker = WorkerEjecucion(ProcesoFierro(), [], modo_prueba=True)
    # NO llamamos .start() -> isRunning() es False.

    vista._cancelar_ejecucion()

    assert llamado["count"] == 0


# ============================================================
# Confirmacion Yes -> cancelar()
# ============================================================

def test_cancelar_confirmado_llama_cancelar(
    vista: "VistaEjecucion", monkeypatch,
) -> None:
    """Yes -> worker.cancelar() se llama, boton se deshabilita, estado cambia."""
    from ui.ventanas.ejecutar_proceso import WorkerEjecucion
    from procesos.fierro import ProcesoFierro

    def fake_question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))

    # Crear un worker "vivo" sin .start() (no podemos .start() en este test
    # porque bloquearia esperando el proceso real).
    vista._worker = WorkerEjecucion(ProcesoFierro(), [], modo_prueba=True)

    # Parchar isRunning para que devuelva True sin haber llamado start().
    monkeypatch.setattr(vista._worker, "isRunning", lambda: True)
    # Parchar cancelar para que solo marque una flag observable.
    cancelado = {"flag": False}

    def fake_cancelar() -> None:
        cancelado["flag"] = True
        vista._worker._cancelado = True

    monkeypatch.setattr(vista._worker, "cancelar", fake_cancelar)

    # Boton visible (estamos simulando que la ejecucion arranco).
    vista.btn_cancelar.show()

    vista._cancelar_ejecucion()

    assert cancelado["flag"] is True, "Esperaba que cancelar() fuera llamado."
    assert vista.btn_cancelar.isEnabled() is False, (
        "El boton debe deshabilitarse para evitar doble click."
    )
    assert "Cancelando" in vista.estado.text(), (
        f"Estado no actualizado: {vista.estado.text()!r}"
    )


# ============================================================
# Confirmacion No -> NO cancelar()
# ============================================================

def test_cancelar_rechazado_no_llama_cancelar(
    vista: "VistaEjecucion", monkeypatch,
) -> None:
    """No -> worker.cancelar() NO se llama y el boton sigue habilitado."""
    from ui.ventanas.ejecutar_proceso import WorkerEjecucion
    from procesos.fierro import ProcesoFierro

    def fake_question(*args, **kwargs):
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))

    vista._worker = WorkerEjecucion(ProcesoFierro(), [], modo_prueba=True)
    monkeypatch.setattr(vista._worker, "isRunning", lambda: True)

    cancelado = {"flag": False}

    def fake_cancelar() -> None:
        cancelado["flag"] = True

    monkeypatch.setattr(vista._worker, "cancelar", fake_cancelar)

    vista.btn_cancelar.show()
    vista._cancelar_ejecucion()

    assert cancelado["flag"] is False, (
        "Si el usuario dijo No, NO se debe llamar cancelar()."
    )
    assert vista.btn_cancelar.isEnabled() is True, (
        "El boton debe seguir enabled para permitir otro intento."
    )


# ============================================================
# _on_terminado / _on_error: ocultar + reset enabled
# ============================================================

def test_on_terminado_oculta_btn_cancelar(
    vista: "VistaEjecucion", monkeypatch,
) -> None:
    """Al terminar OK, el boton cancelar debe ocultarse y re-habilitarse."""
    from procesos.base import ResultadoProceso
    from PySide6.QtWidgets import QMessageBox as MB

    # Silenciar dialogs que se abririan offscreen pero pueden colgarse.
    monkeypatch.setattr(MB, "information", staticmethod(lambda *a, **k: MB.StandardButton.Ok))
    # invalidar_cache_obtener_ultimo tambien lo parcheamos por seguridad.
    import utils.bitacora as _bit
    monkeypatch.setattr(
        _bit, "invalidar_cache_obtener_ultimo",
        lambda: None,
        raising=False,
    )

    # Simulamos estado "ejecutando".
    vista.btn_cancelar.show()
    vista.btn_cancelar.setEnabled(False)
    vista.btn_ejecutar.setEnabled(False)

    resultado = ResultadoProceso(
        exito=True,
        mensaje="ok",
        archivos_salida=[],
    )

    vista._on_terminado(resultado)

    assert vista.btn_cancelar.isVisible() is False
    assert vista.btn_cancelar.isEnabled() is True
    assert vista.btn_ejecutar.isEnabled() is True


def test_on_error_oculta_btn_cancelar(vista: "VistaEjecucion", monkeypatch) -> None:
    """Al fallar, el boton cancelar tambien debe ocultarse y re-habilitarse."""
    # Sin parchar QMessageBox.critical, la UI intentaria abrir un dialog.
    # En offscreen igual no falla, pero lo parchamos por higiene.
    from PySide6.QtWidgets import QMessageBox as MB
    monkeypatch.setattr(MB, "critical", staticmethod(lambda *a, **k: MB.StandardButton.Ok))

    vista.btn_cancelar.show()
    vista.btn_cancelar.setEnabled(False)
    vista.btn_ejecutar.setEnabled(False)

    vista._on_error("Boom")

    assert vista.btn_cancelar.isVisible() is False
    assert vista.btn_cancelar.isEnabled() is True
    assert vista.btn_ejecutar.isEnabled() is True
    assert "[ERROR]" in vista.estado.text()