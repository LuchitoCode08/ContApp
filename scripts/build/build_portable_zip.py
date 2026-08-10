"""Crea el ZIP portable del bundle PyInstaller.

Uso:
    .venv\\Scripts\\python.exe scripts\\build\\build_portable_zip.py [version]

Ejemplo:
    .venv\\Scripts\\python.exe scripts\\build\\build_portable_zip.py 1.0.1

Salida:
    dist/ContApp-{version}-portable.zip
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea el ZIP portable de ContApp")
    parser.add_argument(
        "version",
        nargs="?",
        default=None,
        help='Versión para el nombre del ZIP (ej: 1.0.1). Default: "ContApp_portable.zip"',
    )
    args = parser.parse_args()

    src_dir = Path("dist") / "ContApp"
    if not src_dir.exists():
        print(f"✗ No se encontró el bundle: {src_dir.resolve()}")
        return 1

    # Asegurar que jsons/ quede al lado del .exe en el bundle portable,
    # ademas de (o en lugar de) _internal/jsons. Asi el usuario puede
    # editar las reglas sin tener que abrir _internal/.
    jsons_src = Path("jsons")
    jsons_dst = src_dir / "jsons"
    if jsons_src.exists():
        if jsons_dst.exists():
            shutil.rmtree(jsons_dst)
        shutil.copytree(jsons_src, jsons_dst)
        print(f"Copied jsons to bundle root: {jsons_dst}")

    if args.version:
        zip_path = Path("dist") / f"ContApp-{args.version}-portable.zip"
    else:
        zip_path = Path("dist") / "ContApp_portable.zip"

    if zip_path.exists():
        zip_path.unlink()

    shutil.make_archive(str(zip_path.with_suffix("")), "zip", src_dir.parent, src_dir.name)

    print(f"Created ZIP: {zip_path}")
    print(f"Size: {zip_path.stat().st_size} bytes")

    with zipfile.ZipFile(zip_path) as zf:
        entries = [f for f in zf.namelist() if f.lower().endswith("contapp.exe")]
        print(f"ContApp.exe entries: {entries}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
