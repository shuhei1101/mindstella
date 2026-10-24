"""components/selection-comment.ts（選んだ箇所のコメントの入口）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 入口を置いて、置いた場所と選んだ範囲の矩形の位置関係を返す JavaScript
POSITION_SCRIPT = """({viewport, scroller, first, last}) => {
    const rect = ({x, y, width, height}) => new DOMRect(x, y, width, height);
    const pill = MindmapPreview.selectionComment({
        anchor: {first: rect(first), last: rect(last)},
        area: {viewport, scroller: rect(scroller)},
        on: {press: () => {}, close: () => {}},
    });
    document.body.append(pill);
    const box = pill.getBoundingClientRect();
    return {
        below: box.top >= last.y + last.height,
        above: box.bottom <= first.y,
        inside: box.left >= 8 && box.right <= viewport.width - 8,
        side: pill.getAttribute("data-side"),
        tip: pill.getAttribute("data-tip"),
        width: box.width,
        height: box.height,
    };
}"""


@pytest.mark.parametrize(
    ("viewport", "scroller", "first", "last", "expected"),
    [
        pytest.param(
            {"width": 1000, "height": 800},
            {"x": 0, "y": 0, "width": 1000, "height": 800},
            {"x": 100, "y": 300, "width": 200, "height": 20},
            {"x": 100, "y": 340, "width": 150, "height": 20},
            {
                "below": False,
                "above": True,
                "inside": True,
                "side": "above",
                "tip": "start",
                "width": 32,
                "height": 32,
            },
            id="middle",
        ),
        pytest.param(
            {"width": 1000, "height": 800},
            {"x": 0, "y": 60, "width": 1000, "height": 740},
            {"x": 100, "y": 80, "width": 200, "height": 20},
            {"x": 100, "y": 120, "width": 150, "height": 20},
            {
                "below": True,
                "above": False,
                "inside": True,
                "side": "below",
                "tip": "start",
                "width": 32,
                "height": 32,
            },
            id="near_scroller_top",
        ),
        pytest.param(
            {"width": 390, "height": 800},
            {"x": 0, "y": 0, "width": 390, "height": 800},
            {"x": 300, "y": 300, "width": 80, "height": 20},
            {"x": 300, "y": 340, "width": 80, "height": 20},
            {
                "below": False,
                "above": True,
                "inside": True,
                "side": "above",
                "tip": "end",
                "width": 32,
                "height": 32,
            },
            id="right_edge_narrow",
        ),
    ],
)
def test_selection_comment_position(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    viewport: dict[str, int],
    scroller: dict[str, int],
    first: dict[str, int],
    last: dict[str, int],
    expected: dict[str, Any],
) -> None:
    """始まりの上に出し、上に収まらなければ終わりの下、端は内側に収める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    placed = preview_page.evaluate(
        POSITION_SCRIPT,
        {"viewport": viewport, "scroller": scroller, "first": first, "last": last},
    )
    # 検証
    assert placed == expected


def test_selection_comment_keys(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """Enter で押し、Esc で閉じる。名前のツールチップは読み上げから外す（正常系）。"""
    # 準備
    load_preview_scripts()
    labels: Any = preview_page.evaluate(
        """() => {
            window.calls = {press: 0, close: 0};
            const rect = new DOMRect(100, 100, 100, 20);
            const pill = MindmapPreview.selectionComment({
                anchor: {first: rect, last: rect},
                area: {
                    viewport: {width: 1000, height: 800},
                    scroller: new DOMRect(0, 0, 1000, 800),
                },
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
            return {
                name: button.getAttribute("aria-label"),
                tipHidden: pill.querySelector(".sc-tip")?.getAttribute("aria-hidden") ?? null,
            };
        }"""
    )
    # 実行
    preview_page.keyboard.press("Enter")
    preview_page.keyboard.press("Escape")
    # 検証
    assert labels == {"name": "選んだ箇所にコメント", "tipHidden": "true"}
    assert preview_page.evaluate("() => window.calls") == {"press": 1, "close": 1}
