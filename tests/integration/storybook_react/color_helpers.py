"""ストーリーの色を CSS 変数の値と比べ、コントラスト比を求める補助関数。"""

from __future__ import annotations

import re

from playwright.sync_api import Page

# 選んでいる・未読の塗りと、隣の面とのコントラスト比の下限（WCAG の非テキストのコントラスト）
MIN_CONTRAST = 3.0

# CSS 変数を計算した後の色にする（背景に当てた仮の要素の計算値を返す）
_RESOLVE_JS = """(name) => {
    const probe = document.createElement('span');
    probe.style.backgroundColor = `var(${name})`;
    document.body.append(probe);
    const color = getComputedStyle(probe).backgroundColor;
    probe.remove();
    return color;
}"""


def resolve_color(page: Page, name: str) -> str:
    """CSS 変数（`--mark` など）を、計算した後の色（`rgb(...)`）にして返す。"""
    return page.evaluate(_RESOLVE_JS, name)


def _luminance(color: str) -> float:
    """`rgb(...)`・`rgba(...)` の相対輝度を返す。"""
    channels = [float(value) / 255 for value in re.findall(r"[\d.]+", color)[:3]]
    linear = [value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    """2 つの色のコントラスト比を返す。"""
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)
