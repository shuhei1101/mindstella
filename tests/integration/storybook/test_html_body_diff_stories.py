"""部品設計『HTMLの本文の差分』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory
from storybook_frame_helpers import frame_of, wait_frame_rendered

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
    page = open_story("preview-htmlbodydiff--rendered")
    wait_frame_rendered(page, f"{MARKED} iframe")
    # 検証
    buttons = page.locator(".html-diff-bar .segment button")
    assert buttons.all_inner_texts() == ["描いた結果", "原文の差分"]
    assert [button.get_attribute("aria-pressed") for button in buttons.all()] == ["true", "false"]
    legend = page.inner_text(LEGEND)
    assert "足した" in legend
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
    page = open_story("preview-htmlbodydiff--raw-diff")
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
    page = open_story("preview-htmlbodydiff--removed-only")
    wait_frame_rendered(page, f"{MARKED} iframe")
    # 検証
    assert "消した箇所は原文の差分で見られます" in page.inner_text(LEGEND)
    assert frame_of(page, f"{MARKED} iframe").locator("[data-df]").count() == 0


def test_from_markdown(open_story: OpenStory) -> None:
    """選んだ時点の本文が Markdown のときは、切り替えを出さず、原文の差分だけを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodydiff--from-markdown")
    page.wait_for_selector(RAW)
    # 検証
    assert page.locator(".html-diff-bar").count() == 0
    assert page.locator(MARKED).count() == 0
    assert page.locator(RAW).is_visible()
    assert page.locator(f"{RAW} .df-line.df-del").count() >= 1
    assert page.locator(f"{RAW} .df-line.df-add").count() >= 1
