"""launch.py（起動の手助け：プラグインのフォルダ・MindStella の API の呼び出し）の単体テスト。"""

from __future__ import annotations

import io
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

import launch

# claude plugin list --json の、mindstella 以外のプラグインの要素
OTHER_PLUGIN: dict[str, Any] = {"id": "other@market", "installPath": "/o/1.0.0"}

# claude plugin list --json の、mindstella の要素
MINDSTELLA_PLUGIN: dict[str, Any] = {"id": "mindstella@mindstella", "installPath": "/p/0.0.2"}

# 画面の URL
PREVIEW_URL = "http://127.0.0.1:9100/mindstella.html"

# ワークスペースの作成の応答
CREATED: dict[str, Any] = {
    "id": "mindstella-家計簿-3f2a9c",
    "url": PREVIEW_URL,
    "result": "created",
}


class _Requests:
    """MindStella の API の呼び出しを控え、決めた応答を順に返す偽の request。"""

    def __init__(self, *responses: tuple[int, dict[str, Any]]) -> None:
        """返す応答を呼ばれる順に受け取る。"""
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self._responses = list(responses)

    def __call__(
        self,
        port: int,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        timeout: float = 0,
    ) -> tuple[int, dict[str, Any]]:
        """呼び出しを控え、次の応答を返す。"""
        self.calls.append((method, path, body))
        return self._responses[len(self.calls) - 1]


def _run_start(
    argv: list[str], request: _Requests, environ: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """run_start を呼び、終了コードと標準出力・標準エラーを返す。"""
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = launch.run_start(
        argv, environ=environ or {}, stdout=stdout, stderr=stderr, request=request
    )
    return code, stdout.getvalue(), stderr.getvalue()


def test_find_plugin_dir() -> None:
    """mindstella の installPath を返す（正常系）。"""
    # 実行
    result = launch.find_plugin_dir([OTHER_PLUGIN, MINDSTELLA_PLUGIN])
    # 検証
    assert result == Path("/p/0.0.2")


def test_find_plugin_dir_when_missing() -> None:
    """mindstella が無ければ PluginNotInstalledError（異常系）。"""
    # 実行・検証
    with pytest.raises(launch.PluginNotInstalledError):
        launch.find_plugin_dir([])


def test_run_launch(capsys: pytest.CaptureFixture[str]) -> None:
    """--find-plugin でプラグインのフォルダを 1 行出す（正常系）。"""
    # 準備
    stdin = io.StringIO(json.dumps([OTHER_PLUGIN, MINDSTELLA_PLUGIN]))
    # 実行
    exit_code = launch.run_launch(["--find-plugin"], stdin=stdin)
    # 検証
    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == ["/p/0.0.2"]


def test_run_launch_when_plugin_missing(capsys: pytest.CaptureFixture[str]) -> None:
    """プラグインが無ければ案内して 1（正常系）。"""
    # 実行
    exit_code = launch.run_launch(["--find-plugin"], stdin=io.StringIO("[]"))
    # 検証
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "mindstella@mindstella" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    "text", [pytest.param("{", id="not_json"), pytest.param("{}", id="not_array")]
)
def test_run_launch_when_listing_invalid(capsys: pytest.CaptureFixture[str], text: str) -> None:
    """一覧を読めなければ 1（正常系）。"""
    # 実行
    exit_code = launch.run_launch(["--find-plugin"], stdin=io.StringIO(text))
    # 検証
    assert exit_code == 1
    assert capsys.readouterr().err.startswith("[mindstella] エラー: ")


class _ApiHandler(BaseHTTPRequestHandler):
    """パスで 201 か 409 の problem+json を返し、受けた Host を控える偽の常駐サーバー。"""

    # 受けた Host
    hosts: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        """/conflict なら 409、ほかは 201 を返す。"""
        self.hosts.append(self.headers["Host"])
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path == "/conflict":
            status, body, kind = (
                409,
                {"status": 409, "stage": "exists", "pane": "w:0.0"},
                "application/problem+json",
            )
        else:
            status, body, kind = 201, {"id": "w"}, "application/json"
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        """要求の記録を出さない。"""


@pytest.fixture
def api_port() -> Iterator[int]:
    """偽の常駐サーバーを空きポートで立て、そのポートを返す。"""
    _ApiHandler.hosts = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ApiHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield int(server.server_address[1])
    server.shutdown()
    server.server_close()


def test_api_request(api_port: int) -> None:
    """ステータスと JSON の本文を返し、Host を 127.0.0.1:{port} で送る（正常系）。"""
    # 実行
    created = launch.api_request(api_port, "POST", "/workspaces", {"folder": "/w"}, 5.0)
    conflict = launch.api_request(api_port, "POST", "/conflict", {}, 5.0)
    # 検証
    assert created == (201, {"id": "w"})
    assert conflict[0] == 409
    assert conflict[1]["stage"] == "exists"
    assert _ApiHandler.hosts == [f"127.0.0.1:{api_port}"] * 2


def test_run_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ワークスペースと MindStella のセッションを作り、URL とペインを出す（正常系）。"""
    # 準備
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "a"}}}), encoding="utf-8"
    )
    request = _Requests(
        (201, CREATED), (201, {"session": "S-1", "pane": "w:0.0", "url": PREVIEW_URL})
    )
    argv = ["/w/家計簿", "--flow", "aituber#flow-1", "--mcp-config", "m.json", "--plugin-dir", "p"]
    # 実行
    code, stdout, _stderr = _run_start(argv, request, {"CLAUDE_CONFIG_DIR": "/c"})
    # 検証
    assert code == 0
    assert request.calls[0] == (
        "POST",
        "/workspaces",
        {
            "folder": "/w/家計簿",
            "flow": {"source": "aituber", "doc": "flow-1"},
            "mcp_config": {"mcpServers": {"a": {"command": "a"}}},
            "plugin_dirs": [str(tmp_path / "p")],
        },
    )
    assert request.calls[1] == (
        "POST",
        f"/workspaces/{CREATED['id']}/sessions",
        {"claude_config_dir": "/c"},
    )
    assert stdout.splitlines() == [PREVIEW_URL, "w:0.0"]


def test_run_start_exists() -> None:
    """MindStella のセッションが既にあれば、そのペインを出す（正常系）。"""
    # 準備
    request = _Requests(
        (200, CREATED), (409, {"status": 409, "stage": "exists", "session": "S-1", "pane": "w:0.0"})
    )
    # 実行
    code, stdout, stderr = _run_start(["/w/家計簿"], request)
    # 検証
    assert code == 0
    assert stdout.splitlines() == [PREVIEW_URL, "w:0.0"]
    assert "既に" in stderr


@pytest.mark.parametrize(
    ("responses", "texts"),
    [
        pytest.param(
            [(403, {"status": 403, "stage": "folder", "detail": "許可していないフォルダです"})],
            ["許可していないフォルダです"],
            id="create",
        ),
        pytest.param(
            [
                (201, CREATED),
                (503, {"status": 503, "stage": "account", "detail": "借りられません"}),
            ],
            ["借りられません", PREVIEW_URL],
            id="session",
        ),
    ],
)
def test_run_start_error(responses: list[tuple[int, dict[str, Any]]], texts: list[str]) -> None:
    """作成に失敗したら 1 を返し、理由を出す（異常系）。"""
    # 実行
    code, _stdout, stderr = _run_start(["/w/家計簿"], _Requests(*responses))
    # 検証
    assert code == 1
    assert all(text in stderr for text in texts)


def test_run_server_status() -> None:
    """常駐サーバーの状態を出し、つながらなければ 1（正常系）。"""
    # 準備
    status = {
        "name": "mindstella",
        "version": "v0.12.0",
        "port": 8784,
        "plugin_root": "/p/c938",
        "previews": [],
    }

    def unreachable(*_args: Any, **_kwargs: Any) -> tuple[int, dict[str, Any]]:
        """つながらない。"""
        raise OSError("refused")

    # 実行
    stdout = io.StringIO()
    code = launch.run_server_status({}, stdout, request=lambda *_args, **_kwargs: (200, status))
    failed = launch.run_server_status({}, io.StringIO(), request=unreachable)
    # 検証
    assert code == 0
    assert "v0.12.0" in stdout.getvalue()
    assert "/p/c938" in stdout.getvalue()
    assert failed == 1
