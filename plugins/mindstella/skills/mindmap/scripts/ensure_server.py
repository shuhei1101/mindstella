"""mindstella の常駐サーバーが待ち受けているかを確かめ、落ちていれば systemd --user のユニットを書いて起動する。

依存が揃う前のシステムの `python3` で起動するため、Python 3.8 で読める構文と標準ライブラリだけで書く。
使い方:
# SessionStart のフックから呼ぶ（案内を標準出力に出し、どの結末も終了コード 0）
python3 ensure_server.py --hook
# 起動スクリプトから呼ぶ（案内を標準エラーに出し、起動できなければ終了コード 1）
python3 ensure_server.py
# このスクリプトのプラグインのフォルダでユニットを書き直し、待ち受けていても起動し直す
python3 ensure_server.py --restart
"""

from __future__ import annotations

import argparse
import json
import os
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

# プラグインのフォルダ（`version.ini` を持つ）
PLUGIN_ROOT = Path(__file__).resolve().parents[3]

# プラグインのフォルダから常駐サーバーの入口へのパス
SERVER_ENTRY = Path("skills") / "mindmap" / "scripts" / "server.py"

# systemd --user のユニットの名前
UNIT_NAME = "mindstella.service"

# 常駐サーバーが落ちたときに起動し直すまでの秒数
UNIT_RESTART_SEC = 5

# 起動し直しの上限（この秒数の間にこの回数を超えて落ちたら諦める）
UNIT_START_LIMIT = (60, 3)

# ユニットの Environment= に書く、呼び出し元の環境変数の名前の頭
PASS_ENV_PREFIXES = ("MINDSTELLA_", "PROJECT_INDEX_PORT", "XDG_STATE_HOME")

# ポートはつながるが mindstella の応答でないときの fetch_status の値
PORT_IN_USE = "port_in_use"

# 起動した常駐サーバーが待ち受ける前に落ちたとみなすユニットの状態
EXITED_UNIT_STATES = ("failed", "activating")

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

# 古いコードの常駐サーバーが待ち受けているときの、起動し直す手順の案内
RESTART_GUIDE = (
    "{プラグインのフォルダ}/bin/mindstella server restart で常駐サーバーを起動し直してください"
)

# 待ち受けのポートが使われているときの案内
PORT_GUIDE = "環境変数 MINDSTELLA_PORT で別のポートを渡してください"

# systemd --user が使えないときの案内
SYSTEMD_GUIDE = "常駐サーバーは systemd --user のユニットで動かします。systemd --user が動く端末で使ってください"

# 依存をそろえるコマンドを作れないとき（仮想環境を作る Python が古い）の案内
PYTHON_GUIDE = "Python 3.12 以上を入れてから、スキル専用の仮想環境を作ってください"


class ServerExitedError(Exception):
    """起動した常駐サーバーが待ち受ける前に落ちた（ユニットが failed か、起動し直しを待っている）。"""

    def __init__(self, state: str, log_tail: list[str]) -> None:
        """ユニットの状態と、起動してから記録に書き足された行の末尾を持つ。"""
        super().__init__(f"常駐サーバーが待ち受ける前に落ちました（ユニットの状態 {state}）")
        self.state = state
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
    fetch: Callable[[int], Any] | None = None,
    systemctl: Callable[[list[str]], int] | None = None,
    log_file: Path | None = None,
) -> int:
    """同じコードで待ち受けていれば何もせず、違えば違いと手順を示し、落ちていればユニットを書いて起動して待つ。"""
    parser = argparse.ArgumentParser(description="mindstella の常駐サーバーの起動の確認")
    parser.add_argument("--hook", action="store_true", help="SessionStart のフックからの呼び出し")
    parser.add_argument(
        "--restart", action="store_true", help="待ち受けていてもユニットを書き直して起動し直す"
    )
    args = parser.parse_args(argv)
    env = os.environ if environ is None else environ
    read_status = fetch_status if fetch is None else fetch
    run = run_systemctl if systemctl is None else systemctl
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
        say(
            f"{ERROR_PREFIX}MINDSTELLA_PORT の値 {raw_port} は誤りです。1〜65535 の整数を渡してください"
        )
        return failure

    status = read_status(port)
    # ポートを別のプロセスが使っている: 起動しても待ち受けられないので起動しない
    if status == PORT_IN_USE:
        say(f"{ERROR_PREFIX}ポート {port} は mindstella でないプロセスが使っています", PORT_GUIDE)
        return failure
    # 待ち受けている（起動し直しでない）: バージョンとプラグインのフォルダを比べる
    if isinstance(status, dict) and not args.restart:
        differences = is_outdated(status, PLUGIN_ROOT)
        # 同じコード: 何もしない
        if differences is None:
            return 0
        # 古いコード: 並行する別のセッションが使っているため起動し直さず、違いと手順を示す
        say(
            f"{MESSAGE_PREFIX}常駐サーバーは古いコードで動いています",
            *[
                f"  {name}: 動いている {running} / インストールした {installed}"
                for name, running, installed in differences
            ],
            RESTART_GUIDE,
        )
        return 0

    # 落ちているか起動し直す: 依存を確かめてからユニットを書いて起動する
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

    # systemd --user が使えない: ユニットを書かずに止める
    if run(["show-environment"]) != 0:
        say(f"{ERROR_PREFIX}systemd --user を使えません", SYSTEMD_GUIDE)
        return failure
    log_path.parent.mkdir(parents=True, exist_ok=True)
    offset = log_path.stat().st_size if log_path.exists() else 0
    write_unit(unit_text(report["python_path"], PLUGIN_ROOT, env, log_path), env)
    action = "restart" if args.restart else "start"
    for command in (["daemon-reload"], [action, UNIT_NAME]):
        code = run(command)
        if code != 0:
            say(
                f"{ERROR_PREFIX}systemctl --user {' '.join(command)} が終了コード {code} で終わりました",
                f"記録: {log_path}",
            )
            return failure
    try:
        wait_until_ready(port, log_file=log_path, log_offset=offset, fetch=read_status)
    except ServerExitedError as error:
        say(f"{ERROR_PREFIX}{error}", *error.log_tail, f"記録: {log_path}")
        return failure
    except ServerStartTimeoutError as error:
        say(f"{ERROR_PREFIX}{error}", f"記録を確かめてください: {log_path}")
        return failure

    started = f"{MESSAGE_PREFIX}常駐サーバーを{'起動し直しました' if args.restart else '起動しました'}（ポート {port}）"
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
) -> dict[str, Any] | str | None:
    """`http://127.0.0.1:{port}/_admin/status` を読み、mindstella の状態なら返す。

    つながらないときは None、つながるのに mindstella の応答でないときは `PORT_IN_USE` を返す。
    """
    # 環境変数のプロキシを通さない
    client = (
        urllib.request.build_opener(urllib.request.ProxyHandler({})) if opener is None else opener
    )
    url = f"http://127.0.0.1:{port}{STATUS_PATH}"
    try:
        with client.open(url, timeout=STATUS_TIMEOUT_SEC) as response:
            body = response.read()
            status_code = response.status
    except urllib.error.HTTPError:
        # 200 番台でない応答: 別のプロセスが待ち受けている
        return PORT_IN_USE
    except (OSError, urllib.error.URLError):
        # つながらない・時間切れ: 落ちているとみなす
        return None
    if status_code != HTTP_OK:
        return PORT_IN_USE
    try:
        payload = json.loads(body.decode("utf-8"))
    except ValueError:
        return PORT_IN_USE
    if isinstance(payload, dict) and payload.get("name") == SERVER_NAME:
        return payload
    return PORT_IN_USE


def read_installed_version(plugin_root: Path) -> str:
    """プラグインのフォルダの `version.ini` の 1 行目を返す。"""
    text = (plugin_root / "version.ini").read_text(encoding="utf-8")
    return text.splitlines()[0].strip()


def is_outdated(status: dict[str, Any], plugin_root: Path) -> list[tuple[str, str, str]] | None:
    """動いている常駐サーバーとこのプラグインの、バージョンとプラグインのフォルダの末尾の名前の違う組を返す。同じなら None。"""
    differences: list[tuple[str, str, str]] = []
    installed = read_installed_version(plugin_root)
    if status.get("version") != installed:
        differences.append(("version", str(status.get("version")), installed))
    running_root = status.get("plugin_root")
    # 末尾のフォルダ名（インストールの単位）だけを比べ、別のプロファイルの同じインストールは同じとみなす
    if running_root and Path(str(running_root)).name != plugin_root.name:
        differences.append(("plugin", Path(str(running_root)).name, plugin_root.name))
    return differences or None


def unit_text(
    python_path: str, plugin_root: Path, environ: Mapping[str, str], log_file: Path
) -> str:
    """`mindstella.service` の中身を返す。"""
    interval, burst = UNIT_START_LIMIT
    passed = sorted(
        (name, value)
        for name, value in environ.items()
        if name.startswith(PASS_ENV_PREFIXES) and value
    )
    lines = [
        "[Unit]",
        "Description=MindStella の常駐サーバー",
        f"StartLimitIntervalSec={interval}",
        f"StartLimitBurst={burst}",
        "",
        "[Service]",
        "Type=exec",
        f"ExecStart={_unit_quote(python_path)} {_unit_quote(str(plugin_root / SERVER_ENTRY))}",
        *[f"Environment={_unit_quote(f'{name}={value}')}" for name, value in passed],
        f"StandardOutput=append:{log_file}",
        f"StandardError=append:{log_file}",
        "Restart=on-failure",
        f"RestartSec={UNIT_RESTART_SEC}",
        # 常駐サーバーが立てた tmux のサーバー（MindStella のセッション）を、起動し直しで止めない
        "KillMode=process",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ]
    return "\n".join(lines)


def write_unit(text: str, environ: Mapping[str, str]) -> bool:
    """ユニットのファイルを書く。中身が同じなら書かずに False を返す。"""
    base = environ.get("XDG_CONFIG_HOME") or ""
    path = (Path(base) if base else Path.home() / ".config") / "systemd" / "user" / UNIT_NAME
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{UNIT_NAME}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(str(temp), str(path))
    return True


def run_systemctl(args: list[str]) -> int:
    """`systemctl --user {引数}` を子プロセスで呼び、終了コードを返す。"""
    completed = subprocess.run(["systemctl", "--user", *args], capture_output=True, check=False)
    return completed.returncode


def read_unit_state() -> str:
    """`systemctl --user is-active mindstella.service` の出力を返す。"""
    completed = subprocess.run(
        ["systemctl", "--user", "is-active", UNIT_NAME], capture_output=True, text=True, check=False
    )
    return completed.stdout.strip()


def wait_until_ready(
    port: int,
    *,
    log_file: Path,
    log_offset: int,
    fetch: Callable[[int], Any] | None = None,
    unit_state: Callable[[], str] | None = None,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """起動した常駐サーバーが状態の GET に応答するまで待ち、落ちたか上限を過ぎたら理由の例外を送る。"""
    read_status = fetch_status if fetch is None else fetch
    read_state = read_unit_state if unit_state is None else unit_state
    now = time.monotonic if clock is None else clock
    pause = time.sleep if sleep is None else sleep
    deadline = now() + START_TIMEOUT_SEC
    # 待つ回数の上限（待った秒の合計が上限を越えない回数）
    waits_left = int(START_TIMEOUT_SEC // START_POLL_SEC) - 1
    while True:
        status = read_status(port)
        if isinstance(status, dict):
            return status
        state = read_state()
        # 待ち受ける前に落ちた: 書き足された記録の末尾を添える
        if state in EXITED_UNIT_STATES:
            raise ServerExitedError(state, _read_log_tail(log_file, log_offset))
        # 上限に届いた: これ以上待たない
        if waits_left <= 0 or now() >= deadline:
            raise ServerStartTimeoutError()
        pause(START_POLL_SEC)
        waits_left -= 1


def _unit_quote(value: str) -> str:
    """`%` を書き換え、空白か引用符を含む値を systemd のユニットの二重引用符で囲む。"""
    value = value.replace("%", "%%")
    if not any(char in value for char in " \t\"'\\"):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
