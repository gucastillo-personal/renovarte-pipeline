"""Tests del parser de tabla del PDF de LACA, contra la estructura real
observada (validada a mano contra el PDF real de LACA, spec 0008): sin fila
de encabezado, columnas fijas por posición, celdas de nombre que a veces
agrupan varios códigos con filas de continuación (`None` en la celda de
nombre). Los valores de precio de los fixtures acá son inventados — nunca
se commitean precios reales extraídos del PDF (serían costo real de LACA).
"""

from pipeline.sources.pdf_laca import _split_name_cell, parse_table


def test_split_name_cell_single_code_with_separate_qty_line() -> None:
    blocks = _split_name_cell("510500003\n250\nMascara Shock Antiage")
    assert blocks == [("510500003", "Mascara Shock Antiage")]


def test_split_name_cell_qty_and_suffix_embedded_in_code_line() -> None:
    blocks = _split_name_cell("545190004 A 2\nMonodosis R Dr. Enero (10 unidades)")
    assert blocks == [("545190004", "Monodosis R Dr. Enero (10 unidades)")]


def test_split_name_cell_letter_suffix_on_its_own_line() -> None:
    blocks = _split_name_cell("022180100 CP\nPincel para sombras clasico")
    assert blocks == [("022180100", "Pincel para sombras clasico")]
    blocks2 = _split_name_cell("022330300\nCP\nPincel anatomico")
    assert blocks2 == [("022330300", "Pincel anatomico")]


def test_split_name_cell_groups_multiple_codes() -> None:
    cell = "501040004\n100\nGel de limpieza\n501040003\n250\nGel de limpieza"
    blocks = _split_name_cell(cell)
    assert blocks == [
        ("501040004", "Gel de limpieza"),
        ("501040003", "Gel de limpieza"),
    ]


def test_split_name_cell_no_code_found_is_empty() -> None:
    assert _split_name_cell("RANGO DE PUNTOS\nALGO") == []
    assert _split_name_cell("") == []


def test_split_name_cell_eight_digit_code() -> None:
    # Not every product line uses 9-digit codes — nail polish etc. use 8.
    blocks = _split_name_cell("18128604\n15\nEsmalte efecto gel | 86 Magic Night")
    assert blocks == [("18128604", "Esmalte efecto gel | 86 Magic Night")]


def test_split_name_cell_short_name_that_looks_like_noise_is_not_dropped() -> None:
    # "F1"/"M2" etc. are short but real product-line names, not a stray
    # suffix like "L"/"CP" — both match the same noise-looking shape, so the
    # fallback (last non-empty line) has to win over dropping everything.
    blocks = _split_name_cell("17060004\n55\nF1")
    assert blocks == [("17060004", "F1")]


def test_parse_table_single_code_rows() -> None:
    table = [
        ["510500003\n250\nMascara Shock", "$ 18.000", "$ 22.600", "$ 28.900", "34"],
        ["506530004\n70\nLapiz Secativo", "$ 10.500", "$ 17.600", "$ 21.900", "31"],
    ]
    rows = parse_table(table)
    assert [r.codigo for r in rows] == ["510500003", "506530004"]
    assert rows[0].nombre_pdf == "Mascara Shock"
    assert rows[0].precio_profesional == 18000
    assert rows[0].precio_abc == 22600
    assert rows[0].precio_catalogo == 28900


def test_parse_table_continuation_row_supplies_price_for_second_code() -> None:
    name_cell = "501040004\n100\nGel de limpieza\n501040003\n250\nGel de limpieza"
    table: list[list[str | None]] = [
        [name_cell, "$ 12.300", "$ 17.200", "$ 24.600", "20"],
        [None, "$ 16.700", "$ 23.300", "-", "27"],
    ]
    rows = parse_table(table)
    assert len(rows) == 2
    assert rows[0].codigo == "501040004"
    assert rows[0].precio_profesional == 12300
    assert rows[1].codigo == "501040003"
    assert rows[1].precio_profesional == 16700
    assert rows[1].precio_catalogo is None  # "-" in the PDF


def test_parse_table_three_way_grouping() -> None:
    name_cell = "501500004\n100\nLeche\n501500003\n250\nLeche\n501500002\n500\nLeche"
    table: list[list[str | None]] = [
        [name_cell, "$ 12.400", "$ 17.300", "$ 24.800", "20"],
        [None, "$ 20.300", "$ 28.400", "-", "32"],
        [None, "$ 25.800", "$ 36.100", "-", "41"],
    ]
    rows = parse_table(table)
    assert [r.codigo for r in rows] == ["501500004", "501500003", "501500002"]
    assert [r.precio_profesional for r in rows] == [12400, 20300, 25800]


def test_parse_table_missing_precio_profesional_is_skipped() -> None:
    table = [["510500003\n250\nProducto", "-", "$ 22.600", "$ 28.900", "34"]]
    assert parse_table(table) == []


def test_parse_table_page_with_no_matching_rows_is_empty() -> None:
    table = [["RANGO DE PUNTOS", None, "BEFILA"], [None, "395", "739"]]
    assert parse_table(table) == []


def test_parse_table_four_column_row_has_no_catalogo_price() -> None:
    # Bulk/professional-pack rows drop the Catálogo column entirely — no "-"
    # placeholder, the row just has one less cell. The trailing "202" here is
    # "Ptos" (loyalty points), not a price, and must not be read as one.
    table = [["702000504\nNeblina x 4 unidades", "$ 88.480", "$ 123.760", "202"]]
    rows = parse_table(table)
    assert len(rows) == 1
    assert rows[0].precio_abc == 123760
    assert rows[0].precio_catalogo is None


def test_parse_table_degenerate_row_is_skipped_without_losing_pending() -> None:
    # A malformed row (can't locate price columns at all) shouldn't consume
    # a pending code that a later, well-formed row could still price.
    table: list[list[str | None]] = [
        ["510500003\n250\nProducto", "$ 18.000", "$ 22.600", "$ 28.900", "34"],
        ["garbage"],  # only 1 cell — can't be interpreted, must not crash
    ]
    rows = parse_table(table)
    assert len(rows) == 1
    assert rows[0].codigo == "510500003"


def test_parse_table_empty_input() -> None:
    assert parse_table([]) == []
