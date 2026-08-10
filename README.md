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
- 🟡 **Modo prueba** — banner amarillo visible cuando está activo; los archivos se escriben en `%USERPROFILE%\Documents\ContApp_Resultados/<proceso>/_prueba_YYYY-MM/` con sufijo `_prueba` en el nombre.
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
├── ContApp.spec                 # PyInstaller spec (--onedir, console=False)
├── ContApp.iss                  # Inno Setup script (instalador .exe)
├── .github/
│   └── workflows/
│       ├── tests.yml            # CI: tests en cada PR
│       └── release.yml          # CD: build + release al pushear tag v*
│
├── app/                         # Configuración y arranque
│   ├── __init__.py
│   ├── config.py                # Singleton Config (rutas, usuario, modo_prueba, tema)
│   ├── version.py               # __version__ (single source of truth)
│   └── updater/                 # Sistema de auto-actualizacion
│       ├── version_utils.py     # semver, parsear_release
│       ├── checker.py           # UpdaterChecker (QThread)
│       └── downloader.py        # UpdaterDownloader (QThread)
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
│   │   ├── dialogo_actualizacion.py  # Modal de actualizacion (UpdaterDownloader)
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
├── services/                    # Servicios registrados en el contenedor DI
│   ├── settings_service.py      # Persistencia de preferencias
│   ├── backup_service.py        # Política de backups de JSONs
│   └── reporte_service.py       # Reporte de ejecución
│
├── events/                      # Bus de eventos pub/sub thread-safe
│   ├── bus.py                   # EventBus singleton
│   └── eventos.py               # Dataclasses de eventos
│
├── jsons/                       # Reglas editables (dentro del programa)
│   ├── comprobante/             # 4 JSONs (FOAPAL, NIT Bancolombia, códigos)
│   ├── fierro/                  # 3 JSONs (mapeos auxiliares/descripciones/tarjetas)
│   └── zeus/                    # 1 JSON (auxiliares Zeus)
│
├── data/                        # Estado y datos persistentes
│   ├── backups/                 # Respaldos automáticos de JSONs
│   └── usuario.json             # Preferencias del usuario actual
│
├── log/                         # Registros de la app
│   ├── bitacora.log             # Log automático (rotación por fecha)
│   └── BITACORA.md              # Bitácora de la sesión actual
│
├── tests/                       # Suite de pytest
│   ├── test_smoke.py
│   ├── test_archivos.py
│   ├── test_bitacora.py
│   ├── test_json_manager.py
│   ├── test_config_persistencia.py
│   ├── test_config_paths.py     # sys.frozen, RAIZ, JSONS_DIR
│   ├── test_comprobante_e2e.py
│   ├── test_fierro_e2e.py
│   ├── test_zeus_e2e.py         # 4 saltados mientras EN_DESARROLLO=True
│   ├── test_version_utils.py    # semver, comparacion, parsear_release
│   ├── test_updater_checker.py  # UpdaterChecker + URL mockeada
│   └── test_updater_downloader.py  # UpdaterDownloader + chunks
│
├── scripts/                     # Scripts auxiliares de build y verificación
│   └── build/                   # Scripts del bundle portable
│       ├── build_portable_zip.py
│       ├── check_zip.py
│       └── verify_zip_final.py
│
└── docs/                        # Documentación del proyecto
    └── context.md               # Documento de contexto del proyecto
```

> **Nota:** los resultados NO viven en el repo. Ver tabla "Ubicaciones importantes" abajo.

### Ubicaciones importantes (fuera del repo)

| Recurso | Ruta | Definido en |
|---|---|---|
| Outputs de procesos | `%USERPROFILE%\Documents\ContApp_Resultados\` | `app/config.py:RESULTADOS_DIR` |
| Preferencias del usuario | `<repo>/data/usuario.json` | `app/config.py:PREFERENCIAS` |
| Log automático | `<repo>/log/bitacora.log` | `app/config.py:BITACORA_LOG` |
| Backups de JSONs | `<repo>/data/backups/` | `utils/json_manager.py` |

> `RESULTADOS_DIR` está fuera del repo a propósito: cada usuario de Windows tiene su propia carpeta en `Documents\`, evitando mezclar outputs cuando se clona el proyecto en otra máquina.

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

La primera vez que se ejecuta crea `data/usuario.json` automáticamente (tema, modo prueba, usuario activo).

## Pruebas

```powershell
python -m pytest
```

Estado actual: **153 passed, 4 skipped** (los 4 skipped son los tests de ejecución de Zeus, mientras `EN_DESARROLLO=True`).

## Empaquetado y release

El proyecto se empaqueta con **PyInstaller** (modo `--onedir`) y se distribuye con un instalador generado por **Inno Setup**. Hay un workflow de GitHub Actions que automatiza todo el pipeline.

### Pipeline

```
tag v1.0.1
    │
    ▼
GitHub Actions (.github/workflows/release.yml)
    │
    ├─ PyInstaller  ──►  dist/ContApp/      (bundle con .exe + DLLs + jsons/)
    │
    └─ Inno Setup   ──►  dist/ContApp_Setup-1.0.1.exe  (instalador)
                       └►  dist/ContApp-1.0.1-portable.zip  (alternativa)
    │
    ▼
GitHub Release con los 2 assets
```

### Build local

**1) Instalar Inno Setup** (solo Windows): [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php).

**2) Build del bundle:**
```powershell
pyinstaller --clean ContApp.spec
```
Resultado: `dist/ContApp/ContApp.exe` + `dist/ContApp/_internal/` (170 MB total).

**3) Build del instalador:**
```powershell
iscc /DMyAppVersion=1.0.0 ContApp.iss
```
Resultado: `dist/ContApp_Setup-1.0.0.exe` (instalador para distribuir).

**4) Build completo con un solo script:**
```powershell
.\scripts\build\build_release.ps1 -Version 1.0.1
```
Ejecuta tests, PyInstaller, ZIP portable y el instalador. Requiere Inno Setup instalado; si no, usar `-SkipInstaller`.

**5) Distribuir:**
- **Instalador** (recomendado): `dist/ContApp_Setup-1.0.1.exe` — crea acceso directo en Menú Inicio, registra desinstalador.
- **Portable**: `dist/ContApp-1.0.1-portable.zip` — descomprimir y ejecutar `ContApp.exe`.

### Release automático

```powershell
git tag v1.0.0
git push origin v1.0.0
```

El workflow `release.yml` se dispara solo con tags `v*.*.*`. Lee la versión de `app/version.py` y rechaza el tag si no coincide. Genera un **draft release** en GitHub con el instalador y la versión portable como assets.

### Estructura del bundle

```
dist/ContApp/
├── ContApp.exe             # Ejecutable (9 MB)
├── _internal/              # DLLs + modulos Python + dependencias (160 MB)
└── jsons/                  # JSONs editables (FOAPAL, NIT, auxiliares, etc.)
    ├── comprobante/
    ├── fierro/
    └── zeus/
```

**Importante**: `jsons/` se distribuye **al lado del .exe** (no dentro de `_internal/`) para que el usuario pueda editarlos desde la app sin recompilar. El instalador los copia en `data/` con permisos de escritura para el usuario.

### Auto-actualización desde la app

La propia app puede verificar si hay una versión nueva:

- Al iniciar (silencioso): chequea GitHub API; si hay update, abre un diálogo modal.
- Botón "🔄 Actualizar" en el footer: chequeo manual con feedback inmediato.

Ver `app/updater/` para la implementación. El updater consulta `https://api.github.com/repos/LuchitoCode08/ContApp/releases/latest` (gratis, sin auth, ~60 requests/hora por IP).

## Estado

- ✅ Fase 1 — Preparación del entorno
- ✅ Fase 2 — Núcleo de la app (lógica pura, sin UI)
- ✅ Fase 3 — Interfaz gráfica (PySide6, 4 pantallas, tema claro/oscuro, badge EN DESARROLLO)
- ✅ Fase 4 — Pruebas y ajustes (153 tests, persistencia, modo prueba, botón secundario)
- ✅ Fase 5 — Empaquetado y release (PyInstaller + Inno Setup + GitHub Actions + auto-updater)