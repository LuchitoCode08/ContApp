<!-- From: C:/Users/lfloaiza/Documents/Demo/AGENTS.md -->
# Guía del Agente para ContApp

> Este documento describe la arquitectura, convenciones y estado actual de **ContApp v2.0** para cualquier agente de IA (o desarrollador) que vaya a trabajar en el proyecto. Actualízalo siempre que cambie una convención fundamental.

---

## 1. Visión general del proyecto

**ContApp** es una aplicación de escritorio en Python que automatiza tres procesos manuales de la oficina de contabilidad de una universidad:

1. **Generar Comprobante** — recibe uno o varios archivos ZIP con CSVs de Bancolombia y genera dos archivos Excel (un comprobante de cinco hojas y un archivo FOAPAL).
2. **Interfaz Fierro** — depura un Excel de Fierro siguiendo el instructivo KM5 y agrega las hojas `Diario 2026 - Copia` y `Comprobante`.
3. **Interfaz Zeus** — depura un Excel de Zeus con la hoja `Exportar`.

La versión actual del repositorio es **2.0.0** (única fuente de verdad: `app/version.py`). Esta versión es una refactorización simplificada: se eliminaron el modo CLI, la bitácora, el actualizador automático, la inyección de dependencias, el instalador y los pipelines de CI/CD.

---

## 2. Stack tecnológico

| Capa | Tecnología | Notas |
|------|------------|-------|
| Lenguaje | **Python 3.14+** |  |
| GUI | **PySide6** ≥ 6.11 | Qt6, widgets nativos de Windows |
| Procesamiento de datos | **pandas** ≥ 3.0, **openpyxl** ≥ 3.1 |  |
| Empaquetado | **PyInstaller** ≥ 6.10 | Modo `--onedir` portable |
| Tests | **pytest** ≥ 9.0 |  |
| Dependencia adicional | **pyodc** ≥ 1.5.0 | Requerida indirectamente por pyarrow/pandas |

No se usa `pyproject.toml`, `package.json` ni otro manifiesto de metadatos: el proyecto se describe con `requirements.txt` y `ContApp.spec`.

---

## 3. Estructura de carpetas y módulos principales

```
Demo/
├── main.py                     # Punto de entrada (solo UI)
├── requirements.txt            # Dependencias
├── ContApp.spec                # Spec de PyInstaller (--onedir, console=False)
├── README.md                   # Documentación pública
├── simple_refactor.md          # Especificación del refactor simplificado
│
├── app/                        # Configuración y versionado
│   ├── __init__.py
│   ├── config.py               # Singleton de Config + rutas (RAIZ, JSONS_DIR, RESULTADOS_DIR, DATA_DIR)
│   └── version.py              # __version__, APP_NAME
│
├── core/                       # Lógica de negocio y utilidades (sin dependencia de UI)
│   ├── __init__.py
│   ├── base.py                 # ProcesoBase abstracto + ResultadoProceso + ProcesoCancelado
│   ├── comprobante.py          # ProcesoComprobante
│   ├── fierro.py               # ProcesoFierro
│   ├── zeus.py                 # ProcesoZeus
│   ├── archivos.py             # Carpetas mensuales, timestamps, copiar/mover
│   └── json_manager.py         # Lectura y escritura simple de JSONs
│
├── events/                     # Bus de eventos pub/sub
│   ├── __init__.py
│   ├── bus.py                  # EventBus singleton
│   └── eventos.py              # Dataclasses de eventos
│
├── jsons/                      # Reglas editables (1 carpeta por proceso)
│   ├── comprobante/            # 5 JSONs
│   ├── fierro/                 # 3 JSONs
│   └── zeus/                   # 1 JSON
│
├── ui/                         # Interfaz gráfica (PySide6)
│   ├── __init__.py
│   ├── recursos/
│   │   └── tema.py             # Tema y estilos QSS (modo claro)
│   ├── ventanas/               # Pantallas principales y diálogos
│   │   ├── principal.py
│   │   ├── inicio.py
│   │   ├── procesos.py
│   │   ├── diccionarios.py
│   │   └── dialogo_codigos_nuevos.py  # Diálogo de códigos de concepto no mapeados (Comprobante)
│   └── widgets/                # Componentes reutilizables (DropZone, SwitchModoPrueba, LogoContApp, etc.)
│
└── tests/                      # Suite de pytest reducida
    ├── __init__.py
    ├── test_archivos.py
    ├── test_comprobante.py
    ├── test_fierro.py
    ├── test_json_manager.py
    └── test_zeus.py
```

### Ubicaciones importantes fuera del repositorio

| Recurso | Ruta | Definido en |
|---|---|---|
| Outputs de procesos | `%USERPROFILE%\Documents\ContApp_Resultados\<proceso>\YYYY-Mes\` | `app/config.py:RESULTADOS_DIR` |
| Preferencias del usuario | `<repo>/data/settings.json` | `app/config.py:PREFERENCIAS` |

`RESULTADOS_DIR` vive fuera del repo a propósito para que cada usuario de Windows tenga su propia carpeta y las actualizaciones no borren sus datos. La carpeta `data/` se crea automáticamente al guardar preferencias y no se versiona.

---

## 4. Arquitectura y principios de diseño

### Separación core / UI ("cocina vs comedor")

- **`core/`** = la lógica de negocio. **No importa ni sabe de PySide6 ni de widgets.**
- **`ui/`** = la interfaz visual. **No importa pandas ni openpyxl.**
- La conexión es a través de la firma `ProcesoBase.ejecutar(archivos, modo_prueba, progreso=..., cancelado=...)`. La UI instancia la clase concreta, valida, ejecuta en un `QThread` (`WorkerEjecucion`) y muestra los resultados.

### Patrón de procesos

Cada proceso hereda de `ProcesoBase` (`core/base.py`) y debe implementar:

- `nombre` y `descripcion` (properties)
- `extensiones_entrada` y `extensiones_salida` (properties)
- `validar_archivos(archivos) -> str | None`
- `ejecutar(archivos, modo_prueba=False, *, progreso=None, cancelado=None) -> ResultadoProceso`

La cancelación cooperativa usa el callback `cancelado` y la excepción `ProcesoCancelado`.

### Configuración global

- `app/config.py` implementa un singleton `Config` simple. No hay inyección de dependencias ni servicios.
- `get_config()` inicializa los procesos y carga/guarda preferencias en `data/settings.json`.
- El modo prueba es un estado global gestionado desde el switch de la topbar.

### Bus de eventos

- `events/bus.py` ofrece un `EventBus` thread-safe para desacoplar emisores y consumidores.
- `events/eventos.py` define los eventos inmutables (`ProcesoIniciado`, `ProgresoProceso`, `ProcesoFinalizado`, `ProcesoCancelado`, `JsonEditado`, `TemaCambiado`).
- No reemplaza los signals de Qt; es una capa adicional para futuras extensiones.

---

## 5. Los tres procesos

| Proceso | Entrada | Salida | Reglas JSON | Estado |
|---------|---------|--------|-------------|--------|
| `comprobante` | 1+ archivos `.zip` con CSVs | `YYYY-MM NombreMes Bancolombia.xlsx` + `fzrcoco.xlsx` | 5 JSONs en `jsons/comprobante/` | Activo |
| `fierro` | 1 Excel `.xlsx`/`.xls` con hoja `Diario 2026` | El mismo Excel + hojas `Diario 2026 - Copia` y `Comprobante` | 3 JSONs en `jsons/fierro/` | Activo |
| `zeus` | 1 Excel `.xlsx`/`.xls` con hoja `Exportar` | El mismo Excel + hojas `Exportar - Copia` y `Comprobante` | 1 JSON en `jsons/zeus/` | Activo |

Los 5 JSONs de `comprobante` son: `codigos_conceptos.json`, `codigos_contables.json`, `foapal.json`, `nit_bancolombia.json` y `codigos_ignorados.json`.

Antes de ejecutar `comprobante`, la app escanea los CSVs en busca de códigos de concepto no mapeados. Si encuentra alguno, muestra un diálogo modal (`ui/ventanas/dialogo_codigos_nuevos.py`) donde el usuario puede:

- **Agregar el código a FOAPAL**, completando Fondo, Organización, Cuenta, Programa y D/C.
- **Ignorar el código**, guardándolo en `codigos_ignorados.json` junto con su descripción.

La decisión se aplica sobre una copia de respaldo previa de `foapal.json` y `codigos_ignorados.json`. La copia se guarda en `data/backups/comprobante/`. Desde la pestaña **Diccionarios** se puede restaurar cualquiera de esos archivos a su último backup con el botón **Restaurar último backup**.

---

## 6. Archivos de configuración y build

- `requirements.txt` — dependencias.
- `ContApp.spec` — config de PyInstaller: `--onedir`, `console=False`, `jsons/` y `data/` como data adjunto, hidden imports para PySide6 y submódulos propios, exclusiones para reducir tamaño.
- No hay instalador ni CI/CD. La distribución es el bundle portable generado por PyInstaller.

---

## 7. Comandos de build, test y ejecución

### Entorno virtual

El repositorio puede usarse con un entorno virtual local en `.venv/`. Para activar desde PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Instalar dependencias

```powershell
pip install --no-cache-dir -r requirements.txt
```

### Ejecutar la app en modo UI

```powershell
python main.py
```

### Tests

```powershell
python -m pytest tests/ -v --tb=short
```

### Build local portable

```powershell
pyinstaller --clean ContApp.spec
```

Resultado: `dist/ContApp/ContApp.exe` + `dist/ContApp/_internal/`.

Para distribuir, comprime toda la carpeta `dist/ContApp/` en un `.zip`.

---

## 8. Convenciones de desarrollo

### Idioma

- **Todo el código y los mensajes al usuario deben estar en español.** Nombres de variables, funciones, comentarios, docstrings, excepciones, etc.
- Los identificadores técnicos de Qt (clases, signals, métodos) se respetan en inglés, pero el código propio se escribe en español.

### Estilo y nombres

- Nombres de procesos: `snake_case` (`comprobante`, `fierro`, `zeus`).
- Clases de proceso: `Proceso<Nombre>` (`ProcesoComprobante`).
- Clases de UI: `Vista<Seccion>`, `VentanaPrincipal`, `WorkerEjecucion`.
- Constantes: `MAYUSCULAS` (por ejemplo `COL_CUENTA`, `MESES_ES`).
- Usar `from __future__ import annotations` en la mayoría de los módulos para anotaciones modernas.

### Reglas de negocio críticas

1. **Modo prueba siempre visible:** nunca ejecutar un proceso real sin que el usuario sepa si está en modo prueba.
2. **Resultados organizados por mes:** `core/archivos.carpeta_resultados()` crea `YYYY-Mes` en español.
3. **Resultados separados por proceso:** cada proceso tiene su propia subcarpeta bajo `ContApp_Resultados`.
4. **Mensajes comprensibles:** en español, orientados a usuarios no técnicos.

### Threads y UI

- Los procesos se ejecutan en `WorkerEjecucion` (subclase de `QObject` ejecutado en `QThread`).
- No tocar widgets directamente desde el worker; comunicar por signals (`terminado`, `error`, `progreso`).
- El worker captura excepciones y nunca debe cerrar la app por un error interno.

---

## 9. Estrategia de testing

La suite usa **pytest** y está reducida a pruebas esenciales:

- `test_archivos.py` — utilidades de manejo de archivos y carpetas mensuales.
- `test_comprobante.py` — lógica del proceso Comprobante.
- `test_fierro.py` — lógica del proceso Fierro.
- `test_zeus.py` — lógica del proceso Zeus.
- `test_json_manager.py` — lectura/escritura JSON.

### Estado actual de los tests

La meta es que la suite reporte **56 passed**:

```text
56 passed in X.XXs
```

Si aparecen warnings de openpyxl al cerrar hojas write-only, no rompen los tests pero indican un posible resource leak a revisar.

---

## 10. Proceso de despliegue

### Build portable (manual)

```
pyinstaller --clean ContApp.spec
    │
    ▼
dist/ContApp/
├── ContApp.exe
├── _internal/          # DLLs, Python runtime, dependencias
├── jsons/              # JSONs editables al lado del .exe
└── data/               # Se crea en runtime para settings.json
```

`jsons/` se distribuye al lado del `.exe` para que el usuario pueda editar las reglas sin recompilar.

---

## 11. Estado actual del repositorio

- **Refactor simplificado completado:** la arquitectura v2.0 está implementada y limpia de referencias funcionales a la versión anterior.
- **Zeus activo:** el proceso está disponible en la UI.
- **Sin CLI, bitácora, updater, DI, instalador ni CI/CD:** todo fue eliminado según `simple_refactor.md`.
- **Editor de diccionarios como tabla tipo Excel:** se prefirió sobre un editor de texto plano para mejorar la experiencia del usuario.
- **Diálogo de códigos nuevos recuperado:** antes de ejecutar Comprobante se detectan códigos de concepto no mapeados y se permite agregarlos a FOAPAL o ignorarlos, con backup automático de los JSONs afectados.
- **`codigos_ignorados.json` con descripción:** ahora guarda `código -> descripción` para que el usuario sepa a qué corresponde cada código ignorado.

---

## 12. Consideraciones de seguridad

- **Datos del usuario:** no versionar `data/settings.json` ni los resultados de `ContApp_Resultados`. Están en `.gitignore`.
- **Path traversal:** los procesos escriben en `RESULTADOS_DIR` bajo `%USERPROFILE%\Documents\ContApp_Resultados`. No usan rutas controladas por el usuario directamente, pero cualquier cambio debe mantener el prefijo absoluto y validar extensiones.

---

## 13. Cuándo actualizar este archivo

Actualiza este documento cuando:

- Cambie el stack tecnológico o las versiones mínimas.
- Se añada/mueva/elimine un módulo principal o cambie su responsabilidad.
- Se modifique la firma de `ProcesoBase` o el contrato UI ↔ core.
- Cambie el proceso de build, test o release.

Mantener este archivo actualizado evita que cada agente tenga que re-descubrir el proyecto desde cero.
