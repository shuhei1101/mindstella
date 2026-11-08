"""画面設計『表示の設定.tsx』の結合テスト。"""

from __future__ import annotations

import json

from playwright.sync_api import Locator, Page, expect
from preview_spa_helpers import open_spa

# パネルを画面いっぱいに出す幅（これ以下）と、画面の高さ
NARROW_SIZE = {"width": 800, "height": 700}

# 既定が変わった知らせを出しておくミリ秒の前後
NOTICE_SHOWN_MS = 5_000
NOTICE_GONE_MS = 2_000

# 端末の保存領域のキー
PREFS_KEY = "mindmap-preview"


def _panel(page: Page) -> Locator:
    """表示の設定のパネルを返す。"""
    return page.get_by_role("dialog", name="表示の設定")


def _open(page: Page, url: str, search: str = "") -> Page:
    """表示の設定を開いた画面を返す。"""
    return open_spa(page, url, f"?tab=decisions&panel=display{search}")


def _prefs(page: Page) -> dict[str, object]:
    """端末の保存領域の値を返す。"""
    return json.loads(page.evaluate(f"localStorage.getItem('{PREFS_KEY}') ?? '{{}}'"))


def test_heading(page: Page, spa_preview: str) -> None:
    """パネルの見出しは「表示の設定」（正常系）。"""
    # 準備・実行
    _open(page, spa_preview)
    # 検証
    expect(_panel(page).get_by_role("heading", level=2, name="表示の設定")).to_be_visible()


def test_close(page: Page, spa_preview: str) -> None:
    """閉じるボタン・Esc・グレーアウトのどれでもパネルを閉じ、search params から `panel` を外す（正常系）。"""
    # 準備
    _open(page, spa_preview)
    # 実行
    _panel(page).get_by_role("button", name="表示の設定を閉じる").click()
    # 検証
    expect(_panel(page)).to_have_count(0)
    assert "panel=" not in page.url
    # 実行（Esc）
    _open(page, spa_preview)
    page.keyboard.press("Escape")
    # 検証
    expect(_panel(page)).to_have_count(0)
    # 実行（グレーアウト）
    _open(page, spa_preview)
    page.mouse.click(1200, 400)
    # 検証
    expect(_panel(page)).to_have_count(0)


def test_kinds(page: Page, spa_preview: str) -> None:
    """表示する種類を外すと端末の保存領域に残してタブから外し、開いている画面の種類を外したときは概要へ移す（正常系）。"""
    # 準備
    _open(page, spa_preview)
    # 実行
    _panel(page).get_by_role("checkbox", name="検討事項").click()
    # 検証
    expect(page.get_by_role("navigation", name="項目の種類").get_by_role("link", name="検討事項")).to_have_count(0)
    assert "decisions" not in (_prefs(page).get("kinds") or [])
    assert "tab=decisions" not in page.url


def test_minimap(page: Page, spa_preview: str) -> None:
    """差分のミニマップを表示しないにすると上書きとして残し、表示するに戻すと上書きを外す（正常系）。"""
    # 準備
    _open(page, spa_preview)
    box = _panel(page).get_by_role("checkbox", name="差分のミニマップ")
    # 実行
    box.click()
    # 検証
    assert _prefs(page).get("minimap") is False
    expect(_panel(page)).to_contain_text("この端末で変えている項目")
    # 実行
    box.click()
    # 検証
    assert _prefs(page).get("minimap") is None


def test_reset(page: Page, spa_preview: str) -> None:
    """「既定に戻す」で個人の上書きを全て外す（正常系）。"""
    # 準備
    _open(page, spa_preview)
    _panel(page).get_by_role("checkbox", name="タスク").click()
    _panel(page).get_by_role("checkbox", name="表のしま模様").click()
    # 実行
    _panel(page).get_by_role("button", name="既定に戻す").click()
    # 検証
    prefs = _prefs(page)
    assert prefs.get("kinds") is None
    assert prefs.get("tableStripes") is None
    expect(_panel(page)).to_contain_text("ワークスペースの既定のまま表示しています。")


def test_save_default_opens_confirm(page: Page, spa_preview: str) -> None:
    """「ワークスペースの既定にする」で既定の保存の確かめを開く（正常系）。"""
    # 準備
    _open(page, spa_preview)
    _panel(page).get_by_role("checkbox", name="タスク").click()
    # 実行
    _panel(page).get_by_role("button", name="ワークスペースの既定にする").click()
    # 検証
    expect(page.get_by_role("dialog", name="ワークスペースの既定を書き換えますか")).to_be_visible()


def test_defaults_changed_notice(page: Page, spa_preview: str) -> None:
    """他の人が既定を保存すると、画面の下に知らせを 6 秒出し、パネルに時刻つきで残す（正常系）。"""
    # 準備
    _open(page, spa_preview)
    origin = page.evaluate("location.origin")
    # 実行（他の人の保存として、既定の書き換えを直に送る）
    response = page.request.put(f"{origin}/api/config/display", data={"network_look": "dust", "visible_kinds": ["decisions", "tasks"]})
    # 検証
    assert response.status == 200
    notice = page.get_by_role("status").filter(has_text="ワークスペースの既定が変わりました。")
    expect(notice).to_be_visible(timeout=10_000)
    expect(_panel(page).locator("[data-part=message]")).to_contain_text("ワークスペースの既定が変わりました（")
    page.wait_for_timeout(NOTICE_SHOWN_MS + NOTICE_GONE_MS)
    expect(notice).to_have_count(0)


def test_defaults_changed_notice_when_own_save(page: Page, spa_preview: str) -> None:
    """自分が既定にした直後の書き換えでは、既定が変わった知らせを出さない（正常系）。"""
    # 準備
    _open(page, spa_preview)
    _panel(page).get_by_role("checkbox", name="タスク").click()
    _panel(page).get_by_role("button", name="ワークスペースの既定にする").click()
    # 実行
    page.get_by_role("dialog", name="ワークスペースの既定を書き換えますか").get_by_role("button", name="保存する").click()
    # 検証
    expect(_panel(page).locator("[data-part=message]")).to_contain_text("ワークスペースの既定にしました（")
    page.wait_for_timeout(NOTICE_GONE_MS)
    expect(page.get_by_role("status").filter(has_text="ワークスペースの既定が変わりました。")).to_have_count(0)


def test_workspace_settings(page: Page, spa_preview: str) -> None:
    """「設定を編集する」でパネルを閉じて設定の画面を開く（正常系）。"""
    # 準備
    _open(page, spa_preview)
    # 実行
    _panel(page).get_by_role("button", name="設定を編集する").click()
    # 検証
    page.wait_for_url("**tab=settings**")
    expect(_panel(page)).to_have_count(0)
    expect(page.get_by_role("heading", name="設定", level=1)).to_be_visible()


def test_scrim(page: Page, spa_preview: str) -> None:
    """幅 901px 以上はパネル以外をグレーアウトし、幅 900px 以下はグレーアウトせずパネルを画面の幅いっぱいに出す（正常系）。"""
    # 準備・実行
    _open(page, spa_preview)
    # 検証
    expect(page.locator("[data-scrim]")).to_be_visible()
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    # 検証
    expect(page.locator("[data-scrim]")).to_be_hidden()
    box = _panel(page).bounding_box()
    assert box is not None
    assert box["width"] == NARROW_SIZE["width"]
