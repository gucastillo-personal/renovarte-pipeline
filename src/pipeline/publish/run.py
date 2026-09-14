"""Orquestación de la Fase 3: `products.json` generado -> PR contra
renovarte-catalogo. Nunca push directo a `main`; sin token o en dry-run
deja la rama lista en el checkout local pero no la pushea ni abre PR.
"""

from dataclasses import dataclass
from pathlib import Path

from pipeline.publish.git_ops import prepare_branch, push_branch
from pipeline.publish.github_api import open_pull_request
from pipeline.publish.leak_check import check_file_for_leaks

DEFAULT_REPO = "gucastillo-personal/renovarte-catalogo"
DEFAULT_BRANCH = "pipeline/auto-update-products"
DEFAULT_BASE_BRANCH = "main"
DEST_REL_PATH = Path("public") / "data" / "products.json"


@dataclass
class PublishResult:
    opened_pr_url: str | None
    has_changes: bool
    message: str


def run_publish(
    products_json_path: str | Path,
    catalogo_path: str | Path,
    repo: str = DEFAULT_REPO,
    branch_name: str = DEFAULT_BRANCH,
    base_branch: str = DEFAULT_BASE_BRANCH,
    github_token: str | None = None,
    dry_run: bool = True,
) -> PublishResult:
    products_json_path = Path(products_json_path)
    catalogo_path = Path(catalogo_path)

    hits = check_file_for_leaks(products_json_path)
    if hits:
        joined = "; ".join(f"{h.token!r}" for h in hits)
        raise ValueError(
            f"leak-check FALLÓ ({joined}) — no se toca renovarte-catalogo. "
            "Costo/margen no puede llegar a un archivo público (constitution §I)."
        )

    commit_message = "chore(data): actualizar products.json (renovarte-pipeline)"
    prepared = prepare_branch(
        catalogo_path,
        branch_name,
        base_branch,
        {DEST_REL_PATH: products_json_path},
        commit_message,
    )

    if not prepared.has_changes:
        return PublishResult(
            opened_pr_url=None,
            has_changes=False,
            message="Sin cambios — products.json ya está al día, no se abre PR.",
        )

    if dry_run or not github_token:
        return PublishResult(
            opened_pr_url=None,
            has_changes=True,
            message=(
                f"[dry-run] rama '{branch_name}' lista con cambios en {catalogo_path}, "
                f"no se pusheó ni se abrió PR:\n{prepared.diff_summary}"
            ),
        )

    push_branch(catalogo_path, branch_name)
    pr_url = open_pull_request(
        repo=repo,
        token=github_token,
        head_branch=branch_name,
        base_branch=base_branch,
        title="Actualizar catálogo (products.json)",
        body=(
            "PR automático de `renovarte-pipeline` — leak-check OK "
            "(sin costo/margen/precio de lista). Revisar y mergear a mano; "
            "nunca auto-merge."
        ),
    )
    return PublishResult(opened_pr_url=pr_url, has_changes=True, message=f"PR abierto: {pr_url}")
