"""ETAPA 2 — transformación (spec 0009).

Toma el crudo (dump de la API o un CSV), aplica margen + limpieza de
categorías + filtro de profesional-exclusivos + ofertas (`data/offers.json`)
+ precio del PDF de LACA (automático, por código, desde
`data/reference/laca_pdf_precios.csv` — ver `build_catalog.py`), y escribe
`public/data/products.json` listo para la app.

El `price` del input ES el costo de RenovArte (cuenta de distribuidora):
    precio_venta = round(price * (1 + MARGIN_PERCENT/100))
Ese cálculo es el fallback para todo producto sin precio ABC en el PDF.
"""

import json
from pathlib import Path

from pipeline.sources.serlaca_api import DEFAULT_IMAGE_BASE, raw_to_cost_rows
from pipeline.transform.build_catalog import BuildCatalogResult, build_catalog, build_catalog_from_csv
from pipeline.transform.offers import load_offers
from pipeline.transform.pdf_reference import load_pdf_prices

DEFAULT_IN_PATH = Path("data") / "input" / "serlaca-raw.json"
DEFAULT_OFFERS_PATH = Path("data") / "offers.json"
DEFAULT_OUT_PATH = Path("public") / "data" / "products.json"
DEFAULT_PDF_REFERENCE_PATH = Path("data") / "reference" / "laca_pdf_precios.csv"


def run(
    env: dict[str, str | None],
    in_path: str | Path = DEFAULT_IN_PATH,
    out_path: str | Path = DEFAULT_OUT_PATH,
    offers_path: str | Path = DEFAULT_OFFERS_PATH,
    public_dir: str | Path = Path("public"),
    pdf_reference_path: str | Path = DEFAULT_PDF_REFERENCE_PATH,
) -> BuildCatalogResult:
    in_path = Path(in_path)
    offers = load_offers(offers_path)
    pdf_prices = load_pdf_prices(pdf_reference_path)

    if in_path.suffix == ".csv":
        result = build_catalog_from_csv(in_path, out_path, env, public_dir, offers, pdf_prices)
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
        built = build_catalog(mapped.rows, env, out_path, offers, pdf_prices)
        result = BuildCatalogResult(products=built.products, warnings=[*mapped.warnings, *built.warnings])

    for warning in result.warnings:
        print(f"⚠  {warning}")

    ids = {p.id for p in result.products}
    pdf_pricing_count = len(ids & pdf_prices.keys())
    offer_count = sum(1 for p in result.products if p.en_oferta)
    print(
        f"✓ {len(result.products)} producto(s) ({pdf_pricing_count} con precio del PDF, "
        f"{offer_count} en oferta) → {out_path}"
    )
    return result
