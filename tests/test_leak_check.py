from pathlib import Path

from pipeline.publish.leak_check import check_file_for_leaks


def test_clean_products_json_has_no_hits(tmp_path: Path) -> None:
    path = tmp_path / "products.json"
    path.write_text('[{"id": "1", "precio_venta": 1200, "en_oferta": false, "tags": []}]', encoding="utf-8")
    assert check_file_for_leaks(path) == []


def test_detects_precio_costo(tmp_path: Path) -> None:
    path = tmp_path / "products.json"
    path.write_text('{"precio_costo": 1000}', encoding="utf-8")
    hits = check_file_for_leaks(path)
    assert len(hits) == 1
    assert hits[0].token.lower() == "precio_costo"


def test_margen_word_boundary(tmp_path: Path) -> None:
    path = tmp_path / "a.json"
    path.write_text('{"margen": 20}', encoding="utf-8")
    assert len(check_file_for_leaks(path)) == 1


def test_word_containing_margen_as_substring_is_not_flagged(tmp_path: Path) -> None:
    # "desmargenado" contains "margen" but isn't the word itself — matches
    # the \b-bounded behaviour of the TS check-leak.mjs this mirrors.
    path = tmp_path / "a.json"
    path.write_text('{"nota": "desmargenado"}', encoding="utf-8")
    assert check_file_for_leaks(path) == []


def test_detects_costo_as_a_whole_word_not_substring(tmp_path: Path) -> None:
    path = tmp_path / "a.json"
    path.write_text('{"descripcion": "Este es el costo real"}', encoding="utf-8")
    assert len(check_file_for_leaks(path)) == 1

    path2 = tmp_path / "b.json"
    path2.write_text('{"descripcion": "un envase muy costoso de fabricar"}', encoding="utf-8")
    assert check_file_for_leaks(path2) == []


def test_detects_multiple_forbidden_patterns_independently(tmp_path: Path) -> None:
    path = tmp_path / "a.json"
    path.write_text('{"margin_percent_default": 20, "precio_profesional": 1000}', encoding="utf-8")
    hits = check_file_for_leaks(path)
    assert len(hits) == 2
