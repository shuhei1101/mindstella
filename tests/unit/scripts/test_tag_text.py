"""tag_text.py（タグの表記の正規化・近いタグの候補）の単体テスト。"""

from __future__ import annotations

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
