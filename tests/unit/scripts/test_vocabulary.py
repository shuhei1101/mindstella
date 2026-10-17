"""vocabulary.py（タグの語彙の読み取り・語彙にあるかの確かめ・近いタグの候補）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import errors
import vocabulary

# 近いタグの候補の上限（インターフェース定義『項目の検索』の制約「近いタグの候補」）
CANDIDATE_LIMIT = 5


def test_tag_entries() -> None:
    """語彙を名前の順に並べ、説明が無ければ None にする（正常系）。"""
    # 準備
    settings = {"tags": [{"name": "画面", "summary": "s"}, {"name": "データ"}]}
    # 実行
    entries = vocabulary.tag_entries(settings)
    # 検証
    assert entries == [
        {"name": "データ", "summary": None},
        {"name": "画面", "summary": "s"},
    ]


def test_tag_entries_when_missing() -> None:
    """語彙が無ければ空（正常系）。"""
    # 準備
    settings: dict[str, Any] = {"summary": "題"}
    # 実行
    entries = vocabulary.tag_entries(settings)
    # 検証
    assert entries == []


def test_tag_names() -> None:
    """語彙の名前を集める（正常系）。"""
    # 準備
    settings = {"tags": [{"name": "画面"}, {"name": "データ"}]}
    # 実行
    names = vocabulary.tag_names(settings)
    # 検証
    assert names == {"画面", "データ"}


def test_similar_tags() -> None:
    """字面の近い順に並べ、近さが 0 のタグは入れない（正常系）。"""
    # 準備
    names = ["通知", "保存", "通信"]
    # 実行
    candidates = vocabulary.similar_tags("通知機能", names)
    # 検証
    assert candidates[0] == "通知"
    assert "保存" not in candidates


def test_similar_tags_limit() -> None:
    """候補は上限まで（正常系）。"""
    # 準備
    names = [f"a{number}" for number in range(1, 8)]
    # 実行
    candidates = vocabulary.similar_tags("a", names)
    # 検証
    assert len(candidates) == CANDIDATE_LIMIT


def test_require_known_tags() -> None:
    """全て語彙にあれば何も送らない（正常系）。"""
    # 準備
    settings = {"tags": [{"name": "データ"}, {"name": "画面"}]}
    tags_by_argument = [("tags", ["データ"]), ("any_tags", ["画面"])]
    # 実行
    result = vocabulary.require_known_tags(tags_by_argument, settings)
    # 検証
    assert result is None


def test_require_known_tags_when_unknown() -> None:
    """無いタグを引数ごとに候補つきで返す（異常系）。"""
    # 準備
    settings = {"tags": [{"name": "データ"}]}
    tags_by_argument = [("tags", ["データー"]), ("any_tags", ["データ"])]
    # 実行・検証
    with pytest.raises(errors.UnknownTagError) as raised:
        vocabulary.require_known_tags(tags_by_argument, settings)
    assert raised.value.unknown == [("tags", "データー", ["データ"])]
    assert raised.value.lines == ["tags: データー（候補: データ）"]


def test_require_known_tags_when_empty_vocabulary() -> None:
    """語彙が空なら候補なしで返す（異常系）。"""
    # 準備
    settings: dict[str, Any] = {"summary": "題"}
    # 実行・検証
    with pytest.raises(errors.UnknownTagError) as raised:
        vocabulary.require_known_tags([("tags", ["通知"])], settings)
    assert raised.value.lines == ["tags: 通知（候補なし）"]
