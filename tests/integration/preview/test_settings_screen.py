"""画面設計『表示の設定』（左から出すパネル。表示する種類・既定に戻す・既定が変わった知らせ。見た目はネットワークのドロップダウンで選ぶ）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page
from preview_fit_helpers import assert_fits_smallest, set_smallest
from preview_body_layout_helpers import SIDE_NAME, SIDE_VIEWPORT, open_side_by_side
from preview_body_view_helpers import open_body_view
from preview_comment_helpers import COMMENTS_BUTTON, COMMENTS_PANEL
from preview_drawer_helpers import (
    DRAWER_OPEN,
    FILTER_BUTTON,
    badge_text,
    checked_values,
    click_value,
    close_drawer,
    open_drawer,
)
from preview_fixture_types import OpenPreview, WriteReviewPreview, WriteSamplePreview
from preview_minimap_helpers import MINIMAP_HASH, PANEL_SCOPE, open_minimap
from preview_history_helpers import preselect_diff
from preview_settings_helpers import (
    CONFIRM,
    CONFIRM_OPEN,
    DEFAULT_KINDS,
    LOOK_SELECT,
    SETTINGS_BUTTON,
    SETTINGS_PANEL,
    SETTINGS_PANEL_OPEN,
    open_settings,
    panel_text,
    pick_look,
    read_config,
    read_prefs,
    tab_keys,
    toggle_kind,
)
from preview_stack_helpers import (
    DETAIL_HASH,
    NARROW_VIEWPORT,
    WIDE_VIEWPORT,
    has_left_front,
    is_inert,
    open_narrow,
    wait_front,
)
from workspace_fixtures import RECORD_DIR, CallTool, MakeItem, MakeWorkspace


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

# 絞り込みのドロワーの状態の条件で、「未決定」のチェックが `checked` のとおりになるのを待つ式
UNDECIDED_CHECKED_SCRIPT = """checked => document.querySelector(
    'dialog.drawer input[data-key="status"][value="未決定"]'
)?.checked === checked"""


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
    assert "見た目と表示する種類は、ワークスペースの既定と同じです。" in opened["text"]
    assert opened["buttons"] == ["設定を編集する"]
    assert focus_after_esc == "settings"
    assert focus_after_close == "settings"
    assert page.get_attribute(SETTINGS_BUTTON, "aria-expanded") == "false"


def test_look_override(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """見た目はネットワークのドロップダウンで選び、その場でネットワークに当たり、個人の上書きとして端末に残る。パネルは見た目を選ばせず、変えている項目に出す。config.yaml は書き換えない（正常系）。"""
    # 準備
    url, root = _preview(write_review_preview, make_item, valid_settings)
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    page = open_preview(url, "#tab=graph")
    initial_look = page.get_attribute(".screen.graph", "data-look")
    # 実行
    pick_look(page, "dust")
    open_settings(page)
    # 検証
    assert initial_look == "deep"
    assert page.get_attribute(".screen.graph", "data-look") == "dust"
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["look"] == "dust"
    assert "この端末で変えている項目" in panel_text(page)
    assert "ネットワークの見た目" in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    # パネルには見た目の選びを置かない
    assert page.locator(f"{SETTINGS_PANEL} .st-look").count() == 0
    assert page.locator(f"{SETTINGS_PANEL} input[type=radio]").count() == 0
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before
    # 開き直しても、個人の上書きを使う
    page.reload()
    page.wait_for_selector(".screen.graph", timeout=RENDER_TIMEOUT_MS)
    assert page.get_attribute(".screen.graph", "data-look") == "dust"
    assert page.eval_on_selector(LOOK_SELECT, "select => select.value") == "dust"


def test_kinds_override(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """表示する種類を外すと、その種類のタブをトップバーから外す。概要とネットワークは常に出す（正常系）。"""
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
    # 概要とネットワークの行はチェックの箱を持たない
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
    page = open_preview(url, "#tab=graph")
    pick_look(page, "glow")
    page.evaluate("document.documentElement.dataset.theme = 'light'")
    page.click("header.topbar .top-btn")
    open_settings(page)
    toggle_kind(page, "メモ")
    page.wait_for_selector(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    overridden_text = page.inner_text(f"{SETTINGS_PANEL} .st-over")
    # 実行
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_function("document.querySelectorAll('nav.tabbar a').length === 9")
    # 検証
    assert "ネットワークの見た目" in overridden_text
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
    # 見た目もワークスペースの既定（深宇宙）に戻る
    assert page.get_attribute(".screen.graph", "data-look") == "deep"
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before


def test_workspace_default(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """上書きが無い項目には config.yaml の既定を使い、ドロップダウンの既定の見た目の選択肢に「（既定）」を添える。上書きが無ければ既定のままの旨を出す（正常系）。"""
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
    options = page.eval_on_selector_all(
        f"{LOOK_SELECT} option", "items => items.map(o => [o.value, o.textContent])"
    )
    assert options == [
        ["glow", "グロウ"],
        ["starlight", "星の光（既定）"],
        ["constellation", "星図"],
        ["deep", "深宇宙"],
        ["dust", "星屑"],
    ]
    assert page.eval_on_selector(LOOK_SELECT, "select => select.value") == "starlight"
    # パネルは見た目の選びを持たない
    assert page.locator(f"{SETTINGS_PANEL} .st-look").count() == 0
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
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


def test_narrow_in_front_of_detail(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """幅 390px で詳細パネルを開いたまま開くと、詳細パネルの前に出て詳細パネルが `inert` になる。Esc で表示の設定だけが閉じ、開く前の詳細パネルがそのまま見える（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    # 実行（詳細パネルを開いたまま開く）
    open_settings(page)
    wait_front(page, "settings")
    in_front = {"left_front": has_left_front(page), "detail_inert": is_inert(page, "detail")}
    # 実行（Esc で閉じる）
    page.keyboard.press("Escape")
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    wait_front(page, "detail")
    # 検証
    assert in_front == {"left_front": True, "detail_inert": True}
    assert has_left_front(page) is False
    assert is_inert(page, "detail") is False
    assert page.inner_text("aside.panel .d-title") == "D-1の題"
    assert "id=D-1" in page.evaluate("location.hash")


def test_narrow_when_detail_opened_after(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """幅 390px で表示の設定を開いた後に詳細パネルを開く（別の項目へ移る）と、詳細パネルが前に出て表示の設定が `inert` になる（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_settings(page)
    wait_front(page, "settings")
    # 実行（別の項目 T-1 の詳細パネルへ移る）
    page.evaluate("location.hash = '#tab=tasks&id=T-1'")
    # 検証
    wait_front(page, "detail")
    assert has_left_front(page) is False
    assert is_inert(page, "settings") is True
    assert is_inert(page, "detail") is False


def test_narrow_when_width_crosses_900(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """詳細パネルと両方開いたまま幅が 900px をまたぐと、`left-front` と `inert` が外れ、また 900px 以下に戻ると付け直す（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_settings(page)
    wait_front(page, "settings")
    # 実行（幅 1200px にする）
    page.set_viewport_size(WIDE_VIEWPORT)
    page.wait_for_function("!document.body.classList.contains('left-front')")
    wide = {
        "left_front": has_left_front(page),
        "detail_inert": is_inert(page, "detail"),
        "settings_inert": is_inert(page, "settings"),
    }
    # 実行（幅 390px に戻す）
    page.set_viewport_size(NARROW_VIEWPORT)
    page.wait_for_function("document.body.classList.contains('left-front')")
    # 検証
    assert wide == {"left_front": False, "detail_inert": False, "settings_inert": False}
    assert is_inert(page, "detail") is True
    assert is_inert(page, "settings") is False


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
    # 見た目を個人の上書きにしておく（新しい既定が当たらない項目）
    pick_look(page, "dust")
    open_settings(page)
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


def test_filter_override(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """サーバーの配信で残した条件が画面の既定の条件と違う画面を、「この端末で変えている項目」に「絞り込み（{画面}）」で並べる（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=tasks&view=table")
    open_drawer(page)
    click_value(page, "status", "未着手")
    page.wait_for_function("document.querySelector('[data-act=filter] .fbadge')?.textContent === '1'")
    close_drawer(page)
    # 実行
    open_settings(page)
    # 検証
    assert "絞り込み（タスク）" in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    assert page.locator(f"{SETTINGS_PANEL} button:has-text('既定に戻す')").count() == 1


def test_filter_override_when_same_as_default(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """残した条件が画面の既定の条件と同じ画面は、変えている項目に並べない（正常系）。"""
    # 準備（検討事項の既定の状態の条件から、1 つ外して戻す）
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    click_value(page, "status", "未決定")
    page.wait_for_function(UNDECIDED_CHECKED_SCRIPT, arg=False)
    click_value(page, "status", "未決定")
    page.wait_for_function(UNDECIDED_CHECKED_SCRIPT, arg=True)
    close_drawer(page)
    # 実行
    open_settings(page)
    # 検証
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    assert "絞り込み" not in panel_text(page)
    assert page.locator(f"{SETTINGS_PANEL} button:has-text('既定に戻す')").count() == 0


def test_reset_filters(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """「既定に戻す」で残した絞り込みの条件も外し、開いている画面を画面の既定の条件で描き直す（正常系）。"""
    # 準備（検討事項の既定の状態の条件から 1 つ外して残す）
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    click_value(page, "status", "未決定")
    page.wait_for_function(UNDECIDED_CHECKED_SCRIPT, arg=False)
    close_drawer(page)
    open_settings(page)
    overridden_text = page.inner_text(f"{SETTINGS_PANEL} .st-over")
    # 実行
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_function(
        "document.querySelector('aside.settings-drawer').textContent.includes('ワークスペースの既定のまま表示しています。')"
    )
    page.keyboard.press("Escape")
    page.wait_for_selector(SETTINGS_PANEL, state="detached")
    open_drawer(page)
    # 検証
    assert "絞り込み（検討事項）" in overridden_text
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["filters"] == {}
    # 記録の検討事項は未決定だけなので、ドロワーに並ぶ状態も未決定だけで、外していたチェックが戻る
    assert checked_values(page, "status") == ["未決定"]
    assert badge_text(page) == "1"


# 「詳細に表示するもの」の区画の中の、差分のミニマップのチェックボックスの名前
MINIMAP_LEGEND = "詳細に表示するもの"
MINIMAP_LABEL = "差分のミニマップ"

# 開いている詳細パネルの帯が消える・戻るまで待つ上限ミリ秒
MINIMAP_TOGGLE_MS = 5_000


def _minimap_checkbox(page: Page) -> Any:
    """表示の設定の、区画「詳細に表示するもの」の中の「差分のミニマップ」のチェックボックスを返す。"""
    return page.locator(f"{SETTINGS_PANEL} fieldset", has_text=MINIMAP_LEGEND).get_by_role(
        "checkbox", name=MINIMAP_LABEL
    )


def test_minimap_override(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """「差分のミニマップ」のチェックを外すと、開いている詳細パネルからその場で帯が消え、個人の上書きとして残り、`config.yaml` は変わらない。戻すと帯が戻る（正常系）。"""
    # 準備
    url, root = write_minimap_preview()
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    open_minimap(page, open_preview, url, MINIMAP_HASH)
    history_length = page.evaluate("history.length")
    open_settings(page)
    # 検証（開いた直後は表示するで、上書きを持たない）
    assert _minimap_checkbox(page).is_checked() is True
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    # 実行（チェックを外す）
    _minimap_checkbox(page).click()
    page.wait_for_function(
        "document.querySelector('aside.panel .df-map') === null", timeout=MINIMAP_TOGGLE_MS
    )
    # 検証（詳細パネルは開いたままで、本文の差分の印は出ている）
    assert page.locator(f"{PANEL_SCOPE}.open").count() == 1
    assert page.locator(f"{PANEL_SCOPE} .md del.df-blk").count() == 1
    assert page.locator(f"{PANEL_SCOPE} .md ins.df-blk").count() == 1
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["minimap"] is False
    assert _minimap_checkbox(page).is_checked() is False
    assert MINIMAP_LABEL in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    assert page.evaluate("history.length") == history_length
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before
    # 実行（チェックを戻す）
    _minimap_checkbox(page).click()
    page.wait_for_selector(f"{PANEL_SCOPE} .df-map .df-map-m", timeout=MINIMAP_TOGGLE_MS)
    # 検証（表示するは上書きを外す）
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["minimap"] is None
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before


def test_reset_when_minimap(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """表示しないにした「差分のミニマップ」は、「この端末で変えている項目」の末尾に並び、「既定に戻す」で外れて帯が戻る（正常系）。"""
    # 準備（表示する種類も変え、その後ろに差分のミニマップが並ぶようにする）
    url, _ = write_minimap_preview()
    open_minimap(page, open_preview, url, MINIMAP_HASH)
    open_settings(page)
    toggle_kind(page, "用語集")
    _minimap_checkbox(page).click()
    page.wait_for_function(
        "document.querySelector('aside.panel .df-map') === null", timeout=MINIMAP_TOGGLE_MS
    )
    # 検証
    assert "表示する種類・差分のミニマップ" in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    # 実行
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_selector(f"{PANEL_SCOPE} .df-map .df-map-m", timeout=MINIMAP_TOGGLE_MS)
    # 検証（全ての上書きが外れ、チェックも表示するへ戻る）
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["minimap"] is None
    assert prefs["kinds"] is None
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    assert _minimap_checkbox(page).is_checked() is True


# 「ワークスペースの既定にする」のボタン
SAVE_DEFAULT_BUTTON = f"{SETTINGS_PANEL} button:has-text('ワークスペースの既定にする')"

# 「この端末で変えている項目」に並ぶ名前
BODY_LAYOUT_LABEL = "本文の差分の並べ方"

# 開いている詳細パネルの左右に並べた本文が消える・出るまで待つ上限ミリ秒
BODY_LAYOUT_TOGGLE_MS = 5_000


def _open_side_by_side_panel(
    write_body_layout_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> tuple[Page, Path]:
    """資料 A-1 の詳細パネルを差分の表示で開き、「左右に並べる」を押して、左右に並べた本文が出るまで待つ。"""
    url, root = write_body_layout_preview()
    page.set_viewport_size(SIDE_VIEWPORT)
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=docs&id=A-1")
    page.get_by_role("button", name=SIDE_NAME).click()
    open_side_by_side(page, PANEL_SCOPE)
    return page, root


def test_reset_when_body_diff_layout(
    write_body_layout_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """詳細で選んだ「左右に並べる」は、「この端末で変えている項目」に「本文の差分の並べ方」として並び、「ワークスペースの既定にする」は出さず、「既定に戻す」で外れてインラインに戻る（正常系）。"""
    # 準備
    _open_side_by_side_panel(write_body_layout_preview, open_preview, page)
    history_length = page.evaluate("history.length")
    # 実行
    open_settings(page)
    # 検証（見た目と表示する種類は既定のままなので、ボタンの代わりにその旨を出す）
    assert BODY_LAYOUT_LABEL in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    assert page.get_by_role("button", name="ワークスペースの既定にする").count() == 0
    assert "見た目と表示する種類は、ワークスペースの既定と同じです。" in panel_text(page)
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["bodyLayout"] == "side"
    # 実行（既定に戻す）
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_selector(f"{PANEL_SCOPE} .sbs", state="detached", timeout=BODY_LAYOUT_TOGGLE_MS)
    # 検証（詳細パネルは開いたままインラインに戻り、全ての上書きが外れる）
    assert page.locator(f"{PANEL_SCOPE}.open").count() == 1
    assert page.locator(f"{PANEL_SCOPE} .md:not(.md-value) del.df-blk").count() == 1
    assert page.locator(f"{PANEL_SCOPE} .md:not(.md-value) ins.df-blk").count() == 1
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["bodyLayout"] is None
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    assert page.evaluate("history.length") == history_length


def test_save_default_when_body_diff_layout(
    write_body_layout_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """表示する種類も変えて「ワークスペースの既定にする」で保存しても、本文の差分の並べ方は保存する対象に含めず、config.yaml に書かず、個人の上書きに残す（正常系）。"""
    # 準備
    page, root = _open_side_by_side_panel(write_body_layout_preview, open_preview, page)
    open_settings(page)
    toggle_kind(page, "用語集")
    # 検証（変えている項目に、表示する種類の後ろへ並ぶ）
    assert "表示する種類・本文の差分の並べ方" in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    # 実行
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 検証（確かめに並ぶのは見た目と表示する種類の 2 行だけ）
    assert len(page.locator(f"{CONFIRM} .sc-row").all_inner_texts()) == 2
    assert BODY_LAYOUT_LABEL not in page.inner_text(CONFIRM)
    # 実行
    page.get_by_role("button", name="保存する").click()
    page.wait_for_selector(CONFIRM, state="detached", timeout=BODY_LAYOUT_TOGGLE_MS)
    # 検証
    display = read_config(root)["display"]
    assert sorted(display) == ["network_look", "visible_kinds"]
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["bodyLayout"] == "side"
    assert page.locator(f"{PANEL_SCOPE} .sbs").count() == 1


def test_fit_smallest(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示の設定は、幅 320px で横にスクロールせず、パネルと閉じるボタンが表示幅の中にある（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    set_smallest(page)
    # 実行
    open_settings(page)
    # 検証
    assert_fits_smallest(
        page,
        (SETTINGS_PANEL, f"{SETTINGS_PANEL} button[aria-label='表示の設定を閉じる']"),
        scope=SETTINGS_PANEL,
    )


# ===== 編集（設定を編集する） =====

# 設定の画面（開いている間は本文の区画を置き換える）
WORKSPACE_SCREEN = ".pe-ws"

# 表示の設定のパネルの「設定を編集する」
WORKSPACE_ENTRY = f"{SETTINGS_PANEL} .pe-ws-entry"


def test_workspace_entry(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """サーバーの配信では、パネルの本文の下端に見出し「ワークスペースの設定」と、書き換えられる設定の案内と、「設定を編集する」を出す（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    open_settings(page)
    # 検証
    entry = page.locator(WORKSPACE_ENTRY)
    assert entry.locator("h3").inner_text() == "ワークスペースの設定"
    assert entry.locator(".pe-ws-sum").inner_text() == "題名・フェーズ・ゴール・対象・カテゴリー"
    button = entry.get_by_role("button", name="設定を編集する")
    assert button.count() == 1
    body = page.locator(f"{SETTINGS_PANEL} .st-wrap").bounding_box()
    box = button.bounding_box()
    assert body is not None
    assert box is not None
    # 本文のほかの部品より下にある
    others = page.locator(f"{SETTINGS_PANEL} .st-wrap > :not(.pe-ws-entry)").evaluate_all(
        "nodes => Math.max(...nodes.map(n => n.getBoundingClientRect().bottom))"
    )
    assert box["y"] >= others


def test_workspace_entry_hidden_when_diff(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示をしている間は「設定を編集する」を出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    preselect_diff(page, "V-1")
    diff = open_preview(url, "#tab=decisions&view=table")
    diff.wait_for_selector(".df-chip")
    # 実行
    open_settings(diff)
    # 検証
    assert diff.locator(WORKSPACE_ENTRY).count() == 0
    assert diff.get_by_role("button", name="設定を編集する").count() == 0


def test_workspace_entry_hidden_when_exported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しでは「設定を編集する」を出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    page = open_preview(out.as_uri(), "#tab=decisions&view=table")
    page.wait_for_selector("table.grid")
    # 実行
    open_settings(page)
    # 検証
    assert page.locator(WORKSPACE_ENTRY).count() == 0
    assert page.get_by_role("button", name="設定を編集する").count() == 0


def test_workspace_entry_opens_screen(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """押すと、表示の設定のパネルを閉じて設定の画面を開く（正常系）。"""
    # 準備
    url, _ = _preview(write_review_preview, make_item, valid_settings)
    page = open_preview(url, "#tab=decisions&view=table")
    open_settings(page)
    # 実行
    page.get_by_role("button", name="設定を編集する").click()
    # 検証
    page.wait_for_selector(WORKSPACE_SCREEN)
    assert page.locator(SETTINGS_PANEL_OPEN).count() == 0
    assert page.locator(f"{WORKSPACE_SCREEN} h1").inner_text() == "設定"


# 本文の表とセクションの見せ方の 4 つのチェックの名前と、上書きするときの端末の保存領域のキーと値
BODY_VIEW_CHECKS = [
    pytest.param("表の列の固定", "tablePin", False, id="pin"),
    pytest.param("表の見出しの固定", "tableHead", False, id="head"),
    pytest.param("表のしま模様", "tableStripes", True, id="stripes"),
    pytest.param("セクションの折りたたみ", "sectionFold", False, id="fold"),
]

# 開いている詳細パネルの本文の見せ方が変わるまで待つ上限ミリ秒
BODY_VIEW_TOGGLE_MS = 5_000


def _body_view_checkbox(page: Page, label: str) -> Any:
    """表示の設定の、区画「詳細に表示するもの」の中の、名前のチェックボックスを返す。"""
    return page.locator(f"{SETTINGS_PANEL} fieldset", has_text=MINIMAP_LEGEND).get_by_role(
        "checkbox", name=label
    )


@pytest.mark.parametrize(("label", "key", "value"), BODY_VIEW_CHECKS)
def test_body_view_override(
    write_body_view_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    label: str,
    key: str,
    value: bool,
) -> None:
    """本文の表とセクションの見せ方のチェックを既定と違う側にすると、個人の上書きとして残り、「この端末で変えている項目」に並び、`config.yaml` は変わらない。既定へ戻すと上書きを外す（正常系）。"""
    # 準備
    url, root = write_body_view_preview()
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    open_body_view(page, open_preview, url)
    open_settings(page)
    # 検証（開いた直後は上書きを持たない）
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    before = _body_view_checkbox(page, label).is_checked()
    # 実行（チェックを既定と違う側にする）
    _body_view_checkbox(page, label).click()
    page.wait_for_function(
        "([key, value]) => JSON.parse(localStorage.getItem('mindmap-preview'))[key] === value",
        arg=[key, value],
        timeout=BODY_VIEW_TOGGLE_MS,
    )
    # 検証
    assert _body_view_checkbox(page, label).is_checked() is (not before)
    assert label in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before
    # 実行（チェックを戻す）
    _body_view_checkbox(page, label).click()
    page.wait_for_function(
        "(key) => JSON.parse(localStorage.getItem('mindmap-preview'))[key] === null",
        arg=key,
        timeout=BODY_VIEW_TOGGLE_MS,
    )
    # 検証（既定と同じ側に戻したので、上書きを外す）
    assert _body_view_checkbox(page, label).is_checked() is before
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before


def test_reset_when_body_view(
    write_body_view_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """既定と違う側にした 4 つのチェックは、「この端末で変えている項目」に並び、「既定に戻す」で全て外れて本文が既定の見せ方に戻る（正常系）。"""
    # 準備（4 つとも既定と違う側にする）
    url, _ = write_body_view_preview()
    open_body_view(page, open_preview, url)
    open_settings(page)
    _body_view_checkbox(page, "表の列の固定").click()
    _body_view_checkbox(page, "表の見出しの固定").click()
    _body_view_checkbox(page, "表のしま模様").click()
    _body_view_checkbox(page, "セクションの折りたたみ").click()
    page.wait_for_function(
        "document.querySelector('aside.panel button.md-fold') === null", timeout=BODY_VIEW_TOGGLE_MS
    )
    # 検証（本文は上書きどおりで、4 つの名前が並ぶ）
    over = page.inner_text(f"{SETTINGS_PANEL} .st-over")
    assert "表の列の固定・表の見出しの固定・表のしま模様・セクションの折りたたみ" in over
    assert page.locator(f"{PANEL_SCOPE} button.md-pin").count() == 0
    assert page.locator(f"{PANEL_SCOPE} table.md-head-stick").count() == 0
    assert page.locator(f"{PANEL_SCOPE} table.md-stripes").count() == 1
    # 実行（既定に戻す）
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_selector(f"{PANEL_SCOPE} button.md-fold", timeout=BODY_VIEW_TOGGLE_MS)
    # 検証（詳細パネルは開いたまま既定の見せ方に戻り、全ての上書きが外れる）
    assert page.locator(f"{PANEL_SCOPE}.open").count() == 1
    assert page.locator(f"{PANEL_SCOPE} button.md-pin").count() == 7
    assert page.locator(f"{PANEL_SCOPE} table.md-head-stick").count() == 1
    assert page.locator(f"{PANEL_SCOPE} table.md-stripes").count() == 0
    prefs = read_prefs(page)
    assert prefs is not None
    assert (prefs["tablePin"], prefs["tableHead"], prefs["tableStripes"], prefs["sectionFold"]) == (
        None,
        None,
        None,
        None,
    )
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)


def test_save_default_when_body_view(
    write_body_view_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """表示する種類も変えて「ワークスペースの既定にする」で保存しても、本文の表とセクションの見せ方は保存する対象に含めず、config.yaml に書かず、個人の上書きに残す（正常系）。"""
    # 準備
    url, root = write_body_view_preview()
    open_body_view(page, open_preview, url)
    open_settings(page)
    toggle_kind(page, "用語集")
    _body_view_checkbox(page, "表のしま模様").click()
    _body_view_checkbox(page, "セクションの折りたたみ").click()
    # 検証（変えている項目に、表示する種類の後ろへ並ぶ）
    assert "表示する種類・表のしま模様・セクションの折りたたみ" in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    # 実行
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 検証（確かめに並ぶのは見た目と表示する種類の 2 行だけ）
    assert len(page.locator(f"{CONFIRM} .sc-row").all_inner_texts()) == 2
    assert "しま模様" not in page.inner_text(CONFIRM)
    # 実行
    page.get_by_role("button", name="保存する").click()
    page.wait_for_selector(CONFIRM, state="detached", timeout=BODY_VIEW_TOGGLE_MS)
    # 検証
    display = read_config(root)["display"]
    assert sorted(display) == ["network_look", "visible_kinds"]
    prefs = read_prefs(page)
    assert prefs is not None
    assert (prefs["tableStripes"], prefs["sectionFold"]) == (True, False)
