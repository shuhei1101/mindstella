"""部品設計『表示の設定』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 表示の設定のパネルの外側
PANEL = "aside.settings-drawer"

# 種類の行（チェックの箱を持つ行）の名前・チェック・件数を読む
_KINDS_SCRIPT = """() => [...document.querySelectorAll('.st-kinds li:not(.st-all):not(.st-always)')].map((row) => ({
    name: row.querySelector('.st-k-label').textContent,
    checked: row.querySelector('input').checked,
    count: row.querySelector('.n').textContent,
}))"""


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開く。"""
    return open_story(f"preview-settingspanel--{state}")


def _buttons(page: Page) -> list[str]:
    """パネルの本文のボタンの文字を返す。"""
    return page.locator(f"{PANEL} .st-wrap button").all_inner_texts()


def test_default(open_story: OpenStory) -> None:
    """開いた直後（ワークスペースの既定のまま）。「既定に戻す」と「ワークスペースの既定にする」を出さず、そのことを文言で示す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "default")
    # 検証
    assert page.inner_text(f"{PANEL} h2") == "表示の設定"
    assert page.get_attribute(PANEL, "aria-label") == "表示の設定"
    # 見た目はネットワークのドロップダウンで選ぶので、パネルには選びを出さない
    assert page.locator(f"{PANEL} .st-look").count() == 0
    assert page.locator(f"{PANEL} input[type=radio]").count() == 0
    assert _buttons(page) == []
    text = page.inner_text(f"{PANEL} .st-wrap")
    assert "ワークスペースの既定のまま表示しています。" in text
    assert "今の選びはワークスペースの既定と同じです。" in text
    # 概要とネットワークは、チェックの箱を持たない常に表示の行
    assert page.locator(".st-always").count() == 2
    assert page.locator(".st-always input").count() == 0
    assert page.locator(".st-all input").evaluate("box => box.checked") is True
    assert page.inner_text(".st-all .n") == "7/7"


def test_overridden(open_story: OpenStory) -> None:
    """この端末で変えている。上書きを持つ 4 項目を並べて「既定に戻す」を出し、線で区切った下に「ワークスペースの既定にする」を置く（正常系）。"""
    # 準備・実行
    page = _open(open_story, "overridden")
    # 検証
    over = page.inner_text(f"{PANEL} .st-over")
    assert "この端末で変えている項目" in over
    assert "ネットワークの見た目・表示する種類・ライト / ダーク・表の列（調査）" in over
    assert _buttons(page) == ["既定に戻す", "ワークスペースの既定にする"]
    # 見た目を上書きしていても、パネルには見た目の選びを出さない
    assert page.locator(f"{PANEL} .st-look").count() == 0
    assert page.get_attribute(f"{PANEL} .st-save button", "aria-haspopup") == "dialog"
    # 保存のボタンは、線で区切った下に置く
    assert (
        page.eval_on_selector(f"{PANEL} .st-save", "e => getComputedStyle(e).borderTopWidth")
        != "0px"
    )


def test_some_kinds_hidden(open_story: OpenStory) -> None:
    """用語集と会話ログを外した。「すべて」を途中の印にし、`5/7` を出す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "some-kinds-hidden")
    # 検証
    kinds = page.evaluate(_KINDS_SCRIPT)
    assert [kind["checked"] for kind in kinds] == [True, True, True, True, False, True, False]
    assert page.locator(".st-all input").evaluate("box => box.indeterminate") is True
    assert page.inner_text(".st-all .n") == "5/7"
    assert [kind["count"] for kind in kinds] == ["12", "8", "3", "5", "9", "4", "20"]


def test_saved(open_story: OpenStory) -> None:
    """既定にした直後。今の選びが既定と同じになり、ボタンの代わりにそのことと保存した知らせを出す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "saved")
    # 検証
    assert "今の選びはワークスペースの既定と同じです。" in page.inner_text(f"{PANEL} .st-save")
    assert _buttons(page) == ["既定に戻す"]
    message = page.locator(f"{PANEL} .st-msg")
    assert message.get_attribute("role") == "status"
    assert message.inner_text() == "ワークスペースの既定にしました（10/05 14:20）。"
    assert message.locator("svg.icon").count() == 1


def test_defaults_arrived(open_story: OpenStory) -> None:
    """他の人が保存した既定が届いた。上書きを持たない項目に新しい既定が当たり、パネルに知らせを残す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "defaults-arrived")
    # 検証
    message = page.locator(f"{PANEL} .st-msg")
    assert message.inner_text() == "ワークスペースの既定が変わりました（10/05 14:22）。"
    assert message.get_attribute("class") == "st-msg info"
    assert page.locator(f"{PANEL} .st-look").count() == 0
    assert _buttons(page) == []


def test_no_storage(open_story: OpenStory) -> None:
    """端末の保存領域に書けない。選んだ表示は当てるが、開いている間だけであることを先頭に出す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "no-storage")
    # 検証
    note = page.locator(f"{PANEL} .st-note")
    assert note.get_attribute("role") == "alert"
    assert note.inner_text() == (
        "この端末に保存できません。選んだ表示は、このページを開いている間だけ当たります。"
    )
    # 先頭に出す
    assert (
        page.eval_on_selector(f"{PANEL} .st-wrap", "e => e.firstElementChild.className")
        == "st-note"
    )


def test_export(open_story: OpenStory) -> None:
    """配る書き出し。見た目・表示する種類は変えられ、「ワークスペースの既定にする」は出さない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "export")
    # 検証
    assert _buttons(page) == ["既定に戻す"]
    assert page.locator(f"{PANEL} .st-save").count() == 0
    assert page.locator(f"{PANEL} .st-look").count() == 0
    assert page.locator(f"{PANEL} .st-kinds input").count() == 8


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。画面の幅いっぱいに出し、行の高さと押せる的は変えない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_timeout(500)
    # 検証
    box = page.locator(PANEL).bounding_box()
    assert box is not None
    assert box["x"] == 0
    assert box["width"] == NARROW_SIZE["width"]
    row = page.locator(".st-kinds label").first.bounding_box()
    assert row is not None
    assert row["height"] >= 40
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
