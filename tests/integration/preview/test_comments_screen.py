"""画面設計『コメントの一覧』（スレッドの一覧）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from playwright.sync_api import Page
from preview_comment_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    REVIEW_ENTRY,
    REVIEW_HEAD,
    THREAD_ROWS,
    THREE_LINE_BODY,
    UPDATE_TIMEOUT_MS,
    free_comment,
    open_list,
    read_workspace_yaml,
    thread_row,
    wait_until_focused,
)
from preview_drawer_helpers import DRAWER, DRAWER_OPEN, FILTER_BUTTON, open_drawer
from preview_fixture_types import OpenPreview, WriteReviewPreview
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeComment,
    MakeItem,
    MakePost,
    MakeThread,
)

# パネルを画面いっぱいに出す幅（これ以下）と、画面の高さ
NARROW_WIDTH = 800
VIEWPORT_HEIGHT = 700

# 覆われた本文の部品に付けた `inert` の数
INERT_COUNT_SCRIPT = "document.querySelectorAll('main [inert]').length"

# 絞り込みの帯のセグメント・タグのチップ・空の状態
SEGMENTS = f"{COMMENTS_PANEL} .talk-filter button"
TAG_CHIP = f"{COMMENTS_PANEL} .talk-chips"
EMPTY = f"{COMMENTS_PANEL} .comments-empty"

# 一覧の下端の新しいスレッドの入口と入力
COMPOSE_BUTTON = f"{COMMENTS_PANEL} .talk-new button[data-focus='compose']"
COMPOSE_CLOSE = f"{COMMENTS_PANEL} button[data-focus='compose-close']"
COMPOSE_TEXTAREA = f"{COMMENTS_PANEL} .talk-new form.send textarea"


@pytest.fixture
def served_threads(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
) -> tuple[str, Path]:
    """D-1・D-2 と、スレッド TH-1（オープン・D-1・タグ 画面）・TH-2（オープン・最後が利用者）・TH-5（クローズ・タグ 画面）と、レビュー中の C-41（新しいスレッド）・C-43（TH-1 への返信）を持つワークスペースの配信の URL とフォルダを返す。"""
    return write_review_preview(
        make_item("D-1", title="最初の問い"),
        make_item("D-2"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", read=True, body="案 A にする", created="2026-10-12T00:30:00+00:00"),
                make_post("TH-1-2", author="ai", body="案 A で進めます", created="2026-10-12T01:00:00+00:00"),
                summary="D-1 の案の相談",
                tags=["画面"],
                target="D-1",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", body="二つ目の質問", created="2026-10-12T02:00:00+00:00"),
                summary="二つ目の要約",
                tags=["調査"],
            ),
            make_thread(
                "TH-5",
                make_post("TH-5-1", body="閉じた質問", created="2026-10-12T03:00:00+00:00"),
                status="closed",
                summary="閉じた話",
                tags=["画面"],
                events=[
                    {
                        "kind": "closed",
                        "author": "user",
                        "reason": None,
                        "created": "2026-10-12T03:10:00+00:00",
                    }
                ],
            ),
        ),
        comments=(
            make_comment("C-41", target="D-2", body="写しは git で取る"),
            free_comment(make_comment("C-43", body="了解", thread="TH-1")),
        ),
    )


def test_heading(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """トップバーのコメントのボタンで、見ている画面に重ねて左から出すパネルを開き、見出し「コメント」と「レビュー中」の入口を出す（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    open_list(page)
    page.wait_for_function(
        "document.querySelector('aside.comments-panel').getBoundingClientRect().x === 0"
    )
    # 検証
    assert page.get_attribute(COMMENTS_PANEL, "aria-label") == "コメントの一覧"
    assert page.inner_text(f"{COMMENTS_PANEL} .comments-head h2") == "コメント"
    assert page.get_attribute(COMMENTS_BUTTON, "aria-expanded") == "true"
    assert page.get_attribute(REVIEW_ENTRY, "aria-label") == "レビュー中の書き込みを確かめる（2 件）"
    assert page.inner_text(f"{REVIEW_ENTRY} .count") == "2"
    # 見ている画面を開いたまま重ねる
    assert page.locator("main table.grid").count() == 1


def test_review_entry(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「レビュー中」の入口でレビュー中の書き込みの画面へ切り替える（履歴に積まない）（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    history_length = page.evaluate("history.length")
    open_list(page)
    # 実行
    page.click(REVIEW_ENTRY)
    # 検証
    page.wait_for_selector(REVIEW_HEAD)
    assert page.evaluate("history.length") == history_length


def test_review_entry_when_zero(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """レビュー中が 0 件でも入口を出し、件数の塗りを外す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"))
    page = open_preview(url)
    # 実行
    open_list(page)
    # 検証
    assert page.get_attribute(REVIEW_ENTRY, "aria-label") == "レビュー中の書き込みを確かめる（0 件）"
    assert "zero" in (page.get_attribute(REVIEW_ENTRY, "class") or "").split()


def test_close(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """閉じるボタン・Esc・トップバーのコメントのボタンで閉じ、履歴に積まない（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url, "#tab=decisions&view=table")
    history_length = page.evaluate("history.length")
    open_list(page)
    assert history_length == page.evaluate("history.length")
    # 実行・検証（閉じるボタン）
    page.get_by_role("button", name="コメントの一覧を閉じる").click()
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    assert page.get_attribute(COMMENTS_BUTTON, "aria-expanded") == "false"
    # Esc
    open_list(page)
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    # トップバーのコメントのボタン
    open_list(page)
    page.click(COMMENTS_BUTTON)
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    assert page.evaluate("history.length") == history_length


def test_close_when_detail_open(
    served_threads: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """詳細パネルを開いているときの Esc は、詳細パネルを先に閉じる（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    open_list(page)
    page.click(f"{thread_row('TH-1')} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} button.row-target[data-focus='target']")
    page.click(f"{COMMENTS_PANEL} button.row-target[data-focus='target']")
    page.wait_for_selector("aside.panel.open")
    # 実行・検証
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1


def test_filter(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """オープン・クローズ・すべてを件数つきで並べ、押した状態で一覧を絞る。スレッドの画面との行き来をまたいで保つ（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    # 実行・検証（既定はオープン）
    open_list(page)
    assert page.get_attribute(f"{COMMENTS_PANEL} .talk-filter", "aria-label") == "スレッドの状態で絞る"
    assert page.eval_on_selector_all(
        SEGMENTS, "bs => bs.map(b => [b.textContent.replace(/\\s+/g, ''), b.getAttribute('aria-pressed')])"
    ) == [["オープン2", "true"], ["クローズ1", "false"], ["すべて3", "false"]]
    assert page.eval_on_selector_all(f"{THREAD_ROWS}", "rows => rows.map(r => r.dataset.thread ?? 'new:' + r.dataset.pending)") == [
        "new:C-41",
        "TH-2",
        "TH-1",
    ]
    # クローズ
    page.click(f"{SEGMENTS}[data-focus='filter:closed']")
    assert page.eval_on_selector_all(THREAD_ROWS, "rows => rows.map(r => r.dataset.thread)") == ["TH-5"]
    # スレッドの画面との行き来をまたいで保つ
    page.click(f"{thread_row('TH-5')} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    page.get_by_role("button", name="一覧へ戻る").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-filter")
    assert page.get_attribute(f"{SEGMENTS}[data-focus='filter:closed']", "aria-pressed") == "true"
    # すべて
    page.click(f"{SEGMENTS}[data-focus='filter:all']")
    assert page.locator(THREAD_ROWS).count() == 4


def test_tag_filter(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """行のタグを押すとそのタグで絞ってチップと件数を出し、まだ送っていない新しいスレッドは並べず、外すで戻す（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    open_list(page)
    page.click(f"{SEGMENTS}[data-focus='filter:all']")
    # 実行
    page.click(f"{thread_row('TH-1')} button.th-tag")
    # 検証
    assert page.inner_text(f"{TAG_CHIP} .chip") == "画面"
    assert page.inner_text(f"{TAG_CHIP} .hint") == "2 / 3 件"
    assert page.eval_on_selector_all(THREAD_ROWS, "rows => rows.map(r => r.dataset.thread)") == ["TH-5", "TH-1"]
    assert page.get_attribute(f"{thread_row('TH-1')} button.th-tag", "aria-pressed") == "true"
    # 実行（外す）
    page.get_by_role("button", name="タグ「画面」の絞り込みを外す").click()
    # 検証
    assert page.locator(TAG_CHIP).count() == 0
    assert page.locator(THREAD_ROWS).count() == 4


def test_tag_filter_when_pressed_again(
    served_threads: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """絞っているタグをもう一度押すと外す（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    open_list(page)
    page.click(f"{thread_row('TH-1')} button.th-tag")
    assert page.locator(TAG_CHIP).count() == 1
    # 実行
    page.click(f"{thread_row('TH-1')} button.th-tag")
    # 検証
    assert page.locator(TAG_CHIP).count() == 0


def test_rows(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """まだ送っていない新しいスレッドを先頭に、最後の書き込みの新しい順に並べ、状態・題・向けた項目・最後の書き手・レビュー中の印を出す（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    # 実行
    open_list(page)
    # 検証
    pending = thread_row("new:C-41")
    assert page.inner_text(f"{pending} .th-state") == "レビュー中"
    assert page.inner_text(f"{pending} .th-title") == "写しは git で取る"
    assert page.inner_text(f"{pending} .th-author") == "あなた"
    assert page.locator(f"{pending} .th-tags").count() == 0
    first = thread_row("TH-1")
    assert page.inner_text(f"{first} .th-state") == "オープン"
    assert page.inner_text(f"{first} .th-title") == "D-1 の案の相談"
    assert page.inner_text(f"{first} .th-line2 .mono") == "D-1"
    assert page.inner_text(f"{first} .th-author") == "AI"
    assert page.locator(f"{first} .th-line2 time[datetime]").count() == 1
    # レビュー中の返信を持つスレッドには、レビュー中の印を出す
    assert page.inner_text(f"{first} .th-pending") == "レビュー中"
    assert page.locator(f"{thread_row('TH-2')} .th-pending").count() == 0
    assert page.inner_text(f"{thread_row('TH-2')} .th-author") == "あなた"
    assert page.locator(f"{thread_row('TH-2')} .th-line2 .mono").count() == 0


def test_rows_when_open(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """行を押すと、パネルの中をそのスレッドの画面に切り替える。まだ送っていない新しいスレッドも開く（履歴に積まない）（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    history_length = page.evaluate("history.length")
    open_list(page)
    # 実行・検証（送ったスレッド）
    page.click(f"{thread_row('TH-2')} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    assert page.inner_text(f"{COMMENTS_PANEL} .th-heading") == "オープン\n二つ目の要約"
    page.get_by_role("button", name="一覧へ戻る").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-filter")
    # 実行・検証（まだ送っていない新しいスレッド）
    page.click(f"{thread_row('new:C-41')} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    assert page.inner_text(f"{COMMENTS_PANEL} .th-heading") == "レビュー中\n写しは git で取る"
    assert page.evaluate("history.length") == history_length


def test_empty(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """スレッドが 0 件のときは、印と絞り込みを含めた文言を出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"))
    page = open_preview(url)
    # 実行
    open_list(page)
    # 検証
    assert page.inner_text(EMPTY) == "オープンのスレッドはありません。"
    assert page.locator(f"{EMPTY} svg.icon").count() == 1
    # クローズ
    page.click(f"{SEGMENTS}[data-focus='filter:closed']")
    assert page.inner_text(EMPTY) == "クローズのスレッドはありません。"
    page.click(f"{SEGMENTS}[data-focus='filter:all']")
    assert page.inner_text(EMPTY) == "スレッドはありません。"


def test_empty_when_tag(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """タグで絞って該当が無いときは、頭に「タグ「{タグ}」の」を付けた文言を出す（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    open_list(page)
    page.click(f"{thread_row('TH-2')} button.th-tag")
    # 実行（タグを持たないスレッドだけを残してクローズへ切り替える）
    page.click(f"{SEGMENTS}[data-focus='filter:closed']")
    # 検証
    assert page.inner_text(EMPTY) == "タグ「調査」のクローズのスレッドはありません。"


def test_unreachable(
    served_threads: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """スレッドを読めなかったときは理由を出し、まだ送っていない新しいスレッドは並べる。次に読めたら消す（異常系）。"""
    # 準備
    url, _ = served_threads
    page.route("**/api/threads", lambda route: route.abort())
    open_preview(url)
    # 実行
    open_list(page)
    # 検証
    page.wait_for_selector(f"{COMMENTS_PANEL} [role='alert']", timeout=UPDATE_TIMEOUT_MS)
    assert (
        page.inner_text(f"{COMMENTS_PANEL} [role='alert']")
        == "スレッドを読めませんでした。サーバーが止まっています。立ち上げ直してから開いてください。"
    )
    assert page.locator(f"{COMMENTS_PANEL} svg.icon").count() >= 1
    assert page.locator(f"{thread_row('new:C-41')}").count() == 1
    assert page.locator(f"{thread_row('TH-1')}").count() == 0


def test_unreachable_when_invalid(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_thread: MakeThread,
) -> None:
    """読めない threads.yaml は、サーバーが返した理由を出す（異常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"), threads=(make_thread("TH-1"),))
    threads_file = root / RECORD_DIR / "threads.yaml"
    data = yaml.safe_load(threads_file.read_text(encoding="utf-8"))
    del data["items"][0]["posts"]
    threads_file.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    page = open_preview(url)
    # 実行
    open_list(page)
    # 検証
    page.wait_for_selector(f"{COMMENTS_PANEL} [role='alert']", timeout=UPDATE_TIMEOUT_MS)
    text = page.inner_text(f"{COMMENTS_PANEL} [role='alert']")
    assert text.startswith("スレッドを読めませんでした。")
    assert "threads.yaml" in text


def test_compose(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「新しいスレッド」で入力を出して入力欄へフォーカスを移し、溜めるとまだ送っていない新しいスレッドとして先頭に足して、件数を描き直す。この画面に留まる（正常系）。"""
    # 準備
    url, root = served_threads
    page = open_preview(url)
    open_list(page)
    # 実行
    page.click(COMPOSE_BUTTON)
    page.wait_for_selector(COMPOSE_TEXTAREA)
    # 検証（入力）
    assert page.get_attribute(COMPOSE_TEXTAREA, "aria-label") == "新しいスレッド"
    wait_until_focused(page, COMPOSE_TEXTAREA)
    # 実行（溜める）
    page.fill(COMPOSE_TEXTAREA, "全体への相談")
    page.locator(f"{COMMENTS_PANEL} .talk-new").get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(thread_row("new:C-44"), timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{thread_row('new:C-44')} .th-title") == "全体への相談"
    # まだ送っていない新しいスレッドは溜めた順に、送ったスレッドより前に並ぶ
    assert page.eval_on_selector_all(
        THREAD_ROWS, "rows => rows.map(r => r.querySelector('.th-state').textContent)"
    ) == ["レビュー中", "レビュー中", "オープン", "オープン"]
    assert page.eval_on_selector_all(
        f"{THREAD_ROWS} .th-title", "titles => titles.slice(0, 2).map(t => t.textContent)"
    ) == ["写しは git で取る", "全体への相談"]
    assert page.get_attribute(REVIEW_ENTRY, "aria-label") == "レビュー中の書き込みを確かめる（3 件）"
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "3"
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert saved[-1].get("thread") is None
    assert (saved[-1]["id"], saved[-1].get("target"), saved[-1]["body"]) == ("C-44", None, "全体への相談")


def test_compose_when_closed(served_threads: tuple[str, Path], open_preview: OpenPreview) -> None:
    """× で入力を畳んで「新しいスレッド」に戻し、書きかけは残す（正常系）。"""
    # 準備
    url, _ = served_threads
    page = open_preview(url)
    open_list(page)
    page.click(COMPOSE_BUTTON)
    page.fill(COMPOSE_TEXTAREA, "あとで書く")
    # 実行
    page.get_by_role("button", name="新しいスレッドの入力を閉じる").click()
    # 検証
    page.wait_for_selector(COMPOSE_BUTTON)
    assert page.locator(COMPOSE_TEXTAREA).count() == 0
    page.click(COMPOSE_BUTTON)
    assert page.input_value(COMPOSE_TEXTAREA) == "あとで書く"


def test_exclusive_with_filter_drawer(
    served_threads: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """絞り込みのドロワーとは同時に開かず、どちらかを開くと他方を閉じる。開いている間は覆った範囲の本文の部品を止める（正常系）。"""
    # 準備（一覧を開く）
    url, _ = served_threads
    page = open_preview(url, "#tab=decisions&view=table")
    open_list(page)
    page.wait_for_function(f"{INERT_COUNT_SCRIPT} > 0")
    list_open = (page.locator(DRAWER).count(), page.get_attribute(COMMENTS_BUTTON, "aria-expanded"))
    # 実行（ドロワーを開くと、一覧が閉じる）
    open_drawer(page)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open", state="detached")
    page.wait_for_function(f"{INERT_COUNT_SCRIPT} > 0")
    drawer_open = (
        page.locator(DRAWER_OPEN).count(),
        page.get_attribute(COMMENTS_BUTTON, "aria-expanded"),
        page.get_attribute(FILTER_BUTTON, "aria-expanded"),
    )
    # 実行（一覧を開くと、ドロワーが閉じる）
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.wait_for_selector(DRAWER, state="detached")
    list_again = (
        page.get_attribute(COMMENTS_BUTTON, "aria-expanded"),
        page.get_attribute(FILTER_BUTTON, "aria-expanded"),
    )
    # 実行（一覧を閉じると、止めた部品を戻す）
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open", state="detached")
    page.wait_for_function(f"{INERT_COUNT_SCRIPT} === 0")
    # 検証
    assert list_open == (0, "true")
    assert drawer_open == (1, "false", "true")
    assert list_again == ("true", "false")


def test_narrow_width(served_threads: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """幅 900px 以下は画面の幅いっぱいに出し、パネルから開いた詳細パネルを閉じるとパネルへ戻る（正常系）。"""
    # 準備
    url, _ = served_threads
    page.set_viewport_size({"width": NARROW_WIDTH, "height": VIEWPORT_HEIGHT})
    open_preview(url)
    # 実行
    open_list(page)
    # 検証
    width = page.evaluate(
        "document.querySelector('aside.comments-panel').getBoundingClientRect().width"
    )
    assert width == pytest.approx(NARROW_WIDTH, abs=1)
    page.click(f"{thread_row('TH-1')} button.th-open")
    page.click(f"{COMMENTS_PANEL} button.row-target[data-focus='target']")
    page.wait_for_selector("aside.panel.open")
    page.click("aside.panel button.panel-back")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert page.is_visible(COMMENTS_PANEL)


def test_updated_by_change(
    served_threads: tuple[str, Path], open_preview: OpenPreview, call_tool: CallTool
) -> None:
    """書き換えの知らせが届いたら、スレッドを読み直して描き直す（AI が立てたスレッドが並ぶ）（正常系）。"""
    # 準備
    url, root = served_threads
    page = open_preview(url)
    open_list(page)
    # 実行
    result = call_tool(
        "new_thread", workspace=str(root), body="起票してよいですか", summary="起票の確認", target="D-1"
    )
    # 検証
    assert result.data is not None
    page.wait_for_selector(thread_row(str(result.data["id"])), timeout=UPDATE_TIMEOUT_MS)
    assert page.inner_text(f"{thread_row(str(result.data['id']))} .th-author") == "AI"
    assert page.inner_text(f"{thread_row(str(result.data['id']))} .th-title") == "起票の確認"
