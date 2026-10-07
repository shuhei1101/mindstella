"""preview_url（プレビューの URL）の結合テスト。"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any

from workspace_fixtures import SERVER_SCRIPT

from .fixture_types import CallTool, MakeItem, MakeWorkspace, SnapshotTree, StartServer
from .http_helpers import http_request
from .readme_helpers import section_of

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

# 利用者の README の更新日時として置く、十分に古い日時（ナノ秒）
OLD_MTIME_NS = 1_000_000_000 * 1_000_000_000

# 配信の URL の頭と、画面のパス
URL_PREFIX = "http://127.0.0.1:"
PAGE_PATH = "/mindstella.html"


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
    assert result.data["url"].endswith(PAGE_PATH)
    assert result.data["started"] is True
    assert http_request(result.data["url"], PAGE_PATH).status == 200
    assert not (root / "preview.html").exists()
    # 直下の README のプレビューの節に、返した URL が書かれる
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    assert result.data["url"] in section_of(readme_text, "## プレビュー")


def test_normal_when_user_readme_exists(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """自動で書いた印の無い README.md は書き換えずに配信を立てる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    readme = root / "README.md"
    readme.write_text("# 家計簿アプリの話し合い\n", encoding="utf-8")
    os.utime(readme, ns=(OLD_MTIME_NS, OLD_MTIME_NS))
    content_before = readme.read_bytes()
    mtime_before = readme.stat().st_mtime_ns
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["started"] is True
    assert readme.read_bytes() == content_before
    assert readme.stat().st_mtime_ns == mtime_before


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
    """config.yaml が無いフォルダを指すと、配信を立てずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_config_invalid(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """config.yaml がスキーマに合わないと、違う箇所を返して配信を立てない（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": {"network_look": "rainbow"}})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert any(
        line.startswith("config.yaml: display.network_look: ") and "glow" in line
        for line in result.text.splitlines()
    )
    assert snapshot_tree(root) == before
    # 配信が立っていないので、もう一度呼んでも同じエラーになる
    again = call_tool("preview_url", workspace=str(root))
    assert again.is_error is True
    assert "config.yaml: display.network_look: " in again.text


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
