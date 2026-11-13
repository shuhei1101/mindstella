"""画面設計『全体の検索.tsx』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, ViewportSize, expect
from preview_fixture_types import WritePreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeItem

# 全体の検索のモーダル
DIALOG_NAME = "すべての項目を検索"

# 検索の言葉が空のときの案内
EMPTY_HINT = "ID・タイトル・本文で、すべての項目を検索します。"

# 当たらないときの文
NO_HIT_TEXT = "該当する項目はありません。別の条件を試してください。"

# 検索の中を横に送らせない幅（幅 389px 以下で入力欄を縮める）
NARROW: ViewportSize = {"width": 320, "height": 640}

# 検索のモーダルの中が横にはみ出す量を返す
DIALOG_OVERFLOW_SCRIPT = """() => {
    const dialog = document.querySelector('[role="dialog"]');
    return dialog.scrollWidth - dialog.clientWidth;
}"""


def _dialog(page: Page) -> Locator:
    """全体の検索のモーダルを返す。"""
    return page.get_by_role("dialog", name=DIALOG_NAME)


def _search(page: Page) -> str:
    """URL の search を、値を戻して返す。"""
    value: str = page.evaluate("decodeURIComponent(location.search)")
    return value


def test_open_key(page: Page, spa_preview: str) -> None:
    """`Ctrl+K` で全体の検索を開き、URL に `search=1` を書いて検索の言葉にフォーカスを置く。履歴に積まない（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks")
    before = page.evaluate("history.length")
    # 実行
    page.keyboard.press("Control+k")
    # 検証
    expect(page.get_by_role("textbox", name="検索キーワード")).to_be_focused()
    assert _search(page) == "?tab=tasks&search=1"
    assert page.evaluate("history.length") == before
    expect(_dialog(page)).to_contain_text(EMPTY_HINT)


def test_open_from_topbar(page: Page, spa_preview: str) -> None:
    """トップバーの検索の入口を押しても全体の検索を開く（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks")
    # 実行
    page.get_by_role("button", name="すべての項目を検索").click()
    # 検証
    expect(_dialog(page)).to_be_visible()
    assert _search(page) == "?tab=tasks&search=1"


def test_query(page: Page, spa_preview: str) -> None:
    """入力のたびに URL の `q` を置き換え、当たった項目を段ごとの見出しの下に、種類の順で並べる（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks&search=1")
    before = page.evaluate("history.length")
    # 実行
    page.get_by_role("textbox", name="検索キーワード").fill("画面")
    # 検証
    page.wait_for_url("**q=*")
    assert _search(page) == "?tab=tasks&search=1&q=画面"
    assert page.evaluate("history.length") == before
    group = _dialog(page).get_by_role("group", name="タイトルに一致")
    expect(group.get_by_role("heading", level=2)).to_have_text("タイトルに一致")
    expect(group.get_by_role("option")).to_have_count(2)
    expect(group.get_by_role("option").nth(0)).to_contain_text("D-2")
    expect(group.get_by_role("option").nth(1)).to_contain_text("T-1")


def test_query_when_in_url(page: Page, spa_preview: str) -> None:
    """URL の `q` を検索の言葉の初期値にする（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks&search=1&q=D-1")
    # 検証
    expect(page.get_by_role("textbox", name="検索キーワード")).to_have_value("D-1")
    expect(_dialog(page).get_by_role("group", name="完全に一致").get_by_role("option")).to_contain_text("D-1")


def test_query_when_no_hit(page: Page, spa_preview: str) -> None:
    """当たらないときは、その旨の文を出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks&search=1&q=%E7%84%A1%E3%81%84%E8%A8%80%E8%91%89")
    # 検証
    expect(_dialog(page)).to_contain_text(NO_HIT_TEXT)


def test_query_when_html_body(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """HTML の本文は描いた文で当て、タグ・属性の値では当てない（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", title="画面の資料", body="A-1.html"),
        bodies={"A-1.html": '<p class="unmatched-class">描いた文の言葉</p>'},
    )
    open_spa(page, url, "?search=1")
    search_box = page.get_by_role("textbox", name="検索キーワード")
    # 実行（描いた文の言葉）
    search_box.fill("描いた文の言葉")
    rendered = _dialog(page).get_by_role("option")
    expect(rendered).to_have_count(1)
    # 実行（属性の値）
    search_box.fill("unmatched-class")
    # 検証
    expect(_dialog(page)).to_contain_text(NO_HIT_TEXT)


def test_open_item(page: Page, spa_preview: str) -> None:
    """上下の矢印で選んで Enter で、その項目の種類の画面と詳細パネルを開き、検索を閉じる（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks&search=1&q=%E7%94%BB%E9%9D%A2")
    expect(_dialog(page).get_by_role("option")).to_have_count(2)
    # 実行
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    # 検証
    page.wait_for_url("**/spa/?tab=tasks&id=T-1")
    expect(_dialog(page)).to_be_hidden()
    expect(page.get_by_role("complementary", name="詳細")).to_contain_text("画面を作る")


def test_close(page: Page, spa_preview: str) -> None:
    """閉じるボタンで検索を閉じて URL から `search`・`q` を外し、開く前の要素へフォーカスを戻す（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks")
    page.get_by_role("button", name="すべての項目を検索").click()
    page.get_by_role("textbox", name="検索キーワード").fill("画面")
    page.wait_for_url("**q=*")
    # 実行
    page.get_by_role("button", name="検索を閉じる").click()
    # 検証
    page.wait_for_url("**/spa/?tab=tasks")
    expect(_dialog(page)).to_be_hidden()
    expect(page.get_by_role("button", name="すべての項目を検索")).to_be_focused()


def test_close_when_escape(page: Page, spa_preview: str) -> None:
    """Esc でも検索を閉じ、URL から `search` を外す（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks&search=1")
    expect(_dialog(page)).to_be_visible()
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_url("**/spa/?tab=tasks")
    expect(_dialog(page)).to_be_hidden()


def test_narrow(page: Page, spa_preview: str) -> None:
    """幅 389px 以下では、閉じるボタンを入力欄と同じ行の窓の中に置き、検索の中を横に送らせない（正常系）。"""
    # 準備
    page.set_viewport_size(NARROW)
    # 実行
    open_spa(page, spa_preview, "?tab=tasks&search=1")
    # 検証
    close = page.get_by_role("button", name="検索を閉じる").bounding_box()
    box = page.get_by_role("textbox", name="検索キーワード").bounding_box()
    assert close is not None
    assert box is not None
    assert close["x"] + close["width"] <= NARROW["width"]
    assert abs((close["y"] + close["height"] / 2) - (box["y"] + box["height"] / 2)) <= 2
    assert page.evaluate(DIALOG_OVERFLOW_SCRIPT) == 0
