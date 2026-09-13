"""Command-line entry point: `uv run renovarte-pipeline <command>`.

Commands mirror the two-stage flow already proven in `renovarte-catalogo`
(`pnpm ingest` / `pnpm transform`), plus the new `publish` step that opens a
PR against `renovarte-catalogo` with a freshly generated `products.json`.
`publish` is a stub until Fase 3 of `PLAN.md` is implemented.
"""

import argparse
import os
import sys
from collections.abc import Sequence

from dotenv import dotenv_values


def _load_env() -> dict[str, str | None]:
    """`.env.local` wins over `.env`; both are optional. Mirrors
    `config({ path: [".env.local", ".env"] })` in the TS scripts.
    """
    env: dict[str, str | None] = dict(os.environ)
    env.update(dotenv_values(".env"))
    env.update(dotenv_values(".env.local"))
    return env


def cmd_ingest(args: argparse.Namespace) -> int:
    from pipeline.ingest.serlaca_download import DEFAULT_RAW_PATH, run

    try:
        run(_load_env(), raw_path=args.out or DEFAULT_RAW_PATH)
    except Exception as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1
    return 0


def cmd_transform(args: argparse.Namespace) -> int:
    from pipeline.transform.run import DEFAULT_IN_PATH, run

    try:
        run(_load_env(), in_path=args.in_path or DEFAULT_IN_PATH)
    except Exception as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1
    return 0


def cmd_publish(_args: argparse.Namespace) -> int:
    print("publish: not implemented yet — see PLAN.md Fase 3", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="renovarte-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest", help="Etapa 1: descarga cruda desde la API de Serlaca."
    )
    ingest_parser.add_argument("--out", default=None, help="Ruta de salida del crudo.")
    ingest_parser.set_defaults(func=cmd_ingest)

    transform_parser = subparsers.add_parser(
        "transform", help="Etapa 2: crudo -> products.json (margen, ofertas, limpieza)."
    )
    transform_parser.add_argument(
        "--in", dest="in_path", default=None, help="Crudo de entrada (.json de la API o .csv)."
    )
    transform_parser.set_defaults(func=cmd_transform)

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
