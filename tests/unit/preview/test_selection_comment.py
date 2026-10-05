"""components/selection-comment.ts（選んだ箇所のコメントの入口）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 入口を置いて、置いた場所と選んだ範囲の矩形の位置関係を返す JavaScript
POSITION_SCRIPT = """({viewport, first, last}) => {
    const rect = ({x, y, width, height}) => new DOMRect(x, y, width, height);
    const pill = MindmapPreview.selectionComment({
        anchor: {first: rect(first), last: rect(last)},
        viewport,
        on: {press: () => {}, close: () => {}},
    });
    document.body.append(pill);
    const box = pill.getBoundingClientRect();
    return {
        below: box.top >= last.y + last.height,
        above: box.bottom <= first.y,
        inside: box.left >= 8 && box.right <= viewport.width - 8,
    };
}"""


@pytest.mark.parametrize(
    ("viewport", "first", "last", "expected"),
    [
        pytest.param(
            {"width": 1000, "height": 800},
            {"x": 100, "y": 100, "width": 200, "height": 20},
            {"x": 100, "y": 140, "width": 150, "height": 20},
            {"below": True, "above": False, "inside": True},
            id="middle",
        ),
        pytest.param(
            {"width": 1000, "height": 800},
            {"x": 100, "y": 740, "width": 200, "height": 20},
            {"x": 100, "y": 780, "width": 150, "height": 20},
            {"below": False, "above": True, "inside": True},
            id="near_bottom",
        ),
        pytest.param(
            {"width": 390, "height": 800},
            {"x": 300, "y": 100, "width": 80, "height": 20},
            {"x": 300, "y": 140, "width": 80, "height": 20},
            {"below": True, "above": False, "inside": True},
            id="right_edge_narrow",
        ),
    ],
)
def test_selection_comment_position(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    viewport: dict[str, int],
    first: dict[str, int],
    last: dict[str, int],
    expected: dict[str, bool],
) -> None:
    """下に収まらなければ上、端は内側に収める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    placed = preview_page.evaluate(
        POSITION_SCRIPT, {"viewport": viewport, "first": first, "last": last}
    )
    # 検証
    assert placed == expected


def test_selection_comment_keys(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """Enter で押し、Esc で閉じる（正常系）。"""
    # 準備
    load_preview_scripts()
    name: Any = preview_page.evaluate(
        """() => {
            window.calls = {press: 0, close: 0};
            const rect = new DOMRect(100, 100, 100, 20);
            const pill = MindmapPreview.selectionComment({
                anchor: {first: rect, last: rect},
                viewport: {width: 1000, height: 800},
                on: {
                    press: () => {
                        window.calls.press += 1;
                    },
                    close: () => {
                        window.calls.close += 1;
                    },
                },
            });
            document.body.append(pill);
            const button = pill.matches("button") ? pill : pill.querySelector("button");
            button.focus();
            return button.getAttribute("aria-label");
        }"""
    )
    # 実行
    preview_page.keyboard.press("Enter")
    preview_page.keyboard.press("Escape")
    # 検証
    assert name == "選んだ箇所にコメント"
    assert preview_page.evaluate("() => window.calls") == {"press": 1, "close": 1}
