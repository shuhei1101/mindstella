"""画面設計『記録の表.tsx』の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from preview_fixture_types import WritePreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeItem


@pytest.mark.parametrize(
    ("tab", "item", "column"),
    [("research", "R-1", "問い"), ("terms", "G-1", "意味"), ("notes", "N-1", "内容"), ("logs", "L-1", "日付")],
)
def test_table_columns(page: Page, write_preview: WritePreview, make_item: MakeItem, tab: str, item: str, column: str) -> None:
    """種類ごとの列を持つ表だけを出す（正常系）。"""
    url = write_preview(make_item(item, title="記録の題"))
    open_spa(page, url, f"?tab={tab}")
    expect(page.get_by_role("columnheader", name=column)).to_be_visible()
    expect(page.get_by_role("group", name="表示形式")).to_have_count(0)
    page.get_by_role("button", name="記録の題").click()
    expect(page.get_by_role("complementary", name="詳細")).to_contain_text("記録の題")
