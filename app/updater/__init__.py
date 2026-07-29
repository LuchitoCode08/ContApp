"""Sistema de auto-actualizacion de ContApp.

Componentes:
- ``version_utils``: comparar versiones semver y parsear releases de GitHub.
- ``checker``: UpdaterChecker (QThread) que consulta si hay una version
  nueva disponible en GitHub Releases.
- ``downloader``: UpdaterDownloader (QThread) que descarga el instalador
  con progreso.

El updater NO actualiza automaticamente: solo notifica al usuario y,
si el usuario acepta, descarga + lanza el instalador.
"""
from __future__ import annotations
