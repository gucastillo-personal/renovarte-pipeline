"""ETAPA 2 — transformación (spec 0009).

Toma el crudo (dump de la API o un CSV), aplica margen + limpieza de
categorías + filtro de profesional-exclusivos + ofertas (`data/offers.json`),
y escribe `public/data/products.json` listo para la app.

El `price` del input ES el costo de RenovArte (cuenta de distribuidora):
    precio_venta = round(price * (1 + MARGIN_PERCENT/100))
"""

import json
from pathlib import Path

from pipeline.sources.serlaca_api import DEFAULT_IMAGE_BASE, raw_to_cost_rows
from pipeline.transform.build_catalog import BuildCatalogResult, build_catalog, build_catalog_from_csv
from pipeline.transform.offers import load_offers
from pipeline.transform.pdf_decisions import load_decisions

DEFAULT_IN_PATH = Path("data") / "input" / "serlaca-raw.json"
DEFAULT_OFFERS_PATH = Path("data") / "offers.json"
DEFAULT_OUT_PATH = Path("public") / "data" / "products.json"
DEFAULT_PDF_DECISIONS_PATH = Path("data") / "reference" / "precio_pdf_decisiones.json"


def run(
    env: dict[str, str | None],
    in_path: str | Path = DEFAULT_IN_PATH,
    out_path: str | Path = DEFAULT_OUT_PATH,
    offers_path: str | Path = DEFAULT_OFFERS_PATH,
    public_dir: str | Path = Path("public"),
    pdf_decisions_path: str | Path = DEFAULT_PDF_DECISIONS_PATH,
) -> BuildCatalogResult:
    in_path = Path(in_path)
    offers = load_offers(offers_path)
    pdf_decisions = load_decisions(pdf_decisions_path)

    if in_path.suffix == ".csv":
        result = build_catalog_from_csv(in_path, out_path, env, public_dir, offers, pdf_decisions)
    else:
        try:
            dump = json.loads(in_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise ValueError(
                f"no pude leer el crudo en {in_path} (¿corriste `renovarte-pipeline ingest`?): {error}"
            ) from error
        data_objects = dump.get("dataObjects")
        if not isinstance(data_objects, list):
            raise ValueError(f"{in_path} no tiene un array `dataObjects`")

        mapped = raw_to_cost_rows(data_objects, image_base=env.get("SERLACA_IMAGE_BASE") or DEFAULT_IMAGE_BASE)
        built = build_catalog(mapped.rows, env, out_path, offers, pdf_decisions)
        result = BuildCatalogResult(products=built.products, warnings=[*mapped.warnings, *built.warnings])

    for warning in result.warnings:
        print(f"⚠  {warning}")

    offer_count = sum(1 for p in result.products if p.en_oferta)
    print(f"✓ {len(result.products)} producto(s) ({offer_count} en oferta) → {out_path}")
    return result
