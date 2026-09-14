"""Derivación pública desde el crudo del PDF de LACA (spec 0008).

`to_public_reference` descarta `precio_profesional` (costo) — el resultado
es información pública (precios sugeridos/de catálogo de LACA) y se
commitea en `data/reference/laca_pdf_precios.csv`, a diferencia del crudo
completo (gitignored).
"""

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from pipeline.sources.pdf_laca import LacaPdfRow

REFERENCE_CSV_COLUMNS = ("codigo", "nombre_pdf", "precio_abc", "precio_catalogo", "fuente")


@dataclass(frozen=True)
class LacaPdfPublicRow:
    codigo: str
    nombre_pdf: str
    precio_abc: int | None
    precio_catalogo: int | None
    fuente: str


def to_public_reference(rows: list[LacaPdfRow], fuente: str) -> list[LacaPdfPublicRow]:
    """Strip `precio_profesional`; tag every row with `fuente` (nombre/fecha
    del PDF de origen). Prices round to whole ARS — LACA's list has no cents.
    """
    return [
        LacaPdfPublicRow(
            codigo=row.codigo,
            nombre_pdf=row.nombre_pdf,
            precio_abc=round(row.precio_abc) if row.precio_abc is not None else None,
            precio_catalogo=round(row.precio_catalogo) if row.precio_catalogo is not None else None,
            fuente=fuente,
        )
        for row in rows
    ]


def write_reference_csv(rows: list[LacaPdfPublicRow], path: str | Path) -> None:
    """Deterministic CSV, sorted by `codigo`, for `data/reference/laca_pdf_precios.csv`."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows, key=lambda r: r.codigo)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REFERENCE_CSV_COLUMNS)
        writer.writeheader()
        for row in sorted_rows:
            writer.writerow(asdict(row))
