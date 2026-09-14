"""Extracción del PDF de precios de LACA (spec 0008).

Validado contra el PDF real de LACA (lista de precios, 22 páginas). Su
estructura de tabla es más irregular que lo previsto originalmente en la
spec — de ahí `pdfplumber` en vez de reconstruir el parseo a mano (ver
RFC-0001 §4 en renovarte-catalogo):

- **No hay fila de encabezado** en la tabla extraída — las columnas son
  fijas por posición: `[celda de nombre, profesional, abc, catalogo, ptos]`.
  La columna "ptos" (puntos del programa de fidelización) se descarta.
- Precio ABC / Catálogo pueden faltar (`"-"` en el PDF) — quedan `None`.
- **Una celda de nombre puede agrupar varios códigos** (variantes/tamaños
  del mismo producto listadas una debajo de la otra dentro de la misma
  celda visual). Cuando eso pasa, la fila con la celda agrupada trae el
  precio del **primer** código, y cada código siguiente toma el precio de
  la fila **inmediatamente posterior**, que trae `None` en la celda de
  nombre (es la misma fila visual de precio, separada por pdfplumber en
  una fila de tabla propia porque la celda de nombre, más alta, ocupa
  varias filas de grilla).
- Cada bloque código+nombre puede traer basura pegada (talle/presentación
  como línea suelta, o un sufijo corto como " L"/" CP"/" A 2"): se descarta
  con una heurística de "línea ruido" — no es perfecto, pero `nombre_pdf`
  es solo apoyo visual en el reporte de revisión, no un campo de precio.
- Páginas sin ninguna fila que empiece con un código de 8-9 dígitos (ej. la
  tabla de rango de puntos, o páginas en blanco) no aportan filas — no
  hace falta detectarlas aparte.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from pipeline.sources.csv_source import parse_ars_number

_CODE_START_RE = re.compile(r"^(\d{8,9})\b\s*(.*)$")
_NOISE_LINE_RE = re.compile(r"^[A-Z]{0,3}\s*[\d.,]*$")


@dataclass(frozen=True)
class LacaPdfRow:
    """Una fila cruda del PDF. Nunca se emite completa a un archivo commiteado
    — `precio_profesional` es costo (constitution §I.1). `precio_abc`/
    `precio_catalogo` son `None` cuando el PDF trae "-" para ese producto.
    """

    codigo: str
    nombre_pdf: str
    precio_profesional: float
    precio_abc: float | None
    precio_catalogo: float | None


def _parse_price_or_none(raw: str | None) -> float | None:
    text = (raw or "").strip()
    if text in ("", "-"):
        return None
    return parse_ars_number(text)


def _join_name(lines: list[str]) -> str:
    kept = [line for line in lines if line and not _NOISE_LINE_RE.match(line)]
    if kept:
        return " ".join(kept).strip()
    # Every line looked like noise (qty/short suffix) — happens for genuinely
    # short product names too (e.g. a perfume line coded "F1", "M2"). Better
    # a short name than none: fall back to the last non-empty raw line.
    non_empty = [line for line in lines if line]
    return non_empty[-1] if non_empty else ""


def _split_name_cell(cell_text: str) -> list[tuple[str, str]]:
    """A compound name cell -> `[(codigo, nombre), ...]`, in the order they
    appear (one entry per code found, usually one, sometimes several).
    """
    blocks: list[tuple[str, str]] = []
    current_codigo: str | None = None
    name_lines: list[str] = []

    for raw_line in cell_text.split("\n"):
        line = raw_line.strip()
        match = _CODE_START_RE.match(line)
        if match:
            if current_codigo is not None:
                blocks.append((current_codigo, _join_name(name_lines)))
            current_codigo = match.group(1)
            name_lines = [match.group(2)] if match.group(2) else []
        else:
            name_lines.append(line)

    if current_codigo is not None:
        blocks.append((current_codigo, _join_name(name_lines)))
    return blocks


def parse_table(table: Sequence[Sequence[str | None]]) -> list[LacaPdfRow]:
    """Parse one already-extracted table (`page.extract_table()`'s return
    value) into `LacaPdfRow`s.

    A row whose first cell is `None` is a continuation row: it supplies the
    price for the next pending code from the previous row's grouped name
    cell. A row that yields no code at all (header/legend/blank pages) is
    silently skipped — it isn't a "bad row", it's a page this table format
    doesn't apply to.

    Most rows have 5 cells (`name, profesional, abc, catalogo, ptos`), but
    bulk/professional-pack rows have only 4 — there's no Catálogo price for
    those (`name, profesional, abc, ptos`); `ptos` (loyalty points) is
    discarded either way. A row with any other cell count can't be
    interpreted at all and is skipped.
    """
    rows: list[LacaPdfRow] = []
    pending: list[tuple[str, str]] = []

    for raw_row in table:
        name_cell = raw_row[0] if len(raw_row) > 0 else None
        if name_cell is not None:
            blocks = _split_name_cell(name_cell)
            if blocks:
                pending = blocks

        if len(raw_row) >= 5:
            profesional_cell, abc_cell, catalogo_cell = raw_row[1], raw_row[2], raw_row[3]
        elif len(raw_row) == 4:
            profesional_cell, abc_cell, catalogo_cell = raw_row[1], raw_row[2], None
        else:
            continue  # can't locate price columns in this row at all

        if not pending:
            continue
        codigo, nombre = pending.pop(0)

        profesional = _parse_price_or_none(profesional_cell)
        if profesional is None:
            continue  # no cost at all for this row — nothing to price against

        rows.append(
            LacaPdfRow(
                codigo=codigo,
                nombre_pdf=nombre,
                precio_profesional=profesional,
                precio_abc=_parse_price_or_none(abc_cell),
                precio_catalogo=_parse_price_or_none(catalogo_cell),
            )
        )

    return rows


@dataclass
class ExtractResult:
    rows: list[LacaPdfRow]
    warnings: list[str]


def extract_raw(pdf_path: str | Path) -> ExtractResult:
    """Extract every pricing row across all pages of the LACA price PDF.

    A page whose table doesn't match this format (cover, legend, points
    range) legitimately contributes zero rows — see `parse_table`. But a
    page where `pdfplumber` failed to reconstruct the grid at all (every
    row collapses to one or two cells, so there's nowhere to find a price)
    contributes zero rows for a *different*, worse reason: real pricing
    data on that page went unextracted. Those pages are named in
    `warnings` (1-based page number) instead of silently vanishing — spec
    0008 requires reporting rather than silently dropping.
    """
    rows: list[LacaPdfRow] = []
    warnings: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            table = page.extract_table()
            if not table:
                continue
            page_rows = parse_table(table)
            looks_broken = any(len(raw_row) <= 2 for raw_row in table)
            if looks_broken and not page_rows:
                warnings.append(
                    f"página {page_index + 1}: pdfplumber no reconstruyó la grilla de precios "
                    "(filas de 1-2 celdas) — puede tener productos sin extraer, revisar a mano"
                )
            rows.extend(page_rows)
    return ExtractResult(rows=rows, warnings=warnings)
