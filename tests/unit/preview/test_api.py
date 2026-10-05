"""core/api.ts（サーバーの配信とのやり取り：記録の取得・レビュー中のコメント・書きかけ・まとめて送る・書き換えの知らせ）の単体テスト。"""

from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.sync_api import Page, Route

from .fixture_types import LoadPreviewScripts

# 前回開いた日時として返す日時
PREVIOUS_OPENED = "2026-10-04T13:05:00+00:00"


def _respond_previous(route: Route) -> None:
    """前回開いた日時を 200 で返す。"""
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"previous": PREVIOUS_OPENED, "opened": "2026-10-04T14:45:00+00:00"}),
    )


def _respond_server_error(route: Route) -> None:
    """書き込めないことにして 500 の problem+json を返す。"""
    route.fulfill(
        status=500,
        content_type="application/problem+json",
        body=json.dumps({"detail": "書き込めませんでした: .mindstella-opened"}, ensure_ascii=False),
    )


def _respond_abort(route: Route) -> None:
    """通信を切って、サーバーに届かない状態にする。"""
    route.abort()


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


@pytest.mark.parametrize(
    ("method", "path", "body", "status", "response_text", "expected", "expected_sent"),
    [
        pytest.param(
            "POST",
            "api/comments",
            {"target": "D-1", "body": "x"},
            201,
            '{"id": "C-1", "count": 1}',
            {"ok": True, "data": {"id": "C-1", "count": 1}},
            {"body": '{"target":"D-1","body":"x"}', "contentType": "application/json"},
            id="post_created",
        ),
        pytest.param(
            "PUT",
            "api/drafts",
            {"target": "D-1", "body": "x"},
            204,
            "",
            {"ok": True, "data": None},
            {"body": '{"target":"D-1","body":"x"}', "contentType": "application/json"},
            id="put_no_content",
        ),
        pytest.param(
            "DELETE",
            "api/comments/C-1",
            None,
            200,
            '{"id": "C-1", "count": 0}',
            {"ok": True, "data": {"id": "C-1", "count": 0}},
            {"body": None, "contentType": None},
            id="delete_without_body",
        ),
    ],
)
def test_call_api(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    status: int,
    response_text: str,
    expected: dict[str, Any],
    expected_sent: dict[str, Any],
) -> None:
    """成功の本文を返し、本文を JSON で送る（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """async ([method, path, body, status, responseText]) => {
            const calls = [];
            const fetchFn = async (url, init) => {
                calls.push({
                    url: String(url),
                    method: init?.method,
                    body: init?.body ?? null,
                    contentType: new Headers(init?.headers).get("Content-Type"),
                });
                return new Response(status === 204 ? null : responseText, {status});
            };
            const result = await MindmapPreview.callApi(method, path, body, fetchFn);
            return {result, calls};
        }""",
        [method, path, body, status, response_text],
    )
    # 検証
    assert result["result"] == expected
    assert len(result["calls"]) == 1
    call = result["calls"][0]
    assert call["url"].endswith(path)
    assert call["method"] == method
    assert {"body": call["body"], "contentType": call["contentType"]} == expected_sent


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        pytest.param(
            "conflict",
            {
                "ok": False,
                "status": 409,
                "detail": "箇所が合いません",
                "stale": [{"id": "C-2", "reason": "選んだ文がありません"}],
            },
            id="conflict_with_stale",
        ),
        pytest.param(
            "not_json",
            {"ok": False, "status": 500, "detail": "Internal Server Error", "stale": []},
            id="body_not_json",
        ),
        pytest.param(
            "throws",
            {"ok": False, "status": None, "detail": None, "stale": []},
            id="unreachable",
        ),
    ],
)
def test_call_api_when_failed(
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
                if (failure === "not_json") {
                    return new Response("<html>", {status: 500, statusText: "Internal Server Error"});
                }
                return new Response(
                    JSON.stringify({
                        detail: "箇所が合いません",
                        stale: [{id: "C-2", reason: "選んだ文がありません"}],
                    }),
                    {status: 409},
                );
            };
            return await MindmapPreview.callApi("POST", "api/comments/send", {ids: ["C-2"]}, fetchFn);
        }""",
        failure,
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("name", "arguments", "expected_method", "expected_path", "expected_body"),
    [
        pytest.param("read", [], "GET", "api/comments", None, id="read"),
        pytest.param("add", [{"body": "x"}], "POST", "api/comments", '{"body":"x"}', id="add"),
        pytest.param(
            "update",
            ["C-1", {"loc": None}],
            "PATCH",
            "api/comments/C-1",
            '{"loc":null}',
            id="update",
        ),
        pytest.param("remove", ["C-1"], "DELETE", "api/comments/C-1", None, id="remove"),
        pytest.param(
            "saveDraft",
            [{"target": "D-1", "body": "x"}],
            "PUT",
            "api/drafts",
            '{"target":"D-1","body":"x"}',
            id="save_draft",
        ),
        pytest.param("send", [["C-1"]], "POST", "api/comments/send", '{"ids":["C-1"]}', id="send"),
    ],
)
def test_comment_api(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    name: str,
    arguments: list[Any],
    expected_method: str,
    expected_path: str,
    expected_body: str | None,
) -> None:
    """各呼び出しのメソッドとパス（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    call = preview_page.evaluate(
        """async ([name, args]) => {
            const calls = [];
            const fetchFn = async (url, init) => {
                calls.push({url: String(url), method: init?.method, body: init?.body ?? null});
                return new Response("{}", {status: 200});
            };
            const api = MindmapPreview.commentApi(fetchFn);
            await api[name](...args);
            return calls[0];
        }""",
        [name, arguments],
    )
    # 検証
    assert call["url"].endswith(expected_path)
    assert (call["method"], call["body"]) == (expected_method, expected_body)


# 保存する表示の既定
DISPLAY = {"network_look": "glow", "visible_kinds": ["decisions"]}


@pytest.mark.parametrize(
    ("status", "response_text", "expected"),
    [
        pytest.param(
            200,
            json.dumps({"display": DISPLAY}),
            {"ok": True, "data": {"display": DISPLAY}},
            id="saved",
        ),
        pytest.param(
            500,
            json.dumps({"detail": "書き込めませんでした"}, ensure_ascii=False),
            {"ok": False, "status": 500, "detail": "書き込めませんでした", "stale": []},
            id="write_failed",
        ),
    ],
)
def test_put_display(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: int,
    response_text: str,
    expected: dict[str, Any],
) -> None:
    """PUT api/config/display に JSON で送る（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """async ([display, status, responseText]) => {
            const calls = [];
            const fetchFn = async (url, init) => {
                calls.push({
                    url: String(url),
                    method: init?.method,
                    body: init?.body ?? null,
                    contentType: new Headers(init?.headers).get("Content-Type"),
                });
                return new Response(responseText, {status});
            };
            const result = await MindmapPreview.putDisplay(display, fetchFn);
            return {result, calls};
        }""",
        [DISPLAY, status, response_text],
    )
    # 検証
    assert result["result"] == expected
    assert len(result["calls"]) == 1
    call = result["calls"][0]
    assert call["url"].endswith("api/config/display")
    assert call["method"] == "PUT"
    assert json.loads(call["body"]) == DISPLAY
    assert call["contentType"] == "application/json"


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


@pytest.mark.parametrize(
    ("respond", "expected"),
    [
        pytest.param(_respond_previous, PREVIOUS_OPENED, id="ok"),
        pytest.param(_respond_server_error, None, id="server_error"),
        pytest.param(_respond_abort, None, id="unreachable"),
    ],
)
def test_post_opened(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    respond: Any,
    expected: str | None,
) -> None:
    """前回の日時を返し、失敗は null を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.route("**/api/opened", respond)
    # 実行
    result = preview_page.evaluate("() => MindmapPreview.postOpened()")
    # 検証
    assert result == expected
