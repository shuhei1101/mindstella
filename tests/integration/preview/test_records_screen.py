"""画面設計『記録の表』（調査・用語集・メモ・会話ログ）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from preview_history_helpers import assert_topbar_history, preselect_diff
from workspace_fixtures import MakeItem


@pytest.mark.parametrize(
    ("tab", "name", "row_id", "headers"),
    [
        pytest.param(
            "research",
            "調査",
            "R-1",
            ["ID", "タイトル", "問い", "結論", "確度", "タグ"],
            id="research",
        ),
        pytest.param(
            "terms",
            "用語集",
            "G-1",
            ["ID", "用語", "意味", "別名", "使わない表記", "タグ"],
            id="terms",
        ),
        pytest.param(
            "notes", "メモ", "N-1", ["ID", "タイトル", "内容", "タグ", "関連"], id="notes"
        ),
        pytest.param(
            "logs", "会話ログ", "L-1", ["ID", "日付", "タイトル", "更新した項目"], id="logs"
        ),
    ],
)
def test_table(
    write_sample_preview: WriteSamplePreview,
    open_preview: OpenPreview,
    tab: str,
    name: str,
    row_id: str,
    headers: list[str],
) -> None:
    """種類ごとの列を持つ表だけを出し（表示形式の切り替えは出さない）、行を押すと詳細を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url, f"#tab={tab}")
    # 検証
    assert page.inner_text("main h1") == name
    assert page.locator(".segment").count() == 0
    assert page.get_attribute(".table-block", "data-kind") == tab
    assert (
        page.eval_on_selector_all(
            "table.grid thead .th-sort", "buttons => buttons.map(b => b.textContent)"
        )
        == headers
    )
    page.click(f'table.grid tr[data-id="{row_id}"] button.row-open')
    page.wait_for_selector("aside.panel.open")
    assert row_id in page.inner_text("aside.panel .panel-kind")


def test_notes_id_button_size(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """メモの表の「関連」の列の ID のボタンは、見えている枠が縦横 24px 以上である（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="決定済み"),
        make_item("N-1", related=["D-1"]),
    )
    page = open_preview(url, "#tab=notes")
    # 実行
    sizes = page.eval_on_selector_all("table.grid td button.idlink", ID_BUTTON_SIZE_JS)
    # 検証
    assert sizes["count"] > 0
    assert sizes["smallest"] >= ID_BUTTON_MIN_SIZE_PX


def test_diff_marks(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """表の行のタイトルの右に印を置く。足したメモには +、トップバーに札を出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "pending")
    open_preview(url, "#tab=notes")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    mark = page.locator('table.grid tbody tr[data-id="N-1"] .row-open + .df-mark')
    assert mark.get_attribute("class") == "df-mark df-new"
    assert mark.get_attribute("title") == "新規"
    assert page.locator('nav.tabbar a[data-tab="notes"] .df-dot').count() == 1
    assert_topbar_history(page)
