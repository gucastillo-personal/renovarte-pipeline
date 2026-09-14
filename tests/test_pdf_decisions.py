from pathlib import Path

import pytest

from pipeline.transform.pdf_decisions import PdfDecision, load_decisions, save_decisions


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_decisions(tmp_path / "nope.json") == {}


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "precio_pdf_decisiones.json"
    decisions = {
        "002": PdfDecision(fuente="catalogo", valor=1500),
        "001": PdfDecision(fuente="abc", valor=1300),
    }
    save_decisions(path, decisions)
    loaded = load_decisions(path)
    assert loaded == decisions


def test_save_is_deterministic_sorted_by_codigo(tmp_path: Path) -> None:
    path = tmp_path / "d.json"
    save_decisions(path, {"b": PdfDecision(fuente="actual", valor=100), "a": PdfDecision(fuente="abc", valor=200)})
    content = path.read_text(encoding="utf-8")
    assert content.index('"a"') < content.index('"b"')
    assert content.endswith("\n")


def test_never_stores_cost_fields(tmp_path: Path) -> None:
    path = tmp_path / "d.json"
    save_decisions(path, {"001": PdfDecision(fuente="abc", valor=1300)})
    content = path.read_text(encoding="utf-8")
    assert "precio_costo" not in content
    assert "precio_profesional" not in content
    assert "margen" not in content


def test_invalid_fuente_raises(tmp_path: Path) -> None:
    path = tmp_path / "d.json"
    path.write_text('{"001": {"fuente": "bogus", "valor": 100}}')
    with pytest.raises(ValueError, match="entrada inválida"):
        load_decisions(path)


def test_non_integer_valor_raises(tmp_path: Path) -> None:
    path = tmp_path / "d.json"
    path.write_text('{"001": {"fuente": "abc", "valor": "1300"}}')
    with pytest.raises(ValueError, match="debe ser un entero"):
        load_decisions(path)
