import zipfile
from pathlib import Path

zip_path = r"C:\Users\lfloaiza\Documents\Demo\dist\ContApp_portable.zip"

with zipfile.ZipFile(zip_path) as zf:
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
    else:
        print()
        print("✗ ZIP es INCORRECTO - no contiene el .exe")
