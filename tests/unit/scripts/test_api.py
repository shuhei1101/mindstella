"""api.py（MindStella の API の経路）の単体テスト。"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.routing import Route

import api
from errors import ApiError

# 常駐サーバーのポート
PORT = 8784


def _request(headers: dict[str, str]) -> Request:
    """ヘッダーだけを持つ要求を作る。"""
    raw = [(name.lower().encode(), value.encode()) for name, value in headers.items()]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/workspaces",
            "headers": raw,
            "query_string": b"",
        }
    )


def test_build_routes() -> None:
    """経路とメソッドが揃う。"""
    routes = api.build_routes(SimpleNamespace(port=PORT))
    pairs = {
        (route.path, method)
        for route in routes
        if isinstance(route, Route)
        for method in route.methods or []
    }
    assert {
        ("/workspaces", "POST"),
        ("/workspaces/{id}/sessions", "POST"),
        ("/workspaces/{id}/sessions", "GET"),
        ("/workspaces/{id}/sessions/{session}", "DELETE"),
        ("/workspaces/{id}/close", "POST"),
        ("/_admin/sessions/{session}/events", "POST"),
    } <= pairs


@pytest.mark.parametrize(
    ("headers", "allowed"),
    [
        pytest.param({"Host": f"127.0.0.1:{PORT}"}, True, id="loopback"),
        pytest.param({"Host": f"localhost:{PORT}"}, True, id="localhost"),
        pytest.param({"Host": "preview.example.test"}, False, id="outside-host"),
        pytest.param(
            {"Host": f"127.0.0.1:{PORT}", "Origin": "http://evil.test"}, False, id="outside-origin"
        ),
    ],
)
def test_check_host(headers: dict[str, str], allowed: bool) -> None:
    """端末の中の Host だけを通す。"""
    request = _request(headers)
    if allowed:
        api.check_host(request, PORT)
        return
    with pytest.raises(ApiError) as caught:
        api.check_host(request, PORT)
    assert (caught.value.status, caught.value.stage) == (403, "host")


def test_problem_response() -> None:
    """problem+json の形とステータス。"""
    response = api.problem_response(
        ApiError(409, "exists", "起動中です", session="S-1", pane="w:0.0")
    )
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    body = json.loads(bytes(response.body))
    assert body["status"] == 409
    assert body["stage"] == "exists"
    assert body["detail"] == "起動中です"
    assert (body["session"], body["pane"]) == ("S-1", "w:0.0")
    assert "type" in body
    assert "title" in body
