"""components/thread-post.ts（スレッドの書き込み・状態の記録・レビュー中の返信と、本文の中の項目の ID の切り出し）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 利用者の書き込み
USER_POST = {
    "id": "TH-1-1",
    "author": "user",
    "body": "案 B にしたい",
    "created": "2026-10-12T01:20:00+00:00",
}

# 記録にある D-12 と、記録に無い D-99 を含む 2 行の AI の書き込み
AI_POST = {
    "id": "TH-1-2",
    "author": "ai",
    "body": "D-12 を案 B に決めました。\nD-99 は記録にありません。",
    "created": "2026-10-12T01:24:00+00:00",
}

# まだ送っていない、スレッドへの返信
PENDING_REPLY = {
    "id": "C-43",
    "target": None,
    "target_title": None,
    "loc": None,
    "thread": "TH-1",
    "body": "了解です",
    "created": "2026-10-12T05:20:00+00:00",
}

# 書き込みを作って文書に置き、見た目と押した結果を集める JavaScript
POST_SCRIPT = """(props) => {
    const calls = [];
    const item = MindmapPreview.threadPost({
        titles: (id) => (id === "D-12" ? "失敗時の扱い" : null),
        ...props,
        on: {
            openId: (...a) => calls.push(["openId", ...a]),
            edit: (...a) => calls.push(["edit", ...a]),
            saveEdit: (...a) => calls.push(["saveEdit", ...a]),
            cancelEdit: (...a) => calls.push(["cancelEdit", ...a]),
            remove: (...a) => calls.push(["remove", ...a]),
        },
    });
    document.body.append(item);
    const buttons = [...item.querySelectorAll("button")];
    const named = (name) => buttons.find((button) => button.getAttribute("aria-label") === name);
    const idButton = buttons.find((button) => button.textContent.trim() === "D-12");
    if (idButton !== undefined) idButton.click();
    for (const name of ["TH-1 への返信を修正", "TH-1 への返信を削除"]) {
        const button = named(name);
        if (button !== undefined) button.click();
    }
    return {
        classes: [...item.classList],
        text: item.textContent.replace(/\\s+/g, " "),
        html: item.innerHTML,
        hasTime: item.querySelector("time[datetime]") !== null,
        idButtonTitle: idButton === undefined ? null : idButton.title,
        unknownIdIsButton: buttons.some((button) => button.textContent.trim() === "D-99"),
        buttonNames: buttons.map(
            (button) => button.getAttribute("aria-label") ?? button.textContent.trim()
        ),
        hasField: item.querySelector("textarea") !== null,
        alerts: [...item.querySelectorAll('[role="alert"]')].map((alert) => alert.textContent),
        calls,
    };
}"""


def _observe(preview_page: Page, props: dict[str, Any]) -> dict[str, Any]:
    """書き込みを作って見た目と押した結果を返す。"""
    return preview_page.evaluate(POST_SCRIPT, props)


@pytest.mark.parametrize(
    ("post", "expected_classes", "expected_head", "expected_calls"),
    [
        pytest.param(USER_POST, {"post", "user"}, "あなた", [], id="user"),
        pytest.param(AI_POST, {"post", "ai"}, "AI", [["openId", "D-12"]], id="ai"),
    ],
)
def test_thread_post(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    post: dict[str, Any],
    expected_classes: set[str],
    expected_head: str,
    expected_calls: list[list[str]],
) -> None:
    """書き手ごとの書き込みと、記録にある ID のリンク（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, {"post": post})
    # 検証
    assert expected_classes <= set(observed["classes"])
    assert expected_head in observed["text"]
    assert observed["hasTime"] is True
    assert observed["calls"] == expected_calls


def test_thread_post_when_known_and_unknown_id(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """記録にある ID はタイトルつきのボタン、記録に無い ID は文字のまま。改行を保つ（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, {"post": AI_POST})
    # 検証
    assert observed["idButtonTitle"] == "失敗時の扱い"
    assert observed["unknownIdIsButton"] is False
    assert "D-99" in observed["text"]
    assert "\n" in observed["html"] or "<br" in observed["html"]


@pytest.mark.parametrize(
    ("event", "expected_text", "reason_visible"),
    [
        pytest.param(
            {"kind": "closed", "author": "user", "reason": "案 A で決着", "created": "2026-10-12T02:10:00+00:00"},
            "あなたがクローズにしました",
            True,
            id="user_closed",
        ),
        pytest.param(
            {"kind": "reopened", "author": "user", "reason": None, "created": "2026-10-12T02:20:00+00:00"},
            "あなたがオープンに戻しました",
            False,
            id="user_reopened",
        ),
        pytest.param(
            {"kind": "closed", "author": "ai", "reason": None, "created": "2026-10-12T02:30:00+00:00"},
            "AI がクローズにしました",
            False,
            id="ai_closed",
        ),
        pytest.param(
            {"kind": "reopened", "author": "ai", "reason": None, "created": "2026-10-12T02:40:00+00:00"},
            "AI がオープンに戻しました",
            False,
            id="ai_reopened",
        ),
    ],
)
def test_thread_post_when_event(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    event: dict[str, Any],
    expected_text: str,
    reason_visible: bool,
) -> None:
    """状態の記録の書き手・日時・理由（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, {"event": event})
    # 検証
    assert expected_text in observed["text"]
    assert observed["hasTime"] is True
    assert ("案 A で決着" in observed["text"]) is reason_visible


@pytest.mark.parametrize(
    ("props", "expected_buttons", "expect_field", "expected_alert", "expected_calls"),
    [
        pytest.param(
            {"pending": PENDING_REPLY},
            ["TH-1 への返信を修正", "TH-1 への返信を削除"],
            False,
            None,
            [["edit", "C-43"], ["remove", "C-43"]],
            id="default",
        ),
        pytest.param(
            {"pending": PENDING_REPLY, "editing": True},
            ["キャンセル", "修正"],
            True,
            None,
            [],
            id="editing",
        ),
        pytest.param(
            {"pending": PENDING_REPLY, "editing": True, "editError": "直せませんでした"},
            ["キャンセル", "修正"],
            True,
            "直せませんでした",
            [],
            id="edit_error",
        ),
    ],
)
def test_thread_post_when_pending(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected_buttons: list[str],
    expect_field: bool,
    expected_alert: str | None,
    expected_calls: list[list[str]],
) -> None:
    """レビュー中の書き込みの印・修正・削除と、書き換えている形（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, props)
    # 検証
    assert "レビュー中" in observed["text"]
    assert observed["buttonNames"] == expected_buttons
    assert observed["hasField"] is expect_field
    assert observed["alerts"] == ([] if expected_alert is None else [expected_alert])
    assert observed["calls"] == expected_calls


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(
            "D-12 を案 B に。T-14 も",
            [["id", "D-12"], ["text", " を案 B に。"], ["id", "T-14"], ["text", " も"]],
            id="known_ids",
        ),
        pytest.param("D-99 は無い", [["text", "D-99 は無い"]], id="unknown_id"),
        pytest.param(
            "TH-1 と AD-12 と D-12x", [["text", "TH-1 と AD-12 と D-12x"]], id="not_item_ids"
        ),
        pytest.param("", [["text", ""]], id="empty"),
    ],
)
def test_split_post_body(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    body: str,
    expected: list[list[str]],
) -> None:
    """記録にある ID だけを切り出す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    parts = preview_page.evaluate(
        """(body) => {
            const titles = (id) => (id === "D-12" || id === "T-14" ? id + "の題" : null);
            return MindmapPreview.splitPostBody(body, titles).map(
                (part) => ("id" in part ? ["id", part.id] : ["text", part.text])
            );
        }""",
        body,
    )
    # 検証
    assert parts == expected
    assert "".join(value for _kind, value in parts) == body
