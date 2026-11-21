"""startup.py（常駐サーバーの起動時の照合）の単体テスト。"""

from __future__ import annotations

import logging
import socket
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import project_index
import readme
import serve
import startup
import state
import workspaces
from fixture_types import MakeItem, MakeWorkspace
from project_index import ProjectIndexError

# 記録を見分けるロガーの名前
LOGGER_NAME = "mindstella.startup"

# テストのワークスペースの ID
WORKSPACE_A = "mindstella-家計簿-3f2a9c"
WORKSPACE_B = "mindstella-台本-7b1e04"
WORKSPACE_C = "mindstella-旅行-0c9d55"


def _context(state_root: Path) -> SimpleNamespace:
    """起動時の照合に渡す常駐サーバーの文脈の代わりを作る。"""
    return SimpleNamespace(state_root=state_root, pi_port=1, tmux=object(), proc=object())


def _row(source_id: str, config: str, *, outside_read: bool = True) -> dict[str, Any]:
    """`GET /settings/sources` の応答の行を作る。"""
    return {"id": source_id, "config": config, "outsideRead": outside_read}


def _current_agent_flows_config() -> str:
    """起動した常駐サーバーのプラグインの、エージェントフローの配信の設定のパスを返す。"""
    return str(workspaces.PLUGIN_DIR / workspaces.AGENT_FLOWS_CONFIG)


def _errors(caplog: pytest.LogCaptureFixture, level: int) -> list[logging.LogRecord]:
    """起動時の照合のロガーが出した、指定のレベルの記録を返す。"""
    return [r for r in caplog.records if r.name == LOGGER_NAME and r.levelno == level]


def test_reconcile_before_listen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """作り直しの後に照合する（正常系）。"""
    # 準備
    called: list[str] = []
    monkeypatch.setattr(startup, "rebuild_ids_if_missing", lambda ctx: called.append("rebuild"))
    monkeypatch.setattr(startup.sessions, "watch_crashes_once", lambda ctx: called.append("watch") or 0)
    # 実行
    startup.reconcile_before_listen(_context(tmp_path))
    # 検証
    assert called == ["rebuild", "watch"]


def test_reconcile_before_listen_when_ids_unreadable(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """ID の一覧が読めなければ照合を飛ばして戻る（正常系）。"""
    # 準備
    ids_file = tmp_path / state.IDS_FILE
    ids_file.write_text("ids: [a, b\n", encoding="utf-8")
    caplog.set_level(logging.INFO)
    # 実行
    startup.reconcile_before_listen(_context(tmp_path))
    # 検証
    assert len(_errors(caplog, logging.ERROR)) == 1
    assert ids_file.read_text(encoding="utf-8") == "ids: [a, b\n"


def test_reconcile_before_listen_when_rebuild_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """作り直しが失敗しても照合して戻る（正常系）。"""
    # 準備
    watched: list[object] = []

    def fail(ctx: object) -> None:
        """workspaces.yaml を書けなかったことにする。"""
        raise OSError("書けません")

    monkeypatch.setattr(startup, "rebuild_ids_if_missing", fail)
    monkeypatch.setattr(startup.sessions, "watch_crashes_once", lambda ctx: watched.append(ctx) or 0)
    caplog.set_level(logging.INFO)
    # 実行
    startup.reconcile_before_listen(_context(tmp_path))
    # 検証
    assert len(watched) == 1
    assert len(_errors(caplog, logging.ERROR)) == 1


def test_reconcile_before_listen_when_watch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """照合が想定外の例外で失敗しても戻る（正常系）。"""
    # 準備
    def fail(ctx: object) -> int:
        """workspaces.yaml を読めなかったことにする。"""
        raise PermissionError("読めません")

    monkeypatch.setattr(startup, "rebuild_ids_if_missing", lambda ctx: None)
    monkeypatch.setattr(startup.sessions, "watch_crashes_once", fail)
    caplog.set_level(logging.INFO)
    # 実行
    startup.reconcile_before_listen(_context(tmp_path))
    # 検証
    assert len(_errors(caplog, logging.ERROR)) == 1


def test_rebuild_ids_if_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """一覧が無ければワークスペースの行の ID で作る（正常系）。"""
    # 準備
    timeouts: list[float] = []

    def fake_get_settings(port: int, *, timeout: float = 10.0) -> dict[str, Any]:
        """ワークスペース A・B の行とエージェントフローの行を返す。"""
        timeouts.append(timeout)
        return {
            "version": "v1",
            "sources": [
                _row(WORKSPACE_A, "/w/a/.mindstella/dev-docs.yaml"),
                _row("mindstella-agent-flows", "/p/agent-flows/dev-docs.yaml"),
                _row(WORKSPACE_B, "/w/b/.mindstella/dev-docs.yaml"),
            ],
        }

    monkeypatch.setattr(project_index, "get_settings", fake_get_settings)
    # 実行
    result = startup.rebuild_ids_if_missing(_context(tmp_path))
    # 検証
    assert result == 2
    assert state.read_ids(tmp_path) == [WORKSPACE_A, WORKSPACE_B]
    assert timeouts == [startup.STARTUP_GET_TIMEOUT_SEC]


def test_rebuild_ids_if_missing_when_ids_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """一覧があれば project-index を呼ばない（正常系）。"""
    # 準備
    called: list[int] = []
    (tmp_path / state.IDS_FILE).write_text(f"ids:\n  - {WORKSPACE_A}\n", encoding="utf-8")
    monkeypatch.setattr(project_index, "get_settings", lambda port, **kwargs: called.append(port))
    # 実行
    result = startup.rebuild_ids_if_missing(_context(tmp_path))
    # 検証
    assert result is None
    assert called == []
    assert state.read_ids(tmp_path) == [WORKSPACE_A]


def test_rebuild_ids_if_missing_when_project_index_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """project-index に失敗したら作らない（正常系）。"""
    # 準備
    def fail(port: int, **kwargs: object) -> dict[str, Any]:
        """つながらなかったことにする。"""
        raise ProjectIndexError(None, "つながりません")

    monkeypatch.setattr(project_index, "get_settings", fail)
    caplog.set_level(logging.INFO)
    # 実行
    result = startup.rebuild_ids_if_missing(_context(tmp_path))
    # 検証
    assert result is None
    assert not (tmp_path / state.IDS_FILE).exists()
    assert len(_errors(caplog, logging.WARNING)) == 1


def test_workspace_ids() -> None:
    """ワークスペースの行だけを並び順で返す（正常系）。"""
    # 準備
    settings = {
        "sources": [
            _row(WORKSPACE_A, "/w/a/.mindstella/dev-docs.yaml", outside_read=True),
            _row("mindstella-agent-flows", "/p/agent-flows/dev-docs.yaml"),
            _row("knowledge", "/k/dev-docs.yaml"),
            _row(WORKSPACE_C, "/w/c/.mindstella/dev-docs.yaml", outside_read=False),
            {"id": "no-config"},
            "not-a-row",
        ]
    }
    # 実行
    result = startup.workspace_ids(settings)
    # 検証
    assert result == [WORKSPACE_A, WORKSPACE_C]


def test_workspace_ids_when_config_list() -> None:
    """config が並びの行は先頭の要素で見分ける（正常系）。"""
    # 準備
    settings = {
        "sources": [
            {"id": WORKSPACE_A, "config": ["/w/a/.mindstella/dev-docs.yaml"], "outsideRead": True},
            {
                "id": "mindstella-agent-flows",
                "config": ["/p/agent-flows/dev-docs.yaml"],
                "outsideRead": True,
            },
        ]
    }
    # 実行
    result = startup.workspace_ids(settings)
    # 検証
    assert result == [WORKSPACE_A]


def test_check_agent_flows_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """前のプラグインを指していれば config だけを書き換える（正常系）。"""
    # 準備
    patched: list[tuple[int, str, dict[str, Any]]] = []
    settings = {
        "version": "v1",
        "sources": [_row("mindstella-agent-flows", "/old/plugin/agent-flows/dev-docs.yaml")],
    }
    monkeypatch.setattr(project_index, "get_settings", lambda port, **kwargs: settings)
    monkeypatch.setattr(
        project_index,
        "patch_source",
        lambda port, source_id, changes: patched.append((port, source_id, changes)),
    )
    # 実行
    result = startup.check_agent_flows_source(_context(tmp_path))
    # 検証
    assert result is True
    assert patched == [(1, "mindstella-agent-flows", {"config": _current_agent_flows_config()})]


def test_check_agent_flows_source_when_same(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """今のプラグインを指していれば書き換えない（正常系）。"""
    # 準備
    patched: list[object] = []
    settings = {
        "version": "v1",
        "sources": [_row("mindstella-agent-flows", _current_agent_flows_config())],
    }
    monkeypatch.setattr(project_index, "get_settings", lambda port, **kwargs: settings)
    monkeypatch.setattr(project_index, "patch_source", lambda *args: patched.append(args))
    # 実行
    result = startup.check_agent_flows_source(_context(tmp_path))
    # 検証
    assert result is False
    assert patched == []


def test_check_agent_flows_source_when_config_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """config が今のパス 1 つの並びなら書き換えない（正常系）。"""
    # 準備
    patched: list[object] = []
    settings = {
        "version": "v1",
        "sources": [
            {
                "id": "mindstella-agent-flows",
                "config": [_current_agent_flows_config()],
                "outsideRead": True,
            }
        ],
    }
    monkeypatch.setattr(project_index, "get_settings", lambda port, **kwargs: settings)
    monkeypatch.setattr(project_index, "patch_source", lambda *args: patched.append(args))
    # 実行
    result = startup.check_agent_flows_source(_context(tmp_path))
    # 検証
    assert result is False
    assert patched == []


def test_check_agent_flows_source_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """行が無ければ追加しない（正常系）。"""
    # 準備
    called: list[str] = []
    settings = {"version": "v1", "sources": [_row(WORKSPACE_A, "/w/a/.mindstella/dev-docs.yaml")]}
    monkeypatch.setattr(project_index, "get_settings", lambda port, **kwargs: settings)
    monkeypatch.setattr(project_index, "patch_source", lambda *args: called.append("patch"))
    monkeypatch.setattr(project_index, "add_source", lambda *args: called.append("add"))
    # 実行
    result = startup.check_agent_flows_source(_context(tmp_path))
    # 検証
    assert result is False
    assert called == []


@pytest.mark.parametrize(
    "failing",
    [pytest.param("get_settings", id="get"), pytest.param("patch_source", id="patch")],
)
def test_check_agent_flows_source_when_project_index_fails(
    failing: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """project-index に失敗しても例外を送らない（正常系）。"""
    # 準備
    settings = {
        "version": "v1",
        "sources": [_row("mindstella-agent-flows", "/old/plugin/agent-flows/dev-docs.yaml")],
    }

    def fail(*args: object, **kwargs: object) -> None:
        """つながらなかったことにする。"""
        raise ProjectIndexError(None, "つながりません")

    monkeypatch.setattr(project_index, "get_settings", lambda port, **kwargs: settings)
    monkeypatch.setattr(project_index, "patch_source", lambda *args: None)
    monkeypatch.setattr(project_index, failing, fail)
    caplog.set_level(logging.INFO)
    # 実行
    result = startup.check_agent_flows_source(_context(tmp_path))
    # 検証
    assert result is False
    assert len(_errors(caplog, logging.WARNING)) == 1


def test_start_agent_flows_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """daemon のスレッドで 1 回呼ぶ（正常系）。"""
    # 準備
    called: list[object] = []
    monkeypatch.setattr(startup, "check_agent_flows_source", lambda ctx: called.append(ctx) or False)
    ctx = _context(tmp_path)
    # 実行
    thread = startup.start_agent_flows_check(ctx)
    thread.join(timeout=5)
    # 検証
    assert thread.daemon is True
    assert called == [ctx]


def _served_registry() -> serve.PreviewRegistry:
    """常駐サーバーのポートを 8784 にした配信の台帳を作る。"""
    return serve.PreviewRegistry(threading.Lock(), port=8784)


def test_serve_registered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """ID の一覧のうち配信元の行があるワークスペースを配り、配れないものを飛ばして README を書き直す（正常系）。"""
    # 準備
    first = make_workspace(make_item("D-1"), name="first")
    broken = make_workspace(
        settings={**valid_settings, "display": {"visible_kinds": ["rainbow"]}}, name="broken"
    )
    readme.write_readme(first, preview_url="http://127.0.0.1:47800/w/mindstella-x-1/")
    first_id = workspaces.workspace_id_of(first)
    broken_id = workspaces.workspace_id_of(broken)
    state_root = tmp_path / "state"
    state.create_ids_if_missing(state_root, [first_id, WORKSPACE_B, broken_id])

    def fake_get_settings(port: int, **kwargs: object) -> dict[str, Any]:
        """A と C（broken）の行だけを返す。"""
        return {
            "version": "v1",
            "sources": [
                _row(first_id, str(first / ".mindstella" / "dev-docs.yaml")),
                _row(broken_id, str(broken / ".mindstella" / "dev-docs.yaml")),
            ],
        }

    monkeypatch.setattr(project_index, "get_settings", fake_get_settings)
    previews = _served_registry()
    ctx = SimpleNamespace(state_root=state_root, pi_port=1, previews=previews)
    caplog.set_level(logging.INFO)
    # 実行
    try:
        result = startup.serve_registered(ctx)
        first_url = previews.url_of(first)
        broken_url = previews.url_of(broken)
    finally:
        previews.stop_all()
    # 検証
    assert result == 1
    assert first_url is not None
    assert broken_url is None
    readme_text = (first / readme.README_FILE).read_text(encoding="utf-8")
    assert first_url in readme_text
    assert "47800" not in readme_text
    warnings = [r.getMessage() for r in _errors(caplog, logging.WARNING)]
    assert any(broken_id in message or str(broken) in message for message in warnings)


def test_serve_registered_when_project_index_down(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """project-index に問い合わせられなければ配らずに None を返す（異常系）。"""
    # 準備
    state_root = tmp_path / "state"
    state.create_ids_if_missing(state_root, [WORKSPACE_A])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = int(probe.getsockname()[1])
    previews = _served_registry()
    ctx = SimpleNamespace(state_root=state_root, pi_port=free_port, previews=previews)
    caplog.set_level(logging.INFO)
    # 実行
    try:
        result = startup.serve_registered(ctx)
        served = previews.listing()
    finally:
        previews.stop_all()
    # 検証
    assert result is None
    assert served == []
    assert len(_errors(caplog, logging.WARNING)) == 1


def test_start_serve_registered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """daemon のスレッドで 1 回呼ぶ（正常系）。"""
    # 準備
    called: list[object] = []
    monkeypatch.setattr(startup, "serve_registered", lambda ctx: called.append(ctx) or 0, raising=False)
    ctx = _context(tmp_path)
    # 実行
    thread = startup.start_serve_registered(ctx)
    thread.join(timeout=5)
    # 検証
    assert thread.daemon is True
    assert called == [ctx]
