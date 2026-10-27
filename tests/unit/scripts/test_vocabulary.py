"""vocabulary.py（タグの語彙の読み取り・未登録の候補の洗い出し・近いタグの候補）の単体テスト。"""

from __future__ import annotations

from typing import Any

import vocabulary

# 近いタグの候補の上限（インターフェース定義『項目の検索』の制約「近いタグの候補」）
CANDIDATE_LIMIT = 5


def test_tag_entries() -> None:
    """語彙を名前の順に並べ、持たないキーは None か空の配列にする（正常系）。"""
    # 準備
    settings = {
        "tags": [
            {"name": "画面", "summary": "s", "include": "i", "exclude": "e", "examples": ["x"]},
            {"name": "データ"},
        ]
    }
    # 実行
    entries = vocabulary.tag_entries(settings)
    # 検証
    assert entries == [
        {"name": "データ", "summary": None, "include": None, "exclude": None, "examples": []},
        {"name": "画面", "summary": "s", "include": "i", "exclude": "e", "examples": ["x"]},
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


def test_list_candidate_tags() -> None:
    """候補をタグごとにまとめ、付けた ID を重ならないように並べる（正常系）。"""
    # 準備
    settings = {"tags": [{"name": "通知"}, {"name": "データ"}]}
    owned_tags = [
        ("D-2", ["通知機能", "データ"]),
        ("T-1", ["通知機能"]),
        ("T-1", ["通知機能"]),
        ("D-3", ["保存処理"]),
    ]
    # 実行
    candidates = vocabulary.list_candidate_tags(owned_tags, settings)
    # 検証
    assert candidates == [
        {"tag": "保存処理", "ids": ["D-3"], "similar": []},
        {"tag": "通知機能", "ids": ["D-2", "T-1"], "similar": ["通知"]},
    ]


def test_list_candidate_tags_when_none() -> None:
    """全て語彙にあれば空（正常系）。"""
    # 準備
    settings = {"tags": [{"name": "データ"}]}
    owned_tags = [("D-1", ["データ"]), ("D-2", None)]
    # 実行
    candidates = vocabulary.list_candidate_tags(owned_tags, settings)
    # 検証
    assert candidates == []
