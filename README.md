# ContApp — Sistema de Automatización Contable (v2.0)

**ContApp** es una aplicación de escritorio moderna y liviana desarrollada en Python y PySide6 (Qt6) para automatizar los flujos contables manuales más repetitivos:

1. **Generar Comprobante Bancolombia**: Procesa uno o varios archivos `.ZIP` que contienen extractos bancarios en formato CSV y genera automáticamente:
   - El libro de comprobante contable consolidado (`.xlsx`).
   - El archivo con la estructura **FOAPAL** (`.xlsx`).
2. **Interfaz Fierro (KM5)**: Depura y estandariza libros de contabilidad de Fierro (`.xlsx` / `.xls`), aplicando mapeos de auxiliares, tarjetas y descripciones contables.
3. **Interfaz Zeus**: Depura cuentas contables de 8 a 6 dígitos en archivos de exportación de Zeus (`.xlsx` / `.xls`), generando la estructura de interfaz requerida.

---

## 🎨 Características Principales

- **Topbar de Navegación Fija**:
  - Logotipo vectorial corporativo **"C"** y tipografía institucional.
  - Navegación instantánea entre **INICIO**, **PROCESOS** y **DICCIONARIOS**.
  - Interruptor (**Switch**) para alternar entre **Modo Producción** y **Modo Prueba**.
- **Panel de Inicio (Dashboard)**:
  - Tarjetas interactivas de bienvenida con accesos directos rápidos a cada proceso.
  - Vista compacta y optimizada con cero scroll vertical.
- **Área de Ejecución de Procesos**:
  - Sub-sidebar para alternar entre los 3 procesos.
  - `DropZone` con soporte para **Drag & Drop** de archivos.
  - Lista interactiva de archivos con **botón de eliminación individual (`✕`)** por elemento y botón de vaciado total.
  - Barra de progreso fija en tiempo real.
  - Panel de resultados ampliado con botón directo **`Abrir ubicación →`**.
  - Ejecución en segundo plano (`QThread`) para evitar bloqueos en la interfaz.
- **Editor de Diccionarios y Reglas tipo Excel**:
  - Sub-sidebar con los 8 archivos JSON del sistema agrupados por proceso.
  - Editor interactivo en **tabla de cálculo** con edición directa de celdas.
  - **Pestañas de categorías superiores** para *FOAPAL* (`Créditos` / `Débitos`) y *Códigos de Conceptos* (`Intereses` / `Gastos bancarios`).
  - Buscador / Filtro dinámico en tiempo real (`🔍 Filtrar registros...`).
  - Botones para agregar/eliminar filas y guardar con validación de sintaxis.

---

## 📁 Estructura del Proyecto

```text
ContApp/
├── main.py                     # Punto de entrada principal de la UI
├── requirements.txt            # Dependencias oficiales del proyecto
├── ContApp.spec                # Especificación de PyInstaller para empaquetado portable
├── README.md                   # Documentación principal
├── simple_refactor.md          # Especificación técnica del refactor completado
│
├── app/                        # Configuración global y versionado
│   ├── config.py               # Singleton de configuración y detección de rutas
│   └── version.py              # Declaración de versión (__version__ = "2.0.0")
│
├── core/                       # Lógica contable de negocio pura (sin dependencias de GUI)
│   ├── base.py                 # ProcesoBase abstracto y ResultadoProceso
│   ├── comprobante.py          # Lógica del proceso Comprobante Bancolombia
│   ├── fierro.py               # Lógica del proceso Interfaz Fierro
│   ├── zeus.py                 # Lógica del proceso Interfaz Zeus
│   ├── archivos.py             # Utilidades de carpetas mensuales y manejo de archivos
│   └── json_manager.py         # Lectura y escritura de reglas JSON
│
├── ui/                         # Interfaz gráfica PySide6 (Qt6)
│   ├── recursos/tema.py        # Tema global en modo claro y estilos QSS
│   ├── ventanas/
│   │   ├── principal.py        # Ventana principal con Topbar y QStackedWidget
│   │   ├── inicio.py           # Dashboard de bienvenida y accesos directos
│   │   ├── procesos.py         # Pantalla de selección y ejecución de procesos
│   │   └── diccionarios.py     # Editor de reglas en tabla interactiva tipo Excel
│   └── widgets/
│       ├── logo.py             # Logotipo "C" vectorial antialiased
│       ├── drop_zone.py        # Zona Drag & Drop con lista interactiva
│       ├── item_archivo.py     # Fila de archivo con botón de eliminación individual
│       └── switch_modo_prueba.py # Switch redondeado para modo prueba
│
├── jsons/                      # Diccionarios de reglas editables (comprobante, fierro, zeus)
│   ├── comprobante/
│   ├── fierro/
│   └── zeus/
│
├── data/                       # Preferencias del usuario
│   └── settings.json
│
└── tests/                      # Suite completa de pruebas unitarias (Pytest)
    ├── test_archivos.py
    ├── test_comprobante.py
    ├── test_fierro.py
    ├── test_json_manager.py
    └── test_zeus.py
```

---

## 🚀 Guía Rápida para Usar la Aplicación

### Opción A: Ejecución en Desarrollo (Código Fuente)

1. **Activar el entorno virtual de Python**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. **Instalar dependencias** (si es la primera vez):
   ```powershell
   pip install -r requirements.txt
   ```
3. **Iniciar la aplicación**:
   ```powershell
   python main.py
   ```

---

### Opción B: Ejecutar la Versión Portable (`.exe`)

El ejecutable compilado se encuentra listo para usar en la carpeta:
```text
dist\ContApp\ContApp.exe
```

1. Haz doble clic en `ContApp.exe`.
2. La aplicación arrancará de inmediato sin necesidad de instalar Python ni dependencias adicionales en la máquina de destino.
3. Para distribuir a otros equipos de la oficina, simplemente copia o comprime en `.zip` la carpeta completa `dist\ContApp\`.

---

## 📖 Cómo Operar los Procesos

### 1. Generar Comprobante Bancolombia
1. Ve a la pestaña **PROCESOS** y selecciona **Generar Comprobante** (o haz clic en el botón de la tarjeta en **INICIO**).
2. Arrastra uno o varios archivos `.zip` de extractos a la zona de carga (o haz clic en **Examinar archivos...**).
3. Si cargaste un archivo por error, pulsa su botón **`✕`** para quitarlo individualmente.
4. Pulsa **Ejecutar proceso**.
5. Al finalizar, pulsa **`Abrir ubicación →`** para acceder a los archivos Excel generados en tu carpeta `Documentos\ContApp_Resultados\Comprobante\`.

### 2. Interfaz Fierro
1. Selecciona **Interfaz Fierro** en el sub-sidebar.
2. Arrastra tu archivo Excel (`.xlsx` o `.xls`) de Fierro.
3. Pulsa **Ejecutar proceso**.
4. Se generará la copia de respaldo y el comprobante con los mapeos actualizados.

### 3. Interfaz Zeus
1. Selecciona **Interfaz Zeus** en el sub-sidebar.
2. Arrastra tu archivo Excel de Zeus con la hoja `Exportar`.
3. Pulsa **Ejecutar proceso**.
4. Se generará la hoja depurada con los auxiliares homologados de 8 a 6 dígitos.

### 4. Consultar o Modificar Reglas (Diccionarios)
1. Ve a la pestaña **DICCIONARIOS**.
2. Selecciona el archivo que deseas consultar en el panel lateral (por ejemplo, *FOAPAL*, *Códigos Contables*, *Mapeo Auxiliares*, etc.).
3. Puedes buscar rápidamente con el campo `🔍 Filtrar registros...`.
4. En archivos con varias categorías (*FOAPAL* o *Códigos de Conceptos*), utiliza las pestañas superiores para alternar entre categorías.
5. Edita las celdas directamente en la tabla, usa `+ Agregar fila` o `✕ Eliminar fila`.
6. Haz clic en **Guardar cambios** para aplicar las nuevas reglas de inmediato.

---

## 🧪 Pruebas Automatizadas

Para validar que todos los cálculos, transformaciones contables y utilidades funcionan al 100%:

```powershell
pytest tests/ -v
```

Resultado: **48 de 48 pruebas aprobadas (100% pasando)**.

---

## 📦 Compilar un Nuevo Ejecutable Portable

Si realizas cambios en el código y deseas reconstruir el ejecutable portable:

```powershell
pyinstaller --clean -y ContApp.spec
```

El resultado actualizado se generará en `dist/ContApp/`.