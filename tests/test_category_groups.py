import json
from pathlib import Path

from pipeline.transform.category_groups import FALLBACK_COD_CATEGORIA, resolve_cod_categoria

_CATEGORY_GROUPS_JSON = Path(__file__).resolve().parent.parent / "data" / "reference" / "serlaca_category_groups.json"


def test_resolve_cod_categoria_passes_through_a_single_group() -> None:
    assert resolve_cod_categoria(["2"]) == ["2"]


def test_resolve_cod_categoria_sorts_and_dedupes_multiple_groups() -> None:
    assert resolve_cod_categoria(["3", "1", "1"]) == ["1", "3"]


def test_resolve_cod_categoria_falls_back_to_4_when_empty_list() -> None:
    assert resolve_cod_categoria([]) == [FALLBACK_COD_CATEGORIA]


def test_resolve_cod_categoria_falls_back_to_4_when_none() -> None:
    assert resolve_cod_categoria(None) == [FALLBACK_COD_CATEGORIA]


def test_serlaca_category_groups_json_has_exactly_the_four_group_names() -> None:
    """AC-4: el mapeo (A) id -> nombre existe, committed, con los 3 nombres
    de negocio más el del fallback.
    """
    data = json.loads(_CATEGORY_GROUPS_JSON.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"1", "2", "3", "4"}
    assert all(isinstance(name, str) and name.strip() for name in data.values())
