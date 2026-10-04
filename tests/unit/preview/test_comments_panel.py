"""screens/comments.ts（コメントの一覧：左から出すパネル）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 溜めた日時
CREATED = "2026-10-05T03:00:00+00:00"

# レビュー中のコメント（項目あり・消えた項目で箇所が合わない・項目を指さない）
ITEM_1 = {
    "id": "C-1",
    "target": "D-1",
    "target_title": "問い",
    "loc": None,
    "body": "案 A にする",
    "created": CREATED,
}
ITEM_2 = {
    "id": "C-2",
    "target": "D-9",
    "target_title": None,
    "loc": {"kind": "body", "start": 5, "end": 5, "text": "五行目"},
    "body": "ここは言い換える",
    "created": CREATED,
}
ITEM_3 = {
    "id": "C-3",
    "target": None,
    "target_title": None,
    "loc": None,
    "body": "全体に目を通した",
    "created": CREATED,
}

# 一覧を開いている間に消したコメント
REMOVED = {
    "id": "C-4",
    "target": "D-1",
    "target_title": "問い",
    "loc": None,
    "body": "消したコメント",
    "created": CREATED,
}

# 箇所が合わない理由
STALE_REASON = "選んだ文が D-9 の本文の 5〜5 行目にありません"

# 一覧を作って文書に置き、見た目と操作の結果を集めて返す JavaScript
PANEL_SCRIPT = """(args) => {
    const noop = () => {};
    const sent = [];
    const props = {
        items: args.items,
        removed: args.removed,
        checked: new Set(args.checked),
        editing: null,
        stale: new Map(args.stale),
        result: args.result,
        selected: null,
        titleOf: (id) => (id === "D-1" ? "問い" : null),
        free: {
            target: null, body: "", status: "idle",
            on: {input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop},
        },
        on: {
            close: noop, check: noop, checkAll: noop, open: noop, edit: noop, saveEdit: noop,
            cancelEdit: noop, remove: noop, restore: noop, unloc: noop,
            send: () => sent.push("send"),
        },
    };
    const panel = MindmapPreview.commentsPanel(props);
    document.body.append(panel);
    const buttons = [...panel.querySelectorAll("button")];
    const sendButton = buttons.find((button) => button.textContent.trim().startsWith("まとめて送る"));
    const selectAll = [...panel.querySelectorAll('input[type="checkbox"]')].find(
        (box) => (box.getAttribute("aria-label") ?? box.title) === "すべて選ぶ"
    );
    const result = {
        text: panel.textContent,
        sendLabel: sendButton === undefined ? null : sendButton.textContent.trim(),
        sendDisabled: sendButton === undefined ? null : sendButton.disabled,
        selectAllIndeterminate: selectAll === undefined ? null : selectAll.indeterminate,
        alerts: [...panel.querySelectorAll('[role="alert"]')].map((alert) => alert.textContent),
        unlocCount: buttons.filter((button) => button.textContent.trim() === "箇所を外す").length,
        restoreCount: buttons.filter((button) => button.textContent.trim() === "元に戻す").length,
        noTargetIsPlain: [...panel.querySelectorAll("*")].some(
            (element) =>
                element.children.length === 0 &&
                element.textContent.trim() === "項目を指さない" &&
                element.closest("button") === null
        ),
        hasInput: panel.querySelector("textarea") !== null,
    };
    if (sendButton !== undefined) sendButton.click();
    result.sentCalls = sent.length;
    return result;
}"""


def _observe(preview_page: Page, **overrides: Any) -> dict[str, Any]:
    """一覧を作って見た目と送る操作の結果を返す。引数は overrides で上書きする。"""
    args: dict[str, Any] = {
        "items": [ITEM_1, ITEM_2, ITEM_3],
        "removed": [REMOVED],
        "checked": ["C-1", "C-3"],
        "stale": [["C-2", STALE_REASON]],
        "result": None,
    }
    args.update(overrides)
    return preview_page.evaluate(PANEL_SCRIPT, args)


def test_comments_panel(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """送る帯と行を描く（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page)
    # 検証
    assert "2 / 3 件" in observed["text"]
    assert observed["sendLabel"] == "まとめて送る（2 件）"
    assert observed["selectAllIndeterminate"] is True
    assert [STALE_REASON in alert for alert in observed["alerts"]] == [True]
    assert observed["unlocCount"] == 0
    assert observed["noTargetIsPlain"] is True
    assert observed["restoreCount"] == 1


def test_comments_panel_when_empty(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """0 件は空の状態と入力だけ（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, items=[], removed=[], checked=[], stale=[])
    # 検証
    assert "レビュー中のコメントはありません。" in observed["text"]
    assert observed["hasInput"] is True
    assert observed["sendLabel"] is None


@pytest.mark.parametrize(
    ("checked", "result", "expected_text"),
    [
        pytest.param([], None, "送るコメントにチェックを付けてください。", id="nothing_checked"),
        pytest.param(["C-1"], {"kind": "sending"}, "", id="sending"),
    ],
)
def test_comments_panel_when_send_disabled(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    checked: list[str],
    result: dict[str, Any] | None,
    expected_text: str,
) -> None:
    """チェック 0 件と送っている間は送れない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = _observe(preview_page, checked=checked, result=result)
    # 検証
    assert observed["sendDisabled"] is True
    assert observed["sentCalls"] == 0
    assert expected_text in observed["text"]
