"""タグの表記の正規化・近いタグの候補。"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from difflib import SequenceMatcher

# どの項目も使っていないタグ 1 つに添える近いタグの数の上限
SIMILAR_LIMIT = 5


def normalize_tag(tag: str) -> str:
    """タグを NFKC と小文字にそろえた表記にする。"""
    return unicodedata.normalize("NFKC", tag).lower()


def similar_tags(tag: str, names: Iterable[str]) -> list[str]:
    """使われているタグを、渡したタグと字面が近い順に最大 `SIMILAR_LIMIT` 件返す。"""
    normalized = normalize_tag(tag)
    scored: list[tuple[float, str]] = []
    for name in names:
        ratio = SequenceMatcher(None, normalized, name).ratio()
        # 近さが 0 のタグは候補にしない
        if ratio > 0:
            scored.append((ratio, name))
    # 近さの大きい順、同じ近さは名前の順
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [name for _, name in scored[:SIMILAR_LIMIT]]


def tag_name(entry: object) -> str | None:
    """タグの要素から名前を返す。文字列はそのまま、`name` の無い要素は None。"""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        name = entry.get("name")
        if isinstance(name, str):
            return name
    return None


def compact_tags(tags: object) -> object:
    """主題でないタグの `main` を除いた新しい並びを返す。並びでない値はそのまま返す。"""
    if not isinstance(tags, list):
        return tags
    compacted: list[object] = []
    for entry in tags:
        if isinstance(entry, dict) and entry.get("main") is not True:
            compacted.append({key: value for key, value in entry.items() if key != "main"})
        else:
            compacted.append(entry)
    return compacted


def duplicate_tag_indexes(tags: list[object]) -> list[int]:
    """前の要素と正規化した名前が同じ要素の位置を返す。名前の無い要素は飛ばす。"""
    seen: set[str] = set()
    indexes: list[int] = []
    for index, entry in enumerate(tags):
        name = tag_name(entry)
        if name is None:
            continue
        normalized = normalize_tag(name)
        if normalized in seen:
            indexes.append(index)
        else:
            seen.add(normalized)
    return indexes
