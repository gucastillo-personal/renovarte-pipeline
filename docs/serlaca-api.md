# API de serlaca — referencia

Fuente de datos de costo para `sources/serlaca_api.py`. Documenta el endpoint
tal como lo usa `www.serlaca.com`, observado el 2026-09-10. Migrado desde
`renovarte-catalogo/docs/serlaca-api.md` (2026-09-14) cuando la ingesta se
separó a este repo.

> **Uso previsto:** solo desde `pipeline.sources.serlaca_api`, corriendo
> localmente (`make ingest`) o en CI. Nunca desde el navegador ni desde el
> runtime de `renovarte-catalogo`. Credenciales en `.env.local`, nunca
> commiteadas.

---

## Endpoint

```
POST https://api.serlaca.com/Products/ReadProducts
```

### Headers

| Header | Valor | Nota |
|---|---|---|
| `content-type` | `application/json` | requerido |
| `accept` | `application/json` | |
| `apikey` | `<SERLACA_API_KEY>` | **secreto** — `.env.local` |
| `username` | `<SERLACA_LACA_ID>` (ej. `34797703`) | nº de socia LACA de RenovArte |
| `origin` | `https://www.serlaca.com` | el server valida origen; enviarlo siempre |
| `referer` | `https://www.serlaca.com/` | idem |

> El `user-agent` de navegador y los `sec-ch-ua*` del curl de ejemplo no parecen
> necesarios; se prueba sin ellos y se agregan solo si la API responde 403.

### Body (JSON)

```json
{
  "currentPage": 1,
  "productLineCodes": [],
  "productCompositionIds": [],
  "productNecessityIds": [],
  "productCategoryIds": [],
  "productUseInIds": [],
  "searchText": "",
  "lacaId": "<SERLACA_LACA_ID>"
}
```

| Campo | Para la ingesta |
|---|---|
| `currentPage` | 1..`totalPages` — se itera (ver Paginación) |
| `productCategoryIds` | `[]` = todo el catálogo (confirmado en la corrida real). |
| `productLineCodes`, `productCompositionIds`, `productNecessityIds`, `productUseInIds` | `[]` (sin filtro) |
| `searchText` | `""` |
| `lacaId` | mismo valor que el header `username` |

---

## Paginación

Respuesta envuelta en `payload`:

```jsonc
{
  "payload": {
    "currentPage": 7,
    "totalPages": 13,
    "pageSize": 12,      // 12 ítems por página
    "totalItems": 152,
    "hasPrevious": true,
    "hasNext": true,
    "dataObjects": [ /* productos */ ],
    "urlFile": null
  },
  "error": null
}
```

Estrategia: pedir `currentPage: 1`, leer `totalPages`, pedir 2..N (o mientras
`payload.hasNext`). Acumular `dataObjects`. Si `error !== null` → abortar.
Reintentos acotados para 429/5xx.

---

## Objeto producto (`payload.dataObjects[i]`)

### Campos que usamos

| Campo API | Tipo | → modelo | Transformación |
|---|---|---|---|
| `productCode` | string | `id` / `codigo` | tal cual (`"510500003"`) |
| `name` | string | `nombre` | colapsar espacios; título si viene TODO EN MAYÚSCULAS |
| `productLine.name` | string | `categoria` | tal cual (`"Antiage"`, `"Pieles Grasas"`, `"Teens"`) |
| `productSize.size` + `productSize.measurementCode` | number + string | `presentacion` | `` `${size} ${code.toLowerCase()}` `` → `"250 g"`, `"70 ml"`, `"3.5 g"` |
| `detail` | string (HTML) | `descripcion` | decodificar entidades + quitar tags + colapsar `\r\n`/espacios |
| `price` | number | **`precio_costo`** | es el **costo** de RenovArte (cuenta de distribuidora, con IVA). Ej. `22600` |
| `imageURL` | string | `imagen` | ruta relativa; URL absoluta = `<SERLACA_IMAGE_BASE><imageURL>` |
| `professionalExclusive` | bool | filtro | `true` → se excluye del catálogo |

### Precio

La cuenta de serlaca de RenovArte es de **distribuidora**, así que el `price` que
devuelve la API **ya es el costo** de RenovArte (con IVA). No hay descuento.

```
precio_costo = price
precio_venta = round(price × (1 + MARGIN_PERCENT / 100))
```

Piso de margen desde el PDF de LACA (cuando aplica):
`precio_venta = max(precio_abc, precio_costo × (1 + MARGIN_PERCENT/100))` —
ver `transform/pricing.py`.

`MARGIN_PERCENT_*` va por env (`.env`/`.env.local`), nunca commiteado.
`priceSImp` (ese `price` sin IVA 21%, ≈ `price / 1.21`) **no se usa**.

### Campos que ignoramos

`subtitle`, `description` (siempre `null` en la muestra — usar `detail`),
`composition`, `productCompositions`, `productProtocols`, `rating*`,
`latestRatings`, `points`, `basePoints`, `pointsType`, `productByPdfs`,
`productCategory` (null), `productUsabilities`, `productNecessitiesOrFunctions`
(vacíos en la muestra), `productColor`, `productBaseCode`, `relatedProducts`,
`imageUrls` (vacío), `videoURL`, `infoUrl`, `bestSeller`, `forCabinet`,
`forHome`, `visible`.

### Datos útiles no usados aún

- `productLine.productLineId` (`"0104"`) y `productLine.color` (`"#F0587F"`) —
  código y color por categoría; podría alimentar un `CategoryNav` en el catálogo.
- `infoUrl` — link al catálogo público de LACA por producto.

---

## Gotchas observados

1. **`visible: false` en TODOS los productos de la muestra.** Si se filtrara por
   `visible`, el catálogo quedaría vacío → por ahora se ignora el campo.
2. **`detail` es HTML con entidades** (`&iacute;`, `&oacute;`, `&ntilde;`,
   `&trade;`, `&nbsp;`, `<p>`, `<strong>`, `<br />`, `\r\n`). Hay que
   decodificar + limpiar.
3. **`name` inconsistente**: algunos TODO MAYÚSCULAS
   (`"MASCARA SHOCK ANTIAGE X 250 G"`), otros mixto
   (`"Perfect Pore con Ácido Salicílico x100ml"`).
4. **No hay campo de oferta/promoción.** `en_oferta` se resuelve aparte
   (default `false` + override manual vía `data/offers.json`).
5. **`imageURL` es relativo** al file server de serlaca; se referencia como URL
   remota absoluta (`SERLACA_IMAGE_BASE + imageURL`).
6. **Duplicados por presentación**: `506120004` (100 ml) y `506120003` (235 ml)
   son el mismo producto en distinto tamaño, con `productCode` distinto. Se
   tratan como productos separados (cada uno tiene su código).

---

## Decisiones

1. **Costo:** `precio_costo = price` (cuenta de distribuidora, con IVA). **Sin
   descuento.** `precio_venta = round(price × (1 + MARGIN_PERCENT/100))`, o el
   precio del PDF cuando corresponde (ver arriba).
2. **`professionalExclusive: true` → se EXCLUYEN** de la ingesta. No entran a
   `products.json`.
3. **Imágenes: URL remota.** `imagen = SERLACA_IMAGE_BASE + imageURL` (absoluta,
   sin descargar). `SERLACA_IMAGE_BASE` por env. Si `imageURL` es `null` →
   `/img/placeholder.svg`.
4. **`en_oferta`: default `false`.** La API no trae ofertas; se marcan a mano en
   `data/offers.json` (`{ "codigos": { "<productCode>": { "descuento_pct"?: N } } }`),
   que `transform` aplica — badge y, opcional, N% off `precio_venta`. Con
   descuento, el producto también guarda `precio_regular` (precio sin la
   promo) y `descuento_pct`, para mostrar antes/ahora en la UI del catálogo.

## Confirmado en la corrida real (2026-09-10, y de nuevo 2026-09-14)

- `productCategoryIds: []` trae **todo el catálogo**: 434 productos crudos en 37
  páginas → 384 tras filtrar 50 `professionalExclusive`.
- Las imágenes **NO** están en `api.serlaca.com` (404). Se sirven desde
  `https://www.laboratoriolaca.com` + `imageURL` (mismo path `/files/Products/…`).
  `SERLACA_IMAGE_BASE=https://www.laboratoriolaca.com`; `renovarte-catalogo`'s
  `next.config.ts` `remotePatterns` incluye `www.laboratoriolaca.com` y
  `laboratoriolaca.com`.

### `productCategoryIds` por `productLine` — verificación spec 0001 AC-1 (2026-09-17)

Corrida real con `renovarte-pipeline verify-category-groups` (credenciales
reales, `data/input/category-group-report.json`, gitignored). Pide
`productCategoryIds: ["1"]` / `["2"]` / `["3"]` por separado y agrupa lo que
cada una devuelve por `productLine.name` (limpio con `clean_category`).

**Resultado: CON EXCEPCIONES — bloqueante para spec 0001.** De las 24
categorías específicas (`productLine`) hoy cargadas, **11 aparecen
repartidas entre más de un `productCategoryIds`** (no son mutuamente
excluyentes por categoría):

| Categoría | Grupos donde aparece |
|---|---|
| `Correctores e Iluminadores` | `2`, `3` |
| `Cuidados Básicos` | `1`, `2` |
| `Delineadores` | `2`, `3` |
| `LACA Beauty` | `1`, `2` |
| `Labios` | `1`, `2`, `3` |
| `Pestañas y Cejas` | `2`, `3` |
| `Protección Solar` | `1`, `2` |
| `Rostro` | `2`, `3` |
| `Sombras` | `2`, `3` |
| `Teens` | `1`, `2` |
| `Uñas` | `2`, `3` |

Las otras 13 categorías sí caen limpio en un único grupo (`Antiage`,
`Cuidados Masculinos`, `Dr. Enero`, `Hidratación`, `Pieles Delicadas`,
`Pieles Grasas`, `Renovación Celular` → `1`; `Corporales`, `Cuidados
Capilares`, `Fragancias`, `Manos y Pies`, `Sensorial` → `2`; `Pinceles y
Paletas` → `3`). `"1"`/`"2"`/`"3"` fueron, en efecto, los únicos ids que
devolvió la API en esta corrida (ninguna categoría quedó sin match en
ninguno de los tres).

**Consecuencia:** el diseño de `plan.md` §1(B) — mapeo por
categoría-específica-completa (`CATEGORY_GROUP_BY_CATEGORIA: dict[categoria,
id]`) — no es válido tal cual para estas 11 categorías: un mismo
`productLine` tiene productos individuales en más de un
`productCategoryIds` de Serlaca. Clasificar correctamente requeriría el/los
id(s) de grupo **por producto**, no inferido de `categoria` en `transform`
(ver `plan.md` §10, exactamente el riesgo que ese párrafo anticipaba). Este
hallazgo se reporta como bloqueante de spec 0001 — no se implementó
`pipeline/transform/category_groups.py` ni se tocó el resto del pipeline
sobre esta base; vuelve al `plan.md` antes de seguir.
