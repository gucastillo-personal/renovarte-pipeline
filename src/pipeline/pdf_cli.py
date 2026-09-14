"""`renovarte-pipeline pdf-extract` — spec 0008.

Único paso manual del precio-desde-PDF: el admin baja el PDF de LACA y
corre esto. Produce el crudo gitignored (con costo, para nadie más que este
paso) y `data/reference/laca_pdf_precios.csv` (público, committed) — que
`transform` después carga automáticamente como fuente primaria de
`precio_venta` (ver `transform/build_catalog.py`). Sin revisión manual por
producto: el precio ABC se aplica directo a todo lo que matchea.
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

DEFAULT_RAW_PATH = Path("data") / "private" / "laca_pdf_raw.json"
DEFAULT_REFERENCE_CSV = Path("data") / "reference" / "laca_pdf_precios.csv"


def cmd_pdf_extract(args: argparse.Namespace) -> int:
    from pipeline.sources.pdf_laca import extract_raw
    from pipeline.transform.pdf_reference import to_public_reference, write_reference_csv

    try:
        result = extract_raw(args.pdf)
        if not result.rows:
            raise ValueError(f"no se extrajo ninguna fila de {args.pdf} (¿el layout de tabla cambió?)")

        raw_path = Path(args.raw_out)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(
            json.dumps([asdict(r) for r in result.rows], indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        public_rows = to_public_reference(result.rows, args.fuente)
        write_reference_csv(public_rows, args.reference_out)
    except Exception as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1

    for warning in result.warnings:
        print(f"⚠  {warning}")
    con_abc = sum(1 for r in result.rows if r.precio_abc is not None)
    print(f"✓ {len(result.rows)} fila(s) extraída(s) del PDF ({con_abc} con precio ABC)")
    print(f"  crudo (gitignored, con costo): {raw_path}")
    print(f"  referencia pública (committed): {args.reference_out}")
    print("  Corré `transform` para aplicar estos precios al catálogo.")
    return 0


def add_pdf_extract_command(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    extract = subparsers.add_parser(
        "pdf-extract", help="PDF de LACA -> crudo + data/reference/laca_pdf_precios.csv (spec 0008)."
    )
    extract.add_argument("--pdf", required=True, help="Ruta al PDF de precios de LACA.")
    extract.add_argument("--fuente", required=True, help='Etiqueta de origen, ej. "LACA 2026-09".')
    extract.add_argument("--raw-out", default=str(DEFAULT_RAW_PATH))
    extract.add_argument("--reference-out", default=str(DEFAULT_REFERENCE_CSV))
    extract.set_defaults(func=cmd_pdf_extract)
