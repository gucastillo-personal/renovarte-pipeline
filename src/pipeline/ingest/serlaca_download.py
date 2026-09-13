"""ETAPA 1 — descarga (spec 0009).

Baja el catálogo CRUDO de la API de Serlaca (paginado, sin transformar) a
`data/input/serlaca-raw.json`. No aplica descuento, margen, filtros ni
limpieza — eso es la etapa 2 (`pipeline.transform`).

Config (`SERLACA_API_KEY`, `SERLACA_LACA_ID`, `SERLACA_CATEGORY_IDS`
opcional), leída de `.env`/`.env.local`.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from pipeline.sources.serlaca_api import fetch_all_serlaca_pages

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
    """Download the raw catalog and write it to `raw_path`. Returns the path."""
    category_ids = parse_category_ids(env.get("SERLACA_CATEGORY_IDS"))
    dump = fetch_all_serlaca_pages(
        api_key=env.get("SERLACA_API_KEY") or "",
        laca_id=env.get("SERLACA_LACA_ID") or "",
        category_ids=category_ids,
    )

    out = {
        "_meta": {
            "fetchedAt": datetime.now(UTC).isoformat(),
            "source": "serlaca-api",
            "totalItems": dump.total_items,
            "pages": dump.pages,
            "categoryIds": category_ids,
        },
        "dataObjects": dump.data_objects,
    }

    path = Path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"✓ {dump.total_items} producto(s) crudos ({dump.pages} página(s)) → {path}")
    print("  Siguiente: renovarte-pipeline transform")
    return path
