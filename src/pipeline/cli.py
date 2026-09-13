"""Command-line entry point: `uv run renovarte-pipeline <command>`.

Commands mirror the two-stage flow already proven in `renovarte-catalogo`
(`pnpm ingest` / `pnpm transform`), plus the new `publish` step that opens a
PR against `renovarte-catalogo` with a freshly generated `products.json`.
Each is a stub until Fase 1/3 of `PLAN.md` is implemented.
"""

import argparse
import sys
from collections.abc import Sequence


def cmd_ingest(_args: argparse.Namespace) -> int:
    print("ingest: not implemented yet — see PLAN.md Fase 1", file=sys.stderr)
    return 1


def cmd_transform(_args: argparse.Namespace) -> int:
    print("transform: not implemented yet — see PLAN.md Fase 1", file=sys.stderr)
    return 1


def cmd_publish(_args: argparse.Namespace) -> int:
    print("publish: not implemented yet — see PLAN.md Fase 3", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="renovarte-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "ingest", help="Etapa 1: descarga cruda desde una fuente (API/CSV/PDF)."
    ).set_defaults(func=cmd_ingest)

    subparsers.add_parser(
        "transform", help="Etapa 2: crudo -> products.json (margen, ofertas, limpieza)."
    ).set_defaults(func=cmd_transform)

    subparsers.add_parser(
        "publish", help="Abre un PR a renovarte-catalogo con el products.json generado."
    ).set_defaults(func=cmd_publish)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
