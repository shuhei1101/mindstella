"""画面で項目を足す（種類ごとの画面の「項目を追加」で足す編集を保存待ちに溜め、まとめて保存する）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで操作し、ワークスペースの YAML を読んで確かめる。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from edit_helpers import (
    SETTLE_MS,
    open_pending,
    read_edits,
    read_items,
    save_pending,
    wait_pending_count,
)
from playwright.sync_api import Page, expect
from preview_helpers import OpenPreview, ServeWorkspace
from workspace_fixtures import MakeItem

# 項目を追加するボタンと、足す項目の入力のパネル・最初の入力欄
ADD_BUTTON = "button.pe-add"
ADD_PANEL = "aside.pe-add-panel"
ADD_TITLE_INPUT = f"{ADD_PANEL} [data-first]"

# 足す項目のカードと、メモの表の足す項目の行
ADDED_CARD = ".board button.card[data-new-id]"
ADDED_ROW = "table tr[data-new-id]"

# 保存待ちの item-add の value.options が、採用まで含めて渡した並びになったかを読む。
# wait_for_function は返った Promise を真として扱うため、読みに行った結果を window に置き、次に呼ばれたときに返す
ADDED_OPTIONS_JS = """(expected) => {
  fetch('/api/edits').then(r => r.json()).then(d => {
    window.addedOptionsSaved = d.items.some(e => e.op === 'item-add' && JSON.stringify(e.value.options ?? []) === JSON.stringify(expected));
  });
  return window.addedOptionsSaved === true;
}"""


def _add_titled(page: Page, title: str) -> None:
    """「項目を追加」を押し、タイトルを書いて入力欄を離れる。"""
    page.click(ADD_BUTTON)
    page.wait_for_selector(ADD_PANEL)
    page.locator(ADD_TITLE_INPUT).fill(title)
    page.locator(ADD_TITLE_INPUT).blur()


def _wait_added_options(page: Page, expected: list[dict[str, object]]) -> None:
    """保存待ちの item-add の value.options が expected になるのを待つ。"""
    page.evaluate("() => { window.addedOptionsSaved = false; }")
    page.wait_for_function(ADDED_OPTIONS_JS, arg=expected, timeout=SETTLE_MS)


def test_normal(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    open_preview: OpenPreview,
) -> None:
    """タスクとメモを足す編集を保存待ちに溜め、まとめて保存すると、サーバーが振った ID で足されて画面に出る（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("T-1"), make_item("N-1"))
    page = open_preview(url, "#tab=tasks&view=board")
    # 実行（タスクを足す編集を溜める）
    _add_titled(page, "画面を作る")
    wait_pending_count(page, 1)
    # 検証（保存する前のタスクのカード）
    page.wait_for_selector(ADDED_CARD, timeout=SETTLE_MS)
    added = page.locator(ADDED_CARD)
    assert added.count() == 1
    assert added.locator(".mono").count() == 0
    assert added.locator(".pe-noid").inner_text() == "ID は保存で決まる"
    assert added.locator(".pm.pm-pending").count() == 1
    # 実行（メモを足す編集を溜める）
    page.evaluate("location.hash = '#tab=notes'")
    page.wait_for_selector("table.grid")
    _add_titled(page, "画面の形")
    wait_pending_count(page, 2)
    page.wait_for_selector(ADDED_ROW, timeout=SETTLE_MS)
    # 検証（保存する前）
    assert [edit["op"] for edit in read_edits(root)] == ["item-add", "item-add"]
    assert [item["id"] for item in read_items(root, "tasks.yaml")] == ["T-1"]
    assert [item["id"] for item in read_items(root, "notes.yaml")] == ["N-1"]
    # 実行（まとめて保存する）
    open_pending(page)
    save_pending(page)
    # 検証（保存した後）
    tasks = read_items(root, "tasks.yaml")
    assert [(item["id"], item["title"], item["updated_by"]) for item in tasks[1:]] == [
        ("T-2", "画面を作る", "user")
    ]
    notes = read_items(root, "notes.yaml")
    assert [(item["id"], item["title"], item["updated_by"]) for item in notes[1:]] == [
        ("N-2", "画面の形", "user")
    ]
    assert read_edits(root) == []
    expect(page.locator("table tr[data-id='N-2']")).to_have_count(1, timeout=SETTLE_MS)
    assert page.locator(ADDED_ROW).count() == 0
    page.evaluate("location.hash = '#tab=tasks&view=board'")
    expect(page.locator(".board button.card[data-id='T-2']")).to_have_count(1, timeout=SETTLE_MS)


def test_normal_when_options_written(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    open_preview: OpenPreview,
) -> None:
    """追加の入力で検討事項に案を書いて採用を選び、まとめて保存すると、案を持つ決定済みの検討事項が足される（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("D-1", status="未決定"))
    page = open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector("table tr[data-id='D-1']")
    # 実行（タイトルを書く）
    _add_titled(page, "保存の単位")
    wait_pending_count(page, 1)
    # 実行（案 A・B を書く）
    for key, content in (("A", "項目ごと"), ("B", "まとめて")):
        page.get_by_role("button", name="案を追加").click()
        area = page.get_by_label(f"案 {key} の中身")
        area.fill(content)
        area.blur()
    _wait_added_options(page, [{"key": "A", "content": "項目ごと"}, {"key": "B", "content": "まとめて"}])
    # 実行（案 B を採用する）
    page.get_by_role("radio", name="採用").nth(1).check()
    _wait_added_options(
        page, [{"key": "A", "content": "項目ごと"}, {"key": "B", "content": "まとめて", "adopted": True}]
    )
    # 実行（閉じて開き直す）
    page.get_by_role("button", name="追加の入力を閉じる").click()
    page.wait_for_selector(ADD_PANEL, state="detached")
    page.click(f"{ADDED_ROW} .row-open")
    page.wait_for_selector(ADD_PANEL)
    # 検証（保存する前）
    expect(page.get_by_label("案 A の中身")).to_have_value("項目ごと")
    expect(page.get_by_label("案 B の中身")).to_have_value("まとめて")
    expect(page.get_by_role("radio", name="採用").nth(1)).to_be_checked()
    expect(page.get_by_role("radio", name="採用").nth(0)).not_to_be_checked()
    assert [edit["op"] for edit in read_edits(root)] == ["item-add"]
    wait_pending_count(page, 1)
    # 実行（まとめて保存する）
    page.get_by_role("button", name="追加の入力を閉じる").click()
    page.wait_for_selector(ADD_PANEL, state="detached")
    open_pending(page)
    save_pending(page)
    # 検証（保存した後）
    added = read_items(root, "decisions.yaml")[1:]
    assert [(item["id"], item["title"], item["status"], item["updated_by"]) for item in added] == [
        ("D-2", "保存の単位", "決定済み", "user")
    ]
    assert added[0]["options"] == [
        {"key": "A", "content": "項目ごと"},
        {"key": "B", "content": "まとめて", "adopted": True},
    ]
    assert "A" not in added[0]
    assert "B" not in added[0]
    assert read_edits(root) == []
    expect(page.locator("table tr[data-id='D-2']")).to_have_count(1, timeout=SETTLE_MS)
