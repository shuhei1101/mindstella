"""screens/decisions.ts（検討事項の画面）の単体テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem


# 画面を描く窓の幅と高さ（px）
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# 消した項目の帯の読み上げ名
REMOVED_BAND_NAME = "この時点で消した項目"


@pytest.mark.parametrize(
    ("view", "filters", "list_selector", "ready_selector"),
    [
        pytest.param("board", {}, ".board", ".board .card", id="board"),
        pytest.param("table", {}, ".table-block", "tbody tr[data-id]", id="table"),
        pytest.param(
            "board",
            {"status": ["決定済み"]},
            ".board",
            ".board .card",
            id="board_filtered",
        ),
    ],
)
def test_decisions_screen_when_removed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    view: str,
    filters: dict[str, list[str]],
    list_selector: str,
    ready_selector: str,
) -> None:
    """消した検討事項を、表示形式と絞り込みによらず一覧の上の帯に出す（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item("D-1", status="未決定"),
            make_item("D-2", status="決定済み", answer="案 A"),
        ]
    )
    removed = [{"id": "D-53", "kind": "decision", "title": "消した検討事項"}]
    preview_page.set_viewport_size({"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT})
    load_preview_scripts()
    # 実行
    preview_page.evaluate(
        """({data, view, filters, removed}) => {
            const index = MindmapPreview.buildIndex(data);
            const noop = () => {};
            const screen = MindmapPreview.decisionsScreen({
                index,
                route: {tab: "decisions", view, id: null, full: false, filters: {}, heading: null},
                on: {
                    open: noop,
                    view: noop,
                    filter: noop,
                    closeDrawer: noop,
                },
                filters,
                drawerOpen: false,
                removed,
            });
            document.body.append(screen);
        }""",
        {"data": data, "view": view, "filters": filters, "removed": removed},
    )
    preview_page.wait_for_selector(ready_selector)
    # 検証
    band = preview_page.get_by_role("region", name=REMOVED_BAND_NAME)
    expect(band).to_have_count(1)
    expect(band).to_contain_text("D-53")
    # 帯は一覧より前にある
    assert band.evaluate(
        "(band, selector) => (band.compareDocumentPosition(document.querySelector(selector))"
        " & Node.DOCUMENT_POSITION_FOLLOWING) !== 0",
        list_selector,
    )
    # 消した検討事項は、一覧（ボードの列・表の行）には出ない
    expect(preview_page.locator(list_selector).filter(has_text="D-53")).to_have_count(0)
