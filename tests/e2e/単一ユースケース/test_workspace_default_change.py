"""ワークスペースの既定を変える（利用者が今の選びを config.yaml の既定として保存し、上書きを持たない他の画面に効かせる）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、サーバーが配るプレビューを、端末の保存領域を共有しない 2 つのブラウザのコンテキスト（A と B）で開く。
見た目ごとの描き分けは確かめず、ネットワークの画面に渡った見た目の値だけを確かめる。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from display_settings_helpers import (
    CONFIRM,
    CONFIRM_OPEN,
    DEFAULT_KINDS,
    ERROR_ALERT,
    KINDS_WITHOUT_TERMS,
    RENDER_TIMEOUT_MS,
    SAVE_DEFAULT_BUTTON,
    SETTINGS_PANEL,
    graph_look,
    open_in,
    open_settings,
    read_config,
    read_prefs,
    seed_prefs,
    tab_keys,
)
from playwright.sync_api import BrowserContext, Page
from preview_helpers import ServeWorkspace
from workspace_fixtures import RECORD_DIR, MakeItem

if TYPE_CHECKING:
    from conftest import LockDirs

# タブの帯に並ぶ画面の数（概要・ネットワークと、用語集を除いた 6 種類）
TABS_WITHOUT_TERMS = 8

# 保存の結果を待つ上限ミリ秒
SAVE_TIMEOUT_MS = 10_000


def _open_with_override(page: Page, url: str, prefs: dict[str, Any]) -> Page:
    """ネットワークの画面を開き、端末の保存領域に個人の上書きを置いて読み込み直す。"""
    open_in(page, url, "#tab=graph")
    seed_prefs(page, prefs)
    page.reload()
    page.wait_for_selector(".screen.graph", timeout=RENDER_TIMEOUT_MS)
    return page


def test_normal(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    new_context: Callable[..., BrowserContext],
) -> None:
    """A が今の選びをワークスペースの既定として保存すると、config.yaml が書き換わり、上書きを持たない B の画面に開き直さずに効く（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("D-1"), make_item("G-1"), settings=valid_settings)
    config_before = read_config(root)
    page_a = new_context().new_page()
    page_b = new_context().new_page()
    # B は端末の保存領域が空のまま開く
    open_in(page_b, url, "#tab=graph")
    initial_look_b = graph_look(page_b)
    initial_tabs_b = tab_keys(page_b)
    # A の端末の保存領域に、見た目 glow と、用語集を除いた表示する種類を残しておく
    prefs_a = {
        "theme": None,
        "columns": {},
        "look": "glow",
        "kinds": KINDS_WITHOUT_TERMS,
        "diffSel": None,
    }
    _open_with_override(page_a, url, prefs_a)
    open_settings(page_a)
    saved_prefs_a = read_prefs(page_a)
    # 実行
    page_a.click(SAVE_DEFAULT_BUTTON)
    page_a.wait_for_selector(CONFIRM_OPEN)
    rows = page_a.locator(f"{CONFIRM} .sc-row").all_inner_texts()
    page_a.get_by_role("button", name="保存する").click()
    page_a.wait_for_selector(CONFIRM, state="detached", timeout=SAVE_TIMEOUT_MS)
    page_b.wait_for_function(
        f"document.querySelectorAll('nav.tabbar a').length === {TABS_WITHOUT_TERMS}",
        timeout=SAVE_TIMEOUT_MS,
    )
    page_b.wait_for_function(
        "document.querySelector('.screen.graph')?.dataset.look === 'glow'",
        timeout=SAVE_TIMEOUT_MS,
    )
    # 検証
    # 確かめのモーダルに、保存する見た目 glow と、用語集を除いた表示する種類が出る
    assert len(rows) == 2
    assert "グロウ" in rows[0]
    assert "用語集を表示しない" in rows[1]
    # config.yaml の見た目の既定が glow で、表示する種類の既定が用語集を除いた種類である
    config = read_config(root)
    assert config["display"]["network_look"] == "glow"
    assert config["display"]["visible_kinds"] == KINDS_WITHOUT_TERMS
    # config.yaml のそのほかのキーが、操作の前と同じである
    assert {key: value for key, value in config.items() if key != "display"} == config_before
    # B の画面が、開き直さずに用語集のタブを外し、ネットワークに渡る見た目が glow になる
    assert initial_look_b == "deep"
    assert "terms" in initial_tabs_b
    assert "terms" not in tab_keys(page_b)
    assert graph_look(page_b) == "glow"
    # A の端末の保存領域の上書きが残っている
    assert read_prefs(page_a) == saved_prefs_a
    assert saved_prefs_a is not None
    assert saved_prefs_a["look"] == "glow"
    assert saved_prefs_a["kinds"] == KINDS_WITHOUT_TERMS


def test_normal_when_cancelled(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """確かめのモーダルで取り消すと、何も書かずに閉じ、表示の設定のパネルに戻る（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("D-1"), settings=valid_settings)
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    _open_with_override(
        page,
        url,
        {"theme": None, "columns": {}, "look": "dust", "kinds": None, "diffSel": None},
    )
    sent: list[str] = []
    page.on(
        "request", lambda request: sent.append(request.url) if request.method == "PUT" else None
    )
    open_settings(page)
    # 実行
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    page.get_by_role("button", name="取り消す").click()
    page.wait_for_selector(CONFIRM, state="detached")
    # 検証
    # モーダルが閉じ、表示の設定のパネルが開いたままである
    assert page.locator(CONFIRM).count() == 0
    assert page.locator(f"{SETTINGS_PANEL}.open").count() == 1
    # 既定の書き換えの要求がサーバーへ出ていない
    assert sent == []
    # config.yaml の中身が、操作の前と同じである
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before


def test_error_when_save_fails(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    new_context: Callable[..., BrowserContext],
    lock_dirs: LockDirs,
) -> None:
    """ワークスペースに書けないと、確かめのモーダルの中に理由を出し、config.yaml も他の画面の表示も変えない（異常系）。"""
    # 準備
    url, root = serve_workspace(make_item("D-1"), make_item("G-1"), settings=valid_settings)
    page_a = new_context().new_page()
    page_b = new_context().new_page()
    open_in(page_b, url, "#tab=graph")
    # A の端末の保存領域に見た目 glow を残しておく
    _open_with_override(
        page_a,
        url,
        {"theme": None, "columns": {}, "look": "glow", "kinds": None, "diffSel": None},
    )
    open_settings(page_a)
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    look_b_before = graph_look(page_b)
    tabs_b_before = tab_keys(page_b)
    # 画面を開いた後に、記録のフォルダを読み取り専用にする
    lock_dirs(root / RECORD_DIR)
    # 実行
    page_a.click(SAVE_DEFAULT_BUTTON)
    page_a.wait_for_selector(CONFIRM_OPEN)
    page_a.get_by_role("button", name="保存する").click()
    page_a.wait_for_selector(ERROR_ALERT, timeout=SAVE_TIMEOUT_MS)
    page_b.wait_for_timeout(1_000)
    # 検証
    # 確かめのモーダルの中に、保存できなかった理由が出る
    assert page_a.locator(CONFIRM_OPEN).count() == 1
    alert = page_a.inner_text(ERROR_ALERT)
    assert alert.startswith("保存できませんでした。")
    assert str(root) in alert
    # config.yaml の中身が、操作の前と同じである
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before
    # B の画面の見た目とタブが、操作の前と同じである
    assert graph_look(page_b) == look_b_before == "deep"
    assert tab_keys(page_b) == tabs_b_before
    assert tab_keys(page_b) == ["overview", *DEFAULT_KINDS, "graph"]
    # A の画面の見た目が glow のままである
    assert graph_look(page_a) == "glow"
