"""プレビューを開く（サーバーが配る URL と、`export` が書き出した配る書き出しを開く）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import yaml
from integration.browser_tab_helpers import (
    LINK_PAGE_TITLE,
    WINDOW_OPEN_RECORDER_JS,
    new_tab_after,
    opened_tabs,
    recorded_window_opens,
)
from playwright.sync_api import Download, Page, Route, expect
from preview_body_layout_helpers import (
    INLINE_NAME,
    LAYOUT_GROUP_NAME,
    LAYOUT_SWITCH,
    SIDE_HASH,
    SIDE_NAME,
    SIDE_VIEWPORT,
    build_body_layout_workspace,
    build_html_body_layout_workspace,
    layout_buttons,
    open_side_by_side,
    rows_of_columns,
    seed_side_layout,
)
from preview_body_link_helpers import (
    BODY_LINK_HASH,
    build_body_link_workspace,
)
from preview_body_link_helpers import (
    HEADING_IN_VIEW_JS as BODY_LINK_HEADING_IN_VIEW_JS,
)
from preview_body_view_helpers import (
    BODY_VIEW_SCOPE,
    open_body_view,
    seed_body_view,
    table_state,
)
from preview_comment_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    PILL,
    REVIEW_ENTRY,
    REVIEW_HEAD,
    THREE_LINE_BODY,
    open_review,
    open_thread,
    read_workspace_yaml,
    review_row,
    select_text,
    select_text_for_pill,
    thread_row,
    wait_thread_seen,
)
from preview_drawer_helpers import (
    FILTER_BUTTON,
    badge_text,
    checked_values,
    click_value,
    open_drawer,
)
from preview_embed_helpers import (
    CHART,
    CLIPBOARD_PERMISSIONS,
    EMBEDDED_BODY,
    EXPORT_BODY,
    EXPORT_ENTRY_NAME,
    EXPORT_MENU,
    MARKDOWN_EXPORT_BODY,
    MDMARK_URL_PATTERN,
    RANGE,
    ZOOM_FIT,
    ZOOM_IN,
    build_embedded_diff_workspace,
    drag_in_viewport,
    save_download,
    viewport_scroll,
)
from preview_edit_helpers import (
    DETAIL_PANEL as EDIT_PANEL,
    PENDING_BUTTON as EDIT_PENDING_BUTTON,
    SAVE_BUTTON as EDIT_SAVE_BUTTON,
    open_pending as open_edit_pending,
    read_items_file,
    reached_by_tab,
)
from preview_fixture_types import (
    BODY_WITH_DIAGRAM,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
)
from preview_history_helpers import preselect_diff
from preview_markdown_post_helpers import MARKDOWN_POST_HASH
from preview_post_link_helpers import POST_LINK_HASH
from preview_html_body_helpers import (
    BODY_FRAME,
    BODY_WITH_HTML_CODE_BLOCK,
    BODY_WITHOUT_HTML_CODE_BLOCK,
    FRAME_SETTLE_MS,
    LEAKING_HTML_BODY,
    MARKED_FRAME,
    drag_select_in_frame,
    frame_fit,
    frame_of,
    leak_counts,
    select_in_frame,
    style_snapshot,
    text_rect_in_page,
    wait_frame_rendered,
)
from preview_html_link_helpers import frame_location, html_with_links
from preview_mark_helpers import MARK_TIMEOUT_MS, SCREEN_MARKS, marks_of
from preview_minimap_helpers import (
    MINIMAP_HASH,
    PANEL_SCOPE,
    added_paragraph_in_view,
    drag_view,
    hide_minimap_in_storage,
    map_metrics,
    mark_at_empty_area,
    mark_shapes,
    marks_of_map,
    open_minimap,
    press_empty_area,
    scroll_top,
)
from preview_network_helpers import ball_at, canvas_center
from preview_panel_width_helpers import (
    PANEL as WIDTH_PANEL,
    RESIZER,
    PANEL_VIEWPORT,
    open_panel,
    panel_state,
    press_key_times,
    read_stored_width,
    seed_panel_width,
    wait_for_value_now,
)
from preview_saved_filter_helpers import (
    read_saved_filters,
    reload_preview,
    seed_saved_filters,
)
from preview_settings_helpers import (
    SETTINGS_PANEL,
    open_settings,
    panel_text,
    read_prefs,
)
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeComment,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    StartServer,
    WriteComments,
)

# 描画のライブラリの配信元への要求（全て失敗させるときの URL の形）
LIBRARY_HOST_PATTERN = "https://cdn.jsdelivr.net/**"

# 描画のライブラリを描いた後の図（SVG）が出るまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 書き換えや接続の切れが画面に出るまで待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# タブを移ったネットワークで、選んだ項目の玉が中心へ寄り終わるまで待つミリ秒
TAB_MOVE_SETTLE_MS = 5_000

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 400

# コメントの入力欄・結果・「レビューに追加」のボタン・接続の状態
SEND_TEXTAREA = "aside.panel form.send textarea"
SEND_MESSAGE = "aside.panel form.send .send-msg"
SEND_BUTTON = "aside.panel form.send button[type=submit]"
CONNECTION = "header.topbar .conn"

# サーバーにつながらないとき、接続の状態の全文が出る幅（幅 1440px 以下は短い文言になる）
WIDE_SIZE = {"width": 1441, "height": 900}

# 変更履歴のモーダルと検索のダイアログ・差分の札・札の × のボタン
HISTORY_DIALOG = "dialog.hist"
SEARCH_DIALOG = "dialog.search"
DIFF_CHIP = ".df-chip"
DIFF_CHIP_TITLE = ".df-chip-t"
DIFF_OFF_NAME = "差分の表示をやめる"

# 端末の保存領域に残した選んだ時点を読む
SAVED_DIFF_JS = "JSON.parse(localStorage.getItem('mindmap-preview') || '{}').diffSel ?? null"

# 時点を指すハッシュの書き換えと再描画を待つ上限ミリ秒
DIFF_SETTLE_MS = 10_000

# 溜めたコメントを受け付けるパス
COMMENTS_PATH = "/api/comments"

# コメントの一覧の送る帯の「まとめて送る」
LIST_SEND_BUTTON = f"{COMMENTS_PANEL} .send-band button.btn.primary"


# `file:` 以外の URL への要求（外への要求）を全て拾う条件
def _is_not_file_url(url: str) -> bool:
    """`file:` で始まらない URL かを返す。"""
    return not url.startswith("file:")


def _row_ids(page: Any) -> list[str]:
    """表に並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")


def test_normal(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュが指す画面・表示形式・項目を開く（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1"),
        make_item("D-3", status="要見直し", body="D-3.md"),
        bodies={"D-3.md": BODY_WITH_DIAGRAM},
    )
    hash_text = "#tab=decisions&view=table&id=D-3"
    # 実行
    page = open_preview(url, hash_text)
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.get_attribute('.segment button[data-view="table"]', "aria-pressed") == "true"
    assert _row_ids(page) == ["D-1", "D-3"]
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    assert page.locator("aside.panel .md:not(.md-value).mdmark").count() == 1
    assert page.locator("aside.panel .md:not(.md-value) h4").count() == 1
    assert page.locator("aside.panel .mermaid svg").count() == 1
    # 同じ URL を開き直すと同じ画面と項目が開く
    page.reload()
    page.wait_for_selector("aside.panel.open .d-title")
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.get_attribute('.segment button[data-view="table"]', "aria-pressed") == "true"
    assert page.inner_text("aside.panel .d-title") == "D-3の題"


def test_normal_when_no_hash(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュが無いと概要を開く（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    # 実行
    page = open_preview(url)
    # 検証
    assert page.get_attribute('nav.tabbar a[data-tab="overview"]', "aria-current") == "page"
    assert page.locator("aside.panel").count() == 0
    assert "#" not in page.url


def test_normal_when_filter_in_hash(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュの f.{列} で絞った表を、条件のチップ付きで開く（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="未決定"),
        make_item("D-3", status="要見直し"),
        make_item("D-4", status="保留"),
    )
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&f.status=要見直し|保留")
    # 検証
    chips = page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")
    assert chips == ["状態: 要見直し", "状態: 保留"]
    assert _row_ids(page) == ["D-3", "D-4"]
    # 開いた後は、ハッシュから f. の引数が消えている
    assert "f." not in page.evaluate("location.hash")
    # 絞り込みのドロワーは、状態で要見直し・保留だけが選ばれ、絞り込みのボタンにバッジ 1 が付く
    open_drawer(page)
    assert checked_values(page, "status") == ["要見直し", "保留"]
    assert badge_text(page) == "1"
    page.click(FILTER_BUTTON)
    page.wait_for_selector("dialog.drawer", state="detached")
    # チップを解除すると、D-1 の行も出る
    page.click(".chips >> text=すべて解除")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr').length === 3")
    assert _row_ids(page) == ["D-1", "D-3", "D-4"]
    assert "f." not in page.evaluate("location.hash")


def test_normal_when_tab_moved_with_item(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """詳細パネルに項目を開いたままタブの帯でネットワークへ移ると、その項目を選んだネットワークを開く。戻ると検討事項と詳細パネルに戻る（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"), make_item("D-3"))
    page = open_preview(url, "#tab=decisions&id=D-3")
    page.wait_for_selector("aside.panel.open")
    # 実行（タブの帯のネットワークを押す）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    page.wait_for_timeout(TAB_MOVE_SETTLE_MS)
    moved_hash = page.evaluate("location.hash")
    moved_panel = page.inner_text("aside.panel .d-title")
    selected_at_center = ball_at(page, *canvas_center(page))
    # 実行（ブラウザの戻る）
    page.go_back()
    page.wait_for_selector("#decision-map, table.grid, .board")
    # 検証
    assert moved_hash == "#tab=graph&id=D-3"
    assert page.get_attribute('nav.tabbar a[data-tab="graph"]', "aria-current") is None
    assert moved_panel == "D-3の題"
    # 選んだ項目の玉が中心へ寄る
    assert selected_at_center is True
    assert page.evaluate("location.hash") == "#tab=decisions&id=D-3"
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.inner_text("aside.panel .d-title") == "D-3の題"


def test_normal_when_item_not_found(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """記録に無い ID を指すハッシュでは、画面だけを開く（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-99")
    # 検証
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.get_attribute('.segment button[data-view="board"]', "aria-pressed") == "true"
    assert page.locator("aside.panel").count() == 0
    assert "id=" not in page.evaluate("location.hash")


def test_normal_when_exported_offline(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Any,
    tmp_path: Path,
) -> None:
    """描画のライブラリを中に持つ配る書き出しは、通信が無くても本文・図・マップを描く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-3", status="要見直し", body="D-3.md"), bodies={"D-3.md": BODY_WITH_DIAGRAM}
    )
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    # `file:` 以外への要求を全て失敗させ、数える
    blocked: list[str] = []

    def _block(route: Any) -> None:
        """外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    page.route(_is_not_file_url, _block)
    # 実行
    open_preview(out.as_uri(), "#tab=decisions&view=map&id=D-3")
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    assert blocked == []
    assert page.locator('[role="alert"]').count() == 0
    assert page.locator('#decision-map button[data-node="D-3"]').count() == 1
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    assert page.locator("aside.panel .md:not(.md-value) h4").count() == 1
    assert page.locator("aside.panel .mermaid svg").count() == 1
    # コメントのボタン・入力・選んだ箇所の入口が無く、接続の状態も出ていない
    assert page.locator(COMMENTS_BUTTON).count() == 0
    assert page.locator("aside.panel form.send").count() == 0
    assert page.locator(SEND_TEXTAREA).count() == 0
    assert page.locator(SEND_BUTTON).count() == 0
    assert page.locator(CONNECTION).count() == 0
    select_text(page, "aside.panel .md:not(.md-value)", "本文の段落")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    assert page.locator(PILL).count() == 0


def test_normal_when_exported_filter_changed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しは、絞り込みの条件を変えても端末に残さず、読み込み直すと画面の既定の条件で開く（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1", status="進行中"), make_item("T-2", status="完了"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    page = open_preview(out.as_uri(), "#tab=tasks&view=table")
    open_drawer(page)
    click_value(page, "status", "進行中")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 1")
    rows_filtered = _row_ids(page)
    # 実行
    reload_preview(page)
    saved = read_saved_filters(page) or {}
    rows_reloaded = _row_ids(page)
    badge_reloaded = badge_text(page)
    open_drawer(page)
    # 検証
    assert rows_filtered == ["T-1"]
    assert rows_reloaded == ["T-1", "T-2"]
    assert badge_reloaded is None
    assert checked_values(page, "status") == []
    assert saved.get("tasks") is None


def test_normal_when_exported_with_saved_filter(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しは、端末の個人の上書きに絞り込みの条件があっても当てず、画面の既定の条件で開く（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1", status="進行中"), make_item("T-2", status="完了"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    page = open_preview(out.as_uri(), "#tab=tasks&view=table")
    seed_saved_filters(page, {"tasks": {"status": ["進行中"]}})
    # 実行
    reload_preview(page)
    rows = _row_ids(page)
    badge = badge_text(page)
    open_drawer(page)
    # 検証
    assert rows == ["T-1", "T-2"]
    assert badge is None
    assert checked_values(page, "status") == []


def test_error_when_library_unavailable(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Any,
) -> None:
    """描画のライブラリの配信元に届かないと、使う箇所に読み込めなかったライブラリの名前を出す（異常系）。"""
    # 準備
    url = write_preview(
        make_item("D-3", status="要見直し", body="D-3.md"), bodies={"D-3.md": BODY_WITH_DIAGRAM}
    )
    page.route(LIBRARY_HOST_PATTERN, lambda route: route.abort())
    # 実行
    open_preview(url, "#tab=decisions&view=map&id=D-3")
    page.wait_for_selector("aside.panel.open .md:not(.md-value) .lib-error")
    # 検証
    map_notice = page.inner_text("main .lib-error[role=alert]")
    assert "読み込めなかったライブラリ: elkjs" in map_notice
    assert "通信を確認して、ページを再読み込みしてください。" in map_notice
    body_notice = page.inner_text("aside.panel .md:not(.md-value) .lib-error[role=alert]")
    assert "読み込めなかったライブラリ" in body_notice
    for name in ("mdmark", "mermaid"):
        assert name in body_notice
    assert "marked" not in body_notice
    assert "DOMPurify" not in body_notice
    assert "本文の段落" in page.inner_text("aside.panel .md-raw")
    # 配置できない案内は、表への切り替えを促す
    assert "表示形式を「表」に切り替えると、検討事項を表示できます。" in page.inner_text("main")
    # 表示形式を表に切り替えると、D-3 の行がある
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid tbody tr")
    assert _row_ids(page) == ["D-3"]


def test_normal_when_rewritten(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Any,
) -> None:
    """ツールで書き換えると、開いている画面と項目を保ったまま描き直す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-3", status="要見直し"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(served.data["url"], "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel.open .d-title")
    page.fill(SEND_TEXTAREA, "書きかけ")
    opened_url = page.url
    history_length = page.evaluate("history.length")
    new_decision = {
        "title": "新しい問い",
        "target": "mindmap",
        "category": "データ構造",
        "phase": "要件",
        "status": "未決定",
        "options": [{"key": "A", "content": "案 A"}],
    }
    # 実行
    added = call_tool("add", workspace=str(root), kind="decision", item=new_decision)
    # 検証
    assert added.is_error is False, added.text
    page.wait_for_function(
        "document.querySelectorAll('table.grid tbody tr').length === 3", timeout=UPDATE_TIMEOUT_MS
    )
    assert _row_ids(page) == ["D-1", "D-3", "D-4"]
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.get_attribute('.segment button[data-view="table"]', "aria-pressed") == "true"
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    assert page.input_value(SEND_TEXTAREA) == "書きかけ"
    assert page.url == opened_url
    assert page.evaluate("history.length") == history_length


def test_normal_when_sent(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Any,
) -> None:
    """本文の文を選んで箇所を添えたコメントを溜め、コメントの一覧からまとめて送る（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(served.data["url"], "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md:not(.md-value)")
    # 実行（本文の 2 行目の文を選ぶと、近くに入口が出る）
    select_text_for_pill(page, "aside.panel .md:not(.md-value)", "言い換えたい文")
    # 実行（入口を押し、箇所を添えて溜める）
    page.click(PILL)
    # 検証（箇所を添えた入力）
    assert page.inner_text("aside.panel .send-loc-name") == "本文 2 行目"
    assert page.inner_text("aside.panel .send-quote") == "言い換えたい文"
    assert page.evaluate("document.activeElement.matches('form.send textarea')") is True
    page.fill(SEND_TEXTAREA, "ここは言い換える")
    # 入力欄から Tab キーで「レビューに追加」に届く（箇所を外すの × を経て、追加のボタンへ）
    page.focus(SEND_TEXTAREA)
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.matches('form.send button[type=submit]')") is True
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{SEND_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    # 検証（溜めた後）
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"
    assert page.inner_text("aside.panel .d-review .review-body") == "ここは言い換える"
    assert page.inner_text("aside.panel .d-review .review-loc-name") == "本文 2 行目"
    # 実行（コメントのボタンから一覧を開き、まとめて送る）
    page.focus(COMMENTS_BUTTON)
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    page.focus(LIST_SEND_BUTTON)
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{COMMENTS_PANEL} .send-msg.sent", timeout=UPDATE_TIMEOUT_MS)
    # 検証（送った後）
    threads = read_workspace_yaml(root, "threads.yaml")["items"]
    assert [
        (thread["target"], thread["loc"]["kind"], thread["loc"]["start"], thread["posts"][0]["body"])
        for thread in threads
    ] == [("A-1", "body", 2, "ここは言い換える")]
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "0"
    assert page.locator(f"{COMMENTS_PANEL} .comments-list li").count() == 0
    # 検証（入口は Esc で閉じる）
    # 送った後の記録の読み直しと描き直しが終わってから選ぶ（遅れて描き直されると、選んだ範囲と入口が外れる）
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    select_text_for_pill(page, "aside.panel .md:not(.md-value)", "言い換えたい文")
    page.focus(PILL)
    page.keyboard.press("Escape")
    assert page.locator(PILL).count() == 0
    assert page.locator("aside.panel.open").count() == 1


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Any,
) -> None:
    """空白だけの本文は溜めずに、理由を出す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    posts: list[str] = []
    page.on(
        "request",
        lambda request: (
            posts.append(request.url)
            if request.method == "POST" and request.url.endswith(COMMENTS_PATH)
            else None
        ),
    )
    open_preview(served.data["url"], "#tab=decisions&id=D-1")
    page.wait_for_selector(SEND_TEXTAREA)
    page.fill(SEND_TEXTAREA, "   ")
    # 実行
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.empty", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert posts == []
    assert "コメントを入れてから追加してください。" in page.inner_text(SEND_MESSAGE)


def test_error_when_server_unreachable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Any,
) -> None:
    """サーバーが止まると接続の状態を出し、前に読んだ記録で描き続け、溜められなかった本文を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-3", status="要見直し"))
    server = start_server()
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    page.set_viewport_size(WIDE_SIZE)
    open_preview(served.data["url"], "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel.open .d-title")
    # 実行（サーバーの標準入力を閉じて止める）
    server.close_stdin()
    server.wait_exit()
    page.wait_for_selector(CONNECTION, timeout=UPDATE_TIMEOUT_MS)
    page.fill(SEND_TEXTAREA, "案 A にする")
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.failed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    connection = page.inner_text(CONNECTION)
    assert "サーバーにつながりません" in connection
    assert "に読んだ記録" in connection
    assert _row_ids(page) == ["D-1", "D-3"]
    assert page.inner_text("aside.panel .d-title") == "D-1の題"
    assert "レビューに追加できませんでした" in page.inner_text(SEND_MESSAGE)
    assert page.input_value(SEND_TEXTAREA) == "案 A にする"


def test_normal_when_comment_marks_not_shown(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しは、レビュー中のコメントがあっても、ボード・表のどちらにもコメントの印と印を置く場所を出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-2", status="未決定"))
    write_comments(root, make_comment("C-1", target="D-2"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    # 実行・検証
    for view in ("board", "table"):
        page = open_preview(out.as_uri(), f"#tab=decisions&view={view}")
        page.wait_for_selector(".board button.card, table.grid tbody tr")
        assert page.locator("[data-comment-target]").count() == 0
        assert page.locator(".cmk").count() == 0


def _card_marker_script(selector: str) -> str:
    """要素に目印の値を付け、画面を描き直したかを後で確かめられるようにする JavaScript を返す。"""
    return f"document.querySelector('{selector}').dataset.kept = 'yes'"


def test_normal_when_comment_added(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview, page: Any
) -> None:
    """詳細パネルからコメントを溜めると、その項目の印だけが描き替わり、画面は描き直さない（正常系）。"""
    # 準備
    url, _ = write_commented_preview()
    open_preview(url, "#tab=decisions&view=board&id=D-4")
    page.wait_for_selector("aside.panel.open")
    assert marks_of(page) == SCREEN_MARKS["decisions"]
    page.evaluate(_card_marker_script('.board button.card[data-id="D-2"]'))
    page.evaluate("document.querySelector('.board').scrollLeft = 20")
    scroll = page.evaluate("document.querySelector('.board').scrollLeft")
    # 実行
    page.fill(SEND_TEXTAREA, "期日を決める")
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_function(
        "document.querySelector('.board button.card[data-id=\"D-4\"] .cmk') !== null",
        timeout=MARK_TIMEOUT_MS,
    )
    # 検証
    assert marks_of(page) == {**SCREEN_MARKS["decisions"], "D-4": "1"}
    # 描き直していない（目印とスクロールの位置が残る）
    assert page.get_attribute('.board button.card[data-id="D-2"]', "data-kept") == "yes"
    assert page.evaluate("document.querySelector('.board').scrollLeft") == scroll


def test_normal_when_comment_removed_and_sent(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview, page: Any
) -> None:
    """コメントの一覧で消すと件数が減り、全て送ると印が全て消える。消すだけでは画面を描き直さない（正常系）。"""
    # 準備
    url, _ = write_commented_preview()
    open_preview(url, "#tab=decisions&view=board")
    page.wait_for_selector(".board button.card")
    page.evaluate(_card_marker_script('.board button.card[data-id="D-3"]'))
    open_review(page)
    # 実行（C-1 を消すと D-2 の件数が 2 から 1 になる）
    page.locator(f"{COMMENTS_PANEL} li[data-comment='C-1']").get_by_role(
        "button", name="D-2 へのコメントを削除"
    ).click()
    page.wait_for_function(
        "document.querySelector('.board button.card[data-id=\"D-2\"] .cmk-n').textContent === '1'",
        timeout=MARK_TIMEOUT_MS,
    )
    # 検証（消した後）
    assert marks_of(page) == {"D-2": "1", "D-3": "1"}
    assert page.get_attribute('.board button.card[data-id="D-3"]', "data-kept") == "yes"
    # 実行（全て送ると、印を置く場所が空になる）
    page.click(LIST_SEND_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL} .send-msg.sent", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_function(
        "document.querySelectorAll('.board .cmk').length === 0", timeout=MARK_TIMEOUT_MS
    )
    # 検証（送った後）
    assert marks_of(page) == {}
    assert page.locator(".board [data-comment-target]:not(:empty)").count() == 0


# マップの拡大の倍率と、枠のスクロールの位置を返す
MAP_VIEW_SCRIPT = """() => ({
    transform: document.getElementById('decision-map').style.transform,
    left: document.querySelector('.map-wrap').scrollLeft,
    top: document.querySelector('.map-wrap').scrollTop,
})"""

# マップの描きが落ち着くまで待つミリ秒
MAP_SETTLE_MS = 800


def test_normal_when_comment_added_on_map(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview, page: Any
) -> None:
    """マップを開いたままコメントを溜めても、節点の印だけが描き替わり、マップの拡大と位置は変わらない（正常系）。"""
    # 準備
    url, _ = write_commented_preview()
    open_preview(url, "#tab=decisions&view=map&id=D-4")
    page.wait_for_selector("aside.panel.open")
    page.wait_for_selector("#decision-map .map-node.n-item")
    page.wait_for_timeout(MAP_SETTLE_MS)
    page.evaluate(_card_marker_script('#decision-map .map-node[data-node="D-2"]'))
    before = page.evaluate(MAP_VIEW_SCRIPT)
    # 実行
    page.fill(SEND_TEXTAREA, "期日を決める")
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_function(
        "document.querySelector('#decision-map .map-node[data-node=\"D-4\"] .cmk') !== null",
        timeout=MARK_TIMEOUT_MS,
    )
    page.wait_for_timeout(MAP_SETTLE_MS)
    # 検証
    assert marks_of(page, "#decision-map") == {**SCREEN_MARKS["decisions"], "D-4": "1"}
    assert page.get_attribute('#decision-map .map-node[data-node="D-2"]', "data-kept") == "yes"
    assert page.evaluate(MAP_VIEW_SCRIPT) == before


def test_normal_when_comment_added_on_graph(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview, page: Any
) -> None:
    """ネットワークを開いたままコメントを溜めると、キャンバスを作り直さず、次のコマから新しい件数の印を出す（正常系）。"""
    # 準備
    url, _ = write_commented_preview()
    open_preview(url, "#tab=graph&id=D-2")
    page.wait_for_selector("aside.panel.open")
    shown_mark = (
        "[...document.querySelectorAll('.g3-marks .cmk')]"
        ".filter(m => m.style.visibility !== 'hidden')"
        ".map(m => m.querySelector('.cmk-n').textContent)"
    )
    page.wait_for_function(f"{shown_mark}.includes('2')", timeout=MARK_TIMEOUT_MS)
    page.evaluate("document.getElementById('graph-canvas').dataset.kept = 'yes'")
    # 実行（選んでいる D-2 に 1 件足すと、印の件数が 2 から 3 になる）
    page.fill(SEND_TEXTAREA, "期日を決める")
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    page.wait_for_function(f"{shown_mark}.includes('3')", timeout=MARK_TIMEOUT_MS)
    assert page.evaluate(f"{shown_mark}.includes('2')") is False
    assert page.get_attribute("#graph-canvas", "data-kept") == "yes"


# 見出し「保存先」「決め方」「決め方」の間に、窓に収まらない数の段落を置いた本文
HEADING_BODY = (
    "## 保存先\n\n"
    + "\n\n".join(f"保存先の段落 {number}" for number in range(1, 31))
    + "\n\n## 決め方\n\n"
    + "\n\n".join(f"1 つ目の決め方の段落 {number}" for number in range(1, 31))
    + "\n\n## 決め方\n\n2 つ目の決め方の段落\n"
)

# 詳細パネルの本文のスクロール領域
PANEL_BODY = "aside.panel .panel-body"

# 見出しが本文の領域の中で画面に入っているかを返す
HEADING_IN_VIEW_JS = """(slug) => {
    const body = document.querySelector('aside.panel .panel-body');
    const target = document.querySelector(`[data-heading="${slug}"]`);
    const area = body.getBoundingClientRect();
    const box = target.getBoundingClientRect();
    return box.top >= area.top - 1 && box.bottom <= area.bottom + 1;
}"""


def test_normal_when_text_filter_in_hash(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュの f.~{列} で、その列の値に文字を含む行に絞って開く。文字の中の `|` で分けない。開いた後はハッシュから外れる（正常系）。"""
    # 準備
    url = write_preview(
        make_item("G-1", title="a|b の用語"),
        make_item("G-2", title="a の用語"),
        make_item("G-3", title="b の用語"),
    )
    # 実行
    page = open_preview(url, "#tab=terms&f.~title=a|b")
    # 検証
    assert _row_ids(page) == ["G-1"]
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == [
        "用語に「a|b」を含む"
    ]
    assert "f." not in page.evaluate("location.hash")


def test_normal_when_heading_in_hash(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュの h が指す本文の見出しまで送って開く。見出しの # を押すと h をその見出しにし、履歴に積まない。本文に無い見出しなら本文の頭で開き、h を外す（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": HEADING_BODY})
    # 実行（2 つ目の「決め方」を指して開く）
    page = open_preview(url, "#tab=docs&view=table&id=A-1&h=決め方-1")
    page.wait_for_selector(f"{PANEL_BODY} [data-heading]")
    page.wait_for_function("document.querySelector('aside.panel .panel-body').scrollTop > 0")
    in_view = page.evaluate(HEADING_IN_VIEW_JS, "決め方-1")
    first_not_in_view = page.evaluate(HEADING_IN_VIEW_JS, "保存先")
    history_length = page.evaluate("history.length")
    # 実行（1 つ目の「決め方」の # を押す）
    page.click('aside.panel [data-heading="決め方"] .h-link')
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'")
    # 検証
    assert panel_title_of(page) == "A-1の題"
    assert in_view is True
    assert first_not_in_view is False
    assert page.evaluate("history.length") == history_length
    assert page.evaluate(HEADING_IN_VIEW_JS, "決め方") is True
    # 実行（本文に無い見出しで開き直す）
    page.goto(f"{url}#tab=docs&view=table&id=A-1&h=無い見出し")
    page.wait_for_selector(f"{PANEL_BODY} [data-heading]")
    page.wait_for_function("!new URLSearchParams(location.hash.slice(1)).has('h')")
    assert page.evaluate(f"document.querySelector('{PANEL_BODY}').scrollTop") == 0


def panel_title_of(page: Any) -> str:
    """詳細パネルのタイトル（項目の題）を返す。"""
    return page.inner_text("aside.panel .d-title")


# 詳細パネルのタイトル・トップバー（本文を描く前後で色と余白を比べる要素）
PANEL_TITLE = "aside.panel .d-title"
TOPBAR = "header.topbar"

# 詳細パネルの本文の前後の段落（Markdown）
MARKDOWN_PARAGRAPHS = "aside.panel .md:not(.md-value) p"

# 段落より前にコメントと `<style>` を置き、5〜6 行目に 2 行にまたがる段落を持つ HTML の本文
COMMENT_HTML_BODY = (
    "<!-- 下書き -->\n"
    "<style>p { color: rgb(51, 51, 51); }</style>\n"
    "<h1>画面のモック</h1>\n"
    "\n"
    "<p>前置きの文\n"
    "言い換えたい文</p>\n"
)

# 行がずれやすい文を持つ HTML の本文（1〜3 行目は入れ子の複数行の開きタグ、4 行目は `<br>`、5・6 行目は `<pre>`）
LINE_EDGE_HTML_BODY = (
    "<p>前置き <span\n"
    '  class="x">強調</span>\n'
    "言い換えたい文</p>\n"
    "<p>a<br>別の文</p>\n"
    "<pre>\n"
    "整形した文</pre>\n"
)

# 段落 3 つを 1 行ずつ持つ HTML の本文と、2 つ目の段落を書き換えた本文
THREE_PARAGRAPH_HTML = "<p>1 つ目の段落</p>\n<p>2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"
THREE_PARAGRAPH_HTML_REWRITTEN = (
    "<p>1 つ目の段落</p>\n<p>書き直した 2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"
)

# 複数行にまたがる開きタグ（`<b` の次の行で閉じる）を中に持つ段落（1〜5 行目）と、小見出しの後ろに地の文を持つ節（6〜9 行目）。書き換えるのは 4 行目と 8 行目
CLOSED_ELEMENT_HTML = (
    "<div>\n"
    '<p>見出し <b\n   class="k">強調</b>\n'
    "続きの文</p>\n"
    "</div>\n"
    "<section>\n"
    "<h2>小見出し</h2>\n"
    "節の文\n"
    "</section>\n"
)
CLOSED_ELEMENT_HTML_REWRITTEN = (
    "<div>\n"
    '<p>見出し <b\n   class="k">強調</b>\n'
    "書き直した続きの文</p>\n"
    "</div>\n"
    "<section>\n"
    "<h2>小見出し</h2>\n"
    "書き直した節の文\n"
    "</section>\n"
)

# 差分の印と、凡例の「変わった」の印
CHANGED_MARK_SELECTOR = '[data-df="chg"]'

# 時点を外すボタンと、「原文の差分」の切り替え
RAW_DIFF_BUTTON = "原文の差分"
DIFF_OFF_BUTTON = "差分の表示をやめる"


def test_normal_when_html_body(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """HTML の本文をスクリプトを動かさない枠に描き、本文の CSS を画面へ漏らさない（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", body="A-1.html"),
        make_item("A-2"),
        bodies={"A-1.html": LEAKING_HTML_BODY, "A-2.md": "資料の本文\n"},
    )
    # 描く前の見本として、Markdown の本文の資料のタイトルとトップバーを測る
    page = open_preview(url, "#tab=docs&id=A-2")
    page.wait_for_selector("aside.panel.open .d-title")
    before = style_snapshot(page, [PANEL_TITLE, TOPBAR])
    # 実行
    page.evaluate("location.hash = '#tab=docs&id=A-1'")
    wait_frame_rendered(page, BODY_FRAME)
    frame = frame_of(page, BODY_FRAME)
    frame.click("#click")
    page.wait_for_timeout(FRAME_SETTLE_MS)
    # 検証
    assert page.get_attribute(BODY_FRAME, "sandbox") == "allow-same-origin"
    assert frame.locator("h1").count() == 1
    assert frame.locator("table").count() == 1
    assert frame.locator("svg").count() == 1
    assert leak_counts(page, BODY_FRAME) == {"parent": 0, "frame": 0}
    assert style_snapshot(page, [PANEL_TITLE, TOPBAR]) == before
    fit = frame_fit(page, BODY_FRAME)
    assert fit["bottom"] <= fit["height"]
    assert fit["later_height"] == fit["height"]
    # 詳細パネルにも詳細の全画面にも、「エクスポート」の入口が無い
    assert page.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True).count() == 0
    page.click('aside.panel button[data-act="full"]')
    page.wait_for_selector("dialog.full[open]")
    assert page.locator("dialog.full").get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True).count() == 0


def test_normal_when_html_body_commented(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """枠の中で選んだ文を元の HTML の行の範囲にして、箇所を添えたコメントを溜める（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": COMMENT_HTML_BODY}
    )
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    # 実行
    drag_select_in_frame(page, BODY_FRAME, "言い換えたい文")
    page.wait_for_selector(PILL, timeout=UPDATE_TIMEOUT_MS)
    rect = text_rect_in_page(page, BODY_FRAME, "言い換えたい文")
    pill_box = page.locator(PILL).bounding_box()
    page.get_by_role("button", name="選んだ箇所にコメント").click()
    # 検証（入口の位置: 入口の下端が選んだ文の上端より上にあり、その差が選んだ行の高さ以内）
    assert pill_box is not None
    gap = rect["top"] - (pill_box["y"] + pill_box["height"])
    assert 0 < gap <= rect["height"]
    assert page.inner_text("aside.panel .send-loc-name") == "本文 6 行目"
    assert page.inner_text("aside.panel .send-quote") == "言い換えたい文"
    # 実行（溜める）
    page.fill(SEND_TEXTAREA, "ここは言い換える")
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    # 検証（溜めたコメント）
    saved = yaml.safe_load((root / RECORD_DIR / "comments.yaml").read_text(encoding="utf-8"))
    assert [item["loc"] for item in saved["items"]] == [
        {"kind": "body", "start": 6, "end": 6, "text": "言い換えたい文"}
    ]
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"


def test_normal_when_html_body_diff(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """時点を選ぶと描いた本文の変わった要素に印を付け、「原文の差分」で原文の行の差分に切り替える（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = str(root)
    item = {
        "title": "画面のモック",
        "kind": "モック",
        "status": "下書き",
        "deliverable": False,
        "body_html": THREE_PARAGRAPH_HTML,
    }
    assert call_tool("add", workspace=workspace, kind="doc", item=item).is_error is False
    assert call_tool("commit", workspace=workspace, summary="足す").is_error is False
    updated = call_tool(
        "update", workspace=workspace, id="A-1", item={"body_html": THREE_PARAGRAPH_HTML_REWRITTEN}
    )
    assert updated.is_error is False
    assert call_tool("commit", workspace=workspace, summary="直す").is_error is False
    url = str(call_tool("preview_url", workspace=workspace).data["url"])
    preselect_diff(page, "V-2")
    # 実行
    open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, MARKED_FRAME)
    frame = frame_of(page, MARKED_FRAME)
    # 検証（描いた本文: 2 つ目の段落だけに「変わった」の印が付く）
    marked = frame.eval_on_selector_all(
        "p", "ps => ps.map(p => [p.textContent, p.closest('[data-df]')?.dataset.df ?? null])"
    )
    assert marked == [
        ["1 つ目の段落", None],
        ["書き直した 2 つ目の段落", "chg"],
        ["3 つ目の段落", None],
    ]
    # 実行（原文の差分）
    page.get_by_role("button", name=RAW_DIFF_BUTTON).click()
    # 検証（原文の差分: 2 つ目の段落の原文の行が、消した行と足した行で出る）
    removed = page.inner_text("aside.panel .df-raw .df-line.df-del")
    added = page.inner_text("aside.panel .df-raw .df-line.df-add")
    assert "<p>2 つ目の段落</p>" in removed
    assert "<p>書き直した 2 つ目の段落</p>" in added
    assert "data-line" not in page.inner_text("aside.panel .df-raw")
    # 実行（時点を外す）
    page.get_by_role("button", name=DIFF_OFF_BUTTON).click()
    wait_frame_rendered(page, BODY_FRAME)
    # 検証
    assert frame_of(page, BODY_FRAME).locator("[data-df]").count() == 0


def test_normal_when_html_body_diff_after_closed_element(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """中の要素が閉じた後の行を書き換えると、差分の印を閉じた要素ではなく、その行を含む要素に付ける（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = str(root)
    item = {
        "title": "画面のモック",
        "kind": "モック",
        "status": "下書き",
        "deliverable": False,
        "body_html": CLOSED_ELEMENT_HTML,
    }
    assert call_tool("add", workspace=workspace, kind="doc", item=item).is_error is False
    assert call_tool("commit", workspace=workspace, summary="足す").is_error is False
    updated = call_tool(
        "update", workspace=workspace, id="A-1", item={"body_html": CLOSED_ELEMENT_HTML_REWRITTEN}
    )
    assert updated.is_error is False
    assert call_tool("commit", workspace=workspace, summary="直す").is_error is False
    url = str(call_tool("preview_url", workspace=workspace).data["url"])
    preselect_diff(page, "V-2")
    # 実行
    open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, MARKED_FRAME)
    # 検証
    marked = frame_of(page, MARKED_FRAME).eval_on_selector_all(
        "[data-df]", "els => els.map(e => [e.tagName, e.dataset.df])"
    )
    assert marked == [["P", "chg"], ["SECTION", "chg"]]


def test_normal_when_html_code_block(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
) -> None:
    """Markdown の本文の中の html のコードブロックを、コードではなくスクリプトを動かさない枠に描く（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1"),
        make_item("A-2"),
        bodies={"A-1.md": BODY_WITH_HTML_CODE_BLOCK, "A-2.md": BODY_WITHOUT_HTML_CODE_BLOCK},
    )
    # 描く前の見本として、コードブロックの無い本文の前後の段落の色を測る
    page = open_preview(url, "#tab=docs&id=A-2")
    page.wait_for_selector(MARKDOWN_PARAGRAPHS)
    before = page.eval_on_selector_all(
        MARKDOWN_PARAGRAPHS, "ps => ps.map(p => [getComputedStyle(p).color, getComputedStyle(p).margin])"
    )
    # 実行
    page.evaluate("location.hash = '#tab=docs&id=A-1'")
    code_frame = "aside.panel .md iframe.html-frame"
    wait_frame_rendered(page, code_frame)
    # 実行（枠の中の文を選ぶ）
    select_in_frame(page, code_frame, "枠の中の段落", "枠の中の段落")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    # 検証
    assert page.get_attribute(code_frame, "sandbox") == "allow-same-origin"
    assert page.locator("aside.panel .md pre code").count() == 0
    assert frame_of(page, code_frame).locator("p").inner_text() == "枠の中の段落"
    assert leak_counts(page, code_frame) == {"parent": 0, "frame": 0}
    after = page.eval_on_selector_all(
        MARKDOWN_PARAGRAPHS, "ps => ps.map(p => [getComputedStyle(p).color, getComputedStyle(p).margin])"
    )
    assert after == before
    assert page.locator(PILL).count() == 0


def test_normal_when_html_body_line_edge_cases(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """入れ子の複数行の開きタグの後・`<br>` の後・`<pre>` の中の文を選んでも、元の HTML の行にして箇所を添える（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": LINE_EDGE_HTML_BODY}
    )
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    # 実行（複数行の開きタグの後の文を選び、コメントを溜める）
    select_in_frame(page, BODY_FRAME, "言い換えたい文", "言い換えたい文")
    page.wait_for_selector(PILL, timeout=UPDATE_TIMEOUT_MS)
    page.get_by_role("button", name="選んだ箇所にコメント").click()
    page.fill(SEND_TEXTAREA, "ここは言い換える")
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{SEND_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    saved = yaml.safe_load((root / RECORD_DIR / "comments.yaml").read_text(encoding="utf-8"))
    assert [(item["loc"]["start"], item["loc"]["end"]) for item in saved["items"]] == [(3, 3)]
    # 実行・検証（`<br>` の後の文: `<br>` を数えない）
    select_in_frame(page, BODY_FRAME, "別の文", "別の文")
    page.wait_for_selector(PILL, timeout=UPDATE_TIMEOUT_MS)
    page.get_by_role("button", name="選んだ箇所にコメント").click()
    assert page.inner_text("aside.panel .send-loc-name") == "本文 4 行目"
    # 実行・検証（`<pre>` の中の文）
    select_in_frame(page, BODY_FRAME, "整形した文", "整形した文")
    page.wait_for_selector(PILL, timeout=UPDATE_TIMEOUT_MS)
    page.get_by_role("button", name="選んだ箇所にコメント").click()
    assert page.inner_text("aside.panel .send-loc-name") == "本文 6 行目"


# 詳細パネルの本文のスクロール領域
PANEL_BODY_SELECTOR = "aside.panel .panel-body"

# 本文の枠の中の `id` の要素が、詳細パネルの本文のスクロール領域の見える範囲に入っているかを返す
ANCHOR_VISIBLE_JS = """([frameSelector, id]) => {
    const frame = document.querySelector(frameSelector);
    const target = frame.contentDocument.getElementById(id);
    const box = document.querySelector('aside.panel .panel-body').getBoundingClientRect();
    const top = frame.getBoundingClientRect().top + frame.clientTop + target.getBoundingClientRect().top;
    return top >= box.top - 1 && top + target.getBoundingClientRect().height <= box.bottom + 1;
}"""

# 枠の中の文書へ、ポインターを押す → リンクの文を選ぶ（`selectionchange` は後の task で届く）の順に送る（sandbox の iframe は script を動かさないため、ここで待たない）
PRESS_AND_SELECT_LINK_TEXT_JS = """(id) => {
    const link = document.getElementById(id);
    document.dispatchEvent(new Event('pointerdown'));
    const range = document.createRange();
    range.selectNodeContents(link);
    const selection = getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
}"""

# 枠の中の文書へ、ポインターを離す → リンクを押す（`detail` が 1）の順に送る
RELEASE_AND_CLICK_LINK_JS = """(id) => {
    document.dispatchEvent(new Event('pointerup'));
    document.getElementById(id).dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, detail: 1 }));
}"""


def test_normal_when_html_body_link(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    link_target: str,
) -> None:
    """枠の中の外へのリンクを押すと、枠の中では移らず、新しいタブで開く（正常系）。"""
    # 準備
    body = html_with_links(
        ("plain", f'href="{link_target}/plain"', "target を持たないリンク"),
        ("blank", f'href="{link_target}/blank" target="_blank"', "別のタブを指すリンク"),
        ("mail", 'href="mailto:a@example.com"', "メールのリンク"),
    )
    url = write_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": body})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    frame = frame_of(page, BODY_FRAME)
    location = frame_location(frame)
    tabs = opened_tabs(page)
    # 実行・検証（target を持たないリンク）
    tab = new_tab_after(page, lambda: frame.click("#plain"))
    assert tab.url == f"{link_target}/plain"
    assert tab.title() == LINK_PAGE_TITLE
    assert tab.evaluate("window.opener") is None
    assert opened_tabs(page) == tabs + 1
    # 実行・検証（target="_blank" のリンク）
    tab = new_tab_after(page, lambda: frame.click("#blank"))
    assert tab.url == f"{link_target}/blank"
    assert tab.evaluate("window.opener") is None
    assert opened_tabs(page) == tabs + 2
    # 実行・検証（Ctrl を押しながら押す）
    tab = new_tab_after(page, lambda: frame.click("#plain", modifiers=["Control"]))
    assert tab.url == f"{link_target}/plain"
    assert opened_tabs(page) == tabs + 3
    # 実行・検証（中ボタンで押す）
    tab = new_tab_after(page, lambda: frame.click("#plain", button="middle"))
    assert tab.url == f"{link_target}/plain"
    assert opened_tabs(page) == tabs + 4

    def focus_and_enter() -> None:
        """リンクにフォーカスして Enter を押す。"""
        frame.focus("#plain")
        page.keyboard.press("Enter")

    # 実行・検証（フォーカスして Enter を押す）
    tab = new_tab_after(page, focus_and_enter)
    assert tab.url == f"{link_target}/plain"
    assert opened_tabs(page) == tabs + 5
    # 実行（mailto: のリンク）
    page.evaluate(WINDOW_OPEN_RECORDER_JS)
    frame.click("#mail")
    # 検証（window.open が mailto: を `_blank`・`noopener,noreferrer` で 1 回呼んだ）
    assert recorded_window_opens(page) == [["mailto:a@example.com", "_blank", "noopener,noreferrer"]]
    # 検証（どのリンクを押した後も、枠は本文を描いたまま場所が変わらない）
    assert frame_location(frame) == location
    assert frame.locator("a").count() == 3
    assert page.get_attribute(BODY_FRAME, "sandbox") == "allow-same-origin"


def test_normal_when_html_body_anchor_link(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """`#` で始まるリンクは新しいタブで開かず、本文をその `id` の要素まで送る（正常系）。"""
    # 準備（画面に入らない位置に、`id` の見出しを置く）
    spacer = '<div style="height:2400px"></div>\n'
    body = (
        html_with_links(
            ("to-usage", 'href="#usage"', "usage へ"),
            ("to-encoded", 'href="#%E4%BD%BF%E3%81%84%E6%96%B9"', "使い方へ"),
            ("to-none", 'href="#none"', "無い場所へ"),
        )
        + spacer
        + '<h2 id="usage">usage の見出し</h2>\n'
        + spacer
        + '<h2 id="使い方">使い方の見出し</h2>\n'
        + spacer
    )
    url = write_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": body})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    frame = frame_of(page, BODY_FRAME)
    location = frame_location(frame)
    tabs = opened_tabs(page)
    assert page.evaluate(ANCHOR_VISIBLE_JS, [BODY_FRAME, "usage"]) is False
    assert page.evaluate(ANCHOR_VISIBLE_JS, [BODY_FRAME, "使い方"]) is False
    # 実行（#usage のリンク）
    frame.click("#to-usage")
    page.wait_for_function(ANCHOR_VISIBLE_JS, arg=[BODY_FRAME, "usage"])
    # 検証（後ろの画面は送られない）
    assert page.evaluate("document.scrollingElement.scrollTop") == 0
    # 実行（パーセントエンコードしたリンク）
    frame.click("#to-encoded")
    page.wait_for_function(ANCHOR_VISIBLE_JS, arg=[BODY_FRAME, "使い方"])
    # 実行（無い id のリンク。クリックが要素を見える位置へ送らないよう、先頭へ戻してから押す）
    page.evaluate(f"document.querySelector('{PANEL_BODY_SELECTOR}').scrollTop = 0")
    frame.click("#to-none")
    page.wait_for_timeout(FRAME_SETTLE_MS)
    # 検証
    assert page.evaluate(f"document.querySelector('{PANEL_BODY_SELECTOR}').scrollTop") == 0
    assert opened_tabs(page) == tabs
    assert page.evaluate("location.hash") == "#tab=docs&id=A-1"
    assert frame_location(frame) == location


def test_normal_when_html_body_link_not_opened(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """相対の URL と `http:`・`https:`・`mailto:` 以外のスキームのリンクは、押しても開かず、枠の中でも移らない（正常系）。"""
    # 準備
    body = html_with_links(
        ("relative", 'href="other.html"', "相対の URL"),
        ("absolute-path", 'href="/mindstella.html"', "パスだけの URL"),
        ("script", 'href="javascript:parent.__mark=1"', "javascript のリンク"),
        ("data", 'href="data:text/html,x"', "data のリンク"),
    )
    url = write_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": body})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    frame = frame_of(page, BODY_FRAME)
    location = frame_location(frame)
    tabs = opened_tabs(page)
    # 実行
    frame.click("#relative")
    frame.click("#absolute-path")
    frame.click("#script")
    frame.click("#data")
    page.wait_for_timeout(FRAME_SETTLE_MS)
    # 検証
    assert opened_tabs(page) == tabs
    assert frame_location(frame) == location
    assert frame.locator("a").count() == 4
    assert page.evaluate("window.__mark") is None


def test_normal_when_html_body_link_text_selected(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    link_target: str,
) -> None:
    """リンクの文をなぞって選んだ直後の押下では開かず、選んだ後にリンクにフォーカスして Enter を押すと開く（正常系）。"""
    # 準備
    body = f'<p>前の文 <a id="link" href="{link_target}/selected">リンクの文</a> 後の文</p>\n'
    url, _ = write_review_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": body})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    frame = frame_of(page, BODY_FRAME)
    location = frame_location(frame)
    tabs = opened_tabs(page)
    # 実行（リンクの文をなぞって選ぶ）
    frame.evaluate(PRESS_AND_SELECT_LINK_TEXT_JS, "link")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    frame.evaluate(RELEASE_AND_CLICK_LINK_JS, "link")
    # 検証（開かず、選んだ箇所のコメントの入口が出る）
    page.wait_for_selector(PILL, timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_timeout(FRAME_SETTLE_MS)
    assert opened_tabs(page) == tabs
    assert frame_location(frame) == location

    def focus_and_enter() -> None:
        """文を選んだまま、リンクにフォーカスして Enter を押す。"""
        frame.focus("#link")
        page.keyboard.press("Enter")

    # 実行・検証（Enter を押すと開く）
    tab = new_tab_after(page, focus_and_enter)
    assert tab.url == f"{link_target}/selected"
    assert opened_tabs(page) == tabs + 1
    assert frame_location(frame) == location


def _hash_params(page: Page) -> dict[str, list[str]]:
    """今の URL のハッシュを、キー → 値の並びで返す。"""
    return parse_qs(str(page.evaluate("location.hash")).lstrip("#"))


def _make_diff_workspace(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, *, second: bool
) -> str:
    """D-1 の本文を書き換えて `commit`（V-1）し、`second` なら D-2 の本文も書き換えて `commit`（V-2）した配信の URL を返す。"""
    root = make_workspace(make_item("D-1"), make_item("D-2"))
    workspace = str(root)
    rewrites = [("D-1", "D-1 を直す")] + ([("D-2", "D-2 を直す")] if second else [])
    for item_id, summary in rewrites:
        updated = call_tool(
            "update", workspace=workspace, id=item_id, item={"body_markdown": f"{item_id} の本文を直した\n"}
        )
        assert updated.is_error is False, updated.text
        committed = call_tool("commit", workspace=workspace, summary=summary)
        assert committed.is_error is False, committed.text
    result = call_tool("preview_url", workspace=workspace)
    assert result.is_error is False, result.text
    assert result.data is not None
    return str(result.data["url"])


def test_normal_when_diff_in_hash(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """ハッシュの diff が指すまとまりの差分の表示で開き、時点を選び直すと履歴に積まずに diff を置き換える（正常系）。"""
    # 準備
    url = _make_diff_workspace(make_workspace, make_item, call_tool, second=True)
    # 実行（時点を指すハッシュで開く）
    open_preview(url, "#tab=decisions&view=table&diff=V-1")
    page.wait_for_selector(DIFF_CHIP, timeout=DIFF_SETTLE_MS)
    # 検証
    assert page.inner_text(DIFF_CHIP_TITLE).endswith("D-1 を直す")
    assert page.locator('table.grid tbody tr[data-id="D-1"] .row-open + .df-mark.df-chg').count() == 1
    assert page.locator('table.grid tbody tr[data-id="D-2"] .df-mark').count() == 0
    # 実行（項目を開く）
    page.click('table.grid tbody tr[data-id="D-1"] .row-open')
    page.wait_for_selector("aside.panel.open")
    # 検証（diff を保つ）
    assert _hash_params(page)["id"] == ["D-1"]
    assert _hash_params(page)["diff"] == ["V-1"]
    # 実行（変更履歴で V-2 を選ぶ）
    history_before = page.evaluate("history.length")
    page.get_by_role("button", name="変更履歴").click()
    page.wait_for_selector(f"{HISTORY_DIALOG}[open]")
    page.click(f"{HISTORY_DIALOG} .hist-item[data-sel='V-2']")
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-2 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（diff を置き換え、履歴を増やさない）
    assert _hash_params(page)["diff"] == ["V-2"]
    assert page.evaluate("history.length") == history_before
    # 実行（概要へ移る）
    page.click('nav.tabbar a[data-tab="overview"]')
    page.wait_for_function("!location.hash.includes('tab=decisions')", timeout=DIFF_SETTLE_MS)
    # 検証
    assert _hash_params(page)["diff"] == ["V-2"]
    # 実行（全体の検索で D-2 を開く）
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{SEARCH_DIALOG}[open]")
    page.fill(f"{SEARCH_DIALOG} input", "D-2")
    page.click(f'{SEARCH_DIALOG} .sr-item[data-id="D-2"]')
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert _hash_params(page)["id"] == ["D-2"]
    assert _hash_params(page)["diff"] == ["V-2"]
    # 実行（札の × を押す）
    page.get_by_role("button", name=DIFF_OFF_NAME).click()
    page.wait_for_function(f"!document.querySelector('{DIFF_CHIP}')", timeout=DIFF_SETTLE_MS)
    # 検証
    assert "diff" not in _hash_params(page)
    assert page.evaluate(SAVED_DIFF_JS) is None


def test_normal_when_diff_in_hash_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """記録に無いまとまり・空の pending を指すハッシュでは、差分を出さずに開き、diff を外す（正常系）。"""
    # 準備
    url = _make_diff_workspace(make_workspace, make_item, call_tool, second=False)
    for missing in ("V-99", "pending"):
        # 実行
        open_preview(url, f"#tab=decisions&diff={missing}")
        page.wait_for_function("!location.hash.includes('diff=')", timeout=DIFF_SETTLE_MS)
        # 検証
        assert page.locator(DIFF_CHIP).count() == 0
        assert page.locator(".df-mark").count() == 0
        assert page.locator("nav.tabbar .df-dot").count() == 0
        assert page.evaluate("location.hash") == "#tab=decisions"
        assert page.evaluate(SAVED_DIFF_JS) is None


def test_normal_when_stored_diff_without_hash(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """ハッシュに diff が無ければ端末に残した時点で開き、その時点をハッシュに書く（正常系）。"""
    # 準備（一度開いて変更履歴で V-1 を選び、閉じる）
    url = _make_diff_workspace(make_workspace, make_item, call_tool, second=False)
    open_preview(url, "#tab=decisions&view=table")
    page.get_by_role("button", name="変更履歴").click()
    page.wait_for_selector(f"{HISTORY_DIALOG}[open]")
    page.click(f"{HISTORY_DIALOG} .hist-item[data-sel='V-1']")
    page.wait_for_selector(DIFF_CHIP, timeout=DIFF_SETTLE_MS)
    page.goto("about:blank")
    history_before = page.evaluate("history.length")
    # 実行（時点の無いハッシュで開き直す）
    open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector(DIFF_CHIP, timeout=DIFF_SETTLE_MS)
    # 検証
    assert page.inner_text(DIFF_CHIP_TITLE).endswith("D-1 を直す")
    assert page.locator('table.grid tbody tr[data-id="D-1"] .row-open + .df-mark.df-chg').count() == 1
    assert _hash_params(page)["diff"] == ["V-1"]
    assert page.evaluate("history.length") == history_before + 1


def test_normal_when_body_link_to_change_set(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """詳細の本文の #diff= のリンクを押すと、開いた項目のままそのまとまりの差分の表示に切り替え、履歴に積まずに diff を置き換える。まとまりを指さない値のリンクは何もしない（正常系）。"""
    # 準備
    url = build_body_link_workspace(make_workspace, make_item, call_tool)
    open_preview(url, BODY_LINK_HASH)
    page.wait_for_selector(DIFF_CHIP, timeout=DIFF_SETTLE_MS)
    page.wait_for_selector("aside.panel.open .md a", timeout=DIFF_SETTLE_MS)
    history_before = page.evaluate("history.length")
    # 実行（記録に無いまとまりと since のリンクを押す）
    for text in ("無いまとまり", "前回から"):
        page.locator("aside.panel .md a", has_text=text).click()
        page.wait_for_timeout(SELECTION_SETTLE_MS)
    # 検証
    assert page.inner_text(DIFF_CHIP_TITLE).endswith("D-2 を直す")
    assert _hash_params(page)["diff"] == ["V-2"]
    assert "h" not in _hash_params(page)
    assert page.evaluate("history.length") == history_before
    # 実行（V-1 へのリンクを押す）
    page.locator("aside.panel .md a", has_text="V-1 へ").click()
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-1 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証
    assert page.locator('table.grid tbody tr[data-id="D-1"] .row-open + .df-mark.df-chg').count() == 1
    assert page.locator('table.grid tbody tr[data-id="D-2"] .df-mark').count() == 0
    assert page.locator("aside.panel.open").count() == 1
    assert _hash_params(page)["tab"] == ["decisions"]
    assert _hash_params(page)["view"] == ["table"]
    assert _hash_params(page)["id"] == ["D-2"]
    assert _hash_params(page)["diff"] == ["V-1"]
    assert page.evaluate(SAVED_DIFF_JS) == "V-1"
    assert page.evaluate("history.length") == history_before
    # 実行（変更履歴で V-2 を選び直し、他の引数つきのリンクを押す）
    page.get_by_role("button", name="変更履歴").click()
    page.wait_for_selector(f"{HISTORY_DIALOG}[open]")
    page.click(f"{HISTORY_DIALOG} .hist-item[data-sel='V-2']")
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-2 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    page.locator("aside.panel .md a", has_text="他の引数つき").click()
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-1 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（diff 以外の引数は読まない）
    assert _hash_params(page)["tab"] == ["decisions"]
    assert _hash_params(page)["view"] == ["table"]
    assert _hash_params(page)["id"] == ["D-2"]
    assert _hash_params(page)["diff"] == ["V-1"]
    assert page.evaluate("history.length") == history_before
    # 実行（本文の見出しのリンクを押す）
    assert page.evaluate(BODY_LINK_HEADING_IN_VIEW_JS, ["aside.panel .panel-body", "決め方"]) is False
    page.locator("aside.panel .md a", has_text="決め方へ").click()
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'")
    # 検証
    assert page.evaluate(BODY_LINK_HEADING_IN_VIEW_JS, ["aside.panel .panel-body", "決め方"]) is True
    assert _hash_params(page)["diff"] == ["V-1"]


def test_normal_when_post_link_to_change_set(
    write_post_link_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """スレッドの書き込みとレビュー中を確かめる画面の行の #diff= のリンクを押すと、画面を開いたままそのまとまりの差分の表示に切り替え、履歴に積まずに diff を置き換える。まとまりを指さないものはリンクの文字だけを出す（正常系）。"""
    # 準備
    url, _ = write_post_link_preview()
    open_preview(url, POST_LINK_HASH)
    open_thread(page, "TH-1")
    post = f"{COMMENTS_PANEL} ol.posts > li:nth-child(1) .post-body"
    links = f"{post} a.setlink"
    history_before = page.evaluate("history.length")
    # 検証（リンクは 2 つだけで、リンクの中の D-1 は項目を開くボタンにしない）
    assert page.eval_on_selector_all(links, "links => links.map(a => a.textContent)") == [
        "D-1 を直した",
        "他の引数つき",
    ]
    assert page.locator(f"{post} button.idlink").count() == 0
    text = page.inner_text(post)
    assert "](#diff=V-1)" not in text
    assert "](#tab=tasks&id=D-2&diff=V-2)" not in text
    # 検証（まとまりを指さないものはリンクにならず、リンクの文字だけが出る）
    assert page.locator(f"{post} a").count() == 2
    for word in ("無いまとまり", "前回から", "決め方へ"):
        assert word in text
    for marker in ("[", "](#diff=V-99)", "](#diff=since)", "](#決め方)"):
        assert marker not in text
    # 実行（「D-1 を直した」を押す）
    page.locator(links, has_text="D-1 を直した").click()
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-1 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（V-1 の差分の表示と、開いたままのスレッド）
    assert page.locator('table.grid tbody tr[data-id="D-1"] .row-open + .df-mark.df-chg').count() == 1
    assert page.locator('table.grid tbody tr[data-id="D-2"] .df-mark').count() == 0
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert page.inner_text(f"{COMMENTS_PANEL} .th-heading") != ""
    assert _hash_params(page)["tab"] == ["decisions"]
    assert _hash_params(page)["view"] == ["table"]
    assert _hash_params(page)["diff"] == ["V-1"]
    assert page.evaluate(SAVED_DIFF_JS) == "V-1"
    assert page.evaluate("history.length") == history_before
    # 実行（「他の引数つき」を押す）
    page.locator(links, has_text="他の引数つき").click()
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-2 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（`tab`・`id` は書き換わらず、`diff` だけを読む）
    assert _hash_params(page)["tab"] == ["decisions"]
    assert _hash_params(page)["view"] == ["table"]
    assert "id" not in _hash_params(page)
    assert _hash_params(page)["diff"] == ["V-2"]
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert page.evaluate("history.length") == history_before
    # 実行（V-1 に戻してから、レビュー中を確かめる画面の行の「V-2 の直し」を押す）
    page.locator(links, has_text="D-1 を直した").click()
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-1 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    row = review_row(COMMENTS_PANEL, "C-1")
    # 検証（行のリンクは 1 つで、行の D-2 は文字のまま）
    assert page.eval_on_selector_all(
        f"{row} .review-body a.setlink", "links => links.map(a => a.textContent)"
    ) == ["V-2 の直し"]
    assert page.locator(f"{row} .review-body button").count() == 0
    assert "D-2" in page.inner_text(f"{row} .review-body")
    # 実行
    page.locator(f"{row} .review-body a.setlink").click()
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-2 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（レビュー中を確かめる画面は開いたまま）
    assert page.locator(REVIEW_HEAD).count() == 1
    assert _hash_params(page)["tab"] == ["decisions"]
    assert _hash_params(page)["diff"] == ["V-2"]
    assert page.evaluate("history.length") == history_before


def test_normal_when_markdown_post(
    write_markdown_post_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """スレッドの書き込みとレビュー中の返信を、詳細の本文と同じく mdmark で Markdown として描き、生の HTML のスクリプトを動かさない（正常系）。"""
    # 準備・実行
    url, _ = write_markdown_post_preview()
    open_preview(url, MARKDOWN_POST_HASH)
    open_thread(page, "TH-1")
    post = f"{COMMENTS_PANEL} ol.posts > li:nth-child(1) .post-body"
    page.wait_for_selector(f"{post} figure.diagram svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（見出し・表・コード・図が描かれ、記法の文字が出ない）
    assert page.inner_text(f"{post} h2") == "比べた結果"
    assert page.locator(f"{post} table").count() == 1
    assert page.locator(f"{post} pre > code").count() == 1
    assert page.locator(f"{post} figure.diagram svg").count() >= 1
    text = page.inner_text(post)
    for notation in ("##", "| --- |", "```"):
        assert notation not in text
    # 検証（段落の中の D-1 は項目を開くボタンで、書き込みの要素は詳細の本文と同じ class）
    assert page.locator(f"{post} > p button.idlink").all_inner_texts() == ["D-1"]
    assert page.locator(f"{post}.mdmark").count() == 1
    # 検証（生の HTML のスクリプトは動かない）
    assert page.evaluate("window.injected !== true")
    assert page.locator(f"{post} [onerror]").count() == 0
    # 検証（スレッドの末尾のレビュー中の返信は、太字で出て `**` が出ない）
    reply = f"{COMMENTS_PANEL} ol.posts > li.pending .post-body"
    assert page.inner_text(f"{reply} strong") == "起票してよい"
    assert "**" not in page.inner_text(reply)
    # 実行（レビュー中を確かめる画面を開く）
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    row = review_row(COMMENTS_PANEL, "C-1")
    # 検証（行の返信も太字で出て、`**` が出ない）
    assert page.inner_text(f"{row} .review-body strong") == "起票してよい"
    assert "**" not in page.inner_text(f"{row} .review-body")


# 帯の印の無い、上端に近い位置（帯の上端からの距離。先頭の印の下）
EMPTY_AREA_OFFSET_PX = 40

# 面を押したまま下へ動かす距離
DRAG_DISTANCE_PX = 100


def test_normal_when_diff_minimap(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示で長い資料の詳細を開くと、変わった箇所の印を並べたミニマップが出て、印・印の無い所を押す・ドラッグ・キーで、履歴とハッシュを変えずに本文を送る（正常系）。"""
    # 準備
    url, _ = write_minimap_preview()
    open_minimap(page, open_preview, url, MINIMAP_HASH)
    history_length = page.evaluate("history.length")
    shapes = mark_shapes(page, PANEL_SCOPE)
    # 検証（印の並びと形、開いた直後の本文）
    assert [shape["kind"] for shape in shapes] == ["df-del", "df-add"]
    assert shapes[0]["top"] < shapes[1]["top"]
    assert shapes[0]["border"] == "2px"
    assert shapes[1]["border"] == "0px"
    assert shapes[0]["fill"] != shapes[1]["fill"]
    assert not added_paragraph_in_view(page, PANEL_SCOPE)
    assert map_metrics(page, PANEL_SCOPE)["scrollTop"] == 0
    # 実行（下の印を押す）
    page.locator(f"{PANEL_SCOPE} .df-map .df-map-m").nth(1).click()
    pressed = scroll_top(page, PANEL_SCOPE)
    # 検証
    assert added_paragraph_in_view(page, PANEL_SCOPE)
    # 次に押す位置は、印の上ではない
    assert not mark_at_empty_area(page, PANEL_SCOPE, offset_y=EMPTY_AREA_OFFSET_PX)
    # 実行（印の無い上端近くを押す）
    press_empty_area(page, PANEL_SCOPE, offset_y=EMPTY_AREA_OFFSET_PX)
    top_after_empty_area = scroll_top(page, PANEL_SCOPE)
    # 検証
    assert top_after_empty_area < pressed
    assert top_after_empty_area < map_metrics(page, PANEL_SCOPE)["clientHeight"] / 2
    # 実行（見えている範囲の面を押したまま下へ動かして離す）
    drag_view(page, PANEL_SCOPE, delta_y=DRAG_DISTANCE_PX)
    dragged = scroll_top(page, PANEL_SCOPE)
    page.wait_for_timeout(300)
    # 検証（動かした分だけ送り、離した後もその位置に留まる）
    assert dragged > top_after_empty_area
    assert scroll_top(page, PANEL_SCOPE) == dragged
    # 実行（印にフォーカスして Home を押す）
    page.locator(f"{PANEL_SCOPE} .df-map .df-map-m").nth(1).focus()
    page.keyboard.press("Home")
    # 検証
    assert page.evaluate("document.activeElement?.getAttribute('aria-label')") == "消した箇所（1 / 2）"
    # 検証（ここまでの間、ハッシュは変わらず、履歴は増えない）
    assert _hash_params(page) == {"tab": ["docs"], "id": ["A-1"], "diff": ["V-1"]}
    assert page.evaluate("history.length") == history_length
    # 実行（資料のタブで変わった箇所の無い A-2 を開く）
    page.click('button.card[data-id="A-2"]')
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent.includes('A-2')"
    )
    # 検証
    assert marks_of_map(page, PANEL_SCOPE) == 0
    assert page.locator(f"{PANEL_SCOPE} .df-map").is_visible() is False


def test_normal_when_diff_minimap_hidden(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """端末の保存領域に差分のミニマップを表示しない上書きがあると、ミニマップを出さず、表示の設定で変えている項目に並び、既定に戻すと出る（正常系）。"""
    # 準備
    url, _ = write_minimap_preview()
    hide_minimap_in_storage(page)
    page.set_viewport_size({"width": 1280, "height": 800})
    # 実行
    open_preview(url, MINIMAP_HASH)
    page.wait_for_selector(f"{PANEL_SCOPE}.open .md ins.df-blk")
    # 検証（本文の差分の印はあり、ミニマップは無い）
    assert page.locator(f"{PANEL_SCOPE} .md del.df-blk").count() == 1
    assert page.locator(f"{PANEL_SCOPE} .df-map").count() == 0
    # 実行（表示の設定を開く）
    open_settings(page)
    # 検証
    checkbox = page.locator(f"{SETTINGS_PANEL} fieldset", has_text="詳細に表示するもの").get_by_role(
        "checkbox", name="差分のミニマップ"
    )
    assert checkbox.is_checked() is False
    assert "差分のミニマップ" in page.inner_text(f"{SETTINGS_PANEL} .st-over")
    assert page.get_by_role("button", name="ワークスペースの既定にする").count() == 0
    assert "見た目と表示する種類は、ワークスペースの既定と同じです。" in panel_text(page)
    # 実行（既定に戻す）
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_selector(f"{PANEL_SCOPE} .df-map .df-map-m")
    # 検証
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["minimap"] is None


def test_normal_when_unseen_thread_opened(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    page: Page,
) -> None:
    """未読の印を出し、未読のスレッドを開くと既読にして印を消す。既読のスレッドを開いても既読にする要求は送らない（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", read=True, created="2026-10-12T01:00:00+00:00"),
                make_post("TH-1-2", author="ai", seen=False, created="2026-10-12T02:00:00+00:00"),
                summary="未読のスレッド",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", author="ai", created="2026-10-12T03:00:00+00:00"),
                summary="既読のスレッド",
            ),
        ),
    )
    requested: list[str] = []

    def _record(route: Route) -> None:
        """既読にする要求のスレッドの ID を控えて、サーバーへ通す。"""
        requested.append(route.request.url.split("/")[-2])
        route.continue_()

    page.route("**/api/threads/*/seen", _record)
    # 実行（コメントの一覧を開く前）
    open_preview(url)
    page.wait_for_selector(f"{COMMENTS_BUTTON} .unread-dot")
    # 検証
    assert page.get_attribute(COMMENTS_BUTTON, "aria-label") == "コメント（未読あり・レビュー中 0 件）"
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 0
    # 実行（一覧を開く）
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    # 検証（TH-1 の行だけに未読の札）
    row = f"{COMMENTS_PANEL} ul.th-list > li"
    assert page.locator(f"{row}:has(button[data-focus='thread:TH-1']) .th-unread").count() == 1
    assert page.locator(f"{row}:has(button[data-focus='thread:TH-2']) .th-unread").count() == 0
    assert requested == []
    # 実行（TH-1 を開く）
    page.click(f"{row}:has(button[data-focus='thread:TH-1']) button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    page.wait_for_function(
        "() => !document.querySelector('header.topbar button.comments-btn .unread-dot')",
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証（点は要求の応答より先に消えるので、threads.yaml が既読になるのを待つ）
    wait_thread_seen(page, root, "TH-1")
    threads = read_workspace_yaml(root, "threads.yaml")["items"]
    assert [post["seen"] for post in threads[0]["posts"]] == [True, True]
    assert requested == ["TH-1"]
    # 実行（一覧へ戻る）
    page.get_by_role("button", name="一覧へ戻る").click()
    page.wait_for_selector(f"{row}:has(button[data-focus='thread:TH-1'])")
    # 検証（未読の印の無い一覧とボタン）
    assert page.locator(f"{COMMENTS_PANEL} .th-unread").count() == 0
    assert page.get_attribute(COMMENTS_BUTTON, "aria-label") == "コメント（レビュー中 0 件）"
    # 実行（既読の TH-2 を開く）
    page.click(f"{row}:has(button[data-focus='thread:TH-2']) button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    # 検証
    assert requested == ["TH-1"]


def test_normal_when_reply_seen_while_opened(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    call_tool: CallTool,
    page: Page,
) -> None:
    """開いているスレッドに届いた AI の返信を既読にし、直後に一覧へ戻っても未読の印を出さない（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", read=True, created="2026-10-12T01:00:00+00:00"),
                summary="開いているスレッド",
            ),
        ),
    )
    open_preview(url)
    open_thread(page, "TH-1")
    posts = f"{COMMENTS_PANEL} ol.posts > li"
    # 実行（AI の返信が届く）
    call_tool("reply", workspace=str(root), id="TH-1", body="続きの返信です", summary="開いているスレッド")
    page.wait_for_selector(f"{posts}:has-text('続きの返信です')", timeout=UPDATE_TIMEOUT_MS)
    wait_thread_seen(page, root, "TH-1")
    # 検証
    assert page.locator(posts).last.inner_text().count("続きの返信です") == 1
    assert [post["seen"] for post in read_workspace_yaml(root, "threads.yaml")["items"][0]["posts"]] == [True, True]
    # 実行（threads.yaml が既読になった直後に一覧へ戻る）
    page.get_by_role("button", name="一覧へ戻る").click()
    page.wait_for_selector(thread_row("TH-1"))
    # 検証（戻った時点で未読の印が無い）
    assert page.locator(f"{thread_row('TH-1')} .th-unread").count() == 0
    assert page.locator(f"{COMMENTS_BUTTON} .unread-dot").count() == 0
    assert page.get_attribute(COMMENTS_BUTTON, "aria-label") == "コメント（レビュー中 0 件）"


# 詳細パネル（本文のスクロール領域とミニマップを持つ外側）
PANEL = "aside.panel"

# 左右に並べた本文の列（選んだ時点・今）と、インラインの本文の差分の印
BEFORE_COLUMN = f"{PANEL} .sbs section.sbs-before"
AFTER_COLUMN = f"{PANEL} .sbs section.sbs-after"
INLINE_MARKS = f"{PANEL} .md:not(.md-value) ins.df-blk, {PANEL} .md:not(.md-value) del.df-blk"


def test_normal_when_body_diff_side_by_side(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """本文の幅が足りる詳細パネルで「左右に並べる」を押すと前後の本文を左右に並べて上書きに残し、本文の幅が足りない詳細パネルでは切り替えを出さずインラインで出す（正常系）。"""
    # 準備
    root = build_body_layout_workspace(make_workspace, call_tool)
    url = str(call_tool("preview_url", workspace=str(root)).data["url"])
    page.set_viewport_size(SIDE_VIEWPORT)
    # 実行
    open_preview(url, SIDE_HASH)
    page.wait_for_selector(f"{PANEL}.open {LAYOUT_SWITCH}")
    # 検証（切り替えは「インライン」を押した状態で、本文の差分はインライン）
    assert page.get_attribute(f"{PANEL} {LAYOUT_SWITCH}", "aria-label") == LAYOUT_GROUP_NAME
    assert layout_buttons(page, PANEL) == [
        {"name": INLINE_NAME, "layout": "inline", "pressed": "true"},
        {"name": SIDE_NAME, "layout": "side", "pressed": "false"},
    ]
    assert page.locator(INLINE_MARKS).count() == 2
    assert page.locator(f"{PANEL} .sbs").is_visible() is False
    # 実行（「左右に並べる」を押す）
    page.get_by_role("button", name=SIDE_NAME).click()
    open_side_by_side(page, PANEL)
    # 検証（選んだ時点の列に消した段落、今の列に足した段落。向かいは同じ高さの空き）
    assert page.locator(f"{BEFORE_COLUMN} del.df-blk").inner_text().endswith("1 つ目の段落です。")
    assert page.locator(f"{AFTER_COLUMN} ins.df-blk").inner_text().endswith("4 つ目の段落です。")
    assert page.locator(f"{BEFORE_COLUMN} ins.df-blk").count() == 0
    assert page.locator(f"{AFTER_COLUMN} del.df-blk").count() == 0
    before_rows, after_rows = rows_of_columns(page, PANEL)
    assert [row["gap"] for row in before_rows] == [False, False, False, True]
    assert [row["gap"] for row in after_rows] == [True, False, False, False]
    assert [row["changed"] for row in before_rows] == [True, False, False, True]
    assert [row["top"] for row in before_rows] == [row["top"] for row in after_rows]
    assert [row["height"] for row in before_rows] == [row["height"] for row in after_rows]
    # 検証（変えていない 2 つ目・3 つ目の段落は、左右で同じ高さに印なしで並ぶ）
    unchanged = [(left["text"], right["text"]) for left, right in zip(before_rows, after_rows, strict=True) if not left["changed"]]
    assert unchanged == [("2 つ目の段落です。", "2 つ目の段落です。"), ("3 つ目の段落です。", "3 つ目の段落です。")]
    # 検証（「左右に並べる」を押した状態。ハッシュは開いたときのままで、個人の上書きに side が残る）
    assert [button["pressed"] for button in layout_buttons(page, PANEL)] == ["false", "true"]
    assert page.evaluate("location.hash") == SIDE_HASH
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["bodyLayout"] == "side"
    # 実行（検討事項のタブで D-1 を開く）
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.wait_for_selector('[data-id="D-1"]')
    page.click('[data-id="D-1"]')
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent.includes('いつ決めるか')")
    page.wait_for_selector(f"{PANEL} .md:not(.md-value) ins.df-blk:visible")
    # 実行（幅の区切りで詳細パネルを下限の幅 480px にする）
    press_key_times(page, "Home", 1)
    page.wait_for_selector(f"{PANEL} {LAYOUT_SWITCH}", state="hidden")
    # 検証（D-1 の詳細パネルは幅 480px で、切り替えが無く、書き換えた段落をインラインの消した行と足した行で出す）
    assert page.locator(f"{PANEL} {LAYOUT_SWITCH}").is_visible() is False
    assert page.locator(f"{PANEL} .sbs").is_visible() is False
    assert "来週に決めます" in page.inner_text(f"{PANEL} .md:not(.md-value) del.df-blk:visible")
    assert "今週に決めます" in page.inner_text(f"{PANEL} .md:not(.md-value) ins.df-blk:visible")


def test_normal_when_html_body_diff_side_by_side(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """並べ方の上書きが side のとき、HTML の本文の前後を描いた結果を左右に並べ、「原文の差分」で原文の行を左右に並べる（正常系）。"""
    # 準備
    root = build_html_body_layout_workspace(make_workspace, call_tool)
    url = str(call_tool("preview_url", workspace=str(root)).data["url"])
    page.set_viewport_size(SIDE_VIEWPORT)
    seed_side_layout(page, "V-2")
    full_scope = "dialog.full"
    # 実行
    open_preview(url, "#tab=docs&id=A-1&diff=V-2&full=1")
    page.wait_for_selector(f"{full_scope} .sbs-html")
    wait_frame_rendered(page, f"{full_scope} .sbs-after iframe.html-frame")
    # 検証（並べ方の切り替えは「左右に並べる」を押した状態で、見せ方の組より前の別の組）
    assert [button["pressed"] for button in layout_buttons(page, full_scope)] == ["false", "true"]
    bar_groups = page.eval_on_selector_all(
        f"{full_scope} .html-diff-bar [role=group]", "groups => groups.map(g => g.getAttribute('aria-label'))"
    )
    assert bar_groups == [LAYOUT_GROUP_NAME, "本文の差分の見せ方"]
    # 検証（選んだ時点の列に前の版、今の列に今の版を描いた結果。今の列の 2 つ目の段落だけに「変わった」の印）
    before_text = frame_of(page, f"{full_scope} .sbs-before iframe.html-frame").inner_text("body")
    assert "2 つ目の段落" in before_text
    assert "書き直した" not in before_text
    marked = frame_of(page, f"{full_scope} .sbs-after iframe.html-frame").eval_on_selector_all(
        "p", "ps => ps.map(p => [p.textContent, p.closest('[data-df]')?.dataset.df ?? null])"
    )
    assert marked == [
        ["1 つ目の段落", None],
        ["書き直した 2 つ目の段落", "chg"],
        ["3 つ目の段落", None],
    ]
    # 実行（「原文の差分」を押す）
    page.get_by_role("button", name=RAW_DIFF_BUTTON).click()
    page.wait_for_selector(f"{full_scope} .df-raw.df-split")
    # 検証（左に消した行、右に足した行が同じ高さで出て、行の印を含まない）
    removed = page.locator(f"{full_scope} .df-raw.df-split .df-line.df-del")
    added = page.locator(f"{full_scope} .df-raw.df-split .df-line.df-add")
    assert removed.count() == 1
    assert added.count() == 1
    assert "<p>2 つ目の段落</p>" in removed.inner_text()
    assert "<p>書き直した 2 つ目の段落</p>" in added.inner_text()
    removed_box = removed.bounding_box()
    added_box = added.bounding_box()
    assert removed_box is not None
    assert added_box is not None
    assert removed_box["y"] == added_box["y"]
    assert removed_box["x"] < added_box["x"]
    assert "data-line" not in page.inner_text(f"{full_scope} .df-raw.df-split")


def test_normal_when_edits_saved(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    open_preview: OpenPreview,
) -> None:
    """詳細パネルで答えを書いて保存待ちに溜め、保存待ちのパネルからまとめて保存する（正常系）。"""
    # 準備
    url, root = write_edit_preview(make_item("D-1", title="最初の問い"))
    page = open_preview(url, "#tab=decisions&view=board&id=D-1")
    page.wait_for_selector(f"{EDIT_PANEL}.open")
    page.get_by_role("button", name="編集する").click()
    answer = page.get_by_label("決定内容", exact=True)
    # 実行（溜める）
    answer.fill("新しい答え")
    answer.blur()
    page.wait_for_selector(f"{EDIT_PENDING_BUTTON} .count")
    # 検証（溜めた後）
    assert page.inner_text(f"{EDIT_PENDING_BUTTON} .count") == "1"
    assert page.locator(".pe-field[data-key='answer'] .pm.pm-pending").count() == 1
    assert page.locator(".card[data-id='D-1'] .pm.pm-pending").count() == 1
    assert read_items_file(root, "decisions.yaml")[0].get("answer") is None
    assert reached_by_tab(
        page,
        f"{EDIT_PANEL} button.pe-edit-toggle",
        ".pe-field[data-key='answer'] textarea",
        EDIT_PENDING_BUTTON,
    ) == [
        f"{EDIT_PANEL} button.pe-edit-toggle",
        ".pe-field[data-key='answer'] textarea",
        EDIT_PENDING_BUTTON,
    ]
    # 実行（保存する）
    open_edit_pending(page)
    assert reached_by_tab(page, "button.pe-undo", EDIT_SAVE_BUTTON) == ["button.pe-undo", EDIT_SAVE_BUTTON]
    page.click(EDIT_SAVE_BUTTON)
    page.wait_for_selector(".pe-toast")
    # 検証（保存した後）
    decision = read_items_file(root, "decisions.yaml")[0]
    assert (decision["answer"], decision["updated_by"]) == ("新しい答え", "user")
    assert page.inner_text(".pe-toast").strip() == "1 件を保存しました。"
    assert page.locator(EDIT_PENDING_BUTTON).count() == 0
    assert page.locator(".pm").count() == 0
    assert "新しい答え" in page.inner_text(f"{EDIT_PANEL} .panel-body")


# 表を送る・畳むなどの描き直しが済むまで待つミリ秒
BODY_VIEW_SETTLE_MS = 500

# 長文の列の幅（em）。セルの余白の分だけ広い
LONG_COLUMN_EM = 24
CELL_PADDING_EM = 3

# 見出しの行が領域の上端に残る位置の差（px）
STUCK_TOLERANCE_PX = 2


def _body_view_checkbox(page: Page, label: str) -> Any:
    """表示の設定の、区画「詳細に表示するもの」の中の、名前のチェックボックスを返す。"""
    return page.locator(f"{SETTINGS_PANEL} fieldset", has_text="詳細に表示するもの").get_by_role(
        "checkbox", name=label
    )


def test_normal_when_body_table_and_sections(
    write_body_view_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """列の多い表を持つ資料を開くと、説明の列は 24em で折り返し、ID は折り返さず、表は表の中だけで横に送れる。列の固定のボタンで左の列を残し、縦に送ると見出しの行が領域の上端に残り、見出しの矢印で節を畳める（正常系）。"""
    # 準備・実行
    url, _ = write_body_view_preview()
    open_body_view(page, open_preview, url)
    state = table_state(page)
    # 検証（列の種類と折り返し。表は本文の幅に収まらず、表の中だけで送れる）
    assert state["sizes"][0] == "short"
    assert state["nowraps"]["ID"] is True
    assert state["sizes"][-1] == "long"
    assert state["nowraps"]["説明"] is False
    assert LONG_COLUMN_EM <= state["widths"]["説明"] <= LONG_COLUMN_EM + CELL_PADDING_EM
    assert state["fill"] is False
    assert state["wrapScrolls"] is True
    assert state["fade"] is True
    assert state["pinned"] == []
    # 検証（しま模様は既定でオフで、行を塗り分けない）
    assert len(set(state["rowColors"])) == 1
    # 実行（「名前まで固定」を押して、表を右端まで送る）
    page.get_by_role("button", name="名前まで固定").click()
    page.eval_on_selector(f"{BODY_VIEW_SCOPE} .md-table-wrap", "e => { e.scrollLeft = e.scrollWidth; }")
    page.wait_for_timeout(BODY_VIEW_SETTLE_MS)
    pinned = table_state(page)
    # 検証（押したボタンは押した状態で、左の 3 列は左端に残り、右端の説明の列が見える）
    assert page.get_by_role("button", name="名前まで固定").get_attribute("aria-pressed") == "true"
    assert pinned["pinned"] == ["ID", "状態", "名前"]
    assert pinned["scrollLeft"] > 0
    assert abs(pinned["pinnedLefts"][0]) <= STUCK_TOLERANCE_PX
    assert pinned["pinnedLefts"] == sorted(pinned["pinnedLefts"])
    assert pinned["pinnedRights"][-1] <= pinned["wrapWidth"] + STUCK_TOLERANCE_PX
    assert 0 <= pinned["lastLeft"] < pinned["wrapWidth"]
    assert pinned["fade"] is False
    # 実行（本文を縦に送って、表の途中まで進める）
    page.eval_on_selector(f"{BODY_VIEW_SCOPE} .panel-body", "e => { e.scrollTop = 300; }")
    page.wait_for_selector(f"{BODY_VIEW_SCOPE} table.md-head-stuck")
    stuck = table_state(page)
    # 検証（見出しの行が領域の上端に残る）
    assert abs(stuck["headTop"] - stuck["areaTop"]) <= STUCK_TOLERANCE_PX
    # 実行（先頭へ戻して、見出し「比較」の矢印を押す）
    page.eval_on_selector(f"{BODY_VIEW_SCOPE} .panel-body", "e => { e.scrollTop = 0; }")
    page.get_by_role("button", name="比較を開閉").click()
    # 検証（比較の節は畳まれて表が隠れ、まとめの節は見えたまま）
    assert page.get_by_role("button", name="比較を開閉").get_attribute("aria-expanded") == "false"
    assert page.locator(f"{BODY_VIEW_SCOPE} .md-table-wrap").is_visible() is False
    assert page.get_by_text("表の見せ方をまとめた段落です。").is_visible() is True
    assert page.get_by_role("button", name="まとめを開閉").get_attribute("aria-expanded") == "true"


def test_normal_when_body_view_overridden(
    write_body_view_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """端末の保存領域に「しま模様をオン・セクションの折りたたみをオフ」の上書きがあると、行を塗り分け、見出しに矢印を置かない。表示の設定の変えている項目に並び、「既定に戻す」で矢印が戻り、しま模様が消える（正常系）。"""
    # 準備
    url, _ = write_body_view_preview()
    seed_body_view(page, {"tableStripes": True, "sectionFold": False})
    open_body_view(page, open_preview, url)
    colors = table_state(page)["rowColors"]
    # 検証（上書きどおりに描く）
    assert colors[0] == colors[2] == colors[4]
    assert colors[0] != colors[1]
    assert page.locator(f"{BODY_VIEW_SCOPE} button.md-fold").count() == 0
    # 実行（表示の設定を開く）
    open_settings(page)
    # 検証（上書きしたチェックだけが既定と違い、ワークスペースの既定に保存する対象には並ばない）
    assert _body_view_checkbox(page, "表のしま模様").is_checked() is True
    assert _body_view_checkbox(page, "セクションの折りたたみ").is_checked() is False
    assert _body_view_checkbox(page, "表の列の固定").is_checked() is True
    assert _body_view_checkbox(page, "表の見出しの固定").is_checked() is True
    assert page.inner_text(f"{SETTINGS_PANEL} .st-over").endswith("表のしま模様・セクションの折りたたみ")
    assert page.get_by_role("button", name="ワークスペースの既定にする").count() == 0
    # 実行（既定に戻す）
    page.click(f"{SETTINGS_PANEL} button:has-text('既定に戻す')")
    page.wait_for_selector(f"{BODY_VIEW_SCOPE} button.md-fold")
    # 検証（しま模様は消え、矢印が戻り、上書きは外れる）
    reset = table_state(page)["rowColors"]
    assert reset[0] == reset[1]
    assert page.locator(f"{BODY_VIEW_SCOPE} button.md-fold").count() == 2
    prefs = read_prefs(page)
    assert prefs is not None
    assert (prefs["tableStripes"], prefs["sectionFold"]) == (None, None)
    assert "ワークスペースの既定のまま表示しています。" in panel_text(page)


def test_normal_when_stored_panel_width(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, page: Page
) -> None:
    """同じタブで A-1 の詳細パネルの幅を 768px に変えて読み込み直すと、種類の違う D-3 の詳細パネルも 768px で開き、表の寄せも 768px になる（正常系）。"""
    # 準備（A-1 の詳細パネルで、幅の区切りを矢印キーで 8 回広げて 768px にする）
    url = write_preview(make_item("A-1"), make_item("D-3"), bodies={"A-1.md": "資料の本文です。"})
    open_panel(page, open_preview, url, "#tab=docs&id=A-1", PANEL_VIEWPORT)
    press_key_times(page, "ArrowLeft", 8)
    # 実行（同じタブで D-3 を指すハッシュを読み込み直す）
    page.goto(f"{url}#tab=decisions&view=table&id=D-3")
    page.reload()
    page.wait_for_selector(f"{WIDTH_PANEL}.open")
    state = panel_state(page)
    # 検証
    assert state["panelWidth"] == 768
    assert state["contentMargin"] == 768
    assert state["separator"]["now"] == "768"


def test_normal_when_stored_panel_width_over_max(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, page: Page
) -> None:
    """窓が狭く残した幅 1000px が上限を超えるときは、上限の 840px に収めて開き、保存領域の値は書き換えない（正常系）。"""
    # 準備
    url = write_preview(make_item("D-3"))
    seed_panel_width(page, 1000)
    # 実行（本文に重ねる幅 1000px で開く。上限は 1000 − 160 = 840px）
    open_panel(page, open_preview, url, "#tab=decisions&view=table&id=D-3", {"width": 1000, "height": 800})
    state = panel_state(page)
    # 検証
    assert state["panelWidth"] == 840
    assert state["contentMargin"] == 0
    assert state["separator"]["max"] == "840"
    assert state["separator"]["now"] == "840"
    assert read_stored_width(page) == "1000"


def test_normal_when_window_resized_with_panel_open(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, page: Page
) -> None:
    """詳細パネルを開いたまま窓を 1000px に狭めると上限の 840px に収め直し、1280px に戻すと残した 880px に戻る。保存領域の値は 880px のまま（正常系）。"""
    # 準備
    url = write_preview(make_item("D-3"))
    seed_panel_width(page, 880)
    open_panel(page, open_preview, url, "#tab=decisions&view=table&id=D-3", PANEL_VIEWPORT)
    opened = panel_state(page)
    # 実行（窓を 1000px に狭める）
    page.set_viewport_size({"width": 1000, "height": 800})
    wait_for_value_now(page, 840)
    narrowed = panel_state(page)
    # 実行（窓を 1280px に戻す）
    page.set_viewport_size(PANEL_VIEWPORT)
    wait_for_value_now(page, 880)
    widened = panel_state(page)
    # 検証
    assert opened["panelWidth"] == 880
    assert narrowed["panelWidth"] == 840
    assert narrowed["separator"]["max"] == "840"
    assert narrowed["separator"]["now"] == "840"
    assert widened["panelWidth"] == 880
    assert widened["contentMargin"] == 880
    assert widened["separator"]["now"] == "880"
    assert read_stored_width(page) == "880"


def test_normal_when_window_widened_from_narrow(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, page: Page
) -> None:
    """幅 800px で詳細パネルを開いてから窓を 1280px に広げると、区切りが出て、残した 768px の幅に表の寄せも合わせて開き直す（正常系）。"""
    # 準備
    url = write_preview(make_item("D-3"))
    seed_panel_width(page, 768)
    # 実行（幅 800px で開く）
    open_panel(page, open_preview, url, "#tab=decisions&view=table&id=D-3", {"width": 800, "height": 800})
    narrow = panel_state(page)
    # 実行（窓を 1280px に広げる）
    page.set_viewport_size(PANEL_VIEWPORT)
    wait_for_value_now(page, 768)
    widened = panel_state(page)
    # 検証
    assert narrow["separator"]["display"] == "none"
    assert narrow["panelWidth"] == 800
    assert widened["separator"]["display"] != "none"
    assert page.locator(RESIZER).is_visible() is True
    assert widened["panelWidth"] == 768
    assert widened["contentMargin"] == 768
    assert widened["separator"]["max"] == "880"
    assert widened["separator"]["now"] == "768"
    assert read_stored_width(page) == "768"


def test_normal_when_embedded_html(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, page: Page
) -> None:
    """Markdown の本文に埋め込んだ HTML を本文の中に描き、チャートを動かし、部品の今の値を JSON でコピーする（正常系）。"""
    # 準備
    page.context.grant_permissions(CLIPBOARD_PERMISSIONS)
    url = write_preview(
        make_item("A-1", title="埋め込む資料"),
        make_item("A-2"),
        make_item("G-1", title="用語", aliases=["応答時間"], meaning="返すまでの時間"),
        bodies={"A-1.md": EMBEDDED_BODY},
    )
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector(CHART, timeout=DIAGRAM_TIMEOUT_MS)
    chart = page.locator(CHART).first
    # 実行（範囲のボタンを押す）
    page.get_by_role("button", name="実行", exact=True).click()
    # 検証（範囲は枠に入れず本文の要素として描かれ、スクリプトとイベントの属性は動かない）
    assert page.locator("aside.panel .md > .mdmark-html").count() == 1
    assert page.locator("aside.panel iframe").count() == 0
    assert page.locator(f"{RANGE} script, {RANGE} [onclick]").count() == 0
    assert page.evaluate("[window.__script, window.__onclick]") == [None, None]
    # 実行（拡大して、ドラッグする）
    fit_before = int(chart.locator(ZOOM_FIT).inner_text().rstrip("%"))
    chart.locator(ZOOM_IN).click()
    chart.locator(ZOOM_IN).click()
    fit_after = int(chart.locator(ZOOM_FIT).inner_text().rstrip("%"))
    scroll_before = viewport_scroll(chart)
    drag_in_viewport(page, chart, dx=-80, dy=-50)
    scroll_after = viewport_scroll(chart)
    # 検証（倍率が上がり、ドラッグで表示の位置が変わる。図の拡大の画面は開かず、拡大・縮小のボタンはチャートだけにある）
    assert fit_after > fit_before
    assert scroll_after["left"] > scroll_before["left"]
    assert scroll_after["top"] > scroll_before["top"]
    assert page.locator("dialog.viewer[open]").count() == 0
    assert page.locator(f"{RANGE} {ZOOM_IN}").count() == page.locator(CHART).count()
    assert page.locator(f"{RANGE} p button, {RANGE} .mdmark-param-knob button").count() == 0
    assert page.locator(f"{RANGE} [data-act='diagram-zoom']").count() == 0
    # 実行（スライダーを矢印キーで動かし、今の値をコピーする）
    page.focus(f"{RANGE} input[type=range]")
    page.keyboard.press("ArrowRight")
    page.get_by_role("button", name="今の値をコピー").click()
    # 検証（値とグラフが描き直され、クリップボードに今の値の JSON が入る）
    assert page.inner_text(f"{RANGE} .mdmark-param output") == "6"
    assert "今の値（6）" in page.inner_text(f"{RANGE} .mdmark-param .mdmark-diagram-legend")
    expect(page.locator(f"{RANGE} .mdmark-param-status")).not_to_be_empty()
    assert json.loads(page.evaluate("navigator.clipboard.readText()")) == {
        "rps": {"name": "リクエスト数", "value": 6}
    }
    # 検証（「ﾋﾟｰｸ時の応答時間 」の「応答時間」に用語のマーカーが付き、乗せると G-1 のツールチップが出る）
    page.hover(f"{RANGE} a.term")
    expect(page.locator("#term-tip")).to_be_visible()
    expect(page.locator("#term-tip")).to_contain_text("返すまでの時間")
    # 実行（範囲の中の A-2 のリンクを押す）
    history_length = page.evaluate("history.length")
    page.click(f"{RANGE} a.idref")
    # 検証
    expect(page.locator("aside.panel .d-title")).to_have_text("A-2の題")
    assert page.evaluate("location.hash") == "#tab=docs&id=A-2"
    assert page.evaluate("history.length") == history_length + 1


def test_normal_when_exported_as_html(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    open_preview: OpenPreview,
    page: Page,
    tmp_path: Path,
) -> None:
    """資料 1 件を、通信せずに描く 1 枚の HTML としてダウンロードさせる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", title="書き出す資料"),
        make_item("G-1", title="用語", aliases=["応答時間"], meaning="返すまでの時間"),
        bodies={"A-1.md": EXPORT_BODY},
    )
    url = str(call_tool("preview_url", workspace=str(root)).data["url"])
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector(CHART, timeout=DIAGRAM_TIMEOUT_MS)
    before = snapshot_tree(root)
    history_length = page.evaluate("history.length")
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    entry = page.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True)
    entry.click()
    # 実行
    with page.expect_download() as download_info:
        page.get_by_role("button", name="HTML でエクスポート").click()
    exported = save_download(download_info.value, tmp_path)
    # 検証（ダウンロードは A-1.html の 1 つで、画面は移らず、メニューを閉じた後は入口にフォーカスがある）
    assert exported.name == "A-1.html"
    assert page.evaluate("location.hash") == "#tab=docs&id=A-1"
    assert page.evaluate("history.length") == history_length
    expect(page.locator(EXPORT_MENU)).to_be_hidden()
    expect(entry).to_have_attribute("aria-expanded", "false")
    expect(entry).to_be_focused()
    # 検証（エクスポートの間にサーバーの配信への要求が無い）
    parts = urlsplit(url)
    server_origin = f"{parts.scheme}://{parts.netloc}"
    assert [request for request in requests if request.startswith(server_origin)] == []
    # 実行（通信を止めて file:// で開く）
    blocked: list[str] = []

    def _route(route: Route) -> None:
        """`file:` 以外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    opened = page.context.new_page()
    opened.route(_is_not_file_url, _route)
    opened.goto(exported.as_uri())
    opened.wait_for_selector(".mdmark figure", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（外への要求が 0 件で、本文とチャートが描かれる）
    assert blocked == []
    assert opened.locator(".mdmark").count() == 1
    assert "応答時間の段落" in opened.inner_text(".mdmark")
    assert opened.locator(".mdmark figure").count() == 2
    # 実行（「応答時間」に乗せ、スライダーを動かす）
    opened.hover(".mdmark-term")
    # 検証（G-1 の意味のツールチップが出て、グラフが描き直される）
    expect(opened.locator(".mdmark-term-tip")).to_be_visible()
    expect(opened.locator(".mdmark-term-tip")).to_contain_text("返すまでの時間")
    opened.focus("input[type=range]")
    opened.keyboard.press("ArrowRight")
    assert "今の値（6）" in opened.inner_text(".mdmark-param .mdmark-diagram-legend")
    opened.close()
    # ワークスペースは書き換えない
    assert snapshot_tree(root) == before


def test_normal_when_exported_as_markdown(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Page,
) -> None:
    """警告を挟んでから、埋め込んだ HTML を除いた Markdown をダウンロードさせる（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": MARKDOWN_EXPORT_BODY})
    open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector("dialog.full[open]")
    history_length = page.evaluate("history.length")
    downloads: list[Download] = []
    page.on("download", lambda download: downloads.append(download))
    menu = page.locator(EXPORT_MENU)
    entry = page.locator("dialog.full").get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True)
    entry.click()
    # 実行（Markdown でエクスポートを押す）
    page.get_by_role("button", name="Markdown でエクスポート").click()
    # 検証（ダウンロードされず、警告がモーダルを重ねずに同じメニューの中に出る）
    assert downloads == []
    expect(menu).to_contain_text("埋め込んだ HTML")
    assert page.locator("dialog[open]").count() == 1
    # 実行（戻る）
    menu.get_by_role("button", name="戻る", exact=True).click()
    # 検証（形式を選ぶメニューに戻り、フォーカスは「Markdown でエクスポート」にある）
    assert downloads == []
    expect(page.get_by_role("button", name="Markdown でエクスポート")).to_be_focused()
    # 実行（もう一度選び、警告の「エクスポート」を押す）
    page.get_by_role("button", name="Markdown でエクスポート").click()
    with page.expect_download() as download_info:
        menu.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True).click()
    download = download_info.value
    exported = Path(download.path()).read_text(encoding="utf-8")
    # 検証（A-1.md の 1 つで、範囲の外の文だけがある）
    assert download.suggested_filename == "A-1.md"
    assert "範囲の外の文" in exported
    assert "範囲の中の文" not in exported
    assert "<!-- html -->" not in exported
    # 検証（全画面が開いたまま入口にフォーカスがあり、ハッシュと履歴の数は開く前と同じ）
    expect(menu).to_be_hidden()
    expect(page.locator("dialog.full[open]")).to_have_count(1)
    expect(entry).to_be_focused()
    assert page.evaluate("location.hash") == "#tab=docs&id=A-1&full=1"
    assert page.evaluate("history.length") == history_length


def test_error_when_export_library_unavailable(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Page,
) -> None:
    """HTML でエクスポートするときに mdmark を読めず、ダウンロードせずに理由を出し、再試行でエクスポートする（異常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": "本文の段落\n"})
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md:not(.md-value).mdmark")
    downloads: list[Download] = []
    page.on("download", lambda download: downloads.append(download))
    # 画面を開いた後に、mdmark の CSS と JavaScript の配信元を切断する
    page.route(MDMARK_URL_PATTERN, lambda route: route.abort())
    # 実行
    page.get_by_role("button", name=EXPORT_ENTRY_NAME, exact=True).click()
    page.get_by_role("button", name="HTML でエクスポート").click()
    # 検証（ダウンロードされず、メニューの中に理由と「戻る」「再試行」が出る。本文は描かれたまま）
    menu = page.locator(EXPORT_MENU)
    alert = menu.get_by_role("alert")
    expect(alert).to_be_visible()
    expect(alert).to_contain_text("mdmark")
    expect(menu.get_by_role("button", name="戻る", exact=True)).to_be_visible()
    expect(menu.get_by_role("button", name="再試行")).to_be_visible()
    assert downloads == []
    assert "本文の段落" in page.inner_text("aside.panel .md:not(.md-value)")
    assert page.locator("aside.panel .lib-error").count() == 0
    # 実行（切断を外して再試行する）
    page.unroute(MDMARK_URL_PATTERN)
    with page.expect_download() as download_info:
        menu.get_by_role("button", name="再試行").click()
    # 検証
    assert download_info.value.suggested_filename == "A-1.html"
    expect(menu).to_be_hidden()


def test_normal_when_embedded_html_diff(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """時点を選ぶと、埋め込んだ HTML の範囲を原文の差分で出し、変更前・変更後の描いた結果に切り替える（正常系）。"""
    # 準備
    root = build_embedded_diff_workspace(make_workspace, call_tool)
    url = str(call_tool("preview_url", workspace=str(root)).data["url"])
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .df-raw", timeout=DIAGRAM_TIMEOUT_MS)
    history_length = page.evaluate("history.length")
    hash_text = page.evaluate("location.hash")
    removed = page.locator("aside.panel .df-raw .df-line.df-del")
    added = page.locator("aside.panel .df-raw .df-line.df-add")
    # 検証（開いた直後: 原文の行が消した行と足した行で出て、変えた文字が色分けされ、範囲の外の段落には印が無い）
    expect(removed).to_have_count(1)
    expect(added).to_have_count(1)
    assert "<p>2 つ目の段落</p>" in removed.inner_text()
    assert "<p>書き直した 2 つ目の段落</p>" in added.inner_text()
    assert removed.locator(".df-word.df-del").count() >= 1
    assert added.locator(".df-word.df-add").count() >= 1
    outside = page.locator("aside.panel .md > p[data-line-start]")
    assert outside.inner_text() == "範囲の外の段落"
    assert outside.evaluate("p => p.className + p.querySelectorAll('[class*=df-]').length") == "0"
    assert outside.get_attribute("data-df") is None
    # 実行（変更前）
    page.get_by_role("button", name="描いた結果（変更前）").click()
    # 検証（選んだ時点の範囲が、書き換える前の文で描かれる）
    before_view = page.locator("aside.panel .html-marked:visible .mdmark-html p")
    assert before_view.all_inner_texts() == ["1 つ目の段落", "2 つ目の段落", "3 つ目の段落"]
    # 実行（変更後）
    page.get_by_role("button", name="描いた結果（変更後）").click()
    # 検証（2 つ目の段落だけに「変わった」の印が付き、1・3 つ目の段落には印が無い）
    after_view = page.locator("aside.panel .html-marked:visible .mdmark-html p")
    assert after_view.evaluate_all("ps => ps.map(p => [p.textContent, p.dataset.df ?? null])") == [
        ["1 つ目の段落", None],
        ["書き直した 2 つ目の段落", "chg"],
        ["3 つ目の段落", None],
    ]
    # 検証（見せ方を切り替えても、ハッシュと履歴の数が変わらない）
    assert page.evaluate("location.hash") == hash_text
    assert page.evaluate("history.length") == history_length
