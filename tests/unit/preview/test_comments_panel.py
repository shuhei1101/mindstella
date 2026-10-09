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

# 詳細パネルで消した、D-1 へのコメント
REMOVED_C2 = {
    "id": "C-2",
    "target": "D-1",
    "target_title": "問い",
    "loc": None,
    "body": "消した後に戻すコメント",
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


def test_comments_panel(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
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
        pytest.param(
            [], None, "送るコメントにチェックを付けてください。", id="nothing_checked"
        ),
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


# 部品の戻り値（要素・要素の配列・DocumentFragment のどれでも）を文書に置いて、その入れ物を返す関数
MOUNT_FUNCTION = """const mount = (value) => {
    const host = document.createElement("div");
    host.append(...[value].flat());
    document.body.append(host);
    return host;
};"""

# 行の右上の「修正」「削除」を描き、2 つのボタンを押して、見た目と呼ばれた ID を集める
ROW_ACTIONS_SCRIPT = (
    MOUNT_FUNCTION
    + """
({item, focus}) => {
    const calls = {edit: [], remove: []};
    const host = mount(MindmapPreview.reviewRowActions({
        item,
        focus,
        on: {edit: (id) => calls.edit.push(id), remove: (id) => calls.remove.push(id)},
    }));
    const buttons = [...host.querySelectorAll("button")];
    const buttonInfo = buttons.map((button) => ({
        label: button.getAttribute("aria-label"),
        title: button.title,
        focus: button.getAttribute("data-focus"),
    }));
    buttons.forEach((button) => button.click());
    return {buttonInfo, calls};
}"""
)


@pytest.mark.parametrize(
    ("item", "focus", "expected"),
    [
        pytest.param(
            ITEM_1,
            "detail-",
            {
                "buttonInfo": [
                    {
                        "label": "D-1 へのコメントを修正",
                        "title": "修正",
                        "focus": "detail-edit-open:C-1",
                    },
                    {
                        "label": "D-1 へのコメントを削除",
                        "title": "削除",
                        "focus": "detail-remove:C-1",
                    },
                ],
                "calls": {"edit": ["C-1"], "remove": ["C-1"]},
            },
            id="targeted_in_detail",
        ),
        pytest.param(
            ITEM_3,
            "",
            {
                "buttonInfo": [
                    {
                        "label": "項目を指さないコメントを修正",
                        "title": "修正",
                        "focus": "edit-open:C-3",
                    },
                    {
                        "label": "項目を指さないコメントを削除",
                        "title": "削除",
                        "focus": "remove:C-3",
                    },
                ],
                "calls": {"edit": ["C-3"], "remove": ["C-3"]},
            },
            id="untargeted_in_list",
        ),
    ],
)
def test_review_row_actions(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    item: dict[str, Any],
    focus: str,
    expected: dict[str, Any],
) -> None:
    """読み上げの名前と `title` と `data-focus` を付けて、押すと ID を知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(ROW_ACTIONS_SCRIPT, {"item": item, "focus": focus})
    # 検証
    assert observed == expected


# 行の本文の書き換えを描き、入力欄に入れた中身で操作して、ボタンの並びと呼ばれた引数と理由を集める
EDIT_FORM_SCRIPT = (
    MOUNT_FUNCTION
    + """
({item, body, error, typed, action}) => {
    const calls = {save: [], cancel: 0};
    const host = mount(MindmapPreview.reviewEditForm({
        item,
        body,
        error,
        focus: "",
        on: {
            saveEdit: (id, text) => calls.save.push([id, text]),
            cancelEdit: () => { calls.cancel += 1; },
        },
    }));
    const field = host.querySelector("textarea");
    const buttons = [...host.querySelectorAll("button")];
    const labels = buttons.map((button) => button.textContent.trim());
    if (typed !== null) field.value = typed;
    const named = (label) => buttons.find((button) => button.textContent.trim() === label);
    let escapePrevented = null;
    if (action === "save") named("修正").click();
    if (action === "cancel") named("キャンセル").click();
    if (action === "escape") {
        const event = new KeyboardEvent("keydown", {key: "Escape", bubbles: true, cancelable: true});
        field.dispatchEvent(event);
        escapePrevented = event.defaultPrevented;
    }
    return {
        labels,
        calls,
        escapePrevented,
        value: field.value,
        invalid: field.getAttribute("aria-invalid"),
        alerts: [...host.querySelectorAll('[role="alert"]')].map((alert) => alert.textContent),
    };
}"""
)


@pytest.mark.parametrize(
    ("typed", "action", "expected_calls", "expected_escape_prevented"),
    [
        pytest.param(
            "案 A に決める",
            "save",
            {"save": [["C-1", "案 A に決める"]], "cancel": 0},
            None,
            id="save",
        ),
        pytest.param(None, "cancel", {"save": [], "cancel": 1}, None, id="cancel"),
        pytest.param(None, "escape", {"save": [], "cancel": 1}, True, id="escape"),
    ],
)
def test_review_edit_form(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    typed: str | None,
    action: str,
    expected_calls: dict[str, Any],
    expected_escape_prevented: bool | None,
) -> None:
    """文言と、送る・捨てる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        EDIT_FORM_SCRIPT,
        {"item": ITEM_1, "body": None, "error": None, "typed": typed, "action": action},
    )
    # 検証
    assert observed["labels"] == ["キャンセル", "修正"]
    assert observed["calls"] == expected_calls
    assert observed["escapePrevented"] is expected_escape_prevented


@pytest.mark.parametrize(
    (
        "body",
        "error",
        "typed",
        "action",
        "expected_value",
        "expected_reason",
        "expected_invalid",
    ),
    [
        pytest.param(
            None,
            None,
            "   ",
            "save",
            "   ",
            "コメントを入れてから直してください。",
            "true",
            id="blank_only",
        ),
        pytest.param(
            "案 A に決める",
            "サーバーが止まっています。立ち上げ直してから直してください。",
            None,
            "none",
            "案 A に決める",
            "サーバーが止まっています。立ち上げ直してから直してください。",
            None,
            id="save_failed",
        ),
    ],
)
def test_review_edit_form_when_blank_or_error(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    body: str | None,
    error: str | None,
    typed: str | None,
    action: str,
    expected_value: str,
    expected_reason: str,
    expected_invalid: str | None,
) -> None:
    """空白だけは送らず、直せなかった理由と中身を出す（異常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        EDIT_FORM_SCRIPT,
        {
            "item": ITEM_1,
            "body": body,
            "error": error,
            "typed": typed,
            "action": action,
        },
    )
    # 検証
    assert observed["calls"]["save"] == []
    assert observed["value"] == expected_value
    assert expected_reason in "".join(observed["alerts"])
    assert observed["invalid"] == expected_invalid


# 消した行を描き、「元に戻す」を押して、見た目と呼ばれた ID を集める
REMOVED_ROW_SCRIPT = (
    MOUNT_FUNCTION
    + """
({item, focus}) => {
    const restored = [];
    const host = mount(MindmapPreview.removedReviewRow({
        item,
        focus,
        on: {restore: (id) => restored.push(id)},
    }));
    const button = [...host.querySelectorAll("button")].find(
        (candidate) => candidate.textContent.trim() === "元に戻す"
    );
    const result = {
        status: [...host.querySelectorAll('[role="status"]')].map((status) => status.textContent.trim()),
        restoreFocus: button === undefined ? null : button.getAttribute("data-focus"),
        rowClass: host.querySelector("li.row.removed") === null ? null : "row removed",
    };
    if (button !== undefined) button.click();
    result.restored = restored;
    return result;
}"""
)


def test_removed_review_row(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """消した旨と元に戻すを出し、押すと ID を知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        REMOVED_ROW_SCRIPT, {"item": REMOVED_C2, "focus": "detail-"}
    )
    # 検証
    assert observed == {
        "status": ["コメントを削除しました。"],
        "restoreFocus": "detail-restore:C-2",
        "rowClass": "row removed",
        "restored": ["C-2"],
    }
