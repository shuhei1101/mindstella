"""語の面（変えた行の中の変わった語の濃い面）の結合テストが共有する、ワークスペースの作り方と色の測り方。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "BEFORE_PARAGRAPHS",
    "KEY_LINES_JS",
    "MIN_TEXT_CONTRAST",
    "WORD_COLORS_JS",
    "WORD_MARKS_JS",
    "build_key_newline_diff_workspace",
    "build_key_word_diff_workspace",
    "build_word_diff_workspace",
    "colour_distance",
    "contrast_ratio",
    "serve_key_newline_diff_workspace",
    "serve_key_word_diff_workspace",
    "serve_word_diff_workspace",
]

# 文字と置く面の対比の下限（WCAG の通常の文字）
MIN_TEXT_CONTRAST = 4.5

# 検討事項 D-1 の書き換える前の本文: 書き換える段落（1 つ目）・変えない段落（2 つ目）・消す段落（3 つ目）・表の行・図のノードのラベル
BEFORE_PARAGRAPHS = """# 概要

要件は来週までに決める。

変えない段落

消す段落

| 項目 | 期限 |
| --- | --- |
| 要件 | 来週 |

```mermaid
flowchart TD
  A[仕様を決める] --> B
```
"""

# D-1 の書き換えた後の本文（1 つ目の段落の語・表の行の語・図のノードのラベルの語を書き換え、3 つ目の段落を消す）
AFTER_PARAGRAPHS = """# 概要

要件は今週までに決める。

変えない段落

| 項目 | 期限 |
| --- | --- |
| 要件 | 今週 |

```mermaid
flowchart TD
  A[設計を決める] --> B
```
"""

# 検討事項 D-2 の本文: 1 つ目の段落を消し、続く段落の語を書き換える（消した行 3 行・足した行 1 行で、行の数が揃わない）
UNPAIRED_BEFORE = "消す段落\n\n要件は来週までに決める。\n"
UNPAIRED_AFTER = "要件は今週までに決める。\n"

# 検討事項 D-3 の本文: 同じ語を持たない文への書き換え（行の数は揃うが、同じ部分が少ない）
LITTLE_SAME_BEFORE = "東京は晴れ\n"
LITTLE_SAME_AFTER = "Hello world\n"

# 変えた行の対の、語の面（`span.df-word`）を持つ要素を、面の種類と文字に直して並べる。`selector` の要素ごとに返す
WORD_MARKS_JS = """selector => [...document.querySelectorAll(selector)].map(element => ({
    text: element.textContent,
    words: [...element.querySelectorAll('span.df-word')].map(word => ({
        kind: word.classList.contains('df-add') ? 'add' : word.classList.contains('df-del') ? 'del' : 'none',
        text: word.textContent,
    })),
}))"""

# 背景（`lead`）の前の値と今の値の要素（`del.df-was` / `ins.df-now`）について、計算後の `white-space`・文字が占める行の数（幅を持つ箱の `top` の種類）・
# 渡した文字（読み上げの文字を除く）が始まる位置の `top`・語の面（`span.df-word`）が占める行の数と文字・パネルの右端からのはみ出しを返す。
# `[選択子の頭, 文字の配列]` を渡し、文字は頭から順に、前の値・今の値の中で探す
KEY_LINES_JS = """([scope, needles]) => {
    const lineCount = (elements) => new Set(
        elements.flatMap((element) => [...element.getClientRects()])
            .filter((rect) => rect.width > 0)
            .map((rect) => Math.round(rect.top)),
    ).size;
    const topOf = (root, needle) => {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            if (node.parentElement.closest('.sr-only')) continue;
            const at = node.data.indexOf(needle);
            if (at < 0) continue;
            const range = document.createRange();
            range.setStart(node, at);
            range.setEnd(node, at + needle.length);
            return Math.round(range.getBoundingClientRect().top);
        }
        return null;
    };
    const panelRight = document.querySelector('aside.panel').getBoundingClientRect().right;
    const measure = (selector, wordSelector) => {
        const element = document.querySelector(`${scope} ${selector}`);
        const words = [...element.querySelectorAll(wordSelector)];
        return {
            whiteSpace: getComputedStyle(element).whiteSpace,
            lines: lineCount([element]),
            tops: needles.map((needle) => topOf(element, needle)),
            wordLines: lineCount(words),
            wordText: words.map((word) => word.textContent).join(''),
            overflow: Math.max(0, element.getBoundingClientRect().right - panelRight),
        };
    };
    return {
        was: measure('del.df-was', 'span.df-word.df-del'),
        now: measure('ins.df-now', 'span.df-word.df-add'),
    };
}"""

# 語の面の要素の背景色と文字色、それを含む行の面と画面の地の背景色を、RGB に直して返す。`[語の面の選択子, 行の面の選択子]` を渡す
WORD_COLORS_JS = """([wordSelector, lineSelector]) => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    const rgb = value => {
        context.clearRect(0, 0, 1, 1);
        context.fillStyle = '#000';
        context.fillStyle = value;
        context.fillRect(0, 0, 1, 1);
        return [...context.getImageData(0, 0, 1, 1).data].slice(0, 3);
    };
    // 背景が透明でない最初の祖先の色（画面の地）
    const surfaceOf = element => {
        for (let parent = element.parentElement; parent; parent = parent.parentElement) {
            const background = getComputedStyle(parent).backgroundColor;
            if (background !== 'rgba(0, 0, 0, 0)') return background;
        }
        return '#fff';
    };
    const word = document.querySelector(wordSelector);
    const line = word.closest(lineSelector);
    return {
        wordBackground: rgb(getComputedStyle(word).backgroundColor),
        text: rgb(getComputedStyle(word).color),
        lineBackground: rgb(getComputedStyle(line).backgroundColor),
        surface: rgb(surfaceOf(line)),
    };
}"""


def _call(call_tool: Any, name: str, **arguments: Any) -> dict[str, Any]:
    """ツールを呼び、エラーならテストを止めて結果を返す。"""
    result = call_tool(name, **arguments)
    assert result.is_error is False, result.text
    return result.data


def build_word_diff_workspace(make_workspace: Any, call_tool: Any) -> Path:
    """実際のツールで、本文を書き換えたまとまり V-2 を持つ検討事項 D-1（語の面が付く）・D-2（対にならない）・D-3（同じ部分が少ない）のワークスペースを作る。"""
    root: Path = make_workspace()
    workspace = str(root)
    decision = {
        "status": "未決定",
        "options": [{"key": "A", "content": "案 A"}],
        "weight": "大",
        "category": "データ構造",
        "phase": "要件",
        "target": "mindmap",
    }
    bodies = [
        ("語を書き換える問い", BEFORE_PARAGRAPHS, AFTER_PARAGRAPHS),
        ("行の数が揃わない問い", UNPAIRED_BEFORE, UNPAIRED_AFTER),
        ("同じ部分が少ない問い", LITTLE_SAME_BEFORE, LITTLE_SAME_AFTER),
    ]
    for title, before, _ in bodies:
        _call(
            call_tool,
            "add",
            workspace=workspace,
            kind="decision",
            item={**decision, "title": title, "body_markdown": before},
        )
    _call(call_tool, "commit", workspace=workspace, summary="最初の書き込み")
    for number, (_, _, after) in enumerate(bodies, start=1):
        _call(
            call_tool,
            "update",
            workspace=workspace,
            id=f"D-{number}",
            item={"body_markdown": after},
        )
    _call(call_tool, "commit", workspace=workspace, summary="語を書き換える")
    return root


def build_key_word_diff_workspace(
    make_workspace: Any, call_tool: Any, valid_settings: dict[str, Any]
) -> Path:
    """実際のツールで、背景・案 A の内容の語と、状態・影響度・タグを書き換えたまとまり V-2 を持つ検討事項 D-1（本文は持たない）のワークスペースを作る。"""
    root: Path = make_workspace(settings=valid_settings)
    workspace = str(root)
    decision = {
        "title": "会議の進め方を決める問い",
        "status": "未決定",
        "lead": "要件は来週までに決める。",
        "options": [{"key": "A", "content": "毎週の会議で決める"}],
        "weight": "大",
        "tags": ["要件", "会議"],
        "category": "データ構造",
        "phase": "要件",
        "target": "mindmap",
    }
    _call(call_tool, "add", workspace=workspace, kind="decision", item=decision)
    _call(call_tool, "commit", workspace=workspace, summary="最初の書き込み")
    _call(
        call_tool,
        "update",
        workspace=workspace,
        id="D-1",
        item={
            "status": "要見直し",
            "lead": "要件は今週までに決める。",
            "options": [{"key": "A", "content": "毎月の会議で決める"}],
            "weight": "中",
            "tags": ["要件", "運用"],
        },
    )
    _call(call_tool, "commit", workspace=workspace, summary="語を書き換える")
    return root


# 検討事項 D-1 の背景: 改行で区切った 2 つの文を持ち、2 つ目の文の中の語を 1 つ書き換える（改行は残す）
NEWLINE_LEAD_BEFORE = "要件を決める。\n期限は来週。"
NEWLINE_LEAD_AFTER = "要件を決める。\n期限は今週。"

# 検討事項 D-2 の背景: 書き換えた範囲（`来週` → `今週\n明日`）が改行をまたぐ
ACROSS_LEAD_BEFORE = "予定は来週の会議で決める"
ACROSS_LEAD_AFTER = "予定は今週\n明日の会議で決める"

# 検討事項 D-3 の背景: 改行を持たず、幅に収まらない長さの 1 行で、中の語を 1 つ書き換える
LONG_SENTENCE = "要件を決めるための会議の進め方を、関係者の予定を見ながら慎重に話し合う。"
LONG_LEAD_BEFORE = LONG_SENTENCE * 8 + "期限は来週。"
LONG_LEAD_AFTER = LONG_SENTENCE * 8 + "期限は今週。"


def build_key_newline_diff_workspace(make_workspace: Any, call_tool: Any) -> Path:
    """実際のツールで、背景の改行を確かめる検討事項 D-1（改行を持つ）・D-2（書き換えた範囲が改行をまたぐ）・D-3（長い 1 行）の、背景を書き換えたまとまり V-2 を持つワークスペースを作る。"""
    root: Path = make_workspace()
    workspace = str(root)
    decision = {
        "status": "未決定",
        "options": [{"key": "A", "content": "案 A"}],
        "weight": "大",
        "category": "データ構造",
        "phase": "要件",
        "target": "mindmap",
    }
    leads = [
        ("改行を持つ問い", NEWLINE_LEAD_BEFORE, NEWLINE_LEAD_AFTER),
        ("範囲が改行をまたぐ問い", ACROSS_LEAD_BEFORE, ACROSS_LEAD_AFTER),
        ("長い 1 行の問い", LONG_LEAD_BEFORE, LONG_LEAD_AFTER),
    ]
    for title, before, _ in leads:
        _call(
            call_tool,
            "add",
            workspace=workspace,
            kind="decision",
            item={**decision, "title": title, "lead": before},
        )
    _call(call_tool, "commit", workspace=workspace, summary="最初の書き込み")
    for number, (_, _, after) in enumerate(leads, start=1):
        _call(call_tool, "update", workspace=workspace, id=f"D-{number}", item={"lead": after})
    _call(call_tool, "commit", workspace=workspace, summary="語を書き換える")
    return root


def serve_key_newline_diff_workspace(make_workspace: Any, call_tool: Any) -> str:
    """背景の改行を確かめるワークスペースを作って配信を立て、その URL を返す。"""
    root = build_key_newline_diff_workspace(make_workspace, call_tool)
    served = call_tool("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    return str(served.data["url"])


def serve_key_word_diff_workspace(
    make_workspace: Any, call_tool: Any, valid_settings: dict[str, Any]
) -> str:
    """キーの語の面を確かめるワークスペースを作って配信を立て、その URL を返す。"""
    root = build_key_word_diff_workspace(make_workspace, call_tool, valid_settings)
    served = call_tool("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    return str(served.data["url"])


def serve_word_diff_workspace(make_workspace: Any, call_tool: Any) -> str:
    """語の面を確かめるワークスペースを作って配信を立て、その URL を返す。"""
    root = build_word_diff_workspace(make_workspace, call_tool)
    served = call_tool("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    return str(served.data["url"])


def _linear(channel: int) -> float:
    """sRGB の 1 チャンネル（0〜255）を線形の明るさにする。"""
    value = channel / 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def _luminance(rgb: list[int]) -> float:
    """RGB の相対輝度を返す。"""
    red, green, blue = (_linear(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: list[int], background: list[int]) -> float:
    """文字の色と置く面の色の対比（WCAG のコントラスト比）を返す。"""
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def colour_distance(first: list[int], second: list[int]) -> float:
    """2 つの色の RGB 空間の距離を返す（地の色から離れているほど濃い面）。"""
    return sum((a - b) ** 2 for a, b in zip(first, second, strict=True)) ** 0.5
