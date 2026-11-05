"""React のプレビュー（SPA）の配信（GET /spa/{path}）の結合テスト。"""

from __future__ import annotations

import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from workspace_fixtures import SERVER_SCRIPT

from .fixture_types import MakeItem, MakeWorkspace, StartServer
from .http_helpers import http_request

# SPA の入口のパスと、今の画面のパス
SPA_ROOT_PATH = "/spa/"
PAGE_PATH = "/mindstella.html"

# 本文に出てはいけない `config.yaml` の中身の目印（設定の題名）
SETTINGS_MARK = "要件出しのスキル mindmap を設計する"

# SPA の本文が読む JavaScript と CSS のパス
SCRIPT_SRC_PATTERN = re.compile(r'<script type="module"[^>]*src="(/spa/assets/[^"]+\.js)"')
STYLESHEET_HREF_PATTERN = re.compile(r'<link rel="stylesheet"[^>]*href="(/spa/assets/[^"]+\.css)"')

# 配信が読む SPA の出力のフォルダを差し替えて常駐サーバーを起動するスクリプト
MISSING_SPA_SERVER_SCRIPT = textwrap.dedent(
    """\
    import sys

    sys.path.insert(0, {scripts_dir!r})
    import serve

    serve.SPA_DIR = {spa_dir!r}
    import server

    sys.exit(server.main())
    """
)


def _port(url: str) -> int:
    """配信の URL のポートを返す。"""
    port = urlsplit(url).port
    assert port is not None
    return port


def _asset_path(pattern: re.Pattern[str], html: str) -> str:
    """SPA の本文から、パターンに当たる静的なファイルのパスを返す。"""
    match = pattern.search(html)
    assert match is not None, html
    return match.group(1)


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """`/spa/` で SPA の `index.html` を返す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行
    result = http_request(url, SPA_ROOT_PATH, headers={"Host": f"127.0.0.1:{_port(url)}"})
    # 検証
    assert result.status == 200
    assert result.headers["content-type"] == "text/html; charset=utf-8"
    assert result.headers["cache-control"] == "no-store"
    assert 'id="root"' in result.text
    assert SCRIPT_SRC_PATTERN.search(result.text) is not None


def test_normal_when_asset(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """出力の静的なファイルを拡張子に合う Content-Type で返す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    html = http_request(url, SPA_ROOT_PATH).text
    # 実行
    script = http_request(url, _asset_path(SCRIPT_SRC_PATTERN, html))
    stylesheet = http_request(url, _asset_path(STYLESHEET_HREF_PATTERN, html))
    # 検証
    assert script.status == 200
    assert script.headers["content-type"] == "text/javascript; charset=utf-8"
    assert stylesheet.status == 200
    assert stylesheet.headers["content-type"] == "text/css; charset=utf-8"


def test_normal_when_client_route(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """出力に無いパスと出力の外を指すパスは、SPA の中のルートとして `index.html` を返す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    index = http_request(url, SPA_ROOT_PATH)
    # 実行（`..` は正規化せずにそのまま送る）
    route = http_request(url, "/spa/decisions?view=table")
    outside = http_request(url, "/spa/../config.yaml")
    # 検証
    assert route.status == 200
    assert route.text == index.text
    assert outside.status == 200
    assert outside.text == index.text
    assert SETTINGS_MARK not in outside.text


def test_normal_when_no_trailing_slash(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """`/spa` は `/spa/` へ送り直す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行（送り直しは辿らずに、1 回だけ GET する）
    result = http_request(url, "/spa")
    # 検証
    assert result.status == 302
    assert result.headers["location"] == SPA_ROOT_PATH


def test_error_when_host_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """Host が端末の中の名前でなければ SPA を返さない（異常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    script_path = _asset_path(SCRIPT_SRC_PATTERN, http_request(url, SPA_ROOT_PATH).text)
    host = {"Host": f"attacker.example:{_port(url)}"}
    # 実行
    index = http_request(url, SPA_ROOT_PATH, headers=host)
    script = http_request(url, script_path, headers=host)
    # 検証
    assert index.status == 403
    assert "<html" not in index.text.lower()
    assert script.status == 403
    assert "import" not in script.text


def test_error_when_index_missing(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
) -> None:
    """出力のフォルダに `index.html` が無いとき、SPA を返さず今の画面はそのまま返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    empty_spa_dir = tmp_path / "spa-empty"
    empty_spa_dir.mkdir()
    wrapper = tmp_path / "missing_spa_server.py"
    wrapper.write_text(
        MISSING_SPA_SERVER_SCRIPT.format(
            scripts_dir=str(SERVER_SCRIPT.parent), spa_dir=str(empty_spa_dir)
        ),
        encoding="utf-8",
    )
    server = start_server(script=wrapper)
    url = server.call("preview_url", workspace=str(root)).data["url"]
    # 実行
    spa = http_request(url, SPA_ROOT_PATH)
    page = http_request(url, PAGE_PATH)
    # 検証
    assert spa.status == 500
    assert spa.headers["content-type"].startswith("application/problem+json")
    assert page.status == 200
