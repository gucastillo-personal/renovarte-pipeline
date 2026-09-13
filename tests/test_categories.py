from pipeline.transform.categories import clean_category


def test_strips_trailing_dot_and_spaces() -> None:
    assert clean_category("Uñas. ") == "Uñas"


def test_collapses_internal_whitespace() -> None:
    assert clean_category("Antiage   Facial") == "Antiage Facial"


def test_applies_rename_map_case_insensitively() -> None:
    assert clean_category("Proteccion Solar.") == "Protección Solar"


def test_unmapped_category_passes_through_trimmed() -> None:
    assert clean_category("  Corporales  ") == "Corporales"
