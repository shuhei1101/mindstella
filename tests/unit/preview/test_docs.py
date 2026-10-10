"""screens/docs.ts（資料の画面）の単体テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem


def test_order_docs(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, make_item: MakeItem
) -> None:
    """納品物が先（正常系）。"""
    # 準備
    docs = [
        make_item("A-1", deliverable=False),
        make_item("A-3", deliverable=True),
        make_item("A-2", deliverable=True),
    ]
    load_preview_scripts()
    # 実行
    ids = preview_page.evaluate(
        "(docs) => MindmapPreview.orderDocs(docs).map((doc) => doc.id)", docs
    )
    # 検証
    assert ids == ["A-2", "A-3", "A-1"]


@pytest.mark.parametrize(
    "view", [pytest.param("cards", id="cards"), pytest.param("board", id="board")]
)
def test_docs_screen_when_withdrawn(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    view: str,
) -> None:
    """取り下げた資料のカードに、差分の表示によらず札を置く（正常系）。"""
    # 準備
    data = make_data(docs=[make_item("A-1"), make_item("A-9", withdrawn=True)])
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """({data, view}) => {
            const index = MindmapPreview.buildIndex(data);
            const noop = () => {};
            const screen = MindmapPreview.docsScreen({
                index,
                route: {tab: "docs", view, id: null, full: false, filters: {}, heading: null},
                on: {open: noop, view: noop, filter: noop, closeDrawer: noop},
                filters: {},
                drawerOpen: false,
            });
            document.body.append(screen);
            const summarize = (id) => {
                const card = screen.querySelector(`.doc-card[data-id="${id}"]`);
                return {
                    badgeAfterTitle:
                        card.querySelector(".c-ttl").nextElementSibling?.classList.contains("wd-badge") === true,
                    badgeText: card.querySelector(".wd-badge")?.textContent ?? null,
                    dimmed: card.classList.contains("is-withdrawn"),
                };
            };
            return {withdrawn: summarize("A-9"), kept: summarize("A-1")};
        }""",
        {"data": data, "view": view},
    )
    # 検証
    assert result["withdrawn"]["badgeAfterTitle"] is True
    assert "取り下げ" in result["withdrawn"]["badgeText"]
    assert result["withdrawn"]["dimmed"] is True
    assert result["kept"] == {
        "badgeAfterTitle": False,
        "badgeText": None,
        "dimmed": False,
    }
