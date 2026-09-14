"""Ejercita prepare_branch/push_branch contra un repo git real y descartable
(un "origin" bare local + un clon) — sin red, sin tocar GitHub.
"""

import base64
import subprocess
from pathlib import Path

import pytest

from pipeline.publish.git_ops import BOT_EMAIL, BOT_NAME, GitError, prepare_branch, push_branch


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def origin_and_clone(tmp_path: Path) -> tuple[Path, Path]:
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(["init", "--bare", "-b", "main"], origin)

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(["init", "-b", "main"], seed)
    _git(["config", "user.email", "test@example.com"], seed)
    _git(["config", "user.name", "Test"], seed)
    (seed / "public").mkdir()
    (seed / "public" / "data").mkdir()
    (seed / "public" / "data" / "products.json").write_text("[]\n", encoding="utf-8")
    _git(["add", "."], seed)
    _git(["commit", "-m", "seed"], seed)
    _git(["remote", "add", "origin", str(origin)], seed)
    _git(["push", "origin", "main"], seed)

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(origin), str(clone)], check=True, capture_output=True, text=True)
    # Deliberately no `git config user.name/email` here — a fresh
    # `actions/checkout` in CI has none either. prepare_branch must set its
    # own local identity, not rely on one already being there.
    return origin, clone


def test_prepare_branch_commits_when_content_changes(tmp_path: Path, origin_and_clone: tuple[Path, Path]) -> None:
    _origin, clone = origin_and_clone
    new_products = tmp_path / "new_products.json"
    new_products.write_text('[{"id": "1"}]\n', encoding="utf-8")

    result = prepare_branch(
        clone,
        branch_name="pipeline/auto-update-products",
        base_branch="main",
        files_to_update={Path("public/data/products.json"): new_products},
        commit_message="chore: update",
    )

    assert result.has_changes is True
    assert result.branch == "pipeline/auto-update-products"
    assert "products.json" in result.diff_summary
    committed = (clone / "public" / "data" / "products.json").read_text(encoding="utf-8")
    assert committed == '[{"id": "1"}]\n'


def test_prepare_branch_sets_its_own_identity_without_any_ambient_config(
    tmp_path: Path, origin_and_clone: tuple[Path, Path]
) -> None:
    """Regression: a fresh `actions/checkout` in CI has no git identity at
    all — `git commit` fails outright ("Author identity unknown") without
    one. prepare_branch must never depend on the environment already having
    one configured.
    """
    _origin, clone = origin_and_clone
    new_products = tmp_path / "new_products.json"
    new_products.write_text('[{"id": "1"}]\n', encoding="utf-8")

    prepare_branch(
        clone,
        branch_name="pipeline/auto-update-products",
        base_branch="main",
        files_to_update={Path("public/data/products.json"): new_products},
        commit_message="chore: update",
    )

    name = subprocess.run(
        ["git", "config", "user.name"], cwd=clone, capture_output=True, text=True, check=True
    ).stdout.strip()
    email = subprocess.run(
        ["git", "config", "user.email"], cwd=clone, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert name == BOT_NAME
    assert email == BOT_EMAIL
    author = subprocess.run(
        ["git", "log", "-1", "--format=%an <%ae>"], cwd=clone, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert author == f"{BOT_NAME} <{BOT_EMAIL}>"


def test_prepare_branch_no_changes_when_content_identical(tmp_path: Path, origin_and_clone: tuple[Path, Path]) -> None:
    _origin, clone = origin_and_clone
    same_products = tmp_path / "same_products.json"
    same_products.write_text("[]\n", encoding="utf-8")  # matches the seeded content exactly

    result = prepare_branch(
        clone,
        branch_name="pipeline/auto-update-products",
        base_branch="main",
        files_to_update={Path("public/data/products.json"): same_products},
        commit_message="chore: update",
    )

    assert result.has_changes is False
    assert result.diff_summary == ""


def test_prepare_branch_resets_stale_local_branch(tmp_path: Path, origin_and_clone: tuple[Path, Path]) -> None:
    """A leftover bot branch from a previous run must not accumulate commits
    — each run starts fresh off base_branch.
    """
    _origin, clone = origin_and_clone
    _git(["checkout", "-b", "pipeline/auto-update-products"], clone)
    (clone / "stray.txt").write_text("leftover from a previous run\n", encoding="utf-8")
    _git(["add", "stray.txt"], clone)
    _git(["commit", "-m", "stale commit"], clone)
    _git(["checkout", "main"], clone)

    new_products = tmp_path / "new_products.json"
    new_products.write_text('[{"id": "1"}]\n', encoding="utf-8")
    prepare_branch(
        clone,
        branch_name="pipeline/auto-update-products",
        base_branch="main",
        files_to_update={Path("public/data/products.json"): new_products},
        commit_message="chore: update",
    )

    assert not (clone / "stray.txt").exists()


def test_push_branch_reaches_origin(tmp_path: Path, origin_and_clone: tuple[Path, Path]) -> None:
    origin, clone = origin_and_clone
    new_products = tmp_path / "new_products.json"
    new_products.write_text('[{"id": "1"}]\n', encoding="utf-8")
    prepare_branch(
        clone,
        branch_name="pipeline/auto-update-products",
        base_branch="main",
        files_to_update={Path("public/data/products.json"): new_products},
        commit_message="chore: update",
    )

    push_branch(clone, "pipeline/auto-update-products")

    # The bare origin IS the remote — its own branch list shows what got pushed.
    result = subprocess.run(["git", "branch"], cwd=origin, capture_output=True, text=True, check=True)
    assert "pipeline/auto-update-products" in result.stdout


def test_push_branch_with_token_still_reaches_local_origin(
    tmp_path: Path, origin_and_clone: tuple[Path, Path]
) -> None:
    """`http.extraheader` only matters for HTTP(S) remotes — passing a token
    against this filesystem-path origin must be a harmless no-op, not break
    the push.
    """
    origin, clone = origin_and_clone
    new_products = tmp_path / "new_products.json"
    new_products.write_text('[{"id": "1"}]\n', encoding="utf-8")
    prepare_branch(
        clone,
        branch_name="pipeline/auto-update-products",
        base_branch="main",
        files_to_update={Path("public/data/products.json"): new_products},
        commit_message="chore: update",
    )

    push_branch(clone, "pipeline/auto-update-products", token="fake-token")

    result = subprocess.run(["git", "branch"], cwd=origin, capture_output=True, text=True, check=True)
    assert "pipeline/auto-update-products" in result.stdout


def test_push_branch_with_token_sets_basic_auth_extraheader(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: a real GitHub Actions run failed with a 403 pushing to
    renovarte-catalogo — push_branch relied entirely on whatever credential
    a *previous, separate* `actions/checkout` step happened to leave
    configured, which is fragile once a job checks out two repos with two
    different tokens. The token must be applied explicitly, per push call.
    """
    captured: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("pipeline.publish.git_ops.subprocess.run", fake_run)

    push_branch(Path("/fake/repo"), "pipeline/auto-update-products", token="my-token")

    assert len(captured) == 1
    args = captured[0]
    assert args[0] == "git"
    assert args[1] == "-c"
    expected_b64 = base64.b64encode(b"x-access-token:my-token").decode()
    assert args[2] == f"http.extraheader=AUTHORIZATION: basic {expected_b64}"
    assert args[3:] == ["push", "origin", "pipeline/auto-update-products", "--force"]


def test_git_error_message_includes_stderr(tmp_path: Path) -> None:
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    with pytest.raises(GitError, match="git"):
        prepare_branch(
            not_a_repo,
            branch_name="x",
            base_branch="main",
            files_to_update={},
            commit_message="x",
        )
