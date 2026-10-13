"""部品設計『スレッドの書き込み』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 狭い幅で書き込みが占める部品の幅の割合の下限
NARROW_POST_RATIO = 0.9

POST = "ol.posts > li"


def test_user_post(open_story: OpenStory) -> None:
    """利用者の書き込み。右に寄せ、頭に「あなた」と日時を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--user-post")
    # 検証
    assert page.inner_text(f"{POST} .post-author") == "あなた"
    assert page.get_attribute(f"{POST} time", "datetime") == "2026-10-12T01:20:00+00:00"
    assert "user" in (page.get_attribute(POST, "class") or "").split()
    assert page.inner_text(f"{POST} .post-body").startswith("D-12 は案 B にしたい")
    # 本文の中の記録にある ID は、その項目を開くボタンにする
    assert page.get_attribute(f"{POST} button.idlink", "title") == "移し替えが途中で失敗したときの扱い"
    box = page.locator(POST).bounding_box()
    assert box is not None
    assert box["x"] + box["width"] >= page.evaluate("innerWidth") * 0.5


def test_ai_post(open_story: OpenStory) -> None:
    """AI の書き込み。左に寄せ、頭に「AI」と日時を出し、記録にある項目の ID はその項目を開くボタン、改行は保つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--ai-post")
    # 検証
    assert page.inner_text(f"{POST} .post-author") == "AI"
    assert "ai" in (page.get_attribute(POST, "class") or "").split()
    assert page.eval_on_selector_all(
        f"{POST} button.idlink", "buttons => buttons.map(b => b.textContent)"
    ) == ["D-12", "T-14"]
    assert page.eval_on_selector(f"{POST} .post-body", "e => getComputedStyle(e).whiteSpace") in {
        "pre-wrap",
        "pre-line",
    }


def test_unknown_id(open_story: OpenStory) -> None:
    """本文の中の記録に無い ID は、ボタンにせず文字のまま出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--unknown-id")
    # 検証
    assert "D-99" in page.inner_text(f"{POST} .post-body")
    assert page.eval_on_selector_all(
        f"{POST} button.idlink", "buttons => buttons.map(b => b.textContent)"
    ) == ["D-12"]


def test_closed_event(open_story: OpenStory) -> None:
    """利用者がクローズにした記録。枠の無い 1 行にチェックの印・「あなたがクローズにしました」・日時、次の行に理由を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--closed-event")
    # 検証
    assert page.get_attribute(POST, "data-event") == "closed"
    assert page.inner_text(f"{POST} .th-event-line span") == "あなたがクローズにしました"
    assert page.locator(f"{POST} .th-event-line svg.icon").count() == 1
    assert page.locator(f"{POST} .th-event-line time[datetime]").count() == 1
    assert page.locator(f"{POST} .th-event-reason").count() == 1
    assert page.eval_on_selector(POST, "e => getComputedStyle(e).borderTopWidth") == "0px"


def test_reopened_event(open_story: OpenStory) -> None:
    """利用者が理由を書かずにオープンに戻した記録。戻す印と「あなたがオープンに戻しました」・日時の 1 行だけを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--reopened-event")
    # 検証
    assert page.get_attribute(POST, "data-event") == "reopened"
    assert page.inner_text(f"{POST} .th-event-line span") == "あなたがオープンに戻しました"
    assert page.locator(f"{POST} .th-event-reason").count() == 0


def test_ai_closed_event(open_story: OpenStory) -> None:
    """AI がクローズにした記録。書き手を「AI が」にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--ai-closed-event")
    # 検証
    assert page.inner_text(f"{POST} .th-event-line span") == "AI がクローズにしました"
    assert "ai" in (page.get_attribute(POST, "class") or "").split()


def test_ai_reopened_event(open_story: OpenStory) -> None:
    """AI がオープンに戻した記録。「AI がオープンに戻しました」と理由を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--ai-reopened-event")
    # 検証
    assert page.inner_text(f"{POST} .th-event-line span") == "AI がオープンに戻しました"
    assert page.locator(f"{POST} .th-event-reason").count() == 1


def test_pending(open_story: OpenStory) -> None:
    """レビュー中の返信。利用者の書き込みと同じく右に寄せ、破線の枠と頭に「レビュー中」の印、右上に「修正」「削除」を出し、日時は出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending")
    # 検証
    assert page.get_attribute(POST, "data-comment") == "C-43"
    assert page.inner_text(f"{POST} .post-author") == "あなた"
    assert page.inner_text(f"{POST} .th-pending") == "レビュー中"
    assert page.locator(f"{POST} time").count() == 0
    assert page.eval_on_selector(POST, "e => getComputedStyle(e).borderTopStyle") == "dashed"
    assert page.get_by_role("button", name="TH-1 への返信を修正").count() == 1
    assert page.get_by_role("button", name="TH-1 への返信を削除").count() == 1
    assert page.get_attribute(f"{POST} button.idlink", "title") == "移し替えの失敗の扱いを書く"


def test_pending_editing(open_story: OpenStory) -> None:
    """レビュー中の返信を書き換えている。本文の代わりに書き換えの入力欄と「キャンセル」「修正」を出し、「修正」「削除」のアイコンは出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending-editing")
    # 検証
    assert page.input_value(f"{POST} form.row-edit textarea") == "了解。T-14 は今週中に書いてほしい"
    assert page.get_by_role("button", name="キャンセル").count() == 1
    assert page.locator(f"{POST} form.row-edit button[type='submit']").inner_text() == "修正"
    assert page.get_by_role("button", name="TH-1 への返信を修正").count() == 0
    assert page.get_by_role("button", name="TH-1 への返信を削除").count() == 0


def test_pending_edit_failed(open_story: OpenStory) -> None:
    """書き換えを保てなかった。入力を残し、印のアイコンと理由を出す（異常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending-edit-failed")
    # 検証
    assert page.get_attribute(f"{POST} .send-msg", "role") == "alert"
    assert (
        page.inner_text(f"{POST} .send-msg")
        == "サーバーが止まっています。立ち上げ直してから直してください。"
    )
    assert page.locator(f"{POST} .send-msg svg.icon").count() == 1
    assert page.input_value(f"{POST} form.row-edit textarea") != ""


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。AI の書き込みは左に寄せたまま、書き込みの幅を部品の幅の 9 割以上に広げる（正常系）。"""
    # 準備
    page = open_story("preview-threadpost--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    list_box = page.locator("ol.posts").bounding_box()
    post_box = page.locator(POST).bounding_box()
    assert list_box is not None
    assert post_box is not None
    assert post_box["width"] >= list_box["width"] * NARROW_POST_RATIO
    assert post_box["x"] == pytest.approx(list_box["x"], abs=1)
    assert post_box["x"] + post_box["width"] < list_box["x"] + list_box["width"]
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
