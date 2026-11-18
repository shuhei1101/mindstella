"""screens/overview.ts（概要）の単体テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem
from .thread_data import make_post, make_thread

# 表示する種類の全て
ALL_KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 検討事項・資料を除いた、表示する種類
KINDS_WITHOUT_DECISIONS_DOCS = ["tasks", "research", "terms", "notes", "logs"]


@pytest.mark.parametrize(
    ("visible_kinds", "expects_links"),
    [
        pytest.param(ALL_KINDS, True, id="all_kinds"),
        pytest.param(KINDS_WITHOUT_DECISIONS_DOCS, False, id="kinds_hidden"),
    ],
)
def test_overview_screen_when_kinds_hidden(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    visible_kinds: list[str],
    expects_links: bool,
) -> None:
    """表示しない種類へのリンクだけを外し、タイルは残す（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", status="要見直し"), make_item("D-2", status="未決定")],
        docs=[make_item("A-1", status="確認中")],
    )
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        """({data, kinds}) => {
            const screen = MindmapPreview.overviewScreen({
                index: MindmapPreview.buildIndex(data),
                threads: [],
                visibleKinds: new Set(kinds),
                on: {open: () => {}, navigate: () => {}, openThread: () => {}},
            });
            document.body.append(screen);
            const tile = (id) => screen.querySelector(`#${id}`);
            const rows = (id) => [...tile(id).querySelectorAll("button[data-id]")].map((row) => row.dataset.id);
            const showAll = (id) => [...tile(id).querySelectorAll("button")].some((button) =>
                button.textContent.trim().startsWith("すべて表示")
            );
            return {
                tiles: ["tile-unread", "tile-open", "tile-review", "tile-docs"].map((id) => tile(id) !== null),
                rows: {open: rows("tile-open"), review: rows("tile-review"), docs: rows("tile-docs")},
                showAll: {open: showAll("tile-open"), review: showAll("tile-review"), docs: showAll("tile-docs")},
            };
        }""",
        {"data": data, "kinds": visible_kinds},
    )
    # 検証
    assert observed["tiles"] == [True, True, True, True]
    assert observed["rows"] == {"open": ["D-2"], "review": ["D-1"], "docs": ["A-1"]}
    assert observed["showAll"] == {
        "open": expects_links,
        "review": expects_links,
        "docs": expects_links,
    }


def test_overview_screen_when_unread(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, make_data: MakeData
) -> None:
    """未読の書き込みを持つオープンのスレッドだけを新しい順に並べる（正常系）。"""
    # 準備
    threads = [
        make_thread("TH-1", posts=[make_post("ai", "一", "2026-10-01T00:00:00+00:00", seen=False)]),
        make_thread("TH-2", posts=[make_post("ai", "二", "2026-10-02T00:00:00+00:00", seen=False)]),
        make_thread("TH-3", posts=[make_post("ai", "三", "2026-10-03T00:00:00+00:00", seen=True)]),
        make_thread(
            "TH-4",
            status="closed",
            posts=[make_post("ai", "四", "2026-10-04T00:00:00+00:00", seen=False)],
        ),
    ]
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        """({data, threads, kinds}) => {
            const opened = [];
            const screen = MindmapPreview.overviewScreen({
                index: MindmapPreview.buildIndex(data),
                threads,
                visibleKinds: new Set(kinds),
                on: {open: () => {}, navigate: () => {}, openThread: (id) => opened.push(id)},
            });
            document.body.append(screen);
            const tile = screen.querySelector("#tile-unread");
            const rows = [...tile.querySelectorAll("button[data-id]")];
            tile.querySelector('button[data-id="TH-1"]').click();
            return {
                rows: rows.map((row) => row.dataset.id),
                count: tile.querySelector(".num")?.textContent.trim() ?? null,
                opened,
            };
        }""",
        {"data": make_data(), "threads": threads, "kinds": ALL_KINDS},
    )
    # 検証
    assert observed == {"rows": ["TH-2", "TH-1"], "count": "2", "opened": ["TH-1"]}
