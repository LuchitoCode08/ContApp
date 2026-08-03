import shutil
from pathlib import Path

src_dir = Path("dist") / "ContApp"
zip_path = Path("dist") / "ContApp_portable.zip"

if zip_path.exists():
    zip_path.unlink()

shutil.make_archive(str(zip_path.with_suffix("")), "zip", src_dir.parent, src_dir.name)

print(f"Created ZIP: {zip_path}")
print(f"Size: {zip_path.stat().st_size} bytes")

import zipfile
with zipfile.ZipFile(zip_path) as zf:
    entries = [f for f in zf.namelist() if f.lower().endswith("contapp.exe")]
    print(f"ContApp.exe entries: {entries}")
