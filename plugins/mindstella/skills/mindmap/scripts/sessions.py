"""MindStella のセッションを tmux のペインで起動し、一覧・停止と、フックが送る出来事の記録を行う。"""

from __future__ import annotations

import json
import logging
import os
import secrets
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

import commands
import notify
import state
import workspaces
from errors import ApiError
from inject_session import process_started_at
from kinds import SETTINGS_FILE, records_root
from state import LaunchOptions, SessionState
from store import now_utc, workspace_lock

logger = logging.getLogger("mindstella.sessions")

# SessionStart のフックの登録を待つ秒数
READY_TIMEOUT_SEC = 30.0

# 準備を待つ秒数を上書きする環境変数
READY_TIMEOUT_ENV = "MINDSTELLA_SESSION_READY_TIMEOUT"

# session.json とペインの終わり方を読む間隔
READY_POLL_SEC = 0.5

# 停止で応答の終わりを待つ秒数
STOP_WAIT_SEC = 5400.0

# 停止で待つ秒数を上書きする環境変数
STOP_WAIT_ENV = "MINDSTELLA_STOP_WAIT_TIMEOUT"

# 停止を待つ間に session.json を読む間隔
STOP_POLL_SEC = 1.0

# /exit を貼ってから Claude Code のプロセスが終わるまで待つ秒数（過ぎたら SIGTERM）
EXIT_WAIT_SEC = 10.0

# 失敗のときに detail に入れるペインの最後の行数
PANE_TAIL_LINES = 20

# claude-balancer の exec に渡すクライアントの名前
BALANCER_CLIENT = "mindstella"

# claude-balancer の exec が子プロセスを起動せずに終わるときの終了コード
NO_ACCOUNT_EXIT = 125

# 準備ができた後にペインへ入力する 1 行
FIRST_INPUT = "[mindstella] MindStella のセッションを起動しました"

# /exit の入力
EXIT_INPUT = "/exit"

# あるとみなす状態
ALIVE_STATUSES = ("running", "stopping")

# 起動時の指示のファイル（プラグインのフォルダから）
STARTUP_PROMPT_FILE = Path("skills") / "mindmap" / "references" / "起動時の指示.md"

# 追加の MCP を書く一時ファイルの名前（状態のフォルダのワークスペースのフォルダの下）
MCP_CONFIG_FILE = "mcp-config.json"

# 貼り付けに使う tmux のバッファの名前
PASTE_BUFFER = "mindstella-session"

# tmux へ渡さない常駐サーバーの環境変数の名前の頭
SERVER_ENV_PREFIX = "MINDSTELLA_"

# 1 回の tmux のコマンドを打ち切る秒数
TMUX_TIMEOUT_SEC = 5.0

# SessionEnd の reason のうち、MindStella のセッションを続けるもの
CONTINUING_END_REASONS = ("clear", "resume")

# 受ける出来事
EVENT_NAMES = ("session_start", "session_end", "prompt_submit", "stop", "stop_failure")

# まとめていない変更をまとめるときの説明
COMMIT_SUMMARIES = {
    "before_stop": "MindStella のセッションを止める前の、まとめていない変更",
    "crashed": "MindStella のセッションが落ちていたため、まとめていない変更を記録する",
    "forced": "MindStella のセッションを強制で止めたため、まとめていない変更を記録する",
}


class TmuxRunner:
    """利用者の既定のソケットの tmux を子プロセスで呼ぶ。"""

    def run(self, args: list[str], stdin: bytes | None = None) -> tuple[int, str]:
        """引数の並びで tmux を呼び、終了コードと標準出力を返す。

        常駐サーバーの `MINDSTELLA_*` は渡さない（このとき tmux のサーバーが立つと、ペインがその値を受け継ぐため）。
        MindStella のセッションに渡す値は `respawn-pane -e` で渡す。
        """
        env = {
            key: value for key, value in os.environ.items() if not key.startswith(SERVER_ENV_PREFIX)
        }
        completed = subprocess.run(
            ["tmux", *args],
            input=stdin,
            env=env,
            capture_output=True,
            timeout=TMUX_TIMEOUT_SEC,
            check=False,
        )
        return completed.returncode, completed.stdout.decode("utf-8", errors="replace").strip()


class ProcessInspector:
    """PID の起動時刻を読む。"""

    def started_at(self, pid: int) -> str | None:
        """PID の起動時刻の文字列を返す。プロセスが無ければ None。"""
        return process_started_at(pid)


def new_session_id() -> str:
    """`S-` に続く 12 桁の 16 進を返す。"""
    return f"S-{secrets.token_hex(6)}"


def build_command(
    options: LaunchOptions | None,
    mcp_config_file: Path | None,
    startup_prompt: str,
    balancer: str | None,
) -> list[str]:
    """ペインで動かすコマンドの引数の並びを作る。"""
    claude = ["claude"]
    if mcp_config_file is not None:
        claude += ["--mcp-config", str(mcp_config_file)]
    for folder in options.plugin_dirs if options is not None else []:
        claude += ["--plugin-dir", folder]
    claude += ["--append-system-prompt", startup_prompt]
    # claude-balancer がある: アカウントを借りて起動する
    if balancer is not None:
        return [balancer, "exec", "--client", BALANCER_CLIENT, "--", *claude]
    return claude


def build_env(
    session_id: str,
    workspace_id: str,
    port: int,
    flow: dict[str, str] | None,
    claude_config_dir: str | None,
    has_balancer: bool,
) -> dict[str, str]:
    """MindStella のセッションに渡す環境変数を作る。"""
    env = {
        "MINDSTELLA_SESSION": session_id,
        "MINDSTELLA_WORKSPACE": workspace_id,
        "MINDSTELLA_PORT": str(port),
    }
    if flow is not None:
        env["MINDSTELLA_FLOW"] = f"{flow['source']}#{flow['doc']}"
    # claude-balancer が無い: 依頼の設定のフォルダのアカウントで起動する
    if not has_balancer and claude_config_dir:
        env["CLAUDE_CONFIG_DIR"] = claude_config_dir
    return env


def is_alive(root: Path, workspace_id: str, tmux: TmuxRunner, proc: ProcessInspector) -> bool:
    """ペインと Claude Code のプロセスがあるかを返し、無ければ状態を crashed にする。"""
    current = state.read_session(root, workspace_id)
    if current is None or current.status not in ALIVE_STATUSES:
        return False
    reason = _dead_reason(current, tmux, proc)
    if reason is None:
        return True
    session_id = current.session

    def mark(latest: SessionState | None) -> SessionState | None:
        """同じ MindStella のセッションがまだあるとみなされているときだけ crashed にする。"""
        if latest is None or latest.session != session_id or latest.status not in ALIVE_STATUSES:
            return latest
        return latest.replace(status="crashed", responding=False)

    state.update_session(root, workspace_id, mark)
    logger.warning(
        "mindstella.session.crashed",
        extra={"workspace_id": workspace_id, "session_id": session_id, "reason": reason},
    )
    return False


def create_session(
    workspace_id: str, claude_config_dir: str | None, ctx: Any
) -> tuple[int, dict[str, Any]]:
    """MindStella のセッションを tmux のペインで起動し、SessionStart の登録を待って返す。"""
    _require_known(ctx, workspace_id)
    with ctx.locks.for_workspace(workspace_id):
        row = workspaces.find_workspace_row(ctx.pi_port, workspace_id)
        if row is None:
            raise ApiError(404, "workspace", f"配信元の行がありません: {workspace_id}")
        if workspaces.is_closed(row):
            raise ApiError(
                409, "closed", "ワークスペースはクローズ済みです。作成し直してから起動してください"
            )
        current = state.read_session(ctx.state_root, workspace_id)
        # 生きている MindStella のセッションがある: そのペインを返す
        if current is not None and is_alive(ctx.state_root, workspace_id, ctx.tmux, ctx.proc):
            raise ApiError(
                409,
                "exists",
                "MindStella のセッションが既にあります",
                session=current.session,
                pane=f"{workspace_id}:0.0",
            )
        folder = workspaces.workspace_folder(row)
        session_id = new_session_id()
        pane = f"{workspace_id}:0.0"
        balancer = shutil.which("claude-balancer")
        options = state.read_launch(ctx.state_root, workspace_id)
        command = build_command(
            options,
            _write_mcp_config(ctx.state_root, workspace_id, options),
            (Path(ctx.plugin_root) / STARTUP_PROMPT_FILE).read_text(encoding="utf-8"),
            balancer,
        )
        env = build_env(
            session_id,
            workspace_id,
            ctx.port,
            _read_flow(folder),
            claude_config_dir,
            balancer is not None,
        )
        state.update_session(
            ctx.state_root,
            workspace_id,
            lambda _current: SessionState(
                session=session_id, status="running", pane=pane, started_at=now_utc()
            ),
        )
        # 生きていないのに同じ名前の tmux のセッションが残っている: 閉じてから作る
        if ctx.tmux.run(["has-session", "-t", f"={workspace_id}"])[0] == 0:
            ctx.tmux.run(["kill-session", "-t", f"={workspace_id}"])
        try:
            _launch(ctx.tmux, workspace_id, folder, env, command)
            _wait_ready(ctx, workspace_id)
            registered = state.read_session(ctx.state_root, workspace_id)
            # フックが登録したペイン（`TMUX_PANE`）へ貼る。無ければセッションの今のペイン
            _paste(
                ctx.tmux,
                (registered.pane if registered else None) or _window(workspace_id),
                FIRST_INPUT,
            )
        except ApiError as error:
            # 起動できなかった: ペインを閉じて session.json を作る前に戻す
            ctx.tmux.run(["kill-session", "-t", f"={workspace_id}"])
            state.update_session(ctx.state_root, workspace_id, lambda _current: None)
            logger.error(  # noqa: TRY400
                "mindstella.session.start_failed",
                extra={"workspace_id": workspace_id, "stage": error.stage, "detail": error.detail},
            )
            raise
    url = commands.run_preview_url(folder, ctx.previews)["url"]
    logger.info(
        "mindstella.session.started",
        extra={
            "workspace_id": workspace_id,
            "session_id": session_id,
            "balancer": balancer is not None,
        },
    )
    return 201, {"session": session_id, "pane": pane, "url": url}


def list_sessions(workspace_id: str, ctx: Any) -> dict[str, Any]:
    """ワークスペースの最後の MindStella のセッション 1 つの状態を返す。落ちていれば crashed にする。"""
    _require_known(ctx, workspace_id)
    is_alive(ctx.state_root, workspace_id, ctx.tmux, ctx.proc)
    current = state.read_session(ctx.state_root, workspace_id)
    if current is None:
        return {"sessions": [], "close_pending": False}
    entry = {
        "id": current.session,
        "status": current.status,
        "responding": current.responding,
        "pending_write": current.pending_write,
        "pane": current.pane if current.status in ALIVE_STATUSES else None,
        "last_error": current.last_error,
    }
    return {"sessions": [entry], "close_pending": current.close_pending}


def stop_session(
    workspace_id: str,
    session_id: str,
    force: bool,
    ctx: Any,
    *,
    spawn: Callable[[Callable[[], None]], None] | None = None,
) -> tuple[int, dict[str, Any]]:
    """停止をすぐに受け付けてクローズ待ちにし、別のスレッドで最後の書き込みを待ってから止める。"""
    _require_known(ctx, workspace_id)
    with ctx.locks.for_workspace(workspace_id):
        current = state.read_session(ctx.state_root, workspace_id)
        if current is None or current.session != session_id:
            raise ApiError(404, "session", f"MindStella のセッションがありません: {session_id}")
        # 既に止まっている: 停止済みを返す
        if current.status == "stopped":
            return 200, {"session": session_id, "status": "stopped"}
        # 落ちている: 止める工程を飛ばし、まとめていない変更を記録して停止済みにする
        if not is_alive(ctx.state_root, workspace_id, ctx.tmux, ctx.proc):
            _commit_pending(ctx, workspace_id, "crashed")
            _mark_stopped(ctx, workspace_id, session_id)
            logger.info(
                "mindstella.session.stopped",
                extra={
                    "workspace_id": workspace_id,
                    "session_id": session_id,
                    "forced": force,
                    "crashed": True,
                },
            )
            return 200, {"session": session_id, "status": "stopped"}
        state.update_session(
            ctx.state_root,
            workspace_id,
            lambda latest: (
                None if latest is None else latest.replace(status="stopping", close_pending=True)
            ),
        )
    (spawn or _start_thread)(lambda: _stop_in_background(ctx, workspace_id, session_id, force))
    return 202, {"session": session_id, "status": "stopping"}


def record_event(session_id: str, event: dict[str, Any], ctx: Any) -> bool:
    """フックが送った出来事を session.json に記録する。状態に無い MindStella のセッションなら False。"""
    kind = event.get("event")
    if kind not in EVENT_NAMES:
        raise ApiError(400, "event", f"event は {', '.join(EVENT_NAMES)} のどれかにしてください")
    workspace_id = _find_workspace_of(ctx.state_root, session_id)
    if workspace_id is None:
        logger.warning(
            "mindstella.session.event_unknown", extra={"session_id": session_id, "event": kind}
        )
        return False

    def change(current: SessionState | None) -> SessionState | None:
        """出来事ごとに書き換える。"""
        if current is None or current.session != session_id:
            return current
        # 起動・clear・compact・fork: Claude Code の session_id とプロセスを入れ直す
        if kind == "session_start":
            return current.replace(
                claude_session_id=str(event.get("claude_session_id") or "")
                or current.claude_session_id,
                pid=event.get("pid", current.pid),
                pid_started_at=event.get("pid_started_at", current.pid_started_at),
                pane=event.get("pane") or current.pane,
                socket=event.get("socket") or current.socket,
            )
        # 終了: clear・resume のほかは停止済み
        if kind == "session_end":
            if event.get("reason") in CONTINUING_END_REASONS:
                return current
            return current.replace(status="stopped", responding=False)
        # 応答の始まりと終わり
        return current.replace(responding=kind == "prompt_submit")

    state.update_session(ctx.state_root, workspace_id, change)
    # 応答の終わり: この応答で書き込んでいれば作業の完了を通知する
    if kind == "stop":
        notify.notify_if_written(workspace_id, lambda: _describe_workspace(ctx, workspace_id))
    # 応答の始まり・エラーで終わった応答・終了: 通知せずにマーカーを解除する
    elif kind in ("prompt_submit", "stop_failure", "session_end"):
        notify.clear_written(workspace_id)
    return True


def _describe_workspace(ctx: Any, workspace_id: str) -> tuple[str, str | None] | None:
    """通知に載せるワークスペースの名前（設定の summary、空ならフォルダの名前）と画面の URL を返却する。"""
    row = workspaces.find_workspace_row(ctx.pi_port, workspace_id)
    # 配信元の行が無い: 通知しない
    if row is None:
        return None
    folder = workspaces.workspace_folder(row)
    loaded = yaml.safe_load((records_root(folder) / SETTINGS_FILE).read_text(encoding="utf-8"))
    summary = loaded.get("summary") if isinstance(loaded, dict) else None
    name = str(summary).strip() if summary else ""
    return (name or folder.name, ctx.previews.url_of(folder))


def _require_known(ctx: Any, workspace_id: str) -> None:
    """ID の一覧に無いワークスペースは 404。"""
    if workspace_id not in state.read_ids(ctx.state_root):
        raise ApiError(404, "workspace", f"ワークスペースがありません: {workspace_id}")


def _dead_reason(current: SessionState, tmux: TmuxRunner, proc: ProcessInspector) -> str | None:
    """落ちた理由（ペインが無い・PID が無い・起動時刻が違う）を返す。生きていれば None。"""
    if not current.pane:
        return "pane_missing"
    code, _out = tmux.run(["display-message", "-p", "-t", current.pane, "#{pane_pid}"])
    if code != 0:
        return "pane_missing"
    # SessionStart の前でプロセスを知らない: ペインだけで判定する
    if current.pid is None:
        return None
    started = proc.started_at(current.pid)
    if started is None:
        return "process_missing"
    if current.pid_started_at is not None and started != current.pid_started_at:
        return "process_replaced"
    return None


def _read_flow(folder: Path) -> dict[str, str] | None:
    """ワークスペースの設定の進め方の文書を返す。"""
    loaded = yaml.safe_load((records_root(folder) / SETTINGS_FILE).read_text(encoding="utf-8"))
    flow = loaded.get("flow") if isinstance(loaded, dict) else None
    return flow if isinstance(flow, dict) else None


def _write_mcp_config(root: Path, workspace_id: str, options: LaunchOptions | None) -> Path | None:
    """追加の MCP があれば一時ファイルに書いてそのパスを返す。"""
    if options is None or not options.mcp_config:
        return None
    path = state.workspace_dir(root, workspace_id) / MCP_CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(options.mcp_config, ensure_ascii=False), encoding="utf-8")
    return path


def _launch(
    tmux: TmuxRunner, workspace_id: str, folder: Path, env: dict[str, str], command: list[str]
) -> None:
    """コマンドの無いペインを作り、remain-on-exit を立ててからコマンドを動かす。"""
    target = _window(workspace_id)
    steps = [
        ["new-session", "-d", "-s", workspace_id, "-c", str(folder)],
        ["set-option", "-w", "-t", target, "remain-on-exit", "on"],
        [
            "respawn-pane",
            "-k",
            "-t",
            target,
            "-c",
            str(folder),
            *[part for key, value in env.items() for part in ("-e", f"{key}={value}")],
            *command,
        ],
    ]
    for step in steps:
        code, out = tmux.run(step)
        if code != 0:
            raise ApiError(
                502, "launch", f"tmux {step[0]} が終了コード {code} で終わりました: {out}"
            )


def _window(workspace_id: str) -> str:
    """ワークスペースの ID の tmux のセッションの今のウィンドウ（とペイン）を指す `-t` の値を返す。"""
    # `=` で名前の完全一致にし、末尾の `:` でウィンドウ・ペインを指す（`=` だけではペインに当たらない）
    return f"={workspace_id}:"


def _wait_ready(ctx: Any, workspace_id: str) -> None:
    """SessionStart の登録か、ペインのコマンドの終わりを上限まで待つ。"""
    timeout = float(os.environ.get(READY_TIMEOUT_ENV) or READY_TIMEOUT_SEC)
    deadline = time.monotonic() + timeout
    while True:
        current = state.read_session(ctx.state_root, workspace_id)
        # 登録が入った: 準備ができた
        # 登録が入った: 準備ができたので、以降はペインのコマンドが終わればセッションごと閉じる
        if current is not None and current.claude_session_id:
            ctx.tmux.run(["set-option", "-w", "-t", _window(workspace_id), "remain-on-exit", "off"])
            return
        _code, out = ctx.tmux.run(
            [
                "display-message",
                "-p",
                "-t",
                _window(workspace_id),
                "#{pane_dead} #{pane_dead_status}",
            ]
        )
        words = out.split()
        # ペインのコマンドが先に終わった: 終了コードで分ける
        if words[:1] == ["1"]:
            exit_code = int(words[1]) if len(words) > 1 and words[1].lstrip("-").isdigit() else None
            _code, tail = ctx.tmux.run(
                ["capture-pane", "-p", "-t", _window(workspace_id), "-S", f"-{PANE_TAIL_LINES}"]
            )
            if exit_code == NO_ACCOUNT_EXIT:
                raise ApiError(
                    503, "account", f"claude-balancer がアカウントを貸せませんでした:\n{tail}"
                )
            raise ApiError(
                502, "launch", f"Claude Code が終了コード {exit_code} で終わりました:\n{tail}"
            )
        if time.monotonic() >= deadline:
            raise ApiError(
                504,
                "ready",
                f"{timeout:g} 秒以内に MindStella のセッションの準備ができませんでした",
            )
        time.sleep(READY_POLL_SEC)


def _paste(tmux: TmuxRunner, pane: str, text: str) -> None:
    """文字列をブラケットペーストでペインへ貼り、Enter で確定する。"""
    steps: list[tuple[list[str], bytes | None]] = [
        (["load-buffer", "-b", PASTE_BUFFER, "-"], text.encode("utf-8")),
        (["paste-buffer", "-p", "-d", "-b", PASTE_BUFFER, "-t", pane], None),
        (["send-keys", "-t", pane, "Enter"], None),
    ]
    for args, stdin in steps:
        code, out = tmux.run(args, stdin)
        if code != 0:
            raise ApiError(
                502, "launch", f"tmux {args[0]} が終了コード {code} で終わりました: {out}"
            )


def _start_thread(body: Callable[[], None]) -> None:
    """止める処理を別のスレッドで走らせる。"""
    threading.Thread(target=body, name="mindstella-stop", daemon=True).start()


def _stop_in_background(ctx: Any, workspace_id: str, session_id: str, force: bool) -> None:
    """最後の書き込みを待ってから止める。失敗したら状態を戻して last_error に入れる。"""
    stage = "wait"
    try:
        if not force:
            if not _wait_last_write(ctx, workspace_id, session_id):
                return
            stage = "commit"
            _commit_pending(ctx, workspace_id, "before_stop")
            stage = "exit"
            _exit_claude(ctx, workspace_id)
        else:
            stage = "term"
            _terminate(ctx, workspace_id)
        stage = "term"
        ctx.tmux.run(["kill-session", "-t", f"={workspace_id}"])
        if force:
            stage = "commit"
            _commit_pending(ctx, workspace_id, "forced")
        stage = "state"
        _mark_stopped(ctx, workspace_id, session_id)
        logger.info(
            "mindstella.session.stopped",
            extra={
                "workspace_id": workspace_id,
                "session_id": session_id,
                "forced": force,
                "crashed": False,
            },
        )
    except Exception as error:
        logger.exception(
            "mindstella.session.stop_failed",
            extra={"workspace_id": workspace_id, "session_id": session_id, "stage": stage},
        )
        _restore_after_failure(ctx, workspace_id, session_id, f"{stage}: {error}")


def _wait_last_write(ctx: Any, workspace_id: str, session_id: str) -> bool:
    """応答の終わりを上限まで待つ。上限を過ぎたら pending_write を真にして running に戻し、False を返す。"""
    limit = float(os.environ.get(STOP_WAIT_ENV) or STOP_WAIT_SEC)
    started = time.monotonic()
    while True:
        current = state.read_session(ctx.state_root, workspace_id)
        # 別の MindStella のセッションに変わった・消えた: 止めない
        if current is None or current.session != session_id:
            return False
        if not current.responding:
            return True
        if time.monotonic() - started >= limit:
            state.update_session(
                ctx.state_root,
                workspace_id,
                lambda latest: (
                    None if latest is None else latest.replace(pending_write=True, status="running")
                ),
            )
            logger.warning(
                "mindstella.session.stop_wait_exceeded",
                extra={"workspace_id": workspace_id, "session_id": session_id, "waited_sec": limit},
            )
            return False
        time.sleep(STOP_POLL_SEC)


def _exit_claude(ctx: Any, workspace_id: str) -> None:
    """ペインへ /exit を貼り、上限までに終わらなければ SIGTERM を送る。"""
    current = state.read_session(ctx.state_root, workspace_id)
    if current is None or current.pane is None:
        return
    _paste(ctx.tmux, current.pane, EXIT_INPUT)
    if current.pid is None:
        return
    deadline = time.monotonic() + EXIT_WAIT_SEC
    while time.monotonic() < deadline:
        if ctx.proc.started_at(current.pid) != current.pid_started_at:
            return
        time.sleep(STOP_POLL_SEC)
    os.kill(current.pid, signal.SIGTERM)


def _terminate(ctx: Any, workspace_id: str) -> None:
    """待たずに Claude Code のプロセスへ SIGTERM を送る。"""
    current = state.read_session(ctx.state_root, workspace_id)
    if current is None or current.pid is None:
        return
    # 同じプロセスがまだ動いているときだけ送る（PID の使い回しに送らない）
    if ctx.proc.started_at(current.pid) == current.pid_started_at:
        os.kill(current.pid, signal.SIGTERM)


def _commit_pending(ctx: Any, workspace_id: str, reason: str) -> None:
    """まとめていない変更があれば、理由を説明に入れてまとめる。"""
    row = workspaces.find_workspace_row(ctx.pi_port, workspace_id)
    if row is None:
        return
    folder = workspaces.workspace_folder(row)
    pending = commands.run_pending(folder)
    if not any(pending.get(key) for key in ("added", "changed", "removed")):
        return
    with workspace_lock(folder, ctx.write_lock):
        commands.run_commit(folder, COMMIT_SUMMARIES[reason])


def _mark_stopped(ctx: Any, workspace_id: str, session_id: str) -> None:
    """停止済みを記録する（クローズ待ちのまま）。"""
    state.update_session(
        ctx.state_root,
        workspace_id,
        lambda latest: (
            None
            if latest is None or latest.session != session_id
            else latest.replace(status="stopped", responding=False, close_pending=True)
        ),
    )


def _restore_after_failure(ctx: Any, workspace_id: str, session_id: str, reason: str) -> None:
    """止める間の失敗の後、生きていれば running・落ちていれば crashed に戻し、理由を残す。"""
    alive = is_alive(ctx.state_root, workspace_id, ctx.tmux, ctx.proc)
    state.update_session(
        ctx.state_root,
        workspace_id,
        lambda latest: (
            None
            if latest is None or latest.session != session_id
            else latest.replace(status="running" if alive else "crashed", last_error=reason)
        ),
    )


def _find_workspace_of(root: Path, session_id: str) -> str | None:
    """MindStella のセッションの ID を持つワークスペースの ID を返す。"""
    for workspace_id in state.read_ids(root):
        current = state.read_session(root, workspace_id)
        if current is not None and current.session == session_id:
            return workspace_id
    return None
