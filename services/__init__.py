"""Servicios de ContApp.

Logica de aplicacion de alto nivel, orquestada sobre utilidades y
procesos. Ejemplos:

- ``ReporteService``: genera el reporte de una ejecucion (archivo +
  resumen para mostrar en la UI).
- ``BackupService``: politica de backups automaticos. Mantiene **un solo
  backup por JSON** (la ultima version anterior) en ``data/backups/``.
- ``SettingsService``: carga/guarda las preferencias del usuario.

Los servicios NO saben de UI (no instancian widgets) y NO saben de I/O
detallado (delegan en utilidades y procesos).

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations
