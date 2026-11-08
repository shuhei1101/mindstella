"""画面設計『レビュー中の書き込み.tsx』の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Locator, Page, Route, expect
from preview_comment_helpers import free_comment, read_workspace_yaml
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeComment, MakeItem, MakePost, MakeThread

# 5 行を超える本文
LONG_BODY = "\n\n".join(f"{index} 行目の本文" for index in range(1, 9))

# 要見直しの赤（`--st-review`）の実際の色を読む
REVIEW_COLOR_JS = """(() => {
  const probe = document.createElement('i');
  probe.style.color = 'var(--st-review)';
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color;
})()"""

# 本文 5 行目の箇所
BODY_LOC = {"kind": "body", "start": 5, "end": 5, "text": "選んだ文"}


@pytest.fixture
def review_preview(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
) -> tuple[str, Path]:
    """レビュー中の書き込み（D-1 への箇所つきの新しいスレッド C-41・TH-1 への返信 C-43・クローズの TH-5 への返信 C-44・項目を指さない長い C-45）を持つワークスペースの配信の URL とフォルダを返す。"""
    return write_review_preview(
        make_item("D-1", title="最初の問い", body="D-1.md"),
        threads=(
            make_thread("TH-1", make_post("TH-1-1", body="案 A にする"), summary="D-1 の案の相談", target="D-1"),
            make_thread("TH-5", make_post("TH-5-1", body="閉じた質問"), status="closed", summary="閉じた話"),
        ),
        comments=(
            make_comment("C-41", target="D-1", loc=BODY_LOC, body="D-1 のここを直す"),
            free_comment(make_comment("C-43", body="了解", thread="TH-1")),
            free_comment(make_comment("C-44", body="戻してほしい", thread="TH-5")),
            free_comment(make_comment("C-45", body=LONG_BODY)),
        ),
        bodies={"D-1.md": "一行目\n\n二行目\n\n選んだ文\n"},
    )


def _panel(page: Page) -> Locator:
    """コメントの一覧のパネルを返す。"""
    return page.get_by_role("dialog", name="コメント")


def _row(page: Page, comment_id: str) -> Locator:
    """レビュー中の書き込みの行を返す。"""
    return _panel(page).locator(f"li[data-comment='{comment_id}']")


def _open(page: Page, review_preview: tuple[str, Path], search: str = "") -> Page:
    """レビュー中の書き込みの画面を開いた画面を返す。"""
    url, _ = review_preview
    return open_spa(page, url, f"?tab=decisions&panel=comments&review=1{search}")


def test_back(page: Page, review_preview: tuple[str, Path]) -> None:
    """「戻る」で開く前の画面（スレッド）へ戻る。入力欄の外の Esc も同じ（正常系）。"""
    # 準備
    _open(page, review_preview, "&thread=TH-1")
    # 実行
    _panel(page).get_by_role("button", name="戻る", exact=True).click()
    # 検証
    page.wait_for_url("**thread=TH-1**")
    assert "review=" not in page.url
    # 実行（Esc）
    _open(page, review_preview)
    page.keyboard.press("Escape")
    # 検証
    expect(_panel(page).get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()


def test_heading(page: Page, review_preview: tuple[str, Path]) -> None:
    """見出しに「レビュー中の書き込み」と件数を出す（正常系）。"""
    # 準備・実行
    _open(page, review_preview)
    # 検証
    expect(_panel(page).get_by_role("heading", level=2, name="レビュー中の書き込み（4）")).to_be_visible()


def test_select_all(page: Page, review_preview: tuple[str, Path]) -> None:
    """「すべて選ぶ」は送れる書き込みをまとめてチェックし・外し、一部だけのときは横棒にする（正常系）。"""
    # 準備
    _open(page, review_preview)
    select_all = _panel(page).get_by_role("checkbox", name="すべて選ぶ")
    # 検証（開いたときは全てチェック）
    expect(select_all).to_be_checked()
    # 実行
    _row(page, "C-41").get_by_role("checkbox").click()
    # 検証
    assert select_all.evaluate("box => box.indeterminate") is True
    # 実行
    select_all.click()
    # 検証
    expect(_row(page, "C-43").get_by_role("checkbox")).to_be_checked()
    expect(_row(page, "C-41").get_by_role("checkbox")).to_be_checked()


def test_selected_count(page: Page, review_preview: tuple[str, Path]) -> None:
    """選んだ件数を「{チェックした件数} / {送れる件数} 件」で出す（クローズのスレッドへの返信を数えない）（正常系）。"""
    # 準備
    _open(page, review_preview)
    # 検証
    expect(_panel(page)).to_contain_text("3 / 3 件")
    # 実行
    _row(page, "C-43").get_by_role("checkbox").click()
    # 検証
    expect(_panel(page)).to_contain_text("2 / 3 件")
    expect(_panel(page).get_by_role("button", name="まとめて送る（2 件）")).to_be_visible()


def test_send(page: Page, review_preview: tuple[str, Path]) -> None:
    """まとめて送ると送った行を外し、送った結果を `role="status"` で出す（正常系）。"""
    # 準備
    _, root = review_preview
    _open(page, review_preview)
    # 実行
    _panel(page).get_by_role("button", name="まとめて送る（3 件）").click()
    # 検証
    expect(_panel(page).get_by_role("status").filter(has_text="3 件を送り")).to_be_visible()
    expect(_panel(page).locator("li[data-comment]")).to_have_count(1)
    expect(_row(page, "C-44")).to_be_visible()
    assert [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]] == ["C-44"]


def test_send_result_when_none_checked(page: Page, review_preview: tuple[str, Path]) -> None:
    """チェックが 0 件で送ろうとしたとき、チェックを付けるよう出す（異常系）。"""
    # 準備
    _open(page, review_preview)
    _panel(page).get_by_role("checkbox", name="すべて選ぶ").click()
    # 実行
    _panel(page).get_by_role("button", name="まとめて送る（0 件）").click()
    # 検証
    expect(_panel(page).get_by_role("status").filter(has_text="送る書き込みにチェックを付けてください。")).to_be_visible()


def test_send_result_when_unreachable(page: Page, review_preview: tuple[str, Path]) -> None:
    """届かないとき、立ち上げ直すよう出して行を残す（異常系）。"""
    # 準備
    _open(page, review_preview)
    page.route("**/api/comments/send", lambda route: route.abort())
    # 実行
    _panel(page).get_by_role("button", name="まとめて送る（3 件）").click()
    # 検証
    expect(_panel(page).get_by_role("status").filter(has_text="送れませんでした。サーバーが止まっています。立ち上げ直してから送ってください。")).to_be_visible()
    expect(_panel(page).locator("li[data-comment]")).to_have_count(4)


def test_rows(page: Page, review_preview: tuple[str, Path]) -> None:
    """書き込みを溜めた順に並べ、スレッドの画面から開いたときはそのスレッドの書き込みの行を示す（正常系）。"""
    # 準備・実行
    _open(page, review_preview, "&thread=TH-1")
    # 検証
    assert _panel(page).locator("li[data-comment]").evaluate_all("rows => rows.map(r => r.dataset.comment)") == ["C-41", "C-43", "C-44", "C-45"]
    expect(_row(page, "C-43")).to_have_attribute("data-highlight", "")
    expect(_row(page, "C-41")).not_to_have_attribute("data-highlight", "")


def test_row_checkbox(page: Page, review_preview: tuple[str, Path]) -> None:
    """行のチェックは種類ごとの読み上げの名前を持ち、クローズのスレッドへの返信は押せない（正常系）。"""
    # 準備・実行
    _open(page, review_preview)
    # 検証
    expect(_row(page, "C-41").get_by_role("checkbox", name="D-1 へのコメントを送る")).to_be_checked()
    expect(_row(page, "C-43").get_by_role("checkbox", name="TH-1 への返信を送る")).to_be_checked()
    expect(_row(page, "C-44").get_by_role("checkbox", name="TH-5 への返信を送る")).to_be_disabled()
    expect(_row(page, "C-45").get_by_role("checkbox", name="項目を指さないコメントを送る")).to_be_checked()


def test_row_kind(page: Page, review_preview: tuple[str, Path]) -> None:
    """行の頭に「新しいスレッド」か「返信」の札を出す（正常系）。"""
    # 準備・実行
    _open(page, review_preview)
    # 検証
    expect(_row(page, "C-41").locator("[data-part=kind]")).to_have_text("新しいスレッド")
    expect(_row(page, "C-43").locator("[data-part=kind]")).to_have_text("返信")


def test_row_target(page: Page, review_preview: tuple[str, Path]) -> None:
    """新しいスレッドの向けた項目を押すと、画面を開いたまま右にその項目の詳細パネルを開く（正常系）。"""
    # 準備
    _open(page, review_preview)
    # 実行
    _row(page, "C-41").get_by_role("button", name="D-1 最初の問い").click()
    # 検証
    page.wait_for_url("**id=D-1**")
    expect(page.get_by_role("complementary", name="詳細")).to_be_visible()
    expect(_panel(page).get_by_role("heading", level=2, name="レビュー中の書き込み（4）")).to_be_visible()


def test_reply_thread(page: Page, review_preview: tuple[str, Path]) -> None:
    """返信の行の返信先のスレッドを押すと、そのスレッドを開く（正常系）。"""
    # 準備
    _open(page, review_preview)
    # 実行
    _row(page, "C-43").get_by_role("button", name="オープン D-1 の案の相談").click()
    # 検証
    page.wait_for_url("**thread=TH-1**")
    assert "review=" not in page.url


def test_open_thread(page: Page, review_preview: tuple[str, Path]) -> None:
    """新しいスレッドの行の「スレッドを開く」で、まだ送っていない新しいスレッドの画面を開く（正常系）。"""
    # 準備
    _open(page, review_preview)
    # 実行
    _row(page, "C-41").get_by_role("button", name="スレッドを開く").click()
    # 検証
    page.wait_for_url("**thread=C-41**")
    expect(_panel(page)).to_contain_text("まだ送っていないスレッドです。")


def test_row_location(page: Page, review_preview: tuple[str, Path]) -> None:
    """箇所を持つ書き込みに、箇所の名前と選んだ文の引用を出す（正常系）。"""
    # 準備・実行
    _open(page, review_preview)
    # 検証
    expect(_row(page, "C-41").locator("[data-part=loc]")).to_contain_text("本文 5 行目")
    expect(_row(page, "C-41").locator("[data-part=loc] blockquote")).to_have_text("選んだ文")


def test_row_body(page: Page, review_preview: tuple[str, Path]) -> None:
    """行の本文を Markdown で描き、項目の ID は文字のまま出す（正常系）。"""
    # 準備・実行
    _open(page, review_preview)
    body = _row(page, "C-41").locator("[data-part=body]")
    # 検証
    expect(body.locator(".md")).to_have_text("D-1 のここを直す")
    expect(body.locator("button.idlink")).to_have_count(0)


def test_edit(page: Page, review_preview: tuple[str, Path]) -> None:
    """修正で本文を入力欄に切り替え、Ctrl+Enter で書き換えて本文に戻す（正常系）。"""
    # 準備
    _, root = review_preview
    _open(page, review_preview)
    # 実行
    _row(page, "C-43").get_by_role("button", name="TH-1 への返信を修正").click()
    field = _row(page, "C-43").get_by_role("textbox", name="TH-1 への返信の本文")
    # 検証
    expect(field).to_have_attribute("aria-keyshortcuts", "Control+Enter")
    expect(_row(page, "C-43").get_by_role("button", name="修正", exact=True)).to_have_attribute("title", "修正（Ctrl+Enter）")
    # 実行
    field.fill("了解しました")
    field.press("Control+Enter")
    # 検証
    expect(_row(page, "C-43").locator("[data-part=body]")).to_have_text("了解しました")
    items = {item["id"]: item for item in read_workspace_yaml(root, "comments.yaml")["items"]}
    assert items["C-43"]["body"] == "了解しました"


def test_edit_when_empty(page: Page, review_preview: tuple[str, Path]) -> None:
    """空白だけの本文は送らず、入れてから直すよう出す（異常系）。"""
    # 準備
    _open(page, review_preview)
    _row(page, "C-43").get_by_role("button", name="TH-1 への返信を修正").click()
    # 実行
    _row(page, "C-43").get_by_role("textbox", name="TH-1 への返信の本文").fill("  ")
    _row(page, "C-43").get_by_role("button", name="修正", exact=True).click()
    # 検証
    expect(_row(page, "C-43").get_by_role("alert")).to_have_text("コメントを入れてから直してください。")


def test_edit_when_cancel(page: Page, review_preview: tuple[str, Path]) -> None:
    """Esc で書き換えを捨てて本文に戻す（正常系）。"""
    # 準備
    _open(page, review_preview)
    _row(page, "C-43").get_by_role("button", name="TH-1 への返信を修正").click()
    _row(page, "C-43").get_by_role("textbox", name="TH-1 への返信の本文").fill("捨てる文")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    expect(_row(page, "C-43").locator("[data-part=body]")).to_have_text("了解")
    expect(_panel(page).get_by_role("heading", level=2, name="レビュー中の書き込み（4）")).to_be_visible()


def test_remove_and_undo(page: Page, review_preview: tuple[str, Path]) -> None:
    """削除で行を「コメントを削除しました。」と「元に戻す」に置き換え、「元に戻す」で同じ ID のまま戻す（正常系）。"""
    # 準備
    _, root = review_preview
    _open(page, review_preview)
    # 実行
    _row(page, "C-43").get_by_role("button", name="TH-1 への返信を削除").click()
    # 検証
    expect(_panel(page).get_by_role("status").filter(has_text="コメントを削除しました。")).to_be_visible()
    expect(_panel(page).get_by_role("heading", level=2, name="レビュー中の書き込み（3）")).to_be_visible()
    # 実行
    _panel(page).get_by_role("button", name="元に戻す").click()
    # 検証
    expect(_row(page, "C-43")).to_be_visible()
    assert "C-43" in [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]]


def test_blocked_reason(page: Page, review_preview: tuple[str, Path]) -> None:
    """クローズのスレッドへの返信に、送れない理由と「スレッドを開く」を出す（正常系）。"""
    # 準備・実行
    _open(page, review_preview)
    # 検証
    expect(_row(page, "C-44")).to_contain_text("クローズのスレッドへの返信は送れません。オープンに戻すと送れます。")
    _row(page, "C-44").get_by_role("button", name="スレッドを開く").click()
    page.wait_for_url("**thread=TH-5**")


def test_stale(page: Page, review_preview: tuple[str, Path]) -> None:
    """まとめて送るが 409 のとき、`stale` の行に理由を `role="alert"` で出して枠を要見直しの赤にし、「箇所を外す」で箇所を外す（異常系）。"""
    # 準備
    _, root = review_preview
    _open(page, review_preview)
    body = {"type": "about:blank", "title": "Conflict", "status": 409, "detail": "x", "stale": [{"id": "C-41", "reason": "選んだ文が本文の 3 行目にありません"}]}

    def _refuse(route: Route) -> None:
        """まとめて送るを 409 で断る。"""
        route.fulfill(status=409, content_type="application/problem+json", body=json.dumps(body))

    page.route("**/api/comments/send", _refuse)
    # 実行
    _panel(page).get_by_role("button", name="まとめて送る（3 件）").click()
    # 検証
    expect(_row(page, "C-41").get_by_role("alert")).to_have_text("選んだ文が本文の 3 行目にありません")
    expect(_panel(page).get_by_role("status").filter(has_text="送れませんでした。送れない書き込みが 1 件あります。")).to_be_visible()
    review_color = page.evaluate(REVIEW_COLOR_JS)
    assert _row(page, "C-41").evaluate("e => getComputedStyle(e).borderTopColor") == review_color
    # 実行
    _row(page, "C-41").get_by_role("button", name="箇所を外す").click()
    # 検証
    expect(_row(page, "C-41").get_by_role("alert")).to_have_count(0)
    expect(_row(page, "C-41").locator("[data-part=loc]")).to_have_count(0)
    items = {item["id"]: item for item in read_workspace_yaml(root, "comments.yaml")["items"]}
    assert "loc" not in items["C-41"]


def test_empty(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """レビュー中の書き込みが無いとき、「レビュー中の書き込みはありません。」を出し、送る帯を出さない（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"))
    # 実行
    open_spa(page, url, "?tab=decisions&panel=comments&review=1")
    # 検証
    expect(_panel(page)).to_contain_text("レビュー中の書き込みはありません。")
    expect(_panel(page).get_by_role("button", name="まとめて送る（0 件）")).to_have_count(0)


def test_more(page: Page, review_preview: tuple[str, Path]) -> None:
    """5 行を超える本文は畳んで「続きを読む」を出し、押すと開く（正常系）。"""
    # 準備
    _open(page, review_preview)
    more = _row(page, "C-45").get_by_role("button", name="項目を指さないコメントの続きを読む")
    # 実行
    more.click()
    # 検証
    expect(_row(page, "C-45").get_by_role("button", name="項目を指さないコメントの本文を折りたたむ")).to_have_text("折りたたむ")
