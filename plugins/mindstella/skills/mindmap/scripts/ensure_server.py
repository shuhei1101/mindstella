"""mindstella の常駐サーバーが待ち受けているかを確かめ、落ちていれば仮想環境の Python で起動する。

依存が揃う前のシステムの `python3` で起動するため、Python 3.8 で読める構文と標準ライブラリだけで書く。
使い方:
# SessionStart のフックから呼ぶ（案内を標準出力に出し、どの結末も終了コード 0）
python3 ensure_server.py --hook
# 起動スクリプトから呼ぶ（案内を標準エラーに出し、起動できなければ終了コード 1）
python3 ensure_server.py
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TextIO

import check_env

# `MINDSTELLA_PORT` が無いか空のときに確かめるポート（`server.py` の同じ名前の定数と合わせる）
DEFAULT_PORT = 8784

# 待ち受けているのが mindstella かを見分ける、状態の `name`（`server.py` の同じ名前の定数と合わせる）
SERVER_NAME = "mindstella"

# 常駐サーバーの状態を読む GET のパス（`server.py` の同じ名前の定数と合わせる）
STATUS_PATH = "/_admin/status"

# 状態の GET 1 回を打ち切る秒数
STATUS_TIMEOUT_SEC = 1.0

# 起動してから待ち受けるまで待つ秒数
START_TIMEOUT_SEC = 10.0

# 起動を待つ間に状態を確かめる間隔の秒数
START_POLL_SEC = 0.2

# 常駐サーバーが起動直後に終わったときに示す、記録の末尾の行数
LOG_TAIL_LINES = 20

# 起動する常駐サーバーの入口
SERVER_FILE = Path(__file__).resolve().parent / "server.py"

# プラグインのフォルダ（`version.ini` を持つ）
PLUGIN_ROOT = Path(__file__).resolve().parents[3]

# 状態の GET が成り立ったときの HTTP の終了コード
HTTP_OK = 200

# ポートの値の範囲
PORT_MIN = 1
PORT_MAX = 65535

# 案内の行の頭
MESSAGE_PREFIX = "[mindstella] "
ERROR_PREFIX = "[mindstella] エラー: "

# 起動したときに、会話の始まりにつなげなかったツールをつなぎ直す案内
RECONNECT_GUIDE = "mindstella のツールが無ければ、/mcp で mindstella につなぎ直してください"

# バージョンが違うときの、起動し直す手順の案内
RESTART_GUIDE = (
    "mindstella のツール server_stop で常駐サーバーを止めてから、Claude Code を立ち上げ直してください"
)

# 待ち受けのポートが使われているときの案内
PORT_GUIDE = "環境変数 MINDSTELLA_PORT で別のポートを渡してください"

# 依存をそろえるコマンドを作れないとき（仮想環境を作る Python が古い）の案内
PYTHON_GUIDE = "Python 3.12 以上を入れてから、スキル専用の仮想環境を作ってください"


class PortInUseError(Exception):
    """起動した常駐サーバーが待ち受ける前に終わり、そのポートに別のプロセスがつながる。"""

    def __init__(self, port: int) -> None:
        """待ち受けのポートを持つ。"""
        super().__init__(f"ポート {port} は別のプロセスが使っています")
        self.port = port


class ServerExitedError(Exception):
    """起動した常駐サーバーが待ち受ける前に終わり、ポートは空いている。"""

    def __init__(self, returncode: int, log_tail: list[str]) -> None:
        """終了コードと、起動してから記録に書き足された行の末尾を持つ。"""
        super().__init__(f"常駐サーバーが起動直後に終わりました（終了コード {returncode}）")
        self.returncode = returncode
        self.log_tail = log_tail


class ServerStartTimeoutError(Exception):
    """起動した常駐サーバーが、終わらないまま上限の秒数までに状態の GET へ応答しない。"""

    def __init__(self) -> None:
        """待った秒数の上限をメッセージにする。"""
        super().__init__(f"常駐サーバーが {START_TIMEOUT_SEC:g} 秒以内に応答しません")


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    fetch: Callable[[int], dict[str, Any] | None] | None = None,
    start: Callable[..., Any] | None = None,
    log_file: Path | None = None,
) -> int:
    """常駐サーバーが同じバージョンで待ち受けていれば何もせず、違えば差と手順を示し、落ちていれば起動して待つ。"""
    parser = argparse.ArgumentParser(description="mindstella の常駐サーバーの起動の確認")
    parser.add_argument("--hook", action="store_true", help="SessionStart のフックからの呼び出し")
    args = parser.parse_args(argv)
    env = os.environ if environ is None else environ
    read_status = fetch_status if fetch is None else fetch
    run_start = start_server if start is None else start
    log_path = Path.home() / ".mindmap" / "server.log" if log_file is None else log_file

    # フックからの呼び出し: 入力を読み捨て、案内を標準出力に出し、失敗でも会話の始まりを止めない
    if args.hook:
        (sys.stdin if stdin is None else stdin).read()
        out = sys.stdout if stdout is None else stdout
        failure = 0
    else:
        # 起動スクリプトからの呼び出し: 案内を標準エラーに出し、失敗は終了コード 1
        out = sys.stderr if stderr is None else stderr
        failure = 1

    def say(*lines: str) -> None:
        """案内の行を出力先へ書く。"""
        for line in lines:
            print(line, file=out)

    raw_port = env.get("MINDSTELLA_PORT") or ""
    port = _parse_port(raw_port)
    if port is None:
        say(f"{ERROR_PREFIX}MINDSTELLA_PORT の値 {raw_port} は誤りです。1〜65535 の整数を渡してください")
        return failure

    status = read_status(port)
    # 待ち受けている: バージョンを比べる
    if status is not None:
        installed = read_installed_version(PLUGIN_ROOT)
        # 同じバージョン: 何もしない
        if status.get("version") == installed:
            return 0
        # 違うバージョン: 並行する別のセッションが使っているため起動し直さず、差と手順を示す
        say(
            f"{MESSAGE_PREFIX}常駐サーバーのバージョン {status.get('version')} と、"
            f"インストールしたプラグインのバージョン {installed} が違います",
            RESTART_GUIDE,
        )
        return 0

    # 落ちている: 依存を確かめてから起動する
    venv = env.get("MINDSTELLA_VENV") or ""
    venv_dir = Path(venv).expanduser() if venv else check_env.default_venv_dir()
    try:
        report = check_env.run_check_env(venv_dir)
    except (
        check_env.VenvNotFoundError,
        check_env.PythonVersionError,
        check_env.DependencyMissingError,
    ) as error:
        say(*_dependency_lines(error.report))
        return failure

    offset = log_path.stat().st_size if log_path.exists() else 0
    process = run_start(report["python_path"], environ=env, log_file=log_path)
    try:
        wait_until_ready(process, port, log_file=log_path, log_offset=offset, fetch=read_status)
    except PortInUseError as error:
        say(f"{ERROR_PREFIX}{error}", PORT_GUIDE)
        return failure
    except ServerExitedError as error:
        say(f"{ERROR_PREFIX}{error}", *error.log_tail, f"記録: {log_path}")
        return failure
    except ServerStartTimeoutError as error:
        say(f"{ERROR_PREFIX}{error}", f"記録を確かめてください: {log_path}")
        return failure

    started = f"{MESSAGE_PREFIX}常駐サーバーを起動しました（ポート {port}）"
    # フックからの呼び出しだけ、つなぎ直す案内を添える
    if args.hook:
        say(started, RECONNECT_GUIDE)
    else:
        say(started)
    return 0


def _parse_port(value: str) -> int | None:
    """`MINDSTELLA_PORT` の値をポートにする。空なら既定のポート、1〜65535 の整数でなければ None。"""
    if not value:
        return DEFAULT_PORT
    try:
        port = int(value)
    except ValueError:
        return None
    return port if PORT_MIN <= port <= PORT_MAX else None


def _dependency_lines(report: dict[str, Any]) -> list[str]:
    """依存の確認の結果から、足りないものとそろえるコマンドの案内の行を作る。"""
    missing = [row["name"] for row in report.get("packages") or [] if not row.get("ok")]
    # 仮想環境か Python が足りないときは、ライブラリより先に示す
    if report.get("venv_ok") is False:
        missing.insert(0, "仮想環境")
    elif report.get("python_ok") is False:
        missing.insert(0, "Python")
    command = report.get("install")
    return [
        f"{ERROR_PREFIX}仮想環境の依存がそろっていません（{'・'.join(missing)}）",
        command if command else PYTHON_GUIDE,
    ]


def fetch_status(
    port: int, opener: urllib.request.OpenerDirector | None = None
) -> dict[str, Any] | None:
    """`http://127.0.0.1:{port}/_admin/status` を読み、mindstella の状態なら返す。"""
    # 環境変数のプロキシを通さない
    client = urllib.request.build_opener(urllib.request.ProxyHandler({})) if opener is None else opener
    url = f"http://127.0.0.1:{port}{STATUS_PATH}"
    try:
        with client.open(url, timeout=STATUS_TIMEOUT_SEC) as response:
            if response.status != HTTP_OK:
                return None
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError):
        # つながらない・時間切れ・200 でない・JSON でない: 落ちているとみなす
        return None
    if isinstance(payload, dict) and payload.get("name") == SERVER_NAME:
        return payload
    return None


def read_installed_version(plugin_root: Path) -> str:
    """プラグインのフォルダの `version.ini` の 1 行目を返す。"""
    text = (plugin_root / "version.ini").read_text(encoding="utf-8")
    return text.splitlines()[0].strip()


def start_server(
    python_path: str,
    *,
    environ: Mapping[str, str],
    log_file: Path,
    popen: Callable[..., Any] = subprocess.Popen,
) -> Any:
    """仮想環境の Python で `server.py` を新しいセッションで起動し、標準出力と標準エラーを記録へ書き足す。"""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    # 子プロセスが自分の複製を持つので、親の側は起動した後に閉じる
    with log_file.open("ab") as log:
        # 呼び出し元のセッションが終わっても残るよう、新しいセッションで起動する
        return popen(
            [python_path, str(SERVER_FILE)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=dict(environ),
            cwd=str(Path.home()),
            start_new_session=True,
        )


def wait_until_ready(
    process: Any,
    port: int,
    *,
    log_file: Path,
    log_offset: int,
    fetch: Callable[[int], dict[str, Any] | None] | None = None,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """起動した常駐サーバーが状態の GET に応答するまで待ち、終わったか上限を過ぎたら理由の例外を送る。"""
    read_status = fetch_status if fetch is None else fetch
    now = time.monotonic if clock is None else clock
    pause = time.sleep if sleep is None else sleep
    deadline = now() + START_TIMEOUT_SEC
    # 待つ回数の上限（待った秒の合計が上限を越えない回数）
    waits_left = int(START_TIMEOUT_SEC // START_POLL_SEC) - 1
    while True:
        returncode = process.poll()
        # 待ち受ける前に終わった: ポートの使われ方で理由を分ける
        if returncode is not None:
            if _is_listening(port):
                raise PortInUseError(port)
            raise ServerExitedError(returncode, _read_log_tail(log_file, log_offset))
        status = read_status(port)
        if status is not None:
            return status
        # 上限に届いた: これ以上待たない
        if waits_left <= 0 or now() >= deadline:
            raise ServerStartTimeoutError()
        pause(START_POLL_SEC)
        waits_left -= 1


def _is_listening(port: int) -> bool:
    """`127.0.0.1` のそのポートへつながるかを返す。"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=STATUS_TIMEOUT_SEC):
            return True
    except OSError:
        return False


def _read_log_tail(log_file: Path, offset: int) -> list[str]:
    """記録のファイルの offset より後ろに書き足された行の末尾 `LOG_TAIL_LINES` 行を返す。"""
    if not log_file.exists():
        return []
    with log_file.open("rb") as log:
        log.seek(offset)
        appended = log.read().decode("utf-8", errors="replace")
    return appended.splitlines()[-LOG_TAIL_LINES:]


if __name__ == "__main__":
    sys.exit(main())
