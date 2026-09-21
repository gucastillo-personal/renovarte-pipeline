# PRD — RenovArte Pipeline

| | |
|---|---|
| **Estado** | Draft |
| **Autor** | RenovArte |
| **Fecha** | 2026-09-17 |
| **Contexto** | Primer PRD formal de este repo. Nació por migración de código
existente desde `renovarte-catalogo` (ver `renovarte-parent/PLAN.md`); este
documento formaliza, con requisitos `RF-`/`RNF-`, lo que ya está construido
y en producción, y agrega el primer requisito nuevo pedido después de la
migración. |

---

## 1. Problema

RenovArte vende productos de LACA (vía la distribuidora Serlaca) y necesita
mantener actualizado el catálogo público de `renovarte-catalogo` sin
exponer nunca costo, margen ni precio de lista — pero sí necesita procesar
esos datos sensibles en algún lugar antes de publicar solo el precio final.
Mezclar esa ingesta/transformación con el repo de presentación (como
ocurría antes de la migración de 2026-09) arriesgaba filtrar esos datos al
bundle público y acoplaba el ciclo de vida de "traer y calcular precios" al
de "mostrar el catálogo".

## 2. Objetivo

Ser el único responsable de ingerir datos crudos de proveedores (hoy LACA
vía la API de Serlaca, con CSV de respaldo), calcular el precio público
(costo + margen, con el PDF de LACA como fuente primaria cuando aplica), y
publicar el resultado — sin datos sensibles — como `products.json` hacia
`renovarte-catalogo`, vía Pull Request revisado por un humano.

### 2.1 Objetivos de negocio

- Que actualizar precios cuando LACA cambia su lista sea un proceso
  repetible (`make ingest && make transform`), no manual línea por línea.
- Que el costo real y el margen aplicado nunca puedan filtrarse al sitio
  público, ni por error de un desarrollador.
- Dejar la base lista para sumar más fuentes/proveedores sin tocar el
  contrato con `renovarte-catalogo`.

## 3. Usuarios / audiencia

| Usuario | Necesidad |
|---|---|
| Admin (dueño de RenovArte) | Correr la actualización de catálogo/precios cuando cambia la lista de LACA, revisar el diff antes de publicar, sin depender de un developer para cada corrida |
| `renovarte-catalogo` (repo consumidor) | Recibir `public/data/products.json` ya validado, sin datos sensibles, solo vía Pull Request |

No hay usuario final (cliente comprador) directo de este repo — ese es
`renovarte-catalogo`.

## 4. Alcance

### 4.1 Dentro de alcance (construido)

- Ingesta desde la API de Serlaca (fuente primaria) y desde un CSV de
  respaldo.
- Cálculo de precio de venta (costo + margen configurable por variable de
  entorno, sin tocar código).
- Incorporación del precio de referencia del PDF de LACA (precio ABC) como
  fuente primaria de precio cuando hay match por código, con piso de margen
  (nunca por debajo de costo + margen); sin match, sigue con costo+margen.
- Aplicación de ofertas (`data/offers.json`) sobre el precio ya resuelto.
- Publicación automatizada: `publish` abre un Pull Request contra
  `renovarte-catalogo` (nunca push directo a su `main`); el merge queda a
  revisión humana.
- Leak-check antes de publicar (defensa en origen, espejo del
  `check:leak` de `renovarte-catalogo`).
- Salida determinística siguiendo exactamente el schema público de
  RFC-0001 §2.4 de `renovarte-catalogo`.

### 4.2 Fuera de alcance

- Cualquier UI o presentación del catálogo (responsabilidad de
  `renovarte-catalogo`).
- Corridas automáticas de `ingest`/`transform`/`pdf-extract` — son siempre
  manuales, corridas por el admin; la GitHub Action de este repo corre
  únicamente `publish`.
- Carrito, checkout, stock en tiempo real.
- Base de datos o backend propio — el estado es archivos versionados en
  git (`data/reference/*`, `public/data/products.json`).

## 5. Requisitos funcionales

| ID | Requisito |
|---|---|
| RF-01 | El sistema debe poder ingerir productos crudos desde la API de Serlaca, paginando hasta agotar el catálogo, sin filtrar ni transformar en esta etapa. |
| RF-02 | El sistema debe poder ingerir productos crudos desde un CSV de respaldo cuando la API de Serlaca no está disponible. |
| RF-03 | El sistema debe calcular `precio_venta` como costo real más un margen configurable por variable de entorno (por categoría, con default), sin exponer nunca el costo. |
| RF-04 | El sistema debe poder incorporar precios de referencia extraídos del PDF público de LACA (Precio Profesional / ABC / Catálogo) y, cuando hay match de código, usar el precio ABC como precio de venta, nunca por debajo de costo + margen (piso de margen); el Precio Profesional (costo del revendedor) nunca se commitea ni se publica. |
| RF-05 | El sistema debe poder marcar productos en oferta (`data/offers.json`) y calcular `precio_regular`/`descuento_pct` sobre el precio ya resuelto (PDF o costo+margen). |
| RF-06 | El sistema debe publicar `public/data/products.json` hacia `renovarte-catalogo` exclusivamente vía Pull Request, nunca con push directo a su rama principal. |
| RF-07 | El sistema debe correr un chequeo de fuga de datos sensibles (leak-check) antes de abrir el Pull Request de publicación. |
| RF-08 | La salida pública debe seguir exactamente el schema definido en RFC-0001 §2.4 de `renovarte-catalogo` (`proveedor, categoria, nombre, presentacion, descripcion, precio_venta, imagen, en_oferta, tags`, más los opcionales de oferta); agregar una clave requiere enmendar ese RFC en ambos repos. |
| RF-09 *(nuevo, 2026-09-17; detalle de mapeo confirmado por el CTO/CEO el mismo día)* | El sistema debe publicar, para cada producto, el campo `codCategoria` con el id crudo de `productCategoryIds` de Serlaca (`"1"` = Cuidado facial, `"2"` = Cuidado corporal, `"3"` = Cosmética, `"4"` = fallback para todo producto sin match), más un archivo JSON de mapeo `codCategoria` → nombre de grupo, committed y separado del código, para que `renovarte-catalogo` pueda ofrecer una navegación de filtros en dos niveles (ver `renovarte-catalogo` PRD RF-13). |

## 6. Requisitos no funcionales

| ID | Requisito |
|---|---|
| RNF-01 | Costo de infraestructura $0 — solo free tier de GitHub Actions, sin backend ni base de datos propios. |
| RNF-02 | `ingest`, `transform` y `pdf-extract` son siempre manuales, corridos por el admin en su máquina; la GitHub Action de este repo nunca genera datos, solo publica lo ya commiteado. |
| RNF-03 | Determinismo: correr `transform` dos veces sobre el mismo input debe producir `public/data/products.json` idéntico byte a byte (orden de claves estable). |
| RNF-04 | El costo real, el margen aplicado y el precio de lista de LACA no deben estar presentes en ningún archivo público de este repo ni cruzar hacia `renovarte-catalogo`. |
| RNF-05 | Python 3.13 + `uv`, con `ruff`, `mypy` y `pytest` en verde (`make check`) antes de considerar algo terminado. |

## 7. Métricas de éxito

- El flujo `make ingest && make transform` → revisar diff → commit/push →
  Pull Request a `renovarte-catalogo` es repetible y documentado en el
  README.
- Ninguna corrida real filtró costo/margen/precio de lista al repo de
  destino (verificado por leak-check en origen y destino).
- El `products.json` publicado pasa el gate completo de `renovarte-catalogo`
  (`pnpm gate`) sin cambios de código de ese lado.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Cambios de formato/campos en la API de Serlaca rompen la ingesta silenciosamente | Validación explícita de los campos leídos (`assert_serlaca_product`) antes de mapear |
| Migrar código que lee un archivo (p.ej. `data/offers.json`) sin migrar el archivo real | Verificación aparte del dato, no solo del código (ver hallazgo post-implementación en `renovarte-parent/PLAN.md`) |
| Agregar un campo nuevo al schema público sin coordinar con `renovarte-catalogo` | RFC-0001 §2.4 se enmienda en ambos repos antes de publicar el campo nuevo (constitution.md ítem 7) |
| Publicar `productCategoryIds`/agrupación de alto nivel mal mapeada (producto en el grupo equivocado) | Verificar el mapeo contra una muestra real de la API antes de publicar (ver spec 0001, AC-2) |

## 9. Referencias

- `renovarte-parent/PLAN.md` — arquitectura de la separación
  catálogo/pipeline y fases de migración.
- RFC-0001 §2.4 de `renovarte-catalogo` — schema público que este repo
  produce.
- `docs/serlaca-api.md` — referencia del endpoint de Serlaca usado por la
  ingesta.
