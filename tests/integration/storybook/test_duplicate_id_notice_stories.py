"""部品設計『重なった ID の通知』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 通知の帯
NOTICE = "#storybook-root [role='alert'].dup-note"


def test_single(open_story: OpenStory) -> None:
    """重なった ID が 1 件。見出しと、種類・ID のリンク・片方の ID を変更する案内を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-duplicateidnotice--single")
    # 検証
    notice = page.locator(NOTICE)
    assert notice.locator("strong").inner_text() == "同じ ID の項目が 2 件あります"
    assert " ".join(notice.inner_text().split()) == (
        "同じ ID の項目が 2 件あります ほかのセッションの書き込みで、検討事項 D-12 が重なりました。片方の ID を変更してください。"
    )
    assert notice.locator("a").get_attribute("href") == "#id=D-12"
    assert notice.get_by_role("button", name="通知を閉じる").count() == 1


def test_multiple(open_story: OpenStory) -> None:
    """重なった ID が 3 件。ID のリンクを「、」で並べ、ID の途中で折り返さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-duplicateidnotice--multiple")
    # 検証
    notice = page.locator(NOTICE)
    assert notice.locator("a").all_inner_texts() == ["D-12", "T-3", "N-8"]
    assert "検討事項 D-12、タスク T-3、メモ N-8" in notice.inner_text()
    assert page.evaluate(
        "[...document.querySelectorAll('.dup-note a')].map(a => a.getClientRects().length)"
    ) == [1, 1, 1]


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。本文を折り返し、閉じるボタンを右上に残し、横にはみ出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-duplicateidnotice--narrow")
    page.set_viewport_size(NARROW_SIZE)
    # 検証
    notice_box = page.locator(NOTICE).bounding_box()
    close_box = page.locator(NOTICE).get_by_role("button", name="通知を閉じる").bounding_box()
    body_box = page.locator(f"{NOTICE} .dup-body").bounding_box()
    assert notice_box is not None
    assert close_box is not None
    assert body_box is not None
    assert notice_box["x"] + notice_box["width"] <= NARROW_SIZE["width"]
    assert close_box["y"] <= body_box["y"] + 4
    assert close_box["x"] >= body_box["x"] + body_box["width"]
