from pipeline.sources.html import clean_name, decode_entities, format_size, html_to_text


def test_decode_named_entities() -> None:
    assert decode_entities("Caracter&iacute;sticas") == "Características"


def test_decode_numeric_entities_decimal_and_hex() -> None:
    assert decode_entities("&#237;") == "í"
    assert decode_entities("&#xed;") == "í"


def test_html_to_text_converts_block_tags_to_newlines() -> None:
    html = "<p><strong>Características:</strong> Mascara gelatinosa.</p>\r\n\r\n<p>Presentación: Pote</p>\r\n"
    text = html_to_text(html)
    assert text == "Características: Mascara gelatinosa.\n\nPresentación: Pote"


def test_html_to_text_none_or_empty() -> None:
    assert html_to_text(None) == ""
    assert html_to_text("") == ""


def test_clean_name_title_cases_all_caps() -> None:
    assert clean_name("LAPIZ SEC.ATIVO INCOLORO X3,5G") == "Lapiz Sec.ativo Incoloro X3,5g"


def test_clean_name_leaves_mixed_case_alone() -> None:
    assert clean_name("Ya Con Formato") == "Ya Con Formato"


def test_clean_name_collapses_whitespace() -> None:
    assert clean_name("  Con   espacios  ") == "Con espacios"


def test_format_size_with_unit() -> None:
    assert format_size(250, "mL") == "250 ml"


def test_format_size_integer_amount_has_no_decimal() -> None:
    assert format_size(3.5, "g") == "3.5 g"
    assert format_size(250.0, "g") == "250 g"


def test_format_size_missing() -> None:
    assert format_size(None, None) == ""
