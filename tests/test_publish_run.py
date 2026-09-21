import json
import subprocess
from pathlib import Path

import pytest

from pipeline.models import Product
from pipeline.publish.run import DEFAULT_CATEGORY_GROUPS_PATH, run_publish


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def catalogo_clone(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(["init", "--bare", "-b", "main"], origin)

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(["init", "-b", "main"], seed)
    _git(["config", "user.email", "test@example.com"], seed)
    _git(["config", "user.name", "Test"], seed)
    (seed / "public" / "data").mkdir(parents=True)
    (seed / "public" / "data" / "products.json").write_text("[]\n", encoding="utf-8")
    # Seed the same content `run_publish` would find at its real default
    # `category_groups_path` (spec 0001, plan.md §6bis) — so tests that
    # exercise the "nothing changed" path stay meaningful now that
    # `data/reference/serlaca_category_groups.json` is a real committed
    # file, not a hypothetical one.
    (seed / "public" / "data" / "serlaca_category_groups.json").write_bytes(
        DEFAULT_CATEGORY_GROUPS_PATH.read_bytes()
    )
    _git(["add", "."], seed)
    _git(["commit", "-m", "seed"], seed)
    _git(["remote", "add", "origin", str(origin)], seed)
    _git(["push", "origin", "main"], seed)

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(origin), str(clone)], check=True, capture_output=True, text=True)
    # No identity configured here either — run_publish must work on a
    # bare-fresh checkout like CI's, same as tested in test_git_ops.py.
    return clone


def test_leak_check_blocks_publish_before_touching_the_repo(tmp_path: Path, catalogo_clone: Path) -> None:
    leaking = tmp_path / "products.json"
    leaking.write_text('{"precio_costo": 1000}', encoding="utf-8")

    with pytest.raises(ValueError, match="leak-check"):
        run_publish(products_json_path=leaking, catalogo_path=catalogo_clone, dry_run=True)

    # main must be untouched — no branch, no commit attempted.
    result = subprocess.run(["git", "branch"], cwd=catalogo_clone, capture_output=True, text=True, check=True)
    assert "pipeline/auto-update-products" not in result.stdout


def test_dry_run_prepares_branch_but_never_pushes_or_calls_github(tmp_path: Path, catalogo_clone: Path) -> None:
    clean = tmp_path / "products.json"
    clean.write_text('[{"id": "1"}]\n', encoding="utf-8")

    result = run_publish(products_json_path=clean, catalogo_path=catalogo_clone, dry_run=True, github_token="unused")

    assert result.has_changes is True
    assert result.opened_pr_url is None
    assert "dry-run" in result.message
    committed = (catalogo_clone / "public" / "data" / "products.json").read_text(encoding="utf-8")
    assert committed == '[{"id": "1"}]\n'  # committed locally...
    branches = subprocess.run(["git", "branch"], cwd=catalogo_clone, capture_output=True, text=True, check=True)
    assert "* pipeline/auto-update-products" in branches.stdout


def test_no_changes_reports_and_skips_everything(tmp_path: Path, catalogo_clone: Path) -> None:
    same = tmp_path / "products.json"
    same.write_text("[]\n", encoding="utf-8")  # identical to seeded content

    result = run_publish(
        products_json_path=same,
        catalogo_path=catalogo_clone,
        dry_run=True,
        price_diff_path=tmp_path / "unused-price-changes.json",
    )

    assert result.has_changes is False
    assert result.opened_pr_url is None


def test_live_run_pushes_and_opens_pr(tmp_path: Path, catalogo_clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clean = tmp_path / "products.json"
    clean.write_text('[{"id": "1"}]\n', encoding="utf-8")

    calls: list[str] = []

    def fake_open_pull_request(**kwargs: object) -> str:
        calls.append("opened")
        return "https://github.com/o/r/pull/1"

    monkeypatch.setattr("pipeline.publish.run.open_pull_request", fake_open_pull_request)

    result = run_publish(
        products_json_path=clean,
        catalogo_path=catalogo_clone,
        github_token="real-token",
        dry_run=False,
    )

    assert calls == ["opened"]
    assert result.opened_pr_url == "https://github.com/o/r/pull/1"
    origin = tmp_path / "origin.git"
    pushed = subprocess.run(["git", "branch"], cwd=origin, capture_output=True, text=True, check=True)
    assert "pipeline/auto-update-products" in pushed.stdout


def test_without_token_falls_back_to_dry_run_even_if_dry_run_false(
    tmp_path: Path, catalogo_clone: Path
) -> None:
    clean = tmp_path / "products.json"
    clean.write_text('[{"id": "1"}]\n', encoding="utf-8")

    result = run_publish(products_json_path=clean, catalogo_path=catalogo_clone, github_token=None, dry_run=False)

    assert result.opened_pr_url is None
    assert "dry-run" in result.message


def _product(id: str, precio_venta: int, nombre: str = "Producto") -> Product:
    return Product(
        id=id,
        proveedor="LACA",
        categoria="Uñas",
        codCategoria=["2"],
        nombre=nombre,
        presentacion="15ml",
        descripcion="",
        precio_venta=precio_venta,
        imagen="/img/laca/x.svg",
        en_oferta=False,
        tags=[],
    )


def test_writes_price_diff_file_when_prices_change(tmp_path: Path, catalogo_clone: Path) -> None:
    # compute_price_diff lee el products.json ya publicado directo del disco,
    # antes de que prepare_branch lo pise — no hace falta commitear esto.
    (catalogo_clone / "public" / "data" / "products.json").write_text(
        json.dumps([_product("1", 1000, "Esmalte").to_public_dict()]), encoding="utf-8"
    )
    new_path = tmp_path / "products.json"
    new_path.write_text(json.dumps([_product("1", 1200, "Esmalte").to_public_dict()]), encoding="utf-8")
    price_diff_path = tmp_path / "price-changes.json"

    run_publish(
        products_json_path=new_path,
        catalogo_path=catalogo_clone,
        dry_run=True,
        price_diff_path=price_diff_path,
    )

    payload = json.loads(price_diff_path.read_text(encoding="utf-8"))
    assert payload["changes"] == [
        {"kind": "price_up", "id": "1", "nombre": "Esmalte", "old_price": 1000, "new_price": 1200}
    ]


def test_price_diff_failure_never_blocks_the_real_publish(tmp_path: Path, catalogo_clone: Path) -> None:
    clean = tmp_path / "products.json"
    clean.write_text('[{"id": "1"}]\n', encoding="utf-8")  # no cumple el schema de Product
    price_diff_path = tmp_path / "price-changes.json"

    result = run_publish(
        products_json_path=clean,
        catalogo_path=catalogo_clone,
        dry_run=True,
        price_diff_path=price_diff_path,
    )

    assert result.has_changes is True  # el publish real sigue andando...
    assert not price_diff_path.exists()  # ...aunque el price-diff no se haya podido generar


# --- spec 0001, plan.md §6bis: publish distribuye también el mapeo (A) ------


def test_category_groups_file_gets_copied_alongside_products_json(
    tmp_path: Path, catalogo_clone: Path
) -> None:
    clean = tmp_path / "products.json"
    clean.write_text('[{"id": "1"}]\n', encoding="utf-8")
    groups = tmp_path / "serlaca_category_groups.json"
    groups.write_text('{"1": "Cuidado facial", "2": "Cuidado corporal"}', encoding="utf-8")

    result = run_publish(
        products_json_path=clean,
        catalogo_path=catalogo_clone,
        dry_run=True,
        category_groups_path=groups,
    )

    assert result.has_changes is True
    committed = (catalogo_clone / "public" / "data" / "serlaca_category_groups.json").read_text(encoding="utf-8")
    assert committed == '{"1": "Cuidado facial", "2": "Cuidado corporal"}'


def test_missing_category_groups_file_degrades_gracefully(tmp_path: Path, catalogo_clone: Path) -> None:
    """Un `category_groups_path` inexistente no rompe el publish real de
    `products.json` — mismo criterio de degradación que `load_pdf_prices()`.
    El seed de `catalogo_clone` ya trae su propio
    `serlaca_category_groups.json` (commit previo) — sin un
    `category_groups_path` real para copiar, ese archivo queda tal cual
    estaba, no se toca.
    """
    clean = tmp_path / "products.json"
    clean.write_text('[{"id": "1"}]\n', encoding="utf-8")
    dest = catalogo_clone / "public" / "data" / "serlaca_category_groups.json"
    before = dest.read_text(encoding="utf-8")

    result = run_publish(
        products_json_path=clean,
        catalogo_path=catalogo_clone,
        dry_run=True,
        category_groups_path=tmp_path / "no-existe.json",
    )

    assert result.has_changes is True  # products.json sí cambió
    assert dest.read_text(encoding="utf-8") == before  # el mapeo no se tocó


def test_leaking_category_groups_file_blocks_publish_before_touching_the_repo(
    tmp_path: Path, catalogo_clone: Path
) -> None:
    clean = tmp_path / "products.json"
    clean.write_text('[{"id": "1"}]\n', encoding="utf-8")
    leaking_groups = tmp_path / "serlaca_category_groups.json"
    leaking_groups.write_text('{"1": "precio_costo interno"}', encoding="utf-8")

    with pytest.raises(ValueError, match="leak-check"):
        run_publish(
            products_json_path=clean,
            catalogo_path=catalogo_clone,
            dry_run=True,
            category_groups_path=leaking_groups,
        )

    result = subprocess.run(["git", "branch"], cwd=catalogo_clone, capture_output=True, text=True, check=True)
    assert "pipeline/auto-update-products" not in result.stdout
