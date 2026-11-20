"""画面設計『概要』（タイルの項目 ID で要素を引く）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page
from preview_comment_helpers import COMMENTS_PANEL, THREAD_ROWS
from preview_edit_helpers import (
    PENDING_BUTTON,
    assert_topbar_pending,
    edit_edits,
    edit_items,
)
from preview_fit_helpers import assert_fits_smallest, set_smallest
from preview_fixture_types import OpenPreview, WritePreview, WriteReviewPreview, WriteSamplePreview
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_layout_helpers import assert_bands_stay, assert_page_does_not_scroll, region_metrics
from preview_removed_helpers import REMOVED_IN_V2_BY_TAB
from workspace_fixtures import (
    ADOPTED_OPTIONS,
    CallTool,
    MakeEdit,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
)

# 概要のタイルの項目 ID
TILE_IDS = ("tile-unread", "tile-open", "tile-review", "tile-docs")


def _chips(page: Page) -> list[str]:
    """表の上に並んでいる条件のチップの文字を返す。"""
    return page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")


def _row_ids(page: Page) -> list[str]:
    """表に並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")


def _tile_ids(page: Page, tile_id: str) -> list[str]:
    """タイルに並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all(f"#{tile_id} button[data-id]", "b => b.map(x => x.dataset.id)")


@pytest.fixture
def served_unread_threads(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
) -> tuple[str, Path]:
    """AI の書き込みが未読のオープンの TH-1（古い）・TH-2（新しい）・既読の TH-3・未読のクローズの TH-4 を持つワークスペースの配信の URL とフォルダを返す。"""
    return write_review_preview(
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", read=True, created="2026-10-12T01:00:00+00:00"),
                make_post("TH-1-2", author="ai", seen=False, created="2026-10-12T02:00:00+00:00"),
                summary="古い未読",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", author="ai", seen=False, created="2026-10-12T05:00:00+00:00"),
                summary="新しい未読",
            ),
            make_thread(
                "TH-3",
                make_post("TH-3-1", author="ai", created="2026-10-12T06:00:00+00:00"),
                summary="既読",
            ),
            make_thread(
                "TH-4",
                make_post("TH-4-1", author="ai", seen=False, created="2026-10-12T07:00:00+00:00"),
                status="closed",
                summary="未読のクローズ",
            ),
        ),
    )


def test_tiles_are_laid_out(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """4 つのタイルが項目 ID で引け、概要の題名が h1 になる（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url)
    # 検証
    for tile_id in TILE_IDS:
        assert page.locator(f"#{tile_id}").count() == 1
    assert page.inner_text("main h1") == "要件出しのスキル mindmap を設計する"
    # 前の版のタイルは無い
    for tile_id in ("tile-next", "tile-goal", "tile-hold", "tile-running", "tile-progress"):
        assert page.locator(f"#{tile_id}").count() == 0


def test_unread_tile(served_unread_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """未読の AI の書き込みを持つオープンのスレッドを新しい順に並べ、押すとコメントの一覧でそのスレッドを開く（正常系）。"""
    # 準備
    url, _ = served_unread_threads
    page = open_preview(url)
    page.wait_for_selector("#tile-unread button[data-id]")
    # 実行
    count = page.inner_text("#tile-unread .num")
    ids = _tile_ids(page, "tile-unread")
    first = page.inner_text('#tile-unread button[data-id="TH-2"] .mt')
    page.click('#tile-unread button[data-id="TH-1"]')
    # 検証
    assert count == "2"
    assert ids == ["TH-2", "TH-1"]
    assert first == "TH-2 新しい未読"
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    assert "古い未読" in page.inner_text(f"{COMMENTS_PANEL} .th-head")


def test_unread_tile_show_all(
    served_unread_threads: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """未読の AI の書き込みのすべて表示で、コメントの一覧を開く（正常系）。"""
    # 準備
    url, _ = served_unread_threads
    page = open_preview(url)
    # 実行
    page.click("#tile-unread .t-link")
    # 検証
    page.wait_for_selector(THREAD_ROWS)
    assert page.locator(f"{COMMENTS_PANEL} .th-head").count() == 0


def test_unread_tile_when_exported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しでは、未読の AI の書き込みのタイルを 0 件で描き、「すべて表示」を出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    # 実行
    page = open_preview(out.as_uri())
    page.wait_for_selector("#tile-unread")
    # 検証
    assert page.inner_text("#tile-unread .num") == "0"
    assert page.locator("#tile-unread .t-link").count() == 0


def test_open_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """未決定の検討事項の件数と名前を ID の順に並べ、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    count = page.inner_text("#tile-open .num")
    ids = _tile_ids(page, "tile-open")
    page.click('#tile-open button[data-id="D-5"]')
    # 検証
    assert count == "2"
    assert ids == ["D-2", "D-5"]
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-5の題"


def test_open_tile_show_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """未決定の検討事項のすべて表示で、検討事項の表を 状態 = 未決定 で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    page.click("#tile-open .t-link")
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["状態: 未決定"]
    assert _row_ids(page) == ["D-2", "D-5"]


def test_review_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """要見直しの検討事項の件数と名前を出し、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    count = page.inner_text("#tile-review .num")
    page.click('#tile-review button[data-id="D-3"]')
    # 検証
    assert count == "1"
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"


def test_review_tile_show_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """要見直しのすべて表示で、検討事項の表を 状態 = 要見直し で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    page.click("#tile-review .t-link")
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["状態: 要見直し"]
    assert _row_ids(page) == ["D-3"]


def test_docs_tile(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """確認中の資料の件数と名前を出し、押すと詳細パネルを開く。「すべて表示」で資料を 状態 = 確認中 で絞って開く（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", status="確認中"),
        make_item("A-2", status="下書き"),
        make_item("A-3", status="確認中"),
        bodies={"A-1.mark.md": "本文\n", "A-2.mark.md": "本文\n", "A-3.mark.md": "本文\n"},
    )
    page = open_preview(url)
    # 実行
    count = page.inner_text("#tile-docs .num")
    ids = _tile_ids(page, "tile-docs")
    page.click("#tile-docs .t-link")
    page.wait_for_selector(".doc-card")
    # 検証
    assert count == "2"
    assert ids == ["A-1", "A-3"]
    assert _chips(page) == ["状態: 確認中"]
    assert page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)") == ["A-1", "A-3"]


def test_small_tiles_when_empty(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """該当する項目が無いタイルは 0 件と「〇〇はありません。」を出し、「すべて表示」を置かない（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS))
    # 実行
    page = open_preview(url)
    page.wait_for_selector("#tile-unread")
    # 検証
    empty_texts = {
        "tile-unread": "未読の AI の書き込みはありません。",
        "tile-open": "未決定の検討事項はありません。",
        "tile-review": "要見直しの検討事項はありません。",
        "tile-docs": "確認中の資料はありません。",
    }
    for tile_id, text in empty_texts.items():
        assert page.inner_text(f"#{tile_id} .num") == "0"
        assert page.inner_text(f"#{tile_id} .empty") == text
        assert page.locator(f"#{tile_id} .t-link").count() == 0


def test_description(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """設定の話し合いの概要を題名の上に出す（正常系）。"""
    # 準備
    description = "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。"
    url = write_preview(make_item("D-1"), settings={**valid_settings, "description": description})
    # 実行
    page = open_preview(url)
    # 検証
    assert page.inner_text("#overview-description") == description
    rows = page.eval_on_selector_all("main .hero > *", "els => els.map(e => e.textContent)")
    assert rows == [description, "要件出しのスキル mindmap を設計する"]


def test_description_when_missing(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """話し合いの概要が無い設定では、行を出さず題名がそのまま上に来る（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    # 実行
    page = open_preview(url)
    # 検証
    assert page.locator("#overview-description").count() == 0
    assert page.inner_text("main .hero") == "要件出しのスキル mindmap を設計する"


def test_diff_marks(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間、タイルの項目のタイトルの横に印を文言なしで置く。トップバーに選んだ時点の札を出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "since")
    open_preview(url, "#tab=overview")
    page.wait_for_selector("#tile-open button[data-id]")
    # 検証
    mark = page.locator('#tile-open button[data-id="D-2"] .df-mark')
    assert mark.get_attribute("class") == "df-mark df-chg"
    assert mark.get_attribute("title") == "変更"
    assert page.locator("#tile-open .df-badge").count() == 0
    assert_topbar_history(page)


def test_diff_marks_when_removed(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間、削除した項目を持つ種類のタブに点を付ける。削除した項目はタイルに並べない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=overview")
    page.wait_for_selector("#tile-open")
    # 検証
    dotted = page.eval_on_selector_all(
        "nav.tabbar a.tab:has(.df-dot)", "tabs => tabs.map(t => t.dataset.tab)"
    )
    assert dotted == list(REMOVED_IN_V2_BY_TAB)
    assert page.locator('main#main [data-id="D-3"], main#main [data-id="D-4"]').count() == 0
    assert_topbar_history(page)



# 検討事項・タスク・資料を表示しない種類の既定
KINDS_WITHOUT_DECISIONS_TASKS_DOCS = ["research", "terms", "notes", "logs"]


def test_hidden_kinds_keep_tiles(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
) -> None:
    """表示しない種類のタイルは残し、その種類の画面へ移る「すべて表示」だけを外す（正常系）。"""
    # 準備
    settings = {
        **sample_settings,
        "display": {"visible_kinds": KINDS_WITHOUT_DECISIONS_TASKS_DOCS},
    }
    url = write_preview(*sample_items, settings=settings, bodies=sample_bodies)
    # 実行
    page = open_preview(url)
    # 検証
    # タイルと中の項目は残る
    assert page.inner_text("#tile-review .num") == "1"
    assert page.locator('#tile-review button[data-id="D-3"]').count() == 1
    assert page.locator('#tile-open button[data-id="D-2"]').count() == 1
    # その種類の画面へ移るリンクだけが無い
    for tile_id in ("tile-open", "tile-review"):
        assert page.locator(f"#{tile_id} .t-link").count() == 0
    # タブの帯にもその種類が無い
    assert page.locator('nav.tabbar a[data-tab="decisions"]').count() == 0


def test_visible_kinds_keep_links(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
) -> None:
    """表示する種類の既定が全ての種類のときは、「すべて表示」を出す（正常系）。"""
    # 準備
    settings = {**sample_settings, "display": {"visible_kinds": ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]}}
    url = write_preview(*sample_items, settings=settings, bodies=sample_bodies)
    # 実行
    page = open_preview(url)
    # 検証
    assert page.locator("#tile-review .t-link").count() == 1
    assert page.locator("#tile-open .t-link").count() == 1


def test_region(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ページ全体はスクロールせず、タイルは領域の中で縦にスクロールし、帯は見えたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    page.set_viewport_size({"width": 1280, "height": 520})
    page.wait_for_selector("#tile-open")
    # 実行
    metrics = region_metrics(page)
    # 検証
    assert_page_does_not_scroll(page)
    assert metrics["content"]["scrollHeight"] > metrics["content"]["clientHeight"]
    assert_bands_stay(page)


def test_fit_smallest(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """概要は、幅 320px でページが横にスクロールせず、表のほかに横にあふれる区画が無く、「すべて表示」が表示幅の中にある（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=overview")
    # 実行
    set_smallest(page)
    # 検証
    assert_fits_smallest(page, ("#tile-open .t-link",))


# ===== 編集（トップバーの保存待ち） =====


def test_topbar_pending(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """トップバーに保存待ちのボタンを出し、溜めた件数・開いているか・書き込めない編集の有無を見せる（正常系）。"""
    # 準備
    url, _ = write_edit_preview(*edit_items(make_item, "D"), edits=edit_edits(make_edit, "D"))
    # 実行
    page = open_preview(url)
    page.wait_for_selector(PENDING_BUTTON)
    # 検証
    assert_topbar_pending(page)


def test_topbar_pending_hidden_when_nothing(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """保存待ちの編集が 0 件のときは、保存待ちのボタンを出さない（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"))
    # 実行
    page = open_preview(url)
    page.wait_for_selector("#tile-open")
    # 検証
    assert page.locator(PENDING_BUTTON).count() == 0


def test_topbar_pending_hidden_when_exported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しでは、保存待ちのボタンを出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    # 実行
    page = open_preview(out.as_uri())
    page.wait_for_selector("#tile-open")
    # 検証
    assert page.locator(PENDING_BUTTON).count() == 0
