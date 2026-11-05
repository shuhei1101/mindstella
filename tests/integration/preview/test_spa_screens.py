"""SPA の一覧・詳細・変更履歴・保存待ち・設定の画面を、配信した記録で実ブラウザに開いて確かめる。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, ViewportSize, expect
from preview_fixture_types import WritePreview
from preview_spa_helpers import AXE_SCRIPT, open_spa
from workspace_fixtures import MakeItem

# 押せる範囲と h1 の axe の規則を当て、違反を返す
AXE_RULES_JS = """async () => {
  const result = await axe.run(document, { runOnly: ["target-size", "page-has-heading-one"] });
  return result.violations.flatMap((rule) => rule.nodes.map((node) => `${rule.id}: ${node.target.join(" ")}`));
}"""

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


def test_detail_restores_body_scroll(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文を送った項目を開き直すと、その位置へ戻る。"""
    long_body = "\n\n".join(f"段落 {number}" for number in range(200))
    url = write_preview(make_item("D-1", title="長い本文", status="未決定", body="D-1.md"), make_item("D-2", title="別の項目", status="未決定"), bodies={"D-1.md": long_body})
    open_spa(page, url, "?tab=decisions&id=D-1")
    body = page.locator("aside .panel-body")
    page.get_by_text("段落 199").wait_for()
    body.evaluate("(element) => { element.scrollTop = 600; }")
    page.wait_for_function("sessionStorage.getItem('mindmap-body-scroll') !== null")
    page.goto(page.url.replace("id=D-1", "id=D-2"))
    page.get_by_role("complementary", name="詳細").wait_for()
    page.goto(page.url.replace("id=D-2", "id=D-1"))
    page.get_by_text("段落 199").wait_for()
    # 本文の高さの変化でブラウザが位置を少し補正する
    page.wait_for_function("Math.abs(document.querySelector('aside .panel-body').scrollTop - 600) < 10")


def test_item_add_flow(page: Page, spa_url: str) -> None:
    """項目を追加すると、詳細の場所の入力で溜まり、ボードの先頭に出て、押すと入力を開き直す。"""
    open_spa(page, spa_url, "?tab=tasks")
    page.get_by_role("button", name="タスクの項目を追加").click()
    panel = page.get_by_role("complementary", name="タスクを追加")
    title = panel.get_by_role("textbox", name="タイトル")
    title.fill("足すタスク")
    title.blur()
    card = page.locator("[data-new-id]")
    expect(card).to_contain_text("足すタスク")
    expect(card).to_contain_text("ID は保存で決まる")
    panel.get_by_role("button", name="追加の入力を閉じる").click()
    expect(panel).to_be_hidden()
    card.click()
    expect(page.get_by_role("complementary", name="タスクを追加").get_by_role("textbox", name="タイトル")).to_have_value("足すタスク")


def test_map_lock_and_shake(page: Page, spa_url: str) -> None:
    """開いている節をもう一度押すとロックし、ロック中に余白を押しても選択を解除しない。"""
    open_spa(page, spa_url, "?tab=decisions&view=map&id=D-1")
    page.wait_for_timeout(500)
    node = page.locator('[data-node="D-1"]')
    node.click()
    expect(page.locator("[data-locked-key]")).to_be_visible()
    page.wait_for_timeout(500)
    page.locator("#decision-map").click(position={"x": 2, "y": 2})
    expect(page).to_have_url(re.compile("id=D-1"))


def test_detail_back_disabled_at_start(page: Page, spa_url: str) -> None:
    """パネルで最初に開いた項目では戻るを押せず、移った後は押せる。"""
    open_spa(page, spa_url, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    expect(panel.get_by_role("button", name="前の項目へ戻る")).to_be_disabled()
    panel.get_by_role("button", name="D-2").click()
    expect(panel.get_by_role("button", name="前の項目へ戻る")).to_be_enabled()


@pytest.mark.parametrize("search", ["?tab=decisions&view=table", "?tab=decisions", "?tab=tasks", "?tab=docs", "?tab=research"])
@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, {"width": 390, "height": 844}])
def test_list_screens_pass_axe_rules(page: Page, spa_url: str, search: str, viewport: ViewportSize) -> None:
    """一覧の画面に見出しの h1 があり、表の見出しのボタンが押せる範囲を持つ。"""
    page.set_viewport_size(viewport)
    open_spa(page, spa_url, search)
    page.add_script_tag(path=str(AXE_SCRIPT))
    violations = page.evaluate(AXE_RULES_JS)
    assert violations == []

