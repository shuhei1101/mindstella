"""PoC: ビルドした SPA の配信と、書き換えの知らせの反映を確かめる。"""

from __future__ import annotations

import http.client
import time
from urllib.parse import urlsplit

from playwright.sync_api import Page
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace


def _get(url: str, path: str, host: str | None = None) -> tuple[int, str, bytes]:
    """配信へ GET し、ステータス・Content-Type・本文を返す。"""
    parts = urlsplit(url)
    conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
    headers = {"Host": host} if host else {}
    conn.request("GET", path, headers=headers)
    res = conn.getresponse()
    body = res.read()
    conn.close()
    return res.status, res.getheader("Content-Type") or "", body


def test_spa_paths(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    root = make_workspace(make_item("D-1"))
    url = str(call_tool("preview_url", workspace=str(root)).data["url"])
    status, ctype, body = _get(url, "/spa/")
    print("index", status, ctype)
    assert status == 200 and ctype.startswith("text/html") and b'id="root"' in body
    asset = body.decode().split('src="')[1].split('"')[0]
    status, ctype, _ = _get(url, asset)
    print("asset", asset, status, ctype)
    assert status == 200 and ctype.startswith("text/javascript")
    status, ctype, body = _get(url, "/spa/some/route")
    print("route", status, ctype)
    assert status == 200 and b'id="root"' in body
    status, _, _ = _get(url, "/spa/../config.yaml")
    print("traversal", status)
    status, _, _ = _get(url, "/spa/", host="attacker.example")
    print("host", status)
    assert status == 403
    status, ctype, _ = _get(url, "/mindstella.html")
    print("old", status, ctype)
    assert status == 200


def test_spa_reflects_add(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page
) -> None:
    root = make_workspace(make_item("D-1"), make_item("D-3"))
    url = str(call_tool("preview_url", workspace=str(root)).data["url"])
    base = url.removesuffix("/mindstella.html")
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/spa/?tab=decisions")
    page.wait_for_selector("[data-testid=decision-count]")
    assert page.text_content("[data-testid=decision-count]") == "2"
    assert page.text_content("[data-testid=tab]") == "decisions"
    new_decision = {
        "title": "新しい問い",
        "target": "mindmap",
        "category": "データ構造",
        "phase": "要件",
        "status": "未決定",
        "options": [{"key": "A", "content": "案 A"}],
    }
    started = time.monotonic()
    assert call_tool("add", workspace=str(root), kind="decision", item=new_decision).is_error is False
    page.wait_for_function(
        "document.querySelector('[data-testid=decision-count]').textContent === '3'", timeout=2000
    )
    print("reflect_sec", round(time.monotonic() - started, 3))
    heap = page.evaluate("performance.memory ? performance.memory.usedJSHeapSize : null")
    print("heap_bytes", heap)
    assert errors == []
