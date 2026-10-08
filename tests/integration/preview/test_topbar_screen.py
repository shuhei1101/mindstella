"""全ての画面で共通のトップバーとタブの帯（画面設計の「トップバー」の要素）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
from preview_comment_helpers import COMMENTS_BUTTON, COMMENTS_PANEL, free_comment
from preview_drawer_helpers import DRAWER_OPEN, FILTER_BUTTON, open_drawer
from preview_fixture_types import OpenPreview, WriteReviewPreview, WriteSamplePreview
from preview_history_helpers import assert_topbar_history, preselect_diff
from workspace_fixtures import MakeComment, MakeItem

# タブの帯に並ぶ画面の並び（ネットワークは右端）
TAB_KEYS = [
    "overview",
    "decisions",
    "tasks",
    "research",
    "docs",
    "terms",
    "notes",
    "logs",
    "graph",
]


def test_tabs(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """題名と、種類ごとの件数つきのタブを出す。タブを押すと画面を移って履歴に積む（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    history_length = page.evaluate("history.length")
    # 実行
    tabs = page.eval_on_selector_all(
        "nav.tabbar a",
        "links => links.map(a => [a.dataset.tab, a.querySelector('.count')?.textContent ?? null])",
    )
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_selector(".screen.tasks")
    # 検証
    # トップバーのツール名と、開いたページの題の末尾が mindstella
    assert page.inner_text(".topbar .brand-name") == "mindstella"
    assert page.title() == "要件出しのスキル mindmap を設計する | mindstella"
    assert page.inner_text(".topbar .brand-sub") == "要件出しのスキル mindmap を設計する"
    assert [row[0] for row in tabs] == TAB_KEYS
    assert dict(tabs) == {
        "overview": None,
        "decisions": "5",
        "tasks": "3",
        "research": "1",
        "docs": "2",
        "terms": "1",
        "notes": "1",
        "logs": "1",
        "graph": None,
    }
    assert page.evaluate("history.length") == history_length + 1
    page.go_back()
    page.wait_for_selector(".overview")


def test_tab_keeps_detail_panel(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """タブを押しても、開いている詳細パネルは閉じない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    # 実行
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_selector(".screen.tasks")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-2の題"


def test_theme_is_kept(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ライト / ダークを切り替え、端末の保存領域に残して開き直しても保つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    page.emulate_media(color_scheme="light")
    page.reload()
    page.wait_for_selector("main#main > *")
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
    # 実行
    page.click(".topbar button[data-theme]")
    # 検証
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.reload()
    page.wait_for_selector("main#main > *")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"


@pytest.mark.parametrize(
    "hash_text",
    [
        pytest.param("", id="overview"),
        pytest.param("#tab=decisions&view=table", id="decisions"),
        pytest.param("#tab=tasks", id="tasks"),
        pytest.param("#tab=docs", id="docs"),
        pytest.param("#tab=notes", id="records"),
        pytest.param("#tab=graph", id="graph"),
    ],
)
def test_comments_button(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    hash_text: str,
) -> None:
    """どの画面でも、右端にコメントのボタンを出し、レビュー中の件数を持つ。押すとコメントの一覧を開き、もう一度押すと閉じる（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        make_item("N-1"),
        comments=(
            make_comment("C-1", target="D-1", body="案 A にする"),
            free_comment(make_comment("C-2", body="全体に目を通した")),
        ),
    )
    page = open_preview(url, hash_text)
    button = page.locator(COMMENTS_BUTTON)
    # 実行・検証（開く）
    assert button.get_attribute("aria-label") == "コメント（レビュー中 2 件）"
    assert button.get_attribute("aria-expanded") == "false"
    assert button.locator(".count").inner_text() == "2"
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    assert button.get_attribute("aria-expanded") == "true"
    # 実行・検証（閉じる）
    page.click(COMMENTS_BUTTON)
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    assert button.get_attribute("aria-expanded") == "false"


def test_comments_button_when_zero(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """レビュー中のコメントが 0 件でもコメントのボタンは押せて、件数は 0 を出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"))
    page = open_preview(url)
    # 実行
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    # 検証
    assert page.get_attribute(COMMENTS_BUTTON, "aria-label") == "コメント（レビュー中 0 件）"
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "0"


@pytest.mark.parametrize(
    "hash_text",
    [
        pytest.param("#tab=overview", id="overview"),
        pytest.param("#tab=decisions&view=table", id="decisions"),
        pytest.param("#tab=tasks", id="tasks"),
        pytest.param("#tab=docs", id="docs"),
        pytest.param("#tab=notes", id="notes"),
        pytest.param("#tab=graph", id="graph"),
    ],
)
def test_history_button_on_every_screen(
    write_history_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    hash_text: str,
) -> None:
    """どの画面でも、「変更履歴」のボタンと、差分の表示の間の札・外す × を同じ位置に出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, hash_text)
    page.wait_for_selector(".df-chip")
    # 検証
    assert_topbar_history(page)
    assert page.inner_text(".df-chip-t").endswith("決める")


def test_history_button_when_diff_off(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """差分の表示でなければ「変更履歴」のボタンだけを出し、札とタブの点を出さない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    # 検証
    assert page.get_by_role("button", name="変更履歴").count() == 1
    assert page.locator(".df-chip").count() == 0
    assert page.locator("nav.tabbar .df-dot").count() == 0


def test_diff_off_by_chip(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """札の × を押すと、差分の表示をやめて印と札と点を外し、選んだ時点を端末から消す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector(".df-chip")
    assert page.locator("nav.tabbar .df-dot").count() >= 1
    # 実行
    page.get_by_role("button", name="差分の表示をやめる").click()
    # 検証
    page.wait_for_selector(".df-chip", state="detached")
    assert page.locator("nav.tabbar .df-dot").count() == 0
    assert page.locator("table.grid .df-mark").count() == 0
    saved = page.evaluate("JSON.parse(localStorage.getItem('mindmap-preview')).diffSel ?? null")
    assert saved is None


def test_tab_marks(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間、新規・変更の項目を持つ種類のタブにだけ点を付け、件数は残す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "pending")
    open_preview(url, "#tab=overview")
    page.wait_for_selector(".df-chip")
    # 検証（まだまとめていない変更: タスク T-1 を変え、メモ N-1 を足し、検討事項 D-2 を変えた）
    dotted = page.eval_on_selector_all(
        "nav.tabbar a.tab:has(.df-dot)", "tabs => tabs.map(t => t.dataset.tab)"
    )
    assert dotted == ["decisions", "tasks", "notes"]
    assert page.inner_text('nav.tabbar a[data-tab="tasks"] .count') == "1"
    assert page.inner_text(".df-dot .sr-only") == "新規・変更の項目があります"


@pytest.mark.parametrize("tab", [key for key in TAB_KEYS if key != "overview"])
def test_filter_button_on_item_screens(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, tab: str
) -> None:
    """項目を並べる画面（検討事項・タスク・調査・資料・用語集・メモ・会話ログ・ネットワーク）に絞り込みのボタンを置く（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url, f"#tab={tab}")
    # 検証
    assert page.locator(FILTER_BUTTON).count() == 1


def test_filter_button_not_on_overview(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """概要には絞り込みのボタンを置かない（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url)
    # 検証
    assert page.locator(FILTER_BUTTON).count() == 0


def test_drawer_closes_when_overview_opened(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """絞り込みのドロワーを開いたまま概要のタブへ移ると、ドロワーを閉じ、タスクのタブへ戻っても閉じたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks")
    open_drawer(page)
    # 実行
    page.click('nav.tabbar a[data-tab="overview"]')
    page.wait_for_selector(".overview")
    after_overview = page.locator(DRAWER_OPEN).count()
    # 実行（概要の後にタスクのタブへ戻る）
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_selector(".screen.tasks")
    # 検証
    assert (after_overview, page.locator(DRAWER_OPEN).count()) == (0, 0)


def test_drawer_closes_when_overview_opened_by_history(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """絞り込みのドロワーを開いたまま戻るで概要へ移るとドロワーを閉じ、進むでタスクへ戻ってもドロワーは閉じたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_selector(".screen.tasks")
    open_drawer(page)
    # 実行（戻るで概要へ移る）
    page.go_back()
    page.wait_for_selector(".overview")
    after_back = page.locator(DRAWER_OPEN).count()
    # 実行（進むでタスクへ戻る）
    page.go_forward()
    page.wait_for_selector(".screen.tasks")
    after_forward = page.locator(DRAWER_OPEN).count()
    # 検証
    assert (after_back, after_forward) == (0, 0)


def test_settings_button(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """表示の設定のボタンを、絞り込みの左・ライト / ダークの左に置く。押すとパネルを開閉し、開いている間は選んだ見た目にする（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    button = page.get_by_role("button", name="表示の設定", exact=True)
    # 実行
    order = page.eval_on_selector_all(
        "header.topbar > button",
        "buttons => buttons.map((b) => b.dataset.act ?? b.className)",
    )
    closed = (
        button.get_attribute("aria-expanded"),
        "open" in (button.get_attribute("class") or ""),
    )
    button.click()
    page.wait_for_selector("aside.settings-drawer.open")
    opened = (
        button.get_attribute("aria-expanded"),
        "open" in (button.get_attribute("class") or ""),
    )
    # 検証
    assert order[-4:] == ["settings", "filter", "comments", "top-btn"]
    assert page.inner_text("header.topbar button.settings-btn .label") == "表示の設定"
    assert closed == ("false", False)
    assert opened == ("true", True)
