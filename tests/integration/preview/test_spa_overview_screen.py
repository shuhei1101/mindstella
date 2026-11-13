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
from workspace_fixtures import ADOPTED_OPTIONS, MakeEdit, MakeItem

# 概要のタイルの項目 ID
TILE_IDS = (
    "tile-next",
    "tile-goal",
    "tile-review",
    "tile-hold",
    "tile-running",
    "tile-progress",
)

# React の画面へ移るのを待つ上限ミリ秒
NAVIGATE_TIMEOUT_MS = 15_000

# タイルの見出しの右の「すべて表示」（項目の行は data-id を持つ）
SHOW_ALL = "> div > button"

# トップバーのタブの帯
TABBAR = 'nav[aria-label="項目の種類"]'

# 検討事項・タスク・資料を表示しない種類の既定
KINDS_WITHOUT_DECISIONS_TASKS_DOCS = ["research", "terms", "notes", "logs"]

# 納品物のチェックリストの行ごとに、題名・アイコンがチェック済みか（チェックの線を持つか）・題名に取り消し線があるかを読む
DELIVERABLE_STATES_JS = """() => [...document.querySelectorAll('#tile-goal div ul li')].map((li) => ({
    title: li.textContent,
    checked: li.querySelector('svg path') !== null,
    struck: getComputedStyle(li.querySelector('button, span')).textDecorationLine === 'line-through',
}))"""

# 今の画面の表示の設定で、表示する種類を付け外しする（チェックの箱は種類の名前の行に置く）
LEGACY_KIND_CHECKBOX = "aside.settings-drawer .st-kinds label"

# 納品物を 6 件持つ（5 件を超える）ゴール
SIX_DELIVERABLES = [{"title": f"納品物 {number}"} for number in range(1, 7)]

# 次に検討する項目のタイルの見出しと「すべて表示」が、それぞれ何行に折り返しているかと、「すべて表示」が見出しの下の行にあるかを読む
HEAD_ROWS_JS = """() => {
    // 行の数は、文字の枠の縦の中心が半分の高さより離れるたびに 1 行と数える（印のアイコンと文字は高さが違うので、上端では数えない）
    const rows = (element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const rects = [...range.getClientRects()].sort((a, b) => a.top + a.height / 2 - (b.top + b.height / 2));
        return rects.reduce((count, rect, index) => {
            const previous = rects[index - 1];
            const apart = previous === undefined || rect.top + rect.height / 2 - (previous.top + previous.height / 2) > rect.height / 2;
            return apart ? count + 1 : count;
        }, 0);
    };
    const heading = document.querySelector('#h-next');
    const link = document.querySelector('#tile-next > div > button');
    return {
        headingRows: rows(heading),
        linkRows: rows(link),
        linkBelow: link.getBoundingClientRect().top >= heading.getBoundingClientRect().bottom - 1,
    };
}"""

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


def _texts(page: Page, selector: str) -> list[str]:
    """セレクタに当たる要素の文字を上から返す。"""
    return page.eval_on_selector_all(selector, "els => els.map(e => e.textContent)")


def test_tiles_are_laid_out(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """6 つのタイルが項目 ID で引け、概要の題名が h1 になる（正常系）。"""
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
    page.wait_for_selector("#tile-next")
    # 検証
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert page.evaluate("JSON.parse(localStorage.getItem('mindmap-preview')).theme") == "dark"
    assert page.locator('header button[aria-label="ライトに切り替え"]').count() == 1


def test_next_tile(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """次に検討する項目を build が埋め込んだ順に並べ、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    ids = page.eval_on_selector_all("#tile-next button[data-id]", "b => b.map(x => x.dataset.id)")
    impact = page.inner_text('#tile-next button[data-id="D-2"] [title^="影響度"]')
    page.click('#tile-next button[data-id="D-2"]')
    # 検証
    assert ids == ["D-2", "D-5"]
    assert impact == "影響度 大"
    assert _spa_search(page) == {"tab": "decisions", "id": "D-2"}
    assert page.get_by_role("complementary", name="詳細").get_by_role("heading", level=2).inner_text() == "D-2の題"


def test_next_tile_show_all(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """すべて表示で、検討事項の表を 未決定 × 着手可否 = 着手可能 で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    label = page.inner_text(f"#tile-next {SHOW_ALL}")
    page.click(f"#tile-next {SHOW_ALL}")
    # 検証
    assert label == "すべて表示（2 件）"
    assert _spa_search(page) == {
        "tab": "decisions",
        "view": "table",
        "f.status": "未決定",
        "f.ready": "着手可能",
    }


def test_next_tile_when_nothing_to_discuss(
    write_preview: WritePreview, make_item: MakeItem, page: Page
) -> None:
    """次に検討する項目が無いときは、その旨を出して「すべて表示」を置かない（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS))
    # 実行
    open_spa(page, url)
    # 検証
    assert "次に検討する項目はありません。" in page.inner_text("#tile-next")
    assert page.locator(f"#tile-next {SHOW_ALL}").count() == 0


@pytest.mark.parametrize(
    ("width", "link_below"),
    [
        pytest.param(320, True, id="narrowest"),
        pytest.param(389, False, id="narrow_edge"),
        pytest.param(390, False, id="wide_edge"),
    ],
)
def test_next_tile_head_when_narrow(
    write_sample_preview: WriteSamplePreview, page: Page, width: int, link_below: bool
) -> None:
    """見出しと「すべて表示」はそれぞれ 1 行で、収まらない幅 320px では「すべて表示」が見出しの下の行に回る（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.set_viewport_size({"width": width, "height": 568})
    page.wait_for_function(f"innerWidth === {width}")
    result = page.evaluate(HEAD_ROWS_JS)
    # 検証
    assert result == {"headingRows": 1, "linkRows": 1, "linkBelow": link_below}


def test_goal_tile(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """ゴールのフェーズまでの決定済みの数・フェーズごとの棒・納品物のチェックリストを出し、納品物を押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    heading = page.inner_text("#h-goal")
    big = page.inner_text("#tile-goal p.mono").replace(" ", "")
    stages = _texts(page, "#tile-goal > ul li")
    deliverables = _texts(page, "#tile-goal div ul li")
    states = page.evaluate(DELIVERABLE_STATES_JS)
    page.click("#tile-goal div ul li button")
    # 検証
    assert heading == "ゴールまでの進捗"
    assert big == "1/3"
    assert stages == ["目的1/1", "要件0/2"]
    assert deliverables == ["YAML のスキーマ"]
    assert states == [{"title": "YAML のスキーマ", "checked": True, "struck": True}]
    assert _spa_search(page) == {"tab": "docs", "id": "A-1"}


def test_goal_tile_when_deliverable_remaining(
    write_preview: WritePreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    page: Page,
) -> None:
    """ゴールの判定で残っている納品物は、未チェックで取り消し線を付けずに描く（正常系）。"""
    # 準備
    deliverables = [{"title": "YAML のスキーマ", "doc": "A-1"}, {"title": "画面の下書き", "doc": "A-2"}]
    settings = {**sample_settings, "goal": {**sample_settings["goal"], "deliverables": deliverables}}
    url = write_preview(*sample_items, settings=settings)
    # 実行
    open_spa(page, url)
    states = page.evaluate(DELIVERABLE_STATES_JS)
    # 検証
    assert states == [
        {"title": "YAML のスキーマ", "checked": True, "struck": True},
        {"title": "画面の下書き", "checked": False, "struck": False},
    ]


def test_goal_tile_when_no_goal(
    write_preview: WritePreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """ゴールが無いときは、見出しを「フェーズ別の進捗」にし、ゴールが無いことと全フェーズの棒だけを出す（正常系）。"""
    # 準備
    settings = {
        **{key: value for key, value in valid_settings.items() if key != "goal"},
        "phases": ["目的", "要件"],
    }
    url = write_preview(
        make_item("D-1", phase="目的", status="決定済み", options=ADOPTED_OPTIONS),
        make_item("D-2", phase="要件", status="未決定"),
        settings=settings,
    )
    # 実行
    open_spa(page, url)
    # 検証
    assert page.inner_text("#h-goal") == "フェーズ別の進捗"
    assert "ゴールは決まっていません" in page.inner_text("#tile-goal")
    assert page.inner_text("#tile-goal p.mono").replace(" ", "") == "1/2"
    assert _texts(page, "#tile-goal ul li") == ["目的1/1", "要件0/1"]
    assert "納品物" not in page.inner_text("#tile-goal")


def test_goal_tile_deliverables_show_all(
    write_preview: WritePreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """納品物が 5 件を超えたら先頭 5 件を出し、すべて表示で資料を納品物で絞ってカードで開く（正常系）。"""
    # 準備
    settings = {**valid_settings, "goal": {**valid_settings["goal"], "deliverables": SIX_DELIVERABLES}}
    url = write_preview(make_item("D-1"), settings=settings)
    open_spa(page, url)
    # 実行
    shown = _texts(page, "#tile-goal div ul li")
    page.click("#tile-goal button:text-is('すべて表示（6 件）')")
    # 検証
    assert shown == ["納品物 1", "納品物 2", "納品物 3", "納品物 4", "納品物 5"]
    assert _spa_search(page) == {"tab": "docs", "view": "cards", "f.deliverable": "納品物"}


def test_description(
    write_preview: WritePreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """設定の話し合いの概要を題名の上に出し、プレイブックの名前は出さない（正常系）。"""
    # 準備
    description = "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。"
    url = write_preview(make_item("D-1"), settings={**valid_settings, "description": description})
    # 実行
    open_spa(page, url)
    # 検証
    assert page.inner_text("#overview-description") == description
    assert _texts(page, "main#main header > *") == [description, "要件出しのスキル mindmap を設計する"]
    assert "システム開発" not in page.inner_text("main#main header")


def test_description_when_missing(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """話し合いの概要が無い設定では、行を出さず題名がそのまま上に来る（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    # 実行
    open_spa(page, url)
    # 検証
    assert page.locator("#overview-description").count() == 0
    assert _texts(page, "main#main header > *") == ["要件出しのスキル mindmap を設計する"]


def test_small_tiles(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """要見直し・保留・進行中のタスクの件数と名前を出し、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    counts = {
        tile_id: page.inner_text(f"#{tile_id} p.mono")
        for tile_id in ("tile-review", "tile-hold", "tile-running")
    }
    names = {
        tile_id: page.eval_on_selector_all(f"#{tile_id} button[data-id]", "b => b.map(x => x.dataset.id)")
        for tile_id in ("tile-review", "tile-hold", "tile-running")
    }
    page.click('#tile-running button[data-id="T-1"]')
    # 検証
    assert counts == {"tile-review": "1", "tile-hold": "1", "tile-running": "1"}
    assert names == {"tile-review": ["D-3"], "tile-hold": ["D-4"], "tile-running": ["T-1"]}
    assert _spa_search(page) == {"tab": "tasks", "id": "T-1"}


@pytest.mark.parametrize(
    ("tile_id", "expected"),
    [
        pytest.param("tile-review", {"tab": "decisions", "view": "table", "f.status": "要見直し"}, id="review"),
        pytest.param("tile-hold", {"tab": "decisions", "view": "table", "f.status": "保留"}, id="hold"),
        pytest.param("tile-running", {"tab": "tasks", "view": "table", "f.status": "進行中"}, id="running"),
    ],
)
def test_small_tiles_show_all(
    write_sample_preview: WriteSamplePreview, page: Page, tile_id: str, expected: dict[str, str]
) -> None:
    """すべて表示で、表をタイルの状態で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.click(f"#{tile_id} {SHOW_ALL}")
    # 検証
    assert _spa_search(page) == expected


def test_small_tiles_when_empty(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """該当する項目が無いタイルは 0 件と、種類の名前で「〇〇はありません。」を出す（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS))
    # 実行
    open_spa(page, url)
    # 検証
    assert page.inner_text("#tile-review p.mono") == "0"
    assert "要見直しの検討事項はありません。" in page.inner_text("#tile-review")
    assert page.inner_text("#tile-hold p.mono") == "0"
    assert "保留の検討事項はありません。" in page.inner_text("#tile-hold")
    assert page.inner_text("#tile-running p.mono") == "0"
    assert "進行中のタスクはありません。" in page.inner_text("#tile-running")


def test_progress_tile(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """カテゴリー別の進捗をカテゴリー × フェーズで出し、セルを押すと表をカテゴリーとフェーズで絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    totals = _texts(page, "#tile-progress tbody tr td:last-child")
    empty_cells = page.locator("#tile-progress td >> text=—").count()
    page.click('#tile-progress button[aria-label^="画面 の 構成"]')
    # 検証
    assert totals == ["1/2", "0/3"]
    assert empty_cells == 2
    assert _spa_search(page) == {
        "tab": "decisions",
        "view": "table",
        "f.category": "画面",
        "f.phase": "構成",
    }


def test_progress_tile_category_link(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """行の見出しを押すと、表をカテゴリーだけで絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url)
    # 実行
    page.click("#tile-progress th button:text-is('データ構造')")
    # 検証
    assert _spa_search(page) == {"tab": "decisions", "view": "table", "f.category": "データ構造"}


def test_hidden_kinds_keep_tiles(
    write_preview: WritePreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
    page: Page,
) -> None:
    """表示しない種類のタイルは残し、その種類の画面へ移る「すべて表示」と進捗のセルのリンクだけを外す（正常系）。"""
    # 準備
    settings = {**sample_settings, "display": {"visible_kinds": KINDS_WITHOUT_DECISIONS_TASKS_DOCS}}
    url = write_preview(*sample_items, settings=settings, bodies=sample_bodies)
    # 実行
    open_spa(page, url)
    # 検証
    assert page.inner_text("#tile-review p.mono") == "1"
    assert page.locator('#tile-review button[data-id="D-3"]').count() == 1
    assert page.locator('#tile-running button[data-id="T-1"]').count() == 1
    for tile_id in ("tile-next", "tile-review", "tile-hold", "tile-running"):
        assert page.locator(f"#{tile_id} {SHOW_ALL}").count() == 0
    assert page.locator("#tile-progress button").count() == 0
    assert _texts(page, "#tile-progress tbody tr td:last-child") == ["1/2", "0/3"]
    assert page.locator(f'{TABBAR} a[data-tab="decisions"]').count() == 0



@pytest.mark.parametrize(
    ("visible_kinds", "toggled", "tabs", "next_show_all"),
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
    next_show_all: int,
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
    assert page.locator(f"#tile-next {SHOW_ALL}").count() == next_show_all

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
    link = page.locator(f"#tile-next {SHOW_ALL}").bounding_box()
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
    page.wait_for_selector("#tile-progress")
    # 実行
    violations = wcag_violations(page)
    # 検証
    assert violations == []
