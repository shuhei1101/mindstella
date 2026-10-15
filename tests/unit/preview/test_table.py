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


# 文字の条件の行（G-12 は ID に G-1 を含み、G-4 はタイトルの途中に「シナリオ」を含む）
TEXT_FILTER_ROWS = [
    {"id": "G-1", "title": "シナリオの依頼", "tags": ["a"]},
    {"id": "G-12", "title": "依頼の控え", "tags": ["b"]},
    {"id": "G-2", "title": "データの移し替え", "tags": ["a"]},
    {"id": "G-3", "title": "データの移し先", "tags": ["b"]},
    {"id": "G-4", "title": "古いシナリオ", "tags": []},
]


@pytest.mark.parametrize(
    ("filters", "expected_ids"),
    [
        pytest.param({"~title": ["シナリオ"]}, ["G-1", "G-4"], id="title_contains"),
        pytest.param({"~id": ["g-1"]}, ["G-1", "G-12"], id="id_contains_case_insensitive"),
        pytest.param({"~title": ["移し"], "tags": ["a"]}, ["G-2"], id="text_and_value"),
        pytest.param(
            {"~nope": ["x"]}, ["G-1", "G-12", "G-2", "G-3", "G-4"], id="unknown_column_ignored"
        ),
    ],
)
def test_filter_rows_text(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    filters: dict[str, list[str]],
    expected_ids: list[str],
) -> None:
    """文字の条件は含む一致で、値の条件と重ねられる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    ids = preview_page.evaluate(
        """({rows, filters}) => {
            // 条件の定義は `key` と値を取る `get` だけを持つ
            const columns = ["id", "title", "tags"].map((key) => ({key, get: (row) => row[key]}));
            return MindmapPreview.filterRows({rows, columns, filters}).map((row) => row.id);
        }""",
        {"rows": TEXT_FILTER_ROWS, "filters": filters},
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
    ("tab", "from_hash", "saved", "expected"),
    [
        pytest.param(
            "decisions",
            {},
            None,
            {"status": ["要見直し", "未決定", "未整理", "保留"]},
            id="decisions_default",
        ),
        pytest.param(
            "decisions",
            {"phase": ["要件"]},
            {"status": ["保留"]},
            {"phase": ["要件"]},
            id="decisions_hash_over_saved",
        ),
        pytest.param("tasks", {}, None, {}, id="tasks_default"),
        pytest.param("decisions", {}, {}, {}, id="decisions_saved_cleared"),
        pytest.param("tasks", {}, {"status": ["未着手"]}, {"status": ["未着手"]}, id="tasks_saved"),
    ],
)
def test_initial_filters(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    tab: str,
    from_hash: dict[str, list[str]],
    saved: dict[str, list[str]] | None,
    expected: dict[str, list[str]],
) -> None:
    """ハッシュ → 残した条件 → 画面の既定の順に使う（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    filters = preview_page.evaluate(
        "({tab, fromHash, saved}) => MindmapPreview.initialFilters(tab, fromHash, saved)",
        {"tab": tab, "fromHash": from_hash, "saved": saved},
    )
    # 検証
    assert filters == expected


# 残した条件の刈り込みの行（状態が未着手・完了、タグが a）
PRUNE_ROWS = [
    {"id": "T-1", "status": "未着手", "tags": ["a"]},
    {"id": "T-2", "status": "完了", "tags": ["a"]},
]


@pytest.mark.parametrize(
    ("saved", "expected"),
    [
        pytest.param({"status": ["未着手", "保留"]}, {"status": ["未着手"]}, id="unknown_value"),
        pytest.param({"tags": ["b"]}, {}, id="no_value_left"),
        pytest.param(
            {"~title": ["x"], "nope": ["y"]}, {"~title": ["x"]}, id="text_and_unknown_key"
        ),
        pytest.param({}, {}, id="empty"),
    ],
)
def test_prune_filters(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    saved: dict[str, list[str]],
    expected: dict[str, list[str]],
) -> None:
    """記録に無い値だけを外す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """({rows, saved}) => {
            // 条件の定義は `key` と値を取る `get` だけを持つ
            const columns = ["status", "tags"].map((key) => ({key, get: (row) => row[key]}));
            const copy = JSON.parse(JSON.stringify(saved));
            return {pruned: MindmapPreview.pruneFilters({rows, columns, saved}), saved, copy};
        }""",
        {"rows": PRUNE_ROWS, "saved": saved},
    )
    # 検証
    assert result["pruned"] == expected
    assert result["saved"] == result["copy"]


# 用語集の表の列（`filterable` の列が値で絞る列。数の列は持たない）
TERMS_COLUMN_SPECS = [
    {"key": "id"},
    {"key": "title"},
    {"key": "meaning"},
    {"key": "aliases"},
    {"key": "avoid"},
    {"key": "tags", "filterable": True},
]

# 検討事項の表の列
DECISIONS_COLUMN_SPECS = [
    {"key": "id"},
    {"key": "title"},
    {"key": "status", "filterable": True},
    {"key": "target", "filterable": True},
    {"key": "category", "filterable": True},
    {"key": "phase", "filterable": True},
    {"key": "weight", "filterable": True},
    {"key": "ready", "filterable": True},
    {"key": "depends_on"},
    {"key": "tags", "filterable": True},
]


@pytest.mark.parametrize(
    ("specs", "expected_keys"),
    [
        pytest.param(
            TERMS_COLUMN_SPECS, ["id", "title", "meaning", "aliases", "avoid"], id="terms"
        ),
        pytest.param(DECISIONS_COLUMN_SPECS, ["id", "title", "depends_on"], id="decisions"),
    ],
)
def test_text_columns(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    specs: list[dict[str, Any]],
    expected_keys: list[str],
) -> None:
    """値を選ぶ列と数の列を除く（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    keys = preview_page.evaluate(
        """(specs) => {
            const columns = specs.map((spec) => ({...spec, label: spec.key, get: () => ""}));
            return MindmapPreview.textColumns(columns).map((column) => column.key);
        }""",
        specs,
    )
    # 検証
    assert keys == expected_keys


def test_table_when_withdrawn(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """取り下げた行だけに札を差分の印より前に置き、文字を薄くする（正常系）。"""
    # 準備
    rows = [
        {"id": "R-1", "title": "取り下げた調査", "withdrawn": True},
        {"id": "R-2", "title": "残した調査"},
    ]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """({rows, marks}) => {
            const noop = () => {};
            const columns = [
                {key: "id", label: "ID", get: (row) => row.id},
                {key: "title", label: "タイトル", fixed: true, get: (row) => row.title},
            ];
            const element = MindmapPreview.table({
                kind: "research",
                columns,
                rows,
                marks,
                on: {sort: noop, filter: noop, pin: noop, columns: noop, reset: noop, open: noop},
            });
            document.body.append(element);
            // 行のタイトルのセルの中身を、並びの種類にする
            const kindOf = (child) =>
                child.classList.contains("row-open")
                    ? "title"
                    : child.classList.contains("wd-badge")
                      ? "withdrawn"
                      : child.classList.contains("df-mark")
                        ? "diff"
                        : "other";
            const summarize = (id) => {
                const row = element.querySelector(`tr[data-id="${id}"]`);
                const titleCell = row.querySelector('td[data-col="1"]');
                return {
                    order: [...titleCell.children].map(kindOf),
                    badgeText: titleCell.querySelector(".wd-badge")?.textContent ?? null,
                    dimmed: row.classList.contains("is-withdrawn"),
                };
            };
            return {withdrawn: summarize("R-1"), kept: summarize("R-2")};
        }""",
        {"rows": rows, "marks": {"R-1": "changed"}},
    )
    # 検証
    assert result["withdrawn"]["order"] == ["title", "withdrawn", "diff"]
    assert "取り下げ" in result["withdrawn"]["badgeText"]
    assert result["withdrawn"]["dimmed"] is True
    assert result["kept"] == {"order": ["title"], "badgeText": None, "dimmed": False}
