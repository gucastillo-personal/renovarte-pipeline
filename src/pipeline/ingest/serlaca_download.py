"""ETAPA 1 — descarga (spec 0009, extendida por spec 0001 para
codCategoria).

Baja el catálogo CRUDO de la API de Serlaca (paginado, sin transformar) a
`data/input/serlaca-raw.json`, más el mapeo por-producto `productCode ->
lista de productCategoryIds` (spec 0001, clave `categoryGroupsByProductCode`
en el crudo) — derivado de tres llamadas adicionales, una por grupo
(`productCategoryIds: ["1"]`/`["2"]`/`["3"]`), reusando el mismo mecanismo
que `verify-category-groups`. Un producto puede pertenecer a más de un
grupo (verificado contra la API real 2026-09-17 — ver docs/serlaca-api.md).
No aplica descuento, margen, filtros ni limpieza — eso es la etapa 2
(`pipeline.transform`).

Config (`SERLACA_API_KEY`, `SERLACA_LACA_ID`, `SERLACA_CATEGORY_IDS`
opcional), leída de `.env`/`.env.local`.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from pipeline.ingest.verify_category_groups import fetch_category_group_samples
from pipeline.sources.serlaca_api import fetch_all_serlaca_pages, group_ids_by_product_code

DEFAULT_RAW_PATH = Path("data") / "input" / "serlaca-raw.json"


def parse_category_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        try:
            ids.append(int(part.strip()))
        except ValueError:
            continue
    return ids


def run(env: dict[str, str | None], raw_path: str | Path = DEFAULT_RAW_PATH) -> Path:
    """Download the raw catalog + the per-product category-group mapping
    (spec 0001), and write both to `raw_path`. Returns the path."""
    category_ids = parse_category_ids(env.get("SERLACA_CATEGORY_IDS"))
    dump = fetch_all_serlaca_pages(
        api_key=env.get("SERLACA_API_KEY") or "",
        laca_id=env.get("SERLACA_LACA_ID") or "",
        category_ids=category_ids,
    )

    group_samples = fetch_category_group_samples(env)
    category_groups_by_product_code = group_ids_by_product_code(group_samples)

    out = {
        "_meta": {
            "fetchedAt": datetime.now(UTC).isoformat(),
            "source": "serlaca-api",
            "totalItems": dump.total_items,
            "pages": dump.pages,
            "categoryIds": category_ids,
        },
        "dataObjects": dump.data_objects,
        "categoryGroupsByProductCode": category_groups_by_product_code,
    }

    path = Path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"✓ {dump.total_items} producto(s) crudos ({dump.pages} página(s)) → {path}")
    print(f"  {len(category_groups_by_product_code)} producto(s) con grupo de categoría (codCategoria) clasificado")
    print("  Siguiente: renovarte-pipeline transform")
    return path
