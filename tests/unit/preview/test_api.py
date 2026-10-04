"""core/api.ts（サーバーの配信とのやり取り：記録の取得・回答・意見の送信・書き換えの知らせ）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts


def test_fetch_records(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """200 の本文を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """async () => {
            const calls = [];
            const fetchFn = async (url, init) => {
                calls.push({url: String(url), cache: init?.cache});
                return new Response(JSON.stringify({decisions: []}), {status: 200});
            };
            const result = await MindmapPreview.fetchRecords(fetchFn);
            return {result, calls};
        }"""
    )
    # 検証
    assert result["result"] == {"ok": True, "data": {"decisions": []}}
    assert [call["cache"] for call in result["calls"]] == ["no-store"]
    assert result["calls"][0]["url"].endswith("api/records")


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        pytest.param(
            "throws", {"ok": False, "reason": "unreachable", "detail": None}, id="unreachable"
        ),
        pytest.param("invalid", {"ok": False, "reason": "invalid", "detail": "理由"}, id="invalid"),
    ],
)
def test_fetch_records_when_failed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    failure: str,
    expected: dict[str, Any],
) -> None:
    """届かない・422 を分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """async (failure) => {
            const fetchFn = async () => {
                if (failure === "throws") throw new TypeError("Failed to fetch");
                return new Response(JSON.stringify({detail: "理由"}), {status: 422});
            };
            return await MindmapPreview.fetchRecords(fetchFn);
        }""",
        failure,
    )
    # 検証
    assert result == expected


def test_post_submission(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """201 の本文を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    sent = "2026-10-04T02:23:00+00:00"
    # 実行
    result = preview_page.evaluate(
        """async (sent) => {
            const calls = [];
            const fetchFn = async (url, init) => {
                calls.push({
                    url: String(url),
                    method: init?.method,
                    body: init?.body,
                    contentType: new Headers(init?.headers).get("Content-Type"),
                });
                return new Response(JSON.stringify({id: "S-1", sent}), {status: 201});
            };
            const result = await MindmapPreview.postSubmission("D-1", "案 A にする", fetchFn);
            return {result, calls};
        }""",
        sent,
    )
    # 検証
    assert result["result"] == {"ok": True, "id": "S-1", "sent": sent}
    assert len(result["calls"]) == 1
    call = result["calls"][0]
    assert call["url"].endswith("api/submissions")
    assert call["method"] == "POST"
    assert call["body"] == '{"target":"D-1","body":"案 A にする"}'
    assert call["contentType"] == "application/json"


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        pytest.param("rejected", {"ok": False, "detail": "項目がありません: D-99"}, id="rejected"),
        pytest.param("throws", {"ok": False, "detail": None}, id="unreachable"),
    ],
)
def test_post_submission_when_failed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    failure: str,
    expected: dict[str, Any],
) -> None:
    """断られた・届かないを分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """async (failure) => {
            const fetchFn = async () => {
                if (failure === "throws") throw new TypeError("Failed to fetch");
                return new Response(
                    JSON.stringify({detail: "項目がありません: D-99"}), {status: 404}
                );
            };
            return await MindmapPreview.postSubmission("D-99", "本文", fetchFn);
        }""",
        failure,
    )
    # 検証
    assert result == expected


def test_subscribe_events(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """changed と接続の変化だけを知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            const log = {connection: [], changed: 0, closed: 0, url: null};
            let source = null;
            // 偽の EventSource（addEventListener と onopen・onerror のどちらで受けても動く）
            class FakeEventSource {
                constructor(url) {
                    this.url = String(url);
                    this.listeners = {};
                    source = this;
                }
                addEventListener(type, listener) {
                    (this.listeners[type] ||= []).push(listener);
                }
                close() {
                    log.closed += 1;
                }
                emit(type) {
                    const event = {type};
                    (this.listeners[type] || []).forEach((listener) => listener(event));
                    const handler = this["on" + type];
                    if (typeof handler === "function") handler.call(this, event);
                }
            }
            const close = MindmapPreview.subscribeEvents({
                onChanged: () => {
                    log.changed += 1;
                },
                onConnection: (connected) => {
                    log.connection.push(connected);
                },
                EventSourceCtor: FakeEventSource,
            });
            for (const type of ["open", "changed", "error", "error", "open"]) {
                source.emit(type);
            }
            close();
            log.url = source.url;
            return log;
        }"""
    )
    # 検証
    assert result["connection"] == [True, False, True]
    assert result["changed"] == 1
    assert result["closed"] == 1
    assert result["url"].endswith("api/events")
