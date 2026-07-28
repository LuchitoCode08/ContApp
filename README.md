# ContApp — Sistema de Automatización Contable

App de escritorio en Python que automatiza 3 procesos manuales de la oficina de contabilidad de la universidad:

1. **Generar Comprobante** — desde extractos bancarios en ZIP (CSVs adentro) genera 2 Excel.
2. **Interfaz Fierro** — depura extractos. Entrada ZIP con CSVs, salida 2 Excel.
3. **Interfaz Zeus** — depura extractos. Entrada 1 Excel, salida mismo Excel depurado. *(actualmente en desarrollo)*

## Stack

- **Python 3.14.3**
- **PySide6** — interfaz gráfica
- **Pandas + Openpyxl** — procesamiento de datos
- **Pytest** — pruebas
- **PyInstaller** — empaquetado a `.exe`

## Interfaz gráfica

La app se compone de una **ventana principal** con sidebar de navegación y 4 pantallas.

### Sidebar (4 secciones)

- **Inicio** — dashboard con tarjetas de los 3 procesos y panel "Último ejecutado".
- **Procesos** — grid de procesos disponibles → vista de ejecución (DropZone + lista + ejecutar + resultados).
- **Diccionarios** — editor visual de las reglas (JSONs editables con backup automático).
- **Configuración** — usuario activo, modo de prueba, tema y datos del sistema.

### Footer / estado

Switch de **modo prueba**, nombre de **usuario activo** y selector de **tema** (claro / oscuro).

### Características de UI

- 🎨 **Tema claro/oscuro** — `ui/recursos/tema.py` con paleta dinámica. Se aplica a toda la app y se persiste en `data/usuario.json`.
- 🟡 **Modo prueba** — banner amarillo visible cuando está activo; los archivos se escriben en `resultados/<proceso>/_prueba_YYYY-MM/` con sufijo `_prueba` en el nombre.
- 🧪 **Badge "EN DESARROLLO"** — los procesos no listos se ven con opacidad reducida, badge ámbar y click bloqueado.
- 💾 **Persistencia** — usuario, modo prueba y tema se guardan en `data/usuario.json` y se restauran al arrancar.
- 🖱️ **Cursor mano** sobre items clickeables (sidebar, tarjetas, botones primarios).
- 📋 **DropZone** para arrastrar archivos (con fallback "Examinar").
- 📊 **Tabla de resultados** con los archivos generados y botón "Abrir carpeta".

## Estructura

```
Demo/
├── main.py                      # Entry point (lanza la QApplication)
├── requirements.txt
│
├── app/                         # Configuración y arranque
│   ├── __init__.py
│   └── config.py                # Singleton Config (rutas, usuario, modo_prueba, tema)
│
├── procesos/                    # Lógica de los 3 procesos + receta base
│   ├── __init__.py
│   ├── base.py                  # ProcesoBase abstracta
│   ├── comprobante.py
│   ├── fierro.py
│   └── zeus.py                  # EN_DESARROLLO = True
│
├── ui/                          # Interfaz gráfica (no sabe de Pandas)
│   ├── ventanas/                # Pantallas principales
│   │   ├── principal.py         # VentanaPrincipal + PantallaInicio
│   │   ├── ejecutar_proceso.py  # PantallaProcesos (grid + ejecución)
│   │   └── (otros…)
│   ├── widgets/                 # Componentes reutilizables
│   │   ├── drop_zone.py
│   │   ├── tarjeta_proceso.py
│   │   ├── switch_modo_prueba.py
│   │   ├── banner_modo_prueba.py
│   │   └── tabla_resultados.py
│   └── recursos/
│       └── tema.py              # Paleta + estilos (light/dark)
│
├── utils/                       # Herramientas de apoyo
│   ├── archivos.py              # Manejo de carpetas mensuales
│   ├── bitacora.py              # Logger a archivo + consola
│   └── json_manager.py          # CRUD JSON con backup
│
├── jsons/                       # Reglas editables (dentro del programa)
│   ├── comprobante/             # 4 JSONs (FOAPAL, NIT Bancolombia, códigos)
│   ├── fierro/                  # 3 JSONs (mapeos auxiliares/descripciones/tarjetas)
│   └── zeus/                    # 1 JSON (auxiliares Zeus)
│
├── data/                        # Estado y datos persistentes
│   ├── backups/                 # Respaldos automáticos de JSONs
│   ├── bitacora/                # Logs históricos
│   └── usuario.json             # Preferencias del usuario actual
│
├── resultados/                  # Salidas (fuera del programa, ver Config)
│   ├── comprobante/
│   ├── fierro/
│   └── zeus/
│
├── log/
│   └── BITACORA.md              # Bitácora de la sesión actual
│
└── tests/                       # 93 tests (pytest)
    ├── test_smoke.py
    ├── test_archivos.py
    ├── test_bitacora.py
    ├── test_json_manager.py
    ├── test_config_persistencia.py
    ├── test_comprobante_e2e.py
    ├── test_fierro_e2e.py
    └── test_zeus_e2e.py         # 4 saltados mientras EN_DESARROLLO=True
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

Estado actual: **89 passed, 4 skipped** (los 4 skipped son de Zeus, mientras esté `EN_DESARROLLO=True`).

## Empaquetado (.exe)

```powershell
pyinstaller --noconfirm --onefile --windowed --name ContApp main.py
```

El `.exe` queda en `dist/ContApp.exe`. La primera vez que se ejecuta crea `data/usuario.json` automáticamente.

## Estado

- ✅ Fase 1 — Preparación del entorno
- ✅ Fase 2 — Núcleo de la app (lógica pura, sin UI)
- ✅ Fase 3 — Interfaz gráfica (PySide6, 4 pantallas, tema claro/oscuro)
- ✅ Fase 4 — Pruebas y ajustes (93 tests, persistencia, modo prueba, badge "EN DESARROLLO")
- ⏳ Fase 5 — Empaquetado con PyInstaller