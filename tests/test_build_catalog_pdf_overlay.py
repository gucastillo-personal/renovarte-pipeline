"""El precio del PDF de LACA (por código, automático) se aplica antes del
descuento de oferta; códigos sin precio en el PDF siguen con costo+margen,
sin cambios de comportamiento.
"""

from pathlib import Path

from pipeline.models import CostRow
from pipeline.transform.build_catalog import build_catalog
from pipeline.transform.offers import Offer


def _row(**overrides: object) -> CostRow:
    base = {
        "codigo": "001",
        "nombre": "Producto Uno",
        "categoria": "Antiage",
        "presentacion": "50 g",
        "descripcion": "",
        "precio_costo": 1000.0,
        "en_oferta": False,
        "tags": [],
        "imagen": "/img/placeholder.svg",
    }
    base.update(overrides)
    return CostRow(**base)  # type: ignore[arg-type]


def test_pdf_price_overrides_costo_mas_margen(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},  # would give 1200 without the override
        out_path=tmp_path / "products.json",
        pdf_prices={"001": 1300},
    )
    assert result.products[0].precio_venta == 1300
    assert result.products[0].precio_regular is None  # no offer involved


def test_no_pdf_price_is_unchanged_behaviour(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        pdf_prices=None,
    )
    assert result.products[0].precio_venta == 1200


def test_codigo_without_pdf_price_falls_back_to_costo_mas_margen(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        pdf_prices={"999": 5000},  # a different codigo — irrelevant to this row
    )
    assert result.products[0].precio_venta == 1200


def test_offer_discount_applies_on_top_of_pdf_price_not_costo_mas_margen(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},  # costo+margen would be 1200
        out_path=tmp_path / "products.json",
        offers={"001": Offer(descuento_pct=10)},
        pdf_prices={"001": 1300},
    )
    product = result.products[0]
    assert product.precio_regular == 1300  # the PDF price, not 1200
    assert product.precio_venta == 1170  # round(1300 * 0.9), not round(1200 * 0.9)
    assert product.descuento_pct == 10


def test_codigo_without_pdf_price_unaffected_by_others_having_one(tmp_path: Path) -> None:
    result = build_catalog(
        [_row(codigo="001"), _row(codigo="002")],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        pdf_prices={"001": 1300},
    )
    by_id = {p.id: p for p in result.products}
    assert by_id["001"].precio_venta == 1300
    assert by_id["002"].precio_venta == 1200
