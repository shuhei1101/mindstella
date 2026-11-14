"""MindStella のセッションのフックで、出来事を常駐サーバーへ送り、SessionStart では進め方の文書の場所を注入する。

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

# 代理を通さずに 127.0.0.1 へつなぐ開き方
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    post: Callable[[int, str, dict[str, Any]], None] | None = None,
) -> int:
    """`MINDSTELLA_SESSION` があれば出来事を送り、SessionStart で `MINDSTELLA_FLOW` があれば注入する。どの結末も 0 を返す。"""
    env = os.environ if environ is None else environ
    out = sys.stdout if stdout is None else stdout
    send = post_event if post is None else post
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
    try:
        send(_read_port(env), session_id, body)
    except (OSError, ValueError) as error:
        # 常駐サーバーへ送れない: 会話を止めずに 1 行だけ残す
        print(
            f"[mindstella] 常駐サーバーへ出来事を送れません（{body['event']}）: {error}",
            file=sys.stderr,
        )

    flow = env.get("MINDSTELLA_FLOW")
    # SessionStart で進め方の文書がある: 場所を注入する
    if body["event"] == "session_start" and flow:
        context = (
            f"このワークスペースの進め方の文書は {flow}（配信元の ID#文書の ID）。"
            "project-index の search_docs で参照する。"
        )
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
    return 0


def post_event(port: int, session_id: str, body: dict[str, Any]) -> None:
    """`POST /_admin/sessions/{session}/events` に JSON を送る（`POST_TIMEOUT_SEC` で打ち切る）。"""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/_admin/sessions/{session_id}/events",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with _OPENER.open(request, timeout=POST_TIMEOUT_SEC) as response:
        response.read()


def _build_body(
    event: str, hook_input: dict[str, Any], environ: Mapping[str, str]
) -> dict[str, Any]:
    """出来事・Claude Code の session_id・ペイン・PID の本文を作る。"""
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
    return body


def _read_port(environ: Mapping[str, str]) -> int:
    """送り先のポートを返す。"""
    value = environ.get("MINDSTELLA_PORT")
    return int(value) if value else DEFAULT_PORT


if __name__ == "__main__":
    sys.exit(main())
