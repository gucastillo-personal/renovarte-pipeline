from pathlib import Path

import pytest

from pipeline.sources.csv_source import parse_ars_number, parse_boolean, parse_tags, read_csv_cost_rows


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("28000", 28000),
        ("28.000", 28000),
        ("28000,50", 28000.5),
        ("$ 28.000,50", 28000.5),
        ("28,5", 28.5),
    ],
)
def test_parse_ars_number(raw: str, expected: float) -> None:
    assert parse_ars_number(raw) == expected


def test_parse_ars_number_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="valor numérico inválido"):
        parse_ars_number("no-number")


@pytest.mark.parametrize("raw", ["si", "SI", "sí", "true", "1", "x", "yes"])
def test_parse_boolean_truthy(raw: str) -> None:
    assert parse_boolean(raw) is True


@pytest.mark.parametrize("raw", ["no", "false", "0", "", None])
def test_parse_boolean_falsy(raw: str | None) -> None:
    assert parse_boolean(raw) is False


def test_parse_tags_splits_on_pipe_or_comma() -> None:
    assert parse_tags("día|noche, antiage") == ["día", "noche", "antiage"]


def test_parse_tags_absent_is_empty() -> None:
    assert parse_tags(None) == []


def test_read_csv_cost_rows_from_sample_fixture(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "codigo,nombre,categoria,presentacion,descripcion,precio_costo,en_oferta,tags\n"
        '545300004,Complejo Antiage,Antiage,50 g,"Descripción.",29400,no,día|noche\n',
        encoding="utf-8",
    )
    rows, warnings = read_csv_cost_rows(csv_path, public_dir=tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row.codigo == "545300004"
    assert row.precio_costo == 29400
    assert row.en_oferta is False
    assert row.tags == ["día", "noche"]
    assert row.imagen == "/img/placeholder.svg"
    assert "sin imagen" in warnings[0]


def test_read_csv_cost_rows_missing_required_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("codigo,nombre\n001,Producto\n", encoding="utf-8")
    with pytest.raises(ValueError, match="faltan columnas requeridas"):
        read_csv_cost_rows(csv_path, public_dir=tmp_path)
