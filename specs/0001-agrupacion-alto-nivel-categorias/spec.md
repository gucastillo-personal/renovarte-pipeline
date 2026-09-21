# 0001 — Agrupación de alto nivel de categorías (`codCategoria`: Cuidado facial / Cuidado corporal / Cosmética / fallback)

**Status:** Built (2026-09-18) — ver `tasks.md` para el detalle de qué se
implementó, incluida la actualización 2026-09-18 (`codCategoria` pasa a
`list[str]`, decisión del CTO/CEO tras el bloqueante de AC-1).
**PRD:** RF-09 (nuevo, 2026-09-17)
**Spec espejo:** `renovarte-catalogo` `specs/0015-agrupacion-categorias/spec.md`
(Backlog, bloqueado por este spec) — ese spec consume el campo que este
spec produce, para ofrecer una navegación de filtros en dos niveles.

> **Decisión del CTO/CEO (2026-09-17), resuelve las preguntas abiertas
> originales de este spec** — ver `## Mapeo y modelo de datos (decidido)`
> más abajo. Quedan solo dos puntos abiertos, no bloqueantes: el nombre
> visible del grupo fallback (id `"4"`) y la verificación operativa del
> mapeo contra la API real antes de implementar.

## Problema

Hoy `categoria` en `products.json` viene de `productLine.name` de Serlaca
("Antiage", "Pieles Grasas", "Uñas", etc. — ~24 valores distintos,
limpiados por `transform/categories.py`). Es una lista plana: no existe
ningún campo que indique a qué agrupación de alto nivel pertenece cada
categoría.

El CTO/CEO observó, inspeccionando los requests que hace el sitio de
Serlaca, que la búsqueda de productos (`POST
https://api.serlaca.com/Products/ReadProducts`, el mismo endpoint que ya
usa `sources/serlaca_api.py`) acepta un `productCategoryIds` que separa el
catálogo en al menos dos grupos: `["2"]` trae productos de cuidado
facial/personal y `["3"]` trae cosmética — el resto del body es idéntico.
Hoy la ingesta llama a este endpoint con `productCategoryIds: []` (todo el
catálogo en un solo barrido, confirmado en `docs/serlaca-api.md`), así que
esta distinción nunca se captura.

## Objetivo

Que cada producto publicado en `products.json` lleve, además de su
categoría específica actual, una agrupación de alto nivel (Cuidado facial,
Cuidado corporal, Cosmética, o el grupo genérico de fallback), para que
`renovarte-catalogo` pueda construir una navegación de filtros en dos
niveles en vez de la lista plana de hoy.

## Mapeo y modelo de datos (decidido)

Definición del CTO/CEO (2026-09-17), reemplaza la investigación abierta
que este spec pedía originalmente:

| `productCategoryIds` (Serlaca) | Grupo de alto nivel |
|---|---|
| `"1"` | Cuidado facial |
| `"2"` | Cuidado corporal |
| `"3"` | Cosmética |
| *(sin match / no informado)* | `"4"` — grupo genérico de fallback. **Nombre visible sugerido: "Otros"** — a confirmar con el CTO/CEO, no bloqueante (ver Preguntas abiertas). |

> Nota: esto invierte el mapeo que el reporte original de este spec había
> supuesto por el ejemplo informal del CTO/CEO (`"2"` = facial, `"3"` =
> cosmética). El mapeo correcto, confirmado ahora, es el de la tabla de
> arriba (`"1"` = facial, `"2"` = corporal, `"3"` = cosmética). El AC-1 más
> abajo sigue pidiendo verificarlo contra la API real antes de dar la
> implementación por cerrada — la definición de negocio ya no es una
> incógnita, pero el mapeo id↔producto sigue sin confirmarse operativamente.

**Modelo de datos:**

- `products.json` (schema público, `renovarte-catalogo`) suma un campo
  **`codCategoria`** por producto: el id crudo de Serlaca (`"1"`, `"2"`,
  `"3"`, o `"4"` para el fallback) — no el nombre del grupo. Esto es la
  enmienda concreta a RFC-0001 §2.4 (el detalle formal de cómo se redacta
  la enmienda queda para el `developer-agent`).
- El mapeo `codCategoria` → nombre del grupo (tabla de arriba) vive en un
  **archivo JSON de mapeo, separado del código**, del lado de este repo
  (no hardcodeado en `renovarte-catalogo`): propuesta de ubicación
  `data/reference/serlaca_category_groups.json`, siguiendo la convención ya
  existente de `data/reference/laca_pdf_precios.csv` (datos de referencia
  de Serlaca/LACA, públicos, committed, separados del código). Forma
  propuesta (a confirmar en `plan.md`):
  ```json
  {
    "1": "Cuidado facial",
    "2": "Cuidado corporal",
    "3": "Cosmética",
    "4": "Otros"
  }
  ```
  `renovarte-catalogo` no necesita este archivo en runtime — el nombre del
  grupo se resuelve al armar `products.json` en `transform`, o bien
  `codCategoria` viaja crudo y el nombre se resuelve del lado del catálogo
  con su propia copia de este mismo mapeo (a decidir en `plan.md`; ambas
  opciones cumplen "no hardcodeado en la UI", que es el punto no
  negociable de la decisión del CTO/CEO).

## Alcance

### In

- Verificar contra la API real de Serlaca que el mapeo de negocio ya
  decidido (`"1"` → Cuidado facial, `"2"` → Cuidado corporal, `"3"` →
  Cosmética, sin match → `"4"` fallback) se corresponde con lo que la API
  efectivamente devuelve por producto — la definición de qué significa cada
  id ya no está abierta, pero su verificación operativa sí es parte de este
  spec (AC-1).
- Publicar `codCategoria` (el id crudo `"1"`/`"2"`/`"3"`/`"4"`) por producto
  en el schema público (`products.json`) — enmienda concreta a RFC-0001
  §2.4, cuyo detalle formal de redacción queda para el `developer-agent`.
- Crear y mantener el archivo JSON de mapeo `codCategoria` → nombre de
  grupo (propuesta: `data/reference/serlaca_category_groups.json`, ver
  arriba), separado del código, del lado de este repo.
- Asignar `codCategoria: "4"` a todo producto que no matchee ninguno de los
  ids `"1"`/`"2"`/`"3"` — ningún producto queda sin `codCategoria`.
- Mantener el campo `categoria` (específica) exactamente como hoy — este
  spec agrega, no reemplaza.

### Out

- Cualquier cambio a la UI o filtros del catálogo (`renovarte-catalogo`,
  spec espejo 0015).
- Cambios al cálculo de precio, margen u ofertas.
- Sumar los demás filtros que acepta el mismo endpoint de Serlaca
  (`productLineCodes`, `productCompositionIds`, `productNecessityIds`,
  `productUseInIds`) — no forman parte de este pedido.
- Cambiar la estrategia de paginación/ingesta general (`productCategoryIds:
  []` sigue siendo válido para traer todo el catálogo en un solo barrido;
  este spec es sobre qué se hace con esa información una vez traída, no
  necesariamente sobre cambiar cómo se pide).

## Acceptance criteria

1. **AC-1 (RF-09):** El mapeo `codCategoria` → grupo (`"1"` = Cuidado
   facial, `"2"` = Cuidado corporal, `"3"` = Cosmética, `"4"` = fallback)
   está verificado contra la API real de Serlaca — para una muestra de
   productos de cada categoría específica (`productLine`) hoy cargada, el
   `codCategoria` asignado coincide con lo que la API devuelve al filtrar
   por ese `productCategoryIds`.
2. **AC-2 (RF-09):** Cada producto publicado en `products.json` tiene un
   `codCategoria` (`"1"`, `"2"`, `"3"` o `"4"`) — ninguno queda sin este
   campo.
3. **AC-3 (RF-09):** Todo producto que no matchee ninguno de los ids
   `"1"`/`"2"`/`"3"` recibe `codCategoria: "4"` y sigue publicándose
   normalmente — no se excluye del catálogo por esto.
4. **AC-4 (RF-09):** Existe, committed y separado del código, el archivo
   JSON de mapeo `codCategoria` → nombre de grupo (los 3 nombres de negocio
   más el del fallback).
5. **AC-5 (RNF-03, determinismo):** Correr `transform` dos veces sobre el
   mismo crudo produce el mismo `products.json` (incluido `codCategoria`)
   byte a byte.
6. **AC-6 (RNF-04, seguridad):** `codCategoria` y el archivo de mapeo son
   solo una etiqueta de agrupación — no exponen costo, margen ni precio de
   lista de LACA; pasan el leak-check igual que el resto del schema.
7. **AC-7 (RF-08, compatibilidad de schema):** El resto del schema público
   (`proveedor, categoria, nombre, presentacion, descripcion, precio_venta,
   imagen, en_oferta, tags`, opcionales de oferta) no cambia de forma —
   `codCategoria` se agrega, no reemplaza ni renombra ninguno existente.

## Preguntas abiertas

1. **No bloqueante — nombre del grupo fallback:** el CTO/CEO no dio nombre
   para el grupo `"4"`. Este spec propone **"Otros"** como sugerencia (ver
   tabla arriba) — a confirmar con el CTO/CEO antes o durante la
   implementación; no bloquea el resto del trabajo (el id `"4"` y su
   mecánica sí están decididos).
2. **Verificación operativa pendiente:** aunque el mapeo de negocio
   (AC-1) ya está decidido, todavía no se corrió contra la API real para
   confirmar que ningún `productLine` (categoría específica) queda
   repartido entre más de un `productCategoryIds`, ni que `"1"`/`"2"`/`"3"`
   son los únicos ids que devuelve Serlaca. Se resuelve al implementar
   (AC-1), no bloquea escribir el `plan.md`.
3. **Dónde se resuelve el nombre del grupo (pipeline vs. catálogo):** el
   spec espejo (`renovarte-catalogo` 0015) puede consumir `codCategoria`
   crudo y resolver el nombre con su propia copia del JSON de mapeo, o
   recibir el nombre ya resuelto si `transform` lo agrega como campo
   adicional — cualquiera de las dos cumple "mapeo no hardcodeado en la
   UI"; la elección concreta queda para `plan.md`.
4. **`professionalExclusive`:** hoy esos productos se excluyen del
   catálogo antes de llegar a `categoria`/`codCategoria`. No está
   confirmado si eso cambia el mapeo para los productos que sí se
   publican — a verificar junto con AC-1.
