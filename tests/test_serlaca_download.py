import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from pipeline.ingest import serlaca_download


@dataclass
class _FakeDump:
    data_objects: list[Any]
    total_items: int
    pages: int


def test_run_writes_raw_dump_with_category_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_all_serlaca_pages(**kwargs: object) -> _FakeDump:
        return _FakeDump(data_objects=[{"productCode": "001"}], total_items=1, pages=1)

    def fake_fetch_category_group_samples(
        env: dict[str, str | None], client: object = None
    ) -> dict[str, list[Any]]:
        return {"1": [{"productCode": "001"}], "2": [{"productCode": "001"}]}

    monkeypatch.setattr(serlaca_download, "fetch_all_serlaca_pages", fake_fetch_all_serlaca_pages)
    monkeypatch.setattr(serlaca_download, "fetch_category_group_samples", fake_fetch_category_group_samples)

    out_path = tmp_path / "serlaca-raw.json"
    result_path = serlaca_download.run({"SERLACA_API_KEY": "k", "SERLACA_LACA_ID": "l"}, raw_path=out_path)

    assert result_path == out_path
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["dataObjects"] == [{"productCode": "001"}]
    assert written["categoryGroupsByProductCode"] == {"001": ["1", "2"]}


def test_run_with_no_group_overlap_gives_single_id_lists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_fetch_all_serlaca_pages(**kwargs: object) -> _FakeDump:
        return _FakeDump(data_objects=[{"productCode": "001"}, {"productCode": "002"}], total_items=2, pages=1)

    def fake_fetch_category_group_samples(
        env: dict[str, str | None], client: object = None
    ) -> dict[str, list[Any]]:
        return {"1": [{"productCode": "001"}], "2": [{"productCode": "002"}], "3": []}

    monkeypatch.setattr(serlaca_download, "fetch_all_serlaca_pages", fake_fetch_all_serlaca_pages)
    monkeypatch.setattr(serlaca_download, "fetch_category_group_samples", fake_fetch_category_group_samples)

    out_path = tmp_path / "serlaca-raw.json"
    serlaca_download.run({}, raw_path=out_path)

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["categoryGroupsByProductCode"] == {"001": ["1"], "002": ["2"]}
