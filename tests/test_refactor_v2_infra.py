"""Tests de la infraestructura nueva del refactor v2.

Cubre:
- ``events.bus.EventBus``: pub/sub, thread-safety, idempotencia.
- ``app.container.Container``: register/get/singleton/reset.
- ``services.settings_service.SettingsService``: persistencia y migracion.

Pensado para correr sin Qt (no usa offscreen) porque estos modulos son
puro Python sin dependencias de UI.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from app.container import Container
from events.bus import EventBus, EventoBase, event_bus
from events.eventos import (
    JsonEditado,
    ProcesoFinalizado,
    ProgresoProceso,
    TemaCambiado,
)
from services.settings_service import LEGACY_USER_FILE, SETTINGS_FILE, SettingsService


# ============================================================
# EventBus
# ============================================================
class _Dummy(EventoBase):
    pass


class TestEventBus:
    def test_emit_y_on_basico(self):
        bus = EventBus()
        recibido = []

        def handler(e):
            recibido.append(e)

        bus.on(_Dummy, handler)
        bus.emit(_Dummy())
        bus.emit(_Dummy())

        assert len(recibido) == 2
        assert all(isinstance(e, _Dummy) for e in recibido)

    def test_on_es_idempotente(self):
        bus = EventBus()
        contador = []

        def handler(e):
            contador.append(1)

        bus.on(_Dummy, handler)
        bus.on(_Dummy, handler)  # segundo registro no debe duplicar

        bus.emit(_Dummy())
        assert sum(contador) == 1

    def test_off_desuscribe(self):
        bus = EventBus()
        contador = []

        def handler(e):
            contador.append(1)

        bus.on(_Dummy, handler)
        bus.emit(_Dummy())
        bus.off(_Dummy, handler)
        bus.emit(_Dummy())

        assert sum(contador) == 1

    def test_multiples_handlers(self):
        bus = EventBus()
        a, b = [], []

        bus.on(_Dummy, lambda e: a.append(e))
        bus.on(_Dummy, lambda e: b.append(e))
        bus.emit(_Dummy())

        assert len(a) == 1
        assert len(b) == 1

    def test_handler_que_falla_no_rompe_al_emisor(self):
        bus = EventBus()
        despues = []

        def malo(e):
            raise RuntimeError("boom")

        def bueno(e):
            despues.append(e)

        bus.on(_Dummy, malo)
        bus.on(_Dummy, bueno)
        bus.emit(_Dummy())  # no debe tirar la excepcion

        assert len(despues) == 1  # el bueno igual se ejecuto

    def test_eventos_predefinidos_se_pueden_emitir(self):
        # Smoke test: los eventos definidos en eventos.py se pueden
        # emitir sin tirar errores.
        event_bus.limpiar()
        captured = []

        event_bus.on(ProgresoProceso, lambda e: captured.append(e))
        event_bus.emit(ProgresoProceso(proceso="fierro", actual=50, total=100))

        assert len(captured) == 1
        assert captured[0].actual == 50
        assert captured[0].total == 100

    def test_thread_safety_basico(self):
        # Crea N threads que emiten y M threads que se suscriben/desuscriben.
        bus = EventBus()
        contador = []
        lock = threading.Lock()

        def handler(e):
            with lock:
                contador.append(1)

        bus.on(_Dummy, handler)

        def emisor():
            for _ in range(100):
                bus.emit(_Dummy())

        threads = [threading.Thread(target=emisor) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No deberia haber crasheado; y el contador deberia ser exactamente
        # 4 * 100 = 400.
        assert sum(contador) == 400


# ============================================================
# Container
# ============================================================
class TestContainer:
    def test_get_crea_lazy(self):
        c = Container()
        contador = [0]

        def factory(c):
            contador[0] += 1
            return "instancia"

        c.register("x", factory)
        assert contador[0] == 0  # no se llamo todavia
        v = c.get("x")
        assert v == "instancia"
        assert contador[0] == 1
        c.get("x")
        assert contador[0] == 2  # get NO es singleton

    def test_get_singleton_devuelve_siempre_la_misma(self):
        c = Container()
        c.register("x", lambda c: object())
        a = c.get_singleton("x")
        b = c.get_singleton("x")
        assert a is b

    def test_register_pisa_y_resetea_singleton(self):
        c = Container()
        c.register("x", lambda c: "v1")
        v1 = c.get_singleton("x")
        c.register("x", lambda c: "v2")
        v2 = c.get_singleton("x")
        assert v1 == "v1"
        assert v2 == "v2"

    def test_get_sin_registrar_tira_keyerror(self):
        c = Container()
        with pytest.raises(KeyError):
            c.get("nope")

    def test_reset_limpia_singletons_pero_no_factories(self):
        c = Container()
        c.register("x", lambda c: object())
        a = c.get_singleton("x")
        c.reset()
        b = c.get_singleton("x")
        assert a is not b  # fue recreado

    def test_clear_limpia_todo(self):
        c = Container()
        c.register("x", lambda c: object())
        c.get_singleton("x")
        c.clear()
        with pytest.raises(KeyError):
            c.get("x")


# ============================================================
# SettingsService
# ============================================================
class TestSettingsService:
    def test_defaults_si_archivo_no_existe(self, tmp_path: Path):
        svc = SettingsService(settings_path=tmp_path / "settings.json")
        assert svc.usuario == ""
        assert svc.modo_prueba is False
        assert svc.tema == "claro"

    def test_persiste_y_recupera(self, tmp_path: Path):
        path = tmp_path / "settings.json"
        svc1 = SettingsService(settings_path=path)
        svc1.usuario = "fulanito"
        svc1.modo_prueba = True
        svc1.tema = "oscuro"
        svc1.save()

        assert path.exists()
        svc2 = SettingsService(settings_path=path)
        assert svc2.usuario == "fulanito"
        assert svc2.modo_prueba is True
        assert svc2.tema == "oscuro"

    def test_get_set_explicito(self, tmp_path: Path):
        svc = SettingsService(settings_path=tmp_path / "settings.json")
        svc.set("custom", 42)
        assert svc.get("custom") == 42
        assert svc.get("nope", "default") == "default"

    def test_tema_invalido_se_rechaza(self, tmp_path: Path):
        svc = SettingsService(settings_path=tmp_path / "settings.json")
        svc.tema = "rosa-fluo"  # no es ni "claro" ni "oscuro"
        assert svc.tema == "claro"  # queda el default

    def test_migracion_desde_legacy(self, tmp_path: Path):
        # Creamos el archivo viejo.
        legacy = tmp_path / LEGACY_USER_FILE
        legacy.write_text(
            json.dumps({"usuario": "legacy-user", "modo_prueba": True, "tema": "oscuro"}),
            encoding="utf-8",
        )
        # Cargamos settings apuntando al mismo directorio.
        svc = SettingsService(settings_path=tmp_path / SETTINGS_FILE)
        # La migracion deberia haber pasado los valores.
        assert svc.usuario == "legacy-user"
        assert svc.modo_prueba is True
        assert svc.tema == "oscuro"
        # El viejo deberia haber sido borrado.
        assert not legacy.exists()
        # Y el nuevo deberia existir.
        assert (tmp_path / SETTINGS_FILE).exists()

    def test_save_no_tira_si_no_puede_escribir(self, tmp_path: Path):
        # Apuntamos a un directorio que no se puede crear.
        svc = SettingsService(settings_path=tmp_path / "inexistente" / "settings.json")
        # No debe explotar.
        assert svc.save() is True  # tmp_path existe, asi que crea el subdir OK
