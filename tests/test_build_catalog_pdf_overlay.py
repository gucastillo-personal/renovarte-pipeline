"""AC-5 de spec 0008: el overlay de precio del PDF se aplica después de
costo+margen y antes del descuento de oferta; códigos sin decisión no
cambian de comportamiento.
"""

from pathlib import Path

from pipeline.models import CostRow
from pipeline.transform.build_catalog import build_catalog
from pipeline.transform.offers import Offer
from pipeline.transform.pdf_decisions import PdfDecision


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


def test_decision_overrides_costo_mas_margen(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},  # would give 1200 without the override
        out_path=tmp_path / "products.json",
        pdf_decisions={"001": PdfDecision(fuente="abc", valor=1300)},
    )
    assert result.products[0].precio_venta == 1300
    assert result.products[0].precio_regular is None  # no offer involved


def test_actual_decision_keeps_costo_mas_margen(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        pdf_decisions={"001": PdfDecision(fuente="actual", valor=1200)},
    )
    assert result.products[0].precio_venta == 1200


def test_no_decision_is_unchanged_behaviour(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        pdf_decisions=None,
    )
    assert result.products[0].precio_venta == 1200


def test_offer_discount_applies_on_top_of_pdf_price_not_costo_mas_margen(tmp_path: Path) -> None:
    result = build_catalog(
        [_row()],
        env={"MARGIN_PERCENT_DEFAULT": "20"},  # costo+margen would be 1200
        out_path=tmp_path / "products.json",
        offers={"001": Offer(descuento_pct=10)},
        pdf_decisions={"001": PdfDecision(fuente="abc", valor=1300)},
    )
    product = result.products[0]
    assert product.precio_regular == 1300  # the PDF price, not 1200
    assert product.precio_venta == 1170  # round(1300 * 0.9), not round(1200 * 0.9)
    assert product.descuento_pct == 10


def test_codigo_without_decision_unaffected_by_others_having_one(tmp_path: Path) -> None:
    result = build_catalog(
        [_row(codigo="001"), _row(codigo="002")],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        pdf_decisions={"001": PdfDecision(fuente="abc", valor=1300)},
    )
    by_id = {p.id: p for p in result.products}
    assert by_id["001"].precio_venta == 1300
    assert by_id["002"].precio_venta == 1200
