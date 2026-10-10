"""PoC: HTML の本文の開きタグに原文の行の印を足し、行の範囲の文を取り出す。"""

from __future__ import annotations

from html.parser import HTMLParser

# 行の印の属性（Markdown の本文の描画と同じ名前）
LINE_ATTR = "data-line"
# 描いた文に出ない中身を持つ要素
HIDDEN_TEXT_TAGS = frozenset({"style", "script", "template", "title"})
# 印を足さない要素（文書の外枠と、描いた文を持たない要素）
UNMARKED_TAGS = frozenset({"html", "head", "body", "meta", "link", "base"}) | HIDDEN_TEXT_TAGS


class _Collector(HTMLParser):
    """開きタグの位置と、描いた文の断片を原文の行つきで集める。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # (開きタグの先頭の原文の位置, タグ名の後ろの位置, 中身が始まる行)
        self.marks: list[tuple[int, int, int]] = []
        # (断片の先頭の行, 断片の文)
        self.texts: list[tuple[int, str]] = []
        self._hidden_depth = 0
        self._line_starts: list[int] = []

    def feed_source(self, source: str) -> None:
        """原文を読み、行の先頭の位置を控えてから解析する。"""
        self._line_starts = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(index + 1)
        self.feed(source)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """開きタグの位置と、タグが閉じた行（中身が始まる行）を控える。"""
        line, column = self.getpos()
        raw = self.get_starttag_text() or ""
        if tag in HIDDEN_TEXT_TAGS:
            self._hidden_depth += 1
        # 文書の外枠と描いた文を持たない要素は印を付けない
        if tag in UNMARKED_TAGS:
            return
        offset = self._line_starts[line - 1] + column
        # 複数行にまたがる開きタグは、閉じた行から中身が始まる
        content_line = line + raw.count("\n")
        self.marks.append((offset, offset + 1 + len(tag), content_line))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """`<br/>` などの空要素も、開きタグと同じく印を付ける。"""
        self.handle_starttag(tag, attrs)
        if tag in HIDDEN_TEXT_TAGS:
            self._hidden_depth -= 1

    def handle_endtag(self, tag: str) -> None:
        """隠れた中身を持つ要素の終わりを数える。"""
        if tag in HIDDEN_TEXT_TAGS and self._hidden_depth > 0:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        """描いた文に出る断片だけを、先頭の行つきで控える。"""
        if self._hidden_depth == 0:
            self.texts.append((self.getpos()[0], data))


def annotate(source: str) -> str:
    """開きタグのタグ名の直後に、中身が始まる原文の行（1 始まり）の印を足した HTML を返す。"""
    collector = _Collector()
    collector.feed_source(source)
    pieces: list[str] = []
    cursor = 0
    for _start, name_end, line in collector.marks:
        pieces.append(source[cursor:name_end])
        pieces.append(f' {LINE_ATTR}="{line}"')
        cursor = name_end
    pieces.append(source[cursor:])
    return "".join(pieces)


def text_of_lines(source: str, start: int, end: int) -> str:
    """原文の start〜end 行（1 始まり）にある、描いた文に出る文をつないで返す。"""
    collector = _Collector()
    collector.feed_source(source)
    lines: list[str] = []
    for first_line, data in collector.texts:
        # 断片は改行をまたぐので、行ごとに分けて範囲に入るものだけを取る
        for offset, part in enumerate(data.split("\n")):
            if start <= first_line + offset <= end:
                lines.append(part)
    return "\n".join(lines)


def normalize(text: str) -> str:
    """空白・改行を外す（Markdown の本文の照らし合わせと同じく、空白の違いを比べない）。"""
    return "".join(char for char in text if not char.isspace())


def selection_matches(source: str, start: int, end: int, selected: str) -> bool:
    """選んだ文が、原文の行の範囲の描いた文に含まれるかを返す。"""
    return normalize(selected) in normalize(text_of_lines(source, start, end))
