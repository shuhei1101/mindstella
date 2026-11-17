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


# 保留と音声入力の知らせを渡してトップバーを描き、body に置く JavaScript
STALE_SCRIPT = """(voiceNotice) => {
    const element = MindmapPreview.topbar({
        title: "話し合い",
        tabs: [{key: "overview", label: "概要", icon: "home"}],
        current: "overview",
        theme: "light",
        onNavigate: () => {},
        onSearch: () => {},
        onTheme: () => {},
        stale: true,
        voiceNotice,
        onVoice: () => {},
    });
    document.body.replaceChildren(element);
}"""

# 「更新があります」の帯の文言
STALE_TEXT = "更新があります。入力欄から離れると反映します。"


def test_topbar_when_stale(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """保留中は「更新があります」の帯を出す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    preview_page.evaluate(STALE_SCRIPT, None)
    band = preview_page.get_by_role("status").filter(has_text=STALE_TEXT)
    alone = {"count": band.count(), "buttons": band.get_by_role("button").count()}
    preview_page.evaluate(
        STALE_SCRIPT, {"kind": "discarded", "text": "D-022 が削除されたため、録音を破棄しました。"}
    )
    order = preview_page.evaluate(
        """(staleText) => {
            const texts = [...document.querySelectorAll('[role="status"]')].map((el) => el.textContent);
            return [
                texts.findIndex((text) => text.includes("録音を破棄しました")),
                texts.findIndex((text) => text.includes(staleText)),
            ];
        }""",
        STALE_TEXT,
    )
    # 検証
    assert alone == {"count": 1, "buttons": 0}
    assert order == [0, 1]
