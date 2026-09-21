import json
from pathlib import Path

from pipeline.models import Product
from pipeline.publish.price_diff import ProductChange, compute_price_diff, write_price_diff


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


def _write_products(path: Path, products: list[Product]) -> None:
    path.write_text(json.dumps([p.to_public_dict() for p in products]), encoding="utf-8")


def test_compute_price_diff_detects_added_removed_and_price_changes(tmp_path: Path) -> None:
    old_path = tmp_path / "old.json"
    new_path = tmp_path / "new.json"
    _write_products(
        old_path,
        [
            _product("1", 100, "Sube"),
            _product("2", 200, "Baja"),
            _product("3", 300, "Se elimina"),
        ],
    )
    _write_products(
        new_path,
        [
            _product("1", 120, "Sube"),
            _product("2", 150, "Baja"),
            _product("4", 400, "Nuevo"),
        ],
    )

    changes = compute_price_diff(old_path, new_path)
    by_id = {change.id: change for change in changes}

    assert len(changes) == 4
    assert by_id["1"].kind == "price_up"
    assert (by_id["1"].old_price, by_id["1"].new_price) == (100, 120)
    assert by_id["2"].kind == "price_down"
    assert (by_id["2"].old_price, by_id["2"].new_price) == (200, 150)
    assert by_id["3"].kind == "removed"
    assert by_id["3"].new_price is None
    assert by_id["4"].kind == "added"
    assert by_id["4"].old_price is None


def test_compute_price_diff_ignores_unchanged_products(tmp_path: Path) -> None:
    old_path = tmp_path / "old.json"
    new_path = tmp_path / "new.json"
    products = [_product("1", 100)]
    _write_products(old_path, products)
    _write_products(new_path, products)

    assert compute_price_diff(old_path, new_path) == []


def test_compute_price_diff_treats_missing_old_file_as_empty_catalog(tmp_path: Path) -> None:
    old_path = tmp_path / "does-not-exist.json"
    new_path = tmp_path / "new.json"
    _write_products(new_path, [_product("1", 100)])

    changes = compute_price_diff(old_path, new_path)

    assert len(changes) == 1
    assert changes[0].kind == "added"


def test_write_price_diff_writes_expected_contract(tmp_path: Path) -> None:
    out_path = tmp_path / "out" / "price-changes.json"
    changes = [ProductChange(kind="added", id="1", nombre="A", old_price=None, new_price=100)]

    write_price_diff(changes, out_path)

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert "generated_at" in payload
    assert payload["changes"] == [{"kind": "added", "id": "1", "nombre": "A", "old_price": None, "new_price": 100}]
