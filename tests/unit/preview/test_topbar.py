"""components/topbar.ts（トップバー）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# トップバーを描いて body に置き、閉じるの呼び出しを window.calls に積む JavaScript
MOUNT_SCRIPT = """(duplicateIds) => {
    window.calls = [];
    const element = MindmapPreview.topbar({
        title: "話し合い",
        tabs: [{key: "overview", label: "概要", icon: "home"}],
        current: "overview",
        theme: "light",
        onNavigate: () => {},
        onSearch: () => {},
        onTheme: () => {},
        duplicateIds,
        onOpenDuplicate: (id) => window.calls.push(["open", id]),
        onCloseDuplicate: () => window.calls.push(["close"]),
    });
    document.body.append(element);
}"""


def test_topbar_when_duplicate_ids(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """重なった ID があればタブの帯の下に通知を出し、閉じるで知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(MOUNT_SCRIPT, [{"id": "D-12", "kind": "検討事項"}])
    # 実行
    preview_page.get_by_role("alert").get_by_role("button", name="閉じる").click()
    # 検証
    assert preview_page.get_by_role("alert").get_by_role("link", name="D-12").count() == 1
    assert preview_page.evaluate("() => window.calls") == [["close"]]
