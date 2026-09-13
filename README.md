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

**Estado:** scaffold inicial (Fase 0 del plan) — la lógica de ingesta/
transformación todavía no está portada.

## Stack

Python 3.13 · [uv](https://docs.astral.sh/uv/) · Pydantic · pytest · ruff · mypy.
La extracción del PDF de LACA usará `pdfplumber` (Fase 2).

## Setup

```bash
uv sync
```

## Comandos

```bash
uv run renovarte-pipeline ingest      # Etapa 1: descarga cruda (WIP)
uv run renovarte-pipeline transform   # Etapa 2: crudo -> products.json (WIP)
uv run renovarte-pipeline publish     # Abre PR a renovarte-catalogo (WIP)

uv run pytest       # tests
uv run ruff check .  # lint
uv run mypy          # type check
```

## Estructura

```
src/pipeline/
├── models.py      # Product (schema público, RFC-0001 §2.4) y CostRow (interno)
├── cli.py         # entry point: ingest / transform / publish
├── ingest/        # Etapa 1: descarga cruda por fuente
├── transform/      # Etapa 2: margen, ofertas, limpieza de categorías -> Product
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
