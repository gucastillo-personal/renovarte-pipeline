# RenovArte — Pipeline de ingesta

Ingesta y transformación de datos de catálogo para RenovArte: lee de la API
de Serlaca, de un CSV de respaldo, y (próximamente) del PDF de precios de
LACA, y produce el `products.json` estático que
[`renovarte-catalogo`](https://github.com/gucastillo-personal/renovarte-catalogo)
solo lee y muestra. Este repo es el único responsable de costo, margen y
cualquier dato sensible de proveedor — nada de eso cruza hacia el catálogo.

Es un submodule de
[`renovarte-parent`](https://github.com/gucastillo-personal/renovarte-parent);
el plan completo de esta separación (arquitectura, mapeo de migración desde
`renovarte-catalogo`, fases) está en `PLAN.md` de ese repo.

**Estado:** Fase 0 (scaffold) y Fase 1 (pricing/categorías/ofertas/CSV/API de
Serlaca, con paridad byte a byte verificada contra el pipeline TS original) y
Fase 2 (precio desde el PDF de LACA, spec 0008) hechas. Falta Fase 3
(automatizar el handoff vía PR) y Fase 4 (dar de baja el código viejo en
`renovarte-catalogo`). Ver `PLAN.md` en `renovarte-parent`.

**Extracción del PDF — validada contra un PDF real de LACA** (lista de
precios, 22 páginas, 230 productos extraídos). El parseo es por posición
fija de columnas, no por encabezado (el PDF real no tiene fila de
encabezado) — ver el docstring de `sources/pdf_laca.py` para el detalle de
por qué. Tres páginas del PDF probado no reconstruyeron bien la grilla
(`pdf extract`/`pdf review` avisan cuáles); si eso pasa con un PDF nuevo, es
esperable — se reporta, no se pierde en silencio.

## Stack

Python 3.13 · [uv](https://docs.astral.sh/uv/) · Pydantic · pdfplumber ·
httpx · pytest · ruff · mypy.

## Setup

```bash
uv sync
```

## Comandos

Con `make` (recomendado — ver `make help`):

```bash
make check                              # lint + typecheck + test
make ingest                             # Etapa 1: descarga cruda de Serlaca
make transform                          # Etapa 2: crudo -> products.json

# Precio desde el PDF de LACA (spec 0008). PDF= y FUENTE= son opcionales si
# hay un solo .pdf en data/raw/ — si hay más de uno, make corta y los lista.
make pdf-extract                        # PDF -> crudo + data/reference/laca_pdf_precios.csv
make pdf-review                         # match contra el catálogo + abre el reporte HTML
make pdf-workflow                       # extract + review en un solo paso
# elegir en el reporte, descargar precio_pdf_decisiones.json, y aplicarlo:
make pdf-apply-decisions FILE=~/Downloads/precio_pdf_decisiones.json
```

Equivalente sin `make`:

```bash
uv run renovarte-pipeline ingest
uv run renovarte-pipeline transform
uv run renovarte-pipeline pdf extract --pdf data/raw/laca.pdf --fuente "LACA 2026-09"
uv run renovarte-pipeline pdf review --pdf data/raw/laca.pdf --fuente "LACA 2026-09" \
  --catalog ../renovarte-catalogo/public/data/products.json
uv run renovarte-pipeline pdf apply-decisions ~/Downloads/precio_pdf_decisiones.json

uv run pytest        # tests
uv run ruff check .  # lint
uv run mypy          # type check
```

## Estructura

```
Makefile         # atajos: make help
src/pipeline/
├── models.py      # Product (schema público, RFC-0001 §2.4) y CostRow (interno)
├── cli.py         # entry point: ingest / transform / publish / pdf
├── pdf_cli.py     # subcomandos pdf: extract / review / apply-decisions
├── ingest/        # Etapa 1: descarga cruda por fuente
├── transform/      # Etapa 2: margen, ofertas, PDF overlay, limpieza -> Product
└── sources/       # adaptadores por fuente: Serlaca API, CSV, PDF de LACA
```

## Seguridad

- `data/raw/`, `data/input/`, `.env`/`.env.local` nunca se commitean (ver
  `.gitignore`) — contienen costo real y credenciales.
- El único artefacto público que este repo escribe hacia
  `renovarte-catalogo` es `public/data/products.json`, sin costo, margen ni
  precio de lista de LACA.
- El handoff hacia `renovarte-catalogo` es siempre vía Pull Request (nunca
  push directo a su `main`), y el merge queda a revisión humana.
