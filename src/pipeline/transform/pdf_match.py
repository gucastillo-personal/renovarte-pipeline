"""Match entre el crudo del PDF de LACA y el catálogo ya transformado
(spec 0008, AC-2). Cruza por `codigo` (== `Product.id`); reporta ambos
sentidos de no-match, nunca descarta filas en silencio.
"""

from dataclasses import dataclass

from pipeline.models import Product
from pipeline.sources.pdf_laca import LacaPdfRow


@dataclass(frozen=True)
class MatchedProduct:
    """Un producto con fila de PDF correspondiente, listo para revisión
    (spec 0008, AC-3). `precio_profesional` se muestra solo como contexto
    (nunca es una opción de precio de venta).
    """

    codigo: str
    nombre: str
    precio_venta_actual: int
    precio_profesional: float
    precio_abc: float | None
    precio_catalogo: float | None
    margen_abc_pct: float | None
    margen_catalogo_pct: float | None


@dataclass(frozen=True)
class MatchResult:
    matched: list[MatchedProduct]
    catalogo_sin_pdf: list[Product]
    pdf_sin_match: list[LacaPdfRow]


def _implied_margin_pct(precio: float | None, precio_profesional: float) -> float | None:
    """`(precio - precio_profesional) / precio_profesional * 100`. `None`
    when `precio` is unavailable (PDF had "-") or `precio_profesional` is 0
    (division undefined, not a real product cost).
    """
    if precio is None or precio_profesional == 0:
        return None
    return (precio - precio_profesional) / precio_profesional * 100


def match_pdf_to_catalog(pdf_rows: list[LacaPdfRow], products: list[Product]) -> MatchResult:
    by_codigo = {row.codigo: row for row in pdf_rows}
    matched: list[MatchedProduct] = []
    catalogo_sin_pdf: list[Product] = []
    matched_codigos: set[str] = set()

    for product in products:
        pdf_row = by_codigo.get(product.id)
        if pdf_row is None:
            catalogo_sin_pdf.append(product)
            continue
        matched_codigos.add(pdf_row.codigo)
        matched.append(
            MatchedProduct(
                codigo=product.id,
                nombre=product.nombre,
                precio_venta_actual=product.precio_venta,
                precio_profesional=pdf_row.precio_profesional,
                precio_abc=pdf_row.precio_abc,
                precio_catalogo=pdf_row.precio_catalogo,
                margen_abc_pct=_implied_margin_pct(pdf_row.precio_abc, pdf_row.precio_profesional),
                margen_catalogo_pct=_implied_margin_pct(pdf_row.precio_catalogo, pdf_row.precio_profesional),
            )
        )

    pdf_sin_match = [row for row in pdf_rows if row.codigo not in matched_codigos]
    return MatchResult(matched=matched, catalogo_sin_pdf=catalogo_sin_pdf, pdf_sin_match=pdf_sin_match)
