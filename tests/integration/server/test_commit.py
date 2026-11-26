"""commit（書き換えのまとまり）の結合テスト。"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from .fixture_types import (
    CallTool,
    LockDirs,
    MakeItem,
    MakeWorkspace,
    McpServer,
    SnapshotTree,
)
from .history_helpers import (
    DECISION_ITEM,
    add_item,
    commit,
    read_changes,
    read_history,
    remove_item,
    update_item,
)
from session_fixtures import SessionWorld, wait_until
from workspace_fixtures import (
    MDMARK_COMMAND_ENV,
    NOOP_MDMARK_COMMAND,
    RECORD_DIR,
    TEST_SESSION_ID,
    mindstella_session,
)

from .test_work_done_notify import NO_SEND_WAIT_SEC, WEBHOOK_FILE_ENV, FakeWebhook

# 手で崩した `changes.yaml`（`pending` から `added` を消した）
BROKEN_CHANGES = "last_seq: 0\nsets: []\npending:\n  changed: []\n"


def test_normal(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """まだまとめていない書き換えを、説明つきのまとまりにする（正常系）。"""
    # 準備
    root = make_workspace()
    decision_id = add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    update_item(call_tool, root, decision_id, {"answer": "種類ごとに分ける"})
    task_id = add_item(call_tool, root, "task", {"title": "決める", "kind": "作業", "status": "未着手"})
    first = read_changes(root)
    before = {
        "decisions": (root / RECORD_DIR / "decisions.yaml").read_bytes(),
        "tasks": (root / RECORD_DIR / "tasks.yaml").read_bytes(),
    }
    # 実行
    result = call_tool("commit", workspace=str(root), summary="D-1 を決め、T-1 を積む")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["id"] == "V-2"
    assert result.data["added"] == [task_id]
    assert result.data["changed"] == [decision_id]
    assert result.data["summary"] == "D-1 を決め、T-1 を積む"
    changes = read_changes(root)
    assert changes["sets"][0]["id"] == "V-2"
    assert changes["sets"][0]["until_seq"] == changes["last_seq"]
    assert changes["pending"] == {"added": [], "changed": []}
    history_seq = read_history(root)["D-1"]["history"][0]["seq"]
    assert first["sets"][0]["until_seq"] < history_seq <= changes["sets"][0]["until_seq"]
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == before["decisions"]
    assert (root / RECORD_DIR / "tasks.yaml").read_bytes() == before["tasks"]


def test_normal_when_nothing_pending(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """まとめる書き換えが無いときは、まとまりを足さない（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    before = snapshot_tree(root)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="何もしない")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["id"] is None
    assert result.data["at"] is None
    assert result.data["summary"] is None
    assert result.data["added"] == []
    assert result.data["changed"] == []
    assert snapshot_tree(root) == before


def test_error_when_summary_empty(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """空白だけの説明は引数の誤りにして、何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    before = snapshot_tree(root)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="   ")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 引数の誤り: summary:")
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("commit", workspace=str(root), summary="a")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """手で崩した changes.yaml が残っていると、まとめずに合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"changes.yaml": BROKEN_CHANGES})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="a")
    # 検証
    assert result.is_error is True
    assert "changes.yaml: pending" in result.text
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、まとめずにエラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="a")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_normal_when_item_removed(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """消した項目だけがあるときも、まとまりを 1 つ足す（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "note", {"title": "メモ", "content": "中身"})
    add_item(call_tool, root, "note", {"title": "重複したメモ", "content": "中身"})
    commit(call_tool, root, "足す")
    remove_item(call_tool, root, "N-2")
    # 実行
    result = call_tool("commit", workspace=str(root), summary="重複した N-2 を消す")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["id"] == "V-2"
    assert result.data["removed"] == [{"id": "N-2", "kind": "note", "title": "重複したメモ"}]
    changes = read_changes(root)
    assert [entry["id"] for entry in changes["sets"][0]["removed"]] == ["N-2"]
    pending = changes["pending"]
    assert pending["added"] == []
    assert pending["changed"] == []
    assert pending.get("removed", []) == []


def test_normal_when_external_pending(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """外部の変更が残っていれば、外部の変更のまとまりにして自分のまとまりは作らない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        raw_files={
            "changes.yaml": "last_seq: 1\nsets: []\npending:\n  added: []\n  changed:\n  - D-1\n  by: external\n"
        },
    )
    # 実行
    result = call_tool("commit", workspace=str(root), summary="AI の書き換え")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["id"] is None
    changes = read_changes(root)
    first = changes["sets"][0]
    assert (first["by"], first["summary"], first["changed"]) == ("external", "ほかのセッションの書き込み", ["D-1"])
    assert changes["pending"] == {"added": [], "changed": []}


def test_error_when_not_mindstella_session(
    make_workspace: MakeWorkspace, mcp_server: McpServer
) -> None:
    """MindStella のセッションでない呼び出しではまとめない（異常系）。"""
    # 準備
    root = make_workspace()
    add_item(mcp_server.call, root, "decision", DECISION_ITEM)
    mindstella_session(mcp_server.state_home, root)
    before = (root / RECORD_DIR / "changes.yaml").read_bytes()
    other = {"cwd": str(root), "claude_session_id": "c-other"}
    # 実行
    result = mcp_server.call("commit", workspace=str(root), summary="まとめる", session=other)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: MindStella のセッションだけが呼べます: commit")
    assert (root / RECORD_DIR / "changes.yaml").read_bytes() == before


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    """200 を返却する Webhook の Mock を起動し、テストの後で閉じる。"""
    fake = FakeWebhook()
    fake.start()
    yield fake
    fake.close()



def _start_with_webhook(world: SessionWorld, webhook: FakeWebhook) -> tuple[McpServer, Path]:
    """Webhook の URL を記載した設定のファイルを指定して常駐サーバーを起動し、MindStella のセッションを持つワークスペースを作る。"""
    path = world.root / "webhook.ini"
    path.write_text(f"{webhook.url}\n", encoding="utf-8")
    server = world.start({MDMARK_COMMAND_ENV: NOOP_MDMARK_COMMAND, WEBHOOK_FILE_ENV: str(path)})
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, session=TEST_SESSION_ID, claude_session_id="c-mindstella-test")
    return server, world.folder()


def test_normal_when_hand_back(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """hand_back が真では、まとめる書き換えが無くても、結果を返却した後に作業の完了の通知を呼ぶ（正常系）。"""
    # 準備
    server, root = _start_with_webhook(session_world, webhook)
    add_item(server.call, root, "decision", DECISION_ITEM)
    assert server.call("commit", workspace=str(root), summary="足す").is_error is False
    before = (root / RECORD_DIR / "changes.yaml").read_bytes()
    # 実行
    result = server.call("commit", workspace=str(root), summary="質問に答えた", hand_back=True)
    wait_until(lambda: webhook.requests)
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["id"] is None
    assert len(webhook.requests) == 1
    assert (root / RECORD_DIR / "changes.yaml").read_bytes() == before


def test_normal_when_not_hand_back(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """hand_back を渡さない commit では、まとまりを追加しても通知を呼ばない（正常系）。"""
    # 準備
    server, root = _start_with_webhook(session_world, webhook)
    add_item(server.call, root, "decision", DECISION_ITEM)
    # 実行
    result = server.call("commit", workspace=str(root), summary="D-1 を足す")
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["id"] is not None
    assert webhook.requests == []


def _add_task(server: McpServer, root: Path, title: str, status: str) -> str:
    """状態を指定してタスクを追加し、ID を返却する。"""
    return add_item(server.call, root, "task", {"title": title, "kind": "作業", "status": status})


def test_error_when_open_tasks_remain(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """hand_back が真で、未着手・進行中のタスクが残っていれば、まとめずに残っているタスクを返却して拒む（異常系）。"""
    # 準備
    server, root = _start_with_webhook(session_world, webhook)
    ids = [
        _add_task(server, root, "画面を作る", "未着手"),
        _add_task(server, root, "API を作る", "進行中"),
        _add_task(server, root, "後で決める", "保留"),
        _add_task(server, root, "調べる", "完了"),
    ]
    before = (root / RECORD_DIR / "changes.yaml").read_bytes()
    # 実行
    result = server.call("commit", workspace=str(root), summary="T-1 を積む", hand_back=True)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert result.is_error is True
    lines = result.text.splitlines()
    assert lines[0].startswith("エラー: 未着手・進行中のタスクが残っています")
    assert any(line.startswith(f"{ids[0]}: 未着手") for line in lines)
    assert any(line.startswith(f"{ids[1]}: 進行中") for line in lines)
    assert not any(line.startswith(f"{ids[2]}:") or line.startswith(f"{ids[3]}:") for line in lines)
    assert (root / RECORD_DIR / "changes.yaml").read_bytes() == before
    assert read_changes(root)["pending"]["added"] == ids
    assert webhook.requests == []


def test_normal_when_open_tasks_during_work(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """hand_back を渡さない commit は、未着手・進行中のタスクが残っていてもまとめる（正常系）。"""
    # 準備
    root = make_workspace()
    task_id = add_item(call_tool, root, "task", {"title": "画面を作る", "kind": "作業", "status": "未着手"})
    # 実行
    result = call_tool("commit", workspace=str(root), summary="T-1 を積む")
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["id"]
    assert result.data["added"] == [task_id]
    assert "status: 未着手" in (root / RECORD_DIR / "tasks.yaml").read_text(encoding="utf-8")


def test_error_when_tasks_schema_mismatch_on_hand_back(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """hand_back が真で、手で崩した tasks.yaml ではまとめず、合わない箇所を返却する（異常系）。"""
    # 準備
    server, root = _start_with_webhook(session_world, webhook)
    _add_task(server, root, "画面を作る", "未着手")
    tasks = root / RECORD_DIR / "tasks.yaml"
    seq = read_changes(root)["last_seq"]
    broken = "\n".join(line for line in tasks.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("status:"))
    tasks.write_text(broken + "\n", encoding="utf-8")
    # 手で崩した書き換えを常駐サーバーの変更の検出が記録し終えてから、呼ぶ前の中身を取る
    wait_until(lambda: read_changes(root)["last_seq"] > seq)
    before = (root / RECORD_DIR / "changes.yaml").read_bytes()
    # 実行
    result = server.call("commit", workspace=str(root), summary="a", hand_back=True)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert result.is_error is True
    assert any(line.startswith("tasks.yaml: ") for line in result.text.splitlines()), result.text
    assert (root / RECORD_DIR / "changes.yaml").read_bytes() == before
    assert webhook.requests == []


def test_normal_when_no_tasks_file_on_hand_back(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """tasks.yaml が無いワークスペースでは、タスクが 0 件として手番を返す commit を通す（正常系）。"""
    # 準備
    server, root = _start_with_webhook(session_world, webhook)
    decision_id = add_item(server.call, root, "decision", DECISION_ITEM)
    tasks = root / RECORD_DIR / "tasks.yaml"
    tasks.unlink(missing_ok=True)
    # 実行
    result = server.call("commit", workspace=str(root), summary="D-1 を足す", hand_back=True)
    wait_until(lambda: webhook.requests)
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["id"]
    assert result.data["added"] == [decision_id]
    assert len(webhook.requests) == 1
    assert not tasks.exists()
