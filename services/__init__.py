"""Servicios de ContApp.

Logica de aplicacion de alto nivel, orquestada sobre los repositorios
y validadores. Ejemplos:

- ``ReporteService``: genera el reporte de una ejecucion (archivo +
  resumen para mostrar en la UI).
- ``BackupService``: politica de backups automaticos (cada cuanto, a
  donde, cuantos retener).
- ``SettingsService``: carga/guarda las preferencias del usuario.
- ``EstadisticasService``: contadores de uso (placeholder para v2).

Los servicios NO saben de UI (no instancian widgets) y NO saben de I/O
detallado (delegan en repositorios).

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations
