"""コメントの印の結合テストが共有する値と、画面の印を読む関数。"""

from __future__ import annotations

from playwright.sync_api import Page

__all__ = [
    "MARK_TIMEOUT_MS",
    "SCREEN_MARKS",
    "marks_of",
]

# 画面ごとの、項目の ID → 画面の数字（`write_commented_preview` のコメントのうち、既定でその画面に並ぶ項目だけ）
SCREEN_MARKS = {
    "decisions": {"D-2": "2", "D-3": "1"},
    "tasks": {"T-1": "1"},
    "docs": {"A-1": "1", "A-2": "1"},
    "research": {"R-1": "1"},
}

# 印が描き替わるのを待つ上限ミリ秒
MARK_TIMEOUT_MS = 10_000

# 印を置く場所ごとに、項目の ID → 画面の数字（印が無い場所は含めない）を返す（`root` の中だけを見る）
MARKS_SCRIPT = """(selector) => Object.fromEntries(
    [...document.querySelectorAll(`${selector} [data-comment-target]`)]
        .filter((place) => place.querySelector('.cmk') !== null)
        .map((place) => [place.dataset.commentTarget, place.querySelector('.cmk-n').textContent])
)"""


def marks_of(page: Page, selector: str = "main#main") -> dict[str, str]:
    """画面の中の印を、項目の ID → 画面の数字で返す。"""
    result: dict[str, str] = page.evaluate(MARKS_SCRIPT, selector)
    return result
