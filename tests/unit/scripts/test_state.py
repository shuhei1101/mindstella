"""state.py（常駐サーバーの状態のフォルダの読み書き）の単体テスト。"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

import state
from state import LaunchOptions, SessionState

# テストのワークスペースの ID
WORKSPACE_ID = "mindstella-家計簿-3f2a9c"


def _session(**changes: object) -> SessionState:
    """既定の値の MindStella のセッションの状態を作る。"""
    values: dict[str, object] = {
        "session": "S-0123456789ab",
        "status": "running",
        "started_at": "2026-11-15T00:00:00+00:00",
    }
    values.update(changes)
    return SessionState(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("environ", "relative"),
    [
        pytest.param({"XDG_STATE_HOME": "/tmp/x"}, None, id="xdg"),
        pytest.param({}, ".local/state/mindstella", id="home"),
    ],
)
def test_state_root(
    environ: dict[str, str], relative: str | None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """XDG_STATE_HOME があればその下、無ければ ~/.local/state の下の mindstella を返す。"""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    expected = Path("/tmp/x/mindstella") if relative is None else tmp_path / relative
    assert state.state_root(environ) == expected


def test_read_ids(tmp_path: Path) -> None:
    """ファイルが無ければ空の並び、あれば ids を返す。"""
    assert state.read_ids(tmp_path) == []
    (tmp_path / state.IDS_FILE).write_text("ids:\n  - a\n  - b\n", encoding="utf-8")
    assert state.read_ids(tmp_path) == ["a", "b"]


def test_add_id(tmp_path: Path) -> None:
    """同じ ID を 2 回足しても 1 件だけになる。"""
    state.add_id(tmp_path, WORKSPACE_ID)
    state.add_id(tmp_path, WORKSPACE_ID)
    assert state.read_ids(tmp_path) == [WORKSPACE_ID]


def test_add_id_concurrent(tmp_path: Path) -> None:
    """2 つのスレッドから別の ID を 50 回ずつ足しても失わない。"""

    def add_many(prefix: str) -> None:
        """頭の文字を付けた ID を 50 個足す。"""
        for number in range(50):
            state.add_id(tmp_path, f"{prefix}-{number}")

    threads = [threading.Thread(target=add_many, args=(prefix,)) for prefix in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(state.read_ids(tmp_path)) == 100


def test_read_session(tmp_path: Path) -> None:
    """無ければ None、書いた後は書いた値を返す。"""
    assert state.read_session(tmp_path, WORKSPACE_ID) is None
    written = _session(pane="mindstella-家計簿-3f2a9c:0.0")
    state.update_session(tmp_path, WORKSPACE_ID, lambda _current: written)
    assert state.read_session(tmp_path, WORKSPACE_ID) == written


def test_update_session(tmp_path: Path) -> None:
    """渡した関数で書き換え、None を返すとファイルを消す。"""
    state.update_session(tmp_path, WORKSPACE_ID, lambda _current: _session())
    updated = state.update_session(
        tmp_path,
        WORKSPACE_ID,
        lambda current: None if current is None else _session(responding=True),
    )
    assert updated is not None
    assert updated.responding is True
    path = tmp_path / "workspaces" / WORKSPACE_ID / state.SESSION_FILE
    assert json.loads(path.read_text(encoding="utf-8"))["responding"] is True
    assert state.update_session(tmp_path, WORKSPACE_ID, lambda _current: None) is None
    assert not path.exists()


def test_update_session_concurrent(tmp_path: Path) -> None:
    """2 つのスレッドから別のキーを切り替えても、両方の切り替えが残る。"""
    state.update_session(tmp_path, WORKSPACE_ID, lambda _current: _session())

    def toggle(key: str) -> None:
        """キーを 50 回切り替え、最後に真にする。"""
        for number in range(51):
            value = number % 2 == 0

            def change(current: SessionState | None, value: bool = value) -> SessionState | None:
                """1 つのキーだけを書き換える。"""
                assert current is not None
                return current.replace(**{key: value})

            state.update_session(tmp_path, WORKSPACE_ID, change)

    threads = [
        threading.Thread(target=toggle, args=(key,)) for key in ("pending_write", "responding")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    final = state.read_session(tmp_path, WORKSPACE_ID)
    assert final is not None
    assert final.pending_write is True
    assert final.responding is True


def test_read_launch(tmp_path: Path) -> None:
    """無ければ None、空の指定は空の LaunchOptions を返す。"""
    assert state.read_launch(tmp_path, WORKSPACE_ID) is None
    state.write_launch(tmp_path, WORKSPACE_ID, LaunchOptions(mcp_config=None, plugin_dirs=[]))
    assert state.read_launch(tmp_path, WORKSPACE_ID) == LaunchOptions(
        mcp_config=None, plugin_dirs=[]
    )


def test_write_launch(tmp_path: Path) -> None:
    """書いたものを読める。"""
    options = LaunchOptions(
        mcp_config={"mcpServers": {"aituber": {"command": "a"}}}, plugin_dirs=["/p"]
    )
    state.write_launch(tmp_path, WORKSPACE_ID, options)
    assert state.read_launch(tmp_path, WORKSPACE_ID) == options


def test_delete_launch(tmp_path: Path) -> None:
    """あっても無くても、消した後はファイルが無い。"""
    state.delete_launch(tmp_path, WORKSPACE_ID)
    state.write_launch(tmp_path, WORKSPACE_ID, LaunchOptions(mcp_config=None, plugin_dirs=[]))
    state.delete_launch(tmp_path, WORKSPACE_ID)
    assert state.read_launch(tmp_path, WORKSPACE_ID) is None
