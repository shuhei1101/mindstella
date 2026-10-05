"""部品設計『変更履歴』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# モーダルが開くのを待つ上限ミリ秒
DIALOG_TIMEOUT_MS = 5_000

# 一覧の行の時点の識別子・名前・件数の文字を、上から順に読む
ROWS_SCRIPT = """() => [...document.querySelectorAll('dialog.hist .hist-item')].map(row => ({
    sel: row.dataset.sel,
    name: row.querySelector('.hist-name').textContent,
    n: row.querySelector('.hist-n')?.textContent ?? null,
    current: row.getAttribute('aria-current'),
}))"""


def _open_dialog(open_story: OpenStory, story_id: str) -> Page:
    """ストーリーを開き、モーダルが `showModal()` で開くのを待つ。"""
    page = open_story(story_id)
    page.wait_for_selector("dialog.hist[open]", timeout=DIALOG_TIMEOUT_MS)
    return page


def test_since_selected(open_story: OpenStory) -> None:
    """「前回開いてから」を選んでいる。先頭から差分を出さない・まだまとめていない変更・前回開いてから・まとまり 2 つを並べる（正常系）。"""
    # 準備・実行
    page = _open_dialog(open_story, "preview-historydialog--since-selected")
    # 検証
    rows = page.evaluate(ROWS_SCRIPT)
    assert [row["sel"] for row in rows] == ["", "pending", "since", "V-2", "V-1"]
    assert [row["current"] for row in rows] == [None, None, "true", None, None]
    assert [row["n"] for row in rows] == [None, "2 件", "5 件", "3 件", "2 件"]
    # モーダルの見出しが読み上げ名で、選んでいる行にチェックの印とフォーカスがある
    labelled = page.get_attribute("dialog.hist", "aria-labelledby")
    assert page.inner_text(f"#{labelled}") == "変更履歴"
    assert page.locator("dialog.hist .hist-item[data-sel='since'] .hist-check svg.icon").count() == 1
    assert page.evaluate("document.activeElement?.dataset?.sel") == "since"
    assert page.evaluate("document.querySelector('dialog.hist').matches(':modal')") is True


def test_off(open_story: OpenStory) -> None:
    """差分を出していない。「差分を出さない（今の内容）」にチェックを付ける（正常系）。"""
    # 準備・実行
    page = _open_dialog(open_story, "preview-historydialog--off")
    # 検証
    rows = page.evaluate(ROWS_SCRIPT)
    assert [row["current"] for row in rows] == ["true", None, None, None, None]
    assert rows[0]["name"] == "差分を出さない（今の内容）"
    assert page.locator("dialog.hist .hist-item[data-sel=''] .hist-check svg.icon").count() == 1


def test_no_pending(open_story: OpenStory) -> None:
    """まだまとめていない変更が無い。その行を出さない（正常系）。"""
    # 準備・実行
    page = _open_dialog(open_story, "preview-historydialog--no-pending")
    # 検証
    rows = page.evaluate(ROWS_SCRIPT)
    assert [row["sel"] for row in rows] == ["", "since", "V-2", "V-1"]


def test_long_name(open_story: OpenStory) -> None:
    """長い説明のまとまり。名前を折り返し、日時と件数の列を押し出さない（正常系）。"""
    # 準備・実行
    page = _open_dialog(open_story, "preview-historydialog--long-name")
    # 検証
    row = page.locator("dialog.hist .hist-item[data-sel='V-3']")
    name_box = row.locator(".hist-name").bounding_box()
    count_box = row.locator(".hist-n").bounding_box()
    dialog_box = page.locator("dialog.hist").bounding_box()
    assert name_box is not None
    assert count_box is not None
    assert dialog_box is not None
    # 名前が 2 行以上に折り返し、件数が名前の右で、モーダルの中にある
    assert name_box["height"] > 2 * page.evaluate(
        "parseFloat(getComputedStyle(document.querySelector('.hist-sub')).lineHeight)"
    )
    assert name_box["x"] + name_box["width"] <= count_box["x"]
    assert count_box["x"] + count_box["width"] <= dialog_box["x"] + dialog_box["width"]
    assert row.locator(".hist-n").inner_text() == "12 件"


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。モーダルを画面幅に合わせ、一覧を縦に送る（正常系）。"""
    # 準備
    page = _open_dialog(open_story, "preview-historydialog--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行
    dialog_box = page.locator("dialog.hist").bounding_box()
    # 検証
    assert dialog_box is not None
    assert dialog_box["x"] >= 0
    assert dialog_box["x"] + dialog_box["width"] <= 390
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.evaluate("getComputedStyle(document.querySelector('.hist-list')).overflowY") == "auto"
