"""画面で項目を編集して保存する（詳細パネルと設定の画面で書き換えを保存待ちに溜め、取り消し、まとめて保存する）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで操作し、ワークスペースの YAML と `config.yaml` を読んで確かめる。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from typing import Any

import yaml
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
from playwright.sync_api import Page, expect
from preview_helpers import OpenPreview, ServeWorkspace, pick_history_point
from workspace_fixtures import RECORD_DIR, CallTool, MakeEdit, MakeItem, MakeWorkspace, StartServer, WriteEdits

# タグの語彙を持つ設定に足す項目
TAGS = [{"name": "画面"}, {"name": "記録の形"}]

# 溜めた編集の取り消しに使う、項目を指す見出しの文字
UNDO_TASK_STATUS = "T-1 の状態の編集を取り消す"

# 表示の設定のボタンと、設定の画面
SETTINGS_BUTTON = "header.topbar button.settings-btn"
SETTINGS_SCREEN = ".pe-ws"

# トップバーの題名
TOPBAR_TITLE = "header.topbar .brand-sub"


def _edit_form_ready(page: Page) -> None:
    """詳細パネルの「編集する」を押して、編集の表示のフォームが出るのを待つ。"""
    page.click(EDIT_TOGGLE)
    page.wait_for_selector(f"{DETAIL_PANEL} form.pe-form")


def _open_item(page: Page, hash_text: str, item_id: str) -> None:
    """URL のハッシュを書き換えて項目の詳細パネルを開き、見出しにその ID が出るのを待つ。"""
    page.evaluate("hash => { location.hash = hash; }", hash_text)
    page.wait_for_function(
        "id => document.querySelector('aside.panel .panel-kind')?.textContent?.includes(id)",
        arg=item_id,
        timeout=SETTLE_MS,
    )


def _open_settings_screen(page: Page) -> None:
    """表示の設定のパネルの「設定を編集する」で設定の画面を開く。"""
    page.click(SETTINGS_BUTTON)
    page.get_by_role("button", name="設定を編集する").click()
    page.wait_for_selector(SETTINGS_SCREEN)


def _commit_text(page: Page, label: str, value: str) -> None:
    """名前で引いた入力欄に値を入れて離れる。"""
    field = page.get_by_label(label, exact=True)
    field.fill(value)
    field.blur()


def test_normal(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    read_yaml: Any,
) -> None:
    """検討事項の答え・タグ・案と、タスクの状態を保存待ちに溜め、開き直しても残り、1 件を取り消してからまとめて保存する（正常系）。"""
    # 準備
    options = [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}]
    url, root = serve_workspace(
        make_item("D-1", tags=["画面"], options=options),
        make_item("T-1"),
        settings={**valid_settings, "tags": TAGS},
    )
    page = open_preview(url, "#tab=decisions&view=board&id=D-1")
    page.wait_for_selector(f"{DETAIL_PANEL}.open")
    # 実行（D-1 を編集して溜める）
    _edit_form_ready(page)
    answer = page.get_by_label("決定内容", exact=True)
    answer.fill("案 C にする")
    answer.blur()
    wait_pending_count(page, 1)
    tags = page.get_by_label("タグを追加")
    tags.fill("記録の形")
    tags.press("Enter")
    wait_pending_count(page, 2)
    page.get_by_role("button", name="案を追加").click()
    draft = page.get_by_label("案 C の中身")
    draft.fill("案 C")
    draft.blur()
    wait_pending_count(page, 3)
    page.get_by_role("radio", name="採用").nth(2).check()
    wait_pending_count(page, 4)
    # 検証（D-1 のバッジ）
    assert page.locator(".pe-field[data-key='answer'] .pm").count() == 1
    assert page.locator(".pe-field[data-key='tags'] .pm").count() == 1
    assert "is-pending" in (page.locator(".pe-opt[data-key='C']").get_attribute("class") or "")
    assert page.locator(".board button.card[data-id='D-1'] .pm.pm-pending").count() == 1
    # 実行（T-1 を編集して溜める）
    _open_item(page, "#tab=tasks&view=board&id=T-1", "T-1")
    _edit_form_ready(page)
    page.get_by_label("状態", exact=True).select_option("中止")
    wait_pending_count(page, 5)
    # 実行（ページを開き直す）
    page.reload()
    page.wait_for_selector(PENDING_BUTTON, timeout=SETTLE_MS)
    # 検証（開き直した後も同じバッジと件数）
    wait_pending_count(page, 5)
    assert page.locator(".board button.card[data-id='T-1'] .pm.pm-pending").count() == 1
    open_preview(url, "#tab=decisions&view=board&id=D-1")
    page.wait_for_selector(f"{DETAIL_PANEL}.open")
    assert page.locator(".board button.card[data-id='D-1'] .pm.pm-pending").count() == 1
    assert len(read_edits(root)) == 5
    # 実行（保存待ちのパネルを開き、T-1 の編集を取り消す）
    open_pending(page)
    assert page.locator(f"{PENDING_PANEL} .pe-row").count() == 5
    page.get_by_role("button", name=UNDO_TASK_STATUS).click()
    wait_pending_count(page, 4)
    # 検証（取り消した後、D-1 の 4 件は残る）
    assert page.locator(f"{PENDING_PANEL} .pe-row").count() == 4
    assert {edit["target"] for edit in read_edits(root)} == {"D-1"}
    # 実行（まとめて保存する）
    save_pending(page)
    # 検証（保存した後）
    decision = read_items(root, "decisions.yaml")[0]
    assert decision["answer"] == "案 C にする"
    assert decision["tags"] == ["画面", "記録の形"]
    assert [option["key"] for option in decision["options"] if option.get("adopted")] == ["C"]
    assert decision["updated_by"] == "user"
    assert decision["history"][-1]["by"] == "user"
    task = read_items(root, "tasks.yaml")[0]
    assert task["status"] == "未着手"
    assert task.get("history", []) == []
    assert read_edits(root) == []
    assert page.locator(PENDING_BUTTON).count() == 0
    assert page.locator(PENDING_PANEL).count() == 0
    assert page.locator(".board button.card[data-id='D-1'] .pm").count() == 0
    assert "案 C にする" in page.inner_text(f"{DETAIL_PANEL} .panel-body")
    changes = read_yaml(root, "changes.yaml")
    assert changes["sets"][0]["changed"] == ["D-1"]


def test_normal_when_settings(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """設定の画面で題名とタグの語彙を書き換えて溜め、まとめて保存すると、画面を開き直さずにトップバーの題名が変わる（正常系）。"""
    # 準備
    url, root = serve_workspace(
        make_item("D-1"), settings={**valid_settings, "summary": "話し合い", "tags": TAGS}
    )
    page = open_preview(url, "#tab=decisions&view=board")
    # 実行
    _open_settings_screen(page)
    _commit_text(page, "題名", "画面の編集")
    wait_pending_count(page, 1)
    vocabulary = page.get_by_label("タグの語彙を追加")
    vocabulary.fill("保存")
    vocabulary.press("Enter")
    wait_pending_count(page, 2)
    open_pending(page)
    save_pending(page)
    # 検証
    config = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    assert config["summary"] == "画面の編集"
    assert [tag["name"] for tag in config["tags"]] == ["画面", "記録の形", "保存"]
    assert read_edits(root) == []
    expect(page.locator(TOPBAR_TITLE)).to_have_text("画面の編集", timeout=SETTLE_MS)


def test_normal_when_withdraw(
    serve_workspace: ServeWorkspace,
    make_item: MakeItem,
    open_preview: OpenPreview,
) -> None:
    """検討事項の状態を「対象外」にし、調査を取り下げにして保存すると、調査の表の行に取り下げの札が出る（正常系）。"""
    # 準備
    url, root = serve_workspace(make_item("D-1"), make_item("R-1"))
    page = open_preview(url, "#tab=decisions&view=board&id=D-1")
    page.wait_for_selector(f"{DETAIL_PANEL}.open")
    # 実行
    _edit_form_ready(page)
    page.get_by_label("状態", exact=True).select_option("対象外")
    wait_pending_count(page, 1)
    _open_item(page, "#tab=research&id=R-1", "R-1")
    _edit_form_ready(page)
    page.get_by_label("取り下げ", exact=True).check()
    wait_pending_count(page, 2)
    open_pending(page)
    save_pending(page)
    # 検証
    decision = read_items(root, "decisions.yaml")[0]
    assert decision["status"] == "対象外"
    assert decision["updated_by"] == "user"
    research = read_items(root, "research.yaml")[0]
    assert research["withdrawn"] is True
    assert research["updated_by"] == "user"
    assert page.locator("tr[data-id='R-1'] .wd-badge").count() == 1


def test_normal_when_diff_view(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    call_tool: CallTool,
    open_preview: OpenPreview,
) -> None:
    """保存待ちのパネルを開いたまま差分の表示にすると、パネルを閉じて編集の操作・バッジ・件数を出さず、差分の表示をやめると出し直す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    ws = {"workspace": str(root)}
    # 変更履歴に時点が 1 つ残るよう、項目を書き換えてまとめる
    assert call_tool("update", **ws, id="D-1", item={"title": "書き換えた問い"}).is_error is False
    assert call_tool("commit", **ws, summary="最初のまとまり").is_error is False
    updated = read_items(root, "decisions.yaml")[0]["updated"]
    write_edits(root, make_edit("E-1", value="編集中の答え", before="", base=updated))
    served = call_tool("preview_url", **ws)
    assert served.data is not None
    page = open_preview(str(served.data["url"]), "#tab=decisions&view=board")
    page.wait_for_selector(PENDING_BUTTON)
    open_pending(page)
    # 実行（時点を選んで差分の表示にする）
    pick_history_point(page, "最初のまとまり")
    # 検証（差分の表示中）
    assert page.locator(PENDING_PANEL).count() == 0
    assert page.locator(PENDING_BUTTON).count() == 0
    assert page.locator(".board button.card[data-id='D-1'] .pm").count() == 0
    page.evaluate("location.hash = '#tab=decisions&view=board&id=D-1'")
    page.wait_for_selector(f"{DETAIL_PANEL}.open")
    assert page.locator(EDIT_TOGGLE).count() == 0
    assert len(read_edits(root)) == 1
    # 実行（差分の表示をやめる）
    page.get_by_role("button", name="差分の表示をやめる").click()
    # 検証（差分の表示をやめた後）
    wait_pending_count(page, 1)
    assert page.locator(".board button.card[data-id='D-1'] .pm.pm-pending").count() == 1
    assert page.locator(EDIT_TOGGLE).count() == 1
    assert len(read_edits(root)) == 1


def test_error_when_item_changed_after_staged(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    call_tool: CallTool,
    open_preview: OpenPreview,
) -> None:
    """溜めた後に AI が同じ項目を書き換えると、保存は何も書かず、その項目の行に理由を出す。その編集を取り消して保存し直すと、残りが書かれる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("T-1"))
    write_edits(
        root,
        make_edit("E-1", value="編集中の答え", before=""),
        make_edit("E-2", target="T-1", key="status", value="完了", before="未着手"),
    )
    ws = {"workspace": str(root)}
    # 溜めた後に、話し合いの途中で Claude Code が D-1 のタイトルを書き換える
    assert call_tool("update", **ws, id="D-1", item={"title": "AI が書き換えた題"}).is_error is False
    served = call_tool("preview_url", **ws)
    assert served.data is not None
    page = open_preview(str(served.data["url"]), "#tab=decisions&view=board")
    page.wait_for_selector(PENDING_BUTTON)
    open_pending(page)
    # 実行（まとめて保存する）
    page.click(SAVE_BUTTON)
    page.wait_for_selector(f"{PENDING_PANEL} .pe-alert", timeout=SETTLE_MS)
    # 検証（書き込めなかった）
    assert read_items(root, "tasks.yaml")[0]["status"] == "未着手"
    decision = read_items(root, "decisions.yaml")[0]
    assert decision["title"] == "AI が書き換えた題"
    assert decision.get("answer") is None
    assert len(read_edits(root)) == 2
    row = page.locator(f"{PENDING_PANEL} #pe-row-E-1")
    assert "に AI がこの項目を書き換えたため、書き込めません。" in row.inner_text()
    # 実行（D-1 の編集を取り消して、もう一度保存する）
    page.get_by_role("button", name="D-1 の決定内容の編集を取り消す").click()
    wait_pending_count(page, 1)
    save_pending(page)
    # 検証（残りが書かれた）
    assert read_items(root, "tasks.yaml")[0]["status"] == "完了"
    assert read_items(root, "decisions.yaml")[0]["title"] == "AI が書き換えた題"
    assert read_edits(root) == []


def test_error_when_server_unreachable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    start_server: StartServer,
    open_preview: OpenPreview,
) -> None:
    """保存待ちのパネルを開いた後にサーバーが止まると、保存できなかった旨を出し、溜めた編集を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1", value="編集中の答え", before=""))
    server = start_server()
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    page = open_preview(str(served.data["url"]), "#tab=decisions&view=board")
    page.wait_for_selector(PENDING_BUTTON)
    open_pending(page)
    # 実行（サーバーの標準入力を閉じて止め、保存する）
    server.close_stdin()
    server.wait_exit()
    page.click(SAVE_BUTTON)
    page.wait_for_selector(f"{PENDING_PANEL} .pe-alert", timeout=SETTLE_MS)
    # 検証
    assert "保存できませんでした" in page.inner_text(f"{PENDING_PANEL} .pe-alert")
    assert page.locator(f"{PENDING_PANEL} #pe-row-E-1").count() == 1
    assert read_items(root, "decisions.yaml")[0].get("answer") is None
    assert len(read_edits(root)) == 1
