import json
from pathlib import Path

import pytest

from pipeline.transform.offers import load_offers


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_offers(tmp_path / "nope.json") == {}


def test_array_shape_is_badge_only(tmp_path: Path) -> None:
    path = tmp_path / "offers.json"
    path.write_text(json.dumps(["A", "B"]))
    offers = load_offers(path)
    assert offers["A"].descuento_pct == 0
    assert offers["B"].descuento_pct == 0


def test_codigos_wrapper_with_per_code_discount(tmp_path: Path) -> None:
    path = tmp_path / "offers.json"
    path.write_text(json.dumps({"codigos": {"A": {}, "B": {"descuento_pct": 10}}}))
    offers = load_offers(path)
    assert offers["A"].descuento_pct == 0
    assert offers["B"].descuento_pct == 10


def test_bare_object_shape_without_codigos_wrapper(tmp_path: Path) -> None:
    path = tmp_path / "offers.json"
    path.write_text(json.dumps({"A": {"descuento_pct": 15}}))
    offers = load_offers(path)
    assert offers["A"].descuento_pct == 15


def test_invalid_discount_raises(tmp_path: Path) -> None:
    path = tmp_path / "offers.json"
    path.write_text(json.dumps({"codigos": {"A": {"descuento_pct": 150}}}))
    with pytest.raises(ValueError, match="descuento_pct inválido"):
        load_offers(path)


def test_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "offers.json"
    path.write_text("{not json")
    with pytest.raises(ValueError, match="JSON inválido"):
        load_offers(path)
