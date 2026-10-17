"""components/body-diff-layout-switch.ts（本文の差分の並べ方の切り替え）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 切り替えを作って文書に置き、押す前の見た目を控えてから指定のボタンを押し、知らせた結果を返す JavaScript
SWITCH_SCRIPT = """({layout, press}) => {
    const calls = [];
    const group = MindmapPreview.bodyDiffLayoutSwitch({
        layout,
        on: {change: (...args) => calls.push(args)},
    });
    document.body.append(group);
    const buttons = [...group.querySelectorAll("button")];
    const pressedBefore = Object.fromEntries(
        buttons.map((button) => [button.getAttribute("data-layout"), button.getAttribute("aria-pressed")])
    );
    const labels = Object.fromEntries(
        buttons.map((button) => [button.getAttribute("data-layout"), button.textContent.trim()])
    );
    group.querySelector(`button[data-layout="${press}"]`).click();
    return {
        role: group.getAttribute("role"),
        label: group.getAttribute("aria-label"),
        isSegment: group.classList.contains("segment") && group.classList.contains("sbs-switch"),
        labels,
        pressedBefore,
        calls,
    };
}"""


@pytest.mark.parametrize(
    ("layout", "press", "expected_pressed", "expected_calls"),
    [
        pytest.param(
            "inline",
            "side",
            {"inline": "true", "side": "false"},
            [["side"]],
            id="inline_press_side",
        ),
        pytest.param(
            "inline",
            "inline",
            {"inline": "true", "side": "false"},
            [],
            id="inline_press_inline",
        ),
        pytest.param(
            "side",
            "inline",
            {"inline": "false", "side": "true"},
            [["inline"]],
            id="side_press_inline",
        ),
    ],
)
def test_body_diff_layout_switch(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    layout: str,
    press: str,
    expected_pressed: dict[str, str],
    expected_calls: list[list[Any]],
) -> None:
    """選んでいる方を押した状態で出し、押していない方を押したときだけ知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(SWITCH_SCRIPT, {"layout": layout, "press": press})
    # 検証（組の読み上げの名前とボタンの文言は、どの状態でも同じ）
    assert result["pressedBefore"] == expected_pressed
    assert result["calls"] == expected_calls
    assert result["role"] == "group"
    assert result["label"] == "本文の差分の並べ方"
    assert result["isSegment"] is True
    assert result["labels"] == {"inline": "インライン", "side": "左右に並べる"}
