"""Verifica que pyodc esté incluido en el ZIP portable de ContApp.

Uso:
    .venv\\Scripts\\python.exe scripts\\build\\verify_zip_final.py [ruta_al_zip]

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
        description="Verifica que pyodc esté presente en el ZIP portable"
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
        print(f"[ERROR] No se encontró el ZIP: {args.zip.resolve()}")
        return 1

    with zipfile.ZipFile(args.zip) as zf:
        all_files = zf.namelist()
        pyodc_files = [f for f in all_files if "pyodc" in f.lower()]

        print("=== ZIP Verification ===")
        print(f"Total files: {len(all_files):,}")
        print(f"pyodc files: {len(pyodc_files)}")

        if len(pyodc_files) > 0:
            print()
            print("[OK] pyodc IS bundled in ZIP")
            print("Sample pyodc files:")
            for f in sorted(pyodc_files)[:5]:
                print(f"  - {f}")
            return 0
        else:
            print()
            print("[ERROR] pyodc is NOT in ZIP")
            print()
            print("Buscando alternativas... findlibs?")
            findlibs = [f for f in all_files if "findlibs" in f.lower()]
            print(f"findlibs files: {len(findlibs)}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
