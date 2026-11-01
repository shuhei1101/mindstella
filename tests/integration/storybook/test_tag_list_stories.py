"""部品設計『タグの並び』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# タグごとに、名前・主題か・title・読み上げだけの文字・マーカーの aria-hidden（マーカーが無ければ null）を読む
TAGS_SCRIPT = """() => [...document.querySelectorAll("#storybook-root span.tag")].map((tag) => ({
    name: tag.lastChild.textContent,
    main: tag.classList.contains("is-main"),
    title: tag.getAttribute("title"),
    spoken: tag.querySelector(".sr-only")?.textContent ?? null,
    marker: tag.querySelector("svg")?.getAttribute("aria-hidden") ?? null,
}))"""

# 1 つ目と 2 つ目のタグの枠の色・文字の色が違うか
STYLE_DIFF_SCRIPT = """() => {
    const [first, second] = [...document.querySelectorAll("#storybook-root span.tag")].map((tag) => getComputedStyle(tag));
    return { border: first.borderTopColor !== second.borderTopColor, color: first.color !== second.color };
}"""

# 台の幅・全てのタグが台に収まるか・行の数と、1 つ目のタグの高さ・行の高さ・マーカーがその中にあるか
LAYOUT_SCRIPT = """() => {
    const stage = document.querySelector("#storybook-root > div");
    const stageBox = stage.getBoundingClientRect();
    const tags = [...stage.querySelectorAll("span.tag")];
    const boxes = tags.map((tag) => tag.getBoundingClientRect());
    const first = boxes[0];
    const marker = tags[0].querySelector("svg").getBoundingClientRect();
    return {
        width: stage.offsetWidth,
        inside: boxes.every((box) => box.right <= stageBox.right),
        rows: new Set(boxes.map((box) => box.top)).size,
        firstHeight: first.height,
        lineHeight: parseFloat(getComputedStyle(tags[0]).lineHeight),
        markerInFirst: first.top <= marker.top && marker.bottom <= first.bottom,
    };
}"""

# LongNarrow のストーリーの台の幅
NARROW_WIDTH_PX = 320

# 1 行に収まったタグの高さが超えない、行の高さの倍数（上下の余白を含む）
SINGLE_LINE_RATIO = 2


def test_one_main(open_story: OpenStory) -> None:
    """主題のタグは名前の前に読み上げに出さない二重丸のマーカーと読み上げだけの「主題」を置き、title で「主題」を持つ。主題でないタグは持たない（正常系）。"""
    # 準備・実行
    page = open_story("preview-taglist--one-main")
    # 検証
    assert page.evaluate(TAGS_SCRIPT) == [
        {"name": "画面", "main": True, "title": "主題", "spoken": "主題", "marker": "true"},
        {"name": "記録の形", "main": False, "title": None, "spoken": None, "marker": None},
    ]
    # 主題のタグは枠と文字を 1 段濃くする（主題でないタグと色が違う）
    assert page.evaluate(STYLE_DIFF_SCRIPT) == {"border": True, "color": True}


def test_two_main(open_story: OpenStory) -> None:
    """主題のタグが 2 つでも、主題を先頭へ寄せず記録の順のまま並べる（正常系）。"""
    # 準備・実行
    page = open_story("preview-taglist--two-main")
    # 検証
    assert page.evaluate(TAGS_SCRIPT) == [
        {"name": "mindstella", "main": False, "title": None, "spoken": None, "marker": None},
        {"name": "ゴールと設定", "main": True, "title": "主題", "spoken": "主題", "marker": "true"},
        {"name": "画面", "main": True, "title": "主題", "spoken": "主題", "marker": "true"},
    ]


def test_no_main(open_story: OpenStory) -> None:
    """主題のタグが無いとき、どのタグもマーカーと読み上げだけの「主題」を持たない（正常系）。"""
    # 準備・実行
    page = open_story("preview-taglist--no-main")
    # 検証
    assert page.evaluate(TAGS_SCRIPT) == [
        {"name": "mindstella", "main": False, "title": None, "spoken": None, "marker": None},
        {"name": "タスク", "main": False, "title": None, "spoken": None, "marker": None},
    ]


def test_string_tags(open_story: OpenStory) -> None:
    """名前の文字列の並びを渡したとき、どれも主題でないタグとして出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-taglist--string-tags")
    # 検証
    assert page.evaluate(TAGS_SCRIPT) == [
        {"name": "通知", "main": False, "title": None, "spoken": None, "marker": None},
        {"name": "画面", "main": False, "title": None, "spoken": None, "marker": None},
    ]


def test_long_narrow(open_story: OpenStory) -> None:
    """幅 320px で長い名前の主題のタグを並べる。収まらないタグは次の行へ回し、マーカーは名前と同じ行に残す（正常系）。"""
    # 準備・実行
    page = open_story("preview-taglist--long-narrow")
    # 検証
    layout = page.evaluate(LAYOUT_SCRIPT)
    assert layout["width"] == NARROW_WIDTH_PX
    assert layout["inside"] is True
    assert layout["rows"] > 1
    # 主題のタグは 1 行に収まり、マーカーはその行の中にある
    assert layout["firstHeight"] < layout["lineHeight"] * SINGLE_LINE_RATIO
    assert layout["markerInFirst"] is True
