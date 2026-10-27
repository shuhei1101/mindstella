"""query.py（検索・1 件の表示と参照元・属性名の一覧）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import query
import store
from errors import ArgumentError
from fixture_types import MakeItem, MakeWorkspace


def _ids(rows: list[dict[str, Any]]) -> list[str]:
    """検索結果の行から ID だけを並びのまま取り出す。"""
    return [row["id"] for row in rows]


@pytest.fixture
def schema_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> store.Workspace:
    """文字と属性で探すためのワークスペース（D-1・D-2・T-1）を読み込んで返す。"""
    root = make_workspace(
        make_item("D-1", title="スキーマの設計", attrs={"担当": "自分"}),
        make_item(
            "D-2",
            title="別の問い",
            options=[{"key": "A", "content": "スキーマを分ける"}],
        ),
        make_item("T-1", title="作業", attrs={"担当": "自分"}),
    )
    return store.load_workspace(root)


@pytest.fixture
def field_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> store.Workspace:
    """種類・状態・タグ・対象・カテゴリー・フェーズで絞るためのワークスペースを読み込んで返す。"""
    root = make_workspace(
        make_item(
            "D-1",
            status="未決定",
            tags=["データ"],
            target="mindmap",
            category="データ構造",
            phase="要件",
        ),
        make_item(
            "D-2",
            status="決定済み",
            target="別の対象",
            category="別のカテゴリー",
            phase="目的",
        ),
        make_item(
            "T-1",
            status="未着手",
            tags=["データ"],
            target="mindmap",
            category="データ構造",
            phase="要件",
        ),
    )
    return store.load_workspace(root)


def test_search_items_when_text_and_attr(schema_workspace: store.Workspace) -> None:
    """文字と属性の両方に合う項目だけを返す（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(text="スキーマ", attrs=[("担当", "自分")])
    # 実行
    result = query.search_items(schema_workspace, search_filter)
    # 検証
    assert result == [
        {
            "id": "D-1",
            "kind": "decision",
            "title": "スキーマの設計",
            "status": "未決定",
            "tags": [],
        },
    ]


def test_search_items_when_nested_text(schema_workspace: store.Workspace) -> None:
    """入れ子の文字列にも当たる（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(text="スキーマ")
    # 実行
    result = query.search_items(schema_workspace, search_filter)
    # 検証
    assert _ids(result) == ["D-1", "D-2"]


@pytest.mark.parametrize(
    ("conditions", "expected_ids"),
    [
        pytest.param({"kind": "task"}, ["T-1"], id="kind"),
        pytest.param({"status": "未決定"}, ["D-1"], id="status"),
        pytest.param({"tags": ("データ",)}, ["D-1", "T-1"], id="tags"),
        pytest.param({"target": "別の対象"}, ["D-2"], id="target"),
        pytest.param({"category": "別のカテゴリー"}, ["D-2"], id="category"),
        pytest.param({"phase": "目的"}, ["D-2"], id="phase"),
    ],
)
def test_search_items_when_fields(
    field_workspace: store.Workspace,
    conditions: dict[str, str],
    expected_ids: list[str],
) -> None:
    """種類・状態・タグ・対象・カテゴリー・フェーズで絞る（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(**conditions)
    # 実行
    result = query.search_items(field_workspace, search_filter)
    # 検証
    assert _ids(result) == expected_ids


def test_search_items_when_no_filter(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """条件が無ければ全てを種類の順に返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1"), make_item("D-2"), make_item("D-1"))
    workspace = store.load_workspace(root)
    # 実行
    result = query.search_items(workspace, query.SearchFilter())
    # 検証
    assert _ids(result) == ["D-1", "D-2", "T-1"]


@pytest.mark.parametrize(
    ("conditions", "expected_ids"),
    [
        pytest.param({"tags": ("データ", "画面")}, ["T-1"], id="tags_and"),
        pytest.param({"any_tags": ("データ", "画面")}, ["D-1", "D-2", "T-1"], id="any_tags_or"),
        pytest.param({"tags": ("データ",), "any_tags": ("画面",)}, ["T-1"], id="both"),
    ],
)
def test_search_items_when_tags_and_any_tags(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    conditions: dict[str, tuple[str, ...]],
    expected_ids: list[str],
) -> None:
    """tags は全てを持つ項目、any_tags はいずれかを持つ項目を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["データ"]),
        make_item("D-2", tags=["画面"]),
        make_item("T-1", tags=["データ", "画面"]),
        make_item("N-1"),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = query.search_items(workspace, query.SearchFilter(**conditions))
    # 検証
    assert _ids(result) == expected_ids


def test_search_items_when_detailed(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """detailed は対象・カテゴリー・フェーズ・属性・更新日時を足し、案は入れない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            target="mindmap",
            category="データ構造",
            phase="要件",
            attrs={"担当": "自分"},
            options=[{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}],
        ),
        make_item("N-1"),
    )
    workspace = store.load_workspace(root)
    # 実行
    decision, note = query.search_items(workspace, query.SearchFilter(), detailed=True)
    # 検証
    assert list(decision) == [
        "id",
        "kind",
        "title",
        "status",
        "tags",
        "target",
        "category",
        "phase",
        "attrs",
        "updated",
    ]
    assert decision["target"] == "mindmap"
    assert decision["category"] == "データ構造"
    assert decision["phase"] == "要件"
    assert decision["attrs"] == {"担当": "自分"}
    assert decision["updated"] == "2026-10-01T00:00:00+00:00"
    assert "options" not in decision
    assert note["target"] is None
    assert note["attrs"] == {}
    assert note["tags"] == []


@pytest.mark.parametrize(
    ("value", "needle", "expected"),
    [
        pytest.param({"a": ["Schema"]}, "schema", True, id="nested_value"),
        pytest.param({"schema": 1}, "schema", False, id="dict_key"),
        pytest.param(3, "3", False, id="number"),
    ],
)
def test_contains_text(value: Any, needle: str, expected: bool) -> None:
    """入れ子の値をたどり、キーと数値は見ない（正常系）。"""
    # 実行
    found = query._contains_text(value, needle)
    # 検証
    assert found is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("担当=自分", ("担当", "自分"), id="name_and_value"),
        pytest.param("担当", ("担当", None), id="name_only"),
        pytest.param("式=a=b", ("式", "a=b"), id="value_with_equal"),
    ],
)
def test_parse_attr(text: str, expected: tuple[str, str | None]) -> None:
    """名前と値に分ける（正常系）。"""
    # 実行
    parsed = query.parse_attr(text)
    # 検証
    assert parsed == expected


def test_show_item(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """中身・本文・参照元をまとめる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", depends_on=["D-1"], related=["D-1"]),
        make_item("T-1", **{"for": ["D-1"]}),
        bodies={"D-1.md": "本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    shown = query.show_item(workspace, "D-1")
    # 検証
    assert shown["item"] == make_item("D-1", body="D-1.md")
    assert shown["kind"] == "decision"
    assert shown["body_markdown"] == "本文\n"
    assert shown["referenced_by"] == [
        {"id": "D-2", "key": "depends_on"},
        {"id": "D-2", "key": "related"},
        {"id": "T-1", "key": "for"},
    ]


def test_show_item_when_body_missing(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """本文を持たない項目は body_markdown が None になる（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    shown = query.show_item(workspace, "D-1")
    # 検証
    assert shown["body_markdown"] is None


def test_show_item_when_html_body(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """HTML の本文は body_html と形式で返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": "<p>画面のモック</p>\n"}
    )
    workspace = store.load_workspace(root)
    # 実行
    shown = query.show_item(workspace, "A-1")
    # 検証
    assert shown["body_html"] == "<p>画面のモック</p>\n"
    assert shown["body_format"] == "html"
    assert shown["body_markdown"] is None


def test_list_referrers(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """parent・sources を含む全ての参照のキーを拾い、キーごとに行を分ける（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("L-1"),
        make_item("D-1", sources=["L-1"]),
        make_item("D-2", related=["L-1"]),
        make_item("D-3", parent="D-1"),
    )
    workspace = store.load_workspace(root)
    # 実行
    to_log = query.list_referrers(workspace, "L-1")
    to_decision = query.list_referrers(workspace, "D-1")
    # 検証
    assert to_log == [{"id": "D-1", "key": "sources"}, {"id": "D-2", "key": "related"}]
    assert to_decision == [{"id": "D-3", "key": "parent"}]


def test_list_attrs(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """種類をまたいで数える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", attrs={"担当": "自分"}),
        make_item("D-2", attrs={"担当": "自分"}),
        make_item("T-1", attrs={"期限": "来週", "担当": "自分"}),
    )
    workspace = store.load_workspace(root)
    # 実行
    attrs = query.list_attrs(workspace)
    # 検証
    assert attrs == [
        {"name": "担当", "count": 3, "kinds": ["decision", "task"]},
        {"name": "期限", "count": 1, "kinds": ["task"]},
    ]


def test_list_attrs_when_none(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """属性が無ければ空の並びを返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    attrs = query.list_attrs(workspace)
    # 検証
    assert attrs == []


def test_list_tags(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """語彙のタグごとに説明を返し、種類をまたいで数え、持つ項目が無いタグも返す（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "tags": [
            {"name": "データ", "summary": "s", "include": "i", "exclude": "e", "examples": ["x"]},
            {"name": "画面"},
            {"name": "保留"},
        ],
    }
    root = make_workspace(
        make_item("D-1", tags=["データ"]),
        make_item("D-2", tags=["画面"]),
        make_item("T-1", tags=["データ"]),
        make_item("N-1"),
        settings=settings,
    )
    workspace = store.load_workspace(root)
    # 実行
    tags = query.list_tags(workspace)
    # 検証
    no_description = {"summary": None, "include": None, "exclude": None, "examples": []}
    assert tags == [
        {
            "name": "データ",
            "summary": "s",
            "include": "i",
            "exclude": "e",
            "examples": ["x"],
            "count": 2,
            "kinds": ["decision", "task"],
        },
        {"name": "保留", **no_description, "count": 0, "kinds": []},
        {"name": "画面", **no_description, "count": 1, "kinds": ["decision"]},
    ]


def test_list_tags_when_duplicated(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """1 つの項目が同じタグを 2 回持っても 1 件と数える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["データ", "データ"]),
        settings={**valid_settings, "tags": [{"name": "データ"}]},
    )
    workspace = store.load_workspace(root)
    # 実行
    tags = query.list_tags(workspace)
    # 検証
    assert tags == [
        {
            "name": "データ",
            "summary": None,
            "include": None,
            "exclude": None,
            "examples": [],
            "count": 1,
            "kinds": ["decision"],
        }
    ]


def test_list_tags_when_none(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """語彙が無ければ空の並びを返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1", tags=["データ"])))
    # 実行
    tags = query.list_tags(workspace)
    # 検証
    assert tags == []


@pytest.fixture
def five_decisions_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> store.Workspace:
    """検討事項 D-1〜D-5 を持つワークスペースを読み込んで返す。"""
    root = make_workspace(*(make_item(f"D-{number}") for number in range(1, 6)))
    return store.load_workspace(root)


def test_page_results(five_decisions_workspace: store.Workspace) -> None:
    """件数で切り、続きの値で残りを返す（正常系）。"""
    # 準備
    search_filter = query.SearchFilter()
    results = query.search_items(five_decisions_workspace, search_filter)
    # 実行
    first = query.page_results(results, search_filter, limit=3, cursor=None)
    second = query.page_results(results, search_filter, limit=3, cursor=first["next_cursor"])
    # 検証
    assert _ids(first["items"]) == ["D-1", "D-2", "D-3"]
    assert first["total"] == 5
    assert isinstance(first["next_cursor"], str)
    assert _ids(second["items"]) == ["D-4", "D-5"]
    assert second["total"] == 5
    assert second["next_cursor"] is None


def test_page_results_when_fits(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """件数に収まれば続きの値も案内も無い（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    search_filter = query.SearchFilter()
    results = query.search_items(workspace, search_filter)
    # 実行
    page = query.page_results(results, search_filter, limit=20, cursor=None)
    # 検証
    assert _ids(page["items"]) == ["D-1"]
    assert page["next_cursor"] is None
    assert page["hint"] is None


def test_page_results_when_cursor_mismatched(five_decisions_workspace: store.Workspace) -> None:
    """違う条件の続きの値は引数の誤りにする（異常系）。"""
    # 準備
    results = query.search_items(five_decisions_workspace, query.SearchFilter())
    first = query.page_results(results, query.SearchFilter(), limit=3, cursor=None)
    # 実行・検証
    with pytest.raises(ArgumentError) as raised:
        query.page_results(
            results, query.SearchFilter(kind="task"), limit=3, cursor=first["next_cursor"]
        )
    assert raised.value.argument == "cursor"


def test_page_results_when_cursor_broken(five_decisions_workspace: store.Workspace) -> None:
    """読めない続きの値は引数の誤りにする（異常系）。"""
    # 準備
    search_filter = query.SearchFilter()
    results = query.search_items(five_decisions_workspace, search_filter)
    # 実行・検証
    with pytest.raises(ArgumentError) as raised:
        query.page_results(results, search_filter, limit=3, cursor="!!")
    assert raised.value.argument == "cursor"


def test_encode_cursor_round_trip() -> None:
    """組み立てた値を同じ条件で読むと同じ位置に戻る（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(kind="decision")
    # 実行
    cursor = query._encode_cursor(20, search_filter)
    # 検証
    assert query._decode_cursor(cursor, search_filter) == 20
    assert not {"=", "/", "+"} & set(cursor)


def test_build_hint_when_truncated() -> None:
    """切り詰めたときは、渡していない絞り込みの引数を並べる（正常系）。"""
    # 実行
    hint = query.build_hint(45, 20, query.SearchFilter(kind="decision"), has_next=True)
    # 検証
    assert hint is not None
    assert "45" in hint
    assert "20" in hint
    assert "tags" in hint
    assert "status" in hint
    assert "next_cursor" in hint
    assert "kind" not in hint


def test_build_hint_when_empty() -> None:
    """0 件のときは、渡した条件の引数を並べる（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(kind="decision", tags=("保留",))
    # 実行
    hint = query.build_hint(0, 0, search_filter, has_next=False)
    # 検証
    assert hint is not None
    assert "kind" in hint
    assert "tags" in hint


def test_build_hint_when_stray_tag() -> None:
    """0 件で語彙にもどの項目にも無いタグは、近いタグを案内する（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(tags=("データー",))
    # 実行
    hint = query.build_hint(
        0, 0, search_filter, has_next=False, stray_tags=[("データー", ["データ"])]
    )
    # 検証
    assert hint is not None
    assert "tags" in hint
    assert "データー は語彙にもどの項目にも無いタグです（近いタグ: データ）" in hint


@pytest.mark.parametrize(
    ("total", "returned", "search_filter"),
    [
        pytest.param(3, 3, query.SearchFilter(), id="fits"),
        pytest.param(0, 0, query.SearchFilter(), id="empty_without_filter"),
    ],
)
def test_build_hint_when_none(total: int, returned: int, search_filter: query.SearchFilter) -> None:
    """収まったときと、条件なしで 0 件のときは案内しない（正常系）。"""
    # 実行
    hint = query.build_hint(total, returned, search_filter, has_next=False)
    # 検証
    assert hint is None


def test_list_stray_tags(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """項目が使う未登録の候補と語彙のタグは除き、どこにも無いタグだけを返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["通知"]),
        settings={**valid_settings, "tags": [{"name": "データ"}]},
    )
    workspace = store.load_workspace(root)
    search_filter = query.SearchFilter(tags=("通知", "データー"), any_tags=("データ", "データー"))
    # 実行
    stray_tags = query.list_stray_tags(workspace, search_filter)
    # 検証
    assert stray_tags == [("データー", ["データ"])]
