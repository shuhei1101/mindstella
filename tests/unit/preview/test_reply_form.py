"""components/reply-form.ts（返信の入力の部品）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 部品の状態を見て返す JavaScript（部品を作って文書に置き、ラベル・入力欄・ボタン・結果の要素の属性を集める）
OBSERVE_SCRIPT = """(props) => {
    const noop = () => {};
    const form = MindmapPreview.replyForm({...props, on: {input: noop, save: noop}});
    document.body.append(form);
    const textarea = form.querySelector("textarea");
    const submit = form.querySelector('button[type="submit"]');
    const status = form.querySelector('[role="status"]');
    return {
        submitDisabled: submit.disabled,
        readOnly: textarea.readOnly,
        labelVisible: [...form.querySelectorAll("label")].some(
            (label) => label.textContent.trim() === "返信" && label.offsetParent !== null
        ),
        describedByStatus: status !== null && textarea.getAttribute("aria-describedby") === status.id,
        statusText: status === null ? "" : status.textContent,
    };
}"""

# 返信を溜められない状態の入力欄（空・溜めている間）の期待値
BLOCKED = {"labelVisible": True, "describedByStatus": True}


@pytest.mark.parametrize(
    ("props", "expected", "expected_text"),
    [
        pytest.param(
            {"thread": "TH-2", "body": ""},
            {**BLOCKED, "submitDisabled": True, "readOnly": False},
            "",
            id="empty",
        ),
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい"},
            {**BLOCKED, "submitDisabled": False, "readOnly": False},
            "",
            id="typing",
        ),
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい", "status": "saving"},
            {**BLOCKED, "submitDisabled": True, "readOnly": True},
            "",
            id="saving",
        ),
        pytest.param(
            {"thread": "TH-2", "body": "", "status": "saved", "count": 3},
            BLOCKED,
            "レビューに追加しました（レビュー中 3 件）。",
            id="saved",
        ),
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい", "status": "failed", "detail": None},
            BLOCKED,
            "レビューに追加できませんでした。サーバーが止まっています。立ち上げ直してから追加してください。",
            id="failed_unreachable",
        ),
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい", "status": "failed", "detail": "スレッドがありません"},
            BLOCKED,
            "レビューに追加できませんでした。スレッドがありません",
            id="failed_detail",
        ),
    ],
)
def test_reply_form(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    expected: dict[str, Any],
    expected_text: str,
) -> None:
    """状態ごとの入力欄と結果（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(OBSERVE_SCRIPT, props)
    # 検証
    assert expected.items() <= observed.items()
    assert expected_text in observed["statusText"]


# キーを押して、溜める操作の引数と、外へ伝わったキーを集める JavaScript
KEYS_SCRIPT = """({props, key, ctrl, composing}) => {
    const saved = [];
    const form = MindmapPreview.replyForm({
        ...props,
        on: {input: () => {}, save: (...args) => saved.push(args)},
    });
    const parent = document.createElement("div");
    let parentKeydowns = 0;
    parent.addEventListener("keydown", () => {
        parentKeydowns += 1;
    });
    parent.append(form);
    document.body.append(parent);
    const textarea = form.querySelector("textarea");
    textarea.focus();
    textarea.dispatchEvent(
        new KeyboardEvent("keydown", {
            key, ctrlKey: ctrl, isComposing: composing, bubbles: true, cancelable: true,
        })
    );
    return {saved, parentKeydowns, focused: document.activeElement === textarea};
}"""


@pytest.mark.parametrize(
    ("props", "key", "ctrl", "composing", "expected_saved", "max_parent_keydowns", "expected_focused"),
    [
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい"},
            "Enter",
            True,
            False,
            [["TH-2", "起票してよい"]],
            1,
            True,
            id="ctrl_enter",
        ),
        pytest.param({"thread": "TH-2", "body": "  "}, "Enter", True, False, [], 1, True, id="blank"),
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい", "status": "saving"},
            "Enter",
            True,
            False,
            [],
            1,
            True,
            id="saving",
        ),
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい"},
            "Enter",
            True,
            True,
            [],
            1,
            True,
            id="composing",
        ),
        pytest.param(
            {"thread": "TH-2", "body": "起票してよい"},
            "Escape",
            False,
            False,
            [],
            0,
            False,
            id="escape",
        ),
    ],
)
def test_reply_form_when_keys(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    props: dict[str, Any],
    key: str,
    ctrl: bool,
    composing: bool,
    expected_saved: list[list[str]],
    max_parent_keydowns: int,
    expected_focused: bool,
) -> None:
    """Ctrl+Enter で溜め、空・溜めている間・変換中は溜めず、Esc は外へ伝えない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        KEYS_SCRIPT, {"props": props, "key": key, "ctrl": ctrl, "composing": composing}
    )
    # 検証
    assert observed["saved"] == expected_saved
    assert observed["parentKeydowns"] <= max_parent_keydowns
    assert observed["focused"] is expected_focused
