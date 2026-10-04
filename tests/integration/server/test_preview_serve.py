"""プレビューの配信（GET /）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from .fixture_types import MakeItem, MakeWorkspace
from .http_helpers import http_request

# 画面の本文に出てはいけない `mindmap.yaml` の中身の目印（設定の題名）
SETTINGS_MARK = "要件出しのスキル mindmap を設計する"


def _port(url: str) -> int:
    """配信の URL のポートを返す。"""
    port = urlsplit(url).port
    assert port is not None
    return port


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """雛形に CSS と JavaScript を差し込んだ画面を返す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行
    result = http_request(url, "/", headers={"Host": f"127.0.0.1:{_port(url)}"})
    # 検証
    assert result.status == 200
    assert result.headers["content-type"] == "text/html; charset=utf-8"
    assert result.headers["cache-control"] == "no-store"
    # 画面の CSS と JavaScript が差し込まれ（空の要素のまま残っていない）、記録の埋め込み先は空のまま
    assert '<style id="mindmap-style">' in result.text
    assert '<style id="mindmap-style"></style>' not in result.text
    assert '<script id="mindmap-app">' in result.text
    assert '<script id="mindmap-app"></script>' not in result.text
    assert '<script type="application/json" id="mindmap-data"></script>' in result.text


def test_error_when_host_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """Host が端末の中の名前でなければ、画面を返さない（異常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行
    result = http_request(url, "/", headers={"Host": f"attacker.example:{_port(url)}"})
    # 検証
    assert result.status == 403
    assert "<html" not in result.text.lower()


def test_error_when_path_unknown(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """決めたパス以外は 404 を返す（異常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行
    result = http_request(url, "/mindmap.yaml")
    # 検証
    assert result.status == 404
    assert SETTINGS_MARK not in result.text
