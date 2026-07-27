# Contexto del Proyecto: ContApp (Sistema de Automatización Contable)

> Documento de referencia para el desarrollo del proyecto. Compártelo con tu IDE / asistente de IA al inicio de cada sesión de trabajo para que entienda el proyecto sin tener que explicarlo desde cero.

---

## 🎯 Descripción General

**ContApp** es una aplicación de escritorio en Python que automatiza procesos manuales de la oficina de contabilidad de la universidad. La app envuelve 3 scripts existentes (que hoy corren de forma independiente) y les agrega una interfaz gráfica amigable, manejo de archivos, modo prueba, editor de JSONs inteligente, y registro de actividad visible desde la UI.

- **Usuarios actuales:** 2 personas de la oficina de contabilidad (cada una con sus propios archivos y JSONs, sin compartir datos entre sí).
- **Despliegue:** Instalador `.exe` distribuido por el personal de TI de la universidad.
- **Visión a futuro:** Portal web con autenticación (la arquitectura ya está pensada para permitir esa migración sin reescribir la lógica).

---

## 🏗️ Arquitectura: Cocina vs Comedor

**Principio fundamental:** Separar la LÓGICA de negocio de la INTERFAZ gráfica.

- **`procesos/` + `utils/`** = La cocina. Toda la lógica: procesamiento de archivos, lectura/escritura de JSONs, bitácora, manejo de carpetas mensuales. **No sabe nada de ventanas ni botones.**
- **`ui/`** = El comedor. Toda la interfaz visual: ventanas, botones, drag & drop, switch de modo prueba, editor de JSONs, banner de modo prueba. **No sabe nada de Pandas ni de Excel.**
- **Conexión:** El `ui/` le pide al `procesos/` que ejecute un proceso pasándole los archivos. El `procesos/` devuelve el resultado. La interfaz solo lo muestra.

Esta separación es la que va a permitir que el día de mañana, cuando se quiera hacer un portal web, solo se reescriba `ui/` (manteniendo `procesos/` + `utils/` intactos).

### Patrón de procesos

Cada proceso hereda de una "receta base" (`procesos/base.py`) que define el contrato:

- Nombre y descripción del proceso
- Tipo de archivos que espera
- Tipo de archivos que produce
- Método `ejecutar(archivos, modo_prueba)` que recibe archivos y devuelve resultados

Los procesos específicos (`comprobante`, `fierro`, `zeus`) solo rellenan este contrato con su lógica particular.

---

## ⚙️ Los 3 Procesos

| Proceso | Entrada | Salida | Reglas | JSONs |
|---------|---------|--------|--------|-------|
| **Generar Comprobante** | ZIP (que viene del banco y trae CSVs adentro) | 2 archivos Excel | Desde JSON | 4 archivos |
| **Interfaz Fierro** | Excel | El mismo Excel depurado | Desde JSON | 3 archivos |
| **Interfaz Zeus** | Excel | El mismo Excel depurado | Desde JSON | 1 archivo |

**Total: 8 JSONs en 4 estructuras distintas.**

### Sobre los códigos de los procesos

> ⚠️ **Los procesos de la app se construyen tomando como base los scripts ya existentes del usuario**, refactorizándolos con buenas prácticas para que se ajusten al patrón `ProcesoBase`. No es una reescritura desde cero, es una evolución.

- ✅ Se preserva la lógica de negocio de los scripts actuales.
- ✅ Se respeta la forma de los archivos de entrada y salida que ya funciona.
- ✅ Se aplica el patrón `ProcesoBase` para uniformidad.
- ✅ Se mejora el código con: manejo de errores, mensajes en español, bitácora, validación, etc.
- ✅ Las reglas se mantienen en los JSONs que ya existen.

---

## 📋 Los 8 JSONs y sus 4 estructuras

Los JSONs del proyecto no son todos iguales. El editor detecta automáticamente la estructura y muestra la vista adecuada.

### Tipo A — Plano simple (4 JSONs)
```json
{
  "47789085868": "890903938",
  "47777828641": "890903938"
}
```
- Editor: tabla simple **clave/valor**.
- Archivos: `comprobante/cuentas_bancarias.json`, `comprobante/cuentas_contables.json`, `fierro/descripciones.json`, `fierro/auxiliares_cuentas.json`

### Tipo B — Secciones con sub-objetos (1 JSON)
```json
{
  "creditos": {
    "1334": { "Fondo": "FOPNAL", "Organizacion": "13201", "Cuenta": "530515", "Programa": "999999", "D/C": "C" }
  },
  "debitos": { ... }
}
```
- Editor: **secciones expandibles** + sub-formulario por sub-objeto.
- Archivo: `comprobante/creditos_debitos.json`

### Tipo C — Secciones con valores mixtos (1 JSON)
```json
{
  "Intereses": { "1998": "AJUSTE INTERESES AHORROS DB" },
  "Gastos bancarios": { "480": ["COMIS CONSIGNACION SUCURSAL"] }
}
```
- Editor: **secciones expandibles** + tabla que acepta strings o listas.
- Archivo: `comprobante/intereses_gastos.json`

### Tipo D — Lista de pares (2 JSONs)
```json
{
  "tarjetas": [
    ["^Comisión Tarjeta CR AMEX T CR AMEX", "Comisión T CR AMEX"]
  ]
}
```
- Editor: **tabla de pares** (patrón → valor).
- Archivos: `fierro/tarjetas.json`, `zeus/auxiliares.json`

---

## 📁 Estructura del Proyecto

```
contabilidad_app/
│
├── procesos/                # 3 scripts + receta base
│   ├── base.py              # ProcesoBase (la receta base)
│   ├── comprobante.py       # Proceso 1: Generar Comprobante
│   ├── fierro.py            # Proceso 2: Interfaz Fierro
│   └── zeus.py              # Proceso 3: Interfaz Zeus
│
├── ui/                      # Interfaz gráfica (no sabe de Pandas/Openpyxl)
│   ├── ventanas/
│   │   ├── principal.py     # Pantalla Inicio + sidebar de navegación
│   │   ├── ejecutar_proceso.py  # Pantalla Procesos
│   │   ├── editor_json.py   # Pantalla Diccionarios + editor inteligente
│   │   └── configuracion.py # Pantalla Configuración (Bitácora)
│   ├── widgets/             # Piezas reutilizables
│   │   ├── drop_zone.py         # Zona de arrastrar archivos
│   │   ├── switch_modo_prueba.py  # Toggle del modo prueba
│   │   ├── banner_modo_prueba.py  # Banner naranja del modo prueba
│   │   ├── tabla_resultados.py    # Tabla genérica (clave/valor, pares, archivos)
│   │   └── tarjeta_proceso.py     # Tarjeta clickeable usada en el grid de seleccion
│   └── recursos/            # Íconos, imágenes, estilos visuales
│
├── utils/                   # Herramientas de apoyo (no saben de UI)
│   ├── json_manager.py      # Lee, escribe y respalda JSONs con backup
│   ├── archivos.py          # Maneja archivos y carpetas mensuales
│   └── bitacora.py          # Registro de actividades (logging) → archivo
│
├── jsons/                   # DENTRO del programa, 1 carpeta por proceso
│   ├── comprobante/
│   ├── fierro/
│   └── zeus/
│
├── resultados/              # FUERA del programa (en Documentos del usuario)
│   ├── comprobante/         # Cada proceso en su propia carpeta
│   ├── fierro/              # NUNCA se mezclan resultados
│   └── zeus/
│
├── tests/                   # Pruebas con Pytest
│
├── main.py                  # Punto de entrada
├── requirements.txt
└── README.md
```

> 📌 **Importante:** `resultados/` debe vivir **fuera** de la carpeta del programa (en Documentos del usuario), para que las actualizaciones no borren los datos. `jsons/` sí vive dentro.

---

## 🛠️ Stack Técnico

| Componente | Herramienta | Notas |
|------------|-------------|-------|
| Lenguaje | **Python 3.14.3** | Verificar compatibilidad con PySide6 y PyInstaller al instalar |
| GUI | **PySide6** | Licencia LGPL, ideal para distribución |
| Datos | **Pandas + Openpyxl** | Ya en uso en los scripts actuales |
| Pruebas | **Pytest** | Estándar de la industria |
| Empaquetado | **PyInstaller** | Convierte el proyecto en un `.exe` instalable |
| Entorno virtual | **venv** | Built-in de Python, indispensable |
| Bitácora | **logging** (built-in) | Built-in de Python. Debe guardar en ARCHIVO, no solo consola |
| IDE | **VS Code** | Con extensión de Python instalada |
| Control de versiones | **Git (portátil)** | Ya configurado, listo para usar |

---

## 📋 Funcionalidades de la App

1. **Cargar archivos** — drag & drop sobre la zona de la app, o desde el explorador de archivos. Acepta uno o varios archivos a la vez.

2. **Elegir tipo de proceso** — la pantalla Procesos muestra primero un **grid de tarjetas** con los procesos disponibles (icono + nombre + descripcion). El usuario hace click en una tarjeta para elegir el proceso, recien ahi aparece la opcion de cargar archivos. Esto evita que el usuario suba archivos antes de saber para que proceso son. La pantalla de ejecucion incluye un boton "Volver" para cambiar de proceso.

3. **Guardar resultados automáticamente** — en `resultados/[proceso]/YYYY-MM/` (carpeta por proceso + mes).

4. **Resultados organizados por mes** — cada ejecución mensual se guarda en su propia subcarpeta con timestamp.

5. **Resultados separados por proceso** — **NUNCA** se mezclan los resultados entre Comprobante, Fierro y Zeus.

6. **Modo Prueba:**
   - **Banner naranja** fijo en la parte superior de la app (visible en las 4 pantallas).
   - Mensaje único en las 4 secciones: **"Los cambios no se guardarán en producción"**.
   - **Toggle switch** visible siempre.
   - **Aviso informativo** que le explica al usuario cómo funciona el modo prueba.
   - Los archivos de salida en modo prueba van a una **carpeta temporal**.

7. **Editor de JSONs inteligente** (auto-detecta estructura):
   - **Tipo A (plano):** tabla simple clave/valor.
   - **Tipo B (sub-objetos):** secciones expandibles + sub-formulario.
   - **Tipo C (valores mixtos):** secciones + tabla que acepta strings o listas.
   - **Tipo D (pares):** tabla patrón → valor.
   - **Badges "Modificado" y "Nuevo"** en las filas cambiadas.
   - **Aviso de "X cambios sin guardar"** abajo.
   - **Botones Cancelar / Guardar cambios.**
   - **Backup automático** del JSON antes de cualquier cambio (con fecha en el nombre).

8. **Configuración → Bitácora:**
   - Tabla con: **fecha/hora · usuario · acción · archivos · resultado**.
   - **Filtros:** por fecha, por tipo de acción, por proceso.
   - **Exportar** a Excel o CSV.
   - **Limpiar registros antiguos** (con confirmación).
   - Por ahora **solo esto** en Configuración; más opciones a futuro.

---

## 🎨 Diseño de la Interfaz (ContApp)

**4 secciones en el sidebar + 1 elemento global:**

- **Inicio** — Bienvenida + grid de tarjetas con los procesos disponibles + panel "Último Proceso Ejecutado" (estado, fecha, duración, botón "Ver Reporte").
- **Procesos** — Grid de tarjetas con los 3 procesos disponibles (icono + nombre + descripcion) al entrar. Al elegir uno, aparece la vista de ejecucion: boton "Volver" + titulo del proceso + DropZone + lista de archivos + botones + tabla de resultados. El usuario solo puede cargar archivos despues de elegir proceso.
- **Diccionarios** — Lista de JSONs a la izquierda + editor inteligente a la derecha (con buscador, contador, agregar nuevo, tabla, badges, cambios sin guardar).
- **Configuración** — Vista de bitácora (por ahora solo esto).
- **Modo Prueba:** Banner naranja en la parte superior de las 4 pantallas.

**Nombre de la app:** ContApp (visible en el logo del sidebar).

---

## ⚠️ Reglas de Negocio Críticas (no romper)

1. **Modo prueba siempre visible y obvio:** NUNCA permitir correr un proceso real con el modo prueba mal configurado. El banner naranja es la garantía.
2. **Edición de JSONs con backup:** SIEMPRE hacer backup antes de editar un JSON, sin excepción.
3. **Resultados organizados por mes:** SIEMPRE guardar en la carpeta del mes actual.
4. **Resultados separados por proceso:** NUNCA mezclar resultados entre Comprobante, Fierro y Zeus.
5. **Mensajes en español:** Todos los mensajes al usuario en español y comprensibles para alguien no técnico.
6. **Bitácora en cada acción:** Cada ejecución de proceso, cada edición de JSON, cada acción queda registrada.

---

## 📐 Convenciones de Desarrollo

- **Nombres de procesos en snake_case:** `comprobante`, `fierro`, `zeus`.
- **Mensajes al usuario en español.**
- **Backup automático** de cada JSON antes de editarlo (con fecha en el nombre).
- **Bitácora** en cada acción.
- **Modo prueba** siempre visible y obvio.
- **Resultados organizados por mes** y separados por proceso.
- **`jsons/`** dentro de la carpeta del programa.
- **`resultados/`** fuera de la carpeta del programa (en Documentos del usuario).
- **Las carpetas `jsons/` se organizan 1 por proceso**, con archivos separados adentro.
- **La bitácora debe guardar en archivo** (no solo en consola) para que sea visible desde la UI.
- **Los procesos de la app se construyen refactorizando los scripts existentes** (no reescribiendo desde cero).

---

## 🚀 Paso a Paso para el Desarrollo (5 fases)

### 🟢 FASE 1 — Preparación del entorno

1. Verificar que Python 3.14.3 funciona correctamente.
2. Verificar que PySide6 y PyInstaller son compatibles con 3.14.3 (si fallan, evaluar bajar a 3.12).
3. Instalar las librerías: `pip install PySide6 pandas openpyxl pytest pyinstaller`.
4. Crear la estructura de carpetas del proyecto.
5. Crear el entorno virtual (`venv`) y activarlo.
6. Inicializar el repositorio de Git (con portátil) y hacer el primer commit.
7. Crear `requirements.txt` con las librerías y versiones.
8. Crear `README.md` con las instrucciones básicas.

**Entregable:** Carpeta del proyecto lista, entorno virtual funcionando, Git inicializado, primer commit hecho.

### 🔵 FASE 2 — Núcleo de la app (lógica pura, sin UI)

1. Crear `procesos/base.py` con la clase `ProcesoBase`.
2. Refactorizar los 3 scripts existentes para que hereden de `ProcesoBase`:
   - `procesos/comprobante.py`
   - `procesos/fierro.py`
   - `procesos/zeus.py`
3. Crear `utils/json_manager.py` (lee, escribe, hace backup automático).
4. Crear `utils/archivos.py` (maneja carpetas mensuales, resultados).
5. Crear `utils/bitacora.py` (logging que también guarda en archivo).
6. Mover los 8 JSONs a sus carpetas correspondientes dentro de `jsons/`.
7. Probar la lógica desde la terminal (sin UI) para verificar que todo funciona.

**Entregable:** Los 3 procesos corren desde la terminal, leen sus JSONs, generan resultados en las carpetas correctas, y dejan registro en la bitácora.

### 🟣 FASE 3 — Interfaz gráfica (UI con PySide6)

1. Crear `main.py` (punto de entrada) y `app/config.py`.
2. Crear los widgets reutilizables:
   - `ui/widgets/switch_modo_prueba.py`
   - `ui/widgets/banner_modo_prueba.py`
   - `ui/widgets/drop_zone.py`
   - `ui/widgets/tabla_resultados.py`
3. Crear las 4 ventanas:
   - `ui/ventanas/principal.py` (Inicio + sidebar)
   - `ui/ventanas/ejecutar_proceso.py` (Procesos)
   - `ui/ventanas/editor_json.py` (Diccionarios + editor inteligente)
   - `ui/ventanas/configuracion.py` (Bitácora)
4. Agregar íconos y estilos en `ui/recursos/`.
5. Conectar todo: que la UI llame a la lógica, y muestre los resultados.

**Entregable:** App completa funcionando, con las 4 secciones navegables, modo prueba visible, editor de JSONs inteligente, y bitácora visible.

### 🟡 FASE 4 — Pruebas y ajustes

1. Escribir pruebas con Pytest en `tests/`.
2. Probar todos los flujos manualmente.
3. Probar el modo prueba (que NO guarde en producción).
4. Probar el editor de JSONs con los 4 tipos de estructura.
5. Ajustar lo que sea necesario (errores, UX, mensajes).

**Entregable:** App probada y estable, lista para empaquetar.

### 🔴 FASE 5 — Empaquetado y entrega

1. Generar el instalador `.exe` con PyInstaller.
2. Probar el instalador en una máquina limpia.
3. Crear instrucciones para la universidad sobre cómo instalarlo.
4. Entregar el `.exe` y las instrucciones a la universidad.
5. Soporte post-entrega: ayudar a resolver cualquier issue de los primeros usuarios.

**Entregable:** Archivo `.exe` listo para distribuir, con instrucciones claras para la universidad.

### Orden lógico (dependencias)

```
Fase 1 (Setup)  →  Fase 2 (Core)  →  Fase 3 (UI)  →  Fase 4 (Tests)  →  Fase 5 (Empaquetar)
```

Cada fase depende de la anterior. No se puede empezar la 2 sin la 1, ni la 3 sin la 2, etc.

---

## 🔮 Consideraciones Futuras

- Más opciones en la sección Configuración.
- Migración a portal web (la separación utils/procesos vs ui lo permite).
- Autenticación de usuarios (preparado desde la arquitectura).
- La universidad se encarga de distribuir los instaladores `.exe` y las actualizaciones.

---

## 📚 Glosario de Términos

- **ContApp:** Nombre de la aplicación.
- **Core:** La parte del programa que hace el trabajo real (`procesos/` + `utils/`). No tiene interfaz visual.
- **UI (User Interface):** La parte visual del programa (`ui/`): ventanas, botones, tablas. Es lo que el usuario ve y toca.
- **Proceso:** Cada uno de los 3 trabajos que la app puede hacer (Comprobante, Fierro, Zeus).
- **ProcesoBase:** La clase "molde" de la que heredan los 3 procesos. Define qué información tiene que dar cada proceso.
- **JSON:** Un archivo de texto que guarda información en formato `clave: valor`. Es como una lista de configuraciones que la app puede leer y modificar.
- **Reglas:** Las configuraciones que controlan cómo se limpia o procesa la información. Viven en JSONs para que el usuario las pueda editar sin tocar código.
- **Modo prueba:** Una forma de ejecutar los procesos sin que los resultados se guarden donde quedan los reales. Indicado por el banner naranja.
- **Banner de modo prueba:** La barra naranja fija en la parte superior de la app que aparece cuando el modo prueba está activo.
- **Bitácora:** El registro histórico de "quién hizo qué y cuándo" en la app. Se ve desde Configuración.
- **Entorno virtual (venv):** Una carpeta aislada donde se instalan las librerías del proyecto, separadas del Python del sistema. Evita conflictos entre proyectos.
- **Empaquetado (PyInstaller):** El proceso de convertir todo el proyecto Python en un archivo `.exe` que los usuarios pueden ejecutar con doble clic.
- **Pytest:** La herramienta que se usa para escribir y correr pruebas automáticas del código.
- **Drag & drop:** Arrastrar y soltar. La acción de mover archivos con el mouse desde una carpeta hasta la ventana de la app.
- **Refactorizar:** Mejorar el código de un programa que ya funciona, sin cambiar lo que hace, para que sea más limpio, más fácil de mantener y más fácil de extender.
- **Editor inteligente:** Editor de JSONs que detecta automáticamente la estructura del archivo y muestra la vista adecuada.

---

**Versión del documento:** 2.0
**Última actualización:** 2026-07-15
