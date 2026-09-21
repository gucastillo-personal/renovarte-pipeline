"""Shared, source-agnostic core of the ingest pipeline. Every input is a
plain value so each function is unit-testable in isolation. Source adapters
live in `pipeline.sources`; orchestration in `pipeline.transform.build_catalog`.
"""

import json
import math
import re

from pipeline.models import CostRow, Product
from pipeline.transform.category_groups import resolve_cod_categoria

_NON_WORD_RE = re.compile(r"\s+")


def _js_round(value: float) -> int:
    """`Math.round` (round-half-up), not Python's banker's rounding."""
    return math.floor(value + 0.5)


def resolve_margin(categoria: str, env: dict[str, str | None]) -> float:
    """Margin percentage for a category: `MARGIN_PERCENT_<CATEGORY>`
    (upper-cased, spaces -> "_"), else `MARGIN_PERCENT_DEFAULT`, else 20
    (RFC §2.3 / §2.6). Raises if the resolved value is not a finite number
    >= 0.
    """
    key = f"MARGIN_PERCENT_{_NON_WORD_RE.sub('_', categoria.upper())}"
    source = env.get(key)
    if source is None:
        source = env.get("MARGIN_PERCENT_DEFAULT")
    if source is None:
        source = "20"
    try:
        # Mirrors JS's `Number(source)`: an all-whitespace string is 0, not NaN.
        n = 0.0 if source.strip() == "" else float(source)
    except ValueError:
        n = math.nan
    if not math.isfinite(n) or n < 0:
        raise ValueError(
            f'margen inválido para "{categoria}": {key}={env.get(key, "(no seteado)")}, '
            f'MARGIN_PERCENT_DEFAULT={env.get("MARGIN_PERCENT_DEFAULT", "(no seteado)")}'
        )
    return n


def compute_sale_price(costo: float, margin_percent: float) -> int:
    """precio_venta = round(costo * (1 + margen/100)) — RFC §2.3."""
    return _js_round(costo * (1 + margin_percent / 100))


def build_public_product(
    row: CostRow,
    margin: float,
    descuento_pct: float | None = None,
    pdf_price: int | None = None,
    cod_categoria: list[str] | None = None,
) -> Product:
    """Build one public product from a normalised `CostRow`.

    The cost (`precio_costo`) and the margin are consumed here and never
    stored (constitution §I).

    `cod_categoria` (spec 0001): the raw Serlaca group id(s) — "1"/"2"/"3",
    possibly more than one — resolved for this `codigo` by `build_catalog`
    from the per-product mapping `ingest` persisted in the raw dump. Passed
    through `resolve_cod_categoria` (which applies the `["4"]` fallback
    when `None`/empty) before being stored on `Product`.

    `descuento_pct` (spec 0007, from `data/offers.json`): when > 0, the
    regular price is kept as `precio_regular` and `precio_venta` becomes the
    discounted price. `None`/0 -> no offer-pricing fields, `precio_venta` is
    the regular price (unchanged behaviour).

    `pdf_price` (spec 0008, LACA's ABC price for this código): the "regular"
    price is `max(pdf_price, costo * (1 + margen))`, never just `pdf_price`
    outright — for ~1 in 3 real products, LACA's ABC price equals their own
    Precio Profesional (RenovArte's cost), so using it unconditionally would
    sell at zero margin. The floor guarantees RenovArte's configured margin
    always holds; LACA's price wins only when it's already at least as good.
    Applied *before* the offer discount, so a product that's both PDF-priced
    and on offer gets the discount computed on this resolved price, not on
    a plain costo+margen figure.
    """
    costo_mas_margen = compute_sale_price(row.precio_costo, margin)
    regular = max(pdf_price, costo_mas_margen) if pdf_price is not None else costo_mas_margen

    if descuento_pct is not None and descuento_pct > 0:
        precio_venta = _js_round(regular * (1 - descuento_pct / 100))
        precio_regular: int | None = regular
        descuento_pct_out: int | None = int(descuento_pct)
    else:
        precio_venta = regular
        precio_regular = None
        descuento_pct_out = None

    return Product(
        id=row.codigo,
        proveedor="LACA",
        categoria=row.categoria,
        codCategoria=resolve_cod_categoria(cod_categoria),
        nombre=row.nombre,
        presentacion=row.presentacion,
        descripcion=row.descripcion,
        precio_venta=precio_venta,
        precio_regular=precio_regular,
        descuento_pct=descuento_pct_out,
        imagen=row.imagen,
        en_oferta=row.en_oferta,
        tags=row.tags,
    )


def to_products_json(products: list[Product]) -> str:
    """Deterministic JSON for `public/data/products.json`: sorted by id,
    trailing newline.
    """
    sorted_products = sorted(products, key=lambda p: p.id)
    return json.dumps([p.to_public_dict() for p in sorted_products], indent=2, ensure_ascii=False) + "\n"
