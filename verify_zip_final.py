import zipfile

zip_path = r'C:\Users\lfloaiza\Documents\Demo\dist\ContApp_portable.zip'

with zipfile.ZipFile(zip_path) as zf:
    all_files = zf.namelist()
    pyodc_files = [f for f in all_files if 'pyodc' in f.lower()]
    
    print('=== ZIP Verification ===')
    print(f'Total files: {len(all_files):,}')
    print(f'pyodc files: {len(pyodc_files)}')
    
    if len(pyodc_files) > 0:
        print()
        print('[OK] pyodc IS bundled in ZIP')
        print('Sample pyodc files:')
        for f in sorted(pyodc_files)[:5]:
            print(f'  - {f}')
    else:
        print()
        print('[ERROR] pyodc is NOT in ZIP')
        print()
        print('Buscando alternativas... findlibs?')
        findlibs = [f for f in all_files if 'findlibs' in f.lower()]
        print(f'findlibs files: {len(findlibs)}')
