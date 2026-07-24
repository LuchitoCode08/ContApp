# ContApp — Sistema de Automatización Contable

App de escritorio en Python que automatiza 3 procesos manuales de la oficina de contabilidad de la universidad:

1. **Generar Comprobante** — desde extractos bancarios en ZIP (CSVs adentro) genera 2 Excel.
2. **Interfaz Fierro** — depura extractos. Entrada ZIP con CSVs, salida 2 Excel.
3. **Interfaz Zeus** — depura extractos. Entrada 1 Excel, salida mismo Excel depurado.

## Stack

- **Python 3.14.3**
- **PySide6** — interfaz gráfica
- **Pandas + Openpyxl** — procesamiento de datos
- **Pytest** — pruebas
- **PyInstaller** — empaquetado a `.exe`

## Estructura

```
contabilidad_app/
├── procesos/                # Lógica de los 3 procesos + receta base
├── ui/                      # Interfaz gráfica (no sabe de Pandas)
├── utils/                   # Herramientas de apoyo (JSON, archivos, bitácora)
├── jsons/                   # Reglas editables (dentro del programa)
├── resultados/              # Salidas (fuera del programa, ver Config)
├── tests/
├── main.py
├── requirements.txt
└── README.md
```

## Instalación

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

```powershell
python main.py
```

## Pruebas

```powershell
python -m pytest
```

## Estado

- ✅ Fase 1 — Preparación del entorno
- ✅ Fase 2 — Núcleo de la app (lógica pura, sin UI)
- ⏳ Fase 3 — Interfaz gráfica
- ⏳ Fase 4 — Pruebas y ajustes
- ⏳ Fase 5 — Empaquetado