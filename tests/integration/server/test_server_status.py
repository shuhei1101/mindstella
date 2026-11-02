"""常駐サーバーの状態（server_status・GET /_admin/status）の結合テスト。"""

from __future__ import annotations

from urllib.parse import urlsplit

from workspace_fixtures import plugin_version, read_server_status

from .fixture_types import MakeWorkspace, StartServer

# サーバーが名乗る名前
SERVER_NAME = "mindstella"


def _port(url: str) -> int | None:
    """URL のポートを返す。"""
    return urlsplit(url).port


def test_normal(make_workspace: MakeWorkspace, start_server: StartServer) -> None:
    """待ち受けのポート・バージョン・配信しているワークスペースごとのポートを返す（正常系）。"""
    # 準備
    first = make_workspace(name="a")
    second = make_workspace(name="b")
    server = start_server()
    first_url = server.call("preview_url", workspace=str(first)).data["url"]
    second_url = server.call("preview_url", workspace=str(second)).data["url"]
    # 実行
    result = server.call("server_status")
    # 検証
    assert result.is_error is False, result.text
    status = result.data
    assert status is not None
    assert (status["name"], status["version"], status["port"], status["pid"]) == (
        SERVER_NAME,
        plugin_version(),
        server.port,
        server.process.pid,
    )
    assert status["previews"] == [
        {"workspace": str(first), "port": _port(first_url)},
        {"workspace": str(second), "port": _port(second_url)},
    ]
    assert read_server_status(server.port) == status


def test_normal_when_no_previews(start_server: StartServer) -> None:
    """配信を立てていなければ、`previews` を空で返す（正常系）。"""
    # 準備
    server = start_server()
    # 実行
    result = server.call("server_status")
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["previews"] == []
