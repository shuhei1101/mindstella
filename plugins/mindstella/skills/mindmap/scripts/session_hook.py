"""MindStella のセッションのフックで、出来事を常駐サーバーへ送り、SessionStart では再開の状況を注入する。

依存が揃う前のシステムの `python3` で起動するため、Python 3.8 で読める構文と標準ライブラリだけで書く。
環境変数 `MINDSTELLA_SESSION` が無い通常のセッションでは何もしない。
使い方（Claude Code がフックの入力の JSON を標準入力へ渡す）:
python3 session_hook.py {session-start | session-end | prompt-submit | stop | stop-failure}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, TextIO

from inject_session import find_claude_process

# 常駐サーバーへ 1 回送る上限の秒数
POST_TIMEOUT_SEC = 2.0

# コマンドの引数から本文の `event` への対応
EVENTS = {
    "session-start": "session_start",
    "session-end": "session_end",
    "prompt-submit": "prompt_submit",
    "stop": "stop",
    "stop-failure": "stop_failure",
}

# MINDSTELLA_PORT が無いときのポート
DEFAULT_PORT = 8784

# フックの入力から本文へ写すキー
FORWARDED_KEYS = ("source", "reason")

# SessionStart の出力のフックの名前
SESSION_START_HOOK = "SessionStart"

# 再開の状況を取れないときだけ注入する行（`{flow}` の行は進め方の文書があるときだけ入れる）
FALLBACK_LINES = (
    "MindStella のセッションを{trigger}しました。再開の状況を取得できなかったため、状況は含みません。",
    "進め方の文書: {flow}",
    "エージェントフロー mindstella/startup を参照して先に進めてください。",
)

# 進め方の文書の行（FALLBACK_LINES の 2 行目）
FLOW_LINE_INDEX = 1

# 代理を通さずに 127.0.0.1 へつなぐ開き方
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    post: Callable[[int, str, dict[str, Any]], None] | None = None,
    resume: Callable[[int, str, str], dict[str, Any]] | None = None,
    advance: Callable[[int, str, int], None] | None = None,
) -> int:
    """`MINDSTELLA_SESSION` があれば出来事を送り、SessionStart では再開の状況を注入して前回参照した時点を進める。どの結末も 0 を返す。"""
    env = os.environ if environ is None else environ
    out = sys.stdout if stdout is None else stdout
    send = post_event if post is None else post
    fetch = request_resume if resume is None else resume
    move = post_read_point if advance is None else advance
    parser = argparse.ArgumentParser(
        description="MindStella のセッションの出来事を常駐サーバーへ送る"
    )
    parser.add_argument("event", choices=sorted(EVENTS))
    args = parser.parse_args(argv)
    raw = (sys.stdin if stdin is None else stdin).read()
    session_id = env.get("MINDSTELLA_SESSION")
    # 通常のセッション: 入力を読み捨てて何もしない
    if not session_id:
        return 0
    try:
        hook_input = json.loads(raw)
    except ValueError:
        hook_input = {}
    if not isinstance(hook_input, dict):
        hook_input = {}

    body = _build_body(EVENTS[args.event], hook_input, env)
    port = _read_port(env)
    try:
        send(port, session_id, body)
    except (OSError, ValueError) as error:
        # 常駐サーバーへ送れない: 会話を止めずに 1 行だけ残す
        print(
            f"[mindstella] 常駐サーバーへ出来事を送れません（{body['event']}）: {error}",
            file=sys.stderr,
        )
    source = str(hook_input.get("source") or "")
    # SessionStart で fork でない: 再開の状況を注入する
    if body["event"] == "session_start" and source != "fork":
        _inject(out, port, session_id, source, env.get("MINDSTELLA_FLOW") or None, fetch, move)
    return 0


def _inject(
    out: TextIO,
    port: int,
    session_id: str,
    source: str,
    flow: str | None,
    fetch: Callable[[int, str, str], dict[str, Any]],
    move: Callable[[int, str, int], None],
) -> None:
    """再開の状況の注入文を書き、収まる状況のときだけ前回参照した時点を進める。"""
    status: dict[str, Any] | None
    try:
        status = fetch(port, session_id, source)
    except (OSError, ValueError) as error:
        # 状況を取れない: 状況なしで注入し、時点を進めない
        print(f"[mindstella] 再開の状況を取得できません: {error}", file=sys.stderr)
        status = None
    context = status["context"] if status is not None else fallback_context(source, flow)
    out.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": SESSION_START_HOOK,
                    "additionalContext": context,
                }
            },
            ensure_ascii=False,
        )
    )
    out.flush()
    # 収まらない変更が無い: 注入を書き終えた後に前回参照した時点を進める
    if status is not None and not status.get("changed_more") and not status.get("removed_more"):
        try:
            move(port, session_id, int(status["until_seq"]))
        except (OSError, ValueError) as error:
            print(f"[mindstella] 前回参照した時点を進められません: {error}", file=sys.stderr)


def post_event(port: int, session_id: str, body: dict[str, Any]) -> None:
    """`POST /_admin/sessions/{session}/events` に JSON を送る（`POST_TIMEOUT_SEC` で打ち切る）。"""
    _post_json(port, f"/_admin/sessions/{session_id}/events", body)


def request_resume(port: int, session_id: str, source: str) -> dict[str, Any]:
    """`POST /_admin/sessions/{session}/resume` に `source` を送り、応答の JSON を返す。"""
    result = _post_json(port, f"/_admin/sessions/{session_id}/resume", {"source": source})
    # オブジェクトでない応答は状況として使えない
    if not isinstance(result, dict):
        raise ValueError("再開の状況の応答が JSON のオブジェクトではありません")
    return result


def post_read_point(port: int, session_id: str, until_seq: int) -> None:
    """`POST /_admin/sessions/{session}/read_point` に `until_seq` を送る。"""
    _post_json(port, f"/_admin/sessions/{session_id}/read_point", {"until_seq": until_seq})


def fallback_context(source: str, flow: str | None) -> str:
    """`FALLBACK_LINES` を起動の契機と進め方の文書の場所で埋めて改行でつなぐ。"""
    trigger = "起動" if source == "startup" else "再開"
    lines = [
        line
        for index, line in enumerate(FALLBACK_LINES)
        if flow is not None or index != FLOW_LINE_INDEX
    ]
    return "\n".join(line.format(trigger=trigger, flow=flow) for line in lines)


def _post_json(port: int, path: str, body: dict[str, Any]) -> Any:
    """常駐サーバーへ JSON を POST し、応答の JSON を返す（`POST_TIMEOUT_SEC` で打ち切る。200 以外は OSError）。"""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with _OPENER.open(request, timeout=POST_TIMEOUT_SEC) as response:
        text = response.read()
    return json.loads(text) if text else None


def _build_body(
    event: str, hook_input: dict[str, Any], environ: Mapping[str, str]
) -> dict[str, Any]:
    """出来事・Claude Code の session_id・ペイン・PID・設定のフォルダの本文を作る。"""
    body: dict[str, Any] = {
        "event": event,
        "claude_session_id": str(hook_input.get("session_id") or ""),
    }
    for key in FORWARDED_KEYS:
        if isinstance(hook_input.get(key), str):
            body[key] = hook_input[key]
    pane = environ.get("TMUX_PANE")
    if pane:
        body["pane"] = pane
    # TMUX は `{ソケット},{PID},{番号}`。ペインへ貼る先のソケットを送る
    socket = (environ.get("TMUX") or "").split(",", 1)[0]
    if socket:
        body["socket"] = socket
    # SessionStart だけ、ペインのコメントを貼る先の Claude Code のプロセスを探す
    if event == "session_start":
        found = find_claude_process(os.getppid())
        if found is not None:
            body["pid"], body["pid_started_at"] = found
        # 起動したアカウント: Claude Code が使う設定のフォルダの絶対パス（無ければ既定の ~/.claude）
        config_dir = environ.get("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude")
        body["claude_config_dir"] = os.path.abspath(os.path.expanduser(config_dir))
    return body


def _read_port(environ: Mapping[str, str]) -> int:
    """送り先のポートを返す。"""
    value = environ.get("MINDSTELLA_PORT")
    return int(value) if value else DEFAULT_PORT


if __name__ == "__main__":
    sys.exit(main())
