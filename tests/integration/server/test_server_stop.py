"""常駐サーバーの停止（server_stop）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from external_access_helpers import read_settled_hook_lines, recording_hook
from workspace_fixtures import is_listening

from .fixture_types import MakeWorkspace, StartServer

# 終了時のフックを渡す環境変数
STOP_HOOK_ENV = "MINDSTELLA_PREVIEW_STOP_HOOK"


def test_normal(tmp_path: Path, make_workspace: MakeWorkspace, start_server: StartServer) -> None:
    """止めた配信を返してから、配信ごとに終了時のフックを呼び、全ての配信を止めて常駐サーバーを終える（正常系）。"""
    # 準備
    first = make_workspace(name="a")
    second = make_workspace(name="b")
    record = tmp_path / "stop-hook.txt"
    server = start_server(extra_env={STOP_HOOK_ENV: recording_hook(record)})
    first_url = server.call("preview_url", workspace=str(first)).data["url"]
    second_url = server.call("preview_url", workspace=str(second)).data["url"]
    # 実行
    result = server.call("server_stop")
    exit_code = server.wait_exit()
    # 検証
    assert result.is_error is False, result.text
    assert result.data == {
        "stopping": True,
        "previews": [
            {"workspace": str(first), "url": first_url},
            {"workspace": str(second), "url": second_url},
        ],
    }
    assert exit_code == 0
    assert is_listening(server.port) is False
    assert sorted(read_settled_hook_lines(record, count=2)) == sorted(
        [
            f"{server.port} a {urlsplit(first_url).path}",
            f"{server.port} b {urlsplit(second_url).path}",
        ]
    )
