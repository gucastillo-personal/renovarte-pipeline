# Tasks — 0001 `codCategoria` (agrupación de alto nivel)

## Estimate

**Tamaño: M.** **Rango: 5-8 horas** de trabajo efectivo (sin contar
tiempo de espera por credenciales/acceso a la API real, que puede
bloquear la Tarea 1 si no están disponibles de entrada).

**Por qué M y no S:** el cambio de código en sí es chico (un campo nuevo,
una función pura, un archivo de dato), pero toca un modelo core
(`Product`) que se construye en 5 call-sites de test distintos, y suma un
módulo de verificación nuevo (con su propia función pura testeable +
comando CLI) que no existía antes — no es un simple "agregar una línea".

**Actualizado 2026-09-17** (tras coordinación con el agente de
`renovarte-catalogo`, spec espejo 0015): se sumó la Tarea 10
(`publish` copia también el archivo de mapeo hacia `renovarte-catalogo`).
**No mueve el estimate** — reusa el mecanismo `files_to_update` que ya
existe en `git_ops.prepare_branch`, es una entrada más en un diccionario +
un `check_file_for_leaks()` extra, no un mecanismo nuevo. Se mantiene
tamaño **M**, rango **5-8h**.

**Top riesgos que podrían romper el estimate:**
1. **Acceso a credenciales reales de Serlaca para la Tarea 1.** Si quien
   implementa no tiene `SERLACA_API_KEY`/`SERLACA_LACA_ID` a mano, AC-1 no
   se puede verificar de verdad y el trabajo se bloquea ahí (o se avanza
   con el resto en paralelo pero queda una tarea abierta al final —
   reportar, no improvisar el mapeo sin verificar).
2. **Conflicto de categoría repartida entre grupos** (ver plan.md §10):
   si la Tarea 1 encuentra que alguna `productLine` cae en más de un
   `productCategoryIds`, el diseño de mapeo por-categoría-completa no
   alcanza y hay que volver a plan.md antes de seguir con la Tarea 3+ — no
   es una tarea más, es un motivo de pausa y reporte.
   **Materializado y resuelto (2026-09-18):** pasó exactamente esto (11/24
   categorías); el CTO/CEO decidió la Opción 1 (`codCategoria` como
   `list[str]`, ver plan.md §1/§10) y las Tareas 2+ de abajo ya están
   reescritas sobre esa base — no vuelve a bloquear el estimate, pero sí
   suma trabajo neto respecto del diseño original (nuevas Tareas 3 y 8,
   cambios en `build_catalog.py`/`transform/run.py` que el plan original
   no tocaba). Tamaño sigue siendo razonable como **M**, pero probablemente
   en el extremo superior del rango original (6-9h en vez de 5-8h) por el
   trabajo extra de `ingest`.

## Tareas

> **RESUELTO (2026-09-18) — decisión del CTO/CEO.** La Tarea 1 encontró
> que 11/24 categorías específicas (`productLine`) aparecen repartidas
> entre más de un `productCategoryIds` de Serlaca (bloqueante reportado
> 2026-09-17, detalle en `docs/serlaca-api.md`). El CTO/CEO resolvió el
> bloqueo (Opción 1, 2026-09-18, ver `plan.md` §1/§10): `codCategoria`
> pasa a ser una **lista** (`list[str]`), y el dato de grupo se calcula
> por producto individual en `ingest` (tres llamadas reales a la API, ya
> no una tabla estática `categoría → grupo`). Las Tareas 2 en adelante,
> abajo, están reescritas sobre esta base — ya no hay tarea pausada.

- [x] **1. Verificar el mapeo contra la API real (AC-1) — antes de tocar
  la lógica de mapeo definitiva.**
  - [x] 1a. Crear `pipeline/ingest/verify_category_groups.py` con
    `fetch_category_group_samples()` (red, tres llamadas a
    `fetch_all_serlaca_pages` con `category_ids=[1]`/`[2]`/`[3]`) y
    `build_category_group_report()` (pura: agrupa por `categoria` limpia
    vía `clean_category`, excluye `professionalExclusive: true`, detecta
    conflictos y categorías no clasificadas). *Checkable: el módulo
    importa sin error, `mypy`/`ruff` en verde.*
  - [x] 1b. `tests/test_verify_category_groups.py` para
    `build_category_group_report()` con fixtures fijas (sin red): caso
    limpio (cada categoría en un solo grupo), caso con conflicto, caso con
    categoría no clasificada. *Checkable: los 3 tests nombrados pasan.*
  - [x] 1c. Subcomando `renovarte-pipeline verify-category-groups` en
    `cli.py` (mismo patrón que `cmd_ingest`/`cmd_transform`, usa
    `_load_env()`). *Checkable: `uv run renovarte-pipeline
    verify-category-groups --help` muestra el comando.*
  - [x] 1d. Correr `verify-category-groups` contra la API real con
    credenciales reales. Revisar el reporte: confirmar que las ~24
    categorías específicas hoy cargadas caen limpio en un solo
    `productCategoryIds` cada una, y que `"1"`/`"2"`/`"3"` son los únicos
    ids que devuelve Serlaca. *Checkable: reporte impreso, sin
    conflictos — si hay conflictos, PARAR y reportar (no seguir a la
    Tarea 3) en vez de improvisar.* **Resultado: CON CONFLICTOS (11/24
    categorías) — se paró acá, no se siguió a la Tarea 3, ver nota de
    bloqueo arriba.**
  - [x] 1e. Documentar el resultado en `docs/serlaca-api.md` (sección
    "Confirmado en la corrida real"): fecha, cantidad de categorías
    verificadas, resultado (limpio / con excepciones). *Checkable: sección
    nueva, con fecha, en el archivo.* **Resultado documentado: con
    excepciones (bloqueante).**

- [x] **2. `data/reference/serlaca_category_groups.json`.**
  - [x] Crear el archivo con los 4 pares `id → nombre` (spec, tabla
    decidida). *Checkable: JSON parsea, 4 claves exactas
    `{"1","2","3","4"}`.*
  - [x] Test dedicado confirmando las 4 claves exactas y valores no vacíos
    (AC-4). *Checkable: test nombrado en verde.*

- [x] **3. `pipeline/sources/serlaca_api.py::group_ids_by_product_code`**
  (nueva, reemplaza la Tarea 3 original — ver `plan.md` §1/§6, reescrito
  2026-09-18).
  - [x] 3a. Función pura `group_ids_by_product_code(samples: dict[str,
    list[Any]]) -> dict[str, list[str]]`: de los mismos `samples` que arma
    `fetch_category_group_samples` (id → `dataObjects`), arma `productCode
    → lista ordenada de ids donde apareció`. *Checkable: módulo importa,
    `mypy`/`ruff` verdes.*
  - [x] 3b. Tests (`tests/test_serlaca_api.py`, nuevo): producto en un solo
    grupo, producto en más de un grupo (la lista tiene los dos ids,
    ordenados), objetos malformados/sin `productCode` se ignoran sin
    romper. *Checkable: tests nombrados en verde.*

- [x] **4. `pipeline/transform/category_groups.py`** (reescrito
  2026-09-18 — ya no hay tabla estática `categoría → grupo`).
  - [x] 4a. `FALLBACK_COD_CATEGORIA = "4"` +
    `resolve_cod_categoria(raw_group_ids: list[str] | None) -> list[str]`:
    ordena y deduplica `raw_group_ids`; `None`/lista vacía → `["4"]`.
    *Checkable: módulo importa, `mypy` verde.*
  - [x] 4b. `tests/test_category_groups.py`: un id → se devuelve igual;
    varios ids con duplicados → ordenados y sin duplicados; `None`/`[]` →
    `["4"]` (AC-3). *Checkable: tests nombrados en verde.*

- [x] **5. `pipeline/models.py` — campo `codCategoria: list[str]` en
  `Product`.**
  - [x] Agregar el campo (requerido, sin default, posición inmediatamente
    después de `categoria`) + `model_validator` que rechaza lista vacía o
    ids fuera de `{"1","2","3","4"}`. *Checkable: `Product(...)` sin
    `codCategoria`, o con `codCategoria=[]`, o con un id inválido, lanza
    `ValidationError`; `mypy` verde.*

- [x] **6. `pipeline/transform/pricing.py::build_public_product`.**
  - [x] Nuevo parámetro `cod_categoria: list[str] | None = None`; setear
    `codCategoria=resolve_cod_categoria(cod_categoria)` al construir el
    `Product`. *Checkable: `test_pricing.py` existente sigue en verde sin
    modificar sus llamadas (el parámetro es opcional).*

- [x] **7. `pipeline/transform/build_catalog.py`** (nuevo respecto del
  plan original — ver `plan.md` §5, reescrito 2026-09-18).
  - [x] Nuevo parámetro `category_groups_by_codigo: dict[str, list[str]] |
    None = None` en `build_catalog()` (y passthrough opcional en
    `build_catalog_from_csv()`); resolver por `row.codigo.strip()` dentro
    del loop y pasarlo a `build_public_product`. *Checkable:
    `test_build_catalog_pdf_overlay.py` existente sigue en verde sin
    modificar sus llamadas (el parámetro es opcional, default `None` →
    fallback `["4"]` para todas las filas).*

- [x] **8. `pipeline/ingest/serlaca_download.py` + `pipeline/transform/run.py`**
  (nuevo respecto del plan original — ver `plan.md` §6).
  - [x] 8a. `serlaca_download.run()`: además del dump sin filtrar, llama
    `fetch_category_group_samples(env)` (reusa la Tarea 1), computa
    `group_ids_by_product_code(...)` (Tarea 3) y lo embebe en el crudo
    escrito a `raw_path` bajo la clave `categoryGroupsByProductCode`.
    *Checkable: test nuevo (`tests/test_serlaca_download.py`, red
    monkeypatcheada) confirma que el JSON escrito tiene esa clave con el
    mapeo esperado.*
  - [x] 8b. `transform/run.py`: lee `dump.get("categoryGroupsByProductCode")
    or {}` (degradación graciosa si falta — crudo viejo) y lo pasa a
    `build_catalog` como `category_groups_by_codigo`. *Checkable:
    `mypy`/`ruff` verdes; no rompe ningún test existente de `transform`.*

- [x] **9. Test de integración end-to-end en `build_catalog`.**
  - [x] Sumar un caso con `CostRow`s + un `category_groups_by_codigo` con
    un `codigo` en dos grupos, uno en un solo grupo, y uno ausente,
    confirmando: (a) todo producto resultante tiene `codCategoria` no
    vacío (AC-2), (b) el producto ausente del mapeo queda publicado con
    `codCategoria=["4"]`, no excluido (AC-3), (c) el producto en dos
    grupos lleva ambos ids, ordenados. *Checkable: test nombrado en
    verde.*

- [x] **10. Determinismo (AC-5).**
  - [x] Confirmar (test nuevo si no existe uno genérico ya) que correr
    `build_catalog`/`to_products_json` dos veces sobre el mismo input
    (mismas `CostRow`s + mismo `category_groups_by_codigo`) da el mismo
    output byte a byte, incluido `codCategoria`. *Checkable: test
    nombrado en verde.*

- [x] **11. Actualizar los 5 call-sites de test que construyen `Product`
  directamente** (`tests/test_models.py` ×2, `tests/test_price_diff.py`,
  `tests/test_publish_run.py`, `tests/test_pdf_match.py`) para pasar
  `codCategoria=[...]` (lista, no string). *Checkable: cada archivo de
  test pasa individualmente (`uv run pytest tests/test_models.py`, etc.).*

- [x] **12. Leak-check (AC-6) — regresión, no debería requerir cambios.**
  - [x] Correr `tests/test_leak_check.py` tal cual; si se quiere, sumar un
    caso explícito con `codCategoria`/nombres de grupo confirmando que no
    dispara ningún patrón `FORBIDDEN`. *Checkable: test(s) en verde.*

- [x] **13. `publish` distribuye el mapeo (A) hacia `renovarte-catalogo`**
  (agregado 2026-09-17 — necesario para que la spec espejo `0015` de
  `renovarte-catalogo` no duplique el mapeo; ver `plan.md` §6bis. Sin
  cambios por la actualización 2026-09-18 — el mapeo (A) es ajeno a que
  `codCategoria` sea string o lista.)
  - [x] 13a. En `pipeline/publish/run.py`: agregar
    `CATEGORY_GROUPS_DEST_REL_PATH = Path("public") / "data" /
    "serlaca_category_groups.json"`, `DEFAULT_CATEGORY_GROUPS_PATH =
    Path("data") / "reference" / "serlaca_category_groups.json"`, y un
    parámetro nuevo `category_groups_path` en `run_publish` (default =
    esa constante). Extender el diccionario que se le pasa a
    `prepare_branch` con esa segunda entrada **solo si el archivo
    existe** (degradación graciosa, mismo criterio que
    `load_pdf_prices()`). *Checkable: `mypy`/`ruff` en verde; los tests
    existentes de `test_publish_run.py` (que no crean este archivo) siguen
    pasando sin modificarlos.*
  - [x] 13b. Correr `check_file_for_leaks()` también sobre
    `category_groups_path` antes de tocar el checkout de
    `renovarte-catalogo`, mismo criterio que ya rige para
    `products_json_path` (abortar antes de cualquier cambio si hay hits).
    *Checkable: test nuevo — un `category_groups_path` con contenido que
    matchea `FORBIDDEN` bloquea el publish igual que hoy lo hace
    `products_json_path`.*
  - [x] 13c. `tests/test_publish_run.py`: test nuevo que, con
    `category_groups_path` apuntando a un archivo real, confirma que
    termina copiado en
    `<catalogo_clone>/public/data/serlaca_category_groups.json` dentro de
    la rama preparada (mismo patrón que el test ya existente para
    `products.json`). *Checkable: test nombrado en verde.*

- [x] **14. `make check` completo (ruff + mypy + pytest) en verde** con
  todo lo anterior. *Checkable: `make check` sale 0.*

- [x] **15. Actualizar `specs/README.md`.**
  - [x] Feature index: fila `0001` → status refleja lo construido (no
    "Backlog"/"Bloqueado"). Traceability matrix: `RF-09` → status
    actualizado.
  *Checkable: diff del archivo, sin tocar otras filas.*

- [x] **16. Correr un `transform` real de punta a punta** (con el crudo ya
  bajado por `ingest`, si hay uno disponible con
  `categoryGroupsByProductCode`) y confirmar a ojo, sobre una muestra del
  `products.json` resultante, que `codCategoria` aparece (lista no vacía)
  y tiene sentido contra `categoria` (p. ej. "Uñas" → contiene `"2"`
  y/o `"3"`, según lo verificado en AC-1). *Checkable: inspección manual
  documentada en el reporte final, no autoreportada sin evidencia
  (constitution §IV.17).* **Corrido 2026-09-18** con `ingest`/`transform`
  reales (434 crudos → 384 publicados). Resultado: todos los 384
  productos publicados tienen `codCategoria` no vacío; 0 cayeron en el
  fallback `["4"]` (los 3 grupos reales cubrieron el 100% del catálogo
  publicado, no solo el 24/24 de categorías de AC-1); 0 productos
  quedaron con más de un id simultáneo en esta corrida — la "repartición"
  detectada en AC-1 es a nivel *categoría* (productos distintos de la
  misma `categoria` caen en grupos distintos), no de un mismo producto en
  dos grupos a la vez: p. ej. `categoria: "Uñas"` tiene 44 productos, 39
  con `codCategoria: ["3"]` y 5 con `codCategoria: ["2"]`, ninguno con
  `["2","3"]` juntos; `categoria: "Antiage"` → consistente `["1"]`. La
  lista sigue siendo el diseño correcto (nada en el contrato garantiza que
  ningún producto individual caiga en dos grupos en el futuro), pero en
  los datos reales de hoy el caso "un producto en más de un grupo" no se
  dio.

- [x] **17. Correr `publish` (dry-run) de punta a punta** con el
  `products.json` y el `serlaca_category_groups.json` reales, contra un
  clon descartable de `renovarte-catalogo`, y confirmar que la rama
  preparada trae los dos archivos actualizados. *Checkable: `git diff
  --stat` de la rama preparada muestra ambos paths.* **Corrido
  2026-09-18** contra un clon local descartable (`git clone` a scratchpad,
  nunca el submódulo de trabajo real — borrado después de la corrida):
  `git diff --stat` de la rama preparada confirmó
  `public/data/products.json` (1200 líneas) y
  `public/data/serlaca_category_groups.json` (6 líneas, contenido
  verificado igual al de `data/reference/` de este repo) — ambos en el
  mismo commit (`chore(data): actualizar products.json
  (renovarte-pipeline)`), dry-run, sin push ni PR. El warning esperado de
  `price-diff no generado (no bloqueante)` apareció porque el
  `products.json` hoy publicado en `renovarte-catalogo` todavía no tiene
  `codCategoria` (spec espejo `0015` pendiente del lado de ese repo) — no
  bloqueó el publish real, tal como está diseñado.

## Notas / preguntas abiertas que quedan fuera de este tasks.md

- **Nombre del grupo fallback ("Otros"):** se usa tal cual lo sugiere el
  spec en la Tarea 2 — si el CTO/CEO lo cambia después, es una edición de
  una línea en el JSON de la Tarea 2, sin tocar código.
- **Consumo del mapeo (A) del lado de `renovarte-catalogo`:** la Tarea 10
  resuelve la *distribución* (que el archivo llegue por PR); cómo
  `renovarte-catalogo` lo lee/versiona una vez recibido es responsabilidad
  de su propio `plan.md` (spec espejo `0015`), fuera de alcance de este
  repo.
