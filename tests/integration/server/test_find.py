"""find（項目の検索）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from .fixture_types import CallTool, MakeItem, MakeWorkspace


@pytest.fixture
def schema_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """文字と属性で探すためのワークスペース（D-1・D-2・T-1）を作る。"""
    return make_workspace(
        make_item("D-1", title="スキーマの設計", attrs={"担当": "自分"}),
        make_item(
            "D-2",
            title="別の問い",
            options=[{"key": "A", "content": "スキーマを分ける"}],
        ),
        make_item("T-1", title="作業", attrs={"担当": "自分"}),
    )


@pytest.fixture
def tag_count_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """タグごとの件数を数えるためのワークスペース（D-1 は主題のデータと画面、D-2 はデータ）を作る。"""
    return make_workspace(
        make_item("D-1", tags=[{"name": "データ", "main": True}, {"name": "画面"}]),
        make_item("D-2", tags=[{"name": "データ"}]),
    )


def test_normal(schema_workspace: Path, call_tool: CallTool) -> None:
    """文字と属性で探し、両方に合う項目だけを返す（正常系）。"""
    # 実行
    result = call_tool(
        "find",
        workspace=str(schema_workspace),
        text="スキーマ",
        attr=["担当=自分"],
        format="json",
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    items = result.data["items"]
    assert [item["id"] for item in items] == ["D-1"]
    assert list(items[0]) == ["id", "kind", "title", "status", "tags", "chars"]
    assert (items[0]["kind"], items[0]["title"], items[0]["status"], items[0]["tags"]) == (
        "decision",
        "スキーマの設計",
        "未決定",
        [],
    )
    assert (result.data["total"], result.data["next_cursor"], result.data["hint"]) == (
        1,
        None,
        None,
    )


def test_normal_when_nested_text(schema_workspace: Path, call_tool: CallTool) -> None:
    """文字だけで探すと、案の中身に含む項目も返す（正常系）。"""
    # 実行
    result = call_tool("find", workspace=str(schema_workspace), text="スキーマ", format="json")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert [item["id"] for item in result.data["items"]] == ["D-1", "D-2"]


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("find", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_normal_when_tags_and_any_tags(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """tags は全てを持つ項目、any_tags はいずれかを持つ項目を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "データ"}]),
        make_item("D-2", tags=[{"name": "画面"}]),
        make_item("T-1", tags=[{"name": "データ"}, {"name": "画面"}]),
        make_item("N-1"),
    )
    # 実行
    all_of = call_tool("find", workspace=str(root), tags=["データ", "画面"], format="json")
    any_of = call_tool("find", workspace=str(root), any_tags=["データ", "画面"], format="json")
    # 検証
    assert all_of.is_error is False
    assert all_of.data is not None
    assert [item["id"] for item in all_of.data["items"]] == ["T-1"]
    assert any_of.is_error is False
    assert any_of.data is not None
    assert [item["id"] for item in any_of.data["items"]] == ["D-1", "D-2", "T-1"]


def test_normal_when_paged(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """件数を超える分は next_cursor で続きを返し、最初のページに絞り込みの案内を添える（正常系）。"""
    # 準備
    root = make_workspace(*(make_item(f"D-{number}") for number in range(1, 6)))
    # 実行
    first = call_tool("find", workspace=str(root), limit=3, format="json")
    assert first.data is not None
    second = call_tool(
        "find", workspace=str(root), limit=3, cursor=first.data["next_cursor"], format="json"
    )
    # 検証
    assert first.is_error is False
    assert [item["id"] for item in first.data["items"]] == ["D-1", "D-2", "D-3"]
    assert first.data["total"] == 5
    assert isinstance(first.data["next_cursor"], str)
    assert "tags" in first.data["hint"]
    assert "kind" in first.data["hint"]
    assert "status" in first.data["hint"]
    assert "next_cursor" in first.data["hint"]
    assert second.is_error is False
    assert second.data is not None
    assert [item["id"] for item in second.data["items"]] == ["D-4", "D-5"]
    assert second.data["total"] == 5
    assert second.data["next_cursor"] is None


def test_normal_when_empty(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """使われているタグで 0 件になると、空の結果に外せる条件の案内を添える（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=[{"name": "データ"}]))
    # 実行
    result = call_tool("find", workspace=str(root), kind="task", tags=["データ"], format="json")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["items"] == []
    assert result.data["total"] == 0
    assert result.data["next_cursor"] is None
    assert "kind" in result.data["hint"]
    assert "tags" in result.data["hint"]


def test_normal_when_tag_normalized(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """全角・大文字の違うタグでも絞れ、どの項目も使っていないタグは 0 件と近い使われているタグの案内を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "データ"}]),
        make_item("D-2", tags=[{"name": "API"}]),
        make_item("D-3", tags=[{"name": "ａｐｉ"}]),
    )
    # 実行
    normalized = call_tool("find", workspace=str(root), tags=["Api"], format="json")
    stray = call_tool("find", workspace=str(root), tags=["データー"], format="json")
    # 検証
    assert normalized.is_error is False
    assert normalized.data is not None
    assert [(item["id"], item["tags"]) for item in normalized.data["items"]] == [
        ("D-2", [{"name": "API"}]),
        ("D-3", [{"name": "ａｐｉ"}]),
    ]
    assert stray.is_error is False
    assert stray.data is not None
    assert (stray.data["items"], stray.data["total"]) == ([], 0)
    assert "データー はどの項目も使っていないタグです（近いタグ: データ）" in stray.data["hint"]


def test_error_when_cursor_mismatched(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """続きの値を作った条件と違う条件で渡すとエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("D-2"), make_item("D-3"), make_item("T-1")
    )
    first = call_tool("find", workspace=str(root), limit=2, format="json")
    assert first.data is not None
    # 実行
    result = call_tool(
        "find",
        workspace=str(root),
        kind="task",
        limit=2,
        cursor=first.data["next_cursor"],
        format="json",
    )
    # 検証
    assert result.is_error is True
    assert "cursor" in result.text


def test_normal_when_view_selected(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """view・include・exclude で返す項目が変わり、返さなかった項目を omitted に並べる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            target="mindmap",
            category="データ構造",
            phase="要件",
            attrs={"担当": "自分"},
            options=[{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}],
            body="D-1.md",
        ),
        make_item("D-2"),
        bodies={"D-1.md": "# 背景\n\nスキーマを決める。\n"},
    )
    # 実行
    brief = call_tool("find", workspace=str(root), format="json")
    standard = call_tool(
        "find",
        workspace=str(root),
        view="standard",
        include=["body"],
        exclude=["tags"],
        format="json",
    )
    full = call_tool("find", workspace=str(root), view="full", format="json")
    # 検証
    assert (brief.is_error, standard.is_error, full.is_error) == (False, False, False)
    assert brief.data is not None
    assert standard.data is not None
    assert full.data is not None
    brief_d1, brief_d2 = brief.data["items"]
    assert list(brief_d1) == ["id", "kind", "title", "status", "tags", "chars"]
    assert brief.data["omitted"] == [
        "target",
        "category",
        "phase",
        "attrs",
        "updated",
        "extra",
        "body",
    ]
    assert brief_d1["chars"] > brief_d2["chars"]
    assert brief.data["total_chars"] == brief_d1["chars"] + brief_d2["chars"]
    standard_d1 = standard.data["items"][0]
    assert (
        standard_d1["target"],
        standard_d1["category"],
        standard_d1["phase"],
        standard_d1["attrs"],
    ) == ("mindmap", "データ構造", "要件", {"担当": "自分"})
    assert "updated" in standard_d1
    assert standard_d1["body"] == "# 背景\n\nスキーマを決める。\n"
    assert standard_d1["body_format"] == "markdown"
    assert "tags" not in standard_d1
    assert "extra" not in standard_d1
    assert standard.data["omitted"] == ["tags", "extra"]
    full_d1 = full.data["items"][0]
    assert [option["key"] for option in full_d1["extra"]["options"]] == ["A", "B"]
    assert full.data["omitted"] == []
    assert brief_d1["chars"] == standard_d1["chars"] == full_d1["chars"]


def test_normal_when_count_only(tag_count_workspace: Path, call_tool: CallTool) -> None:
    """count_only は一覧を返さず、全体の件数・合計文字数・タグごとの件数を返す（正常系）。"""
    # 準備
    listed = call_tool("find", workspace=str(tag_count_workspace), format="json")
    assert listed.data is not None
    # 実行
    result = call_tool(
        "find", workspace=str(tag_count_workspace), count_only=True, format="json"
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["total"] == 2
    assert result.data["total_chars"] == listed.data["total_chars"]
    assert result.data["tag_counts"] == [
        {"tag": "データ", "count": 2},
        {"tag": "画面", "count": 1},
    ]
    assert "items" not in result.data
    assert "next_cursor" not in result.data
    assert "omitted" not in result.data


def test_normal_when_markdown(tag_count_workspace: Path, call_tool: CallTool) -> None:
    """format を渡さないと、件数の行・項目の表・省いた項目の行を Markdown の本文だけで返す（正常系）。"""
    # 準備
    listed = call_tool("find", workspace=str(tag_count_workspace), format="json")
    assert listed.data is not None
    total_chars = listed.data["total_chars"]
    # 実行
    table = call_tool("find", workspace=str(tag_count_workspace))
    counts = call_tool("find", workspace=str(tag_count_workspace), count_only=True)
    # 検証
    assert (table.is_error, counts.is_error) == (False, False)
    assert (table.data, counts.data) == (None, None)
    lines = table.text.splitlines()
    assert lines[0] == f"全 2 件・合計 {total_chars} 文字"
    assert "| id | kind | title | status | tags | chars |" in lines
    assert "| D-1 | decision | D-1の題 | 未決定 | データ [main]、画面 |" in table.text
    assert "target" in lines[-1]
    assert "body" in lines[-1]
    assert "view" in lines[-1]
    assert "include" in lines[-1]
    assert counts.text.splitlines() == [
        f"全 2 件・合計 {total_chars} 文字",
        "",
        "| タグ | 件数 |",
        "| --- | --- |",
        "| データ | 2 |",
        "| 画面 | 1 |",
    ]


def test_normal_when_main_tag_first(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """タグで探すと、渡したタグを主題として持つ項目を上に並べ、続きの値は並べた後の位置を指す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "データ"}]),
        make_item("D-2", tags=[{"name": "データ", "main": True}]),
        make_item("T-1", tags=[{"name": "データ", "main": True}, {"name": "画面"}]),
    )
    # 実行
    whole = call_tool("find", workspace=str(root), tags=["データ"], format="json")
    first = call_tool("find", workspace=str(root), tags=["データ"], limit=2, format="json")
    assert first.data is not None
    second = call_tool(
        "find",
        workspace=str(root),
        tags=["データ"],
        limit=2,
        cursor=first.data["next_cursor"],
        format="json",
    )
    # 検証
    assert (whole.is_error, first.is_error, second.is_error) == (False, False, False)
    assert whole.data is not None
    assert second.data is not None
    assert [(item["id"], item["tags"]) for item in whole.data["items"]] == [
        ("D-2", [{"name": "データ", "main": True}]),
        ("T-1", [{"name": "データ", "main": True}, {"name": "画面"}]),
        ("D-1", [{"name": "データ"}]),
    ]
    assert [item["id"] for item in first.data["items"]] == ["D-2", "T-1"]
    assert [item["id"] for item in second.data["items"]] == ["D-1"]


def test_error_when_include_excluded(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """include と exclude に同じ名前を渡すとエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("find", workspace=str(root), include=["attrs"], exclude=["attrs"])
    # 検証
    assert result.is_error is True
    assert "include" in result.text
    assert "exclude" in result.text
    assert "attrs" in result.text
