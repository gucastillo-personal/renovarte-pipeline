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

**Estado:** Fases 0-3 hechas y **en producción** — el primer PR automático
real (`renovarte-catalogo#1`) se abrió y mergeó con éxito. Fase 4 (dar de
baja el código viejo en `renovarte-catalogo`) sigue pendiente. Ver
`PLAN.md` en `renovarte-parent`.

**Precio del PDF de LACA — fuente primaria, automática.** `transform` carga
`data/reference/laca_pdf_precios.csv` (generado por `pdf-extract`) y usa el
precio ABC directo para todo código que matchea, **sin revisión manual por
producto**. Sin match — o sin ABC en el PDF — el producto sigue con
costo+margen, igual que siempre; nada desaparece del catálogo por no estar
en el PDF de un mes dado. El descuento de `data/offers.json` se aplica
después, sobre el precio ya resuelto. Ver
[`docs/flujo-precio-pdf.md`](../docs/flujo-precio-pdf.md) en
`renovarte-parent` para el diagrama completo.

**Extracción del PDF — validada contra un PDF real de LACA** (lista de
precios, 22 páginas, 230 productos extraídos, 220 con precio ABC). El
parseo es por posición fija de columnas, no por encabezado (el PDF real no
tiene fila de encabezado) — ver el docstring de `sources/pdf_laca.py` para
el detalle de por qué. Tres páginas del PDF probado no reconstruyeron bien
la grilla (`pdf-extract` avisa cuáles); si eso pasa con un PDF nuevo, es
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

# Cuando baja un PDF nuevo de LACA (manual, ocasional). PDF= y FUENTE= son
# opcionales si hay un solo .pdf en data/raw/ — si hay más de uno, make
# corta y los lista.
make pdf-extract                        # PDF -> data/reference/laca_pdf_precios.csv (committed)

make ingest                             # Etapa 1: descarga cruda de Serlaca
make transform                          # Etapa 2: crudo + PDF + ofertas -> products.json

# Publicar hacia renovarte-catalogo (Fase 3) — CATALOGO_CHECKOUT SIEMPRE un
# clon descartable, nunca tu carpeta de trabajo real (publish le hace
# reset --hard):
make publish CATALOGO_CHECKOUT=/tmp/catalogo-publish        # dry-run: prepara la rama, no pushea
make publish-live CATALOGO_CHECKOUT=/tmp/catalogo-publish   # pushea y abre el PR de verdad
```

Equivalente sin `make`:

```bash
uv run renovarte-pipeline pdf-extract --pdf data/raw/laca.pdf --fuente "LACA 2026-09"
uv run renovarte-pipeline ingest
uv run renovarte-pipeline transform

uv run pytest        # tests
uv run ruff check .  # lint
uv run mypy          # type check
```

## Estructura

```
Makefile                       # atajos: make help
.github/workflows/publish.yml  # cron + disparo manual: ingest -> transform -> publish
src/pipeline/
├── models.py      # Product (schema público, RFC-0001 §2.4) y CostRow (interno)
├── cli.py         # entry point: ingest / transform / publish / pdf-extract
├── pdf_cli.py     # comando pdf-extract
├── ingest/        # Etapa 1: descarga cruda por fuente
├── transform/      # Etapa 2: margen, ofertas, precio del PDF, limpieza -> Product
├── sources/       # adaptadores por fuente: Serlaca API, CSV, PDF de LACA
└── publish/       # Fase 3: leak-check + rama/commit + PR contra renovarte-catalogo
```

## Publicar hacia renovarte-catalogo (Fase 3)

`renovarte-pipeline publish` nunca pushea a `main` de `renovarte-catalogo`:
prepara una rama (`pipeline/auto-update-products`, se resetea desde `main`
en cada corrida — no acumula commits viejos), corre el leak-check
(`pipeline/publish/leak_check.py`, espeja `check-leak.mjs`) y recién si pasa
push+abre PR. Sin `--live` (o sin `GITHUB_TOKEN`), queda en dry-run: prepara
todo localmente y no toca GitHub.

`.github/workflows/publish.yml` corre `ingest` → `transform` → `publish
--live` en un cron semanal + disparo manual. Para activarlo, cargar estos
secrets en **Settings → Secrets and variables → Actions** de este repo en
GitHub:

| Secret | Para qué |
|---|---|
| `SERLACA_API_KEY`, `SERLACA_LACA_ID` | Etapa 1 (`ingest`) |
| `SERLACA_IMAGE_BASE`, `MARGIN_PERCENT_DEFAULT` | Etapa 2 (`transform`) |
| `CATALOGO_PAT` | Etapa 3 (`publish`) — ver abajo |

**`CATALOGO_PAT`**, paso a paso:
1. GitHub → tu foto de perfil → **Settings** → **Developer settings** →
   **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. **Repository access**: "Only select repositories" → elegir únicamente
   `renovarte-catalogo`. Nunca "All repositories".
3. **Permissions** → Repository permissions: `Contents` = Read and write,
   `Pull requests` = Read and write. Todo lo demás en "No access".
4. Generar, copiar el token, y cargarlo como secret `CATALOGO_PAT` en
   `renovarte-pipeline` (nunca commitearlo, nunca pegarlo en un chat).

El primer PR real (`make publish-live` o disparar la Action a mano desde
GitHub) conviene correrlo vos mismo la primera vez, para ver el diff y
confirmar que todo anda antes de dejarlo en piloto automático semanal.

## Seguridad

- `data/raw/`, `data/input/`, `.env`/`.env.local` nunca se commitean (ver
  `.gitignore`) — contienen costo real y credenciales.
- El único artefacto público que este repo escribe hacia
  `renovarte-catalogo` es `public/data/products.json`, sin costo, margen ni
  precio de lista de LACA.
- El handoff hacia `renovarte-catalogo` es siempre vía Pull Request (nunca
  push directo a su `main`), y el merge queda a revisión humana.
