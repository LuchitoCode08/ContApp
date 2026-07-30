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


## Sesion 2026-07-27 (Fase 4 - Suite pytest)

**Resumen:** Se creo la suite de tests pytest del nucleo (sin UI). **Resultado: 86 tests pasando en ~5 segundos**, organizados en 7 archivos (`test_smoke.py`, `test_archivos.py`, `test_json_manager.py`, `test_bitacora.py`, `test_comprobante_e2e.py`, `test_fierro_e2e.py`, `test_zeus_e2e.py`) + entry point `tests/run_all.py`.

### [x] Completadas (Fase 4)

- [x] **`tests/test_smoke.py` (6 tests)**: imports + `app.config.Config` singleton + registro de procesos (`app.procesos.PROCESOS`) + instanciar cada proceso + `ResultadoProceso` dataclass + compilacion de todos los .py de `app/`, `procesos/`, `utils/`, `ui/`.
- [x] **`tests/test_archivos.py` (12 tests)**: `timestamp_unico` (formato + sin colisiones en 1000 calls), `carpeta_resultados` crea `YYYY-MM/`, `carpeta_modo_prueba` crea `_prueba_YYYY-MM/`, `copiar_a_carpeta` (basico + duplicado -> sufijo `_1`), `mover_a_carpeta` (borra origen), `listar_archivos` (con/sin filtro extensiones + carpeta inexistente).
- [x] **`tests/test_json_manager.py` (12 tests)**: `detectar_tipo` para A/B/C/D + vacio -> A, `leer/escribir_json` roundtrip, `escribir_json` con backup, `escribir_json(sin_backup=True)` no crea backup, primer archivo crea backup, preservacion de tildes y caracteres especiales, `indent=2`.
- [x] **`tests/test_bitacora.py` (23 tests)**: `configurar()` con/sin path, `log()` retorna logger singleton, `leer_registros` parsea formato, vacio -> lista vacia, newest-first (reversed), `limit`, archivo inexistente -> lista vacia, lineas de continuacion, `es_modo_prueba` parametrizado (7 casos), `quitar_marca_prueba` (3 casos), `obtener_ultimo` con/sin filtro por proceso.
- [x] **`tests/test_comprobante_e2e.py` (10 tests)**: `validar_archivos` (valido / no ZIP / vacio), `ejecutar` modo_prueba genera archivos en carpeta `_prueba_YYYY-MM/`, modo_produccion escribe in-place, genera FOAPAL, extensiones .xlsx, ZIP sin CSVs (falla elegante), ZIP con CSV minimo viable, `LOG_PREFIX == "[Comprobante]"`.
- [x] **`tests/test_fierro_e2e.py` (11 tests)**: `validar_archivos` (valido / vacio / muchos / extension invalida), modo_prueba copia a `_prueba_YYYY-MM/`, modo_produccion modifica in-place, Excel resultante tiene 3 hojas (`Diario 2026` + `- Copia` + `Comprobante`), filas coinciden, detalles de filas, `LOG_PREFIX == "[Fierro]"`, error elegante si no existe la hoja `Diario 2026`.
- [x] **`tests/test_zeus_e2e.py` (12 tests)**: `validar_archivos` (valido / vacio / muchos / extension invalida), modo_prueba copia a `_prueba_YYYY-MM/`, modo_produccion modifica in-place, Excel resultante tiene `Exportar` + `Exportar - Copia` + `Depurado`, aplica auxiliares 8 -> 6 digitos (`11902101` -> `119021`), agrega `Valor2/BaseAbs/Tarifa`, detalles de filas, `LOG_PREFIX == "[Zeus]"`, error elegante si no hay columna `Cuenta1`.
- [x] **`tests/run_all.py`**: entry point `python -m tests.run_all` que invoca `pytest tests/ -v` y muestra `[OK] Todos los tests pasaron.` o `[FAIL] pytest retorno N`.

### Bugs encontrados y corregidos durante la implementacion

- **`utils/bitacora.py` UnboundLocalError**: un `from pathlib import Path` LOCAL dentro del `except` en `_resolver_ruta_bitacora` hacia que Python tratara `Path` como local en toda la funcion. **Fix**: agregar `from pathlib import Path` a los imports globales del modulo y borrar el local.
- **`obtener_ultimo` sin `ruta_bitacora`**: la firma original era `obtener_ultimo(proceso=None)` y siempre leia el log global. **Fix**: extender firma a `obtener_ultimo(proceso=None, ruta_bitacora=None)` para que los tests puedan usar un log en `tmp_path`.
- **Fierro/Comprobante con `tmp_path`**: `ProcesoFierro.__init__` resuelve `RAIZ / "jsons" / "fierro"` para leer los JSONs. Para testear en `tmp_path` hay que **copiar los JSONs reales** al `tmp_path/jsons/<proceso>/` antes de patchear `RAIZ` con `monkeypatch.setattr`. **Patron** aplicable a Comprobante (4 JSONs), Fierro (3) y Zeus (1).
- **Modo_prueba en Fierro/Zeus**: NO agrega sufijo `_prueba` al nombre del archivo. La marca de modo_prueba esta SOLO en la carpeta `_prueba_YYYY-MM/`. (Distinto de Comprobante, que tampoco lo agrega; la convencion del proyecto es la carpeta.)

### Verificacion final

- **`pytest tests/` -> 86 passed in 4.97s** (sin warnings).
- **`python -m tests.run_all` -> 86 passed in 5.46s** + `[OK] Todos los tests pasaron.`
- Distribucion: `test_smoke.py` 6 / `test_archivos.py` 12 / `test_json_manager.py` 12 / `test_bitacora.py` 23 / `test_comprobante_e2e.py` 10 / `test_fierro_e2e.py` 11 / `test_zeus_e2e.py` 12.

### Lecciones de la sesion

- **JSONs reales en tmp_path para tests E2E**: copiar con `shutil.copy2(RAIZ/"jsons"/<proceso>/<archivo>.json, tmp_path/"jsons"/<proceso>/<archivo>.json)` permite que `__init__` encuentre los mapeos sin tocar el repo. Patron reusable para los 3 procesos.
- **Aserciones sobre el filesystem son mas fragiles que sobre DataFrames**: validar `len(df) == 2` es mas estable que `assert n_copia == 2` (que cuenta filas via `iter_rows`). Preferir asserts sobre DataFrames siempre que se pueda.
- **Sucio > limpio cuando se valida un proceso existente**: NO intentar refactorizar `copy_data` para hacerlo "mas testeable" (romperia la migracion literal del script original). Testear la caja negra con Excels sinteticos y asserts sobre `archivos_salida` + `detalles` + estructura del Excel escrito.


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


## Sesion 2026-07-29

**Resumen:** Optimizaciones de UI (lag y crash), empaquetado completo (Fase 5), sistema de auto-actualizacion, versionado centralizado. **Resultado: el proyecto esta production-ready con pipeline de release automatico.**

### [x] Completadas

- [x] **Fix #1 (race condition)**: `utils/json_manager.py` agrega `adquirir_lock/liberar_lock/con_lock` con archivos `.lock` por JSON. Worker de ejecucion captura `BaseException` (no solo `Exception`) para que NUNCA cierre la app.
- [x] **Fix #2 (lag al volver a Inicio)**: `utils/bitacora.py` agrega `_leer_ultimas_n_lineas()` (seek desde el final del archivo) + cache de 30s en `obtener_ultimo()`. **Benchmark: 2.84 ms sin cache, 0.001 ms con cache (log de 4.7 MB).**
- [x] **Editor JSON con lock**: `_on_guardar` usa `con_lock(...)` antes de escribir. Si el archivo esta bloqueado, muestra "JSON bloqueado" en vez de pisar.
- [x] **Invalidacion de cache**: `_on_terminado` del worker llama a `invalidar_cache_obtener_ultimo()` para que el panel "Ultimo ejecutado" muestre el resultado nuevo al volver a Inicio.
- [x] **Versionado centralizado**: `app/version.py` con `__version__`, `APP_NAME`, `GITHUB_REPO`. Sidebar ahora muestra `v{__version__}` (antes hardcoded `"v1.0 · Fase 4"`).
- [x] **Auto-updater completo**:
  - `app/updater/version_utils.py`: semver (`parsear_version`, `comparar`, `hay_actualizacion`, `parsear_release`).
  - `app/updater/checker.py`: `UpdaterChecker(QThread)` + `chequear_actualizacion_bloqueante()` + `UpdaterError`.
  - `app/updater/downloader.py`: `UpdaterDownloader(QThread)` con progreso 0-100, cancelacion, escritura atomica (`.partial` -> final).
  - `ui/ventanas/dialogo_actualizacion.py`: modal con notas en markdown, boton "Descargar e instalar", barra de progreso.
  - Integracion en `principal.py`: boton "🔄 Actualizar" en footer + `QTimer.singleShot(1500, ...)` para chequeo silencioso al iniciar.
- [x] **Empaquetado (Fase 5)**:
  - `app/config.py`: `_detectar_raiz()` usa `sys.executable.parent` cuando `sys.frozen=True`. `_data_dir()` y `_log_dir()` helpers monkey-patcheables. `guardar_preferencias` usa `PREFERENCIAS.parent` para que monkey-patching funcione.
  - `ContApp.spec` (PyInstaller): `--onedir`, `console=False`, bundlea `jsons/` como fallback, oculta modulos innecesarios (tkinter/wx/matplotlib/scipy/pytest).
  - `ContApp.iss` (Inno Setup): instala en `%LOCALAPPDATA%\ContApp\` sin UAC (`PrivilegesRequired=lowest`), compresion LZMA2, accesos directos, desinstalador registrado.
  - `.github/workflows/release.yml`: al pushear tag `v*.*.*`, valida version contra `app/version.py`, build con PyInstaller, instala Inno Setup via choco, genera instalador + portable.zip, crea **draft release** en GitHub.
  - `.github/workflows/tests.yml`: corre pytest en cada PR/push.
  - `.github/dependabot.yml`: vigila las 4 actions, abre PRs semanales para minor+patch, ignora major bumps (decision manual).
- [x] **Pines de versiones exactas**: actions migradas de `@v5/@v6/@v4/@v2` a `@v5.0.0/@v6.1.0/@v4.6.2/@v2.4.1` para maxima reproducibilidad. Combinado con Dependabot: parches automaticos + major bumps manuales.
- [x] **Bug encontrado y arreglado**: `liberar_lock` pasaba la ruta del .lock a `lock_adquirido()` (que espera la ruta del JSON). Tests lo detectaron al primer run. Fix: derivar la ruta del JSON antes de chequear.

### [ ] Pendientes (registradas para no perder el hilo)

#### Tier 1 - UX wins

- [x] **#1 Editor JSON lazy**: `_cargar_lista_jsons()` crea solo secciones (procesos), colapsadas con placeholder "Cargando...". Los archivos se cargan via `itemExpanded` solo cuando el usuario expande la seccion. Idempotente (no duplica). Implementado en sesion 2026-07-29 (PM).
- [ ] **#2 Debounce de `_aplicar_tema()`**: al cambiar tema, re-aplica QSS a muchos widgets en el mismo ciclo. Agrupar en 1 repaint (50-100 ms).
- [ ] **#3 Indicador de progreso real**: el `QProgressBar` actual es indeterminate (spinner). Agregar `progreso` signal al Worker para mostrar % real.
- [x] **#4 Cancelar proceso en curso**: `WorkerEjecucion.cancelar()` ya esta conectado a `btn_cancelar` (estilo `danger`) con confirmacion `QMessageBox.question`. Implementado en sesion 2026-07-29 (PM).
- [ ] **#5 Logs filtrables en UI**: tabla en Configuracion hoy muestra todo. Agregar filtros por nivel/proceso/fecha con UI dedicada.

#### Tier 2 - Robustez

- [ ] **#6 Persistencia de `EN_DESARROLLO` de Zeus**: hoy hardcoded `True` en `procesos/zeus.py`. Cuando bajen a `False`, decidir si persiste o siempre False.
- [ ] **#8 Tests E2E del instalador**: test que corra el `.exe` y verifique que abre ventana + lee JSONs + escribe outputs.
- [ ] **#9 Smoke test del `.exe` en CI**: step que lance `dist/ContApp.exe`, espere 5s, verifique vivo, lo mate.

#### Tier 3 - Polish

- [ ] **#10 Icono del .exe**: `.ico` propio. Hoy usa el icono default de PyInstaller.
- [ ] **#11 Changelog automatico**: hoy el body del release es estatico. Generar desde commits convencionales.
- [ ] **#12 Documentacion de usuario** (`docs/USER_GUIDE.md`): manual con capturas, paso a paso.
- [ ] **#13 Type hints completos**: hay `Any` en algunos lados. `mypy --strict` para enforce.
- [ ] **#14 Tests parametrizados faltantes**: `es_modo_prueba` con 6 casos, podria tener 20+.
- [ ] **#15 Internacionalizacion**: hoy todo en espanol. `gettext` para futuro i18n.

### [ ] Riesgos / cosas a vigilar

- [ ] **Deprecation futura de GitHub Actions v5/v6**: Dependabot avisa, hay que actuar.
- [ ] **Antivirus y PyInstaller**: firmas pueden romperse. Considerar code signing (largo plazo).
- [ ] **Inno Setup 6 deprecation**: bajo riesgo por ahora (sigue activo).
- [ ] **PySide6 breaking changes**: monitorear con tests E2E.

### [ ] Proxima sesion

- [ ] Arrancar con **#4 (Cancelar proceso)**: pequeno y util, le da control al usuario. Conectar `WorkerEjecucion.cancelar()` al boton existente + dialogo de confirmacion.
- [ ] O **#1 (Editor JSON lazy)** si hay tiempo: mejora concreta con muchos JSONs.

### Notas

- Tests: **176 passed, 4 skipped** (los 4 skipped son tests de ejecucion de Zeus mientras `EN_DESARROLLO=True`).
- Build local exitoso: `dist/ContApp/ContApp.exe` (170 MB en 888 archivos), arranca correctamente.
- Commit hash local pendiente de push a `origin/main` (segun ultima verificacion).
- **Fase 5 cerrada**. Pipeline de release automatico funcional: tag -> build -> instalador -> GitHub Release.

---

## Sesion 2026-07-29 (Tier-1 #1 Editor JSON lazy)

**Resumen:** La pantalla Diccionarios ahora hace **lazy load**: solo crea las secciones (procesos) al abrir, con placeholder "Cargando...". Los JSONs de cada proceso se listan cuando el usuario expande la seccion. Para 8 JSONs el ahorro es marginal, pero la optimizacion escala bien a 50+ JSONs (caso futuro). **8 tests nuevos, suite total 193 passed + 4 skipped, 0 regresiones.**

### [x] Completadas

- [x] **Lazy load en `_cargar_lista_jsons()`** (`ui/ventanas/editor_json.py`):
  - Antes: enumeraba TODOS los `.json` con `glob`, creaba 1 `QTreeWidgetItem` por archivo, expandia todas las secciones. O(N archivos).
  - Ahora: itera `JSONS_DIR.iterdir()` y crea solo 1 `QTreeWidgetItem` por proceso (seccion). O(procesos). Cada seccion arranca **colapsada** con un hijo placeholder "Cargando...".
  - Conectado `itemExpanded` a nuevo `_on_expandir_seccion` que: lee `glob("*.json")` del directorio del proceso, quita el placeholder y agrega los items reales (idempotente).
  - Filtro de secciones: ignora carpetas que empiezan con `_` o `.` (backups, caches, work-in-progress).
  - Directorio de proceso vacio al expandir -> placeholder "(sin archivos JSON)".
  - Directorio de proceso desaparecido -> placeholder "(directorio no disponible)" (NO crashea).
- [x] **Tests**: nuevo archivo `tests/test_editor_json_lazy.py` con **8 tests**:
  - Estado inicial: 3 secciones, 0 items cargados, todas con placeholder.
  - Filtrado: carpetas `_basura` (con `_`) NO aparecen como seccion.
  - Expansion carga hijos del proceso.
  - Re-expansion es idempotente (no duplica).
  - Directorio sin JSONs -> placeholder amigable.
  - `JSONS_DIR` inexistente -> UI abre sin crashear.
  - Directorio de proceso desaparecido tras cargar -> mensaje de error.
  - Seleccionar un item sigue disparando `_on_seleccionar_json` correctamente.

### Antes vs Despues (apertura de Pantalla Diccionarios)

| Metrica | Antes (eager) | Ahora (lazy) |
|---|---|---|
| `QTreeWidgetItem` creados | 11 (3 secciones + 8 archivos) | 6 (3 secciones + 3 placeholders) |
| `QTreeWidgetItem` por seccion expandida | 8 | 0 hasta expandir |
| `QFileInfo.stat()` implícitos | ~8 | 0 hasta expandir |
| `Path.read_text()` o parsing | 0 | 0 (parseo sigue siendo al seleccionar) |
| Glob `*.json` calls | 3 (uno por proceso) | 0 inicial; 1 lazy por seccion expandida |

> El parseo real del JSON (`leer_json`) sigue siendo lazy: solo ocurre cuando el usuario selecciona el item. Eso ya estaba bien antes.

### Lecciones aprendidas

- **Placeholder + itemExpanded = patron Qt estandar para lazy load en trees**. La senal `itemExpanded(QTreeWidgetItem*)` solo se dispara cuando el usuario interactua (no en la construccion inicial), por lo que conectar ahi es 100% seguro.
- **Filtrar secciones vacias vs. mostrarlas como "sin JSONs"**: trade-off. Si filtras, el usuario no ve procesos nuevos hasta que tengan contenido. Si las dejas, el costo es 1 `QTreeWidgetItem` extra por proceso vacio (despreciable). Decidi **mostrarlas** con placeholder amigable para que el usuario sepa que ese proceso "existe" pero esta vacio.
- **Carpetas con prefijo `_` o `.`**: convencion universal para "archivos/carpetas internas" (`.git`, `.vscode`, `.backups`, `_pycache_`). Filtrarlas del listado es robusto y matchea expectativas del usuario.
- **`sorted(JSONS_DIR.iterdir())` ya estaba en el codigo**; el orden alfabetico es por nombre del archivo (no del proceso). En `comprobante/`: `dos.json` < `uno.json` ('d' < 'u' en ASCII).
- **Monkey-patch sobre `editor_mod.JSONS_DIR`**: la constante se importa al modulo, asi que `monkeypatch.setattr(editor_mod, "JSONS_DIR", tmp)` funciona limpio. NO hace falta patchear `app.config.JSONS_DIR` ni `_detectar_raiz`.

### Estado

- Tests: **193 passed, 4 skipped** (185 anteriores + 8 nuevos, 0 regresiones).
- UI: usuario ahora ve 3 secciones colapsadas al entrar a Diccionarios. Click en `▶` expande y carga los JSONs de ese proceso.
- Sin cambios visibles para el usuario actual (mismos nombres, misma jerarquia) - solo cambia el momento de carga.

### [ ] Proxima sesion

- [ ] **#2 (Debounce de `_aplicar_tema`)**: al cambiar tema, re-aplica QSS a muchos widgets en el mismo ciclo. Agrupar en 1 repaint (50-100 ms).
- [ ] **#3 (Progress real)**: el `QProgressBar(0,0)` solo es indeterminate; conectar a un `Signal(int)` del worker para mostrar % real.
- [ ] **(Opcional) Polear cancelacion en procesos**: refactor `ejecutar()` para aceptar `cancelado: Callable[[], bool]` y chequearlo en loops.
- [ ] **(Opcional) #5 Logs filtrables en UI**: filtros por nivel/proceso/fecha en Pantalla Configuracion.

---

## Sesion 2026-07-29 (Tier-1 #4 Cancelar proceso)

**Resumen:** Implementacion completa del flujo "Cancelar ejecucion" desde la UI. Se agrego el boton `btn_cancelar` (estilo `danger`, rojo) que aparece cuando arranca el worker y se oculta al terminar. Confirmacion con `QMessageBox.question` (default = No, opcion segura). Al confirmar, llama `WorkerEjecucion.cancelar()` y deshabilita el boton para evitar doble click. **9 tests nuevos, suite total 185 passed + 4 skipped.**

### [x] Completadas

- [x] **UI - boton Cancelar**: `ui/ventanas/ejecutar_proceso.py` agrega `btn_cancelar` (objectName="danger", cursor PointingHand, arranca oculto) en el `btn_row` del `_construir_ui()`.
- [x] **UI - confirmacion**: nuevo metodo `_cancelar_ejecucion` que muestra `QMessageBox.question` con default=No. Yes -> llama `self._worker.cancelar()`, deshabilita el boton y actualiza `estado` a "Cancelando ...".
- [x] **UI - visibilidad**: `_ejecutar` hace `self.btn_cancelar.show()` al arrancar el worker; `_on_terminado` y `_on_error` hacen `hide()` + `setEnabled(True)` al finalizar.
- [x] **Tema - estilo #danger**: `ui/recursos/tema.py` agrega bloque QSS para `QPushButton#danger` (rojo de marca, blanco en hover, gris cuando disabled). Reutiliza `p.danger` / `p.on_danger` / `p.surface_alt` / `p.fg_disabled` que ya existian en la paleta.
- [x] **Tests**: nuevo archivo `tests/test_cancelar_proceso.py` con 9 tests cubriendo estado inicial, no-op sin worker, confirm Yes (cancelar + disable), confirm No (no cancelar), y reset al terminar o fallar. Usa `QT_QPA_PLATFORM=offscreen` + monkeypatch sobre `QMessageBox`.

### Tests del flujo Cancelar

| Test                                          | Que verifica                                     |
|-----------------------------------------------|--------------------------------------------------|
| `test_btn_cancelar_aranca_oculto`             | Arranca hidden (no hay job)                      |
| `test_btn_cancelar_es_danger`                 | objectName="danger" (QSS lo pinta rojo)          |
| `test_btn_cancelar_arranca_habilitado`        | Enabled para cuando se muestre                   |
| `test_cancelar_sin_worker_es_noop`            | Click sin worker: no muestra dialog              |
| `test_cancelar_con_worker_detenido_es_noop`   | Worker existe pero `isRunning()==False`: no-op   |
| `test_cancelar_confirmado_llama_cancelar`     | Yes -> `cancelar()` llamado, btn disabled        |
| `test_cancelar_rechazado_no_llama_cancelar`   | No -> `cancelar()` NO llamado, btn enabled       |
| `test_on_terminado_oculta_btn_cancelar`       | `_on_terminado` hide + reset enabled             |
| `test_on_error_oculta_btn_cancelar`           | `_on_error` hide + reset enabled + "[ERROR]"     |

### Lecciones aprendidas

- **PowerShell + pytest + UTF-16**: `Tee-Object` en PS5.1 guarda en UTF-16 con BOM. Usar `Out-File -Encoding ascii` o redirigir con `>` para mantener salida legible desde el visor del host.
- **`QMessageBox.critical/information` en tests offscreen**: aunque `QT_QPA_PLATFORM=offscreen` no muestre la ventana, la llamada puede colgarse si el parent es un widget con event loop. Mejor parchar con `monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))`.
- **Fixture con QThread vivo**: el `tearDown` con `worker.wait(2000)` cuelga los tests. Regla: en tests, **nunca** crear un `WorkerEjecucion().start()` real; usar mocks que satisfagan `isRunning()` y `cancelar()`.
- **`ResultadoProceso` no tiene campo `proceso`**: solo `exito`, `mensaje`, `archivos_salida`, `archivos_salida_originales`, `detalles`. El nombre del proceso vive en otro lado (worker.proceso.LOG_PREFIX).

### Estado

- Tests: **185 passed, 4 skipped** (180 anteriores + 9 nuevos, 0 regresiones).
- UI: boton rojo aparece al ejecutar y se oculta al terminar. Confirmacion obligatoria para cancelar.
- **Limitacion conocida**: `ProcesoBase.ejecutar()` no polea `self._cancelado` en loops internos; la cancelacion es cooperativa (toma efecto en el yield natural entre operaciones de Excel). Para un archivo Fierro de 27k filas (~48s), el usuario ve "Cancelando ..." unos segundos hasta el siguiente yield. Refinar mas requiere pasar `cancelado: Callable[[], bool]` a `ejecutar()` y chequearlo en cada loop - **NO implementado en esta sesion**.

### [ ] Proxima sesion

- [ ] **#1 (Editor JSON lazy)**: cargar JSONs bajo demanda, no al abrir la ventana. Ganar tiempo de inicio.
- [ ] **#3 (Progress real)**: el `QProgressBar(0,0)` solo es indeterminate; conectar a un `Signal(int)` del worker para mostrar % real.
- [ ] **(Opcional) Polear cancelacion en procesos**: refactor `ejecutar()` para aceptar `cancelado: Callable[[], bool]` y chequearlo en loops.
