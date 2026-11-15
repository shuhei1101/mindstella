"""変更の検知の結合テスト。"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from claude_pane_fixtures import StartClaudePane
from workspace_fixtures import (
    RECORD_DIR,
    STATE_SESSION_FILE,
    STATE_SESSION_PATH,
    TEST_CLAUDE_SESSION_ID,
    workspace_id_of,
)

from .fixture_types import (
    MakeEdit,
    MakeItem,
    MakeWorkspace,
    McpServer,
    StartServer,
    WriteEdits,
)
from .http_helpers import EventStream, post_json

# 外部の変更を自動で commit するまでの秒数を縮める環境変数と、テストで渡す秒数
EXTERNAL_DELAY_ENV = "MINDSTELLA_EXTERNAL_COMMIT_DELAY_SEC"
EXTERNAL_DELAY_SEC = 1

# 記録されるのを待つ上限秒数と、確かめる間隔
WAIT_SEC = 10
POLL_SEC = 0.05

# 記録されないことを確かめるために待つ秒数（変更の検知が見る間隔 250ms を数回過ぎる長さ）
QUIET_SEC = 1.5

# 保存待ちの編集をまとめて保存する API のパス
SAVE_PATH = "/api/edits/save"

# 外部の変更のまとまりの説明
EXTERNAL_SUMMARY = "ほかのセッションの書き込み"

# 本文を持つ D-1 の書き換える前と後の本文
BODY_BEFORE = "# 概要\n\n最初の段落です。\n"
BODY_AFTER = "# 概要\n\n書き換えた段落です。\n\n足した段落です。\n"


def _start(start_server: StartServer) -> McpServer:
    """外部の変更を自動で commit するまでの時間を縮めた常駐サーバーを立てる。"""
    return start_server(extra_env={EXTERNAL_DELAY_ENV: str(EXTERNAL_DELAY_SEC)})


def _serve(server: McpServer, root: Path) -> str:
    """配信を立てて変更の検知を始め、配信の URL を返す。"""
    result = server.call("preview_url", workspace=str(root))
    assert result.is_error is False, result.text
    assert result.data is not None
    return str(result.data["url"])


def _replace(path: Path, text: str) -> None:
    """project-index の write_docs と同じく、一時ファイルに書いて置き換える。"""
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _write_decisions(root: Path, *items: dict[str, Any]) -> str:
    """`decisions.yaml` を items で置き換え、書いた中身を返す。"""
    text = yaml.safe_dump({"items": list(items)}, allow_unicode=True, sort_keys=False)
    _replace(root / RECORD_DIR / "decisions.yaml", text)
    return text


def _read(root: Path, name: str) -> Any:
    """記録のフォルダの YAML を読む（無ければ None）。"""
    path = root / RECORD_DIR / name
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None


def _wait(condition: Callable[[], bool]) -> None:
    """condition が真になるまで待つ。上限を過ぎたらテストを止める。"""
    deadline = time.monotonic() + WAIT_SEC
    while not condition():
        assert time.monotonic() < deadline, "変更の検知が記録しません"
        time.sleep(POLL_SEC)


def _history_of(root: Path, item_id: str) -> dict[str, Any]:
    """`history.yaml` の項目の行を返す（無ければ空）。"""
    return ((_read(root, "history.yaml") or {}).get("items") or {}).get(item_id, {})


def _last_seq(root: Path) -> int:
    """`changes.yaml` の `last_seq` を返す（無ければ 0）。"""
    return int((_read(root, "changes.yaml") or {}).get("last_seq", 0))


def _write_session(state_home: Path, root: Path, **values: Any) -> None:
    """状態のフォルダにワークスペースの MindStella のセッションを書く。"""
    path = state_home.joinpath(*STATE_SESSION_PATH, workspace_id_of(root), STATE_SESSION_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    session = {
        "session": "S-000000000001",
        "status": "running",
        "started_at": "2026-11-15T00:00:00+00:00",
        "claude_session_id": TEST_CLAUDE_SESSION_ID,
        **values,
    }
    path.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")


def _revert(body: str, hunks: list[dict[str, Any]]) -> str:
    """書き換えた後の本文に変更履歴の `body_diff` を後ろの行から当て、書き換える前の本文を返す。"""
    lines = body.splitlines()
    for hunk in sorted(hunks, key=lambda entry: entry["line"], reverse=True):
        start = hunk["line"] - 1
        lines[start : start + len(hunk["now"])] = hunk["before"]
    return "".join(f"{line}\n" for line in lines)


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer) -> None:
    """通常のセッションの書き込みを外部の変更として記録し、60 秒後にまとまりにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    server = _start(start_server)
    _serve(server, root)
    # 実行
    written = _write_decisions(root, make_item("D-1", answer="直した答え"))
    _wait(lambda: bool((_read(root, "changes.yaml") or {}).get("sets")))
    # 検証
    row = _history_of(root, "D-1")
    assert [(entry["before"], entry["by"]) for entry in row["history"]] == [({"answer": None}, "external")]
    assert row["updated_by"] == "external"
    assert (root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8") == written
    changes = _read(root, "changes.yaml")
    first = changes["sets"][0]
    assert (first["by"], first["summary"], first["changed"]) == ("external", EXTERNAL_SUMMARY, ["D-1"])
    assert changes["pending"] == {"added": [], "changed": []}


def test_normal_when_responding(
    make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """MindStella のセッションの応答の途中の書き込みは、そのセッションのまだまとめていない変更にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    server = _start(start_server)
    # 実行
    server.write_as_ai(root, lambda records: _write_decisions(root, make_item("D-1", answer="直した答え")))
    time.sleep(EXTERNAL_DELAY_SEC + QUIET_SEC)
    # 検証
    row = _history_of(root, "D-1")
    assert row["updated_by"] == "ai"
    assert [entry["by"] for entry in row["history"]] == ["ai"]
    changes = _read(root, "changes.yaml")
    assert (changes["pending"]["changed"], changes["pending"]["by"]) == (["D-1"], "ai")
    assert changes["sets"] == []


def test_normal_when_session_crashed(
    tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """状態が応答の途中でも、ペインとプロセスが無ければ外部の変更にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    ended = subprocess.Popen(["true"])
    ended.wait()
    _write_session(
        tmp_path / "state",
        root,
        responding=True,
        pane="%9999",
        socket=str(tmp_path / "no-tmux-socket"),
        pid=ended.pid,
        pid_started_at="0",
    )
    server = _start(start_server)
    _serve(server, root)
    # 実行
    _write_decisions(root, make_item("D-1", answer="直した答え"))
    _wait(lambda: bool((_read(root, "changes.yaml") or {}).get("sets")))
    # 検証
    assert [entry["by"] for entry in _history_of(root, "D-1")["history"]] == ["external"]
    assert _read(root, "changes.yaml")["sets"][0]["changed"] == ["D-1"]


def test_normal_when_screen_save(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    start_server: StartServer,
) -> None:
    """画面の保存が書いた変更を二重に記録しない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1", value="画面の答え"))
    server = _start(start_server)
    url = _serve(server, root)
    # 実行
    saved = post_json(url, SAVE_PATH, {})
    time.sleep(EXTERNAL_DELAY_SEC + QUIET_SEC)
    # 検証
    assert saved.status == 200
    assert [entry["by"] for entry in _history_of(root, "D-1")["history"]] == ["user"]
    assert [entry["by"] for entry in _read(root, "changes.yaml")["sets"]] == ["user"]


def test_normal_when_git_checkout(
    make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """checkout による書き換えは記録しない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", answer="main の答え"))

    def _git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

    _git("init", "-b", "main")
    _git("config", "user.name", "テスト")
    _git("config", "user.email", "test@example.com")
    _git("add", "-A")
    _git("commit", "-m", "main")
    _git("checkout", "-b", "other")
    _write_decisions(root, make_item("D-1", answer="other の答え"))
    _git("commit", "-am", "other")
    _git("checkout", "main")
    server = _start(start_server)
    _serve(server, root)
    # 実行
    _git("checkout", "other")
    time.sleep(EXTERNAL_DELAY_SEC + QUIET_SEC)
    checked_out = (_history_of(root, "D-1").get("history"), _read(root, "changes.yaml"))
    _write_decisions(root, make_item("D-1", answer="checkout の後に直した答え"))
    _wait(lambda: bool(_history_of(root, "D-1").get("history")))
    # 検証
    assert checked_out[0] is None
    assert checked_out[1] is None or (
        checked_out[1]["sets"] == [] and checked_out[1]["pending"] == {"added": [], "changed": []}
    )
    assert [entry["before"] for entry in _history_of(root, "D-1")["history"]] == [
        {"answer": "other の答え"}
    ]


def test_normal_when_duplicate_ids(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    start_claude_pane: StartClaudePane,
    open_events: Callable[[str], EventStream],
) -> None:
    """同じ ID の項目が 2 件になったら、画面とペインへ 1 回知らせる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    pane = start_claude_pane(mode="silent", cwd=root)
    _write_session(
        tmp_path / "state",
        root,
        pane=pane.session["tmux_pane"],
        socket=pane.session["tmux"].split(",", 1)[0],
        pid=pane.session["claude_pid"],
        pid_started_at=pane.session["claude_started_at"],
    )
    server = _start(start_server)
    stream = open_events(_serve(server, root))
    # 実行
    _write_decisions(root, make_item("D-1"), make_item("D-1", title="もう 1 件"))
    first = stream.collect(QUIET_SEC)
    _write_decisions(root, make_item("D-1", answer="答え"), make_item("D-1", title="もう 1 件"))
    second = stream.collect(QUIET_SEC)
    # 検証
    events = [entry for entry in [*first, *second] if entry[0] == "duplicate_ids"]
    assert events == [("duplicate_ids", '["D-1"]')]
    # ペインは貼り付けの文字列を折り返して見せるので、行をつないで数える
    pasted = "".join(pane.capture().splitlines()).count("[mindstella] 同じ ID の項目が 2 件あります: D-1")
    assert pasted == 1, pane.capture()


def test_normal_when_history_limit_exceeded(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
) -> None:
    """保持する回数を超えた古い変更履歴を消し、同じ中身の書き換えでは積まない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="docs/D-1.md"),
        settings={**valid_settings, "history_limit": 1},
        bodies={"D-1.md": BODY_BEFORE},
    )
    server = _start(start_server)
    _serve(server, root)
    body = root / RECORD_DIR / "docs" / "D-1.md"
    # 実行
    _write_decisions(root, make_item("D-1", body="docs/D-1.md", answer="直した答え"))
    _wait(lambda: _last_seq(root) == 1)
    _replace(body, BODY_AFTER)
    _wait(lambda: _last_seq(root) == 2)
    after_body = (_history_of(root, "D-1"), _last_seq(root))
    _replace(body, BODY_AFTER)
    time.sleep(QUIET_SEC)
    # 検証
    history = after_body[0]["history"]
    assert [entry["seq"] for entry in history] == [2]
    assert _revert(BODY_AFTER, history[0]["body_diff"]) == BODY_BEFORE
    assert (_history_of(root, "D-1"), _last_seq(root)) == after_body


def test_normal_when_history_limit_zero(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
) -> None:
    """保持する回数が 0 なら、変更履歴を積まずに通し番号だけ進める（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), settings={**valid_settings, "history_limit": 0})
    server = _start(start_server)
    _serve(server, root)
    before = _last_seq(root)
    # 実行
    _write_decisions(root, make_item("D-1", answer="直した答え"))
    _wait(lambda: _last_seq(root) == before + 1)
    # 検証
    row = _history_of(root, "D-1")
    assert "history" not in row
    assert row["seq"] == before + 1
    assert "D-1" not in _read(root, "changes.yaml")["pending"]["changed"]


def test_normal_when_unread(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
) -> None:
    """AI がまだ読んでいない回は、保持する回数を超えても消さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), settings={**valid_settings, "history_limit": 1})
    server = _start(start_server)
    _serve(server, root)
    assert server.call("changes_since_read", workspace=str(root)).is_error is False
    # 実行
    _write_decisions(root, make_item("D-1", answer="1 回目"))
    _wait(lambda: _last_seq(root) == 1)
    _write_decisions(root, make_item("D-1", answer="1 回目", reason="2 回目"))
    _wait(lambda: _last_seq(root) == 2)
    unread = _history_of(root, "D-1")
    assert server.call("changes_since_read", workspace=str(root)).is_error is False
    _write_decisions(root, make_item("D-1", answer="3 回目", reason="2 回目"))
    _wait(lambda: _last_seq(root) == 3)
    # 検証
    assert [entry["seq"] for entry in unread["history"]] == [2, 1]
    assert "history_dropped_seq" not in unread
    row = _history_of(root, "D-1")
    assert [entry["seq"] for entry in row["history"]] == [3]
    assert row["history_dropped_seq"] == 2


def test_normal_when_server_was_stopped(
    make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """常駐サーバーが止まっていた間の書き換えを、起動したときに外部の変更として記録する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    stopped = _start(start_server)
    _serve(stopped, root)
    stopped.stop()
    _write_decisions(root, make_item("D-1", answer="止まっている間の答え"))
    # 実行
    _serve(_start(start_server), root)
    _wait(lambda: bool(_history_of(root, "D-1").get("history")))
    # 検証
    assert [entry["by"] for entry in _history_of(root, "D-1")["history"]] == ["external"]


def test_normal_when_partial_write(
    make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """読めない YAML の回は飛ばし、読めるようになってから記録する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    server = _start(start_server)
    _serve(server, root)
    broken = "items: [\n  - id: D-1\n"
    # 実行
    _replace(root / RECORD_DIR / "decisions.yaml", broken)
    time.sleep(QUIET_SEC)
    during = ((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"), _read(root, "changes.yaml"))
    _write_decisions(root, make_item("D-1", answer="直した答え"))
    _wait(lambda: bool(_history_of(root, "D-1").get("history")))
    # 検証
    assert during == (broken, None)
    assert len(_history_of(root, "D-1")["history"]) == 1
