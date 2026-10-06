"""部品設計『表』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 長いタイトルが折り返す幅
NARROW_SIZE = {"width": 640, "height": 600}

# 見出しの aria-sort を列の key で読む
SORT_SCRIPT = """() => Object.fromEntries([...document.querySelectorAll('table.grid thead th')].map(
    th => [th.querySelector('.th-sort').dataset.sort, th.getAttribute('aria-sort')]
))"""


def test_default(open_story: OpenStory) -> None:
    """通常。全ての見出しの aria-sort が none で、行は元の並び（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--default")
    # 検証
    assert set(page.evaluate(SORT_SCRIPT).values()) == {"none"}
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["D-1", "D-2", "D-3", "D-4"]


def test_sorted_asc(open_story: OpenStory) -> None:
    """タイトルで昇順。見出しが aria-sort="ascending" を持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--sorted-asc")
    # 検証
    sort = page.evaluate(SORT_SCRIPT)
    assert sort["title"] == "ascending"
    assert {value for key, value in sort.items() if key != "title"} == {"none"}


def test_sorted_desc(open_story: OpenStory) -> None:
    """タイトルで降順。見出しが aria-sort="descending" を持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--sorted-desc")
    # 検証
    assert page.evaluate(SORT_SCRIPT)["title"] == "descending"


def test_filtered(open_story: OpenStory) -> None:
    """確度 = 高で絞り込み中。条件のチップとすべて解除を並べ、列の見出しには並べ替えとピン留めだけを置く（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--filtered")
    # 検証
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == ["確度: 高"]
    assert page.locator(".chips >> text=すべて解除").count() == 1
    # 列の見出しに絞り込みのボタンを出さず、並べ替えとピン留めのボタンだけを置く
    assert page.locator('table.grid thead button[aria-label$="で絞り込み"]').count() == 0
    classes = page.eval_on_selector_all(
        "table.grid thead button", "buttons => [...new Set(buttons.map(b => b.className))]"
    )
    assert sorted(classes) == ["th-sort", "th-tool pin"]
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["D-1", "D-3"]


def test_pinned(open_story: OpenStory) -> None:
    """ID の列までピン留め。押した列のボタンだけが押された見た目で、固定した列の境に影（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--pinned")
    # 検証
    pressed = page.eval_on_selector_all(
        "button.pin", "buttons => buttons.filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.pin)"
    )
    assert pressed == ["id"]
    assert page.locator("table.grid .pinned").count() > 0


def test_long_title(open_story: OpenStory) -> None:
    """長いタイトルは折り返し、ほかの列は崩れない（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--long-title")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 640")
    # 検証
    heights = page.evaluate(
        "(() => { const rows = [...document.querySelectorAll('table.grid tbody tr')]; return rows.map(r => Math.round(r.getBoundingClientRect().height)); })()"
    )
    assert heights[0] > heights[1]
    # ID の列の文字は折り返さない
    assert page.evaluate(
        "(() => { const r = document.createRange(); r.selectNodeContents(document.querySelector('table.grid tbody tr td')); return r.getBoundingClientRect().height < 30; })()"
    )


def test_no_match(open_story: OpenStory) -> None:
    """該当なし（ピン留め中）。表の場所に該当なしと次の操作を書き、文言は表の枠の左に留める（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--no-match")
    # 検証
    assert "該当" in page.inner_text("table.grid tbody")
    assert page.locator("table.grid td.no-match-cell .no-match").count() == 1
    assert page.evaluate(
        "getComputedStyle(document.querySelector('td.no-match-cell .no-match')).position"
    ) == "sticky"


def test_columns_popover(open_story: OpenStory) -> None:
    """表示する列のポップオーバーを開いている。タイトルの列は外せない（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--columns-popover")
    page.wait_for_selector(".pop:popover-open")
    # 検証
    boxes = page.evaluate(
        "[...document.querySelectorAll('.pop label')].map(l => [l.textContent.trim(), l.querySelector('input').disabled, l.querySelector('input').checked])"
    )
    assert boxes == [
        ["ID", False, True],
        ["タイトル", True, True],
        ["確度", False, True],
        ["状態", False, True],
    ]
    # ポップオーバーの題は見出しの要素にせず、aria-labelledby から指す
    assert page.locator(".pop h3").count() == 0
    labelled = page.get_attribute(".pop", "aria-labelledby")
    assert page.inner_text(f"#{labelled}") == "表示する列"


def test_marked(open_story: OpenStory) -> None:
    """差分の表示の間。変えた行のタイトルの右に ●、足した行に + を置き、印の無い行は変わらない（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--marked")
    # 検証
    marks = page.evaluate(
        """() => Object.fromEntries([...document.querySelectorAll('table.grid tbody tr')].map(row => {
            const mark = row.querySelector('.row-open + .df-mark');
            return [row.dataset.id, mark === null ? null : [mark.classList.contains('df-new') ? 'new' : 'changed', mark.getAttribute('title')]];
        }))"""
    )
    assert marks["D-5"] == ["changed", "変更"]
    assert marks["D-37"] == ["new", "新規"]
    assert [marks[row] for row in ("D-1", "D-2", "D-3", "D-4")] == [None] * 4
    # 表の印は記号だけで、「新規」「変更」の札にしない
    assert page.locator("table.grid .df-badge").count() == 0
    assert page.locator("table.grid .df-mark svg.icon").count() == 2


# 行ごとに、タイトル・差分の印・コメントの印の要素の並びと、印の無い行の印の数を返す
COMMENTED_ROWS_SCRIPT = """() => Object.fromEntries([...document.querySelectorAll('table.grid tbody tr')].map(row => {
    const cell = row.querySelector('.row-open').parentElement;
    return [row.dataset.id, {
        order: [...cell.children].map(child => child.matches('.row-open') ? 'title' : child.matches('.df-mark') ? 'diff' : child.matches('.cmk-place') ? 'comment' : 'other'),
        count: row.querySelector('.cmk')?.querySelector('.cmk-n').textContent ?? null,
        spoken: row.querySelector('.cmk .sr-only')?.textContent ?? null,
    }];
}))"""

# タイトルのボタンとコメントの印の外形を返す
COMMENT_BOXES_SCRIPT = """(id) => {
    const row = document.querySelector(`table.grid tbody tr[data-id="${id}"]`);
    const box = (element) => { const r = element.getBoundingClientRect(); return {left: r.left, top: r.top, right: r.right, bottom: r.bottom}; };
    return {title: box(row.querySelector('.row-open')), mark: box(row.querySelector('.cmk'))};
}"""

# 幅 390px のストーリーの画面の大きさ
PHONE_VIEWPORT = {"width": 390, "height": 844}


def test_commented(open_story: OpenStory) -> None:
    """コメントを書いた行。タイトル・差分の印・コメントの印の順に置き、印の無い行は変わらない（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--commented")
    # 検証
    rows = page.evaluate(COMMENTED_ROWS_SCRIPT)
    assert rows["D-5"] == {
        "order": ["title", "diff", "comment"],
        "count": "1",
        "spoken": "コメント 1 件",
    }
    assert rows["D-37"] == {"order": ["title", "comment"], "count": "12", "spoken": "コメント 12 件"}
    # 印の無い行は、印を置く場所が空のまま（印も読み上げの文字も無い）
    for row_id in ("D-1", "D-2", "D-3", "D-4"):
        assert rows[row_id]["order"] == ["title", "comment"]
        assert rows[row_id]["count"] is None
        assert rows[row_id]["spoken"] is None
    assert page.locator("table.grid .cmk-place:empty").count() == 4
    assert page.locator("table.grid .cmk").count() == 2


def test_commented_when_narrow(open_story: OpenStory) -> None:
    """幅 390px でも、コメントの印がタイトルに重ならず、収まらなければ次の行へ送る（正常系）。"""
    # 準備
    page = open_story("preview-table--commented")
    # 実行
    page.set_viewport_size(PHONE_VIEWPORT)
    # 検証
    for row_id in ("D-5", "D-37"):
        boxes = page.evaluate(COMMENT_BOXES_SCRIPT, row_id)
        title, mark = boxes["title"], boxes["mark"]
        # 同じ行に並ぶなら右に、次の行へ送られたならタイトルの下にあり、どちらもタイトルと重ならない
        beside = mark["left"] >= title["right"]
        below = mark["top"] >= title["bottom"]
        assert beside or below
