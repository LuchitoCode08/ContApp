"""Repositorios de ContApp.

Capa de acceso a datos. Encapsula la lectura/escritura de:
- JSONs de configuracion (``jsons/``).
- Preferencias del usuario (``data/settings.json``).
- Backups automaticos (``data/backups/``).
- Bitacora historica (``data/bitacora/``).

Cada repositorio expone metodos de alto nivel (ej: ``obtener_reglas``,
``guardar_reglas``) y oculta los detalles de I/O, locks y backup.

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations
