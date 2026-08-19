# ContApp — Sistema de Automatización Contable

Aplicación de escritorio en Python que automatiza 3 procesos manuales de la oficina de contabilidad:

1. **Generar Comprobante**: Recibe uno o varios archivos ZIP con CSVs de Bancolombia y genera dos archivos Excel (`Comprobante` de 5 hojas y el archivo `FOAPAL`).
2. **Interfaz Fierro**: Depura un archivo Excel de Fierro siguiendo el instructivo KM5, agregando las hojas `Diario 2026 - Copia` y `Comprobante`.
3. **Interfaz Zeus**: Depura un archivo Excel de Zeus con la hoja `Exportar`, agregando `Exportar - Copia` y `Comprobante`.

---

## 🚀 Stack Tecnológico

- **Lenguaje**: Python 3.14+
- **GUI**: PySide6 (Qt6)
- **Procesamiento de datos**: Pandas, Openpyxl
- **Pruebas**: Pytest (48 tests)
- **Empaquetado**: PyInstaller (`--onedir`)

---

## 🎨 Interfaz Gráfica

La interfaz cuenta con una estructura limpia con **Topbar fija** de navegación por pestañas:

### Secciones principales

- 🏠 **Inicio**: Pantalla de bienvenida con accesos rápidos a los procesos y a los diccionarios de reglas.
- ⚡ **Procesos**: Selector de proceso (`Comprobante`, `Fierro`, `Zeus`), zona interactiva para arrastrar archivos (`DropZone`), ejecución en segundo plano y visualización de resultados.
- 📖 **Diccionarios**: Navegador y editor integrado para modificar las reglas y mapeos JSON de cada proceso.

### Características

- 🟡 **Modo prueba**: Toggle en la topbar para ejecutar procesos de forma segura sin alterar datos reales. Los resultados de prueba se guardan con prefijo `_prueba_`.
- 📂 **Gestión de resultados**: Los archivos generados se guardan de forma organizada por mes en `%USERPROFILE%\Documents\ContApp_Resultados\<proceso>\YYYY-Mes\`.
- 📝 **Editor de JSONs**: Permite actualizar reglas contables y de mapeo directamente desde la aplicación.

---

## 📁 Estructura del Proyecto

```text
ContApp/
├── main.py                     # Punto de entrada (UI)
├── requirements.txt            # Dependencias
├── ContApp.spec                # Especificación de PyInstaller
├── README.md                   # Documentación pública
├── simple_refactor.md          # Especificación del refactor
│
├── app/                        # Configuración y versionado
│   ├── config.py               # Singleton de configuración y rutas de salida
│   └── version.py              # Versión del software (__version__)
│
├── core/                       # Lógica de negocio y utilidades
│   ├── base.py                 # ProcesoBase abstracto y ResultadoProceso
│   ├── comprobante.py          # ProcesoComprobante
│   ├── fierro.py               # ProcesoFierro
│   ├── zeus.py                 # ProcesoZeus
│   ├── archivos.py             # Gestión de carpetas mensuales y copia de archivos
│   └── json_manager.py         # Lectura y escritura de reglas JSON
│
├── ui/                         # Interfaz gráfica PySide6
│   ├── recursos/tema.py        # Estilos QSS globales
│   ├── ventanas/               # Vistas principales (principal, inicio, procesos, diccionarios)
│   └── widgets/                # Componentes reutilizables (DropZone, SwitchModoPrueba, Logo, ItemArchivo)
│
├── events/                     # Bus de eventos interno (Pub/Sub)
│   ├── bus.py                  # EventBus singleton
│   └── eventos.py              # Definición de eventos
│
├── jsons/                      # Reglas y mapeos editables
│   ├── comprobante/            # Reglas de Comprobante (FOAPAL, NIT, códigos contables y conceptos)
│   ├── fierro/                 # Reglas de Fierro
│   └── zeus/                    # Reglas de Zeus
│
└── tests/                      # Suite de pruebas unitarias e integración (Pytest)
    ├── test_archivos.py
    ├── test_comprobante.py
    ├── test_fierro.py
    ├── test_json_manager.py
    └── test_zeus.py
```

---

## 🛠️ Instalación y Ejecución

### Requisitos previos
- Python 3.14 o superior

### Configuración del entorno

```powershell
# Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### Ejecutar la aplicación

```powershell
python main.py
```

---

## 🧪 Pruebas Automatizadas

Ejecutar la suite completa de pruebas unitarias e integración con Pytest:

```powershell
python -m pytest tests/ -v
```

---

## 📦 Empaquetado Portable (PyInstaller)

Para generar la versión ejecutable portable (`.exe`):

```powershell
pyinstaller --clean ContApp.spec
```

El resultado se generará en la carpeta `dist/ContApp/`, listo para ejecutarse sin necesidad de instalador.