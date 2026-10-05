"""graph/graph.ts（つながり）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem

# 絞り込みの条件に合う項目の ID（N-1 を外す）
SHOWN_IDS = ["D-1", "D-2", "T-1", "R-1"]


def test_build_graph(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """線の種類を分け、渡していない項目の線を落とす（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1"), make_item("D-2", depends_on=["D-1"], sources=["R-1"])],
        tasks=[make_item("T-1", **{"for": ["D-1"]})],
        research=[make_item("R-1")],
        notes=[make_item("N-1", related=["D-1"])],
    )
    load_preview_scripts()
    # 実行
    graph = preview_page.evaluate(
        """({data, shown}) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.buildGraph({index, shownIds: new Set(shown)});
        }""",
        {"data": data, "shown": SHOWN_IDS},
    )
    # 検証
    links = sorted((link["type"], link["source"], link["target"]) for link in graph["links"])
    assert links == [
        ("depends", "D-2", "D-1"),
        ("for", "T-1", "D-1"),
        ("source", "D-2", "R-1"),
    ]
    assert "N-1" not in [node["id"] for node in graph["nodes"]]


def test_graph_conditions(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """種類・状態・タグの値を取る（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", status="未決定", tags=["a"])],
        notes=[make_item("N-1")],
    )
    load_preview_scripts()
    # 実行
    values = preview_page.evaluate(
        """(data) => {
            const index = MindmapPreview.buildIndex(data);
            const conditions = MindmapPreview.graphConditions();
            const valuesOf = (id) => Object.fromEntries(
                conditions.map((condition) => [condition.key, condition.get(index.byId.get(id)) ?? null])
            );
            return {keys: conditions.map((condition) => condition.key), d1: valuesOf("D-1"), n1: valuesOf("N-1")};
        }""",
        data,
    )
    # 検証
    assert values["keys"] == ["type", "status", "tags"]
    assert values["d1"] == {"type": "検討事項", "status": "未決定", "tags": ["a"]}
    assert values["n1"] == {"type": "メモ", "status": None, "tags": []}
