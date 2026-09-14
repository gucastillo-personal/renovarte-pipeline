"""Operaciones git locales sobre el checkout de renovarte-catalogo que va a
recibir el PR automático.

**Este módulo asume un checkout dedicado y descartable** (el que usa la
GitHub Action en CI: `actions/checkout` fresco en cada corrida) — hace
`checkout` + `reset --hard` sobre la rama base y fuerza la rama del bot.
Nunca apuntar `repo_path` al checkout de trabajo real de un humano: se
perdería cualquier cambio local no commiteado ahí.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} falló en {cwd}:\n{result.stderr.strip()}")
    return result.stdout.strip()


@dataclass
class PreparedBranch:
    branch: str
    has_changes: bool
    diff_summary: str


def prepare_branch(
    repo_path: Path,
    branch_name: str,
    base_branch: str,
    files_to_update: dict[Path, Path],
    commit_message: str,
) -> PreparedBranch:
    """Checkout `base_branch` al día con `origin`, (re)crea `branch_name` desde
    ahí, copia cada archivo de `files_to_update` (destino relativo -> origen
    absoluto) y commitea si hay cambios.

    La rama se resetea a `base_branch` en cada corrida — no acumula commits
    de corridas anteriores. Es la rama del bot: siempre parte limpia.
    """
    _run(["fetch", "origin", base_branch], repo_path)
    _run(["checkout", base_branch], repo_path)
    _run(["reset", "--hard", f"origin/{base_branch}"], repo_path)
    _run(["checkout", "-B", branch_name], repo_path)

    for dest_rel, source in files_to_update.items():
        dest = repo_path / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(source).read_bytes())
        _run(["add", str(dest_rel)], repo_path)

    diff_summary = _run(["diff", "--cached", "--stat"], repo_path)
    if not diff_summary:
        return PreparedBranch(branch=branch_name, has_changes=False, diff_summary="")

    _run(["commit", "-m", commit_message], repo_path)
    return PreparedBranch(branch=branch_name, has_changes=True, diff_summary=diff_summary)


def push_branch(repo_path: Path, branch_name: str) -> None:
    """Force-push de la rama del bot. Seguro acá porque `branch_name` es
    exclusivamente del pipeline (se resetea desde base en cada corrida) —
    nunca se usa sobre una rama de trabajo humana.
    """
    _run(["push", "origin", branch_name, "--force"], repo_path)
