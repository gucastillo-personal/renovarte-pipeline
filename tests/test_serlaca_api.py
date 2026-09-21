from pipeline.sources.serlaca_api import group_ids_by_product_code


def test_product_in_a_single_group() -> None:
    samples: dict[str, list[object]] = {"1": [{"productCode": "001"}]}
    assert group_ids_by_product_code(samples) == {"001": ["1"]}


def test_product_in_more_than_one_group_keeps_both_ids_sorted() -> None:
    samples: dict[str, list[object]] = {
        "1": [{"productCode": "001"}],
        "2": [{"productCode": "001"}, {"productCode": "002"}],
        "3": [{"productCode": "001"}],
    }
    result = group_ids_by_product_code(samples)
    assert result["001"] == ["1", "2", "3"]
    assert result["002"] == ["2"]


def test_malformed_or_codeless_objects_are_ignored() -> None:
    samples: dict[str, list[object]] = {
        "1": [
            {"productCode": ""},
            {"no_code": True},
            "not-a-dict",
            {"productCode": "010"},
        ]
    }
    assert group_ids_by_product_code(samples) == {"010": ["1"]}


def test_product_code_is_stripped() -> None:
    samples: dict[str, list[object]] = {"1": [{"productCode": " 001 "}]}
    assert group_ids_by_product_code(samples) == {"001": ["1"]}


def test_empty_samples_gives_empty_map() -> None:
    assert group_ids_by_product_code({}) == {}
