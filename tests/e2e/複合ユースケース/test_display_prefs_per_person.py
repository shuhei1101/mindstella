"""表示の好みを人ごとに分ける（同じワークスペースのプレビューを開いた 2 人が、それぞれの端末で表示の設定を変えても互いの表示に影響せず、既定の保存だけが上書きを持たない項目に効く）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、サーバーが配るプレビューを、端末の保存領域を共有しない 2 つのブラウザのコンテキスト（利用者 A と利用者 B）で開く。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from display_settings_helpers import (
    CONFIRM,
    CONFIRM_OPEN,
    DEFAULT_KINDS,
    KINDS_WITHOUT_TERMS,
    SAVE_DEFAULT_BUTTON,
    SETTINGS_PANEL,
    graph_look,
    open_in,
    open_settings,
    pick_look,
    read_config,
    read_prefs,
    tab_keys,
    toggle_kind,
)
from playwright.sync_api import BrowserContext
from preview_helpers import ServeWorkspace
from workspace_fixtures import MakeItem

# タブの帯に並ぶ画面の数（概要・つながりと、用語集を除いた 6 種類）
TABS_WITHOUT_TERMS = 8

# 保存の結果と、他の人の画面への反映を待つ上限ミリ秒
SAVE_TIMEOUT_MS = 10_000

# 項目を持つ種類の YAML（記録の項目は表示の設定を変えても書き換えない）
RECORD_FILES = ("decisions.yaml", "tasks.yaml", "terms.yaml")


def test_normal(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    new_context: Callable[..., BrowserContext],
) -> None:
    """A が見た目と表示する種類を変えても B の表示は変わらず、A が既定を保存したときだけ、B の上書きを持たない項目が変わる（正常系）。"""
    # 準備
    url, root = serve_workspace(
        make_item("D-1"), make_item("T-1"), make_item("G-1"), settings=valid_settings
    )
    records_before = {name: (root / name).read_bytes() for name in RECORD_FILES}
    page_a = new_context().new_page()
    page_b = new_context().new_page()
    # 実行
    # 利用者 A がプレビューの URL を開き、表示の設定で見た目を glow にし、表示する種類から用語集を外す
    open_in(page_a, url, "#tab=graph")
    open_settings(page_a)
    pick_look(page_a, "グロウ")
    page_a.wait_for_selector(f'{SETTINGS_PANEL} input[value="glow"]:checked')
    toggle_kind(page_a, "用語集")
    page_a.wait_for_function(
        f"document.querySelectorAll('nav.tabbar a').length === {TABS_WITHOUT_TERMS}"
    )
    # 利用者 B が同じ URL を開く
    open_in(page_b, url, "#tab=graph")
    look_b_opened = graph_look(page_b)
    tabs_b_opened = tab_keys(page_b)
    # B が表示の設定で見た目を dust にする
    open_settings(page_b)
    pick_look(page_b, "星屑")
    page_b.wait_for_selector(f'{SETTINGS_PANEL} input[value="dust"]:checked')
    # A がワークスペースの既定にする操作で、今の選びを保存する
    page_a.click(SAVE_DEFAULT_BUTTON)
    page_a.wait_for_selector(CONFIRM_OPEN)
    page_a.get_by_role("button", name="保存する").click()
    page_a.wait_for_selector(CONFIRM, state="detached", timeout=SAVE_TIMEOUT_MS)
    page_b.wait_for_function(
        f"document.querySelectorAll('nav.tabbar a').length === {TABS_WITHOUT_TERMS}",
        timeout=SAVE_TIMEOUT_MS,
    )
    # 検証
    # B が開いた直後の画面は、見た目が deep で、トップバーに用語集のタブがある（A の上書きが効いていない）
    assert look_b_opened == "deep"
    assert tabs_b_opened == ["overview", *DEFAULT_KINDS, "graph"]
    # 既定を保存した後の config.yaml の見た目の既定が glow、表示する種類の既定が用語集を除いた種類である
    config = read_config(root)
    assert config["display"]["network_look"] == "glow"
    assert config["display"]["visible_kinds"] == KINDS_WITHOUT_TERMS
    # 既定を保存した後、B の画面は開き直さずに用語集のタブが外れ、見た目は B が上書きした dust のままである
    assert "terms" not in tab_keys(page_b)
    assert graph_look(page_b) == "dust"
    # A の画面は見た目が glow で、用語集のタブが無い
    assert graph_look(page_a) == "glow"
    assert "terms" not in tab_keys(page_a)
    # A の端末の保存領域に A の上書きが、B の端末の保存領域に B の上書き（見た目だけ）が残っている
    prefs_a = read_prefs(page_a)
    prefs_b = read_prefs(page_b)
    assert prefs_a is not None
    assert prefs_a["look"] == "glow"
    assert prefs_a["kinds"] == KINDS_WITHOUT_TERMS
    assert prefs_b is not None
    assert prefs_b["look"] == "dust"
    assert prefs_b["kinds"] is None
    # ワークスペースの記録の項目の YAML の中身が、開く前と同じ
    assert {name: (root / name).read_bytes() for name in RECORD_FILES} == records_before
