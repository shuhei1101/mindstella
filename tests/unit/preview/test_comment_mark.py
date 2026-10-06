"""components/comment-mark.ts（コメントの印・印の差し替え）の単体テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 印を置く場所を 3 つ（D-1 は 2 件の印・D-2 は印なし・T-1 は 1 件の印）と、場所の外の要素を持つ、スクロールできる本文。
# 印の中身は部品の出力と同じ形（`.cmk` の中に吹き出し・数字 `.cmk-n`・読み上げの文字 `.sr-only`）
MARK_SCREEN_HTML = """
<div id="screen" style="height: 60px; overflow: auto;">
    <p id="outside">場所の外の要素</p>
    <div class="card"><span id="place-d1" data-comment-target="D-1"><span class="cmk" title="コメント 2 件"><span class="cmk-n" aria-hidden="true">2</span><span class="sr-only">コメント 2 件</span></span></span></div>
    <div class="card"><span id="place-d2" data-comment-target="D-2"></span></div>
    <div class="card"><span id="place-t1" data-comment-target="T-1"><span class="cmk" title="コメント 1 件"><span class="cmk-n" aria-hidden="true">1</span><span class="sr-only">コメント 1 件</span></span></span></div>
    <div style="height: 400px;"></div>
</div>
"""

# 差し替えた後の場所ごとの印の中身を、画面の数字・読み上げの文字・title の組（印が無ければ null）で返す
READ_PLACES_SCRIPT = """() => Object.fromEntries(
    [...document.querySelectorAll("[data-comment-target]")].map((place) => {
        const mark = place.querySelector(".cmk");
        return [
            place.dataset.commentTarget,
            mark === null
                ? null
                : {
                    shown: mark.querySelector(".cmk-n").textContent,
                    spoken: mark.querySelector(".sr-only").textContent,
                    title: mark.title,
                },
        ];
    })
)"""


def test_refresh_comment_marks(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """件数のある場所に印を入れ、無くなった場所を空にする。場所の外とスクロールの位置は変えない（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.set_content(MARK_SCREEN_HTML)
    preview_page.evaluate("""() => { document.getElementById("screen").scrollTop = 30; }""")
    outside_before = preview_page.evaluate("""() => document.getElementById("outside").outerHTML""")
    # 実行
    preview_page.evaluate(
        """() => MindmapPreview.refreshCommentMarks({
            root: document.getElementById("screen"),
            counts: {"D-1": 1, "D-2": 3},
        })"""
    )
    # 検証
    assert preview_page.evaluate(READ_PLACES_SCRIPT) == {
        "D-1": {"shown": "1", "spoken": "コメント 1 件", "title": "コメント 1 件"},
        "D-2": {"shown": "3", "spoken": "コメント 3 件", "title": "コメント 3 件"},
        "T-1": None,
    }
    # T-1 の場所は印の無い空の要素になる
    assert (
        preview_page.evaluate("""() => document.getElementById("place-t1").childElementCount""")
        == 0
    )
    # 場所の外の要素とスクロールの位置は変わらない
    assert (
        preview_page.evaluate("""() => document.getElementById("outside").outerHTML""")
        == outside_before
    )
    assert preview_page.evaluate("""() => document.getElementById("screen").scrollTop""") == 30


@pytest.mark.parametrize(
    ("count", "shown", "spoken"),
    [
        pytest.param(1, "1", "コメント 1 件", id="one"),
        pytest.param(99, "99", "コメント 99 件", id="ninety_nine"),
        pytest.param(100, "99+", "コメント 100 件", id="hundred"),
        pytest.param(128, "99+", "コメント 128 件", id="over_hundred"),
    ],
)
def test_comment_mark_label(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    count: int,
    shown: str,
    spoken: str,
) -> None:
    """99 を超えると画面は「99+」、読み上げは実数（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    mark = preview_page.evaluate(
        """(count) => {
            const element = MindmapPreview.commentMark({count});
            return {
                shown: element.querySelector(".cmk-n").textContent,
                spoken: element.querySelector(".sr-only").textContent,
                title: element.title,
            };
        }""",
        count,
    )
    # 検証
    assert mark == {"shown": shown, "spoken": spoken, "title": spoken}
