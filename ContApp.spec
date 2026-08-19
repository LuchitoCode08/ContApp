# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para ContApp (Versión Simplificada 2.0).

Build:
    pyinstaller --clean ContApp.spec

Salida:
    dist/ContApp/ContApp.exe + dist/ContApp/_internal/... + dist/ContApp/jsons/

Para distribuir: zip de toda la carpeta dist/ContApp/.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Directorio del proyecto
SPEC_DIR = Path(SPECPATH).resolve()
APP_DIR = SPEC_DIR

# --------------------------------------------------------------------
# Hidden imports
# --------------------------------------------------------------------
hiddenimports_pyside = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]

hiddenimports = (
    collect_submodules("app")
    + collect_submodules("core")
    + collect_submodules("ui")
    + collect_submodules("pyodc")
    + hiddenimports_pyside
)

# --------------------------------------------------------------------
# Exclusiones para optimizar el tamaño del ejecutable
# --------------------------------------------------------------------
excludes = [
    "pytest",
    "_pytest",
    "ipython",
    "jupyter",
    "tkinter",
    "wx",
    "http.server",
    "xmlrpc",
    "sqlite3",
    "dbm",
    "numpy.tests",
    "pandas.tests",
    "matplotlib",
    "scipy",
]

# --------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------
a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=[
        (str(APP_DIR / "jsons"), "jsons"),
        (str(APP_DIR / "data"), "data"),
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
# EXE (sin consola en producción)
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# --------------------------------------------------------------------
# COLLECT (Directorio portable)
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