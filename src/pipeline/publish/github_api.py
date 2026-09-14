"""Apertura del PR contra renovarte-catalogo vía la API de GitHub.

Nunca hace merge — solo abre (o reutiliza) el PR. El merge queda a
revisión humana (PLAN.md, spec 0010).
"""

import httpx

_API_BASE = "https://api.github.com"


class GitHubApiError(RuntimeError):
    pass


def open_pull_request(
    repo: str,
    token: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
    client: httpx.Client | None = None,
) -> str:
    """Abre un PR `head_branch` -> `base_branch` en `repo` ("owner/name").
    Si ya hay un PR abierto para esa `head_branch`, devuelve su URL en vez
    de abrir uno duplicado. Devuelve la URL del PR (nuevo o existente).
    """
    owner = repo.split("/", 1)[0]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    owns_client = client is None
    http = client or httpx.Client(base_url=_API_BASE, timeout=15.0)
    try:
        params = {"head": f"{owner}:{head_branch}", "state": "open"}
        existing = http.get(f"/repos/{repo}/pulls", headers=headers, params=params)
        if existing.status_code >= 400:
            raise GitHubApiError(f"GitHub respondió {existing.status_code} listando PRs: {existing.text}")
        existing_prs = existing.json()
        if existing_prs:
            return str(existing_prs[0]["html_url"])

        created = http.post(
            f"/repos/{repo}/pulls",
            headers=headers,
            json={"title": title, "head": head_branch, "base": base_branch, "body": body},
        )
        if created.status_code >= 400:
            raise GitHubApiError(f"GitHub respondió {created.status_code} abriendo el PR: {created.text}")
        return str(created.json()["html_url"])
    finally:
        if owns_client:
            http.close()
