"""components/history-dialog.ts（変更履歴のモーダル）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# モーダルを描いて開く JavaScript
MOUNT_SCRIPT = """(points) => {
    const dialog = MindmapPreview.historyDialog({points, current: "", onPick: () => {}, onClose: () => {}});
    document.body.append(dialog);
    dialog.showModal();
}"""


def test_history_dialog_when_external(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """外部の変更のまとまりの行だけに札を付ける（正常系）。"""
    # 準備
    load_preview_scripts()
    points = [
        {"sel": "V-2", "name": "答えを直した", "sub": "11/02 09:00", "count": 1},
        {
            "sel": "V-1",
            "name": "ほかのセッションの書き込み",
            "sub": "11/01 09:00",
            "count": 1,
            "external": True,
        },
    ]
    # 実行
    preview_page.evaluate(MOUNT_SCRIPT, points)
    # 検証
    rows = preview_page.locator(".hist-item")
    assert rows.nth(0).locator(".hist-tag").count() == 0
    assert rows.nth(1).locator(".hist-tag").inner_text() == "外部の変更"
    assert preview_page.get_by_role(
        "button", name="ほかのセッションの書き込み 外部の変更"
    ).count() == 1
