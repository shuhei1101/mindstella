"""画面設計『検討事項.tsx』の結合テスト。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, ViewportSize, expect
from preview_spa_helpers import AXE_SCRIPT, open_spa

# 押せる範囲と h1 の axe の規則を当て、違反を返す
AXE_RULES_JS = """async () => {
  const result = await axe.run(document, { runOnly: ["target-size", "page-has-heading-one"] });
  return result.violations.flatMap((rule) => rule.nodes.map((node) => `${rule.id}: ${node.target.join(" ")}`));
}"""


def test_board_is_default(page: Page, spa_preview: str) -> None:
    """既定はボードで、状態の列にカードを並べる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions")
    expect(page.get_by_role("button", name="ボード", exact=True)).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("region", name="未決定")).to_contain_text("記録の形")


def test_table_sort(page: Page, spa_preview: str) -> None:
    """表の見出しを押すと昇順に並べ、URL に残す（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions")
    page.get_by_role("button", name="表", exact=True).click()
    expect(page.get_by_role("cell", name="記録の形")).to_be_visible()
    page.get_by_role("button", name="タイトルで並べ替え").click()
    expect(page.get_by_role("columnheader", name="タイトル")).to_have_attribute("aria-sort", "ascending")
    expect(page).to_have_url(re.compile("sort=title"))


def test_filter_drawer(page: Page, spa_preview: str) -> None:
    """ドロワーの条件で絞り、チップで解除する（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=table&f.status=%E4%BF%9D%E7%95%99")
    expect(page.get_by_role("cell", name="画面の幅")).to_be_visible()
    expect(page.get_by_role("cell", name="記録の形")).to_be_hidden()
    page.get_by_role("button", name="状態: 保留 の条件を解除").click()
    expect(page.get_by_role("cell", name="記録の形")).to_be_visible()


def test_map_nodes(page: Page, spa_preview: str) -> None:
    """マップは elkjs で配置した節を描く（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=map")
    expect(page.locator('[data-node="D-1"]')).to_be_visible()


def test_map_lock(page: Page, spa_preview: str) -> None:
    """開いている節をもう一度押すとロックし、ロック中に余白を押しても選択を解除しない（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=map&id=D-1")
    page.locator('[data-node="D-1"]').wait_for()
    page.wait_for_timeout(500)
    page.locator('[data-node="D-1"]').click()
    expect(page.locator("[data-locked-key]")).to_be_visible()
    page.wait_for_timeout(500)
    page.locator("#decision-map").click(position={"x": 2, "y": 2})
    expect(page).to_have_url(re.compile("id=D-1"))


@pytest.mark.parametrize("search", ["?tab=decisions&view=table", "?tab=decisions", "?tab=tasks", "?tab=docs", "?tab=research"])
@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, {"width": 390, "height": 844}])
def test_list_screens_pass_axe_rules(page: Page, spa_preview: str, search: str, viewport: ViewportSize) -> None:
    """一覧の画面に見出しの h1 があり、表の見出しのボタンが押せる範囲を持つ（正常系）。"""
    page.set_viewport_size(viewport)
    open_spa(page, spa_preview, search)
    page.add_script_tag(path=str(AXE_SCRIPT))
    assert page.evaluate(AXE_RULES_JS) == []
