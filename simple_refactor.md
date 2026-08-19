# Guía de refactor simplificada — ContApp

> Documento de referencia para simplificar ContApp a una aplicación de escritorio pequeña, enfocada en usuarios no técnicos, con una interfaz limpia y solo lo esencial.

---

## 1. Objetivo

Transformar ContApp en una aplicación mínima pero funcional:

- Tres procesos de negocio: **Comprobante**, **Fierro** y **Zeus**.
- Interfaz gráfica simple con navegación por pestañas, diseñada en Figma.
- Sin actualizador automático, sin bitácora y sin registro de actividad.
- Sin modo CLI.
- Build portable con PyInstaller, sin instalador ni CI/CD.

Este documento sirve como **especificación del estado deseado** y como **guía de refactorización** paso a paso.

---

## 2. Decisiones clave

| Aspecto | Decisión |
|---|---|
| Procesos | Se mantienen los 3: `comprobante`, `fierro`, `zeus`. |
| Modo CLI | Se elimina. `main.py` inicia la UI directamente. |
| Navegación | Topbar con 3 tabs: **Inicio**, **Procesos**, **Diccionarios**. |
| Pantallas eliminadas | Configuración, Backups, diálogo de actualización. |
| Pantallas mantenidas | Editor de JSONs integrado (en la pestaña Diccionarios). |
| Actualizaciones | Se elimina `app/updater/` y todo lo relacionado con GitHub. |
| Bitácora / logging | Se elimina `utils/bitacora.py`, `data/bitacora/` y `log/`. |
| Inyección de dependencias | Se eliminan `app/container.py` y `app/bootstrap.py`. |
| Bus de eventos | Se mantiene `events/` como capa de comunicación UI-core. |
| Build | PyInstaller (`ContApp.spec`) generando un bundle portable. |
| Instalador / CI | Se eliminan `ContApp.iss`, `.github/workflows/` y `scripts/build/`. |
| Tests | Se reduce la suite a tests esenciales de procesos y utilidades. |
| Tema | Solo modo claro. |
| Paleta y detalles visuales | Se ajustan durante la implementación según el diseño de Figma. |

---

## 3. Referencia de diseño (Figma)

Archivo de referencia: `CONTAPP.png` (exportación del boceto de Figma).

### Estructura de la ventana principal

- **Topbar fija**:
  - Izquierda: logo + nombre `"CONTAPP"`.
  - Centro: tabs de navegación `"INICIO"`, `"PROCESOS"`, `"DICCIONARIOS"`. El tab activo se resalta con fondo azul.
  - Derecha: toggle `"Modo prueba"` (azul cuando está activo).
- **Área de contenido dinámico**: cambia según el tab seleccionado.

### Sistema de componentes base

- **Botón primario**: fondo azul, texto blanco.
- **Botón secundario**: fondo gris claro, texto oscuro.
- **Switch/Toggle**: fondo azul en estado activo, gris en estado inactivo.
- **Tipografía y espaciado**: usar los valores por defecto de PySide6 como base, ajustando a medida que el diseño en Figma se refine.

### Pantallas

| Tab | Propósito |
|---|---|
| **Inicio** | Pantalla de bienvenida, acceso rápido y resumen visual de la app. |
| **Procesos** | Selector de proceso, zona para arrastrar archivos, ejecución y visualización del resultado. |
| **Diccionarios** | Listado de JSONs de reglas y editor simple para modificarlos. |

> La paleta exacta, animaciones, textos, botones y mensajes se definirán iterativamente durante el desarrollo, usando el Figma como fuente de verdad visual.

---

## 4. Estructura final de carpetas

```
ContApp/
├── main.py                     # Punto de entrada: solo UI.
├── requirements.txt            # Dependencias mínimas.
├── ContApp.spec                # PyInstaller onedir.
├── README.md                   # Documentación simple para el usuario final.
├── simple_refactor.md          # Este documento.
│
├── app/
│   ├── __init__.py
│   ├── config.py               # Rutas y constantes. Sin DI ni settings service.
│   └── version.py              # Versión y nombre de la app.
│
├── core/                       # Lógica de negocio + utilidades.
│   ├── __init__.py
│   ├── base.py                 # ProcesoBase y ResultadoProceso.
│   ├── comprobante.py
│   ├── fierro.py
│   ├── zeus.py
│   ├── archivos.py             # Carpetas mensuales, timestamps, copiar/mover.
│   └── json_manager.py         # Lectura/escritura JSON simple.
│
├── events/                     # Bus de eventos pub/sub.
│   ├── __init__.py
│   ├── bus.py
│   └── eventos.py
│
├── jsons/                      # Reglas editables.
│   ├── comprobante/
│   ├── fierro/
│   └── zeus/
│
├── data/                       # Estado mínimo persistente.
│   └── settings.json           # Preferencias básicas (tema, última carpeta).
│
├── ui/                         # Interfaz gráfica.
│   ├── __init__.py
│   ├── recursos/
│   │   └── tema.py             # Paleta y QSS base (modo claro).
│   ├── ventanas/
│   │   ├── principal.py        # VentanaPrincipal con topbar y tabs.
│   │   ├── inicio.py           # Pantalla de inicio.
│   │   ├── procesos.py         # Pantalla de ejecución de procesos.
│   │   └── diccionarios.py     # Pantalla de edición de JSONs.
│   └── widgets/                # DropZone, tarjetas, switches, etc.
│
└── tests/                      # Suite reducida.
    ├── __init__.py
    ├── test_comprobante.py
    ├── test_fierro.py
    ├── test_zeus.py
    └── test_json_manager.py
```

---

## 5. Cambios en la arquitectura

### 5.1. `main.py`

- Eliminar `argparse` y todo el modo CLI.
- Inicializar `QApplication` y abrir `VentanaPrincipal`.
- No registrar servicios ni inicializar bitácora.

```python
# main.py
import sys
from PySide6.QtWidgets import QApplication
from ui.ventanas.principal import VentanaPrincipal


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ContApp")
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

### 5.2. `app/`

- `config.py`: rutas simples. Sin `RESULTADOS_DIR` configurable complejo. Leer `data/settings.json` directamente.
- `version.py`: se mantiene como fuente de verdad de la versión.
- Eliminar `container.py`, `bootstrap.py` y `app/updater/`.

### 5.3. `core/`

Fusionar las responsabilidades de `procesos/`, `utils/` y `services/` en una sola carpeta:

- `base.py`: `ProcesoBase`, `ResultadoProceso` y `ProcesoCancelado`.
- `comprobante.py`, `fierro.py`, `zeus.py`: lógica de cada proceso.
- `archivos.py`: utilidades de manejo de archivos y carpetas mensuales.
- `json_manager.py`: lectura/escritura de JSONs. Sin backups automáticos, sin locks, sin detección de tipo compleja.

Eliminar:

- `services/settings_service.py`
- `services/backup_service.py`
- `services/reporte_service.py`
- `utils/bitacora.py`

### 5.4. `events/`

Se mantiene como mecanismo de desacoplamiento entre la UI y los procesos. No reemplaza los signals de Qt, pero facilita futuras extensiones.

### 5.5. `data/`

- `data/settings.json`: preferencias mínimas (última carpeta usada, tema, etc.).
- Eliminar `data/backups/` y `data/bitacora/`.

---

## 6. Cambios en la UI

### 6.1. Ventana principal (`ui/ventanas/principal.py`)

- Usar un layout vertical.
- Topbar con:
  - Logo + nombre.
  - Tabs `QPushButton` o `QTabBar` para Inicio / Procesos / Diccionarios.
  - Toggle `Modo prueba` alineado a la derecha.
- Área de contenido con `QStackedWidget` para cambiar entre pantallas.
- Sin barra lateral, sin footer de bitácora, sin botón de actualización.

### 6.2. Pantalla de Inicio (`ui/ventanas/inicio.py`)

- Bienvenida simple.
- Accesos rápidos a Procesos o Diccionarios.
- Información de versión.

### 6.3. Pantalla de Procesos (`ui/ventanas/procesos.py`)

- Selector del proceso (Comprobante / Fierro / Zeus).
- Zona para arrastrar archivos (`DropZone`).
- Botón ejecutar.
- Indicador de progreso.
- Área de resultado/mensaje final.
- El estado de `modo_prueba` se lee del toggle de la topbar.

### 6.4. Pantalla de Diccionarios (`ui/ventanas/diccionarios.py`)

- Listado de JSONs organizados por proceso.
- Editor de texto simple (lectura/escritura directa del archivo).
- Botón guardar.
- Sin backup automático, sin gestión de versiones.

### 6.5. Tema (`ui/recursos/tema.py`)

- Solo modo claro.
- Paleta base con azul como color primario (ajústese al Figma final).
- QSS mínimo para topbar, tabs, botones y switches.

---

## 7. Lista de eliminaciones

Eliminar archivos y carpetas que ya no aportan valor en la versión simplificada:

- `app/updater/`
- `app/container.py`
- `app/bootstrap.py`
- `services/`
- `utils/bitacora.py`
- `log/`
- `data/backups/`
- `data/bitacora/`
- `ui/ventanas/configuracion.py`
- `ui/ventanas/backups.py`
- `ui/ventanas/dialogo_actualizacion.py`
- `ui/ventanas/ejecutar_proceso.py` (reemplazado por `ui/ventanas/procesos.py`)
- `ContApp.iss`
- `.github/workflows/`
- `scripts/build/`
- `docs/context.md` (integrar en README o eliminar)

---

## 8. Fases de refactorización

- [x] 1. **Limpieza**: eliminar archivos y carpetas no necesarios.
- [x] 2. **Reestructuración**: mover `procesos/`, `utils/` y `services/` a `core/`.
- [x] 3. **Simplificación interna**: quitar DI, bitácora, updater, services.
- [x] 4. **Refactor UI**: implementar topbar con tabs y tres pantallas simples (Inicio, Procesos, Diccionarios en tabla).
- [x] 5. **Ajuste de tests**: reducir la suite a tests esenciales (48/48 tests OK).
- [x] 6. **Build**: actualizar `ContApp.spec` y verificar bundle portable (`dist/ContApp/ContApp.exe`).
- [x] 7. **Documentación**: asegurar que `README.md` y `simple_refactor.md` reflejen el estado final.

---

## 9. Build y ejecución

### Entorno

```powershell
.\.venv\Scripts\Activate.ps1
```

### Instalar dependencias

```powershell
pip install -r requirements.txt
```

### Ejecutar en desarrollo

```powershell
python main.py
```

### Empaquetar

```powershell
pyinstaller --clean ContApp.spec
```

Resultado: `dist/ContApp/ContApp.exe` + `_internal/` + `jsons/`.

> No se genera instalador `.exe`. La distribución es el bundle portable de PyInstaller.

---

## 10. Notas para futuros desarrolladores

- **Idioma**: todo el código y mensajes al usuario en español, siguiendo la convención actual.
- **Separación core/UI**: `core/` no importa PySide6; `ui/` no importa pandas ni openpyxl.
- **JSONs**: se mantienen editables manualmente o desde la pestaña Diccionarios. No hay backup automático.
- **Modo prueba**: estado global en la topbar. Todo proceso debe respetarlo sin escribir archivos reales cuando está activo.
- **Procesos**: continúan heredando de `ProcesoBase` y reportan progreso mediante callbacks.
- **No hay actualizaciones automáticas**: las nuevas versiones se distribuyen manualmente.
- **No hay bitácora**: errores se muestran en la UI; no se guarda historial en disco.

---

## 11. Próximos pasos sugeridos

1. Validar este documento con el diseño final de Figma.
2. Implementar la topbar y el `QStackedWidget` base.
3. Migrar procesos a `core/` y eliminar dependencias innecesarias.
4. Definir paleta exacta y componentes visuales.
5. Probar el bundle portable en una máquina limpia de Windows.
