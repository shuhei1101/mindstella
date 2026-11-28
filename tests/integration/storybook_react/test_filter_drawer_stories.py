"""部品設計『絞り込み.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-filterdrawer--default",
    "shared-filterdrawer--selected",
    "shared-filterdrawer--zero-value",
    "shared-filterdrawer--long-tag",
    "shared-filterdrawer--no-match",
    "shared-filterdrawer--narrow",
    "shared-filterdrawer--text-conditions",
    "shared-filterdrawer--tag-match-all",
    "shared-filterdrawer--tag-match-any",
    "shared-filterdrawer--presets",
    "shared-filterdrawer--preset-applied",
    "shared-filterdrawer--tag-detail",
    "shared-filterdrawer--preset-save-no-tag",
    "shared-filterdrawer--preset-save-open",
    "shared-filterdrawer--changed-condition",
    "shared-filterdrawer--changed-only",
    "shared-filterdrawer--changed-none",
)

# ドロワーの幅（px）。コメントの一覧と同じ
DRAWER_WIDTH_PX = 420

# 幅 900px 以下で開くときの画面の大きさ
NARROW_SIZE = {"width": 390, "height": 844}


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_default(open_story: OpenStory) -> None:
    """何も選んでいない。見出しの右は「8 件」で、「解除」と「すべて解除」を出さず、条件は fieldset と legend で組む（正常系）。"""
    # 準備・実行
    page = open_story("shared-filterdrawer--default")
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog).to_contain_text("8 件")
    expect(dialog.locator("legend")).to_have_text(["種類", "状態", "タグ"])
    assert dialog.get_by_role("button", name="すべて解除").count() == 0
    assert dialog.get_by_role("button", name="解除").count() == 0
    expect(dialog.get_by_role("button", name="8 件を表示")).to_be_visible()
    assert dialog.evaluate("e => e.getBoundingClientRect().width") == DRAWER_WIDTH_PX
    # 検証（開いたら最初の値へフォーカスを移す）
    expect(dialog.get_by_role("checkbox", name="作業")).to_be_focused()


def test_selected(open_story: OpenStory) -> None:
    """状態に 4 つ・タグに 1 つを選んでいる。「36 件中 3 件」、選んだ条件に「{件数} 件を選択」と「解除」、下端に「すべて解除」と「3 件を表示」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--selected").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog).to_contain_text("36 件中 3 件")
    expect(dialog.locator("fieldset").nth(0).locator("legend")).to_contain_text("4 件を選択")
    expect(dialog.locator("fieldset").nth(1).locator("legend")).to_contain_text("1 件を選択")
    expect(dialog.get_by_role("button", name="状態の条件を解除")).to_be_visible()
    expect(dialog.get_by_role("button", name="タグの条件を解除")).to_be_visible()
    expect(dialog.get_by_role("button", name="すべて解除")).to_be_visible()
    expect(dialog.get_by_role("button", name="3 件を表示")).to_be_visible()
    expect(dialog.get_by_role("checkbox", name="要見直し")).to_be_checked()


def test_zero_value(open_story: OpenStory) -> None:
    """今の条件で 0 件になる値は文字と件数を薄くし、件数の 0 でも伝え、選べるまま残す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--zero-value").get_by_role("dialog", name="絞り込み")
    zero = dialog.locator("li", has_text="未整理")
    some = dialog.locator("li", has_text="未決定")
    # 検証
    expect(zero.get_by_label("0 件")).to_have_text("0")
    expect(dialog.get_by_role("checkbox", name="未整理")).to_be_enabled()
    assert zero.locator("label").evaluate("e => getComputedStyle(e).color") != some.locator("label").evaluate("e => getComputedStyle(e).color")


def test_long_tag(open_story: OpenStory) -> None:
    """長いタグは値の文字を折り返し、件数の列を押し出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--long-tag").get_by_role("dialog", name="絞り込み")
    long_label = dialog.locator("li label").first
    count = long_label.get_by_label("12 件").bounding_box()
    box = long_label.bounding_box()
    short = dialog.locator("li label").nth(1).bounding_box()
    # 検証
    assert count is not None
    assert box is not None
    assert short is not None
    assert box["height"] > short["height"]
    assert count["x"] + count["width"] <= box["x"] + box["width"] + 1


def test_no_match(open_story: OpenStory) -> None:
    """該当なし。見出しの右は「8 件中 0 件」、下端のボタンは「0 件を表示」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--no-match").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog).to_contain_text("8 件中 0 件")
    expect(dialog.get_by_role("button", name="0 件を表示")).to_be_visible()


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。画面の幅いっぱいに重ねる（正常系）。"""
    # 準備
    page = open_story("shared-filterdrawer--narrow")
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    assert dialog.evaluate("e => e.getBoundingClientRect().width") == NARROW_SIZE["width"]
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def test_text_conditions(open_story: OpenStory) -> None:
    """用語の欄に「移し」を入れている。値の条件より上に「文字を含む」と列ごとの欄を並べ、見出しの右は「6 件中 1 件」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--text-conditions").get_by_role(
        "dialog", name="絞り込み"
    )
    # 検証
    expect(dialog.locator("legend").first).to_have_text("文字を含む")
    expect(dialog.get_by_label("用語")).to_have_value("移し")
    expect(dialog.get_by_label("ID")).to_have_value("")
    assert dialog.locator("[data-text-key]").evaluate_all(
        "inputs => inputs.map((i) => i.dataset.textKey)"
    ) == ["id", "title", "meaning", "aliases", "avoid"]
    expect(dialog).to_contain_text("6 件中 1 件")
    # 検証（初めて開くときは先頭の文字の欄へフォーカスを移す）
    expect(dialog.get_by_label("ID")).to_be_focused()


@pytest.mark.parametrize(
    ("state", "checked"),
    [
        pytest.param("shared-filterdrawer--tag-match-all", "all", id="all"),
        pytest.param("shared-filterdrawer--tag-match-any", "any", id="any"),
    ],
)
def test_tag_match(open_story: OpenStory, state: str, checked: str) -> None:
    """タグの条件の下に組み合わせ方のラジオボタンを出し、選んだ方を選択済みにする（正常系）。"""
    # 準備・実行
    page = open_story(state)
    group = page.get_by_role("group", name="タグの組み合わせ方")
    # 検証
    expect(group.get_by_role("radio", name="すべて含む")).to_be_attached()
    expect(group.get_by_role("radio", name="どれかを含む")).to_be_attached()
    expect(group.locator(f"input[data-tag-match='{checked}']")).to_be_checked()


def test_presets(open_story: OpenStory) -> None:
    """値の条件より上にプリセットを件数つきで並べ、0 件のプリセットにも「0 件」を出して選択できるまま残す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--presets").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.locator("legend").first).to_have_text("プリセット")
    expect(dialog.get_by_role("button", name="画面の設計 2 件")).to_have_attribute("aria-pressed", "false")
    empty = dialog.get_by_role("button", name="通知 0 件")
    expect(empty).to_be_enabled()
    expect(empty).to_have_attribute("aria-pressed", "false")


def test_preset_applied(open_story: OpenStory) -> None:
    """今のタグの条件と同じプリセットを選択済みの見た目にする（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--preset-applied").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.get_by_role("button", name="廃止する画面 1 件")).to_have_attribute("aria-pressed", "true")
    expect(dialog.get_by_role("button", name="画面の設計 2 件")).to_have_attribute("aria-pressed", "false")


def test_tag_detail(open_story: OpenStory) -> None:
    """簡易で表せない式は詳細の表示にし、簡易を選択できなくし、タグのチェックボックスと組み合わせ方の切り替えを出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--tag-detail").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.get_by_role("radio", name="詳細")).to_be_checked()
    expect(dialog.get_by_role("radio", name="簡易")).to_be_disabled()
    assert dialog.get_by_role("checkbox", name="プレビュー").count() == 0
    assert dialog.get_by_role("radio", name="すべて含む").count() == 0
    expect(dialog.get_by_role("combobox", name="条件の組み合わせ")).to_have_value("and")



def test_preset_save_no_tag(open_story: OpenStory) -> None:
    """タグの条件が無いと、プリセットのまとまりの下の「プリセットとして保存」を押せない見た目にし、理由を出す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--preset-save-no-tag").get_by_role("dialog", name="絞り込み")
    button = dialog.get_by_role("button", name="プリセットとして保存")
    # 検証
    expect(button).to_have_attribute("aria-disabled", "true")
    expect(button).to_have_accessible_description("タグの条件を選ぶと、プリセットとして保存できます。")


def test_preset_save_open(open_story: OpenStory) -> None:
    """タグと状態を選んで名前の入力を開くと、タグの条件だけを保存する旨を出す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--preset-save-open").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.get_by_label("プリセットの名前")).to_be_visible()
    expect(dialog.get_by_text("タグの条件だけを保存します。状態・種類・文字の条件は保存しません。")).to_be_visible()


def test_changed_condition(open_story: OpenStory) -> None:
    """先頭に「変更」の条件を並べ、値「未読の変更あり」の前に未読のマーカーと同じ色の丸を付ける（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--changed-condition").get_by_role("dialog", name="絞り込み")
    first = dialog.locator("fieldset").nth(0)
    # 検証
    expect(first.locator("legend")).to_contain_text("変更")
    expect(dialog.get_by_role("checkbox", name="未読の変更あり")).to_be_visible()
    expect(first.locator("span.bg-topbar-unread")).to_have_count(1)


def test_changed_only(open_story: OpenStory) -> None:
    """「変更」の条件をオンにした。見出しの右が「36 件中 2 件」、下端が「2 件を表示」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--changed-only").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog).to_contain_text("36 件中 2 件")
    expect(dialog.get_by_role("checkbox", name="未読の変更あり")).to_be_checked()
    expect(dialog.get_by_role("button", name="2 件を表示")).to_be_visible()


def test_changed_none(open_story: OpenStory) -> None:
    """未読の変更が 0 件。値の文字と件数を薄くし、選べるまま残す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--changed-none").get_by_role("dialog", name="絞り込み")
    row = dialog.locator("li", has_text="未読の変更あり")
    # 検証
    expect(row.get_by_label("0 件")).to_have_text("0")
    expect(dialog.get_by_role("checkbox", name="未読の変更あり")).to_be_enabled()
