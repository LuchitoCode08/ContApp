# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para ContApp.

Build:
    pyinstaller ContApp.spec

Salida:
    dist/ContApp/ContApp.exe + dist/ContApp/_internal/...

Para distribuir: zip de toda la carpeta dist/ContApp/.

Notas de diseno:
    - --onedir (no --onefile): arranca ~3x mas rapido, mejor para debug,
      menos falsos positivos de antivirus.
    - jsons/ NO se bundlea: vive al lado del .exe para que el usuario
      pueda editar las reglas sin recompilar.
    - console=False: ventana de UI pura, sin terminal al hacer doble click.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Donde esta este .spec.
SPEC_DIR = Path(SPECPATH).resolve()
# Donde esta main.py.
APP_DIR = SPEC_DIR

# --------------------------------------------------------------------
# Hidden imports: PyInstaller a veces no detecta imports dinamicos.
# --------------------------------------------------------------------

# PySide6: enumera modulos que se importan dinamicamente (QThread, signals, etc.).
hiddenimports_pyside = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",
]
# Dependencias no detectadas automáticamente por PyInstaller
hiddenimports = (
    collect_submodules("app") + collect_submodules("procesos") + 
    collect_submodules("ui") + collect_submodules("utils") +
    collect_submodules("pyodc") +  # Requerido por pyarrow/pandas
    hiddenimports_pyside
)

# --------------------------------------------------------------------
# Exclusiones: modulos que NO queremos bundlear (reducen tamano y
# posibles conflictos).
# --------------------------------------------------------------------
# PyInstaller ya excluye algunos por defecto (tkinter, test modules).
# Listamos lo que sabemos que no usamos:
excludes = [
    # Tests y dev tools
    "pytest",
    "_pytest",
    "ipython",
    "jupyter",
    # GUI frameworks que no usamos
    "tkinter",
    "wx",
    # Networking pesado que no usamos directamente
    "http.server",
    "xmlrpc",
    # Bases de datos que no usamos
    "sqlite3",
    "dbm",
    # Compilaciones/cientifico no usados
    "numpy.tests",
    "pandas.tests",
    "matplotlib",
    "scipy",
]

# --------------------------------------------------------------------
# a = Analysis
# --------------------------------------------------------------------
a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=[
        # Si jsons/ no esta al lado del .exe en runtime, este fallback
        # lo bundlea. El usuario lo puede editar igual porque el .exe
        # busca primero en su propio directorio.
        (str(APP_DIR / "jsons"), "jsons"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --------------------------------------------------------------------
# EXE (sin ventana de consola en Windows).
# --------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ContApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # <- importante: no ventana de terminal al doble-click
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(APP_DIR / "ui" / "recursos" / "contapp.ico"),  # opcional
)

# --------------------------------------------------------------------
# COLLECT (los DLLs y modulos van en _internal/ al lado del .exe).
# --------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ContApp",
)

# Renombrar para que el contenido sea entendible.
# Resultado: dist/ContApp/ContApp.exe + dist/ContApp/_internal/...
print(f"Spec cargado. Build con: pyinstaller ContApp.spec")
print(f"Salida esperada: dist/ContApp/ContApp.exe")