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

from pipeline.pdf_cli import add_pdf_extract_command


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


def cmd_publish(args: argparse.Namespace) -> int:
    from pipeline.publish.run import DEFAULT_BASE_BRANCH, DEFAULT_BRANCH, DEFAULT_REPO, run_publish
    from pipeline.transform.run import DEFAULT_OUT_PATH

    env = _load_env()
    dry_run = not args.live
    token = env.get("GITHUB_TOKEN") if not dry_run else None
    if not dry_run and not token:
        print("✗ --live requiere GITHUB_TOKEN en el entorno (.env/.env.local)", file=sys.stderr)
        return 1

    try:
        result = run_publish(
            products_json_path=args.products_json or DEFAULT_OUT_PATH,
            catalogo_path=args.catalogo,
            repo=args.repo or DEFAULT_REPO,
            branch_name=args.branch or DEFAULT_BRANCH,
            base_branch=args.base or DEFAULT_BASE_BRANCH,
            github_token=token,
            dry_run=dry_run,
        )
    except Exception as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1

    print(("✓ " if result.opened_pr_url or not result.has_changes else "") + result.message)
    return 0


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

    publish_parser = subparsers.add_parser(
        "publish", help="Abre un PR a renovarte-catalogo con el products.json generado."
    )
    publish_parser.add_argument(
        "--catalogo", required=True, help="Checkout DEDICADO de renovarte-catalogo (nunca tu carpeta de trabajo)."
    )
    publish_parser.add_argument("--products-json", default=None, help="Default: public/data/products.json")
    publish_parser.add_argument(
        "--repo", default=None, help="owner/name. Default: gucastillo-personal/renovarte-catalogo"
    )
    publish_parser.add_argument("--branch", default=None)
    publish_parser.add_argument("--base", default=None)
    publish_parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Sin esto: dry-run (prepara la rama, no pushea ni abre PR). "
            "Con esto: pushea y abre el PR de verdad (requiere GITHUB_TOKEN)."
        ),
    )
    publish_parser.set_defaults(func=cmd_publish)

    add_pdf_extract_command(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
