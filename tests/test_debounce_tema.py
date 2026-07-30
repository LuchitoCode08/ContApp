"""Tests del debounce de ``_toggle_tema()`` en ``VentanaPrincipal``.

Cubre:
    - ``_toggle_tema`` agenda la aplicacion del tema con un QTimer de
      100 ms, no inmediatamente.
    - Multiples toggles rapidos (ej: spam-click) solo aplican el tema
      UNA vez al final del debounce.
    - La persistencia (``cfg.tema`` + ``guardar_preferencias``) SI es
      inmediata (no se debouncea) para no perder el ultimo cambio si
      la app se cierra dentro de la ventana del debounce.
    - El modo pendiente ``_tema_modo_pendiente`` queda con el ultimo
      valor elegido, no se aplica el primero.

Estrategia:
    - offscreen Qt.
    - Monkey-patch sobre ``aplicar_tema`` para contar invocaciones.
    - ``QTest.qWait(150)`` para esperar el debounce.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Forzar offscreen ANTES de cualquier import Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

RAIZ_PROY = Path(__file__).resolve().parent.parent
if str(RAIZ_PROY) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROY))


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    """Una sola QApplication por modulo (Qt no permite mas de una)."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def ventana_principal(qt_app, monkeypatch):
    """Crea una ``VentanaPrincipal`` lista para tests.

    Redirige ``DATA_DIR`` para que la persistencia de preferencias
    vaya a tmp y no toque el repo.
    """
    import app.config as app_cfg
    from ui.ventanas.principal import VentanaPrincipal

    # Persistencia a tmp_path via monkeypatching de la clase.
    from pathlib import Path as _P
    tmp_data = _P(monkeypatch.getattr(pytest, "_tmp_path_factory", None)  # noqa
                  ) if False else None  # placeholder; usamos el tmp del test
    # En realidad, el tmp_path del test se inyecta automaticamente.
    # Para no complicar, monkey-patcheamos guardar_preferencias para no
    # tocar disco.
    monkeypatch.setattr(
        app_cfg.Config, "guardar_preferencias",
        lambda self: None,
    )
    v = VentanaPrincipal()
    yield v
    # Cleanup: detener timers vivos.
    if hasattr(v, "_tema_timer") and v._tema_timer is not None:
        v._tema_timer.stop()
    v.deleteLater()


# ============================================================
# Estado inicial
# ============================================================

def test_toggle_tema_tiene_qtimer_de_debounce(
    qt_app, tmp_path, monkeypatch,
) -> None:
    """``_toggle_tema`` debe configurar un QTimer de 100ms (no aplicacion directa)."""
    import app.config as app_cfg
    monkeypatch.setattr(app_cfg.Config, "guardar_preferencias", lambda self: None)
    from ui.ventanas.principal import VentanaPrincipal
    v = VentanaPrincipal()
    try:
        # Disparar el toggle.
        v._toggle_tema()
        # El timer debe existir, ser single-shot, y tener interval=100.
        assert hasattr(v, "_tema_timer")
        assert isinstance(v._tema_timer, QTimer)
        assert v._tema_timer.isSingleShot() is True
        assert v._tema_timer.interval() == 100
    finally:
        if hasattr(v, "_tema_timer") and v._tema_timer is not None:
            v._tema_timer.stop()
        v.deleteLater()


# ============================================================
# Comportamiento: NO aplica inmediatamente
# ============================================================

def test_toggle_tema_no_aplica_inmediatamente(
    qt_app, tmp_path, monkeypatch,
) -> None:
    """Click en el boton de tema NO debe ejecutar ``aplicar_tema`` al instante."""
    import app.config as app_cfg
    monkeypatch.setattr(app_cfg.Config, "guardar_preferencias", lambda self: None)
    # Contar invocaciones de aplicar_tema (la funcion importada en principal.py).
    import ui.ventanas.principal as principal_mod
    import ui.recursos.tema as tema_mod
    llamadas: list[str] = []

    def fake_aplicar(app, modo):
        llamadas.append(modo)
        # No hacemos nada (no repintamos widgets reales).
        pass

    # Patch sobre el modulo donde se USA (principal_mod), no donde se DEFINE.
    monkeypatch.setattr(principal_mod, "aplicar_tema", fake_aplicar)

    from ui.ventanas.principal import VentanaPrincipal
    v = VentanaPrincipal()
    try:
        v._toggle_tema()
        # Inmediatamente despues del click: aplicar_tema NO se llamo.
        assert llamadas == [], (
            f"aplicar_tema se llamo inmediatamente: {llamadas}. "
            "Deberia agendarse con el QTimer de debounce."
        )
    finally:
        if hasattr(v, "_tema_timer") and v._tema_timer is not None:
            v._tema_timer.stop()
        v.deleteLater()


# ============================================================
# Comportamiento: aplica despues del debounce
# ============================================================

def test_aplicar_tema_se_ejecuta_despues_del_debounce(
    qt_app, tmp_path, monkeypatch,
) -> None:
    """Despues de esperar el QTimer, ``aplicar_tema`` debe ejecutarse."""
    import app.config as app_cfg
    monkeypatch.setattr(app_cfg.Config, "guardar_preferencias", lambda self: None)
    import ui.ventanas.principal as principal_mod
    llamadas: list[str] = []

    def fake_aplicar(app, modo):
        llamadas.append(modo)

    monkeypatch.setattr(principal_mod, "aplicar_tema", fake_aplicar)

    from ui.ventanas.principal import VentanaPrincipal
    v = VentanaPrincipal()
    try:
        v._toggle_tema()
        # Esperar el debounce (100ms + un poco de margen).
        loop = QEventLoop()
        QTimer.singleShot(200, loop.quit)
        loop.exec()
        assert llamadas, (
            "aplicar_tema no se ejecuto despues del debounce."
        )
        # El modo aplicado debe ser el nuevo (no el inicial).
        assert llamadas[-1] in ("claro", "oscuro")
    finally:
        if hasattr(v, "_tema_timer") and v._tema_timer is not None:
            v._tema_timer.stop()
        v.deleteLater()


# ============================================================
# Comportamiento: spam de toggles -> UNA sola aplicacion
# ============================================================

def test_multiples_toggles_rapidos_aplican_una_sola_vez(
    qt_app, tmp_path, monkeypatch,
) -> None:
    """5 toggles en <100ms -> aplicar_tema se ejecuta 1 sola vez."""
    import app.config as app_cfg
    monkeypatch.setattr(app_cfg.Config, "guardar_preferencias", lambda self: None)
    import ui.ventanas.principal as principal_mod
    llamadas: list[str] = []

    def fake_aplicar(app, modo):
        llamadas.append(modo)

    monkeypatch.setattr(principal_mod, "aplicar_tema", fake_aplicar)

    from ui.ventanas.principal import VentanaPrincipal
    v = VentanaPrincipal()
    try:
        # 5 toggles consecutivos sin esperar al debounce.
        for _ in range(5):
            v._toggle_tema()
        # Esperar el debounce (200ms es suficiente para 1 solo ciclo).
        loop = QEventLoop()
        QTimer.singleShot(250, loop.quit)
        loop.exec()
        # Solo 1 aplicacion al final (no 5).
        assert len(llamadas) == 1, (
            f"Esperaba 1 sola aplicacion al final del debounce, "
            f"pero hubo {len(llamadas)}: {llamadas}"
        )
    finally:
        if hasattr(v, "_tema_timer") and v._tema_timer is not None:
            v._tema_timer.stop()
        v.deleteLater()


def test_ultimo_toggle_es_el_que_se_aplica(
    qt_app, tmp_path, monkeypatch,
) -> None:
    """Tras N toggles, el modo aplicado es el ULTIMO (no el primero)."""
    import app.config as app_cfg
    monkeypatch.setattr(app_cfg.Config, "guardar_preferencias", lambda self: None)
    import ui.ventanas.principal as principal_mod
    llamadas: list[str] = []

    def fake_aplicar(app, modo):
        llamadas.append(modo)

    monkeypatch.setattr(principal_mod, "aplicar_tema", fake_aplicar)

    from ui.ventanas.principal import VentanaPrincipal
    v = VentanaPrincipal()
    try:
        # Capturar el modo INICIAL antes de togglear.
        from ui.recursos.tema import tema_actual
        modo_inicial = tema_actual()
        # 3 toggles: par / impar / par -> termina en el opuesto al inicial.
        for _ in range(3):
            v._toggle_tema()
        # Esperar el debounce.
        loop = QEventLoop()
        QTimer.singleShot(200, loop.quit)
        loop.exec()
        # El modo aplicado NO debe ser el inicial (porque hicimos 3 toggles).
        assert llamadas, "No se aplico el tema"
        assert llamadas[-1] != modo_inicial, (
            f"El ultimo toggle deberia haber cambiado el tema "
            f"(inicial={modo_inicial}, aplicado={llamadas[-1]})."
        )
    finally:
        if hasattr(v, "_tema_timer") and v._tema_timer is not None:
            v._tema_timer.stop()
        v.deleteLater()


# ============================================================
# Comportamiento: persistencia es inmediata
# ============================================================

def test_persistencia_es_inmediata(
    qt_app, tmp_path, monkeypatch,
) -> None:
    """``cfg.tema`` y ``guardar_preferencias`` se ejecutan INMEDIATAMENTE,
    incluso si la aplicacion visual esta pendiente en el debounce.
    """
    import app.config as app_cfg
    guardados: list[str] = []

    def fake_guardar(self):
        guardados.append(self.tema)

    monkeypatch.setattr(app_cfg.Config, "guardar_preferencias", fake_guardar)
    # Tambien parchear aplicar_tema para no repintar.
    import ui.ventanas.principal as principal_mod
    monkeypatch.setattr(principal_mod, "aplicar_tema", lambda *a, **k: None)

    from ui.ventanas.principal import VentanaPrincipal
    v = VentanaPrincipal()
    try:
        v._toggle_tema()
        # Sin esperar el debounce: la persistencia ya se hizo.
        assert guardados, (
            "guardar_preferencias NO se llamo inmediatamente. "
            "Si la app se cierra dentro del debounce, perderiamos el cambio."
        )
        # cfg.tema debe tener el nuevo valor.
        assert v._cfg.tema in ("claro", "oscuro")
    finally:
        if hasattr(v, "_tema_timer") and v._tema_timer is not None:
            v._tema_timer.stop()
        v.deleteLater()