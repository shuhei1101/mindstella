"""画面設計『概要.tsx』（React のプレビューの概要。タイルの項目 ID で要素を引く）の結合テスト。"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest
from playwright.sync_api import Page, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WritePreview, WriteReviewPreview, WriteSamplePreview
from preview_settings_helpers import open_settings
from preview_spa_helpers import open_spa, wcag_violations
from workspace_fixtures import ADOPTED_OPTIONS, MakeEdit, MakeItem, MakePost, MakeThread

# 概要のタイルの項目 ID
TILE_IDS = ("tile-unread", "tile-open", "tile-review", "tile-docs")

# React の画面へ移るのを待つ上限ミリ秒
NAVIGATE_TIMEOUT_MS = 15_000

# タイルの見出しの右の「すべて表示」（項目の行は data-id を持つ）
SHOW_ALL = "> div > button"

# トップバーのタブの帯
TABBAR = 'nav[aria-label="項目の種類"]'

# 検討事項・タスク・資料を表示しない種類の既定
KINDS_WITHOUT_DECISIONS_TASKS_DOCS = ["research", "terms", "notes", "logs"]

# 今の画面の表示の設定で、表示する種類を付け外しする（チェックの箱は種類の名前の行に置く）
LEGACY_KIND_CHECKBOX = "aside.settings-drawer .st-kinds label"

# 窓・本文の区画のスクロールの大きさと、本文を一番下まで送った後のトップバーとタブの帯の位置を読む
REGION_JS = """() => {
    const main = document.querySelector('main#main');
    main.scrollTop = main.scrollHeight;
    const header = document.querySelector('header').getBoundingClientRect();
    const tabs = document.querySelector('nav[aria-label="項目の種類"]').getBoundingClientRect();
    return {
        pageFits: document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth,
        mainScrolls: main.scrollHeight > main.clientHeight,
        headerTop: header.top,
        tabsBottomInView: tabs.bottom <= innerHeight,
    };
}"""


def _spa_search(page: Page) -> dict[str, str]:
    """React の画面へ移るのを待ち、URL の search の引数を返す。"""
    page.wait_for_url("**/spa/?*tab=*", timeout=NAVIGATE_TIMEOUT_MS)
    return dict(parse_qsl(urlsplit(page.url).query))


def _tile_ids(page: Page, tile_id: str) -> list[str]:
    """タイルに並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all(f"#{tile_id} button[data-id]", "b => b.map(x => x.dataset.id)")


@pytest.fixture
def served_unread_threads(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
) -> str:
    """AI の書き込みが未読のオープンの TH-1（古い）・TH-2（新しい）・既読の TH-3・未読のクローズの TH-4 を持つワークスペースの配信の URL を返す。"""
    url, _ = write_review_preview(
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
    return url


def _texts(page: Page, selector: str) -> list[str]:
    """セレクタに当たる要素の文字を上から返す。"""
    return page.eval_on_selector_all(selector, "els => els.map(e => e.textContent)")


def test_tiles_are_laid_out(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """4 つのタイルが項目 ID で引け、概要の題名が h1 になる（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    open_spa(page, url)
    # 検証
    for tile_id in TILE_IDS:
        assert page.locator(f"#{tile_id}").count() == 1
    assert page.inner_text("main h1") == "要件出しのスキル mindmap を設計する"


def test_topbar(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """トップバーに題名・概要と表示する種類のタブと件数を出し、概要を選んだ見た目にする（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    open_spa(page, url)
    # 検証
    assert page.get_attribute("header span[title]", "title") == "要件出しのスキル mindmap を設計する"
    tabs = page.eval_on_selector_all(f"{TABBAR} a", "links => links.map(a => a.dataset.tab)")
    assert tabs == ["overview", "decisions", "tasks", "research", "docs", "terms", "notes", "logs", "graph"]
    counts = page.eval_on_selector_all(
        f"{TABBAR} a[data-tab] > span", "spans => spans.map(s => s.closest('a').dataset.tab + ':' + s.textContent)"
    )
    assert counts == ["decisions:5", "tasks:3", "research:1", "docs:2", "terms:1", "notes:1", "logs:1"]
    assert page.get_attribute(f'{TABBAR} a[data-tab="overview"]', "aria-current") == "page"


def test_topbar_tab_opens_screen(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """タブを押すと、その種類の画面を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.click(f'{TABBAR} a[data-tab="tasks"]')
    # 検証
    assert _spa_search(page) == {"tab": "tasks"}


def test_topbar_network_opens_graph(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """タブの帯の右端のネットワークの入口を押すと、SPA の中のネットワークを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.click(f'{TABBAR} a[data-tab="graph"]')
    # 検証
    assert _spa_search(page) == {"tab": "graph"}
    assert urlsplit(page.url).path == "/spa/"


def test_topbar_search_opens_dialog(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """トップバーの検索の入口を押すと、SPA の中で全体の検索を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.get_by_role("button", name="すべての項目を検索").click()
    # 検証
    expect(page.get_by_role("dialog", name="すべての項目を検索")).to_be_visible()
    assert page.evaluate("location.pathname + location.search") == "/spa/?search=1"


def test_topbar_theme(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """ライト / ダークを SPA の中で切り替え、今の画面と同じ端末の保存領域に残す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page.emulate_media(color_scheme="light")
    open_spa(page, url)
    # 実行
    page.click('header button[aria-label="ダークに切り替え"]')
    page.reload()
    page.wait_for_selector("#tile-open")
    # 検証
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert page.evaluate("JSON.parse(localStorage.getItem('mindmap-preview')).theme") == "dark"
    assert page.locator('header button[aria-label="ライトに切り替え"]').count() == 1


def test_unread_tile(served_unread_threads: str, page: Page) -> None:
    """未読の AI の書き込みを持つオープンのスレッドを新しい順に並べ、押すとコメントの一覧でそのスレッドを開く（正常系）。"""
    # 準備
    open_spa(page, served_unread_threads)
    page.wait_for_selector("#tile-unread button[data-id]")
    # 実行
    count = page.inner_text("#tile-unread p.mono")
    ids = _tile_ids(page, "tile-unread")
    first = page.inner_text('#tile-unread button[data-id="TH-2"]')
    page.click('#tile-unread button[data-id="TH-1"]')
    # 検証
    assert count == "2"
    assert ids == ["TH-2", "TH-1"]
    assert first == "TH-2 新しい未読"
    page.wait_for_url("**thread=TH-1**", timeout=NAVIGATE_TIMEOUT_MS)
    assert dict(parse_qsl(urlsplit(page.url).query)) == {"panel": "comments", "thread": "TH-1"}


def test_unread_tile_show_all(served_unread_threads: str, page: Page) -> None:
    """未読の AI の書き込みのすべて表示で、コメントの一覧を開く（正常系）。"""
    # 準備
    open_spa(page, served_unread_threads)
    page.wait_for_selector(f"#tile-unread {SHOW_ALL}")
    # 実行
    label = page.inner_text(f"#tile-unread {SHOW_ALL}")
    page.click(f"#tile-unread {SHOW_ALL}")
    # 検証
    assert label == "すべて表示（2 件）"
    page.wait_for_url("**panel=comments**", timeout=NAVIGATE_TIMEOUT_MS)
    assert "thread" not in dict(parse_qsl(urlsplit(page.url).query))
    expect(page.get_by_role("dialog", name="コメント")).to_be_visible()


def test_open_tile(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """未決定の検討事項の件数と名前を ID の順に並べ、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    count = page.inner_text("#tile-open p.mono")
    ids = _tile_ids(page, "tile-open")
    page.click('#tile-open button[data-id="D-5"]')
    # 検証
    assert count == "2"
    assert ids == ["D-2", "D-5"]
    assert _spa_search(page) == {"tab": "decisions", "id": "D-5"}
    assert page.get_by_role("complementary", name="詳細").get_by_role("heading", level=2).inner_text() == "D-5の題"


@pytest.mark.parametrize(
    ("tile_id", "expected"),
    [
        pytest.param("tile-open", {"tab": "decisions", "view": "table", "f.status": "未決定"}, id="open"),
        pytest.param("tile-review", {"tab": "decisions", "view": "table", "f.status": "要見直し"}, id="review"),
    ],
)
def test_decision_tiles_show_all(
    write_sample_preview: WriteSamplePreview, page: Page, tile_id: str, expected: dict[str, str]
) -> None:
    """すべて表示で、検討事項の表をタイルの状態で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.click(f"#{tile_id} {SHOW_ALL}")
    # 検証
    assert _spa_search(page) == expected


def test_review_tile(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """要見直しの検討事項の件数と名前を出し、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    count = page.inner_text("#tile-review p.mono")
    ids = _tile_ids(page, "tile-review")
    page.click('#tile-review button[data-id="D-3"]')
    # 検証
    assert count == "1"
    assert ids == ["D-3"]
    assert _spa_search(page) == {"tab": "decisions", "id": "D-3"}


def test_docs_tile(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """確認中の資料の件数と名前を出し、「すべて表示」で資料を 状態 = 確認中 で絞ってカードで開く（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", status="確認中"),
        make_item("A-2", status="下書き"),
        make_item("A-3", status="確認中"),
        bodies={"A-1.mark.md": "本文\n", "A-2.mark.md": "本文\n", "A-3.mark.md": "本文\n"},
    )
    open_spa(page, url)
    # 実行
    count = page.inner_text("#tile-docs p.mono")
    ids = _tile_ids(page, "tile-docs")
    page.click(f"#tile-docs {SHOW_ALL}")
    # 検証
    assert count == "2"
    assert ids == ["A-1", "A-3"]
    assert _spa_search(page) == {"tab": "docs", "view": "cards", "f.status": "確認中"}


def test_docs_tile_open(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """確認中の資料の行を押すと、資料の詳細パネルを開く（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", status="確認中"), bodies={"A-1.mark.md": "本文\n"})
    open_spa(page, url)
    # 実行
    page.click('#tile-docs button[data-id="A-1"]')
    # 検証
    assert _spa_search(page) == {"tab": "docs", "id": "A-1"}


def test_description(
    write_preview: WritePreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """設定の話し合いの概要を題名の上に出す（正常系）。"""
    # 準備
    description = "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。"
    url = write_preview(make_item("D-1"), settings={**valid_settings, "description": description})
    # 実行
    open_spa(page, url)
    # 検証
    assert page.inner_text("#overview-description") == description
    assert _texts(page, "main#main header > *") == [description, "要件出しのスキル mindmap を設計する"]


def test_description_when_missing(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """話し合いの概要が無い設定では、行を出さず題名がそのまま上に来る（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    # 実行
    open_spa(page, url)
    # 検証
    assert page.locator("#overview-description").count() == 0
    assert _texts(page, "main#main header > *") == ["要件出しのスキル mindmap を設計する"]


def test_small_tiles_when_empty(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """該当する項目が無いタイルは 0 件と「〇〇はありません。」を出し、「すべて表示」を置かない（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS))
    # 実行
    open_spa(page, url)
    page.wait_for_selector("#tile-unread")
    # 検証
    empty_texts = {
        "tile-unread": "未読の AI の書き込みはありません。",
        "tile-open": "未決定の検討事項はありません。",
        "tile-review": "要見直しの検討事項はありません。",
        "tile-docs": "確認中の資料はありません。",
    }
    for tile_id, text in empty_texts.items():
        assert page.inner_text(f"#{tile_id} p.mono") == "0"
        assert text in page.inner_text(f"#{tile_id}")
        assert page.locator(f"#{tile_id} {SHOW_ALL}").count() == 0


def test_hidden_kinds_keep_tiles(
    write_preview: WritePreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
    page: Page,
) -> None:
    """表示しない種類のタイルは残し、その種類の画面へ移る「すべて表示」だけを外す（正常系）。"""
    # 準備
    settings = {**sample_settings, "display": {"visible_kinds": KINDS_WITHOUT_DECISIONS_TASKS_DOCS}}
    url = write_preview(*sample_items, settings=settings, bodies=sample_bodies)
    # 実行
    open_spa(page, url)
    # 検証
    assert page.inner_text("#tile-review p.mono") == "1"
    assert page.locator('#tile-review button[data-id="D-3"]').count() == 1
    assert page.locator('#tile-open button[data-id="D-2"]').count() == 1
    for tile_id in ("tile-open", "tile-review"):
        assert page.locator(f"#{tile_id} {SHOW_ALL}").count() == 0
    assert page.locator(f'{TABBAR} a[data-tab="decisions"]').count() == 0



@pytest.mark.parametrize(
    ("visible_kinds", "toggled", "tabs", "open_show_all"),
    [
        pytest.param(
            None,
            "検討事項",
            ["overview", "tasks", "research", "docs", "terms", "notes", "logs", "graph"],
            0,
            id="override_hides",
        ),
        pytest.param(
            KINDS_WITHOUT_DECISIONS_TASKS_DOCS,
            "検討事項",
            ["overview", "decisions", "research", "terms", "notes", "logs", "graph"],
            1,
            id="override_wins_over_default",
        ),
    ],
)
def test_kinds_override(
    write_preview: WritePreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    page: Page,
    visible_kinds: list[str] | None,
    toggled: str,
    tabs: list[str],
    open_show_all: int,
) -> None:
    """今の画面の表示の設定で保存した端末の上書きを読み、タブとタイルの「すべて表示」をワークスペースの既定より優先して上書きの種類に従わせる（正常系）。"""
    # 準備
    settings = sample_settings if visible_kinds is None else {**sample_settings, "display": {"visible_kinds": visible_kinds}}
    url = write_preview(*sample_items, settings=settings)
    page.goto(url)
    open_settings(page)
    page.locator(LEGACY_KIND_CHECKBOX, has_text=toggled).locator("input").click()
    page.wait_for_function("JSON.parse(localStorage.getItem('mindmap-preview') ?? '{}').kinds !== undefined")
    # 実行
    open_spa(page, url)
    # 検証
    assert page.eval_on_selector_all(f"{TABBAR} a", "links => links.map(a => a.dataset.tab)") == tabs
    assert page.locator(f"#tile-open {SHOW_ALL}").count() == open_show_all

def test_region(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """ページ全体はスクロールせず、タイルは領域の中で縦にスクロールし、帯は見えたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    page.set_viewport_size({"width": 1280, "height": 520})
    page.wait_for_function("innerHeight === 520")
    # 実行
    metrics = page.evaluate(REGION_JS)
    # 検証
    assert metrics == {"pageFits": True, "mainScrolls": True, "headerTop": 0, "tabsBottomInView": True}


def test_fit_smallest(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """幅 320px でページが横にスクロールせず、「すべて表示」が表示幅の中にある（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.set_viewport_size({"width": 320, "height": 568})
    page.wait_for_function("innerWidth === 320")
    # 検証
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth") is True
    link = page.locator(f"#tile-open {SHOW_ALL}").bounding_box()
    assert link is not None
    assert link["x"] >= 0
    assert link["x"] + link["width"] <= 320


def test_topbar_pending(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit, page: Page
) -> None:
    """トップバーに保存待ちのボタンを出し、溜めた件数を見せる。押すと概要を開く（正常系）。"""
    # 準備
    url, _ = write_edit_preview(*edit_items(make_item, "D"), edits=edit_edits(make_edit, "D"))
    open_spa(page, url)
    # 実行
    label = page.get_attribute('header button[aria-label^="保存待ち"]', "aria-label")
    page.click('header button[aria-label^="保存待ち"]')
    # 検証
    assert label == "保存待ち（3 件）"
    page.wait_for_url("**panel=pending*", timeout=NAVIGATE_TIMEOUT_MS)
    assert page.get_by_role("complementary", name="保存待ちの編集").is_visible()


def test_topbar_pending_hidden_when_nothing(write_edit_preview: WriteReviewPreview, make_item: MakeItem, page: Page) -> None:
    """保存待ちの編集が 0 件のときは、保存待ちのボタンを出さない（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"))
    # 実行
    open_spa(page, url)
    # 検証
    assert page.locator('header button[aria-label^="保存待ち"]').count() == 0


def test_topbar_comments(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """コメントのボタンを出し、押すと SPA の中でコメントの一覧を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    label = page.get_attribute('header button[aria-label^="コメント"]', "aria-label")
    page.click('header button[aria-label^="コメント"]')
    # 検証
    assert label == "コメント（レビュー中 0 件）"
    page.wait_for_url("**panel=comments**")
    expect(page.get_by_role("dialog", name="コメント")).to_be_visible()


def test_diff_marks_not_shown(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """差分の表示を React へ移すまで、トップバーに変更履歴の札とタイルの項目の差分の印を出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    open_spa(page, url)
    # 検証
    assert page.locator('header button[aria-label="差分の表示をやめる"]').count() == 0
    assert page.locator(f"{TABBAR} .sr-only:text-is('新規・変更・消した項目があります')").count() == 0


@pytest.mark.parametrize("color_scheme", [pytest.param("light", id="light"), pytest.param("dark", id="dark")])
def test_wcag(write_sample_preview: WriteSamplePreview, page: Page, color_scheme: str) -> None:
    """ライトとダークのどちらでも、概要の画面全体に WCAG 2.1 の A・AA の違反が無い（正常系）。"""
    # 準備
    url = write_sample_preview()
    page.emulate_media(color_scheme=color_scheme)
    open_spa(page, url)
    page.wait_for_selector("#tile-docs")
    # 実行
    violations = wcag_violations(page)
    # 検証
    assert violations == []
