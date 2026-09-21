# Plan — 0001 `codCategoria` (agrupación de alto nivel)

**Spec:** [`spec.md`](./spec.md) · **RFC:** enmienda a
[`docs/rfc/0001-arquitectura-pipeline.md`](../../docs/rfc/0001-arquitectura-pipeline.md)
§2.4 (ver ahí el detalle formal; primer RFC propio de este repo, creado
junto con este plan).

El mapeo de negocio (`"1"`→Cuidado facial, `"2"`→Cuidado corporal,
`"3"`→Cosmética, sin match→`"4"`) ya está decidido por el CTO/CEO — este
plan no lo re-discute, solo diseña dónde vive y cómo se verifica.

> **Actualización 2026-09-18 (bloqueante de AC-1, resuelto por el
> CTO/CEO) — `codCategoria` pasa de `string` a `list[str]`.** La Tarea 1
> (verificación de AC-1 contra la API real) mostró que **11 de las 24
> categorías específicas (`productLine`) hoy cargadas aparecen repartidas
> entre más de un `productCategoryIds`** de Serlaca — no son mutuamente
> excluyentes por categoría (detalle completo:
> `docs/serlaca-api.md` § "`productCategoryIds` por `productLine`"). El
> diseño original de este plan (§1(B): tabla estática `categoría
> específica → grupo`, un id único por producto) asumía exclusividad
> mutua y **no es válido** con este resultado real.
>
> Decisión del CTO/CEO (Opción 1, 2026-09-18): `codCategoria` pasa a ser
> una **lista** de ids (`list[str]`, no vacía, p. ej. `["2", "3"]`), y la
> fuente de verdad por producto deja de ser una tabla estática en código:
> pasa a ser el resultado real, por producto, de las tres llamadas de
> `ingest` a la API (`productCategoryIds: ["1"]`/`["2"]`/`["3"]`, el mismo
> mecanismo que ya usa `verify-category-groups`, Tarea 1). Todo lo que
> sigue en este documento (§1, §6, §10 y las secciones marcadas) está
> reescrito para reflejar ese cambio — las secciones §2 (archivo de
> mapeo id→nombre), §4 (posición del campo), §7 (determinismo/seguridad) y
> §9 (archivos tocados) no cambian de fondo, solo de tipo del campo, y se
> anotan inline donde corresponde.

## 1. Dos mapeos distintos, dos lugares distintos (reescrito 2026-09-18)

El spec pide un archivo de mapeo, pero hay en realidad **dos** problemas
de mapeo separados, y conviene no confundirlos:

| Mapeo | De → a | Dónde vive | Por qué |
|---|---|---|---|
| **(A) Nombre del grupo** | `codCategoria` (cada id de la lista, `"1"`/`"2"`/`"3"`/`"4"`) → nombre de negocio ("Cuidado facial", …) | `data/reference/serlaca_category_groups.json` (dato, committed, público) | Es exactamente lo que pide AC-4: 4 pares id→nombre, sin lógica. Sigue la convención ya existente de `data/reference/laca_pdf_precios.csv` — dato de referencia público, separado del código. **Sin cambios** por la actualización 2026-09-18: sigue siendo 4 pares id→nombre, ajeno a que un producto lleve uno o varios ids. |
| **(B) Clasificación por producto** | `productCode` → `codCategoria` (`list[str]`, uno o más de `"1"`/`"2"`/`"3"`, o `["4"]` de fallback si no matcheó ninguno) | Calculada en `ingest` (red real, tres llamadas separadas a la API, una por grupo) y persistida en el crudo (`data/input/serlaca-raw.json`, gitignored, clave `categoryGroupsByProductCode: {productCode: [ids]}`); `transform` la lee tal cual, sin red, vía `pipeline/transform/category_groups.py::resolve_cod_categoria()` | **Reemplaza el diseño original** de una tabla estática `categoría específica → grupo` en código. La Tarea 1 (AC-1) verificó contra la API real que 11 de 24 categorías específicas (`productLine`) aparecen repartidas entre más de un `productCategoryIds` — no son mutuamente excluyentes, así que una tabla `categoria → id único` no puede representar el catálogo real. La fuente de verdad pasa a ser el dato real por producto que la propia API devuelve, no una decisión de negocio transcripta a mano por categoría. |

**Por qué (B) ya no es una tabla estática en código (`RENAMES`-style):**
el diseño original asumía que cada categoría específica pertenece a un
único grupo de Serlaca — verificado falso contra la API real (AC-1, ver
`docs/serlaca-api.md`). Con productos repartidos entre grupos, la única
fuente de verdad correcta es el id o los ids que la API realmente
devuelve **por producto** (`productCode`), no por categoría. Por eso (B)
se mueve de "lógica de negocio en código, verificada una vez" a "dato
real por producto, capturado en cada corrida de `ingest`" — mismo
tratamiento que ya recibe `pdf_prices` (`data/reference/laca_pdf_precios.csv`,
un dict `codigo → precio` inyectado en `build_catalog`), no el de
`RENAMES`. `transform` sigue sin hacer ninguna llamada de red
(constitution §II.10): lee la lista de ids ya resuelta por `ingest` desde
el crudo, la misma garantía de determinismo de antes (correr `transform`
dos veces sobre el mismo crudo da el mismo `codCategoria` siempre — ver
§7).

**Por qué `ingest` pide 3 veces más, en vez de derivarlo del dump sin
filtrar (`productCategoryIds: []`):** ya confirmado en `docs/serlaca-api.md`
("Campos que ignoramos") — el dump sin filtrar trae `productCategory:
null` por producto; la única forma de saber a qué grupo(s) pertenece un
producto es pedirle a la API cada grupo por separado y ver qué
`productCode`s devuelve. `ingest` ya hacía esto para `verify-category-groups`
(Tarea 1, manual); ahora la misma llamada se integra al flujo normal de
`ingest` (automática, cada corrida), no solo a la verificación puntual.

**Consistencia entre (A) y (B) (actualizado 2026-09-18):** ya no hay una
tabla (B) en código contra la que comparar — (B) ahora es dato real por
producto, no una función pura de un dominio conocido de categorías. Lo
único que sigue siendo verificable estáticamente es que (A)
(`data/reference/serlaca_category_groups.json`) tenga exactamente las 4
claves `{"1","2","3","4"}` (AC-4, §8) — los ids que puede llevar
`codCategoria` en la práctica dependen de lo que la API real devuelva en
cada corrida de `ingest`, no de una lista cerrada en código.

## 2. `data/reference/serlaca_category_groups.json`

```json
{
  "1": "Cuidado facial",
  "2": "Cuidado corporal",
  "3": "Cosmética",
  "4": "Otros"
}
```

Igual que `laca_pdf_precios.csv`: público, committed, sin costo/margen —
no dispara `leak_check.py` (que igualmente solo escanea el
`products.json` a publicar, no todo el repo — ver
`pipeline/publish/run.py`). No hace falta un `load_*()` que lo *parsee* en
este repo para esta primera versión: nada en `transform` necesita el
*nombre* del grupo, solo el *id* (§2.4 de la spec — "no el nombre del
grupo") — `transform` sigue sin tocar este archivo. `publish` sí lo toca
a partir de la decisión de la spec espejo `0015` (ver §6bis abajo), pero
solo para **copiarlo tal cual** (bytes) hacia `renovarte-catalogo`, igual
que ya hace con `products.json` — sigue sin hacer falta un
`load_category_group_names()` que lo interprete acá; ese parseo, si algo
lo necesita, corre del lado de `renovarte-catalogo`. Si más adelante
alguna herramienta de *este* repo necesita el nombre (p. ej. un reporte
interno), ahí sí se agregaría un `load_category_group_names()` calcado de
`load_pdf_prices()` — no es necesario para cumplir AC-4 ni para la
distribución de §6bis.

## 3. `pipeline/transform/category_groups.py` (nuevo módulo, reescrito
2026-09-18)

Ya no hay una tabla estática `categoría → grupo` (ver §1) — el módulo se
reduce a normalizar la lista de ids reales que `ingest` ya resolvió por
`productCode`, y aplicar el fallback:

```python
FALLBACK_COD_CATEGORIA = "4"


def resolve_cod_categoria(raw_group_ids: list[str] | None) -> list[str]:
    """Ids reales de Serlaca para este producto (0, 1 o más — ver ingest,
    `categoryGroupsByProductCode`) -> forma pública de `codCategoria`:
    ordenada, sin duplicados, no vacía. `None`/lista vacía (el producto no
    apareció en ninguna de las tres llamadas por grupo) -> `["4"]`
    (fallback).
    """
    if not raw_group_ids:
        return [FALLBACK_COD_CATEGORIA]
    return sorted(set(raw_group_ids))
```

Integración en `pipeline/transform/pricing.py::build_public_product`: nuevo
parámetro `cod_categoria: list[str] | None = None` (los ids crudos para
este `codigo`, resueltos por `build_catalog.py` — ver §5), resuelto
internamente con `resolve_cod_categoria(cod_categoria)` y pasado al
constructor de `Product`. A diferencia del diseño original (una función
pura de `row.categoria`), ahora depende de un dato externo por producto —
mismo patrón que ya usa `pdf_price` (inyectado desde afuera, resuelto por
`codigo`, no derivado de un campo de `CostRow`).

## 4. `pipeline/models.py` — campo nuevo en `Product`

```python
class Product(BaseModel):
    id: str
    proveedor: str
    categoria: str
    codCategoria: list[str]  # nuevo — ver RFC-0001 §2.4 (enmienda 2026-09-17, tipo actualizado 2026-09-18)
    nombre: str
    ...
```

- **`list[str]`, no `str`** (actualizado 2026-09-18 — ver nota al inicio
  del documento): un producto puede pertenecer a más de un grupo real de
  Serlaca. Se agrega un `model_validator` que rechaza una lista vacía y
  cualquier id fuera de `{"1","2","3","4"}` — falla rápido ante un bug de
  `ingest`/`transform`, no solo ante field ausente.
- **Requerido, sin default.** Fuerza a que todo call-site que construye un
  `Product` (hoy: solo `build_public_product`; en tests, los 5 call-sites
  listados en tasks.md) decida explícitamente su `codCategoria` — nada de
  omisión silenciosa (AC-2).
- **Nombre del campo, `codCategoria` (camelCase), no `cod_categoria`:**
  rompe la convención snake_case/español del resto del modelo a propósito,
  porque es literalmente la clave pública pedida por el spec (mismo
  nombre que usa la API de Serlaca para el concepto, `productCategoryIds`,
  ver spec 0001 "Modelo de datos"). `ruff` no tiene la regla de naming
  (`N8xx`) habilitada en este repo (`pyproject.toml`
  `[tool.ruff.lint] select = ["E","F","I","UP","B"]`), así que no hace
  falta un `alias`/`Field(alias=...)` — el nombre del atributo Python es
  directamente la clave JSON, igual que el resto de los campos.
- **Posición:** inmediatamente después de `categoria`, antes de `nombre` —
  agrupación de alto nivel al lado de la específica que agrupa. Cambia el
  orden de claves del JSON de salida (los campos se serializan en el
  orden de declaración del modelo vía `model_dump`), lo cual está bien:
  no hay ningún gate de paridad byte-a-byte contra una versión anterior
  (ese gate era de la migración TS→Python, ya cerrada) — el único
  contrato es el schema, no el orden exacto de claves, y AC-7 solo exige
  que las claves existentes no cambien de forma.

## 5. `pipeline/transform/build_catalog.py` / CSV source (reescrito
2026-09-18)

`build_catalog()` suma un parámetro nuevo, `category_groups_by_codigo:
dict[str, list[str]] | None = None` — mismo patrón ya usado por
`pdf_prices: dict[str, int]`: un dict *codigo → dato*, inyectado desde
afuera, resuelto por `codigo` dentro del loop de filas:

```python
cod_categoria = category_groups_by_codigo.get(row.codigo.strip()) if category_groups_by_codigo else None
products.append(build_public_product(row, margin, descuento_pct, pdf_price, cod_categoria))
```

`build_public_product` aplica el fallback (`resolve_cod_categoria`, §3),
así que pasar `None`/lista vacía es válido y da `["4"]`.

**Fuente de `category_groups_by_codigo` por origen (constitution §II.8,
multi-fuente):**
- **API Serlaca:** `pipeline/transform/run.py` lee
  `categoryGroupsByProductCode` directo del crudo JSON ya bajado por
  `ingest` (ver §6) y lo pasa a `build_catalog`. Sin red — `transform`
  sigue siendo 100% offline.
- **CSV fallback:** no tiene este dato (no pasa por la API de Serlaca por
  grupo). `build_catalog_from_csv` no lo provee —
  `category_groups_by_codigo` queda `None`, y **todo producto del CSV
  recibe `codCategoria: ["4"]`** (fallback) hasta que exista una fuente
  equivalente para ese canal. No es un caso cubierto por AC-1 (que solo
  verifica la API real) — comportamiento explícito, no un bug, documentado
  acá para que no sorprenda si el CSV vuelve a usarse.

## 6. Verificación contra la API real (AC-1) — diseño del mecanismo
(§6.0 agregado 2026-09-18: el mismo mecanismo pasa a usarse también en
`ingest`, no solo en la verificación manual)

> **Actualización 2026-09-18:** todo lo que sigue en esta sección (el
> mecanismo de `fetch_category_group_samples`/`verify-category-groups`)
> **se mantiene sin cambios** — sigue siendo el paso manual de AC-1. Lo
> nuevo es que `pipeline/ingest/serlaca_download.py::run()` (el `ingest`
> normal, cada corrida) **reusa `fetch_category_group_samples()`** para
> las mismas tres llamadas, y agrega una función pura nueva en
> `pipeline/sources/serlaca_api.py`:
>
> ```python
> def group_ids_by_product_code(samples: dict[str, list[Any]]) -> dict[str, list[str]]:
>     """Los mismos samples que arma fetch_category_group_samples()
>     (id "1"/"2"/"3" -> dataObjects) -> productCode -> lista ordenada de
>     ids donde apareció. Un producto puede aparecer en más de un id — eso
>     ya no es un error (ver §1), es el dato real que se persiste.
>     """
> ```
>
> `ingest` embebe el resultado en el crudo ya escrito a
> `data/input/serlaca-raw.json` (gitignored), como una clave nueva junto a
> `dataObjects`:
>
> ```jsonc
> {
>   "_meta": { "...": "..." },
>   "dataObjects": [ /* como hoy */ ],
>   "categoryGroupsByProductCode": { "545300004": ["2", "3"], "...": ["1"] }
> }
> ```
>
> `transform/run.py` lee esa clave (con degradación graciosa —
> `dump.get("categoryGroupsByProductCode") or {}` — un crudo viejo sin esta
> clave no rompe nada, todo cae al fallback `["4"]`, mismo criterio que
> `load_pdf_prices()`) y se la pasa a `build_catalog` como
> `category_groups_by_codigo` (§5). Esto son **3 llamadas de red más por
> corrida de `ingest`** (antes solo corrían a mano, en verificaciones
> puntuales de AC-1) — costo aceptado por el CTO/CEO como parte de la
> Opción 1: es la única forma de que un producto lleve el dato real de a
> qué grupo(s) pertenece, dado que el dump sin filtrar no lo trae (ver
> más abajo, "Problema real").
>
> El subcomando manual `verify-category-groups` (más abajo) sigue
> existiendo tal cual, para spot-checks — ya no es un gate bloqueante
> ("PARAR si hay conflictos"): un producto en más de un grupo es ahora un
> resultado válido y esperado, no un error. Se ajusta el mensaje de
> `CategoryGroupReport`/`cli.py` para reflejar esto (informativo, no
> bloqueante) — el código de salida de `verify-category-groups` deja de
> depender de `conflicts`.

**Problema real, confirmado leyendo `docs/serlaca-api.md`:** el dump crudo
que ya bajamos con `productCategoryIds: []` **no** trae el id de grupo por
producto — `productCategory` viene `null` en la muestra observada (listado
en "Campos que ignoramos"). La única forma de saber a qué
`productCategoryIds` pertenece cada producto es pedirle a la API
explícitamente `productCategoryIds: ["1"]` / `["2"]` / `["3"]` y ver qué
`productCode`s devuelve cada llamada — no hay atajo dentro del dump que ya
tenemus.

**Mecanismo:** nuevo módulo `pipeline/ingest/verify_category_groups.py`,
separado en función pura + función de red (mismo patrón que
`sources/serlaca_api.py` Stage 1/Stage 2):

```python
def fetch_category_group_samples(
    env: dict[str, str | None], client: httpx.Client | None = None
) -> dict[str, list[Any]]:
    """productCategoryIds "1"/"2"/"3" -> los dataObjects crudos que cada uno
    devuelve. Reusa `fetch_all_serlaca_pages` tres veces. Red real — no se
    unit-testea, solo se corre manualmente (constitution §II.6).
    """

@dataclass
class CategoryGroupReport:
    categoria_to_groups: dict[str, set[str]]  # categoría limpia -> ids donde apareció
    conflicts: list[str]     # categorías que aparecieron en más de un id
    unclassified: list[str]  # categorías que no aparecieron en ningún id ("1"/"2"/"3")
    suggested_map: dict[str, str]  # categoría -> id único, solo para las sin conflicto

def build_category_group_report(
    samples: dict[str, list[Any]],
) -> CategoryGroupReport:
    """Pura, sin red — sí se unit-testea con fixtures. Agrupa por
    `productLine.name` limpio (mismo `clean_category` que usa transform),
    ignorando `professionalExclusive: true` (esos productos igual se
    excluyen del catálogo publicado — ver spec 0001, pregunta abierta 4;
    no deberían distorsionar la clasificación de las categorías que sí se
    publican).
    """
```

Subcomando nuevo en `cli.py`: `renovarte-pipeline verify-category-groups`
(mismo `_load_env()` que `ingest`/`transform`). Imprime el reporte legible
(qué categoría específica cayó en qué id, conflictos, no clasificadas) y
opcionalmente escribe un JSON crudo en `data/input/` (gitignored, no
público) para inspección manual. **No escribe** directamente
`CATEGORY_GROUP_BY_CATEGORIA`: el desarrollador transcribe el resultado a
mano en `transform/category_groups.py`, a propósito — mismo principio que
"`ingest`/`transform` son siempre manuales, revisados por el admin"
(constitution §II.6): una clasificación de negocio que decide qué filtro
ve el usuario final no se auto-genera y auto-commitea sin ojos humanos en
el medio.

Esto también resuelve la pregunta abierta 4 del spec
(`professionalExclusive`): el reporte de verificación filtra esos
productos antes de clasificar, así que la clasificación resultante ya
está "limpia" del universo de productos que efectivamente se publican.

## 6bis. Distribución de (A) hacia `renovarte-catalogo` (agregado
2026-09-17, coordinado con la spec espejo `0015` de ese repo)

**Decisión del CTO/CEO (relayed por el agente de `renovarte-catalogo`,
spec 0015):** `renovarte-pipeline` es la única fuente de verdad del mapeo
(A) (`codCategoria` → nombre). Para que `renovarte-catalogo` lo lea sin
mantener su propia copia hardcodeada ni divergir, este repo tiene que
publicárselo junto con `products.json`, no solo dejarlo commiteado acá.

**Mecanismo — reusa el que ya existe, no uno nuevo.**
`pipeline/publish/run.py::run_publish` ya le pasa a
`git_ops.prepare_branch(..., files_to_update: dict[Path, Path], ...)` un
diccionario `{destino relativo en renovarte-catalogo: origen absoluto acá}`
con una sola entrada (`products.json`). Se extiende a una segunda entrada:

```python
CATEGORY_GROUPS_DEST_REL_PATH = Path("public") / "data" / "serlaca_category_groups.json"
DEFAULT_CATEGORY_GROUPS_PATH = Path("data") / "reference" / "serlaca_category_groups.json"

def run_publish(
    ...,
    category_groups_path: str | Path = DEFAULT_CATEGORY_GROUPS_PATH,
) -> PublishResult:
    ...
    category_groups_path = Path(category_groups_path)
    files_to_update = {DEST_REL_PATH: products_json_path}
    if category_groups_path.exists():
        files_to_update[CATEGORY_GROUPS_DEST_REL_PATH] = category_groups_path
    prepared = prepare_branch(catalogo_path, branch_name, base_branch, files_to_update, commit_message)
```

Mismo flujo de PR/rama/revisión-manual que ya rige para `products.json` —
sin mecanismo nuevo, sin invariante de `constitution.md` roto: sigue
siendo "nunca push directo a `main`, merge a revisión humana"
(constitution §I.3), y sigue siendo un solo PR por corrida (una rama, un
commit, sumando un segundo archivo al mismo commit — no dos PRs
separados).

**Por qué `if category_groups_path.exists()` y no incondicional:** mismo
patrón de degradación ya usado por `load_pdf_prices()` (constitution: un
archivo de referencia ausente no rompe el flujo, simplemente no aporta esa
pieza) — evita que el publish real falle si por algún motivo el archivo
todavía no está commiteado, y evita tener que tocar los fixtures de los
tests de `test_publish_run.py` que hoy no crean este archivo (siguen
pasando sin cambios; se suma un test nuevo dedicado para el caso en que sí
existe).

**Leak-check:** se corre `check_file_for_leaks()` también sobre
`category_groups_path` antes de tocar el checkout de `renovarte-catalogo`
(mismo criterio que sobre `products_json_path`) — defensa en profundidad,
aunque el contenido (id/nombre de grupo) no pueda matchear ningún patrón
`FORBIDDEN` en la práctica.

**No hace falta un flag nuevo en `cli.py`:** `cmd_publish` ya invoca
`run_publish` sin pasar explícitamente todos los parámetros opcionales
(usa los defaults del propio `run_publish`, como ya pasa con
`price_diff_path`) — el nuevo `category_groups_path` sigue el mismo
patrón, default `data/reference/serlaca_category_groups.json`, sin
requerir un `--category-groups` en la CLI para esta primera versión.

## 7. Determinismo (AC-5) y seguridad (AC-6) (actualizado 2026-09-18)

- **Determinismo:** `resolve_cod_categoria()` sigue siendo una función pura
  (lista de ids -> lista normalizada + fallback) — cero I/O, cero red,
  dentro de `transform`. La red se movió a `ingest` (§6), que corre una
  sola vez y persiste su resultado en el crudo; `transform` solo *lee* ese
  resultado ya congelado. Correr `transform` dos veces sobre el mismo
  crudo (mismo `categoryGroupsByProductCode` incluido) da el mismo
  `codCategoria` por producto, siempre — la lista se ordena y deduplica
  dentro de `resolve_cod_categoria`, así que el orden de las tres llamadas
  de `ingest` no puede introducir no-determinismo en la salida.
- **Seguridad:** `codCategoria` (lista de ids) y el archivo de mapeo son
  un id/nombre de agrupación (`"1".."4"`, "Cuidado facial", etc.) —
  ningún patrón de `leak_check.py` (`FORBIDDEN`: `precio_costo`,
  `margin_percent`, `\bmargen\b`, `costo`, etc.) puede matchear contra
  esos valores. No hace falta tocar `leak_check.py`.

## 8. Testing por acceptance criterion (actualizado 2026-09-18)

| AC | Cómo se testea |
|---|---|
| AC-1 | Manual: correr `verify-category-groups` contra la API real con credenciales reales, revisar el reporte (ya no bloquea por "conflictos" — informativo, ver §6). `build_category_group_report()` (la parte pura) se cubre con `test_verify_category_groups.py` (fixtures, sin red). El resultado real (2026-09-17) queda documentado en `docs/serlaca-api.md`. |
| AC-2 | `test_models.py`: `Product` sin `codCategoria`, o con lista vacía, falla la validación de Pydantic. `test_build_catalog_pdf_overlay.py` / un test nuevo de integración en `build_catalog`: todo producto de una corrida con `CostRow`s variadas tiene `codCategoria` seteado (lista no vacía). |
| AC-3 | `test_category_groups.py`: `resolve_cod_categoria(None) == ["4"]`, `resolve_cod_categoria([]) == ["4"]`. Un test de integración en `build_catalog` con un `codigo` ausente de `category_groups_by_codigo` confirma que el producto igual se publica con `codCategoria: ["4"]` (no se excluye). |
| AC-4 | Test dedicado (`test_category_groups.py` o similar): `data/reference/serlaca_category_groups.json` existe, parsea, y sus claves son exactamente `{"1","2","3","4"}` con valores no vacíos. Ya no hay una tabla (B) en código con la que verificar consistencia (§1) — el archivo (A) se valida solo contra sí mismo. |
| AC-5 | Test de determinismo ya existente para `transform` (o uno nuevo si no hay): correr `build_catalog` dos veces sobre las mismas `CostRow`s + el mismo `category_groups_by_codigo`, comparar `to_products_json()` byte a byte, incluyendo `codCategoria` (lista ordenada). |
| AC-6 | `test_leak_check.py` (existente) sigue en verde sin cambios — `codCategoria`/nombres de grupo no matchean ningún patrón `FORBIDDEN`. Se agrega un caso explícito si se quiere dejarlo documentado. |
| AC-7 | `test_models.py` existente (offer fields, `to_public_dict`) sigue pasando tras el cambio — confirma que las claves viejas no cambiaron de forma. Ningún test existente debería requerir edición de sus *aserciones*, solo agregar `codCategoria=[...]` a los `Product(...)` de los fixtures. |

## 9. Archivos tocados (resumen, actualizado 2026-09-18)

**Nuevos:**
- `data/reference/serlaca_category_groups.json`
- `pipeline/transform/category_groups.py`
- `tests/test_category_groups.py`
- `pipeline/ingest/verify_category_groups.py`
- `tests/test_verify_category_groups.py`
- `tests/test_serlaca_download.py` (nuevo 2026-09-18 — `ingest` ahora
  hace red real más allá del dump sin filtrar, se cubre con red
  monkeypatcheada)
- `docs/rfc/0001-arquitectura-pipeline.md` (ya creado en este plan)

**Editados:**
- `pipeline/models.py` (campo `codCategoria: list[str]` en `Product`, con
  validación de lista no vacía / ids permitidos)
- `pipeline/transform/pricing.py` (`build_public_product` recibe
  `cod_categoria: list[str] | None` y arma `codCategoria` vía
  `resolve_cod_categoria`)
- `pipeline/transform/build_catalog.py` (nuevo párametro
  `category_groups_by_codigo: dict[str, list[str]] | None` — **cambio
  2026-09-18**, este archivo pasa de "no tocado" a "editado" respecto de
  la versión original de este plan, ver §5)
- `pipeline/sources/serlaca_api.py` (nueva función pura
  `group_ids_by_product_code` — **nuevo 2026-09-18**, ver §6)
- `pipeline/ingest/serlaca_download.py` (`run()` suma las 3 llamadas por
  grupo y persiste `categoryGroupsByProductCode` en el crudo — **nuevo
  2026-09-18**, ver §6)
- `pipeline/transform/run.py` (lee `categoryGroupsByProductCode` del
  crudo y lo pasa a `build_catalog` — **nuevo 2026-09-18**)
- `pipeline/cli.py` (subcomando `verify-category-groups`; código de
  salida ya no depende de `conflicts` — **actualizado 2026-09-18**)
- `pipeline/publish/run.py` (extiende `files_to_update` con
  `data/reference/serlaca_category_groups.json` →
  `public/data/serlaca_category_groups.json`, más el leak-check sobre ese
  segundo archivo — ver §6bis; **actualizado 2026-09-17**, corrección de
  este plan: se había marcado como "no tocado" en la versión original,
  hasta que la spec espejo `0015` de `renovarte-catalogo` definió que
  necesita esta copia para no duplicar el mapeo)
- `docs/serlaca-api.md` (sección "`productCategoryIds` por `productLine`"
  con el resultado real de AC-1, 2026-09-17 — 11/24 categorías repartidas
  entre grupos)
- `tests/test_models.py`, `tests/test_price_diff.py`,
  `tests/test_publish_run.py`, `tests/test_pdf_match.py` (agregar
  `codCategoria=[...]` a los `Product(...)`/fixtures existentes;
  `test_publish_run.py` suma además un caso nuevo para la copia del
  archivo de mapeo — ver §6bis)
- `specs/README.md` (status del feature index + traceability matrix)

**No tocados (a propósito):** `pipeline/sources/csv_source.py` (el CSV
fallback no tiene fuente para `category_groups_by_codigo` — todo producto
CSV cae al fallback `["4"]`, ver §5), `pipeline/publish/leak_check.py`
(`check_file_for_leaks` ya es genérico, se reusa tal cual sobre el segundo
archivo, sin cambios a su propio código), `pipeline/publish/git_ops.py`
(`prepare_branch` ya acepta un diccionario de N archivos — no necesita
cambios, solo se le pasa una entrada más), schema de `renovarte-catalogo`
(spec espejo 0015, otro repo — coordinado por separado por el CTO/CEO).

## 10. Riesgo que sí podría cambiar este diseño — MATERIALIZADO y
RESUELTO (2026-09-18)

Este riesgo, tal como estaba escrito en la versión original de este plan
(cita abajo), **se materializó**: AC-1 (Tarea 1 de `tasks.md`), corrida
contra la API real el 2026-09-17, encontró que 11 de 24 categorías
específicas (`productLine`) aparecen repartidas entre más de un
`productCategoryIds`. Reportado como bloqueante por el `developer-agent`
(no se improvisó una solución en el código); el CTO/CEO resolvió el
bloqueo el 2026-09-18 (Opción 1, documentada en §1/§4/§5/§6 de este
plan): `codCategoria` pasa a `list[str]`, y el dato de grupo se guarda por
producto individual en `ingest`, exactamente la alternativa que esta
sección ya anticipaba como necesaria. No queda ningún riesgo abierto de
este tipo — el resto de las tareas (`tasks.md` 2-14) se reescribieron
sobre esta base y ya no dependen de la exclusividad mutua entre
categorías.

> Texto original (2026-09-17), por trazabilidad: "Si AC-1 revela que
> alguna categoría específica (`productLine`) aparece repartida entre más
> de un `productCategoryIds` (el caso "conflicto" que
> `build_category_group_report` está diseñado para detectar), el mapeo
> (B) por categoría-específica-completa deja de ser válido para esa
> categoría puntual, y clasificar tendría que hacerse por producto
> individual (requeriría guardar el/los id(s) de grupo del producto en el
> crudo de ingesta, no solo inferirlo de `categoria` en transform)."
