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
