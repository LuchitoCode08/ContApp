# Guía del Agente para ContApp

> Este documento describe la arquitectura, convenciones y estado actual de **ContApp** para cualquier agente de IA (o desarrollador) que vaya a trabajar en el proyecto. Actualízalo siempre que cambie una convención fundamental.

---

## 1. Visión general del proyecto

**ContApp** es una aplicación de escritorio en Python que automatiza tres procesos manuales de la oficina de contabilidad de una universidad:

1. **Generar Comprobante** — recibe uno o varios archivos ZIP con CSVs de Bancolombia y genera dos archivos Excel (un comprobante de cinco hojas y un archivo FOAPAL).
2. **Interfaz Fierro** — depura un Excel de Fierro siguiendo el instructivo KM5 y agrega las hojas `Diario 2026 - Copia` y `Comprobante`.
3. **Interfaz Zeus** — depura un Excel de Zeus con la hoja `Exportar`. **Actualmente en desarrollo** (`EN_DESARROLLO = True`) y bloqueado en la UI.

La app está pensada para dos usuarios de la oficina de contabilidad, cada uno con sus propios archivos y reglas JSON. La versión actual del repositorio es **1.0.3** (única fuente de verdad: `app/version.py`).

---

## 2. Stack tecnológico

| Capa | Tecnología | Notas |
|------|------------|-------|
| Lenguaje | **Python 3.14.3** |  |
| GUI | **PySide6** ≥ 6.11 | Qt6, widgets nativos de Windows |
| Procesamiento de datos | **pandas** ≥ 3.0, **openpyxl** ≥ 3.1 |  |
| Empaquetado | **PyInstaller** ≥ 6.10 | Modo `--onedir` |
| Instalador | **Inno Setup 6/7** | Script: `ContApp.iss`; soporta IS 6 y IS 7 |
| Tests | **pytest** ≥ 9.0 |  |
| Dependencia adicional | **pyodc** ≥ 1.5.0 | Requerida indirectamente por pyarrow/pandas; hay scripts de verificación que confirman que se bundlea |

No se usa `pyproject.toml`, `package.json` ni otro manifiesto de metadatos: el proyecto se describe con `requirements.txt` y los scripts de build (`ContApp.spec`, `ContApp.iss`).

---

## 3. Estructura de carpetas y módulos principales

```
Demo/
├── main.py                     # Punto de entrada (UI por defecto, --cli para terminal)
├── requirements.txt            # Dependencias
├── ContApp.spec                # Spec de PyInstaller (--onedir, console=False)
├── ContApp.iss                 # Script de Inno Setup para el instalador .exe
├── README.md                   # Documentación pública
│
├── app/                        # Configuración, arranque y versionado
│   ├── config.py               # Singleton de Config + rutas (RAIZ, JSONS_DIR, RESULTADOS_DIR, etc.)
│   ├── version.py              # __version__, APP_NAME, GITHUB_REPO
│   ├── bootstrap.py            # Registra servicios en el contenedor DI
│   ├── container.py            # Mini contenedor de inyección de dependencias
│   └── updater/                # Auto-actualización (checker/downloader/version_utils)
│
├── procesos/                   # Lógica pura de negocio (sin dependencia de UI)
│   ├── base.py                 # ProcesoBase abstracto + ResultadoProceso + ProcesoCancelado
│   ├── comprobante.py          # ProcesoComprobante
│   ├── fierro.py               # ProcesoFierro
│   └── zeus.py                 # ProcesoZeus (EN_DESARROLLO = True)
│
├── ui/                         # Interfaz gráfica (no sabe de pandas ni openpyxl)
│   ├── recursos/tema.py        # Paleta + QSS global (claro/oscuro)
│   ├── ventanas/               # Pantallas principales
│   │   ├── principal.py        # VentanaPrincipal + sidebar + 5 secciones
│   │   ├── ejecutar_proceso.py # PantallaProcesos + WorkerEjecucion (QThread)
│   │   ├── editor_json.py      # Editor de diccionarios/JSONs
│   │   ├── backups.py          # Gestor de copias de seguridad de JSONs
│   │   ├── configuracion.py    # Bitácora y preferencias
│   │   └── dialogo_actualizacion.py
│   └── widgets/                # Componentes reutilizables (DropZone, tarjetas, switches, etc.)
│
├── utils/                      # Herramientas de apoyo (sin dependencia de UI)
│   ├── archivos.py             # Carpetas mensuales, timestamps, copiar/mover
│   ├── bitacora.py             # Logger + parseo de registros + último proceso
│   └── json_manager.py         # CRUD JSON + backup + restauración + detección de tipo + locks
│
├── services/                   # Servicios registrados en el contenedor DI
│   ├── settings_service.py     # Persistencia de preferencias (reemplaza usuario.json)
│   ├── backup_service.py       # Política de backups de JSONs + restauración
│   └── reporte_service.py      # Reporte de ejecución (logging + dict)
│
├── events/                     # Bus de eventos pub/sub thread-safe
│   ├── bus.py                  # EventBus singleton
│   └── eventos.py              # Dataclasses de eventos (ProcesoIniciado, ProgresoProceso, etc.)
│
├── jsons/                      # Reglas editables (1 carpeta por proceso)
│   ├── comprobante/            # 4 JSONs
│   ├── fierro/                 # 3 JSONs
│   └── zeus/                   # 1 JSON
│
├── data/                       # Estado y datos persistentes
│   ├── backups/                # Backups automáticos de JSONs
│   ├── bitacora/bitacora.log   # Log automático (ignorado en git)
│   └── settings.json           # Preferencias del usuario (ignorado en git)
│
├── log/                        # Logs de sesión y bitácora legible
│   ├── bitacora.log
│   └── BITACORA.md
│
├── tests/                      # Suite de pytest
│   └── ...                     # Ver sección de tests
│
├── .github/workflows/           # CI/CD
│   ├── tests.yml               # Tests en cada push/PR a main
│   └── release.yml             # Build + release al pushear tag v*.*.*
│
├── scripts/                    # Scripts auxiliares de build y verificación
│   └── build/                  # Scripts del bundle PyInstaller
│       ├── build_portable_zip.py
│       ├── check_zip.py
│       └── verify_zip_final.py
│
└── docs/                        # Documentación del proyecto
    └── context.md               # Documento de contexto del proyecto (humano)
```

### Ubicaciones importantes fuera del repositorio

| Recurso | Ruta | Definido en |
|---|---|---|
| Outputs de procesos | `%USERPROFILE%\Documents\ContApp_Resultados\<proceso>\YYYY-Mes\` | `app/config.py:RESULTADOS_DIR` |
| Preferencias del usuario | `<repo>/data/settings.json` | `app/config.py:PREFERENCIAS` |
| Log automático | `<repo>/data/bitacora/bitacora.log` | `app/bootstrap.py` |
| Backups de JSONs | `<repo>/data/backups/` | `services/backup_service.py` |

`RESULTADOS_DIR` vive fuera del repo a propósito para que cada usuario de Windows tenga su propia carpeta y las actualizaciones no borren sus datos.

---

## 4. Arquitectura y principios de diseño

### Separación core / UI ("cocina vs comedor")

- **`procesos/` + `utils/` + `services/`** = la lógica de negocio. **No importan ni saben de PySide6 ni de widgets.**
- **`ui/`** = la interfaz visual. **No importa pandas ni openpyxl.**
- La conexión es a través de la firma `ProcesoBase.ejecutar(archivos, modo_prueba, progreso=..., cancelado=...)`. La UI instancia la clase concreta, valida, ejecuta en un `QThread` (`WorkerEjecucion`) y muestra los resultados.

Esta separación permite que en el futuro se reemplace la UI de escritorio por un portal web sin tocar la lógica de negocio.

### Patrón de procesos

Cada proceso hereda de `ProcesoBase` (`procesos/base.py`) y debe implementar:

- `nombre` y `descripcion` (properties)
- `extensiones_entrada` y `extensiones_salida` (properties)
- `validar_archivos(archivos) -> str | None`
- `ejecutar(archivos, modo_prueba=False, *, progreso=None, cancelado=None) -> ResultadoProceso`

La cancelación cooperativa usa el callback `cancelado` y la excepción `ProcesoCancelado`. Los procesos largos deben revisar `cancelado()` cada ciertas filas (idealmente cada 100).

### Inyección de dependencias (refactor v2)

- `app/container.py` implementa un mini DI propio con registro de factories, lazy instantiation y singletons. No se usa ninguna librería externa para no aumentar el tamaño del build.
- `app/bootstrap.py` registra los servicios por defecto (`settings`, `bitacora`, `backup_service`, `reporte_service`).
- `services/settings_service.py` es la nueva fuente de verdad de preferencias y migra automáticamente `data/usuario.json` a `data/settings.json` si existe el legacy.

### Bus de eventos

- `events/bus.py` ofrece un `EventBus` thread-safe para desacoplar emisores y consumidores.
- `events/eventos.py` define los eventos inmutables (`ProcesoIniciado`, `ProgresoProceso`, `ProcesoFinalizado`, `ProcesoCancelado`, `JsonEditado`, `TemaCambiado`).
- No reemplaza los signals de Qt; es una capa adicional para futuros plugins y para desacoplar la bitácora.

---

## 5. Los tres procesos

| Proceso | Entrada | Salida | Reglas JSON | Estado |
|---------|---------|--------|-------------|--------|
| `comprobante` | 1+ archivos `.zip` con CSVs | `YYYY-MM NombreMes Bancolombia.xlsx` + `fzrcoco.xlsx` | 5 JSONs en `jsons/comprobante/` | Activo |
| `fierro` | 1 Excel `.xlsx`/`.xls` con hoja `Diario 2026` | El mismo Excel + hojas `Diario 2026 - Copia` y `Comprobante` | 3 JSONs en `jsons/fierro/` | Activo |
| `zeus` | 1 Excel `.xlsx`/`.xls` con hoja `Exportar` | El mismo Excel + hojas `Exportar - Copia` y `Depurado` | 1 JSON en `jsons/zeus/` | **En desarrollo (bloqueado)** |

Los 5 JSONs de `comprobante` son: `codigos_conceptos.json`, `codigos_contables.json`, `foapal.json`, `nit_bancolombia.json` y `codigos_ignorados.json`. El último guarda los códigos que el usuario decide no agregar a FOAPAL, para no volver a alertar en siguientes ejecuciones.

### Tipos de estructura de los JSONs (usadas por el editor)

- **Tipo A — Plano simple:** `{clave: valor}`
- **Tipo B — Secciones con sub-objetos:** `{seccion: {id: {objeto}}}`
- **Tipo C — Secciones con valores mixtos:** `{seccion: {id: string | list}}`
- **Tipo D — Lista de pares:** `{"tarjetas": [[patron, reemplazo], ...]}`

`utils/json_manager.detectar_tipo()` decide la vista del editor.

---

## 6. Archivos de configuración, build y despliegue

- `requirements.txt` — dependencias.
- `ContApp.spec` — config de PyInstaller: `--onedir`, `console=False`, `jsons/` como data adjunto, hidden imports para PySide6 y submódulos propios, exclusiones para reducir tamaño.
- `ContApp.iss` — script de Inno Setup: instala en `%LOCALAPPDATA%\ContApp`, no pide UAC, crea acceso directo en Menú Inicio, preserva `data/` y `jsons/` en upgrades. Compatible con Inno Setup 6 y 7.
- `.github/workflows/tests.yml` — corre pytest en Windows con Python 3.14 en cada push/PR a `main`.
- `.github/workflows/release.yml` — build + release al pushear tag `v*.*.*`. Verifica que el tag coincida con `app/version.py`, corre tests, buildea con PyInstaller, crea instalador con Inno Setup, comprime zip portable y genera un draft release en GitHub.
- `scripts/build/` — scripts auxiliares locales para crear y revisar el bundle portable (`build_portable_zip.py`, `check_zip.py`, `verify_zip_final.py`). No los usa CI; son de uso manual en desarrollo.
- `docs/` — documentación humana del proyecto: `context.md`.

---

## 7. Comandos de build, test y ejecución

### Entorno virtual

El repositorio ya incluye `.venv/`. Para activar desde PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

El Python del venv está en `.venv\Scripts\python.exe`.

### Instalar dependencias

```powershell
pip install --no-cache-dir -r requirements.txt
```

### Ejecutar la app en modo UI

```powershell
python main.py
```

### Ejecutar en modo CLI

```powershell
python main.py --cli --listar
python main.py --cli --proceso comprobante --archivo archivo.zip --modo-prueba
python main.py --cli --proceso fierro --archivo "archivo.xlsx" --modo-prueba
```

### Tests

```powershell
python -m pytest tests/ -v --tb=short
```

También existe un runner de conveniencia:

```powershell
python -m tests.run_all
```

### Build local

```powershell
pyinstaller --clean ContApp.spec
```

Resultado: `dist/ContApp/ContApp.exe` + `dist/ContApp/_internal/`.

### Build del instalador local

Requiere Inno Setup instalado. Desde el directorio del proyecto:

```powershell
iscc /DMyAppVersion=1.0.3 ContApp.iss
```

Resultado: `dist/ContApp_Setup-1.0.3.exe`.

### Build completo local (bundle + portable + instalador)

Hay un script PowerShell que corre todo el pipeline en un solo paso:

```powershell
.\scripts\build\build_release.ps1 -Version 1.0.3
```

Parámetros útiles:
- `-SkipTests` — omite `pytest`.
- `-SkipInstaller` — omite Inno Setup y solo genera el bundle y el ZIP portable.

Resultado esperado en `dist/`:
- `ContApp/ContApp.exe` + `_internal/`
- `ContApp-1.0.3-portable.zip`
- `ContApp_Setup-1.0.3.exe`

### Release automático

```powershell
git tag v1.0.3
git push origin v1.0.3
```

El workflow `release.yml` buildea y crea un draft release en GitHub. El tag debe coincidir con `__version__` en `app/version.py`.

---

## 8. Convenciones de desarrollo

### Idioma

- **Todo el código y los mensajes al usuario deben estar en español.** Nombres de variables, funciones, comentarios, docstrings, excepciones, etc.
- Los identificadores técnicos de Qt (clases, signals, métodos) se respetan en inglés, pero el código propio se escribe en español.

### Estilo y nombres

- Nombres de procesos: `snake_case` (`comprobante`, `fierro`, `zeus`).
- Clases de proceso: `Proceso<Nombre>` (`ProcesoComprobante`).
- Clases de UI: `Pantalla<Seccion>`, `VentanaPrincipal`, `WorkerEjecucion`.
- Constantes: `MAYUSCULAS` (por ejemplo `COL_CUENTA`, `MESES_ES`).
- Usar `from __future__ import annotations` en la mayoría de los módulos para anotaciones modernas.

### Reglas de negocio críticas

1. **Modo prueba siempre visible:** nunca ejecutar un proceso real sin que el usuario sepa si está en modo prueba. El banner naranja es la garantía.
2. **Backup antes de editar JSON:** `utils/json_manager.escribir_json()` hace backup automáticamente; `services/backup_service.py` gestiona la política.
3. **Resultados organizados por mes:** `utils/archivos.carpeta_resultados()` crea `YYYY-Mes` en español.
4. **Resultados separados por proceso:** cada proceso tiene su propia subcarpeta bajo `ContApp_Resultados`.
5. **Mensajes comprensibles:** en español, orientados a usuarios no técnicos.
6. **Bitácora en cada acción:** cada ejecución, edición de JSON y cambio de configuración debe quedar registrado en `data/bitacora/bitacora.log`.

### Threads y UI

- Los procesos se ejecutan en `WorkerEjecucion` (subclase de `QThread`).
- No tocar widgets directamente desde el worker; comunicar por signals (`terminado`, `error`, `progreso`).
- El worker captura `BaseException` y nunca debe cerrar la app por un error interno.

---

## 9. Estrategia de testing

La suite usa **pytest** y está organizada en tests unitarios, de integración y E2E:

- `test_smoke.py` — imports básicos y sanidad.
- `test_archivos.py` — utilidades de manejo de archivos y carpetas mensuales.
- `test_bitacora.py` — logging, parseo de registros, `obtener_ultimo()`, cache.
- `test_json_manager.py` — lectura/escritura JSON, detección de tipo, backups, restauración, locks.
- `test_config_paths.py` y `test_config_persistencia.py` — rutas y persistencia de preferencias.
- `test_backup_service.py` — política de backups y restauración desde el servicio.
- `test_comprobante_e2e.py`, `test_fierro_e2e.py`, `test_zeus_e2e.py` — ejecución real de los procesos con datos sintéticos.
- `test_cancelar_proceso.py` — cancelación cooperativa.
- `test_progreso.py` — emisión de progreso y firma de callbacks.
- `test_editor_json_lazy.py`, `test_configuracion_ui.py`, `test_backups_ui.py`, `test_debounce_tema.py` — UI con `qtbot`.
- `test_version_utils.py`, `test_updater_checker.py`, `test_updater_downloader.py` — updater.

### Estado actual de los tests (última ejecución verificada)

```text
277 passed, 4 skipped, 2 warnings in 11.61s
```

- **4 skipped:** tests de ejecución de Zeus (`test_zeus_e2e.py`) porque `EN_DESARROLLO = True`.
- **2 warnings:** `PytestUnraisableExceptionWarning` al cerrar hojas de openpyxl (`WriteOnlyWorksheet` y `WorksheetWriter`) en `test_fierro_chequea_cancelacion_no_en_cada_fila`; no rompen los tests pero indican un resource leak potencial.
- La inconsistencia del callback `progreso` ya fue resuelta; `tests/test_progreso.py` pasa completamente.

---

## 10. Proceso de despliegue

### Pipeline de release (GitHub Actions)

```
git tag v1.0.3
    │
    ▼
release.yml
    │
    ├─ PyInstaller  ──► dist/ContApp/
    ├─ Inno Setup    ──► dist/ContApp_Setup-1.0.3.exe
    └─ Compress-Archive ──► dist/ContApp-1.0.3-portable.zip
    │
    ▼
GitHub Release (draft) con ambos assets
```

### Bundle de PyInstaller

```
dist/ContApp/
├── ContApp.exe
├── _internal/          # DLLs, Python runtime, dependencias
└── jsons/              # JSONs editables al lado del .exe
```

`jsons/` se distribuye al lado del `.exe` para que el usuario pueda editar las reglas sin recompilar. El instalador los copia en `%LOCALAPPDATA%\ContApp` con permisos de escritura.

### Auto-actualización

- `app/updater/checker.py` consulta `https://api.github.com/repos/LuchitoCode08/ContApp/releases/latest` (sin autenticación, ~60 req/h por IP).
- Si hay una versión nueva, la UI muestra un diálogo con `app/updater/downloader.py` que descarga el instalador por chunks con reporte de progreso.
- El botón de "Actualizar" en el footer permite chequeo manual.

---

## 11. Estado actual del repositorio y problemas conocidos

- **Progreso:** resuelto. El callback `progreso` está restaurado en `ProcesoBase` y en las implementaciones; `WorkerEjecucion` y `tests/test_progreso.py` son coherentes.
- **Preferencias:** resuelto. `data/usuario.json` fue migrado a `data/settings.json` y `app/config.py` delega la persistencia en `SettingsService`.
- **Zeus bloqueado:** la UI no permite ejecutar Zeus porque `ProcesoZeus.EN_DESARROLLO = True`. Los tests de ejecución de Zeus se saltan.
- **Ubicación de `jsons/` en el bundle:** resuelto. `app/config.py` busca `jsons/` al lado del ejecutable y hace fallback a `_internal/jsons/`. `scripts/build/build_portable_zip.py` copia `jsons/` a la raíz del bundle antes de comprimir.
- **pyodc en el bundle:** resuelto. Se instaló `pyodc>=1.5.0` en el entorno virtual y `scripts/build/verify_zip_final.py` confirma que PyInstaller lo incluye (vía `Analysis-00.toc` cuando no aparece como archivo suelto).
- **Compatibilidad con Inno Setup 7:** resuelto. `ContApp.iss` ahora compila correctamente en IS 7 (precedencia de `and` corregida y uso de `ExpandConstant` en lugar de `SetupSetting`).
- **Problema ocasional con openpyxl:** warning de I/O sobre archivo cerrado en tests de cancelación; revisar cierre de `Workbook` write_only.
- **Limpieza:** se eliminaron las carpetas vacías `models/`, `repositories/` y `validators/`, se borró la basura local de `build/`, `dist/`, `__pycache__/` y los logs de desarrollo antiguos en `log/`.

---

## 12. Consideraciones de seguridad

- **Datos del usuario:** no versionar `data/settings.json`, `data/bitacora/bitacora.log`, `data/backups/` ni los resultados de `ContApp_Resultados`. Están en `.gitignore`.
- **GitHub API:** el updater usa la API pública sin autenticación. Para un repo privado habría que cambiar `GITHUB_API_BASE` o añadir token.
- **Instalador:** `ContApp.iss` usa `PrivilegesRequired=lowest` para instalar en `%LOCALAPPDATA%` sin UAC. Si se cambia a `admin`, revisar los permisos de escritura sobre `jsons/` y `data/`.
- **Path traversal:** los procesos escriben en `RESULTADOS_DIR` bajo `%USERPROFILE%\Documents\ContApp_Resultados`. No usan rutas controladas por el usuario directamente, pero cualquier cambio debe mantener el prefijo absoluto y validar extensiones.
- **Backup de JSONs:** el editor hace backup automático antes de sobrescribir. No desactivar este comportamiento.

---

## 13. Cuándo actualizar este archivo

Actualiza este documento cuando:

- Cambie el stack tecnológico o las versiones mínimas.
- Se añada/mueva/elimine un módulo principal o cambie su responsabilidad.
- Se modifique la firma de `ProcesoBase` o el contrato UI ↔ core.
- Cambie el proceso de build, test o release.
- Se resuelva un problema conocido (por ejemplo, el de `progreso` o la migración de settings).

Mantener este archivo actualizado evita que cada agente tenga que re-descubrir el proyecto desde cero.
