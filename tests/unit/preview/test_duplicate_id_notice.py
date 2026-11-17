"""components/duplicate-id-notice.ts（重なった ID の通知）の単体テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 通知を描いて body に置き、呼ばれた操作を window.calls に積む JavaScript（何も描かなければ置かない）
MOUNT_SCRIPT = """(ids) => {
    window.calls = [];
    const element = MindmapPreview.duplicateIdNotice({
        ids,
        onOpen: (id) => window.calls.push(["open", id]),
        onClose: () => window.calls.push(["close"]),
    });
    if (element) document.body.append(element);
}"""


def _mount(page: Page, ids: list[dict[str, Any]]) -> None:
    """渡した ID で通知を描く。"""
    page.evaluate(MOUNT_SCRIPT, ids)


def test_duplicate_id_notice(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """重なった ID を並べ、リンクと閉じるで知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    _mount(preview_page, [{"id": "D-12", "kind": "検討事項"}, {"id": "T-3", "kind": "タスク"}])
    alert = preview_page.get_by_role("alert")
    # 実行
    alert.get_by_role("link", name="D-12").click()
    alert.get_by_role("button", name="閉じる").click()
    # 検証
    assert "同じ ID の項目が 2 件あります" in alert.inner_text()
    assert alert.get_by_role("link", name="T-3").count() == 1
    assert preview_page.evaluate("() => window.calls") == [["open", "D-12"], ["close"]]


def test_duplicate_id_notice_when_empty(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """空なら描かない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    _mount(preview_page, [])
    # 検証
    assert preview_page.get_by_role("alert").count() == 0
