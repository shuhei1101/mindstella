"""画面設計『変更履歴.tsx』の結合テスト。"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa


def test_select_and_clear(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """時点を選ぶと差分の表示になり、札の解除で戻す（正常系）。"""
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    page.get_by_role("button", name="変更履歴").click()
    page.get_by_role("dialog").get_by_role("button").filter(has_text="前回開いてから").click()
    expect(page).to_have_url(re.compile("diff=since"))
    open_spa(page, url, "?tab=decisions&diff=V-2&id=D-1")
    expect(page.get_by_role("complementary", name="詳細")).to_contain_text("新しい段落を足しました")
