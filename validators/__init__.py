"""Validadores de ContApp.

Clases que encapsulan las reglas de validacion:
- ``ValidadorArchivos``: cantidad y extension de los archivos de entrada.
- ``ValidadorReglas``: consistencia de los JSONs de reglas (claves
  duplicadas, tipos de valor incorrectos, etc).

Los validadores NO hacen I/O (reciben los datos ya cargados por un
repositorio) y NO lanzan excepciones: devuelven ``True``/``False`` y un
mensaje de error legible.

Anadido en el refactor v2 (Fase 1: infraestructura).
"""
from __future__ import annotations
