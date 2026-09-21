"""`codCategoria` end-to-end en `build_catalog` (spec 0001, AC-2/AC-3): un
`category_groups_by_codigo` (codigo -> ids reales de Serlaca) inyectado
desde afuera, igual que ya pasa con `pdf_prices`.
"""

from pathlib import Path

from pipeline.models import CostRow
from pipeline.transform.build_catalog import build_catalog


def _row(**overrides: object) -> CostRow:
    base = {
        "codigo": "001",
        "nombre": "Producto Uno",
        "categoria": "Antiage",
        "presentacion": "50 g",
        "descripcion": "",
        "precio_costo": 1000.0,
        "en_oferta": False,
        "tags": [],
        "imagen": "/img/placeholder.svg",
    }
    base.update(overrides)
    return CostRow(**base)  # type: ignore[arg-type]


def test_every_product_gets_a_non_empty_cod_categoria(tmp_path: Path) -> None:
    result = build_catalog(
        [_row(codigo="001"), _row(codigo="002"), _row(codigo="003")],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        category_groups_by_codigo={"001": ["1"], "002": ["2", "3"]},  # "003" ausente a propósito
    )
    by_id = {p.id: p for p in result.products}
    assert all(p.codCategoria for p in result.products)  # AC-2: nunca vacío
    assert by_id["001"].codCategoria == ["1"]
    assert by_id["002"].codCategoria == ["2", "3"]  # producto en más de un grupo a la vez


def test_codigo_absent_from_mapping_falls_back_to_4_and_still_publishes(tmp_path: Path) -> None:
    result = build_catalog(
        [_row(codigo="003")],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        category_groups_by_codigo={"001": ["1"]},  # no incluye "003"
    )
    assert len(result.products) == 1  # AC-3: se publica igual, no se excluye
    assert result.products[0].codCategoria == ["4"]


def test_no_category_groups_mapping_at_all_falls_back_to_4(tmp_path: Path) -> None:
    result = build_catalog(
        [_row(codigo="001")],
        env={"MARGIN_PERCENT_DEFAULT": "20"},
        out_path=tmp_path / "products.json",
        category_groups_by_codigo=None,
    )
    assert result.products[0].codCategoria == ["4"]


def test_build_catalog_is_deterministic_including_cod_categoria(tmp_path: Path) -> None:
    """AC-5: correr `transform`/`build_catalog` dos veces sobre el mismo
    input (mismas `CostRow`s + mismo `category_groups_by_codigo`) produce
    el mismo `products.json` byte a byte, incluido `codCategoria`.
    """
    rows = [_row(codigo="002"), _row(codigo="001"), _row(codigo="003")]
    env: dict[str, str | None] = {"MARGIN_PERCENT_DEFAULT": "20"}
    category_groups_by_codigo = {"001": ["3", "1"], "002": ["2"]}  # orden de entrada no ordenado a propósito

    out1 = tmp_path / "products-1.json"
    out2 = tmp_path / "products-2.json"
    build_catalog(rows, env, out1, category_groups_by_codigo=category_groups_by_codigo)
    build_catalog(rows, env, out2, category_groups_by_codigo=category_groups_by_codigo)

    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")
    assert '"codCategoria": [\n      "1",\n      "3"\n    ]' in out1.read_text(encoding="utf-8")
