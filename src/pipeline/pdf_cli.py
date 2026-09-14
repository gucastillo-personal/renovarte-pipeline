"""`renovarte-pipeline pdf <subcommand>` — spec 0008.

Tres pasos separados porque el PDF de LACA se baja y procesa a mano (fuera
de scope automatizarlo — spec 0008 "Out"):

    pdf extract   PDF -> crudo gitignored + data/reference/laca_pdf_precios.csv
    pdf review    crudo + catálogo -> reporte HTML local para decidir
    pdf apply-decisions   JSON descargado del reporte -> data/reference/precio_pdf_decisiones.json
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_RAW_PATH = Path("data") / "private" / "laca_pdf_raw.json"
DEFAULT_REFERENCE_CSV = Path("data") / "reference" / "laca_pdf_precios.csv"
DEFAULT_REVIEW_HTML = Path("data") / "private" / "pdf_review.html"
DEFAULT_DECISIONS_PATH = Path("data") / "reference" / "precio_pdf_decisiones.json"


def cmd_pdf_extract(args: argparse.Namespace) -> int:
    from dataclasses import asdict

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
    print(f"✓ {len(result.rows)} fila(s) extraída(s) del PDF")
    print(f"  crudo (gitignored, con costo): {raw_path}")
    print(f"  referencia pública (committed): {args.reference_out}")
    return 0


def cmd_pdf_review(args: argparse.Namespace) -> int:
    from pipeline.models import validate_products
    from pipeline.sources.pdf_laca import extract_raw
    from pipeline.transform.pdf_decisions import load_decisions
    from pipeline.transform.pdf_match import match_pdf_to_catalog
    from pipeline.transform.pdf_review import write_review_html

    try:
        extracted = extract_raw(args.pdf)
        catalog_raw = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        products = validate_products(catalog_raw)
        match = match_pdf_to_catalog(extracted.rows, products)
        existing = load_decisions(args.decisions)
        out = write_review_html(match, args.fuente, args.out, existing)
    except Exception as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1

    for warning in extracted.warnings:
        print(f"⚠  {warning}")
    print(f"✓ {len(match.matched)} producto(s) matcheado(s) → {out}")
    if match.catalogo_sin_pdf:
        print(f"  {len(match.catalogo_sin_pdf)} sin dato de PDF")
    if match.pdf_sin_match:
        print(f"  {len(match.pdf_sin_match)} fila(s) del PDF sin match en el catálogo")
    print("  Abrí ese archivo en el navegador para revisar y descargar las decisiones.")
    return 0


def cmd_pdf_apply_decisions(args: argparse.Namespace) -> int:
    from pipeline.transform.pdf_decisions import load_decisions, save_decisions

    try:
        file_path = Path(args.file).expanduser()
        if not file_path.is_file():
            # load_decisions() treats "missing" as "no decisions yet" — correct
            # for the *default* decisions path, but wrong here: this argument
            # names a specific file the caller expects to exist (typically just
            # downloaded from the review report). Silently proceeding with {}
            # would overwrite a real decisions.json with an empty one on a typo.
            raise FileNotFoundError(f"no existe: {file_path}")
        decisions = load_decisions(file_path)
        save_decisions(args.out, decisions)
    except Exception as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1

    print(f"✓ {len(decisions)} decisión(es) aplicada(s) → {args.out}")
    return 0


def add_pdf_subcommands(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    pdf_parser = subparsers.add_parser("pdf", help="Precio desde el PDF de LACA (spec 0008).")
    pdf_subparsers = pdf_parser.add_subparsers(dest="pdf_command", required=True)

    extract = pdf_subparsers.add_parser("extract", help="PDF -> crudo + data/reference/laca_pdf_precios.csv.")
    extract.add_argument("--pdf", required=True, help="Ruta al PDF de precios de LACA.")
    extract.add_argument("--fuente", required=True, help='Etiqueta de origen, ej. "LACA 2026-09".')
    extract.add_argument("--raw-out", default=str(DEFAULT_RAW_PATH))
    extract.add_argument("--reference-out", default=str(DEFAULT_REFERENCE_CSV))
    extract.set_defaults(func=cmd_pdf_extract)

    review = pdf_subparsers.add_parser("review", help="Genera el reporte HTML de revisión.")
    review.add_argument("--pdf", required=True, help="Ruta al PDF de precios de LACA.")
    review.add_argument("--fuente", required=True)
    review.add_argument("--catalog", required=True, help="Ruta a products.json ya transformado.")
    review.add_argument("--decisions", default=str(DEFAULT_DECISIONS_PATH))
    review.add_argument("--out", default=str(DEFAULT_REVIEW_HTML))
    review.set_defaults(func=cmd_pdf_review)

    apply_decisions = pdf_subparsers.add_parser(
        "apply-decisions", help="Valida y aplica el JSON descargado del reporte de revisión."
    )
    apply_decisions.add_argument("file", help="precio_pdf_decisiones.json descargado del reporte.")
    apply_decisions.add_argument("--out", default=str(DEFAULT_DECISIONS_PATH))
    apply_decisions.set_defaults(func=cmd_pdf_apply_decisions)
