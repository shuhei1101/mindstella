"""部品設計『資料のエクスポートのメニュー』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from storybook_fixture_types import OpenStory

# メニューと、形式の 2 行・警告とエラーの下のボタンの行
MENU = "div.doc-export"
ROWS = f"{MENU} .dx-item"
FOOTER = f"{MENU} .dx-foot"

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 画面の幅から引く左右の余白（px）
SIDE_MARGIN_PX = 8

# 位置の比べで許す差（px）
TOLERANCE_PX = 2

# 見えるまで・フォーカスが置かれるまで待つミリ秒
SETTLE_MS = 500

# フォーカスがある要素の読み上げの名前（無ければ文字）
_FOCUS_NAME_JS = "() => document.activeElement?.textContent?.replace(/\\s+/g, ' ').trim() ?? ''"


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開き、メニューが開いてフォーカスが置かれるまで待つ。"""
    page = open_story(f"preview-docexportmenu--{state}")
    page.wait_for_selector(f"{MENU}:popover-open")
    page.wait_for_timeout(SETTLE_MS)
    return page


def _focused_text(page: Page) -> str:
    """フォーカスがある要素の文字（空白を 1 つにしたもの）を返す。"""
    return page.evaluate(_FOCUS_NAME_JS)


def test_choose(open_story: OpenStory) -> None:
    """形式を選ぶ。「HTML でエクスポート」と「Markdown でエクスポート」を名前と説明の 2 行で並べ、行の全体が押せて、フォーカスは「HTML でエクスポート」（正常系）。"""
    # 準備・実行
    page = _open(open_story, "choose")
    # 検証（メニューは見出しを読み上げの名前にしたダイアログ）
    menu = page.locator(MENU)
    assert menu.get_attribute("role") == "dialog"
    assert page.inner_text(f"{MENU} .pop-title") == "エクスポート"
    assert menu.get_attribute("aria-labelledby") == page.get_attribute(f"{MENU} .pop-title", "id")
    # 検証（形式の 2 行はボタンの組で、名前と説明を持つ）
    group = menu.get_by_role("group", name="エクスポート")
    expect(group).to_have_count(1)
    assert page.locator(f"{ROWS} .dx-name").all_inner_texts() == ["HTML でエクスポート", "Markdown でエクスポート"]
    assert page.locator(f"{ROWS} .dx-sub").all_inner_texts() == [
        "スタイルと用語のツールチップを含む 1 つのファイル",
        "本文の Markdown だけ",
    ]
    # 検証（行の全体が押せる: 行のボタンが、名前と説明の両方を含む）
    assert page.locator(f"{ROWS}").evaluate_all("rows => rows.map(r => r.tagName)") == ["BUTTON", "BUTTON"]
    # 検証（フォーカスは「HTML でエクスポート」）
    assert _focused_text(page).startswith("HTML でエクスポート")


def test_warn(open_story: OpenStory) -> None:
    """Markdown の警告。警告のアイコンと文の下に「戻る」「エクスポート」を置き、フォーカスは「エクスポート」（正常系）。"""
    # 準備・実行
    page = _open(open_story, "warn")
    # 検証
    assert page.inner_text(f"{MENU} .pop-title") == "Markdown でエクスポートしますか?"
    warning = page.locator(f"{MENU} .dx-warn")
    assert warning.locator("svg.icon").count() == 1
    assert warning.inner_text() == "埋め込んだ HTML・チャート・操作できる部品は含まれず、共通のスタイルも外れます。"
    assert page.locator(f"{FOOTER} button").all_inner_texts() == ["戻る", "エクスポート"]
    assert _focused_text(page) == "エクスポート"
    assert page.locator(ROWS).count() == 0


def test_busy(open_story: OpenStory) -> None:
    """HTML を組み立てている間。「HTML でエクスポート」のアイコンを回る輪にして説明を「エクスポートしています…」に替え、両方の行を押しても何もせず、「Markdown でエクスポート」の行は薄い（正常系）。"""
    # 準備・実行
    page = _open(open_story, "busy")
    menu = page.locator(MENU)
    html_row = page.locator(f"{ROWS}[data-format='html']")
    markdown_row = page.locator(f"{ROWS}[data-format='md']")
    # 検証（組み立て中を知らせ、行は `disabled` にせず `aria-disabled` でフォーカスを残す）
    assert menu.get_attribute("aria-busy") == "true"
    assert html_row.locator(".dx-sub").inner_text() == "エクスポートしています…"
    assert html_row.locator(".dx-sub").get_attribute("role") == "status"
    for row in (html_row, markdown_row):
        assert row.get_attribute("aria-disabled") == "true"
        assert row.get_attribute("disabled") is None
    assert _focused_text(page).startswith("HTML でエクスポート")
    # 検証（アイコンは回る輪に替わり、「Markdown でエクスポート」の行は薄い）
    assert html_row.locator("svg").evaluate("svg => getComputedStyle(svg).visibility") == "hidden"
    assert html_row.evaluate("row => getComputedStyle(row, '::before').animationName") != "none"
    html_opacity = float(html_row.evaluate("row => getComputedStyle(row).opacity"))
    markdown_opacity = float(markdown_row.evaluate("row => getComputedStyle(row).opacity"))
    assert markdown_opacity < html_opacity
    # 実行（行を押す）
    html_row.click(force=True)
    markdown_row.click(force=True)
    # 検証（押しても使う側へ知らせない）
    assert menu.get_attribute("aria-busy") == "true"
    assert html_row.locator(".dx-sub").inner_text() == "エクスポートしています…"


def test_error(open_story: OpenStory) -> None:
    """HTML を組み立てられなかった。何が起きたかの文を `role="alert"` で伝え、下に「戻る」「再試行」を置き、フォーカスは「再試行」（正常系）。"""
    # 準備・実行
    page = _open(open_story, "error")
    # 検証
    assert page.inner_text(f"{MENU} .pop-title") == "エクスポートできませんでした"
    alert = page.locator(MENU).get_by_role("alert")
    expect(alert).to_have_text(
        "mdmark のスタイルとスクリプトを読み込めませんでした。ネットワークにつながっているか確かめて、再試行してください。"
    )
    assert alert.locator("svg.icon").count() == 1
    assert page.locator(f"{FOOTER} button").all_inner_texts() == ["戻る", "再試行"]
    assert _focused_text(page) == "再試行"


def test_back_from_warn(open_story: OpenStory) -> None:
    """警告から「戻る」で戻した。形式を選ぶ並びで、フォーカスは「Markdown でエクスポート」（正常系）。"""
    # 準備・実行
    page = _open(open_story, "back-from-warn")
    # 検証
    assert page.inner_text(f"{MENU} .pop-title") == "エクスポート"
    assert page.locator(f"{ROWS} .dx-name").all_inner_texts() == ["HTML でエクスポート", "Markdown でエクスポート"]
    assert _focused_text(page).startswith("Markdown でエクスポート")


def test_narrow(open_story: OpenStory) -> None:
    """画面の幅 390px。メニューは画面の幅から左右 8px を引いた幅を超えず、行の説明を折り返す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_timeout(SETTLE_MS)
    menu_box = page.locator(MENU).bounding_box()
    sub_box = page.locator(f"{ROWS} .dx-sub").first.bounding_box()
    line_height = page.locator(f"{ROWS} .dx-sub").first.evaluate("e => parseFloat(getComputedStyle(e).lineHeight)")
    # 検証
    assert menu_box is not None
    assert sub_box is not None
    assert menu_box["width"] <= NARROW_SIZE["width"] - SIDE_MARGIN_PX * 2 + TOLERANCE_PX
    # 説明は 2 行以上に折り返す
    assert sub_box["height"] >= line_height * 2 - TOLERANCE_PX
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_warn_narrow(open_story: OpenStory) -> None:
    """画面の幅 390px の警告。警告の文を折り返し、「戻る」「エクスポート」を右端に揃える（正常系）。"""
    # 準備・実行
    page = _open(open_story, "warn-narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_timeout(SETTLE_MS)
    text_box = page.locator(f"{MENU} .dx-warn p").bounding_box()
    line_height = page.locator(f"{MENU} .dx-warn p").evaluate("e => parseFloat(getComputedStyle(e).lineHeight)")
    footer_box = page.locator(FOOTER).bounding_box()
    last_box = page.locator(f"{FOOTER} button").last.bounding_box()
    menu_box = page.locator(MENU).bounding_box()
    # 検証
    assert text_box is not None
    assert footer_box is not None
    assert last_box is not None
    assert menu_box is not None
    assert text_box["height"] >= line_height * 2 - TOLERANCE_PX
    assert menu_box["width"] <= NARROW_SIZE["width"] - SIDE_MARGIN_PX * 2 + TOLERANCE_PX
    # 「エクスポート」は、ボタンの行の右端にある
    assert abs((last_box["x"] + last_box["width"]) - (footer_box["x"] + footer_box["width"])) <= TOLERANCE_PX
    first_box = page.locator(f"{FOOTER} button").first.bounding_box()
    assert first_box is not None
    assert first_box["x"] < last_box["x"]
