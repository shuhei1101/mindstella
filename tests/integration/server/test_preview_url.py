"""preview_url（プレビューの URL）の結合テスト。"""

from __future__ import annotations

import textwrap
from pathlib import Path

from workspace_fixtures import SERVER_SCRIPT

from .fixture_types import CallTool, MakeItem, MakeWorkspace, StartServer
from .http_helpers import http_request

# 待ち受けを立てる処理を、OSError を送る偽に差し替えてからサーバーを動かすスクリプトの中身
FAILING_LISTEN_SCRIPT = textwrap.dedent(
    """\
    import sys

    sys.path.insert(0, {scripts_dir!r})
    import serve


    class FailingHttpServer:
        def __init__(self, *args, **kwargs):
            raise OSError("待ち受けを立てられません（テスト）")


    serve.ThreadingHTTPServer = FailingHttpServer
    import server

    sys.exit(server.main())
    """
)

# 配信の URL の頭
URL_PREFIX = "http://127.0.0.1:"


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """初めて呼ぶと配信を立て、127.0.0.1 の URL を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["url"].startswith(URL_PREFIX)
    assert result.data["started"] is True
    assert http_request(result.data["url"]).status == 200
    assert not (root / "preview.html").exists()


def test_normal_when_called_again(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """同じワークスペースで呼び直すと、同じ URL を返して配信を増やさない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    first = call_tool("preview_url", workspace=str(root))
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert first.data is not None
    assert result.data is not None
    assert result.data["url"] == first.data["url"]
    assert result.data["started"] is False


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """mindmap.yaml が無いフォルダを指すと、配信を立てずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_serve_fails(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
) -> None:
    """待ち受けを立てられないと、エラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    wrapper = tmp_path / "failing_listen_server.py"
    wrapper.write_text(
        FAILING_LISTEN_SCRIPT.format(scripts_dir=str(SERVER_SCRIPT.parent)), encoding="utf-8"
    )
    failing_server = start_server(script=wrapper)
    # 実行
    result = failing_server.call("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
