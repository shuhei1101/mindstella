"""screens/decisions.ts（検討事項の画面とマップの木）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page, expect

from .fixture_types import LoadLibrary, LoadPreviewScripts, MakeData, MakeItem


def test_build_decision_tree(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """渡した検討事項を持たない枝を落とす（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "categories": [
            {"name": "カテゴリー甲", "target": "mindmap", "summary": "甲"},
            {"name": "カテゴリー乙", "target": "mindmap", "summary": "乙"},
        ],
    }
    data = make_data(
        settings=settings,
        decisions=[
            make_item(
                "D-1", target="mindmap", category="カテゴリー甲", phase="要件", status="未決定"
            ),
            make_item(
                "D-2", target="mindmap", category="カテゴリー乙", phase="要件", status="決定済み"
            ),
        ],
    )
    load_preview_scripts()
    # 実行
    tree = preview_page.evaluate(
        """({data, shownIds}) => {
            const index = MindmapPreview.buildIndex(data);
            // 絞り込みの条件に合った検討事項だけを渡す
            const decisions = data.decisions.filter((decision) => shownIds.includes(decision.id));
            const graph = MindmapPreview.buildDecisionTree({index, decisions});
            // 節は入れ子でも平らでも数えられるよう、再帰で集める
            const collect = (nodes) => nodes.flatMap((node) => [node.id, ...collect(node.children ?? [])]);
            return {nodeIds: collect(graph.children), edgeCount: graph.edges.length};
        }""",
        {"data": data, "shownIds": ["D-1"]},
    )
    # 検証
    node_ids = tree["nodeIds"]
    assert "D-1" in node_ids
    assert "D-2" not in node_ids
    # 検討事項 D-1 とその対象・カテゴリー・フェーズの 4 つだけが残り、枝は 3 本
    assert len(node_ids) == 4
    assert len([node_id for node_id in node_ids if node_id.startswith("target:")]) == 1
    assert tree["edgeCount"] == 3


@pytest.mark.parametrize(
    ("scale", "delta_y", "expected_scale"),
    [
        pytest.param(1, -100, 1.12, id="zoom_in"),
        pytest.param(1, 100, 1 / 1.12, id="zoom_out"),
        pytest.param(1.45, -1, 1.5, id="clamped_at_max"),
        pytest.param(0.42, 1, 0.4, id="clamped_at_min"),
        pytest.param(1.5, -1, 1.5, id="stays_at_max"),
        pytest.param(0.3, 1, 0.3, id="stays_below_min"),
    ],
)
def test_wheel_zoom(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    scale: float,
    delta_y: float,
    expected_scale: float,
) -> None:
    """奥へ回すと拡大し、手前へ回すと縮小し、範囲の端で止める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """({scale, deltaY}) => MindmapPreview.wheelZoom({
            scale,
            deltaY,
            point: {x: 0, y: 0},
            scroll: {left: 0, top: 0},
        })""",
        {"scale": scale, "deltaY": delta_y},
    )
    # 検証
    assert result["scale"] == pytest.approx(expected_scale)


@pytest.mark.parametrize(
    ("scale", "expected_scale", "expected_scroll"),
    [
        pytest.param(1, 1.12, {"left": 360, "top": 68}, id="point_kept"),
        pytest.param(1.5, 1.5, {"left": 300, "top": 50}, id="unchanged_at_max"),
    ],
)
def test_wheel_zoom_keeps_point(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    scale: float,
    expected_scale: float,
    expected_scroll: dict[str, float],
) -> None:
    """マウスの下の点を残すスクロールの位置を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """({scale}) => MindmapPreview.wheelZoom({
            scale,
            deltaY: -1,
            point: {x: 200, y: 100},
            scroll: {left: 300, top: 50},
        })""",
        {"scale": scale},
    )
    # 検証
    assert result["scale"] == pytest.approx(expected_scale)
    assert result["scroll"]["left"] == pytest.approx(expected_scroll["left"])
    assert result["scroll"]["top"] == pytest.approx(expected_scroll["top"])


# マップを字下げの一覧にしない幅と、画面を描く窓の高さ（px）
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# 消した項目の帯の読み上げ名
REMOVED_BAND_NAME = "この時点で消した項目"


@pytest.mark.parametrize(
    ("view", "filters", "list_selector", "ready_selector"),
    [
        pytest.param("map", {}, ".map-frame", ".map-node.n-item", id="map"),
        pytest.param("board", {}, ".board", ".board .card", id="board"),
        pytest.param("table", {}, ".table-block", "tbody tr[data-id]", id="table"),
        pytest.param(
            "board",
            {"status": ["決定済み"]},
            ".board",
            ".board .card",
            id="board_filtered",
        ),
    ],
)
def test_decisions_screen_when_removed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
    view: str,
    filters: dict[str, list[str]],
    list_selector: str,
    ready_selector: str,
) -> None:
    """消した検討事項を、表示形式と絞り込みによらず一覧の上の帯に出す（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item("D-1", status="未決定"),
            make_item("D-2", status="決定済み", answer="案 A"),
        ]
    )
    removed = [{"id": "D-53", "kind": "decision", "title": "消した検討事項"}]
    preview_page.set_viewport_size({"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT})
    load_preview_scripts()
    load_library("elkjs")
    # 実行
    preview_page.evaluate(
        """({data, view, filters, removed}) => {
            const index = MindmapPreview.buildIndex(data);
            const noop = () => {};
            const screen = MindmapPreview.decisionsScreen({
                index,
                route: {tab: "decisions", view, id: null, full: false, filters: {}, heading: null},
                on: {
                    open: noop,
                    view: noop,
                    clear: noop,
                    filter: noop,
                    closeDrawer: noop,
                    lock: () => null,
                },
                filters,
                drawerOpen: false,
                lockedId: null,
                removed,
            });
            document.body.append(screen);
        }""",
        {"data": data, "view": view, "filters": filters, "removed": removed},
    )
    preview_page.wait_for_selector(ready_selector)
    # 検証
    band = preview_page.get_by_role("region", name=REMOVED_BAND_NAME)
    expect(band).to_have_count(1)
    expect(band).to_contain_text("D-53")
    # 帯は一覧より前にある
    assert band.evaluate(
        "(band, selector) => (band.compareDocumentPosition(document.querySelector(selector))"
        " & Node.DOCUMENT_POSITION_FOLLOWING) !== 0",
        list_selector,
    )
    # 消した検討事項は、一覧（マップの節・ボードの列・表の行）には出ない
    expect(preview_page.locator(list_selector).filter(has_text="D-53")).to_have_count(0)
