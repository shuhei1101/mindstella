"""資料の HTML の本文の、開きタグへの原文の行の印（始まりと終わり）と、行の範囲の描いた文。"""

from __future__ import annotations

from html.parser import HTMLParser

# 開きタグに足す行の印の属性（Markdown の本文の描画と同じ名前）
LINE_ATTR = "data-line"

# 開きタグに足す、要素が閉じる原文の行の印の属性
LINE_END_ATTR = "data-line-end"

# 閉じタグを持たない要素（終わりの行は始まりの行と同じ）
VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
)

# 中身の文を描いた文に入れない要素
HIDDEN_TEXT_TAGS = frozenset({"style", "script", "template", "title"})

# 行の印を足さない要素（文書の外枠と、描いた文を持たない要素）
UNMARKED_TAGS = frozenset({"html", "head", "body", "meta", "link", "base"}) | HIDDEN_TEXT_TAGS


class _Collector(HTMLParser):
    """開きタグの位置と、描いた文の断片を、原文の行つきで集める。"""

    def __init__(self) -> None:
        """集める入れ物を空にして、文字参照を文字に戻す設定で始める。"""
        super().__init__(convert_charrefs=True)
        # (タグ名の直後の原文の位置, 中身が始まる行)
        self.marks: list[tuple[int, int]] = []
        # marks と同じ並びの、要素が閉じる行
        self.end_lines: list[int] = []
        # (断片の先頭の行, 断片の文)
        self.texts: list[tuple[int, str]] = []
        # 描いた文に出ない要素の中にいる深さ
        self._hidden_depth = 0
        # 原文の各行の先頭の位置
        self._line_starts: list[int] = []
        # 開いている要素の積み上げ（タグ名, marks の添字。印を足さない要素は None）
        self._open_elements: list[tuple[str, int | None]] = []

    def collect(self, source: str) -> None:
        """原文の各行の先頭の位置を控えてから最後まで読み、閉じなかった要素の終わりを原文の最後の行にする。"""
        self._line_starts = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(index + 1)
        self.feed(source)
        self.close()
        last_line = source.rstrip("\n").count("\n") + 1
        for _, mark_index in self._open_elements:
            if mark_index is not None:
                self.end_lines[mark_index] = last_line

    def _open_element(self, tag: str, *, empty: bool) -> None:
        """開きタグの位置と、タグが閉じた行（中身が始まる行）を控え、閉じタグを持つ要素なら積み上げに積む。"""
        line, column = self.getpos()
        raw = self.get_starttag_text() or ""
        start_line = line + raw.count("\n")
        if tag in HIDDEN_TEXT_TAGS and not empty:
            self._hidden_depth += 1
        mark_index: int | None = None
        # 文書の外枠と描いた文を持たない要素には印を付けない
        if tag not in UNMARKED_TAGS:
            offset = self._line_starts[line - 1] + column
            # 複数行にまたがる開きタグは、閉じた行から中身が始まる。終わりの行は閉じタグまで始まりの行にしておく
            self.marks.append((offset + 1 + len(tag), start_line))
            self.end_lines.append(start_line)
            mark_index = len(self.marks) - 1
        if not empty:
            self._open_elements.append((tag, mark_index))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """開きタグを控える（空要素は積み上げに積まない）。"""
        self._open_element(tag, empty=tag in VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """`<br/>` などの空要素にも、開きタグと同じく印を付ける。"""
        self._open_element(tag, empty=True)

    def handle_endtag(self, tag: str) -> None:
        """描いた文に出ない要素の終わりで深さを戻し、同じタグ名の要素までを閉じタグの行で閉じる。"""
        if tag in HIDDEN_TEXT_TAGS and self._hidden_depth > 0:
            self._hidden_depth -= 1
        # 積み上げを上からたどって、同じタグ名の最も内側の要素を探す
        position = next(
            (i for i in range(len(self._open_elements) - 1, -1, -1) if self._open_elements[i][0] == tag),
            None,
        )
        # 同じタグ名の要素が無い閉じタグは飛ばす
        if position is None:
            return
        # そこまでの要素（閉じタグを省いた要素を含む）をこの閉じタグの行で閉じる
        line = self.getpos()[0]
        for _, mark_index in self._open_elements[position:]:
            if mark_index is not None:
                self.end_lines[mark_index] = line
        del self._open_elements[position:]

    def handle_data(self, data: str) -> None:
        """描いた文に出る断片だけを、先頭の行つきで控える。"""
        if self._hidden_depth == 0:
            self.texts.append((self.getpos()[0], data))


def mark_lines(source: str) -> str:
    """開きタグのタグ名の直後に、中身が始まる原文の行と要素が閉じる原文の行（どちらも 1 始まり）の印を足した HTML を返す。"""
    collector = _Collector()
    collector.collect(source)
    pieces: list[str] = []
    cursor = 0
    for (name_end, line), end_line in zip(collector.marks, collector.end_lines, strict=True):
        pieces.append(source[cursor:name_end])
        pieces.append(f' {LINE_ATTR}="{line}" {LINE_END_ATTR}="{end_line}"')
        cursor = name_end
    pieces.append(source[cursor:])
    return "".join(pieces)


def text_of_lines(source: str, start: int, end: int) -> str:
    """原文の `start`〜`end` 行（1 始まり）にある、描いた文に出る文を改行でつないで返す。"""
    collector = _Collector()
    collector.collect(source)
    lines: list[str] = []
    for first_line, data in collector.texts:
        # 断片は改行をまたぐので、行ごとに分けて範囲に入るものだけを取る
        for offset, part in enumerate(data.split("\n")):
            if start <= first_line + offset <= end:
                lines.append(part)
    return "\n".join(lines)
