"""設定の `tags` のタグの語彙の読み取り・語彙にあるかの確かめ・近いタグの候補。"""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Any

from errors import UnknownTagError

# 語彙に無いタグ 1 つに添える近いタグの数の上限
CANDIDATE_LIMIT = 5


def tag_entries(settings: dict[str, Any]) -> list[dict[str, str | None]]:
    """設定の `tags` を `{name, summary}` の並びにして、名前の順に返す（説明が無ければ summary は None）。"""
    tags = settings.get("tags")
    # 配列でなければ語彙は空
    if not isinstance(tags, list):
        return []
    entries: list[dict[str, str | None]] = []
    for tag in tags:
        # 形が合わない要素は飛ばす（スキーマの誤りは点検が返す）
        if not isinstance(tag, dict):
            continue
        name = tag.get("name")
        if not isinstance(name, str) or not name:
            continue
        summary = tag.get("summary")
        entries.append({"name": name, "summary": summary if isinstance(summary, str) else None})
    return sorted(entries, key=lambda entry: str(entry["name"]))


def tag_names(settings: dict[str, Any]) -> frozenset[str]:
    """設定の語彙のタグの名前を集める。"""
    return frozenset(str(entry["name"]) for entry in tag_entries(settings))


def similar_tags(tag: str, names: Iterable[str]) -> list[str]:
    """語彙のタグを、渡したタグと字面が近い順に最大 `CANDIDATE_LIMIT` 件返す。"""
    scored: list[tuple[float, str]] = []
    for name in names:
        # 英字は小文字にして比べる
        ratio = SequenceMatcher(None, tag.lower(), name.lower()).ratio()
        # 近さが 0 のタグは候補にしない
        if ratio > 0:
            scored.append((ratio, name))
    # 近さの大きい順、同じ近さは名前の順
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [name for _, name in scored[:CANDIDATE_LIMIT]]


def require_known_tags(
    tags_by_argument: list[tuple[str, Any]], settings: dict[str, Any]
) -> None:
    """渡したタグが全て語彙にあるかを確かめ、無いタグがあれば候補を添えて `UnknownTagError` を送る。"""
    names = tag_names(settings)
    unknown: list[tuple[str, str, list[str]]] = []
    for argument, tags in tags_by_argument:
        # 並びでない値は、スキーマと引数の確かめに任せて飛ばす
        if not isinstance(tags, list | tuple):
            continue
        for tag in tags:
            # 文字列で語彙に無いタグを、渡した順に拾う
            if isinstance(tag, str) and tag not in names:
                unknown.append((argument, tag, similar_tags(tag, names)))
    # 語彙に無いタグがある: 候補を添えて止める
    if unknown:
        raise UnknownTagError(unknown)
