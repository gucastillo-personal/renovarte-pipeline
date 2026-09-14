from collections.abc import Callable

import httpx
import pytest

from pipeline.publish.github_api import GitHubApiError, open_pull_request


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))


def test_opens_new_pr_when_none_exists() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json={"html_url": "https://github.com/o/r/pull/1"})

    url = open_pull_request(
        repo="o/r",
        token="tok",
        head_branch="pipeline/auto-update-products",
        base_branch="main",
        title="t",
        body="b",
        client=_client(handler),
    )
    assert url == "https://github.com/o/r/pull/1"
    assert calls[0].method == "GET"
    assert calls[1].method == "POST"
    assert calls[1].headers["authorization"] == "Bearer tok"


def test_reuses_existing_open_pr_instead_of_duplicating() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json=[{"html_url": "https://github.com/o/r/pull/7"}])

    url = open_pull_request(
        repo="o/r", token="tok", head_branch="b", base_branch="main", title="t", body="b", client=_client(handler)
    )
    assert url == "https://github.com/o/r/pull/7"


def test_raises_on_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(422, text="validation failed")

    with pytest.raises(GitHubApiError, match="422"):
        open_pull_request(
            repo="o/r", token="tok", head_branch="b", base_branch="main", title="t", body="b", client=_client(handler)
        )
