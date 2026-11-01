"""query.py（検索・1 件の表示と参照元・属性名の一覧）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import query
import store
from errors import ArgumentError
from fixture_types import MakeItem, MakeWorkspace


def _ids(hits: list[query.SearchHit]) -> list[str]:
    """検索で当たった項目から ID だけを並びのまま取り出す。"""
    return [hit.item["id"] for hit in hits]


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
    assert _ids(result) == ["D-1"]
    assert result[0].kind == "decision"


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
        make_item("D-1", tags=[{"name": "データ"}]),
        make_item("D-2", tags=[{"name": "画面"}]),
        make_item("T-1", tags=[{"name": "データ"}, {"name": "画面"}]),
        make_item("N-1"),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = query.search_items(workspace, query.SearchFilter(**conditions))
    # 検証
    assert _ids(result) == expected_ids


def test_search_items_when_tag_normalized(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """全角・大文字の違うタグでも当たる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "API"}]),
        make_item("D-2", tags=[{"name": "ａｐｉ"}]),
        make_item("D-3", tags=[{"name": "データ"}]),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = query.search_items(workspace, query.SearchFilter(tags=("api",)))
    # 検証
    assert _ids(result) == ["D-1", "D-2"]
    assert [hit.item["tags"] for hit in result] == [[{"name": "API"}], [{"name": "ａｐｉ"}]]


@pytest.mark.parametrize(
    ("conditions", "expected_ids"),
    [
        pytest.param({"tags": ("データ",)}, ["D-2", "T-1", "D-1"], id="tags"),
        pytest.param({"any_tags": ("データ", "画面")}, ["D-2", "T-1", "T-2", "D-1"], id="any_tags"),
        pytest.param({}, ["D-1", "D-2", "T-1", "T-2"], id="no_tags"),
    ],
)
def test_search_items_when_main_tag_first(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    conditions: dict[str, tuple[str, ...]],
    expected_ids: list[str],
) -> None:
    """渡したタグを主題として持つ項目を先に並べ、それぞれの中は種類の順・連番の順（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "データ"}]),
        make_item("D-2", tags=[{"name": "データ", "main": True}]),
        make_item("T-1", tags=[{"name": "ﾃﾞｰﾀ", "main": True}, {"name": "画面"}]),
        make_item("T-2", tags=[{"name": "画面", "main": True}]),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = query.search_items(workspace, query.SearchFilter(**conditions))
    # 検証
    assert _ids(result) == expected_ids


def test_search_items_when_chars(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """各項目に item_chars の文字数を添える（正常系）。"""
    # 準備
    decision = make_item("D-1", body="D-1.md")
    note = make_item("N-1")
    root = make_workspace(decision, note, bodies={"D-1.md": "本文\n"})
    workspace = store.load_workspace(root)
    # 実行
    result = query.search_items(workspace, query.SearchFilter())
    # 検証
    assert [hit.chars for hit in result] == [
        query.item_chars(workspace, decision),
        query.item_chars(workspace, note),
    ]


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


def test_list_tags(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """表記の違いをまとめ、種類とスレッドをまたいで件数の多い順に並べる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "API", "main": True}]),
        make_item("D-2", tags=[{"name": "画面"}]),
        make_item("T-1", tags=[{"name": "ａｐｉ"}]),
        make_item("N-1"),
    )
    workspace = store.load_workspace(root)
    # 実行
    tags = query.list_tags(workspace, [["api", "画面"]])
    # 検証
    assert tags == [
        {"name": "api", "count": 3, "kinds": ["decision", "task", "thread"]},
        {"name": "画面", "count": 2, "kinds": ["decision", "thread"]},
    ]


def test_list_tags_when_duplicated(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """1 つの項目が同じタグを表記を変えて 2 回持っても 1 件と数える（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1", tags=[{"name": "データ"}, {"name": "ﾃﾞｰﾀ"}])))
    # 実行
    tags = query.list_tags(workspace, [])
    # 検証
    assert tags == [{"name": "データ", "count": 1, "kinds": ["decision"]}]


def test_list_tags_when_none(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """タグが無ければ空の並びを返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    tags = query.list_tags(workspace, [[]])
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
    """0 件でどの項目も使っていないタグは、近いタグを案内する（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(tags=("データー",))
    # 実行
    hint = query.build_hint(
        0, 0, search_filter, has_next=False, stray_tags=[("データー", ["データ"])]
    )
    # 検証
    assert hint is not None
    assert "tags" in hint
    assert "データー はどの項目も使っていないタグです（近いタグ: データ）" in hint


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


def test_list_stray_tags(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """項目が使うタグは表記が違っても除き、どの項目も使っていないタグだけを返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=[{"name": "データ"}, {"name": "API"}]))
    workspace = store.load_workspace(root)
    search_filter = query.SearchFilter(tags=("ａｐｉ", "データー"), any_tags=("データ", "データー"))
    # 実行
    stray_tags = query.list_stray_tags(workspace, search_filter)
    # 検証
    assert stray_tags == [("データー", ["データ"])]


@pytest.mark.parametrize(
    ("item_id", "body", "bodies", "body_chars"),
    [
        pytest.param("D-1", "D-1.md", {"D-1.md": "あいう"}, 3, id="with_body"),
        pytest.param("N-1", None, {}, 0, id="without_body"),
        pytest.param("D-9", "D-9.md", {}, 0, id="body_file_missing"),
    ],
)
def test_item_chars(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    item_id: str,
    body: str | None,
    bodies: dict[str, str],
    body_chars: int,
) -> None:
    """YAML の文字数に本文の文字数を加える（正常系）。"""
    # 準備
    item = make_item(item_id) if body is None else make_item(item_id, body=body)
    workspace = store.load_workspace(make_workspace(item, bodies=bodies))
    # 実行
    chars = query.item_chars(workspace, item)
    # 検証
    assert chars == len(store.dump_yaml(item)) + body_chars


@pytest.mark.parametrize(
    ("view", "include", "exclude", "expected"),
    [
        pytest.param("brief", [], [], ("title", "status", "tags", "chars"), id="brief"),
        pytest.param(
            "standard",
            ["body"],
            ["tags"],
            ("title", "status", "chars", "target", "category", "phase", "attrs", "updated", "body"),
            id="standard_include_exclude",
        ),
        pytest.param(
            "full",
            [],
            ["extra", "body"],
            ("title", "status", "tags", "chars", "target", "category", "phase", "attrs", "updated"),
            id="full_exclude",
        ),
    ],
)
def test_resolve_fields(
    view: str, include: list[str], exclude: list[str], expected: tuple[str, ...]
) -> None:
    """返す量に加え・外した名前を決まった順で返す（正常系）。"""
    # 実行
    fields = query.resolve_fields(view, include=include, exclude=exclude)
    # 検証
    assert fields == expected


def test_resolve_fields_when_overlapped() -> None:
    """include と exclude に同じ名前は引数の誤りにする（異常系）。"""
    # 実行・検証
    with pytest.raises(ArgumentError, match=r"exclude.*attrs|attrs.*exclude") as raised:
        query.resolve_fields("brief", include=["attrs"], exclude=["attrs"])
    assert raised.value.argument == "include"


@pytest.fixture
def row_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> store.Workspace:
    """案・依存・属性・本文を持つ D-1 と、本文の無い N-1 を持つワークスペースを読み込んで返す。"""
    root = make_workspace(
        make_item(
            "D-1",
            target="mindmap",
            attrs={"担当": "自分"},
            depends_on=["D-2"],
            options=[{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}],
            body="D-1.md",
        ),
        make_item("D-2"),
        make_item("N-1"),
        bodies={"D-1.md": "# 本文\n"},
    )
    return store.load_workspace(root)


def _hit(workspace: store.Workspace, item_id: str) -> query.SearchHit:
    """検索で当たった項目のうち、ID が item_id のものを返す。"""
    hits = query.search_items(workspace, query.SearchFilter())
    return next(hit for hit in hits if hit.item["id"] == item_id)


@pytest.mark.parametrize(
    ("item_id", "fields", "expected_keys", "expected_values"),
    [
        pytest.param(
            "D-1",
            ("title", "status", "tags", "chars"),
            ["id", "kind", "title", "status", "tags", "chars"],
            {"id": "D-1", "kind": "decision", "tags": []},
            id="brief",
        ),
        pytest.param(
            "D-1",
            ("target", "attrs", "extra", "body"),
            ["id", "kind", "target", "attrs", "extra", "body", "body_format"],
            {
                "target": "mindmap",
                "attrs": {"担当": "自分"},
                "body": "# 本文\n",
                "body_format": "markdown",
            },
            id="extra_and_body",
        ),
        pytest.param(
            "N-1",
            ("body",),
            ["id", "kind", "body", "body_format"],
            {"body": None, "body_format": None},
            id="body_missing",
        ),
    ],
)
def test_build_row(
    row_workspace: store.Workspace,
    item_id: str,
    fields: tuple[str, ...],
    expected_keys: list[str],
    expected_values: dict[str, Any],
) -> None:
    """選んだ名前だけを決まった中身で入れる（正常系）。"""
    # 準備
    hit = _hit(row_workspace, item_id)
    # 実行
    row = query.build_row(row_workspace, hit, fields)
    # 検証
    assert list(row) == expected_keys
    assert {key: row[key] for key in expected_values} == expected_values
    if "chars" in fields:
        assert row["chars"] == hit.chars
    if "extra" in fields:
        assert "options" in row["extra"]
        assert row["extra"]["depends_on"] == ["D-2"]
        assert "title" not in row["extra"]


def test_count_tags(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """表記の違いをまとめ、件数の多い順に並べる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "データ", "main": True}, {"name": "画面"}]),
        make_item("D-2", tags=[{"name": "ﾃﾞｰﾀ"}]),
        make_item("N-1"),
    )
    workspace = store.load_workspace(root)
    hits = query.search_items(workspace, query.SearchFilter())
    # 実行
    counts = query.count_tags(hits)
    # 検証
    assert counts == [{"tag": "データ", "count": 2}, {"tag": "画面", "count": 1}]


def test_render_find_markdown() -> None:
    """件数の行・表・省いた項目の行を書く（正常系）。"""
    # 準備
    result = {
        "items": [
            {
                "id": "D-1",
                "kind": "decision",
                "title": "記録の単位",
                "status": "未決定",
                "tags": [{"name": "データ", "main": True}, {"name": "画面"}],
                "chars": 200,
            },
            {
                "id": "D-2",
                "kind": "decision",
                "title": "画面の構成",
                "status": "未決定",
                "tags": [],
                "chars": 100,
            },
        ],
        "total": 2,
        "total_chars": 300,
        "next_cursor": None,
        "hint": None,
        "omitted": ["target", "extra"],
    }
    # 実行
    text = query.render_find_markdown(result)
    # 検証
    lines = text.strip().splitlines()
    assert lines[0] == "全 2 件・合計 300 文字"
    header = next(line for line in lines if line.startswith("|"))
    assert [cell.strip() for cell in header.strip("|").split("|")] == [
        "id",
        "kind",
        "title",
        "status",
        "tags",
        "chars",
    ]
    decision_row = next(line for line in lines if line.startswith("| D-1 "))
    assert "データ [main]、画面" in decision_row
    assert lines[-1] == "省いた項目: target・extra（view か include で取れる）"


def test_render_find_markdown_when_body() -> None:
    """extra と本文は表の後のセクションに書く（正常系）。"""
    # 準備
    result = {
        "items": [
            {
                "id": "D-1",
                "kind": "decision",
                "title": "記録の単位",
                "extra": {"options": [{"key": "A", "content": "案 A"}]},
                "body": "# 本文",
                "body_format": "markdown",
            },
        ],
        "total": 1,
        "total_chars": 120,
        "next_cursor": "abc",
        "hint": "続きを読んでください",
        "omitted": [],
    }
    # 実行
    text = query.render_find_markdown(result)
    # 検証
    header = next(line for line in text.splitlines() if line.startswith("|"))
    assert "extra" not in header
    assert "body" not in header
    section = text[text.index("## D-1 記録の単位") :]
    assert "```yaml" in section
    assert "options:" in section
    assert section.index("options:") < section.index("# 本文")
    assert "next_cursor: abc" in text
    assert "続きを読んでください" in text
    assert "省いた項目" not in text


def test_render_find_markdown_when_count_only() -> None:
    """件数だけのときは先頭の行とタグの件数の表だけを書く（正常系）。"""
    # 準備
    result = {
        "total": 2,
        "total_chars": 300,
        "tag_counts": [{"tag": "データ", "count": 2}, {"tag": "画面", "count": 1}],
    }
    # 実行
    text = query.render_find_markdown(result)
    # 検証
    lines = [line for line in text.strip().splitlines() if line]
    assert lines[0] == "全 2 件・合計 300 文字"
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines[1:]]
    assert rows[0] == ["タグ", "件数"]
    assert rows[2:] == [["データ", "2"], ["画面", "1"]]
    assert len(lines) == 5
