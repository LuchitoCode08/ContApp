# Bitacora de sesiones - ContApp

> Archivo de seguimiento del proyecto. Cada sesion se registra aqui
> con la fecha, las tareas completadas y las pendientes.
>
> Formato: cada sesion es un bloque con encabezado `## Sesion YYYY-MM-DD`
> que contiene tres listas:
> - **[x] Completadas:** lo que se hizo en la sesion.
> - **[ ] Pendientes:** lo que queda por hacer (puede venir de antes).
> - **[ ] Proxima sesion:** ideas / sugerencias para la siguiente.

---

## Sesion 2026-07-27

**Resumen:** Cierre de la Fase 3 (UI) del proyecto. Se implementaron las 2 pantallas UI que faltaban (Diccionarios y Configuracion) y se mejoro la pantalla Inicio. **Resultado: las 4 pantallas de la app estan funcionales y verificadas con smoke tests E2E.**

### [x] Completadas (Fase A: UI completa)

- [x] **Extender `utils/bitacora.py`**: agregar `leer_registros()` (parsea el log), `obtener_ultimo()` (ultimo proceso ejecutado) y `_extraer_proceso()` / `_extraer_archivos()` helpers. Resuelve la ruta del log via `app.config.BITACORA_LOG` con fallback.
- [x] **A1. Mejorar Pantalla Inicio** (`ui/ventanas/principal.py` reescrito):
  - `PantallaInicio` con encabezado de bienvenida al usuario + grid de 3 columnas con `TarjetaProceso`.
  - `PanelUltimoEjecutado` (QFrame): muestra proceso + fecha + archivos generados + botones "Refrescar" y "Ver reporte" (abre la carpeta del archivo mas reciente en el explorador).
  - `VentanaPrincipal._ir_a_procesos_preseleccionado(nombre)`: click en tarjeta del dashboard -> salta directo a Procesos con ese proceso pre-seleccionado.
  - Refresca el panel automaticamente al volver a Inicio.
- [x] **API `PantallaProcesos.seleccionar_proceso(nombre)`** en `ui/ventanas/ejecutar_proceso.py`: salta directo a la vista de ejecucion con un proceso pre-cargado. Pensado para integrar con Inicio.
- [x] **A2. Pantalla Diccionarios** (`ui/ventanas/editor_json.py` creado, **~580 lineas**):
  - `PantallaDiccionarios` con QSplitter horizontal: lista izquierda con los 8 JSONs auto-descubiertos en `JSONS_DIR` + panel derecho con editor.
  - 4 sub-editors especializados segun `detectar_tipo()`:
    - `EditorTipoA`: `QTableWidget` 2 columnas (clave/valor) editable con botones papelera por fila.
    - `EditorTipoB`: `QTreeWidget` con secciones expandibles (creditos/debitos) y sub-formulario auto-inferido del esquema del primer sub-objeto.
    - `EditorTipoC`: `QTreeWidget` similar a B pero las celdas valor aceptan string o lista separadas por `|`.
    - `EditorTipoD`: `QTableWidget` 2 columnas (patron/reemplazo) editable.
  - Snapshot del JSON al cargar, contador de cambios recursivo, badges de color (amarillo=modificado, verde=nuevo) en celdas modificadas.
  - Botones globales: `+ Agregar` (segun tipo), `Cancelar` (revierte), `Guardar cambios` (escribe + backup automatico via `escribir_json`).
  - Advertencia al cambiar de JSON con cambios sin guardar.
- [x] **A3. Pantalla Configuracion** (`ui/ventanas/configuracion.py` creado, **~370 lineas**):
  - `PantallaConfiguracion` con filtros arriba: rango fechas (QDateEdit), proceso (QComboBox), nivel (QComboBox), buscador (QLineEdit con debounce de 300ms via QTimer).
  - `QTableWidget` con 5 columnas (Fecha, Proceso, Nivel, Modulo, Mensaje) con colores de fondo por nivel (rojo=ERROR, naranja=WARNING, blanco=INFO, gris=DEBUG).
  - Refresco automatico cada 5 segundos para ver logs en vivo (`_refresco_silencioso`).
  - Botones: `Exportar a Excel` (openpyxl con estilo), `Exportar a CSV`, `Limpiar registros antiguos` (pide dias, confirma con warning, filtra el log por fecha).
- [x] **A4. Pruebas manuales** via 5 smoke tests E2E (en la raiz del proyecto, **NO** en pytest todavia):
  - `smoke_ui.py`: imports + deteccion de tipos de los 8 JSONs (3 A, 1 B, 1 C, 2 D) + compilar todos los .py nuevos.
  - `smoke_ui_full.py`: instancia `VentanaPrincipal` con Qt offscreen, verifica las 4 pantallas + navegacion + `_ir_a_procesos_preseleccionado`.
  - `smoke_diccionarios.py`: instancia `PantallaDiccionarios`, carga los 8 JSONs, verifica que cada uno use el editor correcto.
  - `smoke_configuracion.py`: instancia `PantallaConfiguracion`, prueba filtros (Comprobante=28, Fierro+INFO=15, ERROR=0, ContApp=10, todos=80) + exportacion CSV/Excel + refresco silencioso.
  - `smoke_e2e_diccionarios.py`: edita `fierro/mapeo_descripciones.json` (tipo A) end-to-end: cargar -> editar -> cancelar -> editar de nuevo -> guardar con backup automatico -> restaurar original -> limpiar backups.
- [x] **Crear `data/backups/`**: carpeta pre-creada (los backups por defecto se guardan en `jsons/<proceso>/.backups/`).

### [x] Cambios en bitacora (sub-sesion 2026-07-27 PM)

Solicitados por el usuario para limpiar el visor de bitacora.

- [x] **NO registrar el inicio de la app**: eliminados de `main.py` los logs `============`, `ContApp iniciando (cli=...)` y `Procesos disponibles:`. El log de "Para ejecutar uno..." sigue saliendo solo si se ejecuta `--cli` (es ayuda al usuario). El listado de procesos en `--listar` ahora va a stdout, no al log.
- [x] **Orden newest-first**: `utils.bitacora.leer_registros()` ahora invierte la lista antes de devolverla (mas reciente arriba). `obtener_ultimo()` ajustada (ya no usa `reversed()` porque la lista viene invertida).
- [x] **Columna Modo**:
  - Los 3 procesos agregan `[PRUEBA]` al final del mensaje del log clave cuando `modo_prueba=True` (en `Generado:`/`FOAPAL generado:` para Comprobante, en `Excel procesado:` para Fierro y Zeus).
  - `Diccionarios` tambien agrega `[PRUEBA]` al log de guardado si el switch de modo_prueba esta activo.
  - `utils.bitacora` expone `es_modo_prueba(msg) -> bool` y `quitar_marca_prueba(msg) -> str`.
  - `PantallaConfiguracion` ahora tiene **6 columnas**: Fecha | Proceso | Nivel | **Modo** | Modulo | Mensaje. Modo muestra `PRUEBA` (naranja + bold), `PROD` (verde) o vacio.
  - Nuevo **filtro por Modo** en la UI: `Todos / Produccion / Prueba`.
  - Exports a Excel/CSV ahora incluyen la columna Modo y quitan la marca `[PRUEBA]` del mensaje exportado.
- [x] **Verificacion**:
  - `smoke_bitacora_cambios.py` (nuevo): verifica el orden newest-first + 5 casos de deteccion de marca `[PRUEBA]` (todos OK).
  - `smoke_bitacora_e2e.py` (nuevo): instancia `PantallaConfiguracion`, verifica 6 columnas, orden newest-first, y agrega/remueve una linea `[PRUEBA]` al log para verificar la deteccion y el filtro.

### Verificacion final

- **Smoke tests (7/7 OK)**:
  - `smoke_ui.py` → imports OK, 80 registros parseados del log, ult. proceso = "fierro", 8 JSONs tipados.
  - `smoke_ui_full.py` → `VentanaPrincipal` instanciada, 4 pantallas creadas, navegacion OK.
  - `smoke_diccionarios.py` → los 8 JSONs cargados con editor correcto (A/A/B/A/A/A/D/D).
  - `smoke_configuracion.py` → filtros reducen filas correctamente (80→28/0/10/15).
  - `smoke_e2e_diccionarios.py` → editar → cancelar → guardar con backup → restaurar archivo.
  - `smoke_bitacora_cambios.py` → orden newest-first OK, 5/5 casos de deteccion `[PRUEBA]`.
  - `smoke_bitacora_e2e.py` → 6 columnas, orden OK, marca `[PRUEBA]` detectada y quitada del mensaje visible, filtro por modo OK.

### [ ] Pendientes (para proxima sesion)

- [ ] Validar procesos con archivos reales del usuario en modo produccion (**Fase B** del plan).
- [ ] Pruebas pytest del nucleo (**Fase 4**): mover los smoke_*.py a `tests/test_ui_*.py` + agregar `test_smoke.py`, `test_comprobante_e2e.py`, `test_fierro_e2e.py`, `test_zeus_e2e.py`, `test_json_manager.py`, `test_archivos.py`, `test_bitacora.py`.
- [ ] Empaquetar con PyInstaller (**Fase 5**).
- [ ] `git push` + tag `v1.0.0` (**Fase E**).

### Lecciones de la sesion

- **Monkey-patching de QMessageBox**: para tests E2E sin dialogos, monkey-patchear `QMessageBox.question`/`warning`/`information`/`critical` a staticmethods que retornen un boton por defecto.
- **Tabla se reconstruye despues de cancelar**: cuando se llama a `_on_cancelar` se reconstruye el editor completo, por lo que cualquier referencia a widgets internos (`p._editor_widget.tabla`) queda obsoleta. Reobtener la referencia despues del cancel.
- **Backup por defecto de `escribir_json`**: se guarda en `<directorio_del_json>/.backups/` (no en `data/backups/`). Se puede sobreescribir pasando `carpeta_backups`.
- **Debounce timer en filtros**: aplicar filtros 300ms despues de dejar de tipear evita re-filtrar en cada tecla. Pero los tests deben llamar `_aplicar_filtros()` directo para verificar el resultado sin esperar.
- **`QT_QPA_PLATFORM=offscreen`**: permite instanciar widgets Qt en CI / tests sin display. Warning de fuentes es benigno (Qt ya no las incluye).
- **Widgets Qt y `processEvents()`**: despues de cambiar `currentRow`, `setText`, `setCurrentText` etc. hay que llamar `QApplication.processEvents()` para que se propaguen las senales.
- **Cambios no detectados por cancel**: `_on_cancelar` reconstruye la tabla llamando a `_cargar_tabla()` que hace `setItem` -> el item tiene un `UserRole` con la clave original y texto con el valor original. Si el test setea texto directamente sin disparar `itemChanged`, el `_on_change` no se entera.
- **Logs como contrato**: agregar `[PRUEBA]` al final del mensaje (sin un campo nuevo en el log) mantiene retro-compatibilidad con archivos `.log` existentes y permite parseo regex simple. La marca se quita de la visualizacion pero se preserva en el archivo para auditoria.

### Proxima sesion (recomendado)

- [ ] Empezar la **Fase B**: coordinar con el usuario para obtener un ZIP Bancolombia real + Excels reales de Fierro y Zeus. Hacer backup de los originales antes de procesarlos en modo produccion.
- [ ] Validar FOAPAL generado contra el archivo real (pendiente de la sesion 2026-07-24).
- [ ] Discutir el bug del filtro TC en `fierro.py` (filas descartadas vs preservadas).

### Notas

- Workspace: `c:\Users\lfloaiza\Documents\Demo`.
- Branch: `main`. **NUEVO**: 16+ commits locales (aun no pusheados).
- Plan completo en `/memories/session/plan.md`.
- 7 smoke tests en la raiz del proyecto: `smoke_ui.py`, `smoke_ui_full.py`, `smoke_diccionarios.py`, `smoke_configuracion.py`, `smoke_e2e_diccionarios.py`, `smoke_bitacora_cambios.py`, `smoke_bitacora_e2e.py`.


### [x] Refactor Pantalla Diccionarios - agrupar por proceso (sub-sesion 2026-07-27 PM)

Solicitado por el usuario: el listado plano de 8 JSONs era poco legible.

- [x] **Mapeos de nombres legibles** agregados en `editor_json.py`:
  - `NOMBRES_JSON` mapea cada uno de los 8 archivos a un titulo amigable (FOAPAL, NIT Bancolombia, Mapeo de Auxiliares, etc.).
  - `NOMBRES_PROCESO` mapea `comprobante`/`fierro`/`zeus` -> `Comprobante`/`Fierro`/`Zeus`.
  - Funciones helper `_nombre_proceso(codigo)` y `_nombre_json_legible(proceso, archivo)`. Fallback para JSONs nuevos.
- [x] **Lista plana -> Tree agrupado por proceso**: el widget `QListWidget` se reemplazo por un `QTreeWidget` con una seccion expandible por proceso (en bold + fondo azul claro), y un hijo por JSON con su nombre legible. Las secciones no son seleccionables.
- [x] **Quitado el badge de tipo A/B/C/D**: eliminado el label `_lbl_tipo` del header derecho. La API `TIPO_NOMBRE` fue reemplazada por `NOMBRES_JSON` + `NOMBRES_PROCESO`.
- [x] **API ajustada**: `_on_seleccionar_json(idx: int)` paso a `_on_seleccionar_json()` (sin argumentos) que consulta `_item_seleccionado()` para obtener el path/proceso del item con `UserRole` valido.
- [x] **Imports limpiados**: removidos `QDialog`, `QDialogButtonBox`, `QFormLayout`, `QLineEdit`, `QListWidget`, `QListWidgetItem`, `QPlainTextEdit`, `QScrollArea`, `QSizePolicy`. Agregado `QFont`.

### Bug encontrado y corregido

- [x] **Indentacion rota**: `_cargar_lista_jsons(self)` quedo anidado dentro de `_construir_ui` por un error de copiado/pegado. Python lo definio como una funcion local que **nunca se invoca**, dejando `_arbol` vacio. Corregido reescribiendo el metodo con la indentacion correcta (4 espacios para `def`, 8 para el cuerpo).

### Verificacion del refactor

- [x] `smoke_diccionarios.py` actualizado para iterar el tree y los 4 sub-editores.
- [x] `smoke_e2e_diccionarios.py` actualizado para extraer el path del `QTreeWidgetItem` via `UserRole`.
- [x] Ambos pasan OK: 8 items visibles con titulos legibles (Comprobante / FOAPAL, Fierro / Mapeo de Tarjetas, etc.), edicion + cancel + guardar con backup automatico funciona end-to-end.

### Lecciones adicionales

- **def anidados**: una funcion local `def` con `self` parece valida sintacticamente pero **nunca se invoca** desde fuera. Si la UI no muestra datos, revisar si los metodos que deberian poblar widgets quedaron anidados por accidente.
- **VS Code + formateador automatico**: un formateador que auto-corre al guardar puede REVERTIR cambios externos al disco sin avisar. Solucion: cerrar el archivo en el editor antes de escribir.
- **Smoke tests con listas -> trees**: actualizar tests E2E es trivial cuando el contrato cambia: el path del archivo se guarda en `Qt.ItemDataRole.UserRole`, asi que solo hay que extraerlo del `QTreeWidgetItem`.


## Sesion 2026-07-24

**Resumen:** Sesion inicial del proyecto. Se monto la estructura base del proyecto desde cero, se migraron los scripts originales al patron `ProcesoBase`, se optimizaron los cuellos de botella, se implemento la UI base y se corrigieron varios bugs.

### [x] Completadas

- [x] **Setup inicial (Fase 1)**: estructura de carpetas, venv con Python 3.14.3, instalacion de dependencias (PySide6, pandas, openpyxl, pytest, pyinstaller), `requirements.txt`, `README.md`, `.gitignore`, primer commit.
- [x] **Nucleo (Fase 2)**: `ProcesoBase` + 3 procesos (Comprobante, Fierro, Zeus) + `utils/` (archivos, bitacora, json_manager con deteccion A/B/C/D) + 8 JSONs reales migrados desde `data/`.
- [x] **Migracion de scripts reales**: logica de `scripts/GenerarComprobante.py`, `InterfazFierro.py`, `InterfazZeus.py` portadas a `procesos/` con refactor para que reciban archivos por parametro (sin depender de `~/Downloads`) y respeten modo_prueba.
- [x] **Limpieza**: borrado de placeholders viejos (`.bak`, JSONs de muestra, `__pycache__`).
- [x] **Bug fix Zeus**: auto-deteccion de la hoja con columna `Cuenta1` (el script original tomaba siempre la primera hoja, lo que falla con Excels que tienen `Hoja1` como metadata).
- [x] **Optimizacion `writer_excel` de Fierro**: refactor con openpyxl `write_only=True` (251s -> 49s, 5.1x mas rapido). Estrategia hibrida que preserva `Diario 2026` y agrega 2 hojas nuevas.
- [x] **Optimizacion `writer_excel` de Zeus**: misma estrategia aplicada al Zeus (125k filas, ~170s).
- [x] **Documentacion `sep="|"`**: comentario explicando por que es necesario en comprobante (el CSV trae comas internas en la descripcion).
- [x] **Optimizacion filtro fiduciario**: `.apply(lambda row: any(...), axis=1)` -> `.eq(cuenta).any(axis=1)` (vectorizado en C).
- [x] **Bug fix FOAPAL**: `_aplicar_foapal` usaba `fila.iloc[3]` que en el original era codigo de concepto pero en el refactor es fecha (la estructura cambio por la insercion de `Codigo Contable`). Corregido a `iloc[6]` (codigo) y `iloc[7]` (descripcion).
- [x] **Constantes con nombre** para columnas del CSV: `COL_CUENTA`, `COL_FECHA`, `COL_CODIGO_CONCEPTO`, etc. (en vez de numeros magicos).
- [x] **Reemplazo de cuenta Bancolombia por NIT universidad** en `fzrcoco.xlsx` usando `nit_bancolombia.json`. Resultado: 1784 filas con `890903938` (universidad) + 94 con `830054539` (cuenta interna/fiduciaria).
- [x] **UI base (Fase 3 parte 1)**: `app/config.py` (singleton con rutas y procesos), 4 widgets (`BannerModoPrueba`, `SwitchModoPrueba`, `DropZone`, `TablaResultados`), `VentanaPrincipal` con sidebar + 4 pantallas + banner + switch.
- [x] **Banner siempre visible**: cambio de show/hide a estilo (naranja/verde) porque `setVisible(True)` no surte efecto en widgets hijos antes de mostrar la ventana.
- [x] **Default modo produccion**: por seguridad, la app arranca con `modo_prueba=False`.
- [x] **Pantalla Procesos (Fase 3 parte 2)**: `PantallaProcesos` con flujo de 2 vistas (grid de tarjetas + vista de ejecucion), `WorkerEjecucion` (QThread para no bloquear UI), `TarjetaProceso` widget.
- [x] **`context.md` actualizado**: 3 secciones (Funcionalidades, Diseno de Interfaz, Estructura).

### [ ] Pendientes

- [ ] Probar los procesos con archivos reales del usuario en modo produccion (los tests fueron todos en modo prueba).
- [ ] Pantalla **Diccionarios**: editor inteligente de los 8 JSONs (Tipo A/B/C/D) con badges "Modificado"/"Nuevo", backup automatico, botones Cancelar/Guardar.
- [ ] Pantalla **Configuracion**: tabla de bitacora con filtros (fecha, tipo, proceso), exportar a Excel/CSV, limpiar registros.
- [ ] Pantalla **Inicio**: dashboard con tarjetas de los 3 procesos + panel "Ultimo ejecutado".
- [ ] Pruebas pytest (Fase 4): smoke tests + E2E con archivos sinteticos.
- [ ] Empaquetado con PyInstaller (Fase 5): generar `.exe` instalable.
- [ ] `git push` para subir los commits a `origin/main` (actualmente hay 1 commit ahead).

### [ ] Proxima sesion

- [ ] **Validar FOAPAL** generado contra el archivo real de Bancolombia para confirmar que las claves se mapean correctamente.
- [ ] Considerar si la columna `col 4 (Identificador)` y `col 8 (Valor numerico)` del CSV necesitan algun procesamiento o se pueden ignorar.
- [ ] Discutir si el bug del filtro TC en `fierro.py` (filas descartadas vs preservadas) requiere algun cambio. El refactor actual preserva el comportamiento del original.
- [ ] Disenar el editor de JSONs: como manejar el caso donde el usuario edita mientras se ejecuta un proceso? (probablemente no es problema, son pantallas separadas).

### Notas

- Workspace: `c:\Users\lfloaiza\Documents\Demo`.
- Branch: `main`, 15 commits locales, 1 commit ahead de `origin/main`.
- Tests verificados: comprobante (2.79s con 2746 filas), fierro (48s con 27k filas), zeus (171s con 125k filas). Todos producen el mismo contenido que el script original.
- **Hallazgo importante**: el script original `scripts/GenerarComprobante.py` tenia un bug latente en `_aplicar_foapal` que nunca se manifesto porque el DataFrame que recibia tenia la estructura antigua. Al migrar, expusimos el bug y lo corregimos.