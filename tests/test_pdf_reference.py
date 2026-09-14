from pathlib import Path

from pipeline.sources.pdf_laca import LacaPdfRow
from pipeline.transform.pdf_reference import to_public_reference, write_reference_csv


def _row(**overrides: object) -> LacaPdfRow:
    base = {
        "codigo": "510500003",
        "nombre_pdf": "Mascara Shock Antiage",
        "precio_profesional": 18000.0,
        "precio_abc": 22600.0,
        "precio_catalogo": 28900.0,
    }
    base.update(overrides)
    return LacaPdfRow(**base)  # type: ignore[arg-type]


def test_to_public_reference_drops_precio_profesional() -> None:
    public_rows = to_public_reference([_row()], fuente="LACA 2026-09")
    row = public_rows[0]
    assert not hasattr(row, "precio_profesional")
    assert row.precio_abc == 22600.0
    assert row.fuente == "LACA 2026-09"


def test_write_reference_csv_sorted_by_codigo(tmp_path: Path) -> None:
    rows = to_public_reference([_row(codigo="002"), _row(codigo="001")], fuente="LACA 2026-09")
    out = tmp_path / "laca_pdf_precios.csv"
    write_reference_csv(rows, out)

    content = out.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert lines[0] == "codigo,nombre_pdf,precio_abc,precio_catalogo,fuente"
    assert lines[1].startswith("001,")
    assert lines[2].startswith("002,")
    assert "precio_profesional" not in content
