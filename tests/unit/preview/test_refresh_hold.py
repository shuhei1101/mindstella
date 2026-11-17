"""core/refresh-hold.ts（描き直しの保留）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# スクロールする枠の中に帯の場所・入力欄・ボタンを置き、保留を作って、呼び出しを window.calls に積む
# JavaScript。保留が変わると帯の場所の高さを 30px と 0 で切り替える
HOLD_SCRIPT = """(voiceActive) => {
    document.body.innerHTML =
        '<div id="band" style="height: 0"></div>' +
        '<div id="scroller" style="height: 200px; overflow-y: auto">' +
        '<div style="height: 400px"></div><textarea id="entry"></textarea>' +
        '<button id="other">外</button><div style="height: 400px"></div></div>';
    document.getElementById("scroller").scrollTop = 300;
    window.calls = [];
    window.voiceActive = voiceActive;
    window.hold = MindmapPreview.createRefreshHold({
        doc: document,
        isVoiceActive: () => window.voiceActive,
        reload: () => window.calls.push(["reload"]),
        onStaleChange: (stale) => {
            window.calls.push(["stale", stale]);
            document.getElementById("band").style.height = stale ? "30px" : "0";
        },
    });
}"""

# 入力欄の画面の上の位置を返す JavaScript
ENTRY_TOP = "() => document.getElementById('entry').getBoundingClientRect().top"


def test_is_text_entry(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """文字を入力する欄を見分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    results = preview_page.evaluate(
        """() => {
            document.body.innerHTML =
                '<textarea></textarea><input type="text"><div contenteditable="true"></div>' +
                '<input type="checkbox"><button>押す</button>';
            const elements = [...document.body.children, null];
            return elements.map((element) => MindmapPreview.isTextEntry(element));
        }"""
    )
    # 検証
    assert results == [True, True, True, False, False, False]


def test_create_refresh_hold(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """入力中でなければすぐ描き直す（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(HOLD_SCRIPT, False)
    preview_page.evaluate("() => document.getElementById('other').focus()")
    # 実行
    preview_page.evaluate("() => window.hold.request()")
    # 検証
    assert preview_page.evaluate("() => window.calls") == [["reload"]]


def test_create_refresh_hold_when_typing(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """入力中は保留し、離れたら 1 回だけ描き直す（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(HOLD_SCRIPT, False)
    preview_page.evaluate("() => document.getElementById('entry').focus()")
    before = preview_page.evaluate(ENTRY_TOP)
    # 実行
    preview_page.evaluate("() => { window.hold.request(); window.hold.request(); }")
    while_typing = preview_page.evaluate("() => [...window.calls]")
    held_top = preview_page.evaluate(ENTRY_TOP)
    preview_page.evaluate("() => document.getElementById('other').focus()")
    released_top = preview_page.evaluate(ENTRY_TOP)
    # 検証
    assert while_typing == [["stale", True]]
    assert held_top == before
    assert released_top == before
    assert preview_page.evaluate("() => window.calls") == [
        ["stale", True],
        ["stale", False],
        ["reload"],
    ]
    assert preview_page.evaluate("() => window.hold.stale()") is False


def test_create_refresh_hold_when_voice(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """音声入力中は保留し、終わったら描き直す（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(HOLD_SCRIPT, True)
    # 実行
    preview_page.evaluate("() => window.hold.request()")
    while_voice = preview_page.evaluate("() => [...window.calls]")
    preview_page.evaluate("() => { window.voiceActive = false; window.hold.release(); }")
    # 検証
    assert while_voice == [["stale", True]]
    assert preview_page.evaluate("() => window.calls") == [
        ["stale", True],
        ["stale", False],
        ["reload"],
    ]
