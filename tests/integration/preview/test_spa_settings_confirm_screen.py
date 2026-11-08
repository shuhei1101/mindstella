"""画面設計『既定の保存の確かめ.tsx』の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from playwright.sync_api import Locator, Page, Route, expect
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import RECORD_DIR, MakeItem

# 確かめのモーダルの見出し
DIALOG_TITLE = "ワークスペースの既定を書き換えますか"


def _open(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> Path:
    """タスクを表示しないにして確かめを開き、ワークスペースのフォルダを返す。"""
    url, root = write_review_preview(make_item("D-1"), make_item("T-1"))
    open_spa(page, url, "?tab=decisions&panel=display")
    panel = page.get_by_role("dialog", name="表示の設定")
    panel.get_by_role("checkbox", name="タスク").click()
    panel.get_by_role("button", name="ワークスペースの既定にする").click()
    return root


def _dialog(page: Page) -> Locator:
    """確かめのモーダルを返す。"""
    return page.get_by_role("dialog", name=DIALOG_TITLE)


def _config(root: Path) -> dict[str, object]:
    """ワークスペースの config.yaml を返す。"""
    return yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))


def test_save(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """「保存する」で既定を書いてモーダルを閉じ、表示の設定に保存した旨を残す（正常系）。"""
    # 準備
    root = _open(page, write_review_preview, make_item)
    expect(_dialog(page)).to_contain_text("タスクを表示しない")
    expect(_dialog(page).get_by_role("button", name="取り消す")).to_be_focused()
    # 実行
    _dialog(page).get_by_role("button", name="保存する").click()
    # 検証
    expect(_dialog(page)).to_have_count(0)
    expect(page.get_by_role("dialog", name="表示の設定").locator("[data-part=message]")).to_contain_text("ワークスペースの既定にしました（")
    display = _config(root)["display"]
    assert isinstance(display, dict)
    assert "tasks" not in display["visible_kinds"]


def test_cancel(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """「取り消す」と Esc は何も書かずに閉じて表示の設定に戻る（正常系）。"""
    # 準備
    root = _open(page, write_review_preview, make_item)
    before = _config(root)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    expect(_dialog(page)).to_have_count(0)
    expect(page.get_by_role("dialog", name="表示の設定")).to_be_visible()
    # 実行
    page.get_by_role("dialog", name="表示の設定").get_by_role("button", name="ワークスペースの既定にする").click()
    _dialog(page).get_by_role("button", name="取り消す").click()
    # 検証
    expect(_dialog(page)).to_have_count(0)
    assert _config(root) == before


def test_failed(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """保存できなかったとき、モーダルを開いたまま理由を出し、config.yaml を書き換えない（異常系）。"""
    # 準備
    root = _open(page, write_review_preview, make_item)
    before = _config(root)
    body = {"type": "about:blank", "title": "Forbidden", "status": 403, "detail": "ワークスペースのフォルダに書き込めません（読み取り専用）。"}

    def _refuse(route: Route) -> None:
        """既定の書き換えを 403 で断る。"""
        route.fulfill(status=403, content_type="application/problem+json", body=json.dumps(body))

    page.route("**/api/config/display", _refuse)
    # 実行
    _dialog(page).get_by_role("button", name="保存する").click()
    # 検証
    expect(_dialog(page).get_by_role("alert")).to_have_text("保存できませんでした。ワークスペースのフォルダに書き込めません（読み取り専用）。")
    expect(_dialog(page)).to_be_visible()
    assert _config(root) == before


def test_busy(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """保存している間は Esc でも閉じない（正常系）。"""
    # 準備
    _open(page, write_review_preview, make_item)
    held: list[Route] = []
    page.route("**/api/config/display", lambda route: held.append(route))
    # 実行
    _dialog(page).get_by_role("button", name="保存する").click()
    expect(_dialog(page).get_by_role("button", name="保存しています")).to_be_disabled()
    page.keyboard.press("Escape")
    # 検証
    expect(_dialog(page)).to_be_visible()
    held[0].abort()
