"""components/review-body-fold.ts（レビュー中の書き込みの本文を、折り返した後の見た目の 5 行までに畳む部品）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, LoadPreviewStyles

# 部品を置く入れ物の幅（px）
CONTAINER_WIDTH = 320

# 改行で 2 行の本文（畳まない）
TWO_LINES = "書き直しを読みました。\n表はこれで分かりやすくなった"

# 改行で 8 行の本文（各行は折り返さない短さ）
EIGHT_LINES = "\n".join(f"{number} 行目の気づき" for number in range(1, 9))

# 改行が無く、320px の幅で折り返して 8 行を超える本文
WRAPPING_BODY = (
    "A-14 の手引きは、差分の表示を初めて使う人が最初に読む資料なので、"
    "冒頭で「何と何を比べているのか」を一文で言い切ってから、"
    "選んだ時点の決め方、足した・変えた・消した項目の印の読み方、"
    "本文の差分の並べ方の切り替え、図の差分の見方の順に並べると読みやすい。"
    "今は印の説明が先に来ていて、何を比べているかが分かる前に細かい話に入っている。"
    "手引きの冒頭に、比べる二つの時点の決め方の例を一つ置いておくと、"
    "初めて開いた人でも迷わずに読み進められるはずだと考えている。"
    "あわせて、足した・変えた・消した項目を示す印の凡例も、"
    "説明の前ではなく後ろにまとめて置いたほうが、本文の流れを切らずに済む。"
)

# 部品を 320px の入れ物に描き、ボタンを操作して、見た目と呼ばれた操作を返す JavaScript
FOLD_SCRIPT = """async ({props, clicks, width}) => {
    const calls = [];
    const parts = MindmapPreview.reviewBodyFold({
        ...props,
        on: {
            toggle: (...a) => calls.push(["toggle", ...a]),
            changeSet: (...a) => calls.push(["changeSet", ...a]),
        },
    });
    const host = document.createElement("li");
    host.style.width = `${width}px`;
    host.append(parts.body, parts.more);
    document.body.append(host);
    // 開閉のボタンを出すかの測りは、描いた後の ResizeObserver の通知で決まる
    const settle = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await settle();
    const norm = (text) => text.replace(/\\s+/g, " ").trim();
    const lineHeight = parseFloat(getComputedStyle(parts.body).lineHeight);
    const observe = () => ({
        folded: parts.body.classList.contains("folded"),
        bodyId: parts.body.id,
        bodyClass: parts.body.className,
        lines: Math.round(parts.body.getBoundingClientRect().height / lineHeight),
        moreHidden: parts.more.hidden,
        moreText: norm(parts.more.textContent),
        moreClass: parts.more.className,
        expanded: parts.more.getAttribute("aria-expanded"),
        controls: parts.more.getAttribute("aria-controls"),
        label: parts.more.getAttribute("aria-label"),
        focus: parts.more.getAttribute("data-focus"),
        fullyVisible: parts.body.scrollHeight <= parts.body.clientHeight,
    });
    const steps = [observe()];
    for (let count = 0; count < clicks; count += 1) {
        parts.more.click();
        steps.push(observe());
    }
    return {steps, calls};
}"""


def _fold(
    preview_page: Page, props: dict[str, Any], *, clicks: int = 0
) -> dict[str, Any]:
    """部品を描き、ボタンを `clicks` 回押して、押す前と押すたびの見た目と呼ばれた操作を返す。"""
    return preview_page.evaluate(
        FOLD_SCRIPT, {"props": props, "clicks": clicks, "width": CONTAINER_WIDTH}
    )


# 畳んだ本文で開閉のボタンが示すもの
FOLDED_BUTTON = {
    "moreText": "続きを読む",
    "expanded": "false",
    "controls": "review-body-C-51",
    "focus": "more:C-51",
}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(
            TWO_LINES,
            {"folded": False, "moreHidden": True, "fullyVisible": True, "lines": 2},
            id="two_lines",
        ),
        pytest.param(
            EIGHT_LINES,
            {"folded": True, "moreHidden": False, "fullyVisible": False, "lines": 5, **FOLDED_BUTTON},
            id="eight_lines",
        ),
        pytest.param(
            WRAPPING_BODY,
            {"folded": True, "moreHidden": False, "fullyVisible": False, "lines": 5, **FOLDED_BUTTON},
            id="wrapping",
        ),
    ],
)
def test_review_body_fold(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    body: str,
    expected: dict[str, Any],
) -> None:
    """5 行を超える本文だけを畳み、開閉のボタンを出す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    props = {"id": "C-51", "label": "項目を指さないコメント", "body": body}
    # 実行
    observed = _fold(preview_page, props)
    # 検証
    shown = observed["steps"][0]
    assert shown | expected == shown
    assert shown["bodyId"] == "review-body-C-51"
    assert "review-body" in shown["bodyClass"].split()
    assert "review-more" in shown["moreClass"].split()


def test_review_body_fold_when_toggle(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
) -> None:
    """開閉で本文とボタンを切り替え、使う側に知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    props = {"id": "C-51", "label": "項目を指さないコメント", "body": EIGHT_LINES}
    # 実行
    observed = _fold(preview_page, props, clicks=2)
    # 検証
    before, opened, closed = observed["steps"]
    assert before["folded"] is True
    assert before["label"] == "項目を指さないコメントの続きを読む"
    assert opened["folded"] is False
    assert opened["moreText"] == "折りたたむ"
    assert opened["expanded"] == "true"
    assert opened["label"] == "項目を指さないコメントの本文を折りたたむ"
    assert closed["folded"] is True
    assert closed["moreText"] == "続きを読む"
    assert closed["expanded"] == "false"
    assert closed["label"] == "項目を指さないコメントの続きを読む"
    assert observed["calls"] == [["toggle", "C-51", True], ["toggle", "C-51", False]]


def test_review_body_fold_when_open(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
) -> None:
    """開いた状態で描く（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    props = {"id": "C-51", "label": "項目を指さないコメント", "body": EIGHT_LINES, "open": True}
    # 実行
    observed = _fold(preview_page, props)
    # 検証
    shown = observed["steps"][0]
    assert shown["folded"] is False
    assert shown["lines"] == 8
    assert shown["moreHidden"] is False
    assert shown["moreText"] == "折りたたむ"
    assert shown["expanded"] == "true"
    assert observed["calls"] == []
