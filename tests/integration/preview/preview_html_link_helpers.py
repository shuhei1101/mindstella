"""HTML の本文の枠の中のリンクを押す結合テストが共有する、本文の組み立てと枠の中の場所の読み取り。"""

from __future__ import annotations

from playwright.sync_api import Frame

__all__ = ["frame_location", "html_with_links"]


def html_with_links(*links: tuple[str, str, str]) -> str:
    """`(id, href の属性, 文)` から、リンクを 1 行ずつ持つ HTML の本文を作る（`href` の属性はそのまま書く）。"""
    lines = [f'<p><a id="{link_id}" {href}>{text}</a></p>' for link_id, href, text in links]
    return "\n".join(lines) + "\n"


def frame_location(frame: Frame) -> str:
    """枠の中の文書の場所（URL）を返す。"""
    return str(frame.evaluate("location.href"))
