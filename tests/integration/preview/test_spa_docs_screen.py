"""画面設計『資料.tsx』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from preview_fixture_types import WritePreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeItem


def test_cards_put_deliverable_first(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """既定はカードで、納品物を先頭に並べる（正常系）。"""
    url = write_preview(make_item("A-1", title="普通の資料"), make_item("A-2", title="納品物の資料", deliverable=True))
    open_spa(page, url, "?tab=docs")
    expect(page.get_by_role("heading", level=3).first).to_have_text("納品物の資料")


def test_board_and_table(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """ボードは状態の列、表は形式の列を持つ（正常系）。"""
    url = write_preview(make_item("A-1", title="普通の資料", body="A-1.md"), bodies={"A-1.md": "本文"})
    open_spa(page, url, "?tab=docs&view=board")
    expect(page.locator("[data-id='A-1']")).to_be_visible()
    open_spa(page, url, "?tab=docs&view=table")
    expect(page.get_by_role("cell", name="MD", exact=True)).to_be_visible()
