"""項目の詳細を読む（案・関係・本文・全画面・図の拡大・関係する項目への移動）の E2E テスト。"""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page
from preview_helpers import OpenPreview, ServePreview
from workspace_fixtures import ADOPTED_OPTIONS, MakeItem

# 本文に mermaid の図を 1 つ持つ Markdown
BODY_WITH_DIAGRAM = """# 要件

本文の段落

```mermaid
flowchart LR
  A --> B
```
"""

# 広い幅の画面（詳細パネルが本文を寄せる幅）
WIDE_SIZE = (1920, 1080)

# 全画面で本文を送れる長さにするために足す段落の数
FILLER_PARAGRAPHS = 60

# 全画面の本文の上でホイールを回す量（px）
WHEEL_DELTA_PX = 800

# 本文に mermaid の図と、モーダルの中で送れる長さの段落を持つ Markdown
LONG_BODY_WITH_DIAGRAM = BODY_WITH_DIAGRAM + "\n".join(
    f"\n続きの段落 {number}\n" for number in range(1, FILLER_PARAGRAPHS + 1)
)

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 全画面の外側（後ろの幕）を押す位置
BACKDROP_POINT = (4, 4)

# Markdown で書いた値（強調とリストを持つ）
MARKDOWN_VALUE = "**強調**した文\n\n- 箇条書き"

# 本文のスクリプトが実行されたときに残す印
SCRIPT_BODY = """<script>window.__bodyScriptRan = true</script>

<img src="missing.png" onerror="window.__bodyScriptRan = true">

本文の文字
"""


def _related(page: Page) -> dict[str, list[str]]:
    """詳細パネルの関係の節（見出し → 押せる項目の ID）を返す。"""
    return page.evaluate(
        """() => Object.fromEntries([...document.querySelectorAll('aside.panel .d-sec')]
            .filter(sec => sec.querySelector('.d-list'))
            .map(sec => [sec.querySelector('h3').textContent, [...sec.querySelectorAll('button.idlink')].map(b => b.textContent)]))"""
    )


def _decision_records(make_item: MakeItem) -> list[dict[str, Any]]:
    """案・前提・後続・進めるタスク・関連・参照元・図つきの本文と Markdown の背景・答え・理由を持つ検討事項 D-3 と、つながる項目を返す。"""
    return [
        make_item("D-1", status="決定済み", answer="種類ごとに分ける", options=ADOPTED_OPTIONS),
        make_item(
            "D-3",
            status="要見直し",
            lead=MARKDOWN_VALUE,
            answer=MARKDOWN_VALUE,
            reason=MARKDOWN_VALUE,
            depends_on=["D-1"],
            related=["R-1"],
            body="D-3.md",
            options=[
                {
                    "key": "A",
                    "content": "表で見せる",
                    "pros": MARKDOWN_VALUE,
                    "adopted": True,
                    "reason": "並べやすい",
                },
                {
                    "key": "B",
                    "content": "カードで見せる",
                    "adopted": False,
                    "reason": "数が多いと長い",
                },
            ],
        ),
        make_item("D-5", status="未決定", depends_on=["D-3"]),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("R-1", question="何を調べたか"),
        make_item("N-1", content="メモの中身", related=["D-3"]),
    ]


def test_normal(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """案・関係・本文と図を読み、全画面と図の拡大で読み、関係する項目へ移って戻る（正常系）。"""
    # 準備
    url = serve_preview(
        *_decision_records(make_item),
        settings=valid_settings,
        bodies={"D-3.md": LONG_BODY_WITH_DIAGRAM},
    )
    page = open_preview(url, "#tab=decisions&view=table", width=WIDE_SIZE[0], height=WIDE_SIZE[1])
    # 本文の中身の枠（表の枠）の左右の位置を測る（外枠 `main#main` は窓の左端から始まるので、寄りを測れない）
    box_script = "(() => { const r = document.querySelector('.table-wrap').getBoundingClientRect(); return [r.left, r.right]; })()"
    left_before = page.evaluate(box_script)[0]
    # 実行
    page.click('table.grid button.row-open[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（案）: 案 A（採用）と案 B（不採用と理由）のカードが縦に並ぶ
    options = page.eval_on_selector_all(
        "aside.panel .opt",
        "opts => opts.map(o => [o.querySelector('.key').textContent, o.querySelector('.res').textContent, o.getBoundingClientRect().top, o.textContent.includes('数が多いと長い')])",
    )
    assert [row[:2] for row in options] == [["A", "採用"], ["B", "不採用"]]
    assert options[0][2] < options[1][2]
    assert options[1][3] is True
    # 検証（並び）: タイトル → 背景 → 案 → 採用した案と理由 → 本文の順に並ぶ
    order = page.evaluate(
        """() => [...document.querySelectorAll('aside.panel .d-title, aside.panel .d-lead, aside.panel .d-sec h3')]
            .map(e => e.classList.contains('d-title') ? 'タイトル' : e.classList.contains('d-lead') ? '背景' : e.textContent)
            .filter(t => ['タイトル', '背景', '案', '採用した案と理由', '本文'].includes(t))"""
    )
    assert order == ["タイトル", "背景", "案", "採用した案と理由", "本文"]
    # 検証（Markdown）: 背景・答え・理由と案 A のメリットが、強調とリストとして描かれる
    drawn = page.eval_on_selector_all(
        "aside.panel .md-value",
        "els => els.map(e => [e.querySelectorAll('strong').length, e.querySelectorAll('li').length])",
    )
    assert drawn.count([1, 1]) == 4
    # 検証（関係）
    related = _related(page)
    assert related["前提"] == ["D-1"]
    assert related["後続の項目"] == ["D-5"]
    assert related["関連タスク"] == ["T-2"]
    assert related["関連"] == ["R-1"]
    assert related["参照元"] == ["N-1"]
    # 検証（本文と図）
    assert page.inner_text('aside.panel .md [data-md-level="1"]') == "要件"
    for action in ("diagram-zoom", "diagram-raw", "diagram-copy"):
        assert page.locator(f'aside.panel button[data-act="{action}"]').count() == 1
    zoom_button = 'aside.panel button[data-act="diagram-zoom"]'
    assert page.get_attribute(zoom_button, "aria-label") == "図を拡大表示"
    assert page.get_attribute(zoom_button, "title") == "拡大表示"
    # 幅 1920px では、パネルを開いている間、本文がパネルの分だけ左へ寄り、パネルに重ならない
    left_after, right_after = page.evaluate(box_script)
    panel_left = page.evaluate("document.querySelector('aside.panel').getBoundingClientRect().left")
    assert left_after < left_before
    assert right_after <= panel_left
    # 「全画面表示」を押し、図の拡大は中身の切り替えで、モーダルが 2 枚重ならない
    button_style_js = """(selector) => {
        const style = getComputedStyle(document.querySelector(selector));
        return [style.color, style.borderTopColor, style.backgroundColor, document.querySelector(selector + ' svg path').getAttribute('d')];
    }"""
    assert page.get_attribute('aside.panel button[data-act="full"]', "aria-label") == "全画面表示"
    before_style = page.evaluate(button_style_js, 'aside.panel button[data-act="full"]')
    page.click('aside.panel button[data-act="full"]')
    page.wait_for_selector("dialog.full[open] .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 全画面の間は縮小のアイコンに替わり、文字色・枠の色・背景色は押す前と同じ。押された状態（aria-pressed）は持たない
    full_style = page.evaluate(button_style_js, 'dialog.full button[data-act="full"]')
    assert full_style[:3] == before_style[:3]
    assert full_style[3] != before_style[3]
    assert page.get_attribute('dialog.full button[data-act="full"]', "aria-pressed") is None
    # モーダルの本文の幅が、モーダルの中の左右の余白を除いた幅いっぱいに広がる
    widths = page.evaluate(
        """() => {
            const dialog = document.querySelector('dialog.full').getBoundingClientRect();
            const body = document.querySelector('dialog.full .panel-body').getBoundingClientRect();
            return {dialog: dialog.width, body: body.width};
        }"""
    )
    assert widths["body"] >= widths["dialog"] - 2
    # モーダルの中でホイールを回して本文を下へ送ると、モーダルの中が送られる（後ろの画面へ伝えない CSS は結合テストで確かめる）
    body_box = page.locator("dialog.full .panel-body").bounding_box()
    assert body_box is not None
    page.mouse.move(body_box["x"] + body_box["width"] / 2, body_box["y"] + body_box["height"] / 2)
    page.mouse.wheel(0, WHEEL_DELTA_PX)
    page.wait_for_function("document.querySelector('dialog.full .panel-body').scrollTop > 0")
    page.click('dialog.full button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.full .full-viewer .v-stage svg")
    assert page.locator("dialog[open]").count() == 1
    page.click('dialog.full button[data-act="diagram-close"]')
    page.wait_for_selector("dialog.full .panel-body", state="visible")
    # 全画面に全てを閉じるボタンが無く、外側を押すと D-3 の詳細パネルに戻る
    assert page.locator('dialog.full button[data-act="close"]').count() == 0
    page.mouse.click(*BACKDROP_POINT)
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    # D-1 を押すと詳細パネルに D-1 が開き、URL のハッシュが D-1 を指す
    page.click("aside.panel .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'"
    )
    assert "id=D-1" in page.evaluate("location.hash")
    # 戻る操作で D-3 の詳細パネルに戻り、URL のハッシュが D-3 を指す
    page.go_back()
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === 'D-3の題'"
    )
    assert "id=D-3" in page.evaluate("location.hash")


def test_normal_when_recommendation_shown(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """未決定の検討事項の詳細パネルで、推奨の案だけに推奨の印が出て、背景が Markdown で描かれる（正常系）。"""
    # 準備
    url = serve_preview(
        make_item(
            "D-7",
            status="未決定",
            lead="**背景**を読んで選ぶ",
            options=[
                {"key": "A", "content": "案 A"},
                {"key": "B", "content": "案 B", "recommended": True},
            ],
        ),
        settings=valid_settings,
    )
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    page.click('table.grid button.row-open[data-id="D-7"]')
    page.wait_for_selector("aside.panel.open .opt")
    # 検証
    # 案 B のカードだけが推奨の印を持ち、案 A・B のどちらも採用・不採用の表示を持たない
    marks = page.eval_on_selector_all(
        "aside.panel .opt",
        """opts => opts.map(o => [
          o.querySelector('.key').textContent,
          o.querySelector('.o-head .rec-badge')?.textContent ?? null,
          o.querySelector('.res')?.textContent ?? null,
        ])""",
    )
    assert marks == [["A", None, None], ["B", "推奨", None]]
    assert page.locator("aside.panel .opt.adopted, aside.panel .opt.rejected").count() == 0
    # 背景の Markdown が強調として描かれる
    assert page.inner_text("aside.panel .d-lead strong") == "背景"
    # 採用した案と理由の節が出ない
    titles = page.eval_on_selector_all("aside.panel .d-sec h3", "hs => hs.map(h => h.textContent)")
    assert "採用した案と理由" not in titles


def test_error_when_body_has_script(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """本文の script と onerror 属性は実行せず、詳細パネルの中にも残さない（異常系）。"""
    # 準備
    url = serve_preview(make_item("A-1"), settings=valid_settings, bodies={"A-1.md": SCRIPT_BODY})
    # 実行
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel.open .md")
    page.wait_for_timeout(1_000)
    # 検証
    assert page.evaluate("window.__bodyScriptRan") is None
    assert page.locator("aside.panel script").count() == 0
    assert page.locator("aside.panel [onerror]").count() == 0
    assert "本文の文字" in page.inner_text("aside.panel .md")


def test_error_when_render_library_unavailable(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """本文の描画のライブラリ（marked・mermaid）が読めないと、名前を出し、本文を文字のまま読める（異常系）。"""
    # 準備
    url = serve_preview(
        make_item("A-1"), settings=valid_settings, bodies={"A-1.md": BODY_WITH_DIAGRAM}
    )
    page.route(re.compile(r"/npm/(marked|mermaid)@"), lambda route: route.abort())
    # 実行
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel.open .md .lib-error[role=alert]")
    # 検証
    notice = page.inner_text("aside.panel .md .lib-error[role=alert]")
    assert "marked" in notice
    assert "mermaid" in notice
    raw = page.inner_text("aside.panel .md .md-raw")
    assert "# 要件" in raw
    assert "flowchart LR" in raw


# 本文の見出し「決め方」を、詳細パネルを開いたときに画面に入らない位置に置く段落の数
LINK_FILLER_PARAGRAPHS = 60

# 本文のリンクで移る資料 A-1 の本文（見出し「保存先」「決め方」、リンク・用語・ID を並べた段落、コードブロック）
LINKED_BODY = (
    "## 保存先\n\n"
    "保存先は [決め方](#決め方) で決める。D-3 と `D-5` と D-99 を見る。\n\n"
    "```\n保存先 D-3\n```\n\n"
    + "\n\n".join(f"間の段落 {number}" for number in range(1, LINK_FILLER_PARAGRAPHS + 1))
    + "\n\n## 決め方\n\n決め方の本文\n"
)

# 本文のスクロール領域
PANEL_BODY = "aside.panel .panel-body"


def _heading_in_view(page: Page, slug: str) -> bool:
    """見出し（`data-heading`）が、詳細パネルの本文の領域の中で画面に入っているかを返す。"""
    return page.evaluate(
        """(slug) => {
            const area = document.querySelector('aside.panel .panel-body').getBoundingClientRect();
            const box = document.querySelector(`aside.panel [data-heading="${slug}"]`).getBoundingClientRect();
            return box.top >= area.top - 1 && box.bottom <= area.bottom + 1;
        }""",
        slug,
    )


def test_normal_when_body_links(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """本文の用語の印にカーソルを合わせて意味を読み、見出しのリンクで送り、その URL を開き直し、項目の ID と用語のリンクで移る（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("A-1"),
        make_item("G-1", title="保存先", meaning="記録を置くフォルダ", body="G-1.md"),
        make_item("D-3"),
        make_item("D-5"),
        settings=valid_settings,
        bodies={"A-1.md": LINKED_BODY, "G-1.md": "保存先の説明\n"},
    )
    # 実行（A-1 の詳細パネルを開く）
    open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector(f"{PANEL_BODY} [data-heading]")
    # 検証（用語の印・ID のリンク・見出しのリンク）
    marks = page.eval_on_selector_all(
        "aside.panel .md a.term", "a => a.map(x => [x.textContent, x.dataset.id])"
    )
    refs = page.eval_on_selector_all(
        "aside.panel .md a.idref", "a => a.map(x => [x.textContent, x.dataset.id])"
    )
    in_code_or_heading = page.locator(
        "aside.panel .md :is(pre, h2) :is(a.term, a.idref)"
    ).count()
    heading_links = page.eval_on_selector_all(
        "aside.panel [data-heading] .h-link", "l => l.map(x => x.getAttribute('aria-label'))"
    )
    # 段落の「保存先」だけに印が付き、見出し「保存先」とコードブロックには付かない。D-99 はリンクでない
    assert marks == [["保存先", "G-1"]]
    assert refs == [["D-3", "D-3"], ["D-5", "D-5"]]
    assert in_code_or_heading == 0
    assert heading_links == ["見出し「保存先」へのリンク", "見出し「決め方」へのリンク"]
    # 実行（「保存先」の印にカーソルを合わせる）
    mark = "aside.panel .md a.term"
    page.hover(mark)
    page.wait_for_selector("#term-tip:popover-open")
    assert "記録を置くフォルダ" in page.inner_text("#term-tip")
    # キーボードでフォーカスしても同じツールチップが出る
    page.mouse.move(2, 2)
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    page.focus(mark)
    page.wait_for_selector("#term-tip:popover-open")
    assert "記録を置くフォルダ" in page.inner_text("#term-tip")
    page.keyboard.press("Escape")
    # 実行（本文の「決め方」のリンクを押す）
    assert _heading_in_view(page, "決め方") is False
    content_scroll_before = page.evaluate("document.querySelector('.content').scrollTop")
    page.click("aside.panel .md p a:has-text('決め方')")
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'")
    # 検証（詳細パネルの中が送られ、後ろの画面は送られない）
    assert _heading_in_view(page, "決め方") is True
    assert page.evaluate("document.querySelector('.content').scrollTop") == content_scroll_before
    hash_text = page.evaluate("location.hash")
    assert "tab=docs" in hash_text
    assert "id=A-1" in hash_text
    # 実行（「決め方」の見出しのリンクを押す。リンクを押した後の URL のハッシュが見出しを指す）
    page.click('aside.panel [data-heading="決め方"] .h-link')
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'")
    shared = page.url
    # 実行（その URL を新しいタブで開く）
    other = page.context.new_page()
    other.set_viewport_size({"width": 1280, "height": 800})
    other.goto(shared)
    other.wait_for_selector(f"{PANEL_BODY} [data-heading]")
    other.wait_for_function("document.querySelector('aside.panel .panel-body').scrollTop > 0")
    # 検証（新しいタブでも、「決め方」が画面に入る位置まで送られて開く）
    assert _heading_in_view(other, "決め方") is True
    other.close()
    # 実行（本文の「D-3」を押す）
    page.click('aside.panel .md a.idref[data-id="D-3"]')
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-3の題'")
    assert "id=D-3" in page.evaluate("location.hash")
    # 実行（戻る操作をし、本文の「保存先」を押す）
    page.go_back()
    page.wait_for_selector(f"{PANEL_BODY} a.term")
    page.click("aside.panel .md a.term")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === '保存先'")
    # 検証（G-1 の詳細パネルが開き、G-1 の本文の「保存先」には用語の印が付かない）
    assert "id=G-1" in page.evaluate("location.hash")
    assert page.locator("aside.panel .md a.term").count() == 0


def test_normal_when_withdrawn(
    serve_preview: ServePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """取り下げた資料の表の行に取り下げの印が付き、詳細パネルに取り下げの印と理由が出る。取り下げていない資料には出ない（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("A-1", status="完成", kind="仕様書", withdrawn=True, reason="別の資料にまとめた"),
        make_item("A-2", status="完成", kind="仕様書"),
        bodies={"A-1.md": "# 取り下げた資料\n", "A-2.md": "# 残す資料\n"},
    )
    # 実行（資料の表を開く）
    page = open_preview(url, "#tab=docs&view=table")
    page.wait_for_selector("table.grid tbody tr")
    # 検証（A-1 に取り下げの印が付き、A-2 には付かない）
    assert page.locator('table.grid tbody tr[data-id="A-1"] .row-open + .wd-badge').count() == 1
    assert page.locator('table.grid tbody tr[data-id="A-2"] .wd-badge').count() == 0
    # 実行（A-1 を押す）
    page.click('table.grid button.row-open[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open .d-title")
    # 検証（取り下げの印と理由が出る）
    assert page.inner_text("aside.panel .d-title .wd-badge") == "取り下げ"
    assert page.inner_text('aside.panel [data-key="reason"]') == "別の資料にまとめた"
    # 実行（A-2 を押す）
    page.click('table.grid button.row-open[data-id="A-2"]')
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'A-2の題'")
    # 検証（取り下げの印も理由も出ない）
    assert page.locator("aside.panel .wd-badge").count() == 0
    assert page.locator('aside.panel [data-key="reason"]').count() == 0


# 本文の語に一致する資料・調査のエイリアスと、もう 1 つのエイリアス
ALIAS_WORD = "特殊効果"
OTHER_ALIAS_WORD = "エフェクト"

# 「特殊効果」に一致する資料 A-2～A-7 のうち、A-4 から後の資料の番号
EXTRA_DOC_NUMBERS = range(4, 8)

# A-1 の本文で、印の段落の前と後に置く段落の数（本文を送れる長さにし、印を画面の中ほどへ置けるようにする）
ALIAS_BODY_FILLER = 20

# A-1 の本文: 「特殊効果」と「エフェクト」を持つ段落を、語を持たない段落ではさむ
ALIAS_BODY = (
    "".join(f"段落 {number}\n\n" for number in range(ALIAS_BODY_FILLER))
    + "特殊効果とエフェクトを重ねる\n\n"
    + "".join(f"続きの段落 {number}\n\n" for number in range(ALIAS_BODY_FILLER))
)

# 本文の印・ツールチップ（開いている間）の選び方
BODY_MARKS = "aside.panel .md:not(.md-value) p a.term"
TIP = "#term-tip"
TIP_OPEN = "#term-tip:popover-open"

# ツールチップの最大の高さ（px）と、中を送るホイールの量・回数
TIP_MAX_HEIGHT_PX = 360
TIP_WHEEL_DELTA_PX = 600
TIP_WHEEL_TIMES = 6

# 高さに余裕のある画面（上に出す 360px のツールチップが印の上に収まる高さ）
TALL_SIZE = (1280, 1000)

# ツールチップの中身（種類ごとの見出し・項目のリンクと文・絞り込みの入力・区切り線）を読む
READ_TIP_SCRIPT = """() => {
    const tip = document.getElementById('term-tip');
    return {
        kinds: [...tip.querySelectorAll('.tt-kind')].map((e) => e.textContent),
        links: [...tip.querySelectorAll('a.tt-link')].map((a) => [a.dataset.id, a.textContent]),
        bodies: [...tip.querySelectorAll('.tt-item')].map((li) => [
            li.querySelector('a.tt-link').dataset.id,
            li.querySelector('.tt-body')?.textContent ?? null,
        ]),
        inputs: tip.querySelectorAll('input, textarea, [role="searchbox"]').length,
        groupLine: getComputedStyle(tip.querySelectorAll('.tt-group')[1]).borderTopWidth,
    };
}"""


def _alias_records(make_item: MakeItem) -> list[dict[str, Any]]:
    """用語 G-1・エイリアスを持たない資料 A-1・「特殊効果」に一致する資料 A-2～A-7 と調査 R-1・取り下げた資料 A-8 を返す。"""
    extra_docs = [
        make_item(
            f"A-{number}",
            title=f"追加の資料 {number}",
            aliases=[ALIAS_WORD],
            description=f"追加の資料 {number} の説明",
        )
        for number in EXTRA_DOC_NUMBERS
    ]
    return [
        make_item("G-1", title=ALIAS_WORD, meaning="画面に重ねる演出"),
        make_item("A-1"),
        make_item(
            "A-2",
            title="特殊効果のスキーマ",
            aliases=[ALIAS_WORD, OTHER_ALIAS_WORD],
            description="特殊効果の設定ファイルのキーと型",
        ),
        make_item(
            "A-3", title="炎ノード", aliases=[ALIAS_WORD], description="炎の見た目を決めるノード"
        ),
        *extra_docs,
        make_item(
            "A-8",
            title="古い資料",
            aliases=[ALIAS_WORD],
            withdrawn=True,
            reason="別の資料にまとめた",
        ),
        make_item(
            "R-1",
            title="特殊効果を重ねたときの描画の負荷",
            aliases=[ALIAS_WORD],
            description="ノードを 1〜8 個重ねたときの測り方と結果",
        ),
    ]


def _alias_bodies() -> dict[str, str]:
    """A-1 は印を持つ長い本文、A-2 は「特殊効果」を持つ本文、ほかの資料は語を持たない本文にする。"""
    bodies = {f"A-{number}.md": f"資料 A-{number} の本文\n" for number in range(2, 9)}
    bodies["A-1.md"] = ALIAS_BODY
    bodies["A-2.md"] = "特殊効果を重ねる\n"
    return bodies


def _tip_ids(page: Page) -> list[str]:
    """開いているツールチップに並ぶ項目の ID を返す。"""
    return page.eval_on_selector_all(f"{TIP} a.tt-link", "links => links.map(a => a.dataset.id)")


def _wheel_through_tip(page: Page) -> None:
    """ツールチップの真ん中にカーソルを置き、ホイールを回して中を末尾まで送る。"""
    box = page.locator(TIP).bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(TIP_WHEEL_TIMES):
        page.mouse.wheel(0, TIP_WHEEL_DELTA_PX)
        page.wait_for_timeout(60)
    page.wait_for_timeout(300)


def _section_text(page: Page, heading: str) -> str:
    """詳細パネルの見出し付きの節の文字を返す。"""
    return page.inner_text(f"aside.panel .d-sec:has(h3:text-is('{heading}'))")


def test_normal_when_aliases_matched(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """本文の語に一致した資料・調査をツールチップで読み、押して残して中を送り、リンクで詳細へ移る。キーボードでも同じツールチップを読める（正常系）。"""
    # 準備
    url = serve_preview(
        *_alias_records(make_item), settings=valid_settings, bodies=_alias_bodies()
    )
    page = open_preview(url, "#tab=docs&view=table&id=A-1", width=TALL_SIZE[0], height=TALL_SIZE[1])
    page.wait_for_selector(BODY_MARKS)
    hash_before = page.evaluate("location.hash")
    # 実行（A-1 の本文の印）
    marks = page.eval_on_selector_all(
        BODY_MARKS,
        "a => a.map(x => [x.textContent, x.dataset.ids, getComputedStyle(x).textDecorationLine, getComputedStyle(x).textDecorationStyle])",
    )
    # 印を画面の中ほどへ送り、「エフェクト」に乗せる
    page.locator(BODY_MARKS).first.evaluate("e => e.scrollIntoView({block: 'center'})")
    page.hover(f"{BODY_MARKS} >> nth=1")
    page.wait_for_selector(TIP_OPEN)
    other_ids = _tip_ids(page)
    page.mouse.move(2, 2)
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    # 実行（「特殊効果」の印に乗せる）
    mark = f"{BODY_MARKS} >> nth=0"
    page.hover(mark)
    page.wait_for_selector(TIP_OPEN)
    page.wait_for_timeout(200)
    tip = page.evaluate(READ_TIP_SCRIPT)
    placement = page.evaluate(
        """() => {
            const m = document.querySelector('aside.panel .md a.term').getBoundingClientRect();
            const t = document.getElementById('term-tip');
            return {
                above: t.getBoundingClientRect().bottom <= m.top,
                height: Math.round(t.getBoundingClientRect().height),
                scrollable: t.scrollHeight > t.clientHeight,
            };
        }"""
    )
    # 実行（押して、印から外してもツールチップを残し、中を送る）
    page.click(mark)
    page.mouse.move(2, 2)
    page.wait_for_timeout(400)
    kept = page.evaluate("document.querySelector('#term-tip').matches(':popover-open')")
    body_top_before = page.evaluate("document.querySelector('aside.panel .panel-body').scrollTop")
    _wheel_through_tip(page)
    scrolled = page.evaluate(
        """() => {
            const t = document.getElementById('term-tip');
            const last = [...t.querySelectorAll('a.tt-link')].at(-1).getBoundingClientRect();
            const box = t.getBoundingClientRect();
            return {
                id: [...t.querySelectorAll('a.tt-link')].at(-1).dataset.id,
                inside: last.bottom <= box.bottom + 1 && last.top >= box.top,
                bodyTop: document.querySelector('aside.panel .panel-body').scrollTop,
            };
        }"""
    )
    # 検証（印とツールチップ）
    # 「特殊効果」と「エフェクト」に点線の印が付く。「特殊効果」の印は取り下げた A-8 を含まない 8 件にまとまる
    assert marks == [
        ["特殊効果", "G-1 A-2 A-3 A-4 A-5 A-6 A-7 R-1", "underline", "dotted"],
        ["エフェクト", "A-2", "underline", "dotted"],
    ]
    assert other_ids == ["A-2"]
    # 用語 → 資料 → 調査の順に、種類ごとの見出しと区切り線で並び、全項目のタイトルが詳細へのリンクになる
    assert tip["kinds"] == ["用語 1", "資料 6", "調査 1"]
    assert tip["links"] == [
        ["G-1", "特殊効果"],
        ["A-2", "特殊効果のスキーマ"],
        ["A-3", "炎ノード"],
        ["A-4", "追加の資料 4"],
        ["A-5", "追加の資料 5"],
        ["A-6", "追加の資料 6"],
        ["A-7", "追加の資料 7"],
        ["R-1", "特殊効果を重ねたときの描画の負荷"],
    ]
    # G-1 は意味、資料・調査は説明を持つ。絞り込みの入力は無い
    assert tip["bodies"] == [
        ["G-1", "画面に重ねる演出"],
        ["A-2", "特殊効果の設定ファイルのキーと型"],
        ["A-3", "炎の見た目を決めるノード"],
        ["A-4", "追加の資料 4 の説明"],
        ["A-5", "追加の資料 5 の説明"],
        ["A-6", "追加の資料 6 の説明"],
        ["A-7", "追加の資料 7 の説明"],
        ["R-1", "ノードを 1〜8 個重ねたときの測り方と結果"],
    ]
    assert tip["inputs"] == 0
    assert tip["groupLine"] == "1px"
    # 印の上に出て、高さが上限で止まり、中を送れる
    assert placement == {"above": True, "height": TIP_MAX_HEIGHT_PX, "scrollable": True}
    # 押しても詳細へ移らず、印から外してもツールチップが出たままになる
    assert page.evaluate("location.hash") == hash_before
    assert kept is True
    # 中を送ると末尾の R-1 が画面に入り、後ろの本文は送られない
    assert scrolled == {"id": "R-1", "inside": True, "bodyTop": body_top_before}
    # 実行（A-3 のリンクを押す）
    page.click(f'{TIP} a.tt-link[data-id="A-3"]')
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === '炎ノード'")
    # 検証（A-3 の詳細）
    assert "id=A-3" in page.evaluate("location.hash")
    assert "炎の見た目を決めるノード" in _section_text(page, "説明")
    assert page.eval_on_selector_all(
        "aside.panel .d-sec:has(h3:text-is('エイリアス')) .tag", "t => t.map(x => x.textContent)"
    ) == [ALIAS_WORD]
    # 実行（A-2 の詳細を開き、本文の「特殊効果」にキーボードでフォーカスする）
    page.goto(f"{url}#tab=docs&view=table&id=A-2")
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === '特殊効果のスキーマ'"
    )
    page.wait_for_selector(BODY_MARKS)
    page.focus(BODY_MARKS)
    page.wait_for_selector(TIP_OPEN)
    own_excluded_ids = _tip_ids(page)
    # 実行（Tab でツールチップの中へ移り、Esc を押す）
    page.keyboard.press("Tab")
    first_link = page.evaluate("document.activeElement.dataset.id")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    after_escape = page.evaluate("document.activeElement.textContent")
    # 検証（A-2 の本文のツールチップ）
    assert own_excluded_ids == ["G-1", "A-3", "A-4", "A-5", "A-6", "A-7", "R-1"]
    assert first_link == "G-1"
    assert after_escape == ALIAS_WORD
