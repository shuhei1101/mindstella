"""部品設計『HTMLの本文の差分.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest

from playwright.sync_api import Page
from .storybook_react_fixture_types import OpenStory
from integration.storybook_react.storybook_frame_helpers import frame_of, wait_frame_rendered

# 部品が描き終わったとみなす要素（描画のライブラリを読んでから描く部品は、読み終わるまで待つ）
READY = "#storybook-root > div > *"

# 部品が描き終わるまで待つ上限ミリ秒
READY_TIMEOUT_MS = 20_000


def _open_ready(open_story: OpenStory, story_id: str) -> Page:
    """ストーリーを開き、部品が描き終わるまで待つ。"""
    page = open_story(story_id)
    page.wait_for_selector(READY, state="attached", timeout=READY_TIMEOUT_MS)
    return page


# 描いた結果の枠・原文の差分・凡例
MARKED = ".html-marked"
RAW = ".df-raw"
LEGEND = ".df-legend"

# 切り替えを待つ上限ミリ秒
SWITCH_TIMEOUT_MS = 10_000

# 枠の中の段落ごとの本文と印の種類を返す
MARKED_PARAGRAPHS_SCRIPT = """() => [...document.querySelector('.html-marked iframe').contentDocument.querySelectorAll('p')].map((p) => [
    p.textContent,
    p.closest('[data-df]')?.getAttribute('data-df') ?? null,
])"""


def test_rendered(open_story: OpenStory) -> None:
    """描いた結果で、変えた段落に「変わった」の印を付け、上に切り替えと凡例を出す（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, "shared-htmlbodydiff--rendered")
    wait_frame_rendered(page, f"{MARKED} iframe")
    # 検証
    buttons = page.locator(".html-diff-bar .segment button")
    assert buttons.all_inner_texts() == ["描いた結果", "原文の差分"]
    assert [button.get_attribute("aria-pressed") for button in buttons.all()] == ["true", "false"]
    legend = page.inner_text(LEGEND)
    assert "追加した" in legend
    assert "変わった" in legend
    assert page.evaluate(MARKED_PARAGRAPHS_SCRIPT) == [
        ["一つ目の段落", None],
        ["書き換えた二つ目の段落", "chg"],
        ["三つ目の段落", None],
    ]
    assert page.locator(RAW).is_hidden()


def test_raw_diff(open_story: OpenStory) -> None:
    """原文の差分に切り替えると、消した行と足した行を出し、描いた結果と凡例は隠す（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, "shared-htmlbodydiff--raw-diff")
    page.wait_for_selector(f"{RAW}:not([hidden])", timeout=SWITCH_TIMEOUT_MS)
    # 検証
    assert page.locator(MARKED).is_hidden()
    assert page.locator(LEGEND).is_hidden()
    removed = page.locator(f"{RAW} .df-line.df-del").all_inner_texts()
    added = page.locator(f"{RAW} .df-line.df-add").all_inner_texts()
    assert len(removed) == 1
    assert "<p>二つ目の段落</p>" in removed[0]
    assert len(added) == 1
    assert "<p>書き換えた二つ目の段落</p>" in added[0]
    buttons = page.locator(".html-diff-bar .segment button")
    assert [button.get_attribute("aria-pressed") for button in buttons.all()] == ["false", "true"]


def test_removed_only(open_story: OpenStory) -> None:
    """段落を消しただけのときは、描いた結果に印を付けず、凡例に原文の差分で見られる旨を添える（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, "shared-htmlbodydiff--removed-only")
    wait_frame_rendered(page, f"{MARKED} iframe")
    # 検証
    assert "削除した箇所は原文の差分で見られます" in page.inner_text(LEGEND)
    assert frame_of(page, f"{MARKED} iframe").locator("[data-df]").count() == 0


def test_from_markdown(open_story: OpenStory) -> None:
    """選んだ時点の本文が Markdown のときは、切り替えを出さず、原文の差分だけを出す（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, "shared-htmlbodydiff--from-markdown")
    page.wait_for_selector(RAW)
    # 検証
    assert page.locator(".html-diff-bar").count() == 0
    assert page.locator(MARKED).count() == 0
    assert page.locator(RAW).is_visible()
    assert page.locator(f"{RAW} .df-line.df-del").count() >= 1
    assert page.locator(f"{RAW} .df-line.df-add").count() >= 1


# 範囲の差分の見せ方の組（読み上げの名前）と、その 3 つの見せ方
RANGE_GROUP = ".html-diff-bar .segment"
RANGE_NAMES = ["描いた結果（変更前）", "描いた結果（変更後）", "原文の差分"]

# 見せ方のボタンが 1 行で収まるかを、ボタンごとに返す（高さが上下の余白を除いた文字の高さに収まる）
_BUTTON_FIT_JS = """() => [...document.querySelectorAll('.html-diff-bar .segment button')].map((button) => ({
    text: button.textContent.trim(),
    clipped: button.scrollHeight > button.clientHeight || button.scrollWidth > button.clientWidth,
    lines: Math.round(button.getBoundingClientRect().height / parseFloat(getComputedStyle(button).lineHeight || '16')),
}))"""


def _range_pressed(page: Page) -> list[str | None]:
    """範囲の差分の 3 つの見せ方のボタンの `aria-pressed` を、並びのまま返す。"""
    group = page.locator(RANGE_GROUP)
    return [
        group.get_by_role("button", name=name).get_attribute("aria-pressed") for name in RANGE_NAMES
    ]


def _assert_range_buttons_on_one_line(page: Page) -> None:
    """見せ方の 3 つのボタンが、文言を切らず 1 行で読める。"""
    fit = page.evaluate(_BUTTON_FIT_JS)
    assert [button["text"] for button in fit] == RANGE_NAMES
    assert [button["clipped"] for button in fit] == [False, False, False]
    assert [button["lines"] for button in fit] == [1, 1, 1]


def test_range_raw(open_story: OpenStory) -> None:
    """埋め込んだ HTML の範囲の差分。「埋め込んだ HTML」の名前の後に 3 つの見せ方を並べ、「原文の差分」を選んだ状態で開き、凡例は出さない（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, "shared-htmlbodydiff--range-raw")
    page.wait_for_selector(f"{RAW}:not([hidden])", timeout=SWITCH_TIMEOUT_MS)
    # 検証（名前の後に 3 つの見せ方があり、「原文の差分」が押された状態）
    assert page.inner_text(".html-diff-heading") == "埋め込んだ HTML"
    assert page.get_by_role("group", name="埋め込んだ HTMLの差分の見せ方").count() == 1
    assert _range_pressed(page) == ["false", "false", "true"]
    _assert_range_buttons_on_one_line(page)
    # 検証（消した行 1 つと足した行 2 つを出し、描いた結果と凡例は隠す）
    removed = page.locator(f"{RAW} .df-line.df-del").all_inner_texts()
    added = page.locator(f"{RAW} .df-line.df-add").all_inner_texts()
    assert len(removed) == 1
    assert "<p>二つ目の段落</p>" in removed[0]
    assert len(added) == 2
    assert "<p>書き換えた二つ目の段落</p>" in added[0]
    assert "<p>足した段落</p>" in added[1]
    assert page.locator(MARKED).first.is_hidden()
    assert page.locator(LEGEND).is_hidden()


def test_range_before(open_story: OpenStory) -> None:
    """範囲の差分で「描いた結果（変更前）」に切り替えた。選んだ時点の範囲を描いた結果をマーカー無しで出し、凡例は出さない（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, "shared-htmlbodydiff--range-before")
    page.wait_for_selector(f"{MARKED}:not([hidden]) .mdmark-html", timeout=SWITCH_TIMEOUT_MS)
    # 検証
    assert _range_pressed(page) == ["true", "false", "false"]
    _assert_range_buttons_on_one_line(page)
    visible = page.locator(f"{MARKED}:not([hidden]) .mdmark-html p")
    assert visible.all_inner_texts() == ["一つ目の段落", "二つ目の段落"]
    assert page.locator(f"{MARKED}:not([hidden]) [data-df]").count() == 0
    assert page.locator(LEGEND).is_hidden()
    assert page.locator(RAW).is_hidden()


def test_range_after(open_story: OpenStory) -> None:
    """範囲の差分で「描いた結果（変更後）」に切り替えた。今の範囲を描いた結果で、書き換えた段落に「変わった」、足した段落に「足した」のマーカーを付け、凡例を出す（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, "shared-htmlbodydiff--range-after")
    page.wait_for_selector(f"{MARKED}:not([hidden]) .mdmark-html", timeout=SWITCH_TIMEOUT_MS)
    # 検証
    assert _range_pressed(page) == ["false", "true", "false"]
    _assert_range_buttons_on_one_line(page)
    marked = page.locator(f"{MARKED}:not([hidden]) .mdmark-html p").evaluate_all(
        "ps => ps.map(p => [p.textContent, p.dataset.df ?? null])"
    )
    assert marked == [
        ["一つ目の段落", None],
        ["書き換えた二つ目の段落", "chg"],
        ["足した段落", "add"],
    ]
    legend = page.inner_text(LEGEND)
    assert "追加した" in legend
    assert "変わった" in legend
    assert page.locator(RAW).is_hidden()


# 部品設計の状態
STATES = (
    "shared-htmlbodydiff--rendered",
    "shared-htmlbodydiff--raw-diff",
    "shared-htmlbodydiff--removed-only",
    "shared-htmlbodydiff--from-markdown",
    "shared-htmlbodydiff--range-raw",
    "shared-htmlbodydiff--range-before",
    "shared-htmlbodydiff--range-after",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = _open_ready(open_story, state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []
