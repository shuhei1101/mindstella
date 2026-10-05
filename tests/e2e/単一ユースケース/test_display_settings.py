"""表示の設定を変える（利用者がトップバーから表示の設定のパネルを開き、見た目と表示する種類を自分の端末だけで変え、既定に戻す）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。
見た目ごとの描き分けは確かめず、つながりの画面に渡った見た目の値だけを確かめる。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from display_settings_helpers import (
    DEFAULT_KINDS,
    RENDER_TIMEOUT_MS,
    SETTINGS_PANEL,
    SETTINGS_PANEL_OPEN,
    checked_kind_count,
    graph_look,
    open_in,
    open_settings,
    pick_look,
    read_prefs,
    seed_prefs,
    tab_keys,
    table_headers,
    toggle_kind,
)
from playwright.sync_api import BrowserContext, Page
from preview_helpers import COMMENTS_BUTTON, COMMENTS_PANEL, OpenPreview, ServeWorkspace
from workspace_fixtures import MakeItem

# タブの帯に並ぶ画面の数（概要・つながりと、表示する種類）
TABS_WITHOUT_TERMS = 8
TABS_WITHOUT_NOTES = 8

# 端末のライト / ダークを上書きするテーマ
OVERRIDE_THEME = "dark"

# 調査の表で隠しておく列の key と、その列の名前
HIDDEN_COLUMN_KEY = "conclusion"
HIDDEN_COLUMN_LABEL = "結論"

# 現在のタブの key を読む
CURRENT_TAB_SCRIPT = "document.querySelector('nav.tabbar a[aria-current=\"page\"]')?.dataset.tab"


def test_normal(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """見た目で glow を選び、表示する種類から用語集を外すと、その場で画面に当たり、端末に残って読み込み直しても保たれる（正常系）。"""
    # 準備
    url, root = serve_workspace(
        make_item("D-1"), make_item("T-1"), make_item("G-1"), settings=valid_settings
    )
    config_before = (root / "config.yaml").read_bytes()
    open_preview(url, "#tab=graph")
    # 実行
    open_settings(page)
    initial_look = graph_look(page)
    deep_checked = page.locator(f'{SETTINGS_PANEL} input[value="deep"]').is_checked()
    initial_kinds = checked_kind_count(page)
    pick_look(page, "グロウ")
    page.wait_for_selector(f'{SETTINGS_PANEL} input[value="glow"]:checked')
    toggle_kind(page, "用語集")
    page.wait_for_function(
        f"document.querySelectorAll('nav.tabbar a').length === {TABS_WITHOUT_TERMS}"
    )
    tabs_after_toggle = tab_keys(page)
    prefs = read_prefs(page)
    page.reload()
    page.wait_for_selector(".screen.graph", timeout=RENDER_TIMEOUT_MS)
    # 検証
    # パネルを開いた直後、見た目が deep で、全ての種類に印が付いている
    assert initial_look == "deep"
    assert deep_checked is True
    assert initial_kinds == len(DEFAULT_KINDS)
    # 用語集を外した直後と、読み込み直した後のどちらも、トップバーに用語集のタブが無く、概要とつながりのタブはある
    assert "terms" not in tabs_after_toggle
    assert tabs_after_toggle[0] == "overview"
    assert tabs_after_toggle[-1] == "graph"
    assert "terms" not in tab_keys(page)
    assert tab_keys(page)[0] == "overview"
    assert tab_keys(page)[-1] == "graph"
    # 読み込み直した後、つながりの画面に渡る見た目が glow である
    assert graph_look(page) == "glow"
    # 端末の保存領域に、見た目 glow と、用語集を除いた表示する種類が残っている
    assert prefs is not None
    assert prefs["look"] == "glow"
    assert prefs["kinds"] == [kind for kind in DEFAULT_KINDS if kind != "terms"]
    assert read_prefs(page) == prefs
    # config.yaml の中身が、開く前と同じである
    assert (root / "config.yaml").read_bytes() == config_before


def test_normal_when_reset(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    new_context: Callable[..., BrowserContext],
) -> None:
    """既定に戻すと、見た目・表示する種類・ライト / ダーク・表の列の上書きが外れ、ワークスペースの既定の表示に戻る（正常系）。"""
    # 準備
    url, root = serve_workspace(
        make_item("R-1"),
        make_item("N-1"),
        settings={
            **valid_settings,
            "display": {
                "network_look": "starlight",
                "visible_kinds": [kind for kind in DEFAULT_KINDS if kind != "notes"],
            },
        },
    )
    config_before = (root / "config.yaml").read_bytes()
    # ブラウザのライト / ダークはライトにしておく
    context = new_context(color_scheme="light")
    page = context.new_page()
    open_in(page, url, "#tab=research")
    # 端末の保存領域に、見た目 dust・全ての種類・ダーク・調査の表で隠した列 1 つを残しておく
    seed_prefs(
        page,
        {
            "theme": OVERRIDE_THEME,
            "columns": {"research": {"hidden": [HIDDEN_COLUMN_KEY], "pinTo": None}},
            "look": "dust",
            "kinds": DEFAULT_KINDS,
            "diffSel": None,
        },
    )
    page.reload()
    page.wait_for_selector("table.grid", timeout=RENDER_TIMEOUT_MS)
    headers_before = table_headers(page)
    theme_before = page.evaluate("document.documentElement.dataset.theme")
    # 実行
    open_settings(page)
    dust_checked = page.locator(f'{SETTINGS_PANEL} input[value="dust"]').is_checked()
    kinds_before = checked_kind_count(page)
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_function(
        f"document.querySelectorAll('nav.tabbar a').length === {TABS_WITHOUT_NOTES}"
    )
    tabs_after_reset = tab_keys(page)
    theme_after = page.evaluate("document.documentElement.dataset.theme")
    prefs_after = read_prefs(page)
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector(".screen.graph", timeout=RENDER_TIMEOUT_MS)
    look_after = graph_look(page)
    page.click('nav.tabbar a[data-tab="research"]')
    page.wait_for_selector("table.grid", timeout=RENDER_TIMEOUT_MS)
    headers_after = table_headers(page)
    # 検証
    # 上書きが効いている状態から始まる（見た目 dust・全ての種類に印・ダーク・隠した列）
    assert dust_checked is True
    assert kinds_before == len(DEFAULT_KINDS)
    assert theme_before == OVERRIDE_THEME
    assert HIDDEN_COLUMN_LABEL not in headers_before
    # つながりの画面に渡る見た目が starlight である
    assert look_after == "starlight"
    # トップバーにメモのタブが無い
    assert "notes" not in tabs_after_reset
    # 画面がブラウザのライト / ダークに従ってライトになる
    assert theme_after == "light"
    # 調査の表が既定の列で並ぶ
    assert HIDDEN_COLUMN_LABEL in headers_after
    # 端末の保存領域に、見た目・表示する種類・ライト / ダーク・表の列の上書きが無い
    assert prefs_after is not None
    assert prefs_after["look"] is None
    assert prefs_after["kinds"] is None
    assert prefs_after["theme"] is None
    assert prefs_after["columns"] == {}
    # config.yaml の中身が、操作の前と同じである
    assert (root / "config.yaml").read_bytes() == config_before


def test_normal_when_current_kind_hidden(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """開いている画面の種類を表示しない種類にすると、概要へ移り、ブラウザの戻るでその画面へは戻らない（正常系）。"""
    # 準備
    url, _ = serve_workspace(make_item("D-1"), make_item("T-1"), settings=valid_settings)
    open_preview(url, "#tab=overview")
    # 概要からタスクのタブへ移る
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_function(f"{CURRENT_TAB_SCRIPT} === 'tasks'")
    # 実行
    open_settings(page)
    toggle_kind(page, "タスク")
    page.wait_for_selector(".overview")
    tab_after_hide = page.evaluate(CURRENT_TAB_SCRIPT)
    hash_after_hide = page.evaluate("location.hash")
    tabs_after_hide = tab_keys(page)
    page.go_back()
    page.wait_for_selector("main#main > *", state="attached", timeout=RENDER_TIMEOUT_MS)
    tab_after_back = page.evaluate(CURRENT_TAB_SCRIPT)
    # 検証
    # タスクを外した直後、画面が概要で、URL のハッシュが概要を指す
    assert tab_after_hide == "overview"
    assert "tab=" not in hash_after_hide
    # トップバーにタスクのタブが無い
    assert "tasks" not in tabs_after_hide
    # ブラウザの戻るで、タスクの画面が開かない
    assert tab_after_back == "overview"
    assert "tasks" not in tab_keys(page)


def test_normal_when_switched_with_comments(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """表示の設定とコメントの一覧は入れ替えて開き、どちらの間も右の詳細パネルは開いたままである（正常系）。"""
    # 準備
    url, _ = serve_workspace(make_item("D-1"), settings=valid_settings)
    open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel.open")
    # トップバーからコメントの一覧を左に開く
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    # 実行（表示の設定を押す）
    page.click("header.topbar button.settings-btn", force=True)
    page.wait_for_selector(SETTINGS_PANEL_OPEN)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open", state="detached")
    after_settings = {
        "settings": page.locator(SETTINGS_PANEL_OPEN).count(),
        "comments": page.locator(f"{COMMENTS_PANEL}.open").count(),
        "detail": page.locator("aside.panel.open").count(),
    }
    # 実行（コメントを押す）
    page.click(COMMENTS_BUTTON, force=True)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    after_comments = {
        "settings": page.locator(SETTINGS_PANEL_OPEN).count(),
        "comments": page.locator(f"{COMMENTS_PANEL}.open").count(),
        "detail": page.locator("aside.panel.open").count(),
    }
    # 検証
    # 表示の設定を押した後、コメントの一覧が閉じ、表示の設定のパネルが開いている
    assert after_settings["settings"] == 1
    assert after_settings["comments"] == 0
    # コメントを押した後、表示の設定のパネルが閉じ、コメントの一覧が開いている
    assert after_comments["settings"] == 0
    assert after_comments["comments"] == 1
    # どちらの間も、右の D-1 の詳細パネルが開いたままである
    assert after_settings["detail"] == 1
    assert after_comments["detail"] == 1
