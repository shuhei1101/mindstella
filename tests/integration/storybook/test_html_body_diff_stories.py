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


# 左右の列
SIDE_BEFORE = ".sbs-html section.sbs-before"
SIDE_AFTER = ".sbs-html section.sbs-after"

# 切り替えの行にある、ボタンの組ごとの読み上げの名前
_GROUPS_JS = """() => [...document.querySelectorAll('.html-diff-bar [role=group]')].map((group) => ({
    label: group.getAttribute('aria-label'),
    pressed: [...group.querySelectorAll('button')].map((button) => [button.textContent.trim(), button.getAttribute('aria-pressed')]),
}))"""


def test_side_rendered(open_story: OpenStory) -> None:
    """左右に並べた描いた結果。左に選んだ時点、右に今の本文を描き、右の変えた 2 つ目の段落にだけ「変わった」の印を付ける。切り替えの行に並べ方の組と見せ方の組を並べる（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodydiff--side-rendered")
    wait_frame_rendered(page, f"{SIDE_AFTER} iframe")
    wait_frame_rendered(page, f"{SIDE_BEFORE} iframe")
    # 検証（並べ方の組が、見せ方の組の前にある）
    assert page.evaluate(_GROUPS_JS) == [
        {"label": "本文の差分の並べ方", "pressed": [["インライン", "false"], ["左右に並べる", "true"]]},
        {"label": "本文の差分の見せ方", "pressed": [["描いた結果", "true"], ["原文の差分", "false"]]},
    ]
    # 検証（左は前の版で印なし、右は今の版で 2 つ目の段落だけに「変わった」の印）
    assert page.get_attribute(SIDE_BEFORE, "aria-label") == "選んだ時点の本文"
    assert page.get_attribute(SIDE_AFTER, "aria-label") == "今の本文"
    assert frame_of(page, f"{SIDE_BEFORE} iframe").locator("[data-df]").count() == 0
    assert "二つ目の段落" in frame_of(page, f"{SIDE_BEFORE} iframe").inner_text("body")
    assert frame_of(page, f"{SIDE_AFTER} iframe").eval_on_selector_all(
        "p", "ps => ps.map(p => [p.textContent, p.closest('[data-df]')?.dataset.df ?? null])"
    ) == [
        ["一つ目の段落", None],
        ["書き換えた二つ目の段落", "chg"],
        ["三つ目の段落", None],
    ]
    assert page.locator(LEGEND).is_visible()


def test_side_raw(open_story: OpenStory) -> None:
    """左右に並べた原文の差分。左に消した行、右に足した行を同じ高さで並べ、片側にしか無い行の向かいは縞の空き。変わっていない長い並びは両方の列にまたがる 1 行に畳む（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodydiff--side-raw")
    page.wait_for_selector(".df-raw.df-split")
    # 検証（消した行と足した行が同じ高さで、左右に並ぶ）
    removed = page.locator(".df-raw.df-split .df-line.df-del")
    added = page.locator(".df-raw.df-split .df-line.df-add")
    assert removed.count() == 1
    assert added.count() == 1
    assert "<p>二つ目の段落</p>" in removed.inner_text()
    assert "<p>書き換えた二つ目の段落</p>" in added.inner_text()
    removed_box = removed.bounding_box()
    added_box = added.bounding_box()
    assert removed_box is not None
    assert added_box is not None
    assert removed_box["y"] == added_box["y"]
    assert removed_box["x"] < added_box["x"]
    # 検証（描いた結果と凡例は隠す。見せ方は「原文の差分」が押された状態）
    assert page.locator(MARKED).is_hidden()
    assert page.locator(LEGEND).is_hidden()
    assert page.evaluate(_GROUPS_JS)[1]["pressed"] == [["描いた結果", "false"], ["原文の差分", "true"]]


def test_side_from_markdown(open_story: OpenStory) -> None:
    """選んだ時点の本文が Markdown のとき、左右に並べる。左は Markdown として描き、右の今の本文には印を付けない（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodydiff--side-from-markdown")
    wait_frame_rendered(page, f"{SIDE_AFTER} iframe")
    # 検証（左は Markdown として描いた見出しと段落、右の今の本文には印が無い）
    assert page.locator(f"{SIDE_BEFORE} iframe").count() == 0
    assert "一つ目の段落" in page.inner_text(f"{SIDE_BEFORE}")
    assert page.locator(f"{SIDE_BEFORE} h1").count() == 1
    assert frame_of(page, f"{SIDE_AFTER} iframe").locator("[data-df]").count() == 0
