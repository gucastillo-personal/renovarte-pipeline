from pipeline.models import Product
from pipeline.sources.pdf_laca import LacaPdfRow
from pipeline.transform.pdf_match import match_pdf_to_catalog


def _product(**overrides: object) -> Product:
    base = {
        "id": "001",
        "proveedor": "LACA",
        "categoria": "Antiage",
        "codCategoria": ["1"],
        "nombre": "Producto Uno",
        "presentacion": "50 g",
        "descripcion": "",
        "precio_venta": 1200,
        "imagen": "/img/placeholder.svg",
        "en_oferta": False,
        "tags": [],
    }
    base.update(overrides)
    return Product(**base)  # type: ignore[arg-type]


def _pdf_row(**overrides: object) -> LacaPdfRow:
    base = {
        "codigo": "001",
        "nombre_pdf": "Producto Uno PDF",
        "precio_profesional": 1000.0,
        "precio_abc": 1300.0,
        "precio_catalogo": 1500.0,
    }
    base.update(overrides)
    return LacaPdfRow(**base)  # type: ignore[arg-type]


def test_matches_by_codigo_and_computes_implied_margins() -> None:
    result = match_pdf_to_catalog([_pdf_row()], [_product()])
    assert len(result.matched) == 1
    matched = result.matched[0]
    assert matched.codigo == "001"
    assert matched.margen_abc_pct == 30.0  # (1300-1000)/1000*100
    assert matched.margen_catalogo_pct == 50.0
    assert result.catalogo_sin_pdf == []
    assert result.pdf_sin_match == []


def test_product_without_pdf_row_is_catalogo_sin_pdf() -> None:
    result = match_pdf_to_catalog([], [_product()])
    assert result.matched == []
    assert len(result.catalogo_sin_pdf) == 1
    assert result.catalogo_sin_pdf[0].id == "001"


def test_pdf_row_without_product_is_pdf_sin_match() -> None:
    result = match_pdf_to_catalog([_pdf_row(codigo="999")], [_product()])
    assert result.matched == []
    assert len(result.pdf_sin_match) == 1
    assert result.pdf_sin_match[0].codigo == "999"
    assert len(result.catalogo_sin_pdf) == 1


def test_no_rows_lost_in_either_direction() -> None:
    products = [_product(id="001"), _product(id="002")]
    pdf_rows = [_pdf_row(codigo="002"), _pdf_row(codigo="003")]
    result = match_pdf_to_catalog(pdf_rows, products)
    assert {p.id for p in result.catalogo_sin_pdf} == {"001"}
    assert {r.codigo for r in result.pdf_sin_match} == {"003"}
    assert {m.codigo for m in result.matched} == {"002"}


def test_implied_margin_is_none_when_precio_profesional_is_zero() -> None:
    result = match_pdf_to_catalog([_pdf_row(precio_profesional=0.0)], [_product()])
    assert result.matched[0].margen_abc_pct is None
    assert result.matched[0].margen_catalogo_pct is None
