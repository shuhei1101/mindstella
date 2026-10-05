"""コメントが指す箇所（本文の行の範囲か項目の値のキーと、選んだ文）の形を確かめ、今の項目に合うかを確かめる。"""

from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from errors import CommentInvalidError
from store import Workspace, read_body
from submissions import MAX_BODY_CHARS

# 比べる前に、選んだ文と元の文の両方から外す Markdown の書式の記号
MARK_CHARS = "*_~`\\|#>"

# 本文の元の文から、記号を外す前に行ごとに並びの順で当てる正規表現と置き換え先（画像はリンクより先に当てる）
LINE_MARKUP_PATTERNS = (
    # 行頭のリストの記号
    (re.compile(r"^\s*(?:[-+]|\d+[.)])\s+"), ""),
    # 表の区切りの行
    (re.compile(r"^\s*\|?\s*:?-{3,}.*$"), ""),
    # コードブロックのフェンスの行
    (re.compile(r"^\s*(?:`{3,}|~{3,}).*$"), ""),
    # 画像（描いた文では代わりの文が選んだ文に入らない）
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""),
    # リンク（描いた文には括弧と URL が出ない）
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),
)

# キーのパスの 1 段が `name[{key}]` の形のとき、名前と案の key に分ける
INDEXED_STEP = re.compile(r"^([^\[\]]+)\[([^\]]*)\]$")


@dataclass(frozen=True, slots=True, kw_only=True)
class Location:
    """コメント・書きかけ・送信が持つ `loc`。"""

    # `body` は本文の文、`value` は項目の値
    kind: Literal["body", "value"]
    # `body` のときの始めの行（1 始まり）
    start: int | None = None
    # `body` のときの終わりの行（`start` 以上）
    end: int | None = None
    # `value` のときの項目のキーのパス
    key: str | None = None
    # 画面で選んだ文（前後の空白を除いたもの）
    text: str


def parse_location(value: Any) -> Location:
    """要求の `loc` の形を確かめ、`Location` にする。"""
    # オブジェクトでない
    if not isinstance(value, dict):
        raise CommentInvalidError("loc: オブジェクトで渡してください")
    kind = value.get("kind")
    start = end = key = None
    if kind == "body":
        start, end = value.get("start"), value.get("end")
        # 行が 1 以上の整数でない（真偽値は整数として扱わない）
        for name, line in (("start", start), ("end", end)):
            if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                raise CommentInvalidError(f"loc.{name}: 1 以上の整数で渡してください")
        if start > end:
            raise CommentInvalidError("loc.end: start 以上にしてください")
    elif kind == "value":
        key = value.get("key")
        # キーが空でない文字列でない
        if not isinstance(key, str) or not key:
            raise CommentInvalidError("loc.key: 空でない文字列で渡してください")
    else:
        raise CommentInvalidError("loc.kind: body か value で渡してください")
    text = value.get("text")
    # 選んだ文が文字列でない
    if not isinstance(text, str):
        raise CommentInvalidError("loc.text: 文字列で渡してください")
    text = text.strip()
    # 空白だけか、上限を超える
    if not text or len(text) > MAX_BODY_CHARS:
        raise CommentInvalidError(f"loc.text: 1〜{MAX_BODY_CHARS} 文字で渡してください")
    return Location(kind=kind, start=start, end=end, key=key, text=text)


def location_to_dict(location: Location) -> dict[str, Any]:
    """`Location` を YAML・JSON に書く辞書にする（`None` のキーは書かない）。"""
    return {name: item for name, item in asdict(location).items() if item is not None}


def check_location(workspace: Workspace, item: dict[str, Any], location: Location) -> str | None:
    """箇所が今の項目に合うかを確かめ、合わなければ理由を返す。"""
    item_id = item["id"]
    if location.kind == "body":
        name = item.get("body")
        text = read_body(workspace, name) if isinstance(name, str) else None
        # 本文を持たない
        if text is None:
            return f"{item_id} は本文を持ちません"
        lines = text.splitlines()
        # 行の範囲が本文に収まらない
        if location.end is None or location.start is None or location.end > len(lines):
            return f"{item_id} の本文は {len(lines)} 行しかありません"
        source = normalize_source("\n".join(lines[location.start - 1 : location.end]))
        where = f"本文の {location.start}〜{location.end} 行目"
    else:
        value = value_at(item, location.key or "")
        # キーが無い
        if value is None:
            return f"{item_id} にキー {location.key} がありません"
        # 配列は要素を改行でつなぎ、それ以外は文字列にする
        joined = "\n".join(str(entry) for entry in value) if isinstance(value, list) else str(value)
        source = normalize_selected(joined)
        where = str(location.key)
    # 選んだ文が元の文に含まれない
    if normalize_selected(location.text) not in source:
        return f"選んだ文が {item_id} の {where} にありません"
    return None


def value_at(item: dict[str, Any], key: str) -> Any | None:
    """`.` で区切ったキーのパスをたどる。`name[{key}]` は配列のうち `key` が等しい要素を引く。"""
    current: Any = item
    for step in key.split("."):
        indexed = INDEXED_STEP.match(step)
        # 辞書でない: たどれない
        if not isinstance(current, dict):
            return None
        if indexed is None:
            current = current.get(step)
        else:
            entries = current.get(indexed.group(1))
            # 配列でない: たどれない
            if not isinstance(entries, list):
                return None
            current = next(
                (
                    entry
                    for entry in entries
                    if isinstance(entry, dict) and entry.get("key") == indexed.group(2)
                ),
                None,
            )
        # 途中で無くなった
        if current is None:
            return None
    return current


def normalize_selected(text: str) -> str:
    """`MARK_CHARS` と空白・改行を外す。"""
    return "".join(char for char in text if char not in MARK_CHARS and not char.isspace())


def normalize_source(markdown: str) -> str:
    """本文の Markdown の行から、描いた文に現れない書式を外してから記号と空白を外す。"""
    lines = []
    for line in markdown.split("\n"):
        # 行ごとに並びの順で書式を外す
        for pattern, replacement in LINE_MARKUP_PATTERNS:
            line = pattern.sub(replacement, line)
        lines.append(line)
    return normalize_selected(html.unescape("\n".join(lines)))
