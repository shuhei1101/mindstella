"""画面設計『表示の設定』（左から出すパネル。見た目・表示する種類・既定に戻す・既定が変わった知らせ）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page
from preview_comment_helpers import COMMENTS_BUTTON, COMMENTS_PANEL
from preview_drawer_helpers import DRAWER_OPEN, FILTER_BUTTON, open_drawer
from preview_fixture_types import OpenPreview, WriteReviewPreview
from preview_settings_helpers import (
    DEFAULT_KINDS,
    SETTINGS_BUTTON,
    SETTINGS_PANEL,
    SETTINGS_PANEL_OPEN,
    open_settings,
    panel_text,
    read_config,
    read_prefs,
    tab_keys,
    toggle_kind,
)
from workspace_fixtures import RECORD_DIR, MakeItem


# 画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 15_000

# ワークスペースの既定が持つ表示する種類（用語集・会話ログを外す）
KINDS_WITHOUT_TERMS_LOGS = ["decisions", "tasks", "research", "docs", "notes"]

# 開いた画面の幅（詳細パネルを別画面として積む幅）
PHONE_VIEWPORT = {"width": 390, "height": 844}

# 覆われた本文の部品に付けた `inert` の数
INERT_COUNT_SCRIPT = "document.querySelectorAll('main [inert]').length"

# 既定が変わった知らせが画面の下に出てから消えるまでの余裕の上限ミリ秒（画面は 6 秒出す）
NOTICE_GONE_MS = 9_000


def _preview(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    **display: Any,
) -> tuple[str, Path]:
    """検討事項・タスク・メモを持つワークスペースを配る。display を渡すと、ワークスペースの既定にする。"""
    settings = {**valid_settings, "display": display} if display else valid_settings
    return write_review_preview(
        make_item("D-1"), make_item("T-1"), make_item("N-1"), settings=settings
    )


def test_open_and_close(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """トップバーのボタンで開き、見出しと既定のままの旨を出す。履歴に積まず、Esc・×・ボタンで閉じてボタンへフォーカスを戻す（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=decisions&view=table")
    history_length = page.evaluate("history.length")
    # 実行（ボタンで開く）
    open_settings(page)
    opened = {
        "heading": page.inner_text(f"{SETTINGS_PANEL} h2"),
        "expanded": page.get_attribute(SETTINGS_BUTTON, "aria-expanded"),
        "history": page.evaluate("history.length"),
        "text": panel_text(page),
        "buttons": page.locator(f"{SETTINGS_PANEL} .st-wrap button").all_inner_texts(),
    }
    # 実行（Esc で閉じる）
    page.keyboard.press("Escape")
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    focus_after_esc = page.evaluate("document.activeElement?.dataset.act ?? null")
    # 実行（もう一度開き、× で閉じる）
    open_settings(page)
    page.get_by_role("button", name="表示の設定を閉じる").click()
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    focus_after_close = page.evaluate("document.activeElement?.dataset.act ?? null")
    # 実行（もう一度開き、ボタンで閉じる）
    open_settings(page)
    page.click(SETTINGS_BUTTON)
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    # 検証
    assert opened["heading"] == "表示の設定"
    assert opened["expanded"] == "true"
    assert opened["history"] == history_length
    assert "ワークスペースの既定のまま表示しています。" in opened["text"]
    assert "今の選びはワークスペースの既定と同じです。" in opened["text"]
    assert opened["buttons"] == []
    assert focus_after_esc == "settings"
    assert focus_after_close == "settings"
    assert page.get_attribute(SETTINGS_BUTTON, "aria-expanded") == "false"


def test_look_override(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """見た目を選ぶと、その場でつながりに当たり、個人の上書きとして端末に残る。config.yaml は書き換えない（正常系）。"""
    # 準備
    url, root = _preview(write_review_preview, make_item, valid_settings)
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    page = open_preview(url, "#tab=graph")
    initial_look = page.get_attribute(".screen.graph", "data-look")
    open_settings(page)
    # 実行
    page.locator(f"{SETTINGS_PANEL} .st-look", has_text="星屑").locator("input").click()
    page.wait_for_selector(f'{SETTINGS_PANEL} input[value="dust"]:checked')
    # 検証
    assert initial_look == "deep"
    assert page.get_attribute(".screen.graph", "data-look") == "dust"
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["look"] == "dust"
    assert "この端末で変えている項目" in panel_text(page)
    assert "つながりの見た目" in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before
    # 開き直しても、個人の上書きを使う
    page.reload()
    page.wait_for_selector(".screen.graph", timeout=RENDER_TIMEOUT_MS)
    assert page.get_attribute(".screen.graph", "data-look") == "dust"


def test_kinds_override(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """表示する種類を外すと、その種類のタブをトップバーから外す。概要とつながりは常に出す（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url)
    open_settings(page)
    all_kinds_text = panel_text(page)
    # 実行
    toggle_kind(page, "用語集")
    toggle_kind(page, "会話ログ")
    page.wait_for_function("document.querySelectorAll('nav.tabbar a').length === 7")
    # 検証
    assert "常に表示" in all_kinds_text
    assert tab_keys(page) == [
        "overview",
        "decisions",
        "tasks",
        "research",
        "docs",
        "notes",
        "graph",
    ]
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["kinds"] == KINDS_WITHOUT_TERMS_LOGS
    assert "5/7" in panel_text(page)
    # 概要とつながりの行はチェックの箱を持たない
    assert page.locator(f"{SETTINGS_PANEL} .st-always input").count() == 0
    # 「すべて」で全ての種類に戻す
    page.locator(f"{SETTINGS_PANEL} .st-all input").click()
    page.wait_for_function("document.querySelectorAll('nav.tabbar a').length === 9")
    assert tab_keys(page)[1:-1] == DEFAULT_KINDS


def test_kinds_override_moves_to_overview(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """開いている画面の種類を外すと概要へ移り、履歴は積まずに置き換える。外した種類のタブを指す URL は概要で開く（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=tasks&view=board")
    open_settings(page)
    history_length = page.evaluate("history.length")
    # 実行
    toggle_kind(page, "タスク")
    page.wait_for_selector(".overview")
    # 検証
    assert page.evaluate("history.length") == history_length
    assert "tab=tasks" not in page.evaluate("location.hash")
    assert "tasks" not in tab_keys(page)
    # 外した種類のタブを指す URL を開き直すと概要が開く
    page.goto(f"{url}#tab=tasks&view=board")
    page.wait_for_selector(".overview", timeout=RENDER_TIMEOUT_MS)
    assert "tab=tasks" not in page.evaluate("location.hash")


def test_reset(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """「既定に戻す」で、見た目・表示する種類・ライト / ダーク・表の列の上書きを全て外し、ワークスペースの既定の表示に戻す（正常系）。"""
    # 準備
    url, root = _preview(write_review_preview, make_item, valid_settings)
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    page = open_preview(url, "#tab=decisions&view=table")
    page.evaluate("document.documentElement.dataset.theme = 'light'")
    page.click("header.topbar .top-btn")
    open_settings(page)
    page.locator(f"{SETTINGS_PANEL} .st-look", has_text="グロウ").locator("input").click()
    toggle_kind(page, "メモ")
    page.wait_for_selector(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    overridden_text = page.inner_text(f"{SETTINGS_PANEL} .st-over")
    # 実行
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_function("document.querySelectorAll('nav.tabbar a').length === 9")
    # 検証
    assert "つながりの見た目" in overridden_text
    assert "表示する種類" in overridden_text
    assert "ライト / ダーク" in overridden_text
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["look"] is None
    assert prefs["kinds"] is None
    assert prefs["theme"] is None
    assert prefs["columns"] == {}
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    assert page.evaluate("document.activeElement?.dataset.focus ?? null") == "over"
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before


def test_workspace_default(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """上書きが無い項目には config.yaml の既定を使い、既定の見た目に「既定」の札を付ける。上書きが無ければ既定のままの旨を出す（正常系）。"""
    # 準備
    url, _ = _preview(
        write_review_preview,
        make_item,
        valid_settings,
        network_look="starlight",
        visible_kinds=KINDS_WITHOUT_TERMS_LOGS,
    )
    # 実行
    page = open_preview(url, "#tab=graph")
    open_settings(page)
    # 検証
    assert page.get_attribute(".screen.graph", "data-look") == "starlight"
    assert tab_keys(page) == [
        "overview",
        "decisions",
        "tasks",
        "research",
        "docs",
        "notes",
        "graph",
    ]
    badge = page.locator(f"{SETTINGS_PANEL} .st-look", has_text="既定")
    assert badge.count() == 1
    assert "星の光" in badge.inner_text()
    assert page.locator(f'{SETTINGS_PANEL} input[value="starlight"]').is_checked()
    assert read_prefs(page) is None or read_prefs(page) == {
        "theme": None,
        "columns": {},
        "look": None,
        "kinds": None,
        "diffSel": None,
    }


def test_exclusive_panels(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """コメントの一覧・絞り込みのドロワー・表示の設定のパネルは 1 つだけを開く。表示の設定を開いている間は、覆った本文の部品に `inert` を付ける（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=decisions&view=table")
    states: list[tuple[int, int, int]] = []

    def _record() -> None:
        """今開いているパネルの数（表示の設定・コメントの一覧・絞り込みのドロワー）を控える。"""
        states.append(
            (
                page.locator(SETTINGS_PANEL_OPEN).count(),
                page.locator(f"{COMMENTS_PANEL}.open").count(),
                page.locator(DRAWER_OPEN).count(),
            )
        )

    # 実行（表示の設定 → コメント → 絞り込み → 表示の設定）
    open_settings(page)
    page.wait_for_function(f"{INERT_COUNT_SCRIPT} > 0")
    _record()
    inert_while_open = page.evaluate(INERT_COUNT_SCRIPT)
    page.click(COMMENTS_BUTTON, force=True)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    _record()
    open_drawer(page)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open", state="detached")
    _record()
    page.click(SETTINGS_BUTTON, force=True)
    page.wait_for_selector(SETTINGS_PANEL_OPEN)
    page.wait_for_selector("dialog.drawer[open]", state="detached")
    _record()
    # 実行（閉じると、止めた部品を戻す）
    page.click(SETTINGS_BUTTON, force=True)
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    page.wait_for_function(f"{INERT_COUNT_SCRIPT} === 0")
    # 検証
    assert inert_while_open > 0
    assert states == [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)]
    assert page.get_attribute(FILTER_BUTTON, "aria-expanded") == "false"


def test_keeps_detail_panel(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """表示の設定を開いても、右の詳細パネルは開いたまま。詳細パネルを開いているときの Esc は、詳細パネルを先に閉じる（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel.open")
    # 実行
    open_settings(page)
    panel_while_settings = page.locator("aside.panel.open").count()
    page.keyboard.press("Escape")
    page.wait_for_selector("aside.panel.open", state="detached")
    settings_after_first_esc = page.locator(SETTINGS_PANEL_OPEN).count()
    page.keyboard.press("Escape")
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    # 検証
    assert panel_while_settings == 1
    assert settings_after_first_esc == 1


def test_narrow(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """幅 390px では画面の幅いっぱいに出し、ページを横に送らせない（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url)
    page.set_viewport_size(PHONE_VIEWPORT)
    # 実行
    open_settings(page)
    page.wait_for_timeout(500)
    box = page.locator(SETTINGS_PANEL).bounding_box()
    # 検証
    assert box is not None
    assert box["x"] == 0
    assert box["width"] == PHONE_VIEWPORT["width"]
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def test_defaults_changed_by_other(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """他の人が既定を書き換えると、上書きを持たない項目だけに新しい既定を当て、画面の下に知らせを出して、パネルにも時刻つきで残す（正常系）。"""
    # 準備
    url, root = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=graph")
    open_settings(page)
    # 見た目を個人の上書きにしておく（新しい既定が当たらない項目）
    page.locator(f"{SETTINGS_PANEL} .st-look", has_text="星屑").locator("input").click()
    # 実行（別のブラウザの代わりに、配信の既定の書き換えを直接呼ぶ）
    response = page.request.put(
        f"{url.rsplit('/', 1)[0]}/api/config/display",
        data={"network_look": "glow", "visible_kinds": KINDS_WITHOUT_TERMS_LOGS},
    )
    # 検証
    assert response.status == 200
    page.wait_for_selector(".stoast.show", timeout=RENDER_TIMEOUT_MS)
    assert page.get_attribute(".stoast", "role") == "status"
    assert page.inner_text(".stoast") == "ワークスペースの既定が変わりました。"
    page.wait_for_function("document.querySelectorAll('nav.tabbar a').length === 7")
    # 上書きを持つ見た目はそのまま、上書きを持たない表示する種類だけが新しい既定になる
    assert page.get_attribute(".screen.graph", "data-look") == "dust"
    assert tab_keys(page) == [
        "overview",
        "decisions",
        "tasks",
        "research",
        "docs",
        "notes",
        "graph",
    ]
    assert "ワークスペースの既定が変わりました（" in panel_text(page)
    assert read_config(root)["display"]["network_look"] == "glow"
    # 知らせは 6 秒で消える
    page.wait_for_selector(".stoast", state="detached", timeout=NOTICE_GONE_MS)
