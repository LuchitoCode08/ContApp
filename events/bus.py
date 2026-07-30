"""EventBus de ContApp.

Capa de desacople adicional (no reemplaza a los signals Qt existentes).

Uso:
    from events.bus import event_bus
    from events.eventos import ProgresoProceso

    # Suscribirse
    event_bus.on(ProgresoProceso, mi_handler)

    # Publicar
    event_bus.emit(ProgresoProceso(actual=50, total=100))

    # Desuscribirse
    event_bus.off(ProgresoProceso, mi_handler)

El bus es thread-safe (usa un lock). Esta pensado para que los procesos
puedan emitir desde QThreads sin riesgo, y para que la UI y los plugins
futuros se suscriban sin acoplarse a quien emite.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Type


@dataclass(frozen=True)
class EventoBase:
    """Base para todos los eventos del bus.

    Los eventos son dataclasses inmutables (``frozen=True``) para que
    sean seguros de pasar entre threads.
    """


# Tipo del handler: recibe la instancia del evento.
Handler = Callable[[Any], None]


class EventBus:
    """Bus de eventos pub/sub thread-safe.

    Singleton de proceso. No tiene estado por usuario: cualquier modulo
    que importe ``event_bus`` ve la misma instancia.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._suscriptores: dict[Type[EventoBase], list[Handler]] = defaultdict(list)

    def on(self, tipo_evento: Type[EventoBase], handler: Handler) -> None:
        """Suscribe ``handler`` al evento ``tipo_evento``.

        Si el mismo handler se suscribe dos veces al mismo evento, se
        registra una sola vez (idempotente).
        """
        with self._lock:
            if handler in self._suscriptores[tipo_evento]:
                return
            self._suscriptores[tipo_evento].append(handler)

    def off(self, tipo_evento: Type[EventoBase], handler: Handler) -> None:
        """Desuscribe ``handler`` del evento ``tipo_evento``."""
        with self._lock:
            if handler in self._suscriptores[tipo_evento]:
                self._suscriptores[tipo_evento].remove(handler)

    def emit(self, evento: EventoBase) -> None:
        """Publica ``evento``: invoca todos los handlers suscritos.

        Las excepciones en los handlers se capturan y se imprimen a
        stderr para que un handler buggy no rompa al emisor. Esto es
        deseable en un bus desacoplado: el emisor no deberia caer por
        culpa de un consumidor.
        """
        # Tomamos una copia atomica de la lista bajo lock para no
        # sostener el lock mientras se llaman los handlers.
        with self._lock:
            handlers = list(self._suscriptores[type(evento)])
        for h in handlers:
            try:
                h(evento)
            except Exception:
                # Log minimalista: el handler no debe tirar al emisor.
                import sys
                import traceback
                print(
                    f"[EventBus] handler {h!r} fallo en evento "
                    f"{type(evento).__name__}:",
                    file=sys.stderr,
                )
                traceback.print_exc()

    def limpiar(self) -> None:
        """Quita todos los suscriptores. Pensado solo para tests."""
        with self._lock:
            self._suscriptores.clear()

    def contar_suscriptores(self, tipo_evento: Type[EventoBase]) -> int:
        """Cantidad de handlers suscritos a un tipo de evento (para tests)."""
        with self._lock:
            return len(self._suscriptores[tipo_evento])


# Singleton de proceso. Importar ``event_bus`` desde cualquier modulo.
event_bus = EventBus()
