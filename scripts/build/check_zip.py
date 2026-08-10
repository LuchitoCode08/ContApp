"""Verifica que el ZIP portable de ContApp contenga ContApp.exe.

Uso:
    .venv\\Scripts\\python.exe scripts\\build\\check_zip.py [ruta_al_zip]

Si no se pasa ruta, busca el primer dist/ContApp-*-portable.zip.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


def _detectar_zip_default() -> Path:
    dist_dir = Path("dist")
    if dist_dir.exists():
        candidatos = sorted(dist_dir.glob("ContApp-*-portable.zip"))
        if candidatos:
            return candidatos[0]
    return dist_dir / "ContApp_portable.zip"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifica que el ZIP portable contenga ContApp.exe"
    )
    parser.add_argument(
        "zip",
        type=Path,
        nargs="?",
        default=_detectar_zip_default(),
        help="Ruta al ZIP portable (default: dist/ContApp-*-portable.zip)",
    )
    args = parser.parse_args()

    if not args.zip.exists():
        print(f"✗ No se encontró el ZIP: {args.zip.resolve()}")
        return 1

    with zipfile.ZipFile(args.zip) as zf:
        files = zf.namelist()
        has_exe = any("ContApp.exe" in f for f in files)
        has_main = any("main.py" in f for f in files)

        print("=" * 50)
        print("ZIP Contents Analysis")
        print("=" * 50)
        print(f"Total files: {len(files)}")
        print(f"Has ContApp.exe: {has_exe} {'✓ CORRECTO' if has_exe else '✗ INCORRECTO'}")
        print(f"Has main.py (source): {has_main}")
        print()
        print("First 10 entries:")
        for f in files[:10]:
            print(f"  {f}")

        if has_exe:
            print()
            print("✓ ZIP es CORRECTO - contiene el ejecutable compilado")
            return 0
        else:
            print()
            print("✗ ZIP es INCORRECTO - no contiene el .exe")
            return 1


if __name__ == "__main__":
    sys.exit(main())
