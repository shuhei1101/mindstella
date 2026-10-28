"""記録の検索（スキルが項目を探し、1 件の中身と参照元・使っている属性名とタグを読む）の E2E テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree


# 検索結果の 1 ページの既定の件数（インターフェース定義『項目の検索』の制約「件数」）
DEFAULT_LIMIT = 20

# タグの語彙に登録するタグ（説明つき。`データ` は含める条件・含めない条件・例も持つ。`保留` はどの項目も持たない）
TAG_VOCABULARY = [
    {
        "name": "データ",
        "summary": "記録の形",
        "include": "記録のキーと保存の形",
        "exclude": "画面の見た目",
        "examples": ["ワークスペースの YAML"],
    },
    {"name": "画面", "summary": "利用者が見る画面"},
    {"name": "保留", "summary": "決めるのを待つもの"},
]


@pytest.fixture
def search_workspace(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> Path:
    """文字・タグ・属性・参照を持つ D-1・D-2・T-1 と、タグの語彙を持つワークスペースを作る。"""
    return make_workspace(
        make_item("D-1", title="スキーマの設計", tags=["データ"], attrs={"担当": "自分"}),
        make_item(
            "D-2", title="別の問い", depends_on=["D-1"], attrs={"担当": "自分"}, tags=["画面"]
        ),
        make_item(
            "T-1", title="作業", attrs={"期限": "10 月"}, tags=["データ", "画面"], **{"for": ["D-1"]}
        ),
        settings={**valid_settings, "tags": TAG_VOCABULARY},
    )


def test_normal(search_workspace: Path, call_tool: CallTool, snapshot_tree: SnapshotTree) -> None:
    """文字で探し、D-1 の中身と参照元を読み、属性名とタグの語彙を読み、タグで探す（正常系）。"""
    # 準備
    before = snapshot_tree(search_workspace)
    root = str(search_workspace)
    # 実行
    found = call_tool("find", workspace=root, text="スキーマ")
    shown = call_tool("show", workspace=root, id="D-1")
    attrs = call_tool("attrs", workspace=root)
    tags = call_tool("tags", workspace=root)
    found_all = call_tool("find", workspace=root, tags=["データ", "画面"])
    found_any = call_tool("find", workspace=root, any_tags=["データ", "画面"])
    found_empty = call_tool("find", workspace=root, kind="decision", tags=["保留"])
    # 検証
    assert found.is_error is False
    assert [row["id"] for row in found.data["items"]] == ["D-1"]
    assert found.data["total"] == 1
    assert found.data["next_cursor"] is None
    assert {"id", "kind", "title", "status", "tags"} <= set(found.data["items"][0])
    assert shown.is_error is False
    shown_payload = shown.data
    assert shown_payload["item"]["title"] == "スキーマの設計"
    assert shown_payload["item"]["status"] == "未決定"
    assert shown_payload["item"]["tags"] == ["データ"]
    assert shown_payload["item"]["attrs"] == {"担当": "自分"}
    assert shown_payload["referenced_by"] == [
        {"id": "D-2", "key": "depends_on"},
        {"id": "T-1", "key": "for"},
    ]
    assert attrs.is_error is False
    counts = {row["name"]: row["count"] for row in attrs.data["attrs"]}
    assert counts == {"担当": 2, "期限": 1}
    # タグの語彙が名前の順で、説明つきの 3 件を持ち、含める条件・含めない条件・例は持つタグだけが値を返す
    assert tags.is_error is False
    assert tags.data["tags"] == [
        {
            "name": "データ",
            "summary": "記録の形",
            "include": "記録のキーと保存の形",
            "exclude": "画面の見た目",
            "examples": ["ワークスペースの YAML"],
            "count": 2,
            "kinds": ["decision", "task"],
        },
        {
            "name": "保留",
            "summary": "決めるのを待つもの",
            "include": None,
            "exclude": None,
            "examples": [],
            "count": 0,
            "kinds": [],
        },
        {
            "name": "画面",
            "summary": "利用者が見る画面",
            "include": None,
            "exclude": None,
            "examples": [],
            "count": 2,
            "kinds": ["decision", "task"],
        },
    ]
    # 両方のタグを持つ項目は T-1 だけ、どちらかを持つ項目は D-1・D-2・T-1
    assert found_all.is_error is False
    assert [row["id"] for row in found_all.data["items"]] == ["T-1"]
    assert found_any.is_error is False
    assert [row["id"] for row in found_any.data["items"]] == ["D-1", "D-2", "T-1"]
    # 語彙にあるタグで 0 件になると、外せる条件を案内する
    assert found_empty.is_error is False
    assert found_empty.data["items"] == []
    assert found_empty.data["total"] == 0
    assert "tags" in found_empty.data["hint"]
    assert "kind" in found_empty.data["hint"]
    assert snapshot_tree(search_workspace) == before


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """存在しない ID の中身は出せず、ID が無いエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("show", workspace=str(root), id="D-9")
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text


def test_normal_when_paged(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """既定の件数を超える分を、続きの値で読み進める（正常系）。"""
    # 準備
    total = DEFAULT_LIMIT + 5
    root = make_workspace(*(make_item(f"D-{number}") for number in range(1, total + 1)))
    expected_ids = [f"D-{number}" for number in range(1, total + 1)]
    # 実行
    first = call_tool("find", workspace=str(root))
    second = call_tool("find", workspace=str(root), cursor=first.data["next_cursor"])
    # 検証
    assert first.is_error is False
    assert [row["id"] for row in first.data["items"]] == expected_ids[:DEFAULT_LIMIT]
    assert first.data["total"] == total
    assert isinstance(first.data["next_cursor"], str)
    assert "tags" in first.data["hint"]
    assert "kind" in first.data["hint"]
    assert "status" in first.data["hint"]
    assert second.is_error is False
    assert [row["id"] for row in second.data["items"]] == expected_ids[DEFAULT_LIMIT:]
    assert second.data["next_cursor"] is None
    pages = [row["id"] for row in first.data["items"]] + [row["id"] for row in second.data["items"]]
    assert pages == expected_ids


def test_normal_when_unknown_tag(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """語彙に無いタグでも探せ、どの項目にも無いタグには近いタグを案内する（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["データ"]),
        make_item("D-2", tags=["通知"]),
        settings={**valid_settings, "tags": [{"name": "データ"}]},
    )
    # 実行
    candidate = call_tool("find", workspace=str(root), tags=["通知"])
    stray = call_tool("find", workspace=str(root), tags=["データー"])
    # 検証
    # 未登録の候補のタグで探した結果がエラーにならず、D-2 だけである
    assert candidate.is_error is False
    assert [row["id"] for row in candidate.data["items"]] == ["D-2"]
    # どの項目にも語彙にも無いタグで探した結果がエラーにならず、空の一覧・全体の件数 0 である
    assert stray.is_error is False
    assert stray.data["items"] == []
    assert stray.data["total"] == 0
    # 案内の文に、渡したタグと近い語彙のタグがある
    assert "データー" in stray.data["hint"]
    assert "近いタグ: データ" in stray.data["hint"]
