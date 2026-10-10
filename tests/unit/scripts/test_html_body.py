"""html_body.py（HTML の本文の行の印と、行の範囲の描いた文）の単体テスト。"""

from __future__ import annotations

import pytest

import html_body

# 文書の外枠と描いた文を持たない要素を並べ、段落が 9 行目にある文書
DOCUMENT_WITH_FRAME = (
    "<!doctype html>\n"
    "<html>\n"
    "<head>\n"
    '<meta charset="utf-8">\n'
    "<title>t</title>\n"
    "<style>p{}</style>\n"
    "</head>\n"
    "<body>\n"
    "<p>a</p>\n"
    "<script>x()</script>\n"
    "</body>\n"
    "</html>\n"
)

# 1 行目が style、2 行目がコメント、4 行目が段落の文書
STYLE_COMMENT_PARAGRAPH = "<style>p{}</style>\n<!-- メモ -->\n\n<p>言い<b>換え</b>たい文</p>\n"

# 段落を 1 行ずつ持つ文書
THREE_PARAGRAPHS = "<p>一</p>\n<p>二</p>\n<p>三</p>\n"


def _squash(text: str) -> str:
    """空白と改行を全て外した文を返す（断片のつなぎ方に依らず、文の中身だけを比べる）。"""
    return "".join(text.split())


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("<p>a</p>", '<p data-line="1">a</p>', id="single_line"),
        pytest.param(
            '<p\n class="a">b</p>', '<p data-line="2"\n class="a">b</p>', id="multi_line_tag"
        ),
        pytest.param("<!-- <p>x</p> -->", "<!-- <p>x</p> -->", id="in_comment"),
        pytest.param("<style>a > b {}</style>", "<style>a > b {}</style>", id="in_style"),
        pytest.param(
            '<a title="x>y">t</a>', '<a data-line="1" title="x>y">t</a>', id="gt_in_attribute"
        ),
        pytest.param("a<br/>b", 'a<br data-line="1"/>b', id="void_element"),
        pytest.param(
            "<ul>\n<li>a\n<li>b\n</ul>",
            '<ul data-line="1">\n<li data-line="2">a\n<li data-line="3">b\n</ul>',
            id="omitted_end_tag",
        ),
    ],
)
def test_mark_lines(source: str, expected: str) -> None:
    """開きタグに中身が始まる行の印を足す（正常系）。"""
    # 実行
    marked = html_body.mark_lines(source)
    # 検証
    assert marked == expected


def test_mark_lines_when_unmarked() -> None:
    """文書の外枠と描いた文を持たない要素には足さず、印を消すと原文に戻る（正常系）。"""
    # 実行
    marked = html_body.mark_lines(DOCUMENT_WITH_FRAME)
    # 検証
    assert marked.count("data-line") == 1
    assert '<p data-line="9">a</p>' in marked
    assert marked.replace(' data-line="9"', "") == DOCUMENT_WITH_FRAME


@pytest.mark.parametrize(
    ("source", "start", "end", "expected"),
    [
        pytest.param(STYLE_COMMENT_PARAGRAPH, 4, 4, "言い換えたい文", id="across_tags"),
        pytest.param(STYLE_COMMENT_PARAGRAPH, 1, 1, "", id="style_line"),
        pytest.param(STYLE_COMMENT_PARAGRAPH, 2, 2, "", id="comment_line"),
        pytest.param("<p>A &amp; B</p>", 1, 1, "A&B", id="char_reference"),
        pytest.param(THREE_PARAGRAPHS, 2, 2, "二", id="outside_range"),
    ],
)
def test_text_of_lines(source: str, start: int, end: int, expected: str) -> None:
    """タグをまたぐ文をつなぎ、隠れた中身と範囲の外を外す（正常系）。"""
    # 実行
    text = html_body.text_of_lines(source, start, end)
    # 検証
    assert _squash(text) == expected
