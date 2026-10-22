"""画面で項目を消す（詳細パネルの「項目を削除」で消す編集を保存待ちに溜め、まとめて保存する）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで操作し、ワークスペースの YAML と本文のファイルを読んで確かめる。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from typing import Any

from edit_helpers import (
    DETAIL_PANEL,
    EDIT_TOGGLE,
    PENDING_BUTTON,
    PENDING_PANEL,
    SAVE_BUTTON,
    SETTLE_MS,
    open_pending,
    read_edits,
    read_items,
    save_pending,
    wait_pending_count,
)
from playwright.sync_api import expect
from preview_helpers import OpenPreview, ServeWorkspace
from workspace_fixtures import RECORD_DIR, CallTool, MakeEdit, MakeItem, MakeWorkspace, WriteEdits

# メモ N-1 の本文
BODY = "消すメモの本文\n"


def test_normal(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    open_preview: OpenPreview,
    read_yaml: Any,
) -> None:
    """メモを消す編集を保存待ちに溜め、まとめて保存すると、メモとその本文が消え、メモの表から外れる（正常系）。"""
    # 準備
    url, root = serve_workspace(
        make_item("N-1", body="N-1.md"), make_item("N-2"), bodies={"N-1.md": BODY}
    )
    page = open_preview(url, "#tab=notes&id=N-1")
    page.wait_for_selector(f"{DETAIL_PANEL}.open")
    # 実行（消す編集を溜める）
    page.click(EDIT_TOGGLE)
    page.wait_for_selector(f"{DETAIL_PANEL} form.pe-form")
    page.get_by_role("button", name="項目を削除").click()
    wait_pending_count(page, 1)
    # 検証（保存する前）
    assert page.locator("tr[data-id='N-1'] .pm.pm-remove").count() == 1
    assert [item["id"] for item in read_items(root, "notes.yaml")] == ["N-1", "N-2"]
    # 実行（まとめて保存する）
    open_pending(page)
    save_pending(page)
    # 検証（保存した後）
    assert [item["id"] for item in read_items(root, "notes.yaml")] == ["N-2"]
    assert not (root / RECORD_DIR / "N-1.md").exists()
    changes = read_yaml(root, "changes.yaml")
    first = changes["sets"][0]
    assert first["summary"] == "画面からの編集"
    assert [entry["id"] for entry in first["removed"]] == ["N-1"]
    assert changes["pending"].get("added", []) == []
    assert changes["pending"].get("changed", []) == []
    assert changes["pending"].get("removed", []) == []
    assert read_edits(root) == []
    expect(page.locator("tr[data-id='N-1']")).to_have_count(0, timeout=SETTLE_MS)
    assert page.locator("tr[data-id='N-2']").count() == 1


def test_error_when_item_referenced(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    call_tool: CallTool,
    open_preview: OpenPreview,
) -> None:
    """ほかの項目が指している項目を消す編集は、保存しても何も書かず、消す行に指している項目と理由を出す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2", depends_on=["D-1"]))
    write_edits(
        root,
        make_edit("E-1", target="D-1", op="item-remove", key=None, value=None, before=None),
        make_edit("E-2", target="D-2", value="編集中の答え", before=""),
    )
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    page = open_preview(str(served.data["url"]), "#tab=decisions&view=board")
    page.wait_for_selector(PENDING_BUTTON)
    open_pending(page)
    # 実行
    page.click(SAVE_BUTTON)
    page.wait_for_selector(f"{PENDING_PANEL} .pe-alert", timeout=SETTLE_MS)
    # 検証
    assert [item["id"] for item in read_items(root, "decisions.yaml")] == ["D-1", "D-2"]
    assert read_items(root, "decisions.yaml")[1].get("answer") is None
    assert len(read_edits(root)) == 2
    row = page.locator(f"{PENDING_PANEL} #pe-row-E-1")
    assert "D-2" in row.inner_text()
    assert "が指しているため削除できません。" in row.inner_text()
