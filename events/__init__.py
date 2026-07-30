"""Eventos y EventBus de ContApp.

El ``EventBus`` es una capa adicional de desacople que se AGREGA encima
de los signals Qt existentes (no los reemplaza). Permite que emisores
(procesos, servicios) y suscriptores (UI, bitacora, plugins futuros)
se comuniquen sin referenciarse mutuamente.

Eventos predefinidos (en ``eventos.py``):
- ``ProcesoIniciado``: una ejecucion empezo.
- ``ProgresoProceso``: actualizacion de progreso (idempotente al signal Qt).
- ``ProcesoFinalizado``: una ejecucion termino (exito o error).
- ``JsonEditado``: el usuario edito un JSON desde el editor.
- ``TemaCambiado``: el usuario cambio el tema visual.

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations
