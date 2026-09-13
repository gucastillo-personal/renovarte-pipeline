import pytest

from pipeline.models import CostRow
from pipeline.transform.pricing import build_public_product, compute_sale_price, resolve_margin, to_products_json


def test_resolve_margin_uses_category_override() -> None:
    env: dict[str, str | None] = {"MARGIN_PERCENT_ANTIAGE": "30", "MARGIN_PERCENT_DEFAULT": "20"}
    assert resolve_margin("Antiage", env) == 30


def test_resolve_margin_falls_back_to_default() -> None:
    env: dict[str, str | None] = {"MARGIN_PERCENT_DEFAULT": "20"}
    assert resolve_margin("Corporales", env) == 20


def test_resolve_margin_defaults_to_20_with_no_env() -> None:
    assert resolve_margin("Corporales", {}) == 20


def test_resolve_margin_category_key_uppercases_and_replaces_spaces() -> None:
    env: dict[str, str | None] = {"MARGIN_PERCENT_PROTECCIÓN_SOLAR": "25"}
    assert resolve_margin("Protección Solar", env) == 25


def test_resolve_margin_rejects_negative() -> None:
    with pytest.raises(ValueError, match="margen inválido"):
        resolve_margin("Antiage", {"MARGIN_PERCENT_ANTIAGE": "-5"})


def test_resolve_margin_rejects_non_numeric() -> None:
    with pytest.raises(ValueError, match="margen inválido"):
        resolve_margin("Antiage", {"MARGIN_PERCENT_ANTIAGE": "abc"})


def test_compute_sale_price_rounds_half_up_like_js_math_round() -> None:
    # 1 * 2.5 = 2.5 exactly (no float imprecision). JS Math.round(2.5) == 3;
    # Python's builtin round(2.5) == 2 (banker's rounding rounds to even).
    assert compute_sale_price(1, 150) == 3


@pytest.mark.parametrize(
    ("costo", "margin", "expected"),
    [(1000, 20, 1200), (28000, 20, 33600), (0, 20, 0)],
)
def test_compute_sale_price(costo: float, margin: float, expected: int) -> None:
    assert compute_sale_price(costo, margin) == expected


def _row(**overrides: object) -> CostRow:
    base = {
        "codigo": "545300004",
        "nombre": "Esmalte semipermanente",
        "categoria": "Uñas",
        "presentacion": "15ml",
        "descripcion": "",
        "precio_costo": 1000.0,
        "en_oferta": False,
        "tags": [],
        "imagen": "/img/laca/545300004.svg",
    }
    base.update(overrides)
    return CostRow(**base)  # type: ignore[arg-type]


def test_build_public_product_without_discount() -> None:
    product = build_public_product(_row(), margin=20)
    assert product.precio_venta == 1200
    assert product.precio_regular is None
    assert product.descuento_pct is None


def test_build_public_product_with_discount() -> None:
    product = build_public_product(_row(), margin=20, descuento_pct=10)
    assert product.precio_regular == 1200
    assert product.descuento_pct == 10
    assert product.precio_venta == 1080  # round(1200 * 0.9)


def test_build_public_product_zero_discount_is_no_discount() -> None:
    product = build_public_product(_row(), margin=20, descuento_pct=0)
    assert product.precio_regular is None
    assert product.precio_venta == 1200


def test_to_products_json_sorts_by_id_and_ends_with_newline() -> None:
    p1 = build_public_product(_row(codigo="002"), margin=20)
    p2 = build_public_product(_row(codigo="001"), margin=20)
    out = to_products_json([p1, p2])
    assert out.endswith("\n")
    assert out.index('"001"') < out.index('"002"')
