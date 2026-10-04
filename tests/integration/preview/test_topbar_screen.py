"""全ての画面で共通のトップバーとタブの帯（画面設計の「トップバー」の要素）の結合テスト。"""

from __future__ import annotations

import pytest
from preview_comment_helpers import COMMENTS_BUTTON, COMMENTS_PANEL, free_comment
from preview_fixture_types import OpenPreview, WriteReviewPreview, WriteSamplePreview
from workspace_fixtures import MakeComment, MakeItem

# タブの帯に並ぶ画面の並び（つながりは右端）
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
