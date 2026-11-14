"""ensure_server.py（常駐サーバーの起動の確認：状態を読む・ユニットを書いて起動する・待ち受けるまで待つ）の単体テスト。"""

from __future__ import annotations

import ast
import io
import json
import subprocess
from types import SimpleNamespace
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

import check_env
import ensure_server

# インストールしたプラグインのバージョン（テストの中で置く version.ini の 1 行目）
CURRENT_VERSION = "v0.12.0"

# 待ち受けている常駐サーバーが返す、同じバージョンの状態（plugin_root は fixture が足す）
RUNNING_STATUS: dict[str, Any] = {"name": "mindstella", "version": CURRENT_VERSION}

# プラグインのフォルダの末尾のフォルダ名（インストールの単位）
PLUGIN_TAIL = "c938"

# SessionStart のフックが標準入力へ渡す入力
HOOK_INPUT = json.dumps({"hook_event_name": "SessionStart"})

# 依存がそろっているときの依存の確認の結果
GOOD_REPORT: dict[str, Any] = {
    "venv_ok": True,
    "python_ok": True,
    "python_path": "/v/bin/python",
    "packages": [
        {"name": "PyYAML", "ok": True},
        {"name": "jsonschema", "ok": True},
        {"name": "mcp", "ok": True},
    ],
    "install": None,
}

# mcp が足りないときの依存の確認の結果
MISSING_MCP_REPORT: dict[str, Any] = {
    "venv_ok": True,
    "python_ok": True,
    "python_path": "/v/bin/python",
    "packages": [
        {"name": "PyYAML", "ok": True},
        {"name": "jsonschema", "ok": True},
        {"name": "mcp", "ok": False},
    ],
    "install": '"/v/bin/python" -m pip install "mcp>=2.3.0"',
}

# 起動してから記録のファイルに書き足される 30 行と、そのうち示す末尾の 20 行
APPENDED_LOG_LINES = [f"line {number}" for number in range(1, 31)]
TAIL_LOG_LINES = [f"line {number}" for number in range(11, 31)]


class _FakeTime:
    """時刻を控え、待つと待った分だけ進む偽の時計と待ち。"""

    def __init__(self) -> None:
        """時刻を 0 から始め、待った秒を控える入れ物を作る。"""
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        """今の時刻を返す。"""
        return self.now

    def sleep(self, seconds: float) -> None:
        """待たずに、待った秒を控えて時刻を進める。"""
        self.sleeps.append(seconds)
        self.now += seconds


class _Recorder:
    """呼ばれた引数を控え、決めた値を順に返す偽の関数。最後の値は繰り返す。"""

    def __init__(self, *results: Any) -> None:
        """返す値を呼ばれる順に受け取る。"""
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self._results = list(results)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """引数を控え、次の値を返す。"""
        self.calls.append((args, kwargs))
        index = min(len(self.calls), len(self._results)) - 1
        return self._results[index]


@pytest.fixture
def installed_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """プラグインのフォルダを version.ini に CURRENT_VERSION を書いた一時フォルダに差し替え、その版を返す。"""
    plugin_root = tmp_path / "plugin" / PLUGIN_TAIL
    plugin_root.mkdir(parents=True)
    (plugin_root / "version.ini").write_text(f"{CURRENT_VERSION}\n", encoding="utf-8")
    monkeypatch.setattr(ensure_server, "PLUGIN_ROOT", plugin_root)
    return CURRENT_VERSION


@pytest.fixture
def running_status(installed_version: str) -> dict[str, Any]:
    """同じバージョンと同じプラグインのフォルダで待ち受けている常駐サーバーの状態。"""
    return {**RUNNING_STATUS, "plugin_root": str(ensure_server.PLUGIN_ROOT)}


def _patch_check_env(monkeypatch: pytest.MonkeyPatch, run: Callable[..., dict[str, Any]]) -> None:
    """依存の確認を run に差し替える（モジュールの関数と、名前で取り込んだ関数の両方）。"""
    monkeypatch.setattr(check_env, "run_check_env", run)
    monkeypatch.setattr(ensure_server, "run_check_env", run, raising=False)


def _raising(error: Exception) -> Callable[..., Any]:
    """呼ばれると error を送る関数を作る。"""

    def _raise(*args: Any, **kwargs: Any) -> Any:
        """何もせずに決めた例外を送る。"""
        raise error

    return _raise


class _Systemctl:
    """systemctl --user の引数を控え、show-environment だけ決めた終了コードを返す偽の関数。"""

    def __init__(self, show_environment: int = 0) -> None:
        """show-environment の終了コードを受け取る。"""
        self.calls: list[list[str]] = []
        self._show_environment = show_environment

    def __call__(self, args: list[str]) -> int:
        """引数を控え、終了コードを返す。"""
        self.calls.append(list(args))
        return self._show_environment if args[:1] == ["show-environment"] else 0

    def commands(self) -> list[str]:
        """控えた呼び出しを 1 つの文字列ずつにして返す。"""
        return [" ".join(call) for call in self.calls]


def _unit_path(config_home: Path) -> Path:
    """ユニットのファイルのパス。"""
    return config_home / "systemd" / "user" / ensure_server.UNIT_NAME


def _run_main(
    argv: list[str],
    *,
    fetch: Callable[[int], Any],
    systemctl: _Systemctl,
    log_file: Path,
    environ: dict[str, str] | None = None,
) -> tuple[int, dict[str, str]]:
    """main を呼び、終了コードと、標準出力・標準エラーに出た文字列を返す。"""
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = ensure_server.main(
        argv,
        environ={"XDG_CONFIG_HOME": str(log_file.parent / "config")}
        if environ is None
        else environ,
        stdin=io.StringIO(HOOK_INPUT),
        stdout=stdout,
        stderr=stderr,
        fetch=fetch,
        systemctl=systemctl,
        log_file=log_file,
    )
    return code, {"stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


def test_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, running_status: dict[str, Any]
) -> None:
    """落ちていればユニットを書いて起動し、つなぎ直す案内を出す（正常系）。"""
    # 準備
    fetch = _Recorder(None, running_status)
    systemctl = _Systemctl()
    _patch_check_env(monkeypatch, lambda *args, **kwargs: GOOD_REPORT)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    # 実行
    code, output = _run_main(
        ["--hook"], fetch=fetch, systemctl=systemctl, log_file=tmp_path / "server.log"
    )
    # 検証
    assert code == 0
    assert _unit_path(tmp_path / "config").is_file()
    assert systemctl.commands() == [
        "show-environment",
        "daemon-reload",
        f"start {ensure_server.UNIT_NAME}",
    ]
    assert "ポート 8784" in output["stdout"]
    assert "/mcp" in output["stdout"]


def test_main_when_running(tmp_path: Path, running_status: dict[str, Any]) -> None:
    """同じバージョンと同じプラグインのフォルダで待ち受けていれば何もしない（正常系）。"""
    # 準備
    systemctl = _Systemctl()
    # 実行
    code, output = _run_main(
        ["--hook"],
        fetch=_Recorder(running_status),
        systemctl=systemctl,
        log_file=tmp_path / "server.log",
    )
    # 検証
    assert code == 0
    assert systemctl.calls == []
    assert output["stdout"] == ""


@pytest.mark.parametrize(
    ("changes", "expected_texts"),
    [
        pytest.param({"version": "v0.0.1"}, ["v0.0.1", CURRENT_VERSION], id="version"),
        pytest.param({"plugin_root": "/p/mindstella/0fd2"}, ["0fd2", PLUGIN_TAIL], id="plugin"),
    ],
)
def test_main_when_outdated(
    tmp_path: Path,
    running_status: dict[str, Any],
    changes: dict[str, str],
    expected_texts: list[str],
) -> None:
    """古いコードで待ち受けていれば起動し直さずに違いと手順を示す（正常系）。"""
    # 準備
    systemctl = _Systemctl()
    # 実行
    code, output = _run_main(
        ["--hook"],
        fetch=_Recorder({**running_status, **changes}),
        systemctl=systemctl,
        log_file=tmp_path / "server.log",
    )
    # 検証
    assert code == 0
    assert not any(call[0] in ("start", "restart") for call in systemctl.calls)
    assert all(text in output["stdout"] for text in expected_texts)
    assert "mindstella server restart" in output["stdout"]


@pytest.mark.parametrize(
    ("argv", "expected_code", "stream"),
    [
        pytest.param(["--hook"], 0, "stdout", id="hook"),
        pytest.param([], 1, "stderr", id="launcher"),
    ],
)
def test_main_when_port_invalid(
    tmp_path: Path, argv: list[str], expected_code: int, stream: str
) -> None:
    """ポートの値が誤りなら確かめずに案内する（異常系）。"""
    # 準備
    fetch = _Recorder(None)
    systemctl = _Systemctl()
    # 実行
    code, output = _run_main(
        argv,
        fetch=fetch,
        systemctl=systemctl,
        log_file=tmp_path / "server.log",
        environ={"MINDSTELLA_PORT": "abc"},
    )
    # 検証
    assert code == expected_code
    assert "abc" in output[stream]
    assert fetch.calls == []
    assert systemctl.calls == []


@pytest.mark.parametrize(
    ("argv", "expected_code", "stream"),
    [
        pytest.param(["--hook"], 0, "stdout", id="hook"),
        pytest.param([], 1, "stderr", id="launcher"),
    ],
)
def test_main_when_dependency_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    expected_code: int,
    stream: str,
) -> None:
    """依存が足りなければ起動せずにそろえるコマンドを示す（異常系）。"""
    # 準備
    systemctl = _Systemctl()
    _patch_check_env(monkeypatch, _raising(check_env.DependencyMissingError(MISSING_MCP_REPORT)))
    # 実行
    code, output = _run_main(
        argv, fetch=_Recorder(None), systemctl=systemctl, log_file=tmp_path / "server.log"
    )
    # 検証
    assert code == expected_code
    assert "mcp" in output[stream]
    assert MISSING_MCP_REPORT["install"] in output[stream]
    assert not any(call[0] == "start" for call in systemctl.calls)


def test_main_when_port_in_use(tmp_path: Path, installed_version: str) -> None:
    """ポートが別のプロセスに使われていれば起動せずに示す（異常系）。"""
    # 準備
    systemctl = _Systemctl()
    # 実行
    code, output = _run_main(
        ["--hook"],
        fetch=_Recorder(ensure_server.PORT_IN_USE),
        systemctl=systemctl,
        log_file=tmp_path / "server.log",
    )
    # 検証
    assert code == 0
    assert systemctl.calls == []
    assert "8784" in output["stdout"]
    assert "MINDSTELLA_PORT" in output["stdout"]


@pytest.mark.parametrize(
    ("argv", "expected_code", "stream"),
    [
        pytest.param(["--hook"], 0, "stdout", id="hook"),
        pytest.param([], 1, "stderr", id="launcher"),
    ],
)
def test_main_when_systemd_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    installed_version: str,
    argv: list[str],
    expected_code: int,
    stream: str,
) -> None:
    """systemd --user が使えなければユニットを書かずに示す（異常系）。"""
    # 準備
    systemctl = _Systemctl(show_environment=1)
    _patch_check_env(monkeypatch, lambda *args, **kwargs: GOOD_REPORT)
    # 実行
    code, output = _run_main(
        argv, fetch=_Recorder(None), systemctl=systemctl, log_file=tmp_path / "server.log"
    )
    # 検証
    assert code == expected_code
    assert not _unit_path(tmp_path / "config").exists()
    assert "systemd --user" in output[stream]


def test_main_when_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, running_status: dict[str, Any]
) -> None:
    """--restart では待ち受けていてもユニットを書き直して起動し直す（正常系）。"""
    # 準備
    systemctl = _Systemctl()
    _patch_check_env(monkeypatch, lambda *args, **kwargs: GOOD_REPORT)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    # 実行
    code, _output = _run_main(
        ["--restart"],
        fetch=_Recorder(running_status),
        systemctl=systemctl,
        log_file=tmp_path / "server.log",
    )
    # 検証
    assert code == 0
    unit = _unit_path(tmp_path / "config").read_text(encoding="utf-8")
    assert (
        f"ExecStart=/v/bin/python {ensure_server.PLUGIN_ROOT}/skills/mindmap/scripts/server.py"
        in unit
    )
    commands = systemctl.commands()
    assert commands.index("daemon-reload") < commands.index(f"restart {ensure_server.UNIT_NAME}")


def test_main_when_start_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, installed_version: str
) -> None:
    """起動した常駐サーバーが待ち受ける前に終われば、記録の末尾を示す（異常系）。"""
    # 準備
    _patch_check_env(monkeypatch, lambda *args, **kwargs: GOOD_REPORT)
    monkeypatch.setattr(
        ensure_server,
        "wait_until_ready",
        _raising(ensure_server.ServerExitedError("failed", ["ImportError: x"])),
    )
    # 実行
    code, output = _run_main(
        [], fetch=_Recorder(None), systemctl=_Systemctl(), log_file=tmp_path / "server.log"
    )
    # 検証
    assert code == 1
    assert "ImportError: x" in output["stderr"]


def test_main_when_old_syntax(scripts_dir: Path) -> None:
    """Python 3.8 の構文で読め、型注釈を実行時に評価しない（正常系）。"""
    # 準備
    source = (scripts_dir / "ensure_server.py").read_text(encoding="utf-8")
    # 実行
    tree = ast.parse(source, feature_version=(3, 8))
    # 検証
    # 先頭は docstring で、その次の文が `from __future__ import annotations`
    statement = tree.body[1]
    assert isinstance(statement, ast.ImportFrom)
    assert statement.module == "__future__"
    assert len(statement.names) == 1
    assert statement.names[0].name == "annotations"


class _StatusHandler(BaseHTTPRequestHandler):
    """決めた終了コードと本文を、どのパスの GET にも返す偽の常駐サーバー。"""

    # テストごとに差し替える、返す終了コードと本文
    status_code = 200
    body = b""

    def do_GET(self) -> None:
        """決めた終了コードと本文を返す。"""
        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args: Any) -> None:
        """要求の記録を出さない。"""


@pytest.fixture
def status_server() -> Iterator[Callable[[int, bytes], int]]:
    """決めた応答を返す HTTP のサーバーを空きポートで立てる関数を返し、テストの後に止める。"""
    servers: list[ThreadingHTTPServer] = []

    def _start(status_code: int, body: bytes) -> int:
        """status_code と body を返すサーバーを立て、そのポートを返す。"""
        handler = type("_Handler", (_StatusHandler,), {"status_code": status_code, "body": body})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return int(server.server_address[1])

    yield _start
    for server in servers:
        server.shutdown()
        server.server_close()


def _status_port(
    response: tuple[int, bytes] | None,
    status_server: Callable[[int, bytes], int],
    free_port: int,
) -> int:
    """response があればそれを返すサーバーを立ててそのポートを、無ければ待ち受けていないポートを返す。"""
    # 応答を決めていない: 待ち受けていないポート
    if response is None:
        return free_port
    # 応答を決めた: その応答を返すサーバーのポート
    return status_server(*response)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param(
            (200, b'{"name": "mindstella", "version": "v1.0.0"}'),
            {"name": "mindstella", "version": "v1.0.0"},
            id="mindstella",
        ),
        pytest.param((404, b"{}"), ensure_server.PORT_IN_USE, id="not_found"),
        pytest.param((200, b'{"name": "other"}'), ensure_server.PORT_IN_USE, id="other_server"),
        pytest.param((200, b"x"), ensure_server.PORT_IN_USE, id="not_json"),
        pytest.param(None, None, id="not_listening"),
    ],
)
def test_fetch_status(
    status_server: Callable[[int, bytes], int],
    free_port: int,
    response: tuple[int, bytes] | None,
    expected: dict[str, Any] | str | None,
) -> None:
    """mindstella の状態を返し、つながるのに mindstella でなければ PORT_IN_USE を返す（正常系）。"""
    # 準備
    port = _status_port(response, status_server, free_port)
    # 実行
    result = ensure_server.fetch_status(port)
    # 検証
    assert result == expected


def test_read_installed_version(tmp_path: Path) -> None:
    """1 行目を返す（正常系）。"""
    # 準備
    (tmp_path / "version.ini").write_text("v0.12.0\n", encoding="utf-8")
    # 実行
    result = ensure_server.read_installed_version(tmp_path)
    # 検証
    assert result == "v0.12.0"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param({}, None, id="same"),
        pytest.param({"version": "v0.0.1"}, [("version", "v0.0.1", CURRENT_VERSION)], id="version"),
        pytest.param(
            {"plugin_root": f"/other/.claude-sub1/plugins/cache/mindstella/{PLUGIN_TAIL}"},
            None,
            id="other-profile",
        ),
        pytest.param(
            {"plugin_root": "/p/mindstella/0fd2"}, [("plugin", "0fd2", PLUGIN_TAIL)], id="plugin"
        ),
    ],
)
def test_is_outdated(
    running_status: dict[str, Any],
    status: dict[str, str],
    expected: list[tuple[str, str, str]] | None,
) -> None:
    """バージョンとプラグインのフォルダの末尾のフォルダ名の違う組を返す（正常系）。"""
    # 実行
    result = ensure_server.is_outdated({**running_status, **status}, ensure_server.PLUGIN_ROOT)
    # 検証
    assert result == expected


def test_unit_text(tmp_path: Path) -> None:
    """ExecStart・渡す環境変数・記録の書き足し先を持つユニットを返す（正常系）。"""
    # 準備
    log_file = tmp_path / "server.log"
    plugin_root = tmp_path / "plugin"
    # 実行
    text = ensure_server.unit_text(
        "/v/bin/python",
        plugin_root,
        {
            "MINDSTELLA_PORT": "9000",
            "PROJECT_INDEX_PORT": "8786",
            "PATH": "/h/.local/bin:/usr/bin",
            "HOME": "/h",
        },
        log_file,
    )
    # 検証
    lines = text.splitlines()
    assert f"ExecStart=/v/bin/python {plugin_root}/skills/mindmap/scripts/server.py" in lines
    assert "Environment=MINDSTELLA_PORT=9000" in lines
    assert "Environment=PROJECT_INDEX_PORT=8786" in lines
    assert "Environment=PATH=/h/.local/bin:/usr/bin" in lines
    assert not any("HOME=" in line for line in lines)
    assert f"StandardOutput=append:{log_file}" in lines
    assert f"StandardError=append:{log_file}" in lines
    assert "Type=exec" in lines
    assert "Restart=on-failure" in lines


def test_write_unit(tmp_path: Path) -> None:
    """中身が変わったときだけ書く（正常系）。"""
    # 準備
    environ = {"XDG_CONFIG_HOME": str(tmp_path)}
    # 実行
    first = ensure_server.write_unit("[Service]\n", environ)
    written_at = _unit_path(tmp_path).stat().st_mtime_ns
    second = ensure_server.write_unit("[Service]\n", environ)
    # 検証
    assert first is True
    assert second is False
    assert _unit_path(tmp_path).stat().st_mtime_ns == written_at


def test_run_systemctl(monkeypatch: pytest.MonkeyPatch) -> None:
    """systemctl --user を呼び、終了コードを返す（正常系）。"""
    # 準備
    calls: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> SimpleNamespace:
        """引数を控えて 3 を返す。"""
        calls.append(args)
        return SimpleNamespace(returncode=3)

    monkeypatch.setattr(subprocess, "run", run)
    # 実行
    code = ensure_server.run_systemctl(["daemon-reload"])
    # 検証
    assert calls == [["systemctl", "--user", "daemon-reload"]]
    assert code == 3


def test_wait_until_ready(tmp_path: Path) -> None:
    """応答したら状態を返す（正常系）。"""
    # 準備
    fake = _FakeTime()
    fetch = _Recorder(None, None, RUNNING_STATUS)
    # 実行
    result = ensure_server.wait_until_ready(
        8784,
        log_file=tmp_path / "server.log",
        log_offset=0,
        fetch=fetch,
        unit_state=lambda: "active",
        clock=fake.clock,
        sleep=fake.sleep,
    )
    # 検証
    assert result == RUNNING_STATUS
    assert len(fake.sleeps) == 2


def _write_exit_log(log_file: Path) -> int:
    """起動前の 1 行を書いて大きさを控え、起動してから書き足された 30 行を足して、控えた大きさを返す。"""
    log_file.write_text("before start\n", encoding="utf-8")
    offset = log_file.stat().st_size
    with log_file.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(APPENDED_LOG_LINES) + "\n")
    return offset


@pytest.mark.parametrize(
    "unit_state", [pytest.param("failed", id="failed"), pytest.param("activating", id="activating")]
)
def test_wait_until_ready_when_exited(tmp_path: Path, unit_state: str) -> None:
    """ユニットが落ちたら、書き足された記録の末尾を持つ ServerExitedError（異常系）。"""
    # 準備
    log_file = tmp_path / "server.log"
    offset = _write_exit_log(log_file)
    fake = _FakeTime()
    # 実行・検証
    with pytest.raises(ensure_server.ServerExitedError) as raised:
        ensure_server.wait_until_ready(
            8784,
            log_file=log_file,
            log_offset=offset,
            fetch=_Recorder(None),
            unit_state=lambda: unit_state,
            clock=fake.clock,
            sleep=fake.sleep,
        )
    assert raised.value.state == unit_state
    assert raised.value.log_tail == TAIL_LOG_LINES


def test_wait_until_ready_when_timeout(tmp_path: Path) -> None:
    """上限までに応答しなければ ServerStartTimeoutError（異常系）。"""
    # 準備
    fake = _FakeTime()
    # 実行・検証
    with pytest.raises(ensure_server.ServerStartTimeoutError):
        ensure_server.wait_until_ready(
            8784,
            log_file=tmp_path / "server.log",
            log_offset=0,
            fetch=_Recorder(None),
            unit_state=lambda: "active",
            clock=fake.clock,
            sleep=fake.sleep,
        )
    assert sum(fake.sleeps) <= ensure_server.START_TIMEOUT_SEC
