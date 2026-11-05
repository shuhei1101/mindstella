"""SPA の一覧・詳細・変更履歴・保存待ち・設定の画面を、配信した記録で実ブラウザに開いて確かめる。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from preview_fixture_types import WritePreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeItem

BODY = "## 決め方\n\n本文の段落\n\n| ID | 名前 |\n| --- | --- |\n| A-1 | 表の行 |\n"


@pytest.fixture
def spa_url(write_preview: WritePreview, make_item: MakeItem) -> str:
    """検討事項とタスクを持つワークスペースの配信の URL を返す。"""
    return write_preview(
        make_item("D-1", title="記録の形", status="未決定", options=[{"key": "A", "content": "案 A"}], body="D-1.md"),
        make_item("D-2", title="画面の幅", status="保留", depends_on=["D-1"]),
        make_item("T-1", title="画面を作る", status="進行中"),
        bodies={"D-1.md": BODY},
    )


def test_decisions_board_and_table(page: Page, spa_url: str) -> None:
    """検討事項はボードで開き、表へ切り替えると行と並べ替えの見出しを出す。"""
    open_spa(page, spa_url, "?tab=decisions")
    expect(page.get_by_role("button", name="ボード", exact=True)).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name="表", exact=True).click()
    expect(page.get_by_role("cell", name="記録の形")).to_be_visible()
    page.get_by_role("button", name="タイトルで並べ替え").click()
    expect(page.get_by_role("columnheader", name="タイトル")).to_have_attribute("aria-sort", "ascending")


def test_decisions_map(page: Page, spa_url: str) -> None:
    """マップは elkjs で配置した節を描く。"""
    open_spa(page, spa_url, "?tab=decisions&view=map")
    expect(page.locator('[data-node="D-1"]')).to_be_visible()


def test_detail_panel_draws_body_with_mdmark(page: Page, spa_url: str) -> None:
    """詳細パネルは mdmark で本文を描き、見出しと表を出す。"""
    open_spa(page, spa_url, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    expect(panel.get_by_role("heading", name="決め方")).to_be_visible()
    expect(panel.get_by_role("cell", name="表の行")).to_be_visible()
    expect(panel).to_contain_text("案 A")


def test_detail_edit_stores_pending(page: Page, spa_url: str) -> None:
    """タイトルを書き換えると保存待ちに溜まり、パネルに行が出る。"""
    open_spa(page, spa_url, "?tab=decisions&id=D-1")
    page.get_by_role("button", name="編集する").click()
    title = page.get_by_role("textbox", name="タイトル")
    title.fill("書き換えた題")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    expect(page.get_by_role("complementary", name="保存待ちの編集")).to_contain_text("書き換えた題")


def test_settings_screen(page: Page, spa_url: str) -> None:
    """設定の画面を URL で開ける。"""
    open_spa(page, spa_url, "?tab=settings")
    expect(page.get_by_role("heading", name="ワークスペースの設定")).to_be_visible()
