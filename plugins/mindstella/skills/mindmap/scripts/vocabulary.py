"""設定の `tags` のタグの語彙の読み取り・未登録の候補の洗い出し・近いタグの候補。"""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Any

# 未登録の候補のタグ 1 つに添える近いタグの数の上限
CANDIDATE_LIMIT = 5


def tag_entries(settings: dict[str, Any]) -> list[dict[str, Any]]:
    """設定の `tags` を `{name, summary, include, exclude, examples}` の並びにして、名前の順に返す。"""
    tags = settings.get("tags")
    # 配列でなければ語彙は空
    if not isinstance(tags, list):
        return []
    entries: list[dict[str, Any]] = []
    for tag in tags:
        # 形が合わない要素は飛ばす（スキーマの誤りは点検が返す）
        if not isinstance(tag, dict):
            continue
        name = tag.get("name")
        if not isinstance(name, str) or not name:
            continue
        examples = tag.get("examples")
        entries.append(
            {
                "name": name,
                "summary": _text_or_none(tag.get("summary")),
                "include": _text_or_none(tag.get("include")),
                "exclude": _text_or_none(tag.get("exclude")),
                # 文字列の配列でなければ空。文字列でない要素は飛ばす
                "examples": (
                    [example for example in examples if isinstance(example, str)]
                    if isinstance(examples, list)
                    else []
                ),
            }
        )
    return sorted(entries, key=lambda entry: str(entry["name"]))


def _text_or_none(value: Any) -> str | None:
    """文字列ならそのまま、そうでなければ None を返す。"""
    return value if isinstance(value, str) else None


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


def list_candidate_tags(
    owned_tags: list[tuple[str, Any]], settings: dict[str, Any]
) -> list[dict[str, Any]]:
    """渡したタグのうち語彙に無い未登録の候補を、付けた ID と近い語彙のタグを添えて、タグごとに並べる。"""
    names = tag_names(settings)
    owners: dict[str, list[str]] = {}
    for owner, tags in owned_tags:
        # 並びでない値は、スキーマと引数の確かめに任せて飛ばす
        if not isinstance(tags, list | tuple):
            continue
        for tag in tags:
            # 文字列で語彙に無いタグの ID を、重ならないように控える
            if isinstance(tag, str) and tag not in names:
                ids = owners.setdefault(tag, [])
                if owner not in ids:
                    ids.append(owner)
    return [
        {"tag": tag, "ids": owners[tag], "similar": similar_tags(tag, names)}
        for tag in sorted(owners)
    ]
