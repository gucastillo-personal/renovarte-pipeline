from pipeline.ingest.verify_category_groups import build_category_group_report


def _obj(name: str, professional_exclusive: bool = False) -> dict[str, object]:
    return {
        "productLine": {"name": name},
        "professionalExclusive": professional_exclusive,
    }


def test_clean_case_each_categoria_falls_in_a_single_group() -> None:
    samples: dict[str, list[object]] = {
        "1": [_obj("Antiage"), _obj("Antiage")],
        "2": [_obj("Uñas.")],  # clean_category strips the trailing dot
        "3": [_obj("Cosmética")],
    }
    report = build_category_group_report(samples)

    assert report.conflicts == []
    assert report.categoria_to_groups["Antiage"] == {"1"}
    assert report.categoria_to_groups["Uñas"] == {"2"}
    assert report.suggested_map == {"Antiage": "1", "Uñas": "2", "Cosmética": "3"}


def test_conflict_when_categoria_appears_in_more_than_one_group() -> None:
    samples: dict[str, list[object]] = {
        "1": [_obj("Antiage")],
        "2": [_obj("Antiage")],
    }
    report = build_category_group_report(samples)

    assert report.conflicts == ["Antiage"]
    assert "Antiage" not in report.suggested_map
    assert report.categoria_to_groups["Antiage"] == {"1", "2"}


def test_unclassified_categoria_not_found_in_any_group() -> None:
    samples: dict[str, list[object]] = {"1": [_obj("Antiage")]}
    report = build_category_group_report(samples, known_categorias={"Antiage", "Uñas"})

    assert report.unclassified == ["Uñas"]


def test_unclassified_stays_empty_without_known_categorias() -> None:
    samples: dict[str, list[object]] = {"1": [_obj("Antiage")]}
    report = build_category_group_report(samples)

    assert report.unclassified == []


def test_professional_exclusive_products_are_ignored() -> None:
    samples: dict[str, list[object]] = {"1": [_obj("Antiage", professional_exclusive=True)]}
    report = build_category_group_report(samples)

    assert report.categoria_to_groups == {}


def test_malformed_objects_are_skipped_not_raised() -> None:
    samples: dict[str, list[object]] = {
        "1": [{"professionalExclusive": False}, "not-a-dict", _obj("Antiage")],
    }
    report = build_category_group_report(samples)

    assert report.categoria_to_groups == {"Antiage": {"1"}}
