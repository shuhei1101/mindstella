"""ensure_server.py（常駐サーバーの起動の確認：状態を読む・起動する・待ち受けるまで待つ）の単体テスト。"""

from __future__ import annotations

import ast
import io
import json
import subprocess
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

# 待ち受けている常駐サーバーが返す、同じバージョンの状態
RUNNING_STATUS: dict[str, Any] = {"name": "mindstella", "version": CURRENT_VERSION}

# 待ち受けている常駐サーバーが返す、古いバージョンの状態
OUTDATED_STATUS: dict[str, Any] = {"name": "mindstella", "version": "v0.0.1"}

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


class _FakeProcess:
    """poll が決めた終了コードを返す偽のプロセス。"""

    def __init__(self, returncode: int | None) -> None:
        """poll が返す値（終わっていなければ None）を受け取る。"""
        self._returncode = returncode

    def poll(self) -> int | None:
        """決めた終了コードを返す。"""
        return self._returncode


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
    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()
    (plugin_root / "version.ini").write_text(f"{CURRENT_VERSION}\n", encoding="utf-8")
    monkeypatch.setattr(ensure_server, "PLUGIN_ROOT", plugin_root)
    return CURRENT_VERSION


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


def _run_main(
    argv: list[str],
    *,
    fetch: Callable[[int], dict[str, Any] | None],
    start: Callable[..., Any],
    log_file: Path,
    environ: dict[str, str] | None = None,
) -> tuple[int, dict[str, str]]:
    """main を呼び、終了コードと、標準出力・標準エラーに出た文字列を返す。"""
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = ensure_server.main(
        argv,
        environ={} if environ is None else environ,
        stdin=io.StringIO(HOOK_INPUT),
        stdout=stdout,
        stderr=stderr,
        fetch=fetch,
        start=start,
        log_file=log_file,
    )
    return code, {"stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


def test_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, installed_version: str
) -> None:
    """落ちていれば起動し、つなぎ直す案内を出す（正常系）。"""
    # 準備
    fetch = _Recorder(None, {"name": "mindstella", "version": installed_version})
    start = _Recorder(_FakeProcess(None))
    _patch_check_env(monkeypatch, lambda *args, **kwargs: GOOD_REPORT)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    # 実行
    code, output = _run_main(
        ["--hook"], fetch=fetch, start=start, log_file=tmp_path / "server.log"
    )
    # 検証
    assert code == 0
    assert len(start.calls) == 1
    assert "ポート 8784" in output["stdout"]
    assert "/mcp" in output["stdout"]
    assert output["stderr"] == ""


def test_main_when_running(tmp_path: Path, installed_version: str) -> None:
    """同じバージョンが待ち受けていれば何もしない（正常系）。"""
    # 準備
    fetch = _Recorder({"name": "mindstella", "version": installed_version})
    start = _Recorder(_FakeProcess(None))
    # 実行
    code, output = _run_main(
        ["--hook"], fetch=fetch, start=start, log_file=tmp_path / "server.log"
    )
    # 検証
    assert code == 0
    assert start.calls == []
    assert output["stdout"] == ""


@pytest.mark.parametrize(
    ("argv", "stream"),
    [
        pytest.param(["--hook"], "stdout", id="hook"),
        pytest.param([], "stderr", id="launcher"),
    ],
)
def test_main_when_outdated(
    tmp_path: Path, installed_version: str, argv: list[str], stream: str
) -> None:
    """バージョンが違えば起動し直さずに差と手順を示す（正常系）。"""
    # 準備
    fetch = _Recorder(OUTDATED_STATUS)
    start = _Recorder(_FakeProcess(None))
    # 実行
    code, output = _run_main(argv, fetch=fetch, start=start, log_file=tmp_path / "server.log")
    # 検証
    assert code == 0
    assert start.calls == []
    assert "v0.0.1" in output[stream]
    assert installed_version in output[stream]
    assert "server_stop" in output[stream]


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
    start = _Recorder(_FakeProcess(None))
    # 実行
    code, output = _run_main(
        argv,
        fetch=fetch,
        start=start,
        log_file=tmp_path / "server.log",
        environ={"MINDSTELLA_PORT": "abc"},
    )
    # 検証
    assert code == expected_code
    assert "abc" in output[stream]
    assert fetch.calls == []
    assert start.calls == []


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
    fetch = _Recorder(None)
    start = _Recorder(_FakeProcess(None))
    _patch_check_env(monkeypatch, _raising(check_env.DependencyMissingError(MISSING_MCP_REPORT)))
    # 実行
    code, output = _run_main(argv, fetch=fetch, start=start, log_file=tmp_path / "server.log")
    # 検証
    assert code == expected_code
    assert "mcp" in output[stream]
    assert MISSING_MCP_REPORT["install"] in output[stream]
    assert start.calls == []


@pytest.mark.parametrize(
    ("error", "expected_texts"),
    [
        pytest.param(ensure_server.PortInUseError(8784), ["MINDSTELLA_PORT"], id="port_in_use"),
        pytest.param(
            ensure_server.ServerExitedError(1, ["ImportError: x"]),
            ["ImportError: x", "{log_file}"],
            id="exited",
        ),
        pytest.param(ensure_server.ServerStartTimeoutError(), ["{log_file}"], id="timeout"),
    ],
)
def test_main_when_start_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_texts: list[str],
) -> None:
    """起動できなければ理由ごとに案内する（異常系）。"""
    # 準備
    log_file = tmp_path / "server.log"
    fetch = _Recorder(None)
    start = _Recorder(_FakeProcess(None))
    _patch_check_env(monkeypatch, lambda *args, **kwargs: GOOD_REPORT)
    monkeypatch.setattr(ensure_server, "wait_until_ready", _raising(error))
    # 実行
    code, output = _run_main(["--hook"], fetch=fetch, start=start, log_file=log_file)
    # 検証
    assert code == 0
    assert _missing_texts(output["stdout"], expected_texts, log_file=log_file) == []


def _missing_texts(text: str, expected: list[str], *, log_file: Path) -> list[str]:
    """expected の {log_file} を記録のファイルのパスに置き換え、text に含まれないものを返す。"""
    filled = [item.format(log_file=log_file) for item in expected]
    return [item for item in filled if item not in text]


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
        handler = type(
            "_Handler", (_StatusHandler,), {"status_code": status_code, "body": body}
        )
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
        pytest.param((404, b"{}"), None, id="not_found"),
        pytest.param((200, b'{"name": "other"}'), None, id="other_server"),
        pytest.param((200, b"x"), None, id="not_json"),
        pytest.param(None, None, id="not_listening"),
    ],
)
def test_fetch_status(
    status_server: Callable[[int, bytes], int],
    free_port: int,
    response: tuple[int, bytes] | None,
    expected: dict[str, Any] | None,
) -> None:
    """mindstella の状態だけを返す（正常系）。"""
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


def test_start_server(tmp_path: Path) -> None:
    """新しいセッションで、記録へつないで起動する（正常系）。"""
    # 準備
    popen = _Recorder(_FakeProcess(None))
    # 実行
    ensure_server.start_server(
        "/v/bin/python",
        environ={"MINDSTELLA_PORT": "9000"},
        log_file=tmp_path / "logs" / "server.log",
        popen=popen,
    )
    # 検証
    args, kwargs = popen.calls[0]
    assert args[0] == ["/v/bin/python", str(ensure_server.SERVER_FILE)]
    assert ensure_server.SERVER_FILE.name == "server.py"
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.STDOUT
    assert (tmp_path / "logs").is_dir()


def test_wait_until_ready(tmp_path: Path) -> None:
    """応答したら状態を返す（正常系）。"""
    # 準備
    fake = _FakeTime()
    fetch = _Recorder(None, None, RUNNING_STATUS)
    # 実行
    result = ensure_server.wait_until_ready(
        _FakeProcess(None),
        8784,
        log_file=tmp_path / "server.log",
        log_offset=0,
        fetch=fetch,
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


def _exit_error_attrs(error: Exception, names: list[str]) -> dict[str, Any]:
    """例外の names の属性を辞書にして返す。"""
    return {name: getattr(error, name) for name in names}


def _expected_exit_attrs(error_type: type[Exception], port: int) -> dict[str, Any]:
    """終わったときの例外の型ごとに、持つはずの属性を返す。"""
    # ポートに別のプロセスがつながる: そのポート
    if error_type is ensure_server.PortInUseError:
        return {"port": port}
    # ポートが空いている: 終了コードと、書き足された末尾の 20 行
    return {"returncode": 1, "log_tail": TAIL_LOG_LINES}


@pytest.mark.parametrize(
    ("port_fixture", "error_type"),
    [
        pytest.param("listening_port", ensure_server.PortInUseError, id="port_in_use"),
        pytest.param("free_port", ensure_server.ServerExitedError, id="port_free"),
    ],
)
def test_wait_until_ready_when_exited(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    port_fixture: str,
    error_type: type[Exception],
) -> None:
    """終わったらポートの使われ方で分ける（異常系）。"""
    # 準備
    port = request.getfixturevalue(port_fixture)
    log_file = tmp_path / "server.log"
    offset = _write_exit_log(log_file)
    fake = _FakeTime()
    expected = _expected_exit_attrs(error_type, port)
    # 実行・検証
    with pytest.raises(error_type) as raised:
        ensure_server.wait_until_ready(
            _FakeProcess(1),
            port,
            log_file=log_file,
            log_offset=offset,
            fetch=_Recorder(None),
            clock=fake.clock,
            sleep=fake.sleep,
        )
    assert _exit_error_attrs(raised.value, list(expected)) == expected


def test_wait_until_ready_when_timeout(tmp_path: Path) -> None:
    """上限までに応答しなければ ServerStartTimeoutError（異常系）。"""
    # 準備
    fake = _FakeTime()
    # 実行・検証
    with pytest.raises(ensure_server.ServerStartTimeoutError):
        ensure_server.wait_until_ready(
            _FakeProcess(None),
            8784,
            log_file=tmp_path / "server.log",
            log_offset=0,
            fetch=_Recorder(None),
            clock=fake.clock,
            sleep=fake.sleep,
        )
    assert sum(fake.sleeps) <= ensure_server.START_TIMEOUT_SEC
