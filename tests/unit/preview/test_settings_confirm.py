"""components/settings-confirm.ts（既定の保存の確かめ）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 表示する種類の全て
ALL_KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 保存できなかった理由
ERROR_TEXT = "保存できませんでした。ワークスペースのフォルダに書き込めません（読み取り専用）。"

# 確かめを作って文書に置き、`showModal()` で開いて、見た目を集めて返す JavaScript
CONFIRM_SCRIPT = """(args) => {
    window.confirmCalls = {save: 0, cancel: 0};
    const props = {
        from: {look: args.from.look, kinds: new Set(args.from.kinds)},
        to: {look: args.to.look, kinds: new Set(args.to.kinds)},
        busy: args.busy,
        error: args.error,
        on: {
            save: () => { window.confirmCalls.save += 1; },
            cancel: () => { window.confirmCalls.cancel += 1; },
        },
    };
    const dialog = MindmapPreview.settingsConfirm(props);
    document.body.append(dialog);
    dialog.showModal();
    const buttons = [...dialog.querySelectorAll("button")];
    return {
        text: dialog.textContent,
        focusedLabel: document.activeElement?.textContent.trim() ?? null,
        buttonLabels: buttons.map((button) => button.textContent.trim()),
        buttonsDisabled: buttons.map((button) => button.disabled),
        alerts: [...dialog.querySelectorAll('[role="alert"]')].map((alert) => alert.textContent),
        open: dialog.open,
    };
}"""


@pytest.mark.parametrize(
    (
        "args",
        "expected_texts",
        "expected_focus",
        "expected_all_disabled",
        "expected_alerts",
        "expected_cancel_calls",
    ),
    [
        pytest.param(
            {
                "from": {"look": "deep", "kinds": ALL_KINDS},
                "to": {"look": "glow", "kinds": ALL_KINDS},
            },
            ["ワークスペースの既定を書き換えますか", "深宇宙", "グロウ", "すべて表示", "変えない"],
            "取り消す",
            False,
            [],
            1,
            id="look_changed",
        ),
        pytest.param(
            {
                "from": {"look": "deep", "kinds": ALL_KINDS},
                "to": {"look": "glow", "kinds": ALL_KINDS},
                "busy": True,
            },
            ["保存しています"],
            None,
            True,
            [],
            0,
            id="busy",
        ),
        pytest.param(
            {
                "from": {"look": "deep", "kinds": ALL_KINDS},
                "to": {"look": "glow", "kinds": ALL_KINDS},
                "error": ERROR_TEXT,
            },
            ["保存する"],
            None,
            False,
            [ERROR_TEXT],
            1,
            id="error",
        ),
    ],
)
def test_settings_confirm(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    args: dict[str, Any],
    expected_texts: list[str],
    expected_focus: str | None,
    expected_all_disabled: bool,
    expected_alerts: list[str],
    expected_cancel_calls: int,
) -> None:
    """変える項目と変えない項目、保存している間と失敗を描き分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    arguments: dict[str, Any] = {"busy": False, "error": None, **args}
    # 実行
    observed = preview_page.evaluate(CONFIRM_SCRIPT, arguments)
    preview_page.keyboard.press("Escape")
    cancel_calls = preview_page.evaluate("() => window.confirmCalls.cancel")
    # 検証
    assert all(text in observed["text"] for text in expected_texts)
    assert expected_focus is None or observed["focusedLabel"] == expected_focus
    assert all(observed["buttonsDisabled"]) is expected_all_disabled
    assert observed["alerts"] == expected_alerts
    assert cancel_calls == expected_cancel_calls
