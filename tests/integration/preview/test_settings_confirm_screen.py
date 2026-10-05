"""画面設計『既定の保存の確かめ』（ワークスペースの既定として保存する前のモーダル）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Route
from preview_fixture_types import OpenPreview, WriteReviewPreview
from preview_settings_helpers import (
    CONFIRM,
    CONFIRM_OPEN,
    SETTINGS_PANEL,
    open_settings,
    panel_text,
    read_config,
    read_prefs,
    tab_keys,
    toggle_kind,
)
from workspace_fixtures import MakeItem

# 既定の保存のボタン
SAVE_DEFAULT_BUTTON = f"{SETTINGS_PANEL} button:has-text('ワークスペースの既定にする')"

# 保存できなかったときの確かめの中の理由
ERROR_ALERT = f"{CONFIRM} .sc-error"

# 保存を待つ間の応答を保つ上限ミリ秒
SAVE_TIMEOUT_MS = 10_000

# 保存を失敗させる要求のパターン
PUT_PATTERN = "**/api/config/display"


def _open_changed(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> tuple[Page, Path]:
    """見た目を星屑・用語集を外した選びにして表示の設定を開いたページと、ワークスペースのフォルダを返す。"""
    url, root = write_review_preview(
        make_item("D-1"), make_item("G-1"), make_item("N-1"), settings=valid_settings
    )
    page = open_preview(url, "#tab=graph")
    open_settings(page)
    page.locator(f"{SETTINGS_PANEL} .st-look", has_text="星屑").locator("input").click()
    toggle_kind(page, "用語集")
    page.wait_for_selector(SAVE_DEFAULT_BUTTON)
    return page, root


def test_open(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """「ワークスペースの既定にする」で開き、今の既定と保存する値を並べる。最初のフォーカスは「取り消す」。変えない項目には札を付ける（正常系）。"""
    # 準備
    page, _ = _open_changed(write_review_preview, make_item, valid_settings, open_preview)
    # 実行
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 検証
    assert page.inner_text(f"{CONFIRM} h2") == "ワークスペースの既定を書き換えますか"
    rows = page.locator(f"{CONFIRM} .sc-row").all_inner_texts()
    assert len(rows) == 2
    assert "深宇宙" in rows[0]
    assert "星屑" in rows[0]
    assert "すべて表示" in rows[1]
    assert "用語集を表示しない" in rows[1]
    assert page.evaluate("document.activeElement.textContent.trim()") == "取り消す"
    assert page.get_attribute(SAVE_DEFAULT_BUTTON, "aria-haspopup") == "dialog"


def test_unchanged_item(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """表示する種類を変えないときは、その行に今の値と「変えない」の札を出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), settings=valid_settings)
    page = open_preview(url, "#tab=graph")
    open_settings(page)
    page.locator(f"{SETTINGS_PANEL} .st-look", has_text="グロウ").locator("input").click()
    # 実行
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 検証
    rows = page.locator(f"{CONFIRM} .sc-row").all_inner_texts()
    assert "グロウ" in rows[0]
    assert "変えない" not in rows[0]
    assert "すべて表示" in rows[1]
    assert "変えない" in rows[1]


def test_save(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """保存すると config.yaml の display を書き換え、確かめを閉じてパネルに知らせを残す。個人の上書きはそのまま残し、画面の下の知らせは出さない（正常系）。"""
    # 準備
    page, root = _open_changed(write_review_preview, make_item, valid_settings, open_preview)
    config_before = read_config(root)
    prefs_before = read_prefs(page)
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 実行
    page.get_by_role("button", name="保存する").click()
    page.wait_for_selector(CONFIRM, state="detached", timeout=SAVE_TIMEOUT_MS)
    # 検証
    config = read_config(root)
    assert config["display"] == {
        "network_look": "dust",
        "visible_kinds": ["decisions", "tasks", "research", "docs", "notes", "logs"],
    }
    assert {key: value for key, value in config.items() if key != "display"} == config_before
    assert "ワークスペースの既定にしました（" in panel_text(page)
    # 今の選びが既定と同じになり、ボタンの代わりにその旨を出す
    assert "今の選びはワークスペースの既定と同じです。" in panel_text(page)
    assert read_prefs(page) == prefs_before
    page.wait_for_timeout(1500)
    assert page.locator(".stoast").count() == 0


def test_cancel(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """「取り消す」と Esc では、何も書かずに閉じて、「ワークスペースの既定にする」へフォーカスを戻す（正常系）。"""
    # 準備
    page, root = _open_changed(write_review_preview, make_item, valid_settings, open_preview)
    config_before = (root / "config.yaml").read_bytes()
    sent: list[str] = []
    page.on(
        "request", lambda request: sent.append(request.url) if request.method == "PUT" else None
    )
    # 実行（取り消す）
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    page.get_by_role("button", name="取り消す").click()
    page.wait_for_selector(CONFIRM, state="detached")
    focus_after_cancel = page.evaluate("document.activeElement.textContent.trim()")
    # 実行（Esc）
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    page.keyboard.press("Escape")
    page.wait_for_selector(CONFIRM, state="detached")
    # 検証
    assert focus_after_cancel == "ワークスペースの既定にする"
    assert page.locator(SETTINGS_PANEL).count() == 1
    assert sent == []
    assert (root / "config.yaml").read_bytes() == config_before


def test_save_fails(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """サーバーが断ると、確かめを開いたまま理由を出し、config.yaml と画面の表示は保存の前のままにする。もう一度保存できる（正常系）。"""
    # 準備
    page, root = _open_changed(write_review_preview, make_item, valid_settings, open_preview)
    config_before = (root / "config.yaml").read_bytes()
    tabs_before = tab_keys(page)

    def _refuse(route: Route) -> None:
        """書けないことにして 500 の problem+json を返す。"""
        route.fulfill(
            status=500,
            content_type="application/problem+json",
            body='{"detail": "書き込めませんでした: config.yaml（読み取り専用）"}',
        )

    page.route(PUT_PATTERN, _refuse)
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 実行
    page.get_by_role("button", name="保存する").click()
    page.wait_for_selector(ERROR_ALERT, timeout=SAVE_TIMEOUT_MS)
    # 検証
    assert page.get_attribute(ERROR_ALERT, "role") == "alert"
    assert "保存できませんでした。書き込めませんでした: config.yaml" in page.inner_text(ERROR_ALERT)
    assert page.locator(CONFIRM_OPEN).count() == 1
    assert (root / "config.yaml").read_bytes() == config_before
    assert tab_keys(page) == tabs_before
    # 直したあとの保存は通る
    page.unroute(PUT_PATTERN)
    page.get_by_role("button", name="保存する").click()
    page.wait_for_selector(CONFIRM, state="detached", timeout=SAVE_TIMEOUT_MS)
    assert read_config(root)["display"]["network_look"] == "dust"


def test_save_fails_when_offline(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """サーバーに届かないときは、立ち上げ直して新しい URL で開くよう案内する（正常系）。"""
    # 準備
    page, root = _open_changed(write_review_preview, make_item, valid_settings, open_preview)
    config_before = (root / "config.yaml").read_bytes()
    page.route(PUT_PATTERN, lambda route: route.abort())
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 実行
    page.get_by_role("button", name="保存する").click()
    page.wait_for_selector(ERROR_ALERT, timeout=SAVE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(ERROR_ALERT) == (
        "保存できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、"
        "示された新しい URL で開いてから保存してください。"
    )
    assert (root / "config.yaml").read_bytes() == config_before


def test_busy(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """保存している間は、2 つのボタンを押せなくし、Esc でも閉じない（正常系）。"""
    # 準備
    page, root = _open_changed(write_review_preview, make_item, valid_settings, open_preview)
    held: list[Route] = []
    # 応答を保留して、保存している途中の状態を保つ
    page.route(PUT_PATTERN, lambda route: held.append(route))
    page.click(SAVE_DEFAULT_BUTTON)
    page.wait_for_selector(CONFIRM_OPEN)
    # 実行
    page.get_by_role("button", name="保存する").click()
    page.wait_for_selector(f"{CONFIRM} .spinner")
    page.keyboard.press("Escape")
    # 検証
    assert page.locator(CONFIRM_OPEN).count() == 1
    assert page.locator(f"{CONFIRM} button").evaluate_all(
        "buttons => buttons.map(b => b.disabled)"
    ) == [
        True,
        True,
    ]
    assert "保存しています" in page.inner_text(CONFIRM)
    # 保留を解くと保存が終わる
    held[0].continue_()
    page.wait_for_selector(CONFIRM, state="detached", timeout=SAVE_TIMEOUT_MS)
    assert read_config(root)["display"]["network_look"] == "dust"
