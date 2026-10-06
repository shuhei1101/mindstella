"""プレビューを開く（サーバーが配る URL と、`export` が書き出した配る書き出しを開く）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from preview_comment_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    PILL,
    THREE_LINE_BODY,
    select_text,
    select_text_for_pill,
)
from preview_drawer_helpers import FILTER_BUTTON, badge_text, checked_values, open_drawer
from preview_fixture_types import BODY_WITH_DIAGRAM, OpenPreview, WritePreview
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, StartServer

# 描画のライブラリの配信元への要求（全て失敗させるときの URL の形）
LIBRARY_HOST_PATTERN = "https://cdn.jsdelivr.net/**"

# 描画のライブラリを描いた後の図（SVG）が出るまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 書き換えや接続の切れが画面に出るまで待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 400

# コメントの入力欄・結果・「レビューに追加」のボタン・接続の状態
SEND_TEXTAREA = "aside.panel form.send textarea"
SEND_MESSAGE = "aside.panel form.send .send-msg"
SEND_BUTTON = "aside.panel form.send button[type=submit]"
CONNECTION = "header.topbar .conn"

# サーバーにつながらないとき、接続の状態の全文が出る幅（幅 1440px 以下は短い文言になる）
WIDE_SIZE = {"width": 1441, "height": 900}

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
    assert page.locator("aside.panel .md h4").count() == 1
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
    assert page.locator("aside.panel .md h4").count() == 1
    assert page.locator("aside.panel .mermaid svg").count() == 1
    # コメントのボタン・入力・選んだ箇所の入口が無く、接続の状態も出ていない
    assert page.locator(COMMENTS_BUTTON).count() == 0
    assert page.locator("aside.panel form.send").count() == 0
    assert page.locator(SEND_TEXTAREA).count() == 0
    assert page.locator(SEND_BUTTON).count() == 0
    assert page.locator(CONNECTION).count() == 0
    select_text(page, "aside.panel .md", "本文の段落")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    assert page.locator(PILL).count() == 0


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
    page.wait_for_selector("aside.panel.open .md .lib-error")
    # 検証
    map_notice = page.inner_text("main .lib-error[role=alert]")
    assert "読み込めなかったライブラリ: elkjs" in map_notice
    assert "通信を確認して、ページを再読み込みしてください。" in map_notice
    body_notice = page.inner_text("aside.panel .md .lib-error[role=alert]")
    assert "読み込めなかったライブラリ" in body_notice
    for name in ("marked", "DOMPurify", "mermaid"):
        assert name in body_notice
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
    page.wait_for_selector("aside.panel .md")
    # 実行（本文の 2 行目の文を選ぶと、近くに入口が出る）
    select_text_for_pill(page, "aside.panel .md", "言い換えたい文")
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
    page.focus(LIST_SEND_BUTTON)
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{COMMENTS_PANEL} .send-msg.sent", timeout=UPDATE_TIMEOUT_MS)
    # 検証（送った後）
    pending = call_tool("submissions", workspace=str(root))
    assert pending.data is not None
    assert [
        (item["target"], item["loc"]["kind"], item["loc"]["start"], item["body"])
        for item in pending.data["items"]
    ] == [("A-1", "body", 2, "ここは言い換える")]
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "0"
    assert page.locator(f"{COMMENTS_PANEL} .comments-list li").count() == 0
    # 検証（入口は Esc で閉じる）
    select_text_for_pill(page, "aside.panel .md", "言い換えたい文")
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
