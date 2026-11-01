"""記録の検索（スキルが項目を探し、1 件の中身と参照元・使っている属性名とタグを読む）の E2E テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree


# 検索結果の 1 ページの既定の件数（インターフェース定義『項目の検索』の制約「件数」）
DEFAULT_LIMIT = 20


@pytest.fixture
def search_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """文字・タグ・属性・参照を持つ D-1・D-2・T-1 のワークスペースを作る。"""
    return make_workspace(
        make_item("D-1", title="スキーマの設計", tags=["データ"], attrs={"担当": "自分"}),
        make_item(
            "D-2", title="別の問い", depends_on=["D-1"], attrs={"担当": "自分"}, tags=["画面"]
        ),
        make_item(
            "T-1", title="作業", attrs={"期限": "10 月"}, tags=["データ", "画面"], **{"for": ["D-1"]}
        ),
    )


def test_normal(search_workspace: Path, call_tool: CallTool, snapshot_tree: SnapshotTree) -> None:
    """文字で探し、D-1 の中身と参照元を読み、使っている属性名とタグを読み、タグで探す（正常系）。"""
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
    # 使われているタグが、件数の多い順（同じ件数は名前の順）に 2 件だけ返る
    assert tags.is_error is False
    assert tags.data["tags"] == [
        {"name": "データ", "count": 2, "kinds": ["decision", "task"]},
        {"name": "画面", "count": 2, "kinds": ["decision", "task"]},
    ]
    # 両方のタグを持つ項目は T-1 だけ、どちらかを持つ項目は D-1・D-2・T-1
    assert found_all.is_error is False
    assert [row["id"] for row in found_all.data["items"]] == ["T-1"]
    assert found_any.is_error is False
    assert [row["id"] for row in found_any.data["items"]] == ["D-1", "D-2", "T-1"]
    # どの項目も持たないタグで 0 件になると、外せる条件を案内する
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


def test_normal_when_tag_normalized(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """全角・大文字の違うタグでも探せ、どの項目も使っていないタグには近い使われているタグを案内する（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["データ"]),
        make_item("D-2", tags=["API"]),
        make_item("D-3", tags=["ａｐｉ"]),
    )
    # 実行
    normalized = call_tool("find", workspace=str(root), tags=["Api"])
    tags = call_tool("tags", workspace=str(root))
    stray = call_tool("find", workspace=str(root), tags=["データー"])
    # 検証
    # タグ Api で探した結果がエラーにならず、D-2・D-3 である
    assert normalized.is_error is False
    assert [row["id"] for row in normalized.data["items"]] == ["D-2", "D-3"]
    # タグの一覧が、API と ａｐｉ を正規化した api の 1 つのタグ（2 件）にまとめて返し、データ（1 件）を返す
    assert [(row["name"], row["count"]) for row in tags.data["tags"]] == [("api", 2), ("データ", 1)]
    # タグ データー で探した結果がエラーにならず、空の一覧・全体の件数 0 で、近い使われているタグ データ を案内する
    assert stray.is_error is False
    assert stray.data["items"] == []
    assert stray.data["total"] == 0
    assert "近いタグ: データ" in stray.data["hint"]
    # D-2・D-3 のタグが、書いたときの表記のままである
    assert [row["tags"] for row in normalized.data["items"]] == [["API"], ["ａｐｉ"]]
