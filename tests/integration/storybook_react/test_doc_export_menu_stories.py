"""部品設計『資料のエクスポートのメニュー.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-docexportmenu--choose",
    "shared-docexportmenu--warn",
    "shared-docexportmenu--busy",
    "shared-docexportmenu--error",
    "shared-docexportmenu--back-from-warn",
    "shared-docexportmenu--narrow",
    "shared-docexportmenu--warn-narrow",
)

# 幅 390px の画面の大きさ
NARROW_SIZE = {"width": 390, "height": 844}


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# 警告の文
WARN_TEXT = "埋め込んだ HTML・チャート・操作できる部品は含まれず、共通のスタイルも外れます。"

# 組み立てられなかった文
ERROR_TEXT = "mdmark のスタイルとスクリプトを読み込めませんでした。ネットワークにつながっているか確かめて、再試行してください。"


def test_choose(open_story: OpenStory) -> None:
    """形式を選ぶ。見出し「エクスポート」の dialog に、名前と説明を読み上げに含む 2 行のボタンの組を並べ、フォーカスは「HTML でエクスポート」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-docexportmenu--choose").get_by_role("dialog", name="エクスポート")
    group = dialog.get_by_role("group", name="エクスポート")
    html = group.get_by_role(
        "button", name="HTML でエクスポート スタイルと用語のツールチップを含む 1 つのファイル"
    )
    # 検証
    expect(html).to_be_focused()
    expect(
        group.get_by_role("button", name="Markdown でエクスポート 本文の Markdown だけ")
    ).to_be_visible()
    expect(group.get_by_role("button")).to_have_count(2)


def test_warn(open_story: OpenStory) -> None:
    """Markdown の警告。警告のアイコンと文の下に「戻る」「エクスポート」を並べ、フォーカスは「エクスポート」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-docexportmenu--warn").get_by_role(
        "dialog", name="Markdown でエクスポートしますか?"
    )
    # 検証
    expect(dialog.get_by_text(WARN_TEXT)).to_be_visible()
    assert dialog.locator("p", has_text=WARN_TEXT).locator("svg").count() == 1
    expect(dialog.get_by_role("button")).to_have_text(["戻る", "エクスポート"])
    expect(dialog.get_by_role("button", name="エクスポート")).to_be_focused()


def test_busy(open_story: OpenStory) -> None:
    """HTML を組み立てている間。`aria-busy`、回る輪と「エクスポートしています…」の status、行は `aria-disabled` で、Markdown の行は薄い（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-docexportmenu--busy").get_by_role("dialog", name="エクスポート")
    buttons = dialog.get_by_role("button")
    # 検証
    expect(dialog).to_have_attribute("aria-busy", "true")
    expect(dialog.get_by_role("status")).to_have_text("エクスポートしています…")
    assert buttons.evaluate_all("rows => rows.map((r) => r.getAttribute('aria-disabled'))") == [
        "true",
        "true",
    ]
    assert (
        buttons.nth(0).locator("svg").evaluate("e => getComputedStyle(e).animationName") != "none"
    )
    assert float(buttons.nth(1).evaluate("e => getComputedStyle(e).opacity")) < 1
    expect(buttons.nth(0)).to_be_focused()


def test_error(open_story: OpenStory) -> None:
    """HTML を組み立てられなかった。文を alert で伝え、下に「戻る」「再試行」。フォーカスは「再試行」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-docexportmenu--error").get_by_role(
        "dialog", name="エクスポートできませんでした"
    )
    # 検証
    expect(dialog.get_by_role("alert")).to_have_text(ERROR_TEXT)
    expect(dialog.get_by_role("button")).to_have_text(["戻る", "再試行"])
    expect(dialog.get_by_role("button", name="再試行")).to_be_focused()


def test_back_from_warn(open_story: OpenStory) -> None:
    """警告から「戻る」で戻した。形式を選ぶ並びで、フォーカスは「Markdown でエクスポート」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-docexportmenu--back-from-warn").get_by_role(
        "dialog", name="エクスポート"
    )
    # 検証
    expect(
        dialog.get_by_role("button", name="Markdown でエクスポート 本文の Markdown だけ")
    ).to_be_focused()


def test_narrow(open_story: OpenStory) -> None:
    """画面の幅 390px。メニューは画面の幅から左右 8px を引いた幅を超えず、画面を横に送らない（正常系）。"""
    # 準備
    page = open_story("shared-docexportmenu--narrow")
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    box = page.get_by_role("dialog", name="エクスポート").bounding_box()
    # 検証
    assert box is not None
    assert box["width"] <= NARROW_SIZE["width"] - 16
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def test_warn_narrow(open_story: OpenStory) -> None:
    """画面の幅 390px の警告。警告の文を折り返し、「戻る」「エクスポート」を右端に揃える（正常系）。"""
    # 準備
    page = open_story("shared-docexportmenu--warn-narrow")
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    dialog = page.get_by_role("dialog", name="Markdown でエクスポートしますか?")
    text = dialog.get_by_text(WARN_TEXT).bounding_box()
    confirm = dialog.get_by_role("button", name="エクスポート").bounding_box()
    actions = dialog.get_by_role("button", name="エクスポート").locator("xpath=..").bounding_box()
    # 検証
    assert text is not None
    assert confirm is not None
    assert actions is not None
    assert text["height"] > 24
    assert abs((confirm["x"] + confirm["width"]) - (actions["x"] + actions["width"])) <= 1
