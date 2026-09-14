"""Transform stage core (spec 0009): normalised `CostRow`s -> public
`Product`s -> `public/data/products.json`, applying category cleanup and the
configured margin per category. Source-agnostic (CSV or Serlaca API raw
dump).

Precio del PDF de LACA es la fuente primaria de `precio_venta` (por
código, vía `pdf_prices`): cuando un producto matchea contra la referencia
pública del PDF (`data/reference/laca_pdf_precios.csv`, cargada
automáticamente por `transform`), ese precio ABC se usa directo, sin
revisión manual. Sin match — o sin ABC en el PDF — el producto sigue con
costo+margen, igual que siempre. El descuento de oferta (`data/offers.json`)
se aplica después, sobre el precio ya resuelto sea cual sea su origen.

Raises (writing nothing) on a bad margin env var, any row-level error, or
output that fails the app's own `validate_products` contract. The internal
margin report is spec 0007 and is not produced here.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from pipeline.models import CostRow, Product, validate_products
from pipeline.sources.csv_source import read_csv_cost_rows
from pipeline.transform.categories import clean_category
from pipeline.transform.offers import Offer
from pipeline.transform.pricing import build_public_product, resolve_margin, to_products_json

_NON_WORD_RE = re.compile(r"\s+")


@dataclass
class BuildCatalogResult:
    products: list[Product]
    warnings: list[str]


def build_catalog(
    rows: list[CostRow],
    env: dict[str, str | None],
    out_path: str | Path,
    offers: dict[str, Offer] | None = None,
    pdf_prices: dict[str, int] | None = None,
) -> BuildCatalogResult:
    if len(rows) == 0:
        raise ValueError("transform abortado: no hay productos para procesar")

    offers = offers or {}
    pdf_prices = pdf_prices or {}

    # Normalise category names (spec 0009 AC-5) and flag manual offers
    # (spec 0005) before anything groups or builds.
    normalised = [
        CostRow(
            **{
                **row.model_dump(),
                "categoria": clean_category(row.categoria),
                "en_oferta": True if row.codigo.strip() in offers else row.en_oferta,
            }
        )
        for row in rows
    ]

    warnings: list[str] = []

    # Resolve margins once per category so a bad env var fails fast with one message.
    categorias = list(dict.fromkeys(r.categoria.strip() for r in normalised if r.categoria.strip()))
    margin_by_categoria: dict[str, float] = {}
    used_default: list[str] = []
    for categoria in categorias:
        margin_by_categoria[categoria] = resolve_margin(categoria, env)
        key = f"MARGIN_PERCENT_{_NON_WORD_RE.sub('_', categoria.upper())}"
        if env.get(key) is None:
            used_default.append(categoria)
    if used_default:
        pct = env.get("MARGIN_PERCENT_DEFAULT") or "20"
        warnings.append(
            f"{len(used_default)} categoría(s) sin MARGIN_PERCENT_* propio → "
            f"MARGIN_PERCENT_DEFAULT ({pct}%): {', '.join(used_default)}"
        )

    errors: list[str] = []
    products: list[Product] = []

    for index, row in enumerate(normalised):
        try:
            categoria = row.categoria.strip()
            if not categoria:
                raise ValueError('campo "categoria" vacío')
            if not row.codigo.strip():
                raise ValueError('campo "codigo" vacío')
            margin = margin_by_categoria.get(categoria)
            if margin is None:
                raise ValueError(f"categoría desconocida: {categoria}")

            offer = offers.get(row.codigo.strip())
            descuento_pct = offer.descuento_pct if offer is not None else None

            # PDF price (primary source, automatic): applied before the
            # offer discount, so a discounted product on a PDF price gets
            # the discount computed on that price, not on costo+margen.
            precio_override = pdf_prices.get(row.codigo.strip())

            products.append(build_public_product(row, margin, descuento_pct, precio_override))
        except Exception as error:
            errors.append(f"item {index + 1}: {error}")

    if errors:
        joined = "\n  ".join(errors)
        raise ValueError(f"transform abortado ({len(errors)} error(es)):\n  {joined}")

    # Final gate: the output must satisfy the exact contract the app consumes.
    validated = validate_products([p.to_public_dict() for p in products])

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_products_json(validated), encoding="utf-8")

    return BuildCatalogResult(products=validated, warnings=warnings)


def build_catalog_from_csv(
    csv_path: str | Path,
    out_path: str | Path,
    env: dict[str, str | None],
    public_dir: str | Path,
    offers: dict[str, Offer] | None = None,
    pdf_prices: dict[str, int] | None = None,
) -> BuildCatalogResult:
    """CSV-source convenience wrapper (spec 0002 fallback)."""
    rows, warnings = read_csv_cost_rows(csv_path, public_dir)
    result = build_catalog(rows, env, out_path, offers, pdf_prices)
    return BuildCatalogResult(products=result.products, warnings=[*warnings, *result.warnings])
