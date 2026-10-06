"""タスクをボードで見る（状態ごとの列のボードで見て、ドロワーで絞り、カードから詳細を開く）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from preview_helpers import (
    OpenPreview,
    ServePreview,
    badge_text,
    bands_stay_on_top,
    close_drawer,
    open_drawer,
    page_scroll_overflow,
    row_ids,
    toggle_value,
)
from workspace_fixtures import MakeItem

# ボードの列の並び（タスクの状態の順）
TASK_COLUMNS = ["未着手", "進行中", "保留", "完了", "中止"]


def test_normal(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """状態ごとの 5 列にタスクを並べ、カードから進める検討事項を読み、表に切り替える（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("D-3", status="要見直し"),
        make_item("T-1", status="未着手"),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("T-3", status="保留"),
        make_item("T-4", status="完了"),
        make_item("T-5", status="中止"),
        settings=valid_settings,
    )
    # 実行
    page = open_preview(url, "#tab=tasks")
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        "cols => cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)])",
    )
    # 検証（ボード）
    assert [name for name, _ in columns] == TASK_COLUMNS
    assert dict(columns) == {
        "未着手": ["T-1"],
        "進行中": ["T-2"],
        "保留": ["T-3"],
        "完了": ["T-4"],
        "中止": ["T-5"],
    }
    # T-2 の詳細パネルに、進める検討事項として D-3 がある
    page.click('.board button.card[data-id="T-2"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "T-2の題"
    targets = page.eval_on_selector_all(
        "aside.panel .d-sec:has(h3:text-is('進める検討事項')) button.idlink",
        "buttons => buttons.map(b => b.textContent)",
    )
    assert targets == ["D-3"]
    # 表に切り替えると 5 行ある
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    assert row_ids(page) == ["T-1", "T-2", "T-3", "T-4", "T-5"]


def _board_columns(page: Page) -> dict[str, list[str]]:
    """ボードの列を、状態ごとのカードの ID の並びで返す。"""
    return page.eval_on_selector_all(
        ".board section.board-col",
        "cols => Object.fromEntries(cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)]))",
    )


def _column_counts(page: Page) -> dict[str, int]:
    """ボードの列の見出しの件数を、状態ごとに返す。"""
    return page.eval_on_selector_all(
        ".board section.board-col",
        "cols => Object.fromEntries(cols.map(c => [c.getAttribute('aria-label'), Number(c.querySelector('h3 .n').textContent)]))",
    )


def test_normal_when_filtered(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """ドロワーのタグで話題を選び、種類を足して、条件に合うタスクだけのボードにする（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("T-1", kind="作業", status="未着手", tags=["保存"]),
        make_item("T-2", kind="調査", status="進行中", tags=["保存"]),
        make_item("T-3", kind="作業", status="完了", tags=["通知"]),
        settings=valid_settings,
    )
    page = open_preview(url, "#tab=tasks")
    page.wait_for_selector(".board")
    # 実行（タグ「保存」を選ぶ）
    open_drawer(page)
    toggle_value(page, "tags", "保存")
    page.wait_for_function("document.querySelectorAll('.board .card').length === 2")
    tagged = _board_columns(page)
    # 実行（種類に「調査」を足す）
    toggle_value(page, "kind", "調査")
    page.wait_for_function("document.querySelectorAll('.board .card').length === 1")
    both = _board_columns(page)
    counts = _column_counts(page)
    close_drawer(page)
    # 検証
    assert tagged == {"未着手": ["T-1"], "進行中": ["T-2"], "保留": [], "完了": [], "中止": []}
    # 絞っても 5 列が残り、各列の件数が絞った後のカードの数に合う
    assert both == {"未着手": [], "進行中": ["T-2"], "保留": [], "完了": [], "中止": []}
    assert counts == {"未着手": 0, "進行中": 1, "保留": 0, "完了": 0, "中止": 0}
    assert badge_text(page) == "2"


# 未着手の列が画面の高さに収まらない件数
OVERFLOW_TASK_COUNT = 40

# 5 列が幅に収まらず、横にも送る表示の幅（px）と高さ（px）
OVERFLOW_WIDTH = 768
OVERFLOW_HEIGHT = 800

# ボードの上でホイールを回す量（px）
WHEEL_DELTA_PX = 600


def test_normal_when_overflowing(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """未着手の列が画面の高さに収まらず、5 列が幅にも収まらないとき、ボードは帯の下の領域の中で縦にも横にも送れ、ページ全体はスクロールしない（正常系）。"""
    # 準備
    url = serve_preview(
        *(make_item(f"T-{number}", status="未着手") for number in range(1, OVERFLOW_TASK_COUNT + 1)),
        make_item("T-41", status="進行中"),
        make_item("T-42", status="保留"),
        make_item("T-43", status="完了"),
        make_item("T-44", status="中止"),
        settings=valid_settings,
    )
    # 実行（タスクのタブを開く）
    page = open_preview(url, "#tab=tasks", width=OVERFLOW_WIDTH, height=OVERFLOW_HEIGHT)
    page.wait_for_selector(".board .card")
    before = page_scroll_overflow(page)
    # 検証（開いた直後、ページ全体に縦・横ともスクロールが無い）
    assert before["vertical"] == 0
    assert before["horizontal"] == 0
    # 実行（ボードの上でホイールを回して下へ送る）
    box = page.locator(".board").bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.wheel(0, WHEEL_DELTA_PX)
    page.wait_for_function("document.querySelector('.board').scrollTop > 0")
    after_wheel = page_scroll_overflow(page)
    # 検証（ボードの中だけを送り、帯が見えたままで、ページ全体の縦のスクロールの位置は 0）
    assert after_wheel["scrollY"] == 0
    assert bands_stay_on_top(page) is True
    # 実行（ボードを右端まで横に送る）
    page.evaluate("document.querySelector('.board').scrollLeft = document.querySelector('.board').scrollWidth")
    page.wait_for_function(
        "document.querySelector('.board').scrollLeft > 0"
    )
    # 検証（ボードの中を縦と横に送れ、横に送ると中止の列が画面に入る）
    scroll = page.evaluate(
        """() => {
            const board = document.querySelector('.board');
            const last = document.querySelector('.board section.board-col[aria-label="中止"]').getBoundingClientRect();
            return {
                vertical: board.scrollHeight > board.clientHeight,
                horizontal: board.scrollWidth > board.clientWidth,
                lastInView: last.left >= 0 && last.right <= innerWidth,
            };
        }"""
    )
    assert scroll == {"vertical": True, "horizontal": True, "lastInView": True}
    assert page_scroll_overflow(page)["scrollY"] == 0
    # 実行（最後のカード T-40 を押す。未着手の列は左端にあるので、ボードを左端へ戻して押す）
    page.evaluate("document.querySelector('.board').scrollLeft = 0")
    page.click('.board button.card[data-id="T-40"]')
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "T-40の題"
