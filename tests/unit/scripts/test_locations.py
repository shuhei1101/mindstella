"""locations.py（コメントが指す箇所の形の確かめ・今の項目に合うかの確かめ）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import locations
import store
from errors import CommentInvalidError
from fixture_types import MakeItem, MakeWorkspace

# 選んだ文の上限（非機能要件の「送信の本文の長さ」）
MAX_TEXT_CHARS = 10000


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            {"kind": "body", "start": 2, "end": 3, "text": " 文 "},
            locations.Location(kind="body", start=2, end=3, text="文"),
            id="body",
        ),
        pytest.param(
            {"kind": "value", "key": "options[B].cons", "text": "文"},
            locations.Location(kind="value", key="options[B].cons", text="文"),
            id="value",
        ),
    ],
)
def test_parse_location(value: dict[str, Any], expected: locations.Location) -> None:
    """本文と値の箇所を読む（正常系）。"""
    # 実行
    result = locations.parse_location(value)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param([], id="not_object"),
        pytest.param({"kind": "line", "text": "文"}, id="kind_unknown"),
        pytest.param({"kind": "body", "start": 1, "text": "文"}, id="end_missing"),
        pytest.param({"kind": "body", "start": 3, "end": 2, "text": "文"}, id="start_after_end"),
        pytest.param({"kind": "body", "start": True, "end": 2, "text": "文"}, id="start_bool"),
        pytest.param({"kind": "value", "text": "文"}, id="key_missing"),
        pytest.param({"kind": "value", "key": "title", "text": "  "}, id="text_blank"),
        pytest.param(
            {"kind": "value", "key": "title", "text": "あ" * (MAX_TEXT_CHARS + 1)}, id="text_long"
        ),
    ],
)
def test_parse_location_when_invalid(value: Any) -> None:
    """崩れた箇所は読まない（異常系）。"""
    # 実行・検証
    with pytest.raises(CommentInvalidError) as exc_info:
        locations.parse_location(value)
    assert str(exc_info.value).startswith("loc")


def test_location_to_dict() -> None:
    """無いキーを書かない（正常系）。"""
    # 準備
    location = locations.Location(kind="value", key="title", text="文")
    # 実行
    result = locations.location_to_dict(location)
    # 検証
    assert result == {"kind": "value", "key": "title", "text": "文"}


# 値の箇所を確かめる検討事項の案（B だけが短所を持つ）
OPTIONS = [
    {"key": "A", "content": "案 A"},
    {"key": "B", "content": "案 B", "cons": "数が多いと長い"},
]


def _body_location(start: int, end: int, text: str) -> locations.Location:
    """本文の箇所を作る。"""
    return locations.Location(kind="body", start=start, end=end, text=text)


@pytest.mark.parametrize(
    ("item_id", "body", "location"),
    [
        pytest.param(
            "A-1",
            "1 行目\n- **言い換えたい**文\n3 行目\n",
            _body_location(2, 2, "言い換えたい文"),
            id="list_and_bold",
        ),
        pytest.param(
            "A-1",
            "1 行目\n前半の文\n後半の文\n",
            _body_location(2, 3, "前半の文\n後半の文"),
            id="soft_break",
        ),
        pytest.param(
            "A-1",
            "| 名前 | 説明 |\n| --- | --- |\n| A | 内容 |\n",
            _body_location(3, 3, "A 内容"),
            id="table_row",
        ),
        pytest.param("A-1", "[資料](https://x)\n", _body_location(1, 1, "資料"), id="link"),
        pytest.param(
            "A-1",
            "詳しくは [規約](https://e.x) を読む。\n",
            _body_location(1, 1, "詳しくは規約を読む"),
            id="link_in_sentence",
        ),
        pytest.param(
            "A-1",
            "図は ![構成](a.png) のとおり。\n",
            _body_location(1, 1, "図は のとおり"),
            id="image_in_sentence",
        ),
        pytest.param("A-1", "A &amp; B\n", _body_location(1, 1, "&"), id="character_reference"),
        pytest.param(
            "D-1",
            "",
            locations.Location(kind="value", key="options[B].cons", text="数が多いと長い"),
            id="option_value",
        ),
        pytest.param(
            "D-1",
            "",
            locations.Location(kind="value", key="title", text="D-1の題"),
            id="title_value",
        ),
    ],
)
def test_check_location(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    item_id: str,
    body: str,
    location: locations.Location,
) -> None:
    """書式の記号を外して合う箇所を通す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", options=OPTIONS), make_item("A-1"), bodies={"A-1.md": body}
    )
    workspace = store.load_workspace(root)
    item = store.find_item(workspace, item_id).item
    # 実行
    result = locations.check_location(workspace, item, location)
    # 検証
    assert result is None


@pytest.mark.parametrize(
    ("item_id", "bodies", "location", "expected_in_reason"),
    [
        pytest.param(
            "A-1",
            {"A-1.md": "1 行目\n2 行目\n3 行目"},
            _body_location(1, 5, "1 行目"),
            "3 行",
            id="past_last_line",
        ),
        pytest.param(
            "A-1",
            {"A-1.md": "1 行目\n2 行目\n3 行目"},
            _body_location(1, 1, "存在しない文"),
            "1〜1 行目",
            id="text_missing",
        ),
        pytest.param(
            "D-1",
            None,
            _body_location(1, 1, "文"),
            "本文を持ちません",
            id="no_body",
        ),
        pytest.param(
            "D-1",
            None,
            locations.Location(kind="value", key="options[Z].cons", text="文"),
            "options[Z].cons",
            id="key_missing",
        ),
    ],
)
def test_check_location_when_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    item_id: str,
    bodies: dict[str, str] | None,
    location: locations.Location,
    expected_in_reason: str,
) -> None:
    """合わない箇所は理由を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item(item_id, options=OPTIONS), bodies=bodies)
    workspace = store.load_workspace(root)
    item = store.find_item(workspace, item_id).item
    # 実行
    result = locations.check_location(workspace, item, location)
    # 検証
    assert result is not None
    assert expected_in_reason in result


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        pytest.param("title", "D-1の題", id="title"),
        pytest.param("options[B].cons", "数が多いと長い", id="option_value"),
        pytest.param("options[Z].cons", None, id="option_missing"),
        pytest.param("title.x", None, id="through_string"),
    ],
)
def test_value_at(make_item: MakeItem, key: str, expected: str | None) -> None:
    """入れ子と案の中を引く（正常系）。"""
    # 準備
    item = make_item("D-1", options=OPTIONS)
    # 実行
    result = locations.value_at(item, key)
    # 検証
    assert result == expected


def test_normalize_selected() -> None:
    """記号と空白を外す（正常系）。"""
    # 実行
    result = locations.normalize_selected("**太字** | `コード`\n次")
    # 検証
    assert result == "太字コード次"


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        pytest.param("1. 項目", "項目", id="list_marker"),
        pytest.param("| --- | --- |", "", id="table_separator"),
        pytest.param("```mermaid", "", id="fence"),
        pytest.param("![図](a.png)", "", id="image"),
        pytest.param("[資料](https://x)", "資料", id="link"),
        pytest.param("A &amp; B", "A&B", id="character_reference"),
    ],
)
def test_normalize_source(markdown: str, expected: str) -> None:
    """行頭の記号・区切りの行・フェンス・画像・リンクの括弧と URL・文字参照を外す（正常系）。"""
    # 実行
    result = locations.normalize_source(markdown)
    # 検証
    assert result == expected
