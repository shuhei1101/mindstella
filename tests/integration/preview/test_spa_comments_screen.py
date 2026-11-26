"""画面設計『コメントの一覧.tsx』の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import StartVoicePreview as _StartVoicePreview
from preview_voice_helpers import (
    assert_mic_blocked_after_click,
)
from workspace_fixtures import MakeItem as _MakeItem

import json
import re
from pathlib import Path

from playwright.sync_api import Locator, Page, Route, expect
from preview_comment_helpers import read_workspace_yaml
from preview_pending_helpers import assert_waiting, hold_requests, press_twice
from preview_spa_helpers import assert_below_topbar, open_spa
from preview_width_helpers import LONG_TITLE, NARROWEST_SIZE, assert_no_horizontal_scroll, narrow_left_panel
from preview_fixture_types import WriteReviewPreview
from workspace_fixtures import MakePost, MakeThread

import pytest
from preview_record_id_helpers import assert_described, assert_tip

# パネルを画面いっぱいに出す幅（これ以下）と、画面の高さ
NARROW_SIZE = {"width": 800, "height": 700}

# 書き換えの知らせ・保存を待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000


def _panel(page: Page) -> Locator:
    """コメントの一覧のパネルを返す。"""
    return page.get_by_role("dialog", name="コメント")


def _rows(page: Page) -> Locator:
    """スレッドの行を上から返す。"""
    return _panel(page).locator("li[data-thread], li[data-pending]")


def _open(page: Page, spa_comments_preview: tuple[str, Path], search: str = "") -> Page:
    """コメントの一覧を開いた画面を返す。"""
    url, _ = spa_comments_preview
    return open_spa(page, url, f"?tab=decisions&panel=comments{search}")


def test_heading(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """見出し「コメント」を、スレッドの一覧とスレッドの画面の両方で出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview)
    # 検証
    expect(_panel(page).get_by_role("heading", level=2, name="コメント")).to_be_visible()
    _rows(page).filter(has_text="二つ目の要約").locator("> button").click()
    expect(_panel(page).get_by_role("heading", level=2, name="コメント")).to_be_visible()


def test_review_entry(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """「レビュー中」の入口は件数を出し、押すとレビュー中の書き込みの画面に切り替えて入口を出さない（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    entry = _panel(page).get_by_role("button", name="レビュー中の書き込みを確かめる（2 件）")
    # 実行
    expect(entry).to_have_text("レビュー中2")
    entry.click()
    # 検証
    page.wait_for_url("**review=1**")
    expect(_panel(page).get_by_role("button", name="レビュー中の書き込みを確かめる（2 件）")).to_have_count(0)


def test_close(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """閉じるボタン・Esc・グレーアウトのどれでもパネルを閉じ、search params から `panel` を外す（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    # 実行（閉じるボタン）
    _panel(page).get_by_role("button", name="コメントの一覧を閉じる").click()
    # 検証
    expect(_panel(page)).to_have_count(0)
    assert "panel=" not in page.url
    # 実行（Esc）
    _open(page, spa_comments_preview)
    page.keyboard.press("Escape")
    # 検証
    expect(_panel(page)).to_have_count(0)
    # 実行（グレーアウト）
    _open(page, spa_comments_preview)
    page.mouse.click(1200, 400)
    # 検証
    expect(_panel(page)).to_have_count(0)


def test_status_filter(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """状態の絞り込みは件数つきの 3 つのボタンで、押した状態を `aria-pressed` で持ち、押すと行を絞る（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    group = _panel(page).get_by_role("group", name="スレッドの状態で絞る")
    # 検証（件数と押した状態）
    expect(group.get_by_role("button")).to_have_text(["オープン2", "クローズ1", "すべて3"])
    expect(group.get_by_role("button", name="オープン")).to_have_attribute("aria-pressed", "true")
    # 実行
    group.get_by_role("button", name="クローズ").click()
    # 検証
    page.wait_for_url("**tstatus=closed**")
    expect(group.get_by_role("button", name="クローズ")).to_have_attribute("aria-pressed", "true")
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page).first).to_contain_text("閉じた話")


# CSS 変数を計算した後の色にして返す
_RESOLVE_COLOR_JS = """(name) => {
    const probe = document.createElement('span');
    probe.style.backgroundColor = `var(${name})`;
    document.body.append(probe);
    const color = getComputedStyle(probe).backgroundColor;
    probe.remove();
    return color;
}"""


def test_status_filter_look(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """状態の絞り込みは表示形式の切り替えと同じ切り替えボタンで、選んでいる状態を `--tab-selected` の面と太字で浮き出させる（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview)
    group = _panel(page).get_by_role("group", name="スレッドの状態で絞る")
    selected = group.get_by_role("button", name="オープン")
    unselected = group.get_by_role("button", name="クローズ")
    # 検証
    assert selected.evaluate("e => getComputedStyle(e).backgroundColor") == page.evaluate(_RESOLVE_COLOR_JS, "--tab-selected")
    assert int(selected.evaluate("e => getComputedStyle(e).fontWeight")) > int(unselected.evaluate("e => getComputedStyle(e).fontWeight"))
    assert group.evaluate("e => getComputedStyle(e).borderTopWidth") != "0px"


def test_tag_filter(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """行のタグを押すとそのタグで絞り、チップに件数を出し、× で外す（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    # 実行
    _rows(page).filter(has_text="D-1 の案の相談").get_by_role("button", name="タグ「画面」で絞る").click()
    # 検証（タグで絞ると、まだ送っていない新規スレッドは並べない）
    page.wait_for_url("**ttag=**")
    expect(_rows(page)).to_have_count(1)
    expect(_panel(page)).to_contain_text("1 / 2 件")
    # 実行
    _panel(page).get_by_role("button", name="タグ「画面」の絞り込みを外す").click()
    # 検証
    expect(_rows(page)).to_have_count(3)
    assert "ttag=" not in page.url


def test_thread_rows(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """まだ送っていない新規スレッドを先頭に、続けてスレッドを最後の書き込みの新しい順に並べ、行を押すとスレッドの画面を開く（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    # 検証（並び）
    expect(_rows(page)).to_have_count(3)
    assert _rows(page).evaluate_all("rows => rows.map(r => r.dataset.thread ?? r.dataset.pending)") == ["C-41", "TH-2", "TH-1"]
    # 検証（未読の札）
    expect(_rows(page).filter(has_text="D-1 の案の相談").locator("[data-part=unread]")).to_have_text("未読")
    # 実行
    _rows(page).filter(has_text="二つ目の要約").locator("> button").click()
    # 検証
    page.wait_for_url("**thread=TH-2**")
    expect(_panel(page).get_by_role("heading", level=2, name="二つ目の要約")).to_be_visible()


def test_empty_state(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """並べる行が無いとき、絞り込みを含めた文言を出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview, "&tstatus=closed&ttag=調査")
    # 検証
    expect(_rows(page)).to_have_count(0)
    expect(_panel(page)).to_contain_text("タグ「調査」のクローズのスレッドはありません。")


def test_threads_unreadable(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """スレッドを読めないとき、理由を `role="alert"` で出し、まだ送っていない新規スレッドは並べる（異常系）。"""
    # 準備
    page.route("**/api/threads", lambda route: route.abort())
    # 実行
    _open(page, spa_comments_preview)
    # 検証
    alert = _panel(page).get_by_role("alert")
    expect(alert).to_have_text("スレッドを読めませんでした。サーバーが止まっています。再起動してから開いてください。")
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page).first).to_have_attribute("data-pending", "C-41")


def test_threads_unreadable_with_detail(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """スレッドの読み取りが 422 のとき、`detail` を続けて出す（異常系）。"""
    # 準備
    body = {"type": "about:blank", "title": "Unprocessable Entity", "status": 422, "detail": "threads.yaml が壊れています"}

    def _refuse(route: Route) -> None:
        """スレッドの読み取りを 422 で断る。"""
        route.fulfill(status=422, content_type="application/problem+json", body=json.dumps(body))

    page.route("**/api/threads", _refuse)
    # 実行
    _open(page, spa_comments_preview)
    # 検証
    expect(_panel(page).get_by_role("alert")).to_have_text("スレッドを読めませんでした。threads.yaml が壊れています")


def test_new_thread(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """「新規スレッド」を押すと入力を出して入力欄へフォーカスを移し、溜めると一覧の先頭と入口の件数に足す（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview)
    # 実行
    _panel(page).get_by_role("button", name="新規スレッド").click()
    field = _panel(page).get_by_role("textbox", name="新規スレッド")
    # 検証（入力欄へフォーカス）
    expect(field).to_be_focused()
    # 実行
    field.fill("全体を見直したい")
    _panel(page).get_by_role("button", name="レビューに追加").click()
    # 検証
    expect(field).to_have_value("")
    expect(_panel(page).get_by_role("button", name="レビュー中の書き込みを確かめる（3 件）")).to_be_visible()
    # まだ送っていない新規スレッドは、溜めた順に一覧の先頭へ並べる
    expect(_panel(page).locator("li[data-pending]")).to_have_count(2)
    expect(_panel(page).locator("li[data-pending]").last).to_contain_text("全体を見直したい")
    items = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [item["body"] for item in items if "target" not in item and "thread" not in item] == ["全体を見直したい"]



def test_new_thread_when_pressed_again_while_adding(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """溜めるのを待つ間にもう一度押しても溜めるのは 1 件で、待つ間は押せず、1 秒を超えるとボタンに回るマーカーを重ね、結果の行は文言だけにする（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview)
    _panel(page).get_by_role("button", name="新規スレッド").click()
    _panel(page).get_by_role("textbox", name="新規スレッド").fill("全体を見直したい")
    held = hold_requests(page, "**/api/comments", "POST")
    button = _panel(page).get_by_role("button", name="レビューに追加")
    box = button.bounding_box()
    assert box is not None
    # 実行（再描画の前に 2 回押す）
    press_twice(button)
    # 検証
    assert_waiting(page, button, held, box["width"])
    message = _panel(page).get_by_role("status").filter(has_text="レビューに追加しています")
    expect(message).to_be_visible()
    expect(message.locator("svg.animate-spin")).to_have_count(0)
    held.release()
    expect(_panel(page).locator("li[data-pending]").filter(has_text="全体を見直したい")).to_have_count(1)
    items = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [item["body"] for item in items if "target" not in item and "thread" not in item] == ["全体を見直したい"]

def test_new_thread_close(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """新規スレッドの入力を閉じると「新規スレッド」に戻し、下書きは残す（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    _panel(page).get_by_role("button", name="新規スレッド").click()
    _panel(page).get_by_role("textbox", name="新規スレッド").fill("下書きの文")
    # 実行
    _panel(page).get_by_role("button", name="新規スレッドの入力を閉じる").click()
    # 検証
    expect(_panel(page).get_by_role("textbox", name="新規スレッド")).to_have_count(0)
    _panel(page).get_by_role("button", name="新規スレッド").click()
    expect(_panel(page).get_by_role("textbox", name="新規スレッド")).to_have_value("下書きの文")


def test_pin(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """ピン止めを押すと `aria-pressed` を切り替えてグレーアウトを外し、開き直しても当てる（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    pin = _panel(page).get_by_role("button", name="ピン止めする（外側を押しても閉じない）")
    expect(pin).to_have_attribute("aria-pressed", "false")
    expect(page.locator("[data-scrim]")).to_have_count(1)
    # 実行
    pin.click()
    # 検証
    pinned = _panel(page).get_by_role("button", name="ピン止めを外す（外側を押したら閉じる）")
    expect(pinned).to_have_attribute("aria-pressed", "true")
    expect(page.locator("[data-scrim]")).to_have_count(0)
    page.reload()
    expect(_panel(page).get_by_role("button", name="ピン止めを外す（外側を押したら閉じる）")).to_be_visible()


def test_scrim(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """幅 901px 以上はパネル以外をグレーアウトし、幅 900px 以下はグレーアウトせずパネルを画面の幅いっぱいに出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview)
    # 検証（広い幅）
    expect(page.locator("[data-scrim]")).to_be_visible()
    # 実行（狭い幅）
    page.set_viewport_size(NARROW_SIZE)
    # 検証
    expect(page.locator("[data-scrim]")).to_be_hidden()
    box = _panel(page).bounding_box()
    assert box is not None
    assert box["width"] == NARROW_SIZE["width"]


def test_voice_input_when_service_stopped(
    page: Page,
    make_item: _MakeItem,
    start_voice_preview: _StartVoicePreview,
    unreachable_transcriber_url: str,
) -> None:
    """新規スレッドの入力で、文字起こしのサービスが起動していないときはマイクのボタンを押せなくし、押すと理由を結果の行に出す（正常系）。"""
    # 準備
    url, _ = start_voice_preview(unreachable_transcriber_url, make_item("D-1"))
    open_spa(page, url, "?tab=decisions&panel=comments")
    # 実行
    _panel(page).get_by_role("button", name="新規スレッド").click()
    # 検証
    field = page.get_by_role("textbox", name="新規スレッド")
    assert_mic_blocked_after_click(_panel(page).locator("form").filter(has=field), "[role=status]")


def test_target_filter(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """詳細パネルのボタンでその項目で絞った一覧を開き、絞っている間の新規スレッドはその項目へ向けて溜めて一覧に並べる。チップの × と、一覧を閉じて開き直すと絞らない（正常系）。"""
    # 準備
    url, root = spa_comments_preview
    open_spa(page, url, "?tab=decisions&id=D-1")
    detail = page.get_by_role("complementary", name="詳細")
    # 実行（詳細パネルのボタンで開く）
    detail.get_by_role("button", name="D-1 のコメントの一覧を開く").click()
    # 検証（D-1 へ向けたスレッドだけ。D-2 への新規スレッド C-41 は出ない）
    page.wait_for_url("**ttarget=D-1**")
    expect(_panel(page)).to_contain_text("最初の問い")
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page).first).to_contain_text("D-1 の案の相談")
    # 実行（絞っている間の新規スレッド）
    _panel(page).get_by_role("button", name="新規スレッド").click()
    expect(_panel(page).get_by_role("heading", name="D-1 への新規スレッド")).to_be_visible()
    _panel(page).get_by_role("textbox", name="D-1 への新規スレッド").fill("D-1 の進め方")
    _panel(page).get_by_role("button", name="レビューに追加").click()
    # 検証
    expect(_rows(page)).to_have_count(2, timeout=UPDATE_TIMEOUT_MS)
    expect(_rows(page).first).to_contain_text("D-1 の進め方")
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert (saved[-1].get("target"), saved[-1].get("loc"), saved[-1]["body"]) == ("D-1", None, "D-1 の進め方")
    # 実行（チップの × で外す）
    _panel(page).get_by_role("button", name="項目「D-1」の絞り込みを外す").click()
    # 検証
    expect(_rows(page)).to_have_count(4)
    assert "ttarget=" not in page.url
    # 実行（一覧を閉じてからもう一度絞り、閉じてトップバーで開き直す）
    _panel(page).get_by_role("button", name="コメントの一覧を閉じる").click()
    expect(_panel(page)).to_have_count(0)
    detail.get_by_role("button", name="D-1 のコメントの一覧を開く").click()
    page.wait_for_url("**ttarget=D-1**")
    _panel(page).get_by_role("button", name="コメントの一覧を閉じる").click()
    expect(_panel(page)).to_have_count(0)
    page.get_by_role("button", name=re.compile(r"^コメント（")).click()
    # 検証
    expect(_rows(page)).to_have_count(4)
    assert "ttarget=" not in page.url

# ─── パネルの上端（トップバーの下） ───


@pytest.mark.parametrize(
    "size",
    [pytest.param({"width": 1280, "height": 800}, id="wide"), pytest.param({"width": 390, "height": 844}, id="phone")],
)
def test_panel_below_topbar(page: Page, spa_comments_preview: tuple[str, Path], size: dict[str, int]) -> None:
    """パネルはトップバーとタブを覆わず、その下端から画面の下端まで出す（正常系）。"""
    # 準備
    page.set_viewport_size(size)
    # 実行
    _open(page, spa_comments_preview)
    # 検証
    assert_below_topbar(page, _panel(page))


def test_scrim_below_topbar(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """幅 901px 以上のグレーアウトはトップバーとタブを覆わず、その下端から画面の下端まで出す（正常系）。"""
    # 準備
    page.set_viewport_size({"width": 1280, "height": 800})
    # 実行
    _open(page, spa_comments_preview)
    # 検証
    assert_below_topbar(page, page.locator("[data-scrim]"))


@pytest.mark.parametrize(
    "size",
    [pytest.param({"width": 1280, "height": 800}, id="wide"), pytest.param({"width": 390, "height": 844}, id="phone")],
)
def test_topbar_usable_while_open(page: Page, spa_comments_preview: tuple[str, Path], size: dict[str, int]) -> None:
    """パネルを開いている間もトップバーのコメントのボタンを押せ、押すとパネルを閉じる（正常系）。"""
    # 準備
    page.set_viewport_size(size)
    _open(page, spa_comments_preview)
    # 実行
    page.get_by_role("banner").get_by_role("button", name=re.compile("^コメント（")).click()
    # 検証
    expect(_panel(page)).to_have_count(0)


def test_row_labels_not_wrapped_when_narrow(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """幅 390px でも、行の状態の札・書き手の文字は折り返さない（#690。正常系）。"""
    # 準備・実行
    page.set_viewport_size({"width": 390, "height": 844})
    _open(page, spa_comments_preview)
    rows = _panel(page).locator("li[data-thread]")
    expect(rows.first).to_be_visible()
    # 検証
    for selector in ("[data-state]", "[data-part=author]"):
        lines = [element.evaluate(_TEXT_LINES_JS) for element in rows.locator(selector).all()]
        assert lines and all(value == 1 for value in lines), (selector, lines)


# 要素の中の文字（テキストノード）が並ぶ行の数（折り返していなければ 1）
_TEXT_LINES_JS = "(e) => { const walker = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); const tops = new Set(); for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) { if (node.textContent.trim() === '') continue; const range = document.createRange(); range.selectNodeContents(node); for (const rect of range.getClientRects()) if (rect.width > 0) tops.add(Math.round(rect.top)); } return tops.size; }"


def test_thread_row_id_markers(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """スレッドの行の要約の中の記録にある D-1 をマーカーにし、乗せるとツールチップを出し、行を開くボタンの aria-describedby で読み上げる（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    row = _rows(page).filter(has_text="D-1 の案の相談").locator("> button")
    marker = row.locator("[data-record-id='D-1']").first
    # 実行
    marker.hover()
    # 検証
    expect(row.locator("a")).to_have_count(0)
    assert_tip(page, "最初の問い")
    assert_described(page, row, "最初の問い")

# ─── 幅の区切り ───

# 左のパネルの幅を残す sessionStorage のキー（ワークスペースの配信ではワークスペースの ID を付ける）
_LEFT_WIDTH_KEY_JS = "'mindmap-left-panel-width' + (location.pathname.split('/')[1] === 'w' ? ':' + decodeURIComponent(location.pathname.split('/')[2]) : '')"

# 幅の区切りを出す広い幅
WIDE_SIZE = {"width": 1440, "height": 800}


def _resizer(page: Page) -> Locator:
    """コメントの一覧の幅の区切りを返す。"""
    return _panel(page).get_by_role("separator", name="コメントの一覧の幅")


def test_resizer_visible(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """幅の区切りは表示の幅が 901px 以上のときだけ出す（正常系）。"""
    # 準備
    page.set_viewport_size({"width": 1280, "height": 800})
    _open(page, spa_comments_preview)
    expect(_resizer(page)).to_be_visible()
    # 実行
    page.set_viewport_size({"width": 900, "height": 800})
    # 検証
    expect(_resizer(page)).to_have_count(0)


def test_resizer_initial_value(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """そのタブに残した幅が無ければ既定の 384 で開き、残した幅があればその幅、上限を超えるときは上限で開いて残した値は書き換えない（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE_SIZE)
    _open(page, spa_comments_preview)
    expect(_resizer(page)).to_have_attribute("aria-valuenow", "384")
    # 実行（残した幅で開き直す）
    page.evaluate(f"sessionStorage.setItem({_LEFT_WIDTH_KEY_JS}, '500')")
    page.reload()
    # 検証
    expect(_resizer(page)).to_have_attribute("aria-valuenow", "500")
    assert _panel(page).evaluate("(e) => e.getBoundingClientRect().width") == 500
    # 実行（上限を超える幅で開き直す）
    page.evaluate(f"sessionStorage.setItem({_LEFT_WIDTH_KEY_JS}, '1200')")
    page.reload()
    # 検証（上限は表示の幅 − 400）
    expect(_resizer(page)).to_have_attribute("aria-valuemax", "1040")
    expect(_resizer(page)).to_have_attribute("aria-valuenow", "1040")
    assert page.evaluate(f"sessionStorage.getItem({_LEFT_WIDTH_KEY_JS})") == "1200"


def test_resizer_action(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """→ で広げ ← で狭め、Home で下限、End で上限にし、変えた幅をそのタブに残す（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE_SIZE)
    _open(page, spa_comments_preview)
    resizer = _resizer(page)
    resizer.focus()
    # 実行・検証（矢印キー）
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowLeft")
    expect(resizer).to_have_attribute("aria-valuenow", "400")
    assert page.evaluate(f"sessionStorage.getItem({_LEFT_WIDTH_KEY_JS})") == "400"
    # 実行・検証（Home・End）
    page.keyboard.press("Home")
    expect(resizer).to_have_attribute("aria-valuenow", "320")
    page.keyboard.press("End")
    expect(resizer).to_have_attribute("aria-valuenow", "1040")
    assert page.evaluate(f"sessionStorage.getItem({_LEFT_WIDTH_KEY_JS})") == "1040"
    # 実行・検証（ドラッグ）
    page.keyboard.press("Home")
    box = resizer.bounding_box()
    assert box is not None
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 40, y)
    page.mouse.move(x + 80, y)
    page.mouse.up()
    expect(resizer).to_have_attribute("aria-valuenow", "400")
    assert page.evaluate(f"sessionStorage.getItem({_LEFT_WIDTH_KEY_JS})") == "400"


def test_resizer_max_when_detail_open(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """幅 1100px 以上で詳細パネルを開いているときは、上限からさらに詳細パネルの幅を引く（正常系）。"""
    # 準備・実行
    page.set_viewport_size(WIDE_SIZE)
    _open(page, spa_comments_preview, "&id=D-1")
    resizer = _resizer(page)
    resizer.focus()
    page.keyboard.press("End")
    # 検証（1440 − 400 − 640）
    expect(resizer).to_have_attribute("aria-valuemax", "400")
    expect(resizer).to_have_attribute("aria-valuenow", "400")


def test_left_width_shared(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """コメントの一覧で変えた幅で表示の設定も開き、表示の設定は区切りを持たない（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE_SIZE)
    _open(page, spa_comments_preview)
    _resizer(page).focus()
    page.keyboard.press("ArrowRight")
    expect(_resizer(page)).to_have_attribute("aria-valuenow", "400")
    url, _ = spa_comments_preview
    # 実行
    open_spa(page, url, "?tab=decisions&panel=display")
    # 検証
    region = page.locator("[role=dialog][aria-label='表示の設定']")
    expect(region).to_have_count(1)
    assert region.evaluate("(e) => e.getBoundingClientRect().width") == 400
    expect(region.get_by_role("separator")).to_have_count(0)


@pytest.mark.parametrize("narrowed", [pytest.param(False, id="width-360"), pytest.param(True, id="panel-320")])
def test_no_horizontal_scroll(
    page: Page,
    write_review_preview: WriteReviewPreview,
    make_item: _MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    narrowed: bool,
) -> None:
    """スレッド 100 件（改行の無い長いタイトルを含む）を、幅 360px と、幅 1440px で左のパネルを下限の 320px にして開いても、ページもパネルも横にスクロールしない（正常系）。"""
    # 準備
    threads = tuple(
        make_thread(f"TH-{n}", make_post(f"TH-{n}-1", body="相談"), summary=LONG_TITLE if n % 10 == 1 else f"相談 {n}", target="D-1", tags=["画面"])
        for n in range(1, 101)
    )
    url, _ = write_review_preview(make_item("D-1", title=LONG_TITLE), threads=threads)
    page.set_viewport_size(WIDE_SIZE if narrowed else NARROWEST_SIZE)
    # 実行
    open_spa(page, url, "?tab=decisions&panel=comments")
    if narrowed:
        narrow_left_panel(page)
        expect(_resizer(page)).to_have_attribute("aria-valuenow", "320")
    expect(_rows(page)).to_have_count(100)
    # 検証
    assert_no_horizontal_scroll(page, _panel(page))
