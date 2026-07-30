"""Contenedor de dependencias de ContApp.

Implementa un mini-DI (inyeccion de dependencias) por registro. La idea:

- ``container.register("clave", factory)`` registra una ``factory`` que
  produce la instancia cuando se pida.
- ``container.get("clave")`` devuelve la instancia (lazy: se crea en el
  primer ``get``).
- ``container.get_singleton("clave")`` siempre devuelve la misma
  instancia.

Para que un modulo reciba sus dependencias sin acoplarse al contenedor
global, las factories reciben el contenedor como argumento:
    container.register("backup_service", lambda c: BackupService(c.get("json_repo")))

Por que un contenedor propio en vez de usar uno externo (python-inject,
dependency-injector): queremos CERO dependencias nuevas para no
disparar el build size del .exe ni el riesgo de incompatibilidad con
PyInstaller.

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations

import threading
from typing import Any, Callable


Factory = Callable[["Container"], Any]


class Container:
    """Mini contenedor de dependencias con soporte lazy + singleton.

    Uso:
        c = Container()
        c.register("bitacora", lambda c: configurar_bitacora(...))
        log = c.get("bitacora")
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._factories: dict[str, Factory] = {}
        self._singletons: dict[str, Any] = {}

    # -- Registro ----------------------------------------------------
    def register(self, clave: str, factory: Factory) -> None:
        """Registra una ``factory`` bajo ``clave``.

        La factory debe aceptar un ``Container`` como argumento y devolver
        la instancia a cachear (lazy o singleton segun se pida).
        """
        with self._lock:
            self._factories[clave] = factory
            # Si ya habia un singleton bajo esta clave, lo limpiamos:
            # la nueva factory manda.
            self._singletons.pop(clave, None)

    # -- Resolucion --------------------------------------------------
    def get(self, clave: str) -> Any:
        """Devuelve una instancia nueva cada vez (lazy)."""
        with self._lock:
            if clave not in self._factories:
                raise KeyError(f"Dependencia '{clave}' no registrada en el container")
            return self._factories[clave](self)

    def get_singleton(self, clave: str) -> Any:
        """Devuelve siempre la misma instancia (lazy)."""
        with self._lock:
            if clave in self._singletons:
                return self._singletons[clave]
            if clave not in self._factories:
                raise KeyError(f"Dependencia '{clave}' no registrada en el container")
            instance = self._factories[clave](self)
            self._singletons[clave] = instance
            return instance

    def has(self, clave: str) -> bool:
        """True si hay una factory registrada bajo ``clave``."""
        with self._lock:
            return clave in self._factories

    # -- Ciclo de vida ------------------------------------------------
    def reset(self) -> None:
        """Limpia singletons (las factories registradas se conservan).

        Pensado para tests que quieren empezar de cero entre casos.
        """
        with self._lock:
            self._singletons.clear()

    def clear(self) -> None:
        """Limpia TODO: factories y singletons. Pensado para tests."""
        with self._lock:
            self._factories.clear()
            self._singletons.clear()


# Singleton de proceso. Los modulos pueden hacer
# ``from app.container import container`` y usar la misma instancia.
container = Container()
