# RFC-0001 — Arquitectura del pipeline de ingesta RenovArte

| | |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 2026-09-17 |
| **PRD relacionado** | [PRD — Pipeline RenovArte](../PRD/PRD-pipeline-renovarte.md) |
| **Reemplaza** | — (primer RFC propio de este repo; hasta ahora la arquitectura vivía solo en `renovarte-parent/PLAN.md` y en el `README.md` de este repo, sin RFC formal — ver `docs/rfc/README.md`) |
| **Enmiendas** | 2026-09-17 — §2.4: nuevo campo público `codCategoria` + archivo de mapeo `data/reference/serlaca_category_groups.json` (spec [0001](../../specs/0001-agrupacion-alto-nivel-categorias/spec.md)). **2026-09-18 — §2.4: `codCategoria` pasa de string único a `list[str]`** (un producto puede pertenecer a más de un grupo de Serlaca a la vez — decisión del CTO/CEO tras la verificación real de AC-1, ver más abajo). |

> **Por qué este RFC nace ahora, y no antes:** `docs/rfc/README.md` dejaba
> pendiente escribir el primer RFC propio "la primera vez que un cambio de
> arquitectura lo amerita". La spec 0001 (`codCategoria`) es exactamente
> ese disparador: agrega una clave al schema público que este repo produce
> (`public/data/products.json`), lo cual constitution §II.7 define como un
> cambio que "requiere enmendar el RFC en ambos repos". Este documento
> transcribe la arquitectura ya construida (fuentes de `PLAN.md` §"Qué se
> migra" y del `README.md` de este repo) como línea de base (§1-§4,
> "Aceptado", sin cambios de comportamiento respecto de lo ya en
> producción), y agrega la enmienda concreta de la spec 0001 en §2.4.

## 1. Contexto

`renovarte-pipeline` es el único responsable de ingerir y transformar datos
de catálogo (costo, categorías, precio) para RenovArte, separado de
`renovarte-catalogo` (que solo lee y muestra `products.json`). Nace de la
migración descripta en `renovarte-parent/PLAN.md` (2026-09-13 a
2026-09-14): todo lo que antes eran `scripts/*.ts` en `renovarte-catalogo`
pasó 1:1 a Python (`pyproject.toml`, `uv`, `pydantic`, `pytest`), más dos
piezas nuevas construidas directo acá (extracción del PDF de LACA con
`pdfplumber`, y `publish` — el paso que abre PR contra `renovarte-catalogo`).

El contrato entre los dos repos es el schema público de `products.json`,
originalmente definido en `RFC-0001 §2.4` de `renovarte-catalogo` — ese
documento sigue siendo la fuente canónica del schema para quien lee desde
el lado del catálogo, pero como el pipeline es quien hoy *produce* ese
archivo, este RFC documenta el mismo contrato desde el lado de origen y es
donde este repo registra sus propias enmiendas al schema (siempre en
paralelo con la enmienda espejo del lado de `renovarte-catalogo`, que
corre por su propio spec-kit).

## 2. Decisión

### 2.1 Stack

Python 3.13 · `uv` · Pydantic (todo modelo que cruza un límite) · `httpx`
(API de Serlaca) · `pdfplumber` (PDF de LACA) · `pytest`/`ruff`/`mypy`
(`make check`, gate obligatorio). $0 infraestructura — solo free tier de
GitHub Actions, sin backend ni base de datos propios (constitution §II.9).

### 2.2 Flujo de datos

```
ingest (manual)        transform (manual)              publish (Action)
─────────────────      ───────────────────────         ────────────────
sources/*.py      →    CostRow (interno, con costo) →  leak-check
  Serlaca API           transform/*.py:                → rama + commit
  CSV fallback            - clean_category               (renovarte-catalogo)
  PDF LACA                 - resolve margin (env)       → PR (nunca push
                            - precio PDF (piso margen)      directo a main)
                            - ofertas (data/offers.json)
                          Product (público, sin costo)
                       →  public/data/products.json
```

`ingest`, `transform` y `pdf-extract` son **siempre manuales**, corridos
por el admin en su máquina (constitution §II.6). La única automatización
en CI es `publish --live`, disparada por un push a `main` que toque
`public/data/products.json` — nunca genera datos, solo los publica.

### 2.3 Modelos (`pipeline/models.py`)

- **`CostRow`** — intermedio, source-agnóstico, interno. Todo adaptador de
  fuente (`pipeline/sources/*`) produce `CostRow`s; incluye `precio_costo`
  (el costo real de RenovArte), que nunca cruza a `Product`.
- **`Product`** — schema público, la única forma permitida de
  `public/data/products.json`. Pydantic valida cada instancia
  (`_check_offer_fields`) y `to_public_dict()` es el único punto de
  serialización hacia el archivo público.

### 2.4 Modelo de datos público (`products.json`)

**Producto público**, schema vigente (idéntico al de `RFC-0001 §2.4` de
`renovarte-catalogo`, sin cambios de forma respecto de lo migrado en
`PLAN.md`):

```json
{
  "id": "545300004",
  "proveedor": "LACA",
  "categoria": "Antiage",
  "nombre": "Complejo Antiage con Omega Plus",
  "presentacion": "50g",
  "descripcion": "Textura sedosa, otorga una segunda piel luminosa.",
  "precio_venta": 35280,
  "imagen": "/img/laca/545300004.jpg",
  "en_oferta": false,
  "tags": ["día", "antiage"]
}
```

Con `precio_regular`/`descuento_pct` opcionales cuando el producto está en
oferta con descuento (heredado de spec 0007 de `renovarte-catalogo`, antes
de la migración — sin cambios acá).

> **Enmienda 2026-09-17 (spec [0001](../../specs/0001-agrupacion-alto-nivel-categorias/spec.md) — `codCategoria`).**
> Se suma un campo público más, **`codCategoria`**, el id crudo de
> `productCategoryIds` de Serlaca ("1"/"2"/"3", o "4" para el grupo de
> fallback) — **no** el nombre del grupo. Decisión de negocio del CTO/CEO
> (2026-09-17, ver spec 0001 "Mapeo y modelo de datos"), no discutida acá.
>
> ```json
> {
>   "...": "...",
>   "categoria": "Antiage",
>   "codCategoria": "1",
>   "nombre": "Complejo Antiage con Omega Plus"
> }
> ```
>
> `codCategoria` se ubica inmediatamente después de `categoria` en el
> schema (agrupación de alto nivel al lado de la categoría específica que
> agrupa) — el resto de las claves no cambia de posición ni de forma
> (constitution §II.7, AC-7 de la spec 0001). Es un campo **requerido**:
> todo producto público lo lleva, nunca `null` ni ausente (AC-2/AC-3).
>
> El nombre de cada grupo ("Cuidado facial", "Cuidado corporal",
> "Cosmética", y el del fallback) vive en un archivo de mapeo separado,
> público y committed en este repo —
> [`data/reference/serlaca_category_groups.json`](../../data/reference/serlaca_category_groups.json)
> (ver §4 y `plan.md` de la spec 0001 para el detalle de implementación) —
> nunca hardcodeado en `renovarte-catalogo`. `products.json` **no** lleva
> el nombre del grupo, solo el id.
>
> **Actualización 2026-09-17** (coordinado con la spec espejo `0015` de
> `renovarte-catalogo`, tras decisión del CTO/CEO): este repo es la única
> fuente de verdad del mapeo id→nombre, así que `renovarte-catalogo` no
> mantiene su propia copia hardcodeada ni la duplica a mano — `pipeline
> publish` copia `data/reference/serlaca_category_groups.json` hacia
> `public/data/serlaca_category_groups.json` en el mismo PR que ya abre
> para `products.json` (mismo mecanismo `files_to_update` de
> `git_ops.prepare_branch`, mismo leak-check, mismo flujo de revisión
> humana — constitution §I.3/§I.4). Ver `plan.md` §6bis de la spec 0001
> para el detalle.
>
> **Actualización 2026-09-18 (bloqueante de AC-1, resuelto por el
> CTO/CEO) — `codCategoria` pasa de `string` a `list[str]`.** La Tarea 1 de
> `tasks.md` (verificación de AC-1 contra la API real,
> `renovarte-pipeline verify-category-groups`) mostró que **11 de las 24
> categorías específicas (`productLine`) hoy cargadas aparecen repartidas
> entre más de un `productCategoryIds`** de Serlaca — no son mutuamente
> excluyentes por categoría (detalle completo en `docs/serlaca-api.md`,
> sección "`productCategoryIds` por `productLine`"). El diseño original de
> esta enmienda (un id único por producto, inferido de una tabla estática
> `categoría específica → grupo`) no es válido tal cual.
>
> El CTO/CEO decidió (Opción 1, 2026-09-18): `ingest` guarda el/los
> `productCategoryIds` **reales por producto**, tal como los devuelve la
> API en tres llamadas separadas (`productCategoryIds: ["1"]`/`["2"]`/
> `["3"]`, el mismo mecanismo que ya usa `verify-category-groups`), y un
> producto puede pertenecer a **más de un grupo simultáneamente**. En
> consecuencia:
>
> ```json
> {
>   "...": "...",
>   "categoria": "Uñas",
>   "codCategoria": ["2", "3"],
>   "nombre": "Esmalte semipermanente"
> }
> ```
>
> - `codCategoria` es ahora **`list[str]`, no `string`** — una lista no
>   vacía de ids ordenados y sin duplicados (`"1"`..`"4"`). Un producto sin
>   match en ninguno de los tres grupos reales lleva `["4"]` (fallback;
>   nunca mezclado con un id real — o el producto matcheó al menos un grupo
>   real, o cae entero en el fallback).
> - Sigue siendo un campo **requerido**, nunca `null`/ausente/vacío
>   (AC-2/AC-3 sin cambios) — solo cambia de forma (`string` → `list[str]`
>   de al menos un elemento).
> - El mapeo id→nombre (`data/reference/serlaca_category_groups.json`,
>   §2.4 original) **no cambia** — sigue siendo 4 pares id→nombre, ajeno a
>   si un producto lleva uno o varios ids.
> - La fuente de verdad por producto deja de ser una tabla estática
>   `categoría específica → grupo` en código (el diseño original de
>   `plan.md` §1(B)) — pasa a ser el resultado real, por producto, de las
>   tres llamadas de `ingest` a la API, persistido en el crudo
>   (`data/input/serlaca-raw.json`, gitignored, campo
>   `categoryGroupsByProductCode`) y leído (puro, sin red) por `transform`.
>
> Impacto conocido y ya coordinado por separado: `renovarte-catalogo`
> (spec espejo `0015`) asumía `codCategoria` como valor único — el CTO/CEO
> coordina ese ajuste directamente con el agente de ese repo, no es parte
> de este RFC.

### 2.5 Seguridad (constitution §I)

- `precio_costo`, margen y precio de lista de LACA nunca cruzan a
  `Product`/`products.json` — se consumen y descartan en
  `transform/pricing.py`.
- `data/raw/`, `data/input/`, `.env`/`.env.local` gitignored.
- `pipeline/publish/leak_check.py` corre sobre el `products.json` a
  publicar antes de abrir cualquier PR (defensa en origen).
- El handoff hacia `renovarte-catalogo` es siempre vía Pull Request —
  nunca push directo a `main` — y el merge queda a revisión humana.

## 3. Alternativas consideradas

Documentadas en su momento en `PLAN.md` (no se repiten acá en detalle):
migrar 1:1 desde TypeScript en vez de reescribir desde cero (se migró,
preservando 98 tests portados); construir el PDF-extract en
`renovarte-catalogo` vs. en el repo nuevo (se construyó acá directamente,
cayendo la excepción Python que existía del lado del catálogo).

## 4. Referencias

- [`renovarte-parent/PLAN.md`](../../../PLAN.md) — plan de la separación
  catálogo/pipeline (5 fases, cerrado 2026-09-14).
- [`renovarte-catalogo/docs/rfc/0001-arquitectura-catalogo.md`](https://github.com/gucastillo-personal/renovarte-catalogo/blob/main/docs/rfc/0001-arquitectura-catalogo.md)
  — RFC canónico del schema público, lado catálogo.
- [`docs/serlaca-api.md`](../serlaca-api.md) — referencia del endpoint de
  Serlaca (incluye, desde la spec 0001, la verificación de
  `productCategoryIds`).
- [`specs/0001-agrupacion-alto-nivel-categorias/`](../../specs/0001-agrupacion-alto-nivel-categorias/)
  — spec, plan y tasks de `codCategoria`.
