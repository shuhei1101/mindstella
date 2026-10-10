"""部品設計『取り下げの札』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 札の高さ・枠の太さ・文字の色を読む
BADGE_SCRIPT = """(selector) => {
    const style = getComputedStyle(document.querySelector(selector));
    return {
        height: parseFloat(style.height),
        border: style.borderTopWidth,
        color: style.color,
    };
}"""

# 表の行・カードのタイトルの右に置く札の高さ
DEFAULT_HEIGHT_PX = 20

# 詳細パネルの題の右に置く札の高さ
LARGE_HEIGHT_PX = 22


def test_default(open_story: OpenStory) -> None:
    """表の行・カードのタイトルの右に置く大きさ。枠付きの × と「取り下げ」で、× は読み上げに出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-withdrawnbadge--default")
    # 検証
    badge = page.locator(".wd-badge")
    assert badge.count() == 1
    assert badge.inner_text() == "取り下げ"
    assert badge.locator("svg.mark").get_attribute("aria-hidden") == "true"
    style = page.evaluate(BADGE_SCRIPT, ".wd-badge")
    assert style["border"] == "1px"
    assert style["height"] == DEFAULT_HEIGHT_PX
    assert page.locator(".wd-large").count() == 0


def test_large(open_story: OpenStory) -> None:
    """詳細パネルの題の右に置く大きさ。通常より一回り大きい（正常系）。"""
    # 準備・実行
    page = open_story("preview-withdrawnbadge--large")
    # 検証
    badge = page.locator(".wd-badge.wd-large")
    assert badge.count() == 1
    assert badge.inner_text() == "取り下げ"
    assert page.evaluate(BADGE_SCRIPT, ".wd-badge")["height"] == LARGE_HEIGHT_PX
    assert page.evaluate(BADGE_SCRIPT, ".wd-badge")["border"] == "1px"


def test_beside_status_badges(open_story: OpenStory) -> None:
    """検討事項の状態「取り下げ」・タスクの状態「中止」・資料の状態「完成」の札と並べ、枠の有無で見分けられる（正常系）。"""
    # 準備・実行
    page = open_story("preview-withdrawnbadge--beside-status-badges")
    # 検証
    statuses = page.eval_on_selector_all(".st", "badges => badges.map(b => b.textContent)")
    assert statuses == ["取り下げ", "中止", "完成"]
    # 取り下げの札だけが枠を持つ（状態の札は枠なし）
    assert page.evaluate(BADGE_SCRIPT, ".wd-badge")["border"] == "1px"
    borders = page.eval_on_selector_all(".st", "badges => badges.map(b => getComputedStyle(b).borderTopWidth)")
    assert borders == ["0px", "0px", "0px"]
    # 同じ × の印と文言の状態「取り下げ」と並ぶ
    assert page.locator('.st[data-st="取り下げ"] svg.mark path').get_attribute("d") == page.locator(
        ".wd-badge svg.mark path"
    ).get_attribute("d")
    assert page.locator(".wd-badge").inner_text() == page.locator('.st[data-st="取り下げ"]').inner_text()
