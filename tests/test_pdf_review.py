from pipeline.models import Product
from pipeline.transform.pdf_decisions import PdfDecision
from pipeline.transform.pdf_match import MatchedProduct, MatchResult
from pipeline.transform.pdf_review import render_review_html


def test_render_review_html_embeds_matched_rows_and_counts() -> None:
    match = MatchResult(
        matched=[
            MatchedProduct(
                codigo="001",
                nombre='Producto <raro> & "especial"',
                precio_venta_actual=1200,
                precio_profesional=1000,
                precio_abc=1300,
                precio_catalogo=1500,
                margen_abc_pct=30.0,
                margen_catalogo_pct=50.0,
            )
        ],
        catalogo_sin_pdf=[],
        pdf_sin_match=[],
    )
    html = render_review_html(match, fuente="LACA 2026-09", existing_decisions={"999": PdfDecision("actual", 100)})

    assert "</script><script>" not in html  # no premature script-tag close from embedded data
    assert '"codigo": "001"' in html
    assert "LACA 2026-09" in html
    assert '"999"' in html  # existing decision carried into the payload


def test_render_review_html_no_matches_still_valid() -> None:
    html = render_review_html(MatchResult(matched=[], catalogo_sin_pdf=[], pdf_sin_match=[]), fuente="x")
    assert "<html" in html
    assert '"matched": []' in html


def test_render_review_html_lists_unmatched_both_directions() -> None:
    product = Product(
        id="002",
        proveedor="LACA",
        categoria="Antiage",
        nombre="Sin PDF",
        presentacion="1 u",
        descripcion="",
        precio_venta=500,
        imagen="/img/placeholder.svg",
        en_oferta=False,
        tags=[],
    )
    from pipeline.sources.pdf_laca import LacaPdfRow

    pdf_row = LacaPdfRow(
        codigo="003", nombre_pdf="Sin match", precio_profesional=1, precio_abc=2, precio_catalogo=3
    )
    match = MatchResult(matched=[], catalogo_sin_pdf=[product], pdf_sin_match=[pdf_row])
    html = render_review_html(match, fuente="x")
    assert '"codigo": "002"' in html
    assert '"codigo": "003"' in html
