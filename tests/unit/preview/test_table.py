"""components/table.ts（表と、並べ替え・絞り込みの計算）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 列の定義を作る JavaScript（値を取る get は関数なので、ページの中で作る）
COLUMNS_JS = """
    const makeColumns = (specs) => specs.map(({key, order}) => ({
        key,
        label: key,
        filterable: true,
        order,
        get: (row) => row[key],
    }));
"""

# 絞り込みの行
FILTER_ROWS = [
    {"id": "D-1", "status": "要見直し", "ready": "なし", "tags": ["a", "b"]},
    {"id": "D-2", "status": "保留", "ready": "なし", "tags": ["c"]},
    {"id": "D-3", "status": "未決定", "ready": "着手可能", "tags": ["a"]},
    {"id": "D-4", "status": "未決定", "ready": "前提待ち", "tags": []},
]


@pytest.mark.parametrize(
    ("filters", "expected_ids"),
    [
        pytest.param({"status": ["要見直し", "保留"]}, ["D-1", "D-2"], id="any_in_column"),
        pytest.param({"status": ["未決定"], "ready": ["着手可能"]}, ["D-3"], id="all_columns"),
        pytest.param({"tags": ["a"]}, ["D-1", "D-3"], id="array_value"),
        pytest.param({}, ["D-1", "D-2", "D-3", "D-4"], id="no_filter"),
    ],
)
def test_filter_rows(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    filters: dict[str, list[str]],
    expected_ids: list[str],
) -> None:
    """列の中はどれか、列の間は全て（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    ids = preview_page.evaluate(
        """({rows, filters}) => {
            // 条件の定義は `key` と値を取る `get` だけを持つ
            const columns = ["status", "ready", "tags"].map((key) => ({key, get: (row) => row[key]}));
            return MindmapPreview.filterRows({rows, columns, filters}).map((row) => row.id);
        }""",
        {"rows": FILTER_ROWS, "filters": filters},
    )
    # 検証
    assert ids == expected_ids


@pytest.mark.parametrize(
    ("sort", "expected_ids"),
    [
        pytest.param({"key": "title", "dir": "asc"}, ["R-2", "R-3", "R-1"], id="title_asc"),
        pytest.param({"key": "status", "dir": "desc"}, ["R-3", "R-2", "R-1"], id="order_desc"),
        pytest.param(None, ["R-1", "R-2", "R-3"], id="none"),
    ],
)
def test_sort_rows(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    sort: dict[str, Any] | None,
    expected_ids: list[str],
) -> None:
    """昇順・降順・解除（正常系）。"""
    # 準備
    rows = [
        {"id": "R-1", "title": "うさぎ", "status": "未決定"},
        {"id": "R-2", "title": "あひる", "status": "決定済み"},
        {"id": "R-3", "title": "いぬ", "status": "保留"},
    ]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        f"""({{rows, sort}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([
                {{key: "title"}},
                {{key: "status", order: ["未決定", "決定済み", "保留"]}},
            ]);
            const sorted = MindmapPreview.sortRows({{rows, columns, sort}});
            return {{sorted: sorted.map((row) => row.id), original: rows.map((row) => row.id)}};
        }}""",
        {"rows": rows, "sort": sort},
    )
    # 検証
    assert result["sorted"] == expected_ids
    # 渡した配列は変わらない
    assert result["original"] == ["R-1", "R-2", "R-3"]


def test_filter_counts(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """ほかの列の条件だけを当てて数える（正常系）。"""
    # 準備
    rows = [
        {"id": "D-1", "status": "未決定", "category": "A"},
        {"id": "D-2", "status": "決定済み", "category": "A"},
        {"id": "D-3", "status": "未決定", "category": "B"},
        {"id": "D-4", "status": "未決定", "category": "A"},
    ]
    filters = {"status": ["未決定"], "category": ["A"]}
    load_preview_scripts()
    # 実行
    counts = preview_page.evaluate(
        f"""({{rows, filters}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([
                {{key: "status", order: ["未決定", "決定済み"]}},
                {{key: "category"}},
            ]);
            return MindmapPreview.filterCounts({{rows, columns, filters, key: "status"}});
        }}""",
        {"rows": rows, "filters": filters},
    )
    # 検証
    assert counts == [{"value": "未決定", "count": 2}, {"value": "決定済み", "count": 1}]


def test_drawer_groups(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """種類・状態・タグを先に並べ、件数はその条件以外で絞って数える（正常系）。"""
    # 準備
    rows = [
        {"id": "T-1", "kind": "作業", "status": "未着手", "tags": ["a"], "target": "甲"},
        {"id": "T-2", "kind": "調査", "status": "完了", "tags": ["a", "b"], "target": "乙"},
    ]
    filters = {"kind": ["作業"]}
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        f"""({{rows, filters}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([
                {{key: "target"}},
                {{key: "tags"}},
                {{key: "status", order: ["未着手", "完了"]}},
                {{key: "kind"}},
            ]);
            const groups = MindmapPreview.drawerGroups({{rows, columns, filters}});
            return {{
                keys: groups.map((group) => group.key),
                values: Object.fromEntries(
                    groups.map((group) => [
                        group.key,
                        group.values.map((entry) => [entry.value, entry.count]),
                    ]),
                ),
                statusMark: groups.find((group) => group.key === "status").mark,
            }};
        }}""",
        {"rows": rows, "filters": filters},
    )
    # 検証
    assert result["keys"] == ["kind", "status", "tags", "target"]
    assert result["values"]["kind"] == [["作業", 1], ["調査", 1]]
    assert result["values"]["status"] == [["未着手", 1], ["完了", 0]]
    assert result["values"]["tags"] == [["a", 1], ["b", 0]]
    assert result["statusMark"] == "status"


def test_drawer_groups_when_no_values(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """値を持たない条件は含めない（正常系）。"""
    # 準備
    rows = [
        {"id": "D-1", "status": "未決定", "tags": []},
        {"id": "D-2", "status": "保留", "tags": []},
    ]
    load_preview_scripts()
    # 実行
    keys = preview_page.evaluate(
        f"""({{rows}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([{{key: "status"}}, {{key: "tags"}}]);
            return MindmapPreview.drawerGroups({{rows, columns, filters: {{}}}}).map(
                (group) => group.key
            );
        }}""",
        {"rows": rows},
    )
    # 検証
    assert keys == ["status"]


def test_drawer_groups_when_hit(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """キーワードに一致した件数を添える（正常系）。"""
    # 準備
    rows = [
        {"id": "D-1", "status": "未決定"},
        {"id": "D-2", "status": "未決定"},
        {"id": "D-3", "status": "保留"},
    ]
    load_preview_scripts()
    # 実行
    values = preview_page.evaluate(
        f"""({{rows}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([{{key: "status", order: ["未決定", "保留"]}}]);
            const hit = (row) => row.id === "D-1";
            const groups = MindmapPreview.drawerGroups({{rows, columns, filters: {{}}, hit}});
            return groups.find((group) => group.key === "status").values.map(
                (entry) => [entry.value, entry.count, entry.hit]
            );
        }}""",
        {"rows": rows},
    )
    # 検証
    assert values == [["未決定", 2, 1], ["保留", 1, 0]]


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        pytest.param({}, 0, id="empty"),
        pytest.param({"status": ["未決定", "保留"], "tags": ["a"]}, 2, id="two_conditions"),
        pytest.param({"status": []}, 0, id="no_value_selected"),
    ],
)
def test_active_condition_count(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    filters: dict[str, list[str]],
    expected: int,
) -> None:
    """値を選んだ条件だけを数える（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    count = preview_page.evaluate(
        "(filters) => MindmapPreview.activeConditionCount(filters)", filters
    )
    # 検証
    assert count == expected


@pytest.mark.parametrize(
    ("tab", "from_hash", "expected"),
    [
        pytest.param(
            "decisions",
            {},
            {"status": ["要見直し", "未決定", "未整理", "保留"]},
            id="decisions_default",
        ),
        pytest.param("decisions", {"phase": ["要件"]}, {"phase": ["要件"]}, id="decisions_hash"),
        pytest.param("tasks", {}, {}, id="tasks_default"),
    ],
)
def test_initial_filters(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    tab: str,
    from_hash: dict[str, list[str]],
    expected: dict[str, list[str]],
) -> None:
    """ハッシュがあれば既定に代えて使う（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    filters = preview_page.evaluate(
        "({tab, fromHash}) => MindmapPreview.initialFilters(tab, fromHash)",
        {"tab": tab, "fromHash": from_hash},
    )
    # 検証
    assert filters == expected
