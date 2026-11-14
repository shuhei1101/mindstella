"""常駐サーバーの状態のフォルダ（ワークスペースの ID の一覧・MindStella のセッション・追加の MCP とプラグイン）を読み書きする。"""

from __future__ import annotations

import contextlib
import dataclasses
import fcntl
import json
import logging
import os
import tempfile
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("mindstella.state")

# `XDG_STATE_HOME` の下に置くフォルダの名前
STATE_DIR_NAME = "mindstella"

# ワークスペースの ID の一覧
IDS_FILE = "workspaces.yaml"

# `workspaces/{ID}/` の下の MindStella のセッション
SESSION_FILE = "session.json"

# `workspaces/{ID}/` の下の追加の MCP とプラグイン
LAUNCH_FILE = "launch.json"

# ワークスペースごとのフォルダを置くフォルダ
WORKSPACES_DIR = "workspaces"

# 鍵のファイルの名前の後ろに付ける文字列
LOCK_SUFFIX = ".lock"


@dataclass(frozen=True)
class SessionState:
    """`session.json` の MindStella のセッション。"""

    session: str
    # running・stopping・stopped・crashed
    status: str
    started_at: str
    # SessionStart のフックが入れる Claude Code の session_id（入るまで None）
    claude_session_id: str | None = None
    pane: str | None = None
    pid: int | None = None
    pid_started_at: str | None = None
    # UserPromptSubmit から Stop・StopFailure までの応答の途中か
    responding: bool = False
    # 停止を待つ上限を過ぎ、最後の書き込みを待っているか
    pending_write: bool = False
    # API で停止かクローズを受けた後か（コメントをペインへ貼らない）
    close_pending: bool = False
    # 最後の停止に失敗した段階と理由
    last_error: str | None = None

    def replace(self, **changes: Any) -> SessionState:
        """渡したキーだけを変えた値を返す。"""
        return dataclasses.replace(self, **changes)


@dataclass(frozen=True)
class LaunchOptions:
    """`launch.json` の追加の MCP とプラグイン。"""

    mcp_config: dict[str, Any] | None
    plugin_dirs: list[str] = field(default_factory=list)


def state_root(environ: Mapping[str, str]) -> Path:
    """`${XDG_STATE_HOME:-~/.local/state}/mindstella` を返す（作らない）。"""
    base = environ.get("XDG_STATE_HOME")
    return (Path(base) if base else Path.home() / ".local" / "state") / STATE_DIR_NAME


def workspace_dir(root: Path, workspace_id: str) -> Path:
    """ワークスペースの状態を置くフォルダを返す。"""
    return root / WORKSPACES_DIR / workspace_id


def read_ids(root: Path) -> list[str]:
    """`workspaces.yaml` の `ids` を返す。ファイルが無ければ空の並び。"""
    path = root / IDS_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        logger.exception("mindstella.state.read_failed", extra={"path": str(path)})
        raise
    # 空のファイル: ID が 1 つも無い
    if data is None:
        return []
    ids = data.get("ids") if isinstance(data, dict) else None
    # ids が並びでない: 壊れたファイルとして止める
    if not isinstance(ids, list):
        error = ValueError(f"ids が並びではありません: {path}")
        logger.error(
            "mindstella.state.read_failed", extra={"path": str(path), "reason": str(error)}
        )
        raise error
    return [str(value) for value in ids]


def add_id(root: Path, workspace_id: str) -> None:
    """全体で 1 つの鍵を取り、`ids` に無ければ足して置き換える。"""
    with _file_lock(root / IDS_FILE):
        ids = read_ids(root)
        # 既にある: 書き換えない
        if workspace_id in ids:
            return
        _write_ids(root, [*ids, workspace_id])


def remove_id(root: Path, workspace_id: str) -> None:
    """全体の鍵を取り、`ids` から外す（作成の巻き戻しに使う）。"""
    with _file_lock(root / IDS_FILE):
        ids = read_ids(root)
        # 無い: 書き換えない
        if workspace_id not in ids:
            return
        _write_ids(root, [value for value in ids if value != workspace_id])


def read_session(root: Path, workspace_id: str) -> SessionState | None:
    """`session.json` を読む。無ければ `None`。"""
    data = _read_json(workspace_dir(root, workspace_id) / SESSION_FILE)
    if data is None:
        return None
    return SessionState(**data)


def update_session(
    root: Path, workspace_id: str, change: Callable[[SessionState | None], SessionState | None]
) -> SessionState | None:
    """`session.json` ごとの鍵を取り、今の値を渡した関数で書き換えて置き換える。`None` が返ればファイルを消す。"""
    path = workspace_dir(root, workspace_id) / SESSION_FILE
    with _file_lock(path):
        updated = change(read_session(root, workspace_id))
        # 関数が None を返した: MindStella のセッションを作る前に戻す
        if updated is None:
            path.unlink(missing_ok=True)
            return None
        _replace_text(path, json.dumps(dataclasses.asdict(updated), ensure_ascii=False, indent=2))
        return updated


def read_launch(root: Path, workspace_id: str) -> LaunchOptions | None:
    """`launch.json` を読む。無ければ `None`（記録が無いことと空の指定を区別する）。"""
    data = _read_json(workspace_dir(root, workspace_id) / LAUNCH_FILE)
    if data is None:
        return None
    return LaunchOptions(
        mcp_config=data.get("mcp_config"), plugin_dirs=list(data.get("plugin_dirs") or [])
    )


def write_launch(root: Path, workspace_id: str, options: LaunchOptions) -> None:
    """`launch.json` を一時ファイルから置き換えて書く。"""
    _replace_text(
        workspace_dir(root, workspace_id) / LAUNCH_FILE,
        json.dumps(dataclasses.asdict(options), ensure_ascii=False, indent=2),
    )


def delete_launch(root: Path, workspace_id: str) -> None:
    """`launch.json` を消す（作成の巻き戻しに使う）。"""
    (workspace_dir(root, workspace_id) / LAUNCH_FILE).unlink(missing_ok=True)


def _write_ids(root: Path, ids: list[str]) -> None:
    """`workspaces.yaml` を置き換える。"""
    _replace_text(root / IDS_FILE, yaml.safe_dump({"ids": ids}, allow_unicode=True))


def _read_json(path: Path) -> dict[str, Any] | None:
    """JSON のオブジェクトを読む。無ければ `None`。"""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        logger.exception("mindstella.state.read_failed", extra={"path": str(path)})
        raise
    # オブジェクトでない: 壊れたファイルとして止める
    if not isinstance(data, dict):
        error = ValueError(f"JSON のオブジェクトではありません: {path}")
        logger.error(
            "mindstella.state.read_failed", extra={"path": str(path), "reason": str(error)}
        )
        raise error
    return data


@contextlib.contextmanager
def _file_lock(target: Path) -> Iterator[None]:
    """`{target}.lock` の排他ロックを取り、抜けるときに放す。

    開くたびに別の鍵になるため、同じプロセスのスレッドの間でも待つ。
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_name(target.name + LOCK_SUFFIX).open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _replace_text(path: Path, text: str) -> None:
    """同じフォルダの一時ファイルに書いてから置き換える。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    except BaseException:
        # 置き換えられなかった: 一時ファイルを残さない
        Path(temp).unlink(missing_ok=True)
        raise
