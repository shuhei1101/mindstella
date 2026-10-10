"""画面設計『記録の表』（調査・用語集・メモ・会話ログ）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
from preview_drawer_helpers import (
    DRAWER,
    badge_text,
    checked_values,
    chip_texts,
    click_value,
    close_drawer,
    drawer_groups,
    drawer_text_fields,
    open_drawer,
    remove_chip,
)
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_layout_helpers import (
    BOUNDARY_HEIGHT,
    NARROW_VIEWPORT,
    TABLE_BOARD_BOUNDARY_WIDTHS,
    WIDE_VIEWPORT,
    assert_bands_stay,
    assert_page_does_not_scroll,
    assert_region_mode,
    region_metrics,
)
from preview_mark_helpers import SCREEN_MARKS, marks_of
from preview_removed_helpers import (
    BAND,
    REMOVED_IN_V2_BY_TAB,
    WITHDRAWN_BADGE,
    assert_band_above,
    assert_removed_band,
)
from workspace_fixtures import ADOPTED_OPTIONS, MakeItem


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
            "logs", "会話ログ", "L-1", ["ID", "日付", "タイトル", "タグ", "更新した項目"], id="logs"
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
        make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS),
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


# 種類の画面ごとの、取り下げていない項目・取り下げた項目・消した項目の ID
RECORD_IDS = {
    "research": ("R-1", "R-2", "R-3"),
    "terms": ("G-1", "G-2", "G-3"),
    "notes": ("N-1", "N-2", "N-3"),
    "logs": ("L-1", "L-2", "L-3"),
}

# 4 つの種類の画面
RECORD_TABS = [pytest.param(tab, id=tab) for tab in RECORD_IDS]


@pytest.mark.parametrize("tab", RECORD_TABS)
def test_removed_band(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page, tab: str
) -> None:
    """差分の表示の間、選んだ時点で消したその種類の項目を、表の上の帯に並べる。押せず、行にもしない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, f"#tab={tab}")
    page.wait_for_selector("table.grid")
    # 検証
    assert_removed_band(page, REMOVED_IN_V2_BY_TAB[tab])
    assert_band_above(page, "table.grid")
    assert page.locator(f'[data-id="{RECORD_IDS[tab][2]}"]').count() == 0


def test_removed_band_when_filtered(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """文字の条件で表の行が 0 件になっても、消した項目は絞り込まず帯に出す（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=research")
    page.wait_for_selector("table.grid")
    open_drawer(page)
    page.fill(f'{DRAWER} input[data-text-key="title"]', "一致しない文字")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 0")
    # 検証
    assert page.locator("table.grid tbody tr[data-id]").count() == 0
    assert_removed_band(page, REMOVED_IN_V2_BY_TAB["research"])


@pytest.mark.parametrize(
    "sel",
    [
        pytest.param(None, id="diff_off"),
        pytest.param("V-1", id="nothing_removed"),
        pytest.param("pending", id="removed_other_kind"),
    ],
)
def test_removed_band_when_nothing_to_show(
    write_removed_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    sel: str | None,
) -> None:
    """差分を出していないとき、選んだ時点でその種類の項目を消していないとき（消したのがほかの種類だけのときも）は、帯を置かない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, sel)
    open_preview(url, "#tab=research")
    page.wait_for_selector("table.grid")
    # 検証
    assert page.locator(BAND).count() == 0


@pytest.mark.parametrize("tab", RECORD_TABS)
def test_withdrawn_badge(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page, tab: str
) -> None:
    """取り下げた項目の行は、差分を出していなくてもタイトルの右に取り下げの札を置き、文字を薄くする。取り下げていない行は変えない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, None)
    open_preview(url, f"#tab={tab}")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    normal_id, withdrawn_id, _ = RECORD_IDS[tab]
    row = f'table.grid tbody tr[data-id="{withdrawn_id}"]'
    normal = f'table.grid tbody tr[data-id="{normal_id}"]'
    badge = page.locator(f"{row} .row-open + {WITHDRAWN_BADGE}")
    assert badge.count() == 1
    assert badge.inner_text() == "取り下げ"
    assert "is-withdrawn" in str(page.get_attribute(row, "class"))
    assert page.locator(f"{normal} {WITHDRAWN_BADGE}").count() == 0
    assert "is-withdrawn" not in str(page.get_attribute(normal, "class"))
    # 取り下げた行の文字は、取り下げていない行より薄い
    color_script = "e => getComputedStyle(e).color"
    assert page.eval_on_selector(f"{row} .row-open", color_script) != page.eval_on_selector(
        f"{normal} .row-open", color_script
    )
    assert page.eval_on_selector(f"{row} td", color_script) != page.eval_on_selector(
        f"{normal} td", color_script
    )


@pytest.mark.parametrize("tab", RECORD_TABS)
def test_withdrawn_badge_with_diff(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page, tab: str
) -> None:
    """差分の表示で取り下げた項目に変更の印が付くとき、取り下げの札は差分の印より前に置く（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-1")
    open_preview(url, f"#tab={tab}")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    withdrawn_id = RECORD_IDS[tab][1]
    row = f'table.grid tbody tr[data-id="{withdrawn_id}"]'
    assert page.locator(f"{row} .row-open + .wd-badge + .df-mark.df-chg").count() == 1


def _row_ids(page: Page) -> list[str]:
    """表に並んでいる行の ID を並びのまま返す。"""
    return page.eval_on_selector_all(
        "table.grid tbody tr[data-id]", "rows => rows.map(r => r.dataset.id)"
    )


def test_drawer_per_kind(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ドロワーの条件は種類ごとに持つ。調査はタグ・確度、メモはタグを並べ、別の種類へ移っても条件を持ち越さず、戻ると保っている（正常系）。"""
    # 準備
    url = write_preview(
        make_item("R-1", confidence="高", tags=["調査の話題"]),
        make_item("R-2", confidence="低"),
        make_item("N-1", tags=["調査の話題"]),
        make_item("N-2"),
    )
    page = open_preview(url, "#tab=research")
    open_drawer(page)
    research_groups = [group["label"] for group in drawer_groups(page)]
    # 実行（調査で確度を選ぶ）
    click_value(page, "confidence", "高")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 1")
    research_rows = _row_ids(page)
    research_badge = badge_text(page)
    # 実行（メモへ移る。ドロワーは開いたまま）
    page.click('a.tab[data-tab="notes"]')
    page.wait_for_selector('table.grid tbody tr[data-id="N-2"]')
    notes_state = (
        [group["label"] for group in drawer_groups(page)],
        badge_text(page),
        _row_ids(page),
        page.locator("dialog.drawer[open]").count(),
    )
    # 実行（調査へ戻る）
    page.click('a.tab[data-tab="research"]')
    page.wait_for_selector('table.grid tbody tr[data-id="R-1"]')
    # 検証
    assert research_groups == ["タグ", "確度"]
    assert (research_rows, research_badge) == (["R-1"], "1")
    assert notes_state == (["タグ"], None, ["N-1", "N-2"], 1)
    assert badge_text(page) == "1"
    assert checked_values(page, "confidence") == ["高"]
    # 文字の欄のまとまりを除いた、値を選ぶ条件の数
    assert page.locator(f"{DRAWER} .fd-group:not(.fd-text)").count() == 2


def test_drawer_logs_tags(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """会話ログもタグの列を持ち、ドロワーのタグの条件で絞れる。表の上のチップで解除できる（正常系）。"""
    # 準備
    url = write_preview(
        make_item("L-1", tags=["脱線"]),
        make_item("L-2", date="2026-10-02"),
    )
    page = open_preview(url, "#tab=logs")
    open_drawer(page)
    # 実行
    click_value(page, "tags", "脱線")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 1")
    rows = _row_ids(page)
    tag_cells = page.eval_on_selector_all(
        "table.grid tbody tr[data-id] td .tag", "tags => tags.map(t => t.textContent)"
    )
    chips = page.eval_on_selector_all(".table-block .chip", "chips => chips.map(c => c.textContent)")
    # 検証
    assert rows == ["L-1"]
    assert tag_cells == ["脱線"]
    assert chips == ["タグ: 脱線"]


def test_comment_marks(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """調査の表の行のタイトルの右に印を出す。コメントの無い行には出さない（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=research")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert marks_of(page) == SCREEN_MARKS["research"]
    assert page.get_attribute('table.grid tr[data-id="R-1"] .cmk', "title") == "コメント 1 件"


# 項目を多く持つメモの数（領域の高さを超える数）
MANY_NOTES = 40


def test_region_when_wide(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """幅が広いとき、ページ全体はスクロールせず、帯は見えたままで、表は領域の高さいっぱいに広がって中でスクロールする（正常系）。"""
    # 準備
    url = write_preview(*(make_item(f"N-{number}") for number in range(1, MANY_NOTES + 1)))
    page = open_preview(url, "#tab=notes")
    page.set_viewport_size(WIDE_VIEWPORT)
    page.wait_for_selector(".table-wrap")
    # 実行
    metrics = region_metrics(page, ".table-wrap")
    # 検証
    assert_page_does_not_scroll(page)
    assert metrics["content"]["scrollHeight"] <= metrics["content"]["clientHeight"]
    assert metrics["target"]["scrollHeight"] > metrics["target"]["clientHeight"]
    assert_bands_stay(page)


def test_region_when_narrow(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """幅が狭いとき、表は領域ごと縦にスクロールし、ページ全体はスクロールせず、帯は見えたまま（正常系）。"""
    # 準備
    url = write_preview(*(make_item(f"N-{number}") for number in range(1, MANY_NOTES + 1)))
    page = open_preview(url, "#tab=notes")
    page.set_viewport_size(NARROW_VIEWPORT)
    page.wait_for_selector(".table-wrap")
    # 実行
    metrics = region_metrics(page, ".table-wrap")
    # 検証
    assert_page_does_not_scroll(page)
    assert metrics["content"]["scrollHeight"] > metrics["content"]["clientHeight"]
    assert metrics["target"]["scrollHeight"] <= metrics["target"]["clientHeight"] + 1
    assert_bands_stay(page)


def test_drawer_text_fields_when_terms(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """用語集のドロワーに文字の欄（ID・用語・意味・別名・使わない表記）を並べ、用語に文字を入れると表を絞ってチップに出す。× で解除できる（正常系）。"""
    # 準備
    url = write_preview(
        make_item("G-1", title="移し替え", tags=["mindstella"]),
        make_item("G-2", title="ワークスペース"),
        make_item("G-3", title="検討事項"),
    )
    page = open_preview(url, "#tab=terms")
    page.wait_for_selector("table.grid tbody tr[data-id]")
    # 実行
    open_drawer(page)
    fields = [(field["key"], field["label"]) for field in drawer_text_fields(page)]
    page.fill(f'{DRAWER} input[data-text-key="title"]', "移し")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 1")
    rows = _row_ids(page)
    chips = chip_texts(page)
    close_drawer(page)
    remove_chip(page, "用語に「移し」を含む")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 3")
    # 検証
    assert fields == [
        ("id", "ID"),
        ("title", "用語"),
        ("meaning", "意味"),
        ("aliases", "別名"),
        ("avoid", "使わない表記"),
    ]
    assert rows == ["G-1"]
    assert chips == ["用語に「移し」を含む"]


@pytest.mark.parametrize(("width", "filled"), TABLE_BOARD_BOUNDARY_WIDTHS)
def test_region_at_boundary(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    width: int,
    filled: bool,
) -> None:
    """領域の高さいっぱいに広げる境（721px）の前後の幅で、表が広がるか領域ごとスクロールするかが切り替わる（正常系）。"""
    # 準備
    url = write_preview(*(make_item(f"N-{number}") for number in range(1, MANY_NOTES + 1)))
    page = open_preview(url, "#tab=notes")
    page.set_viewport_size({"width": width, "height": BOUNDARY_HEIGHT})
    page.wait_for_selector(".table-wrap")
    # 実行・検証
    assert_region_mode(page, ".table-wrap", filled=filled)
