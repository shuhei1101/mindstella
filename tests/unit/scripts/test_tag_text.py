"""tag_text.py（タグの表記の正規化・近いタグの候補）の単体テスト。"""

from __future__ import annotations

import copy
from typing import Any

import pytest

import tag_text

# 近いタグの候補の上限（インターフェース定義『項目の検索』の制約「近いタグの候補」）
SIMILAR_LIMIT = 5


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        pytest.param("ＡＰＩ", "api", id="full_width_upper"),
        pytest.param("Api", "api", id="mixed_case"),
        pytest.param("データ", "データ", id="japanese"),
    ],
)
def test_normalize_tag(tag: str, expected: str) -> None:
    """全角と大文字の違いをそろえる（正常系）。"""
    # 実行
    normalized = tag_text.normalize_tag(tag)
    # 検証
    assert normalized == expected


def test_similar_tags() -> None:
    """字面の近い順に並べ、近さが 0 のタグは入れない（正常系）。"""
    # 準備
    names = ["通知", "保存", "通信"]
    # 実行
    similar = tag_text.similar_tags("通知機能", names)
    # 検証
    assert similar[0] == "通知"
    assert "保存" not in similar


def test_similar_tags_when_width_differs() -> None:
    """渡したタグを正規化してから比べる（正常系）。"""
    # 準備
    names = ["api"]
    # 実行
    similar = tag_text.similar_tags("ＡＰＩｓ", names)
    # 検証
    assert similar[0] == "api"


def test_similar_tags_limit() -> None:
    """候補は上限まで（正常系）。"""
    # 準備
    names = [f"a{number}" for number in range(1, 8)]
    # 実行
    similar = tag_text.similar_tags("a", names)
    # 検証
    assert len(similar) == SIMILAR_LIMIT


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        pytest.param({"name": "API", "main": True}, "API", id="object"),
        pytest.param("画面", "画面", id="string"),
        pytest.param({"main": True}, None, id="object_without_name"),
        pytest.param(3, None, id="number"),
    ],
)
def test_tag_name(entry: Any, expected: str | None) -> None:
    """辞書と文字列から名前を取り、取れない要素は None（正常系）。"""
    # 実行
    name = tag_text.tag_name(entry)
    # 検証
    assert name == expected


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        pytest.param(
            [
                {"name": "通知", "main": True},
                {"name": "通知機能", "main": False},
                {"name": "画面"},
            ],
            [{"name": "通知", "main": True}, {"name": "通知機能"}, {"name": "画面"}],
            id="objects",
        ),
        pytest.param(["通知"], ["通知"], id="strings"),
        pytest.param(None, None, id="not_list"),
    ],
)
def test_compact_tags(tags: Any, expected: Any) -> None:
    """主題でないタグの main を除き、ほかは変えない（正常系）。"""
    # 準備
    original = copy.deepcopy(tags)
    # 実行
    compacted = tag_text.compact_tags(tags)
    # 検証
    assert compacted == expected
    assert tags == original


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        pytest.param(
            [{"name": "API"}, {"name": "ａｐｉ", "main": True}, {"name": "画面"}, {"name": "Api"}],
            [1, 3],
            id="duplicated",
        ),
        pytest.param([{"name": "API"}, {"name": "画面"}], [], id="unique"),
    ],
)
def test_duplicate_tag_indexes(tags: list[Any], expected: list[int]) -> None:
    """表記をそろえて同じ名前の 2 件目以降を拾う（正常系）。"""
    # 実行
    indexes = tag_text.duplicate_tag_indexes(tags)
    # 検証
    assert indexes == expected
