"""screens/settings.ts（表示の設定のパネルと、既定が変わった知らせ）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 表示する種類の全て
ALL_KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 上書きを持たない表示の設定の中身を作って文書に置き、× を押した結果を集めて返す JavaScript
DRAWER_SCRIPT = """(kinds) => {
    const calls = [];
    const panel = {
        look: "deep",
        defaultLook: "deep",
        kinds: new Set(kinds),
        defaultKinds: new Set(kinds),
        counts: {decisions: 1, tasks: 1, research: 1, docs: 1, terms: 1, notes: 1, logs: 1},
        overrides: [],
        canSave: true,
        message: null,
        storageOk: true,
        on: {
            look: () => {},
            kinds: () => {},
            reset: () => {},
            save: () => {},
            close: () => calls.push("close"),
        },
    };
    const drawer = MindmapPreview.settingsDrawer({panel});
    document.body.append(drawer);
    const nameOf = (element) =>
        element.getAttribute("aria-label") ?? element.title ?? element.textContent.trim();
    const closeButton = [...drawer.querySelectorAll("button")].find(
        (button) => nameOf(button) === "表示の設定を閉じる"
    );
    const headings = [...drawer.querySelectorAll("h1, h2, h3, [role='heading']")].map((heading) =>
        heading.textContent.trim()
    );
    const result = {hasClose: closeButton !== undefined, headings};
    if (closeButton !== undefined) closeButton.click();
    result.closeCalls = calls.length;
    return result;
}"""


def test_settings_drawer(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """見出しと閉じるボタンを持つ左のパネルに中身を入れる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(DRAWER_SCRIPT, ALL_KINDS)
    # 検証
    assert "表示の設定" in observed["headings"]
    assert observed["hasClose"] is True
    assert observed["closeCalls"] == 1
