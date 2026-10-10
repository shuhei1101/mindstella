"""core/records.ts（記録の索引・関係する項目・検索・箇所の名前）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem


def test_build_index(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """ID で引け、参照元を逆に引ける（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1"), make_item("D-2", depends_on=["D-1"])],
        tasks=[make_item("T-1", **{"for": ["D-1"]})],
        next_ids=["D-1"],
    )
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(data) => {
            const index = MindmapPreview.buildIndex(data);
            return {
                kind: index.byId.get("T-1").kind,
                referencedBy: index.referencedBy.get("D-1"),
                readyIds: [...index.readyIds],
            };
        }""",
        data,
    )
    # 検証
    assert result == {"kind": "tasks", "referencedBy": ["D-2", "T-1"], "readyIds": ["D-1"]}


def test_related_items(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """関係の種類ごとに分ける（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item("D-1", depends_on=["D-0"]),
            make_item("D-2", depends_on=["D-1"]),
        ],
        tasks=[make_item("T-1", **{"for": ["D-1"]})],
        logs=[make_item("L-1", related=["D-1"])],
        notes=[make_item("N-1", related=["D-1"])],
    )
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(data) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.relatedItems({id: "D-1", index});
        }""",
        data,
    )
    # 検証
    assert result["prerequisites"] == ["D-0"]
    assert result["successors"] == ["D-2"]
    assert result["tasks"] == ["T-1"]
    assert result["logs"] == ["L-1"]
    assert result["referencedBy"] == ["N-1"]


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        pytest.param("d-1", ["D-1"], id="id_case_insensitive"),
        pytest.param("ゼブラ", ["A-1"], id="body_only"),
        pytest.param("d-1 ゼブラ", [], id="only_one_word"),
        pytest.param("   ", [], id="blank"),
    ],
)
def test_search_items(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    query: str,
    expected_ids: list[str],
) -> None:
    """全ての語を含む項目を返す（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1"), make_item("D-2")],
        docs=[make_item("A-1")],
        bodies={"A-1.md": "ゼブラの話\n"},
    )
    load_preview_scripts()
    # 実行
    found = preview_page.evaluate(
        """({data, query}) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.searchItems({query, index}).map((hit) => hit.id);
        }""",
        {"data": data, "query": query},
    )
    # 検証
    assert found == expected_ids


@pytest.mark.parametrize(
    ("kinds", "bodies", "query", "expected_hits"),
    [
        pytest.param(
            {
                "decisions": [("D-1", {"title": "シナリオの依頼の受け方"})],
                "terms": [("G-1", {"title": "シナリオの依頼"})],
                "docs": [("A-1", {})],
            },
            {"A-1.md": "シナリオの依頼の話\n"},
            "シナリオの依頼 ",
            [["G-1", 1], ["D-1", 2], ["A-1", 3]],
            id="title_exact_then_title_part_then_other",
        ),
        pytest.param(
            {
                "terms": [
                    ("G-1", {"title": "シナリオの依頼"}),
                    ("G-12", {"title": "依頼の控え"}),
                ],
            },
            {},
            "g-1",
            [["G-1", 1], ["G-12", 3]],
            id="id_exact_case_insensitive",
        ),
        pytest.param(
            {
                "decisions": [("D-1", {"answer": "保存先は共有のフォルダにする"})],
                "docs": [("A-2", {"title": "保存先の決め方"})],
            },
            {"A-2.md": "本文\n"},
            "保存先",
            [["A-2", 2], ["D-1", 3]],
            id="tier_before_kind_order",
        ),
        pytest.param(
            {
                "decisions": [("D-1", {"title": "シナリオの依頼の受け方"})],
                "terms": [("G-1", {"title": "シナリオの依頼"})],
                "docs": [("A-1", {})],
            },
            {"A-1.md": "シナリオの依頼の話\n"},
            "シナリオ 受け方",
            [["D-1", 2]],
            id="all_words_in_title",
        ),
    ],
)
def test_search_items_tier_order(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    kinds: dict[str, list[tuple[str, dict[str, Any]]]],
    bodies: dict[str, str],
    query: str,
    expected_hits: list[list[Any]],
) -> None:
    """段の順に並べる（正常系）。"""
    # 準備
    data = make_data(
        bodies=bodies,
        **{
            kind: [make_item(item_id, **overrides) for item_id, overrides in specs]
            for kind, specs in kinds.items()
        },
    )
    load_preview_scripts()
    # 実行
    found = preview_page.evaluate(
        """({data, query}) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.searchItems({query, index}).map((hit) => [hit.id, hit.tier]);
        }""",
        {"data": data, "query": query},
    )
    # 検証
    assert found == expected_hits


@pytest.mark.parametrize(
    ("loc", "expected"),
    [
        pytest.param({"kind": "body", "start": 3, "end": 3}, "本文 3 行目", id="body_one_line"),
        pytest.param({"kind": "body", "start": 2, "end": 4}, "本文 2〜4 行目", id="body_range"),
        pytest.param(
            {"kind": "value", "key": "options[C].cons"}, "案 C のデメリット", id="option_value"
        ),
        pytest.param({"kind": "value", "key": "unknown_key"}, "unknown_key", id="unknown_key"),
    ],
)
def test_location_label(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    loc: dict[str, Any],
    expected: str,
) -> None:
    """箇所の名前（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    label = preview_page.evaluate("(loc) => MindmapPreview.locationLabel(loc)", loc)
    # 検証
    assert label == expected
