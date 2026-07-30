"""Modelos de dominio de ContApp.

Dataclasses y tipos que representan las entidades del negocio:
- ``MovimientoContable``: una fila de un extracto depurado.
- ``Comprobante``: estructura del comprobante generado.
- ``Regla``: una regla de mapeo cargada desde JSON.

Los modelos son objetos puros (sin logica de UI ni de I/O). Son la
fuente de verdad para los datos que pasan entre procesos, UI y
servicios.

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations
