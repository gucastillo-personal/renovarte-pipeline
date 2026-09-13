"""CSV source adapter (spec 0002): a local `serlaca_export.csv` -> `CostRow`
list. Kept as the offline fallback for the API source (spec 0009).
"""

import csv
import io
import re
from pathlib import Path

from pipeline.models import CostRow
from pipeline.transform.images import PLACEHOLDER_IMAGE, resolve_image_path

REQUIRED_COLUMNS = ("codigo", "nombre", "categoria", "presentacion", "descripcion", "precio_costo")
OPTIONAL_COLUMNS = ("en_oferta", "tags")

CsvRow = dict[str, str | None]

_TRUTHY = {"si", "sí", "true", "1", "x", "yes"}
_NON_NUMERIC_RE = re.compile(r"[^0-9.,-]")


def validate_columns(headers: list[str]) -> None:
    """Raise naming every missing required column, so a changed Serlaca
    export fails loud (PRD §8).
    """
    present = {h.strip() for h in headers}
    missing = [c for c in REQUIRED_COLUMNS if c not in present]
    if missing:
        raise ValueError(
            f"CSV: faltan columnas requeridas: {', '.join(missing)}. "
            f"Columnas encontradas: {', '.join(headers)}"
        )


def parse_ars_number(raw: str) -> float:
    """Parse a number that may arrive in Argentine format: "28000",
    "28.000", "28000,50", "$ 28.000,50". Raises if there is no parseable
    number.
    """
    cleaned = _NON_NUMERIC_RE.sub("", raw)
    if cleaned in ("", "-"):
        raise ValueError(f"valor numérico inválido: {raw!r}")

    last_comma = cleaned.rfind(",")
    last_dot = cleaned.rfind(".")

    if last_comma != -1 and last_dot != -1:
        normalized = (
            cleaned.replace(".", "").replace(",", ".")
            if last_comma > last_dot
            else cleaned.replace(",", "")
        )
    elif last_comma != -1:
        decimals = len(cleaned) - last_comma - 1
        normalized = (
            cleaned.replace(",", ".")
            if cleaned.index(",") == last_comma and decimals != 3
            else cleaned.replace(",", "")
        )
    elif last_dot != -1:
        decimals = len(cleaned) - last_dot - 1
        normalized = cleaned if cleaned.index(".") == last_dot and decimals != 3 else cleaned.replace(".", "")
    else:
        normalized = cleaned

    try:
        return float(normalized)
    except ValueError as error:
        raise ValueError(f"valor numérico inválido: {raw!r}") from error


def parse_boolean(raw: str | None) -> bool:
    """Absent / empty / "no" / "false" / "0" -> False."""
    return (raw or "").strip().lower() in _TRUTHY


def parse_tags(raw: str | None) -> list[str]:
    """Split on "|" or ",", trim, drop empties. Absent -> []."""
    return [t.strip() for t in re.split(r"[|,]", raw or "") if t.strip()]


def _require_field(row: CsvRow, key: str) -> str:
    value = row.get(key)
    if value is None or value.strip() == "":
        raise ValueError(f'campo "{key}" vacío')
    return value.strip()


def read_csv_cost_rows(csv_path: str | Path, public_dir: str | Path) -> tuple[list[CostRow], list[str]]:
    """Read a Serlaca cost CSV into `CostRow`s.

    Aborts (raising, writing nothing) if a required column is missing or
    any row fails to parse; the error names every bad row by its 1-based
    line number.
    """
    text = Path(csv_path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError(f"CSV sin filas de datos: {csv_path}")
    validate_columns([h.strip() for h in reader.fieldnames])

    records = [
        {(k.strip() if k else k): (v.strip() if v is not None else v) for k, v in r.items()}
        for r in reader
        if any((v or "").strip() for v in r.values())  # skip_empty_lines
    ]
    if not records:
        raise ValueError(f"CSV sin filas de datos: {csv_path}")

    warnings: list[str] = []
    errors: list[str] = []
    rows: list[CostRow] = []

    for index, row in enumerate(records):
        line = index + 2  # header is line 1
        try:
            codigo = _require_field(row, "codigo")
            imagen = resolve_image_path(codigo, public_dir)
            if imagen == PLACEHOLDER_IMAGE:
                warnings.append(f"línea {line} ({codigo}): sin imagen, se usó el placeholder")
            rows.append(
                CostRow(
                    codigo=codigo,
                    nombre=_require_field(row, "nombre"),
                    categoria=_require_field(row, "categoria"),
                    presentacion=_require_field(row, "presentacion"),
                    descripcion=_require_field(row, "descripcion"),
                    precio_costo=parse_ars_number(_require_field(row, "precio_costo")),
                    en_oferta=parse_boolean(row.get("en_oferta")),
                    tags=parse_tags(row.get("tags")),
                    imagen=imagen,
                )
            )
        except Exception as error:
            errors.append(f"línea {line}: {error}")

    if errors:
        joined = "\n  ".join(errors)
        raise ValueError(f"ingesta abortada ({len(errors)} error(es)):\n  {joined}")

    return rows, warnings
