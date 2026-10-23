"""詳細パネルと詳細の全画面の、本文の長い URL・インラインコード・表の見せ方の結合テストが共有する本文と測り方。"""

from __future__ import annotations

__all__ = [
    "BODY_WIDTHS",
    "WRAP_BODY",
    "WRAP_ITEM_ID",
    "WRAP_METRICS_JS",
]

# 本文の長い URL・インラインコード・表を確かめる幅（幅 320px・幅 389px 以下の境・幅 390px 以上・広い窓）
BODY_WIDTHS = [320, 389, 390, 1280]

# 本文で指す項目の ID（押せるリンクになり、折り返さない）
WRAP_ITEM_ID = "D-1"

# 広い窓にも収まらない列の数
WIDE_COLUMNS = 30
WIDE_HEADER = "| " + " | ".join(f"第{column}列" for column in range(1, WIDE_COLUMNS + 1)) + " |"
WIDE_DIVIDER = "| " + " | ".join("---" for _ in range(WIDE_COLUMNS)) + " |"
WIDE_ROW = "| " + " | ".join(f"2026-10-{column:02d}" for column in range(1, WIDE_COLUMNS + 1)) + " |"

# 空白を含まない長い URL、途中で切れない長いインラインコード、列の多い表（セルは折り返せない値）、幅に収まる表を持つ本文
WRAP_BODY = f"""# 折り返し

長い URL: https://example.com/{"a" * 300}

長いコード: `{"b" * 300}`

項目: {WRAP_ITEM_ID} を読む

{WIDE_HEADER}
{WIDE_DIVIDER}
{WIDE_ROW}

| 列 A | 列 B |
| --- | --- |
| 1 | 2 |
"""

# 本文のスクロール領域・長い URL と長いコードの折り返し・ID のリンクの折り返しの有無・2 つの表の入れ物の送れ方を読む
WRAP_METRICS_JS = """(scope) => {
    const body = document.querySelector(`${scope} .panel-body`);
    const bodyBox = body.getBoundingClientRect();
    const md = body.querySelector('.md:not(.md-value)');
    const rows = (element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size;
    };
    const inside = (element) => {
        const box = element.getBoundingClientRect();
        return box.left >= bodyBox.left - 0.5 && box.right <= bodyBox.right + 0.5;
    };
    const url = md.querySelector('a[href^="https://example.com/"]');
    const code = md.querySelector('p > code');
    const idref = md.querySelector('a.idref');
    const wraps = [...md.querySelectorAll('.md-table-wrap')].map((wrap) => ({
        role: wrap.getAttribute('role'),
        label: wrap.getAttribute('aria-label'),
        tabindex: wrap.getAttribute('tabindex'),
        scrolls: wrap.scrollWidth > wrap.clientWidth,
        overflowX: getComputedStyle(wrap).overflowX,
        tableNarrowerThanWrap: wrap.querySelector('table').getBoundingClientRect().width < wrap.clientWidth - 1,
        inside: inside(wrap),
    }));
    return {
        bodyScrollsHorizontally: body.scrollWidth > body.clientWidth,
        urlInside: inside(url),
        urlRows: rows(url),
        codeInside: inside(code),
        codeRows: rows(code),
        idrefOverflowWrap: getComputedStyle(idref).overflowWrap,
        idrefRows: rows(idref),
        mdScrollsHorizontally: md.scrollWidth > md.clientWidth,
        wraps,
    };
}"""
