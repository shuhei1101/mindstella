"""プレビューの配信（GET /w/{workspace}/）の結合テスト。"""

from __future__ import annotations

import re
import textwrap
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote, urlsplit

from session_fixtures import SessionWorld
from workspace_fixtures import SERVER_SCRIPT

from .fixture_types import MakeItem, MakeWorkspace, StartServer
from .http_helpers import http_request

# 許可するホスト名を渡す環境変数と、許可するホスト名
ALLOWED_HOSTS_ENV = "MINDSTELLA_ALLOWED_HOSTS"
ALLOWED_HOST = "preview.example.test"

# 画面のパス（ワークスペースの経路より後ろ）
PAGE_PATH = "/"

# どのワークスペースにも当たらない ID
UNKNOWN_WORKSPACE_ID = "mindstella-unknown-000000"

# 画面の本文に出てはいけない `config.yaml` の中身の目印（設定の題名）
SETTINGS_MARK = "要件出しのスキル mindmap を設計する"

# 画面の本文が読む JavaScript と CSS の相対の参照（`./assets/`）
SCRIPT_SRC_PATTERN = re.compile(r'<script type="module"[^>]*src="\./(assets/[^"]+\.js)"')
STYLESHEET_HREF_PATTERN = re.compile(r'<link rel="stylesheet"[^>]*href="\./(assets/[^"]+\.css)"')

# 配信が読む画面のビルドの出力のフォルダを差し替えて常駐サーバーを起動するスクリプト
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
    """画面の本文から、パターンに当たる静的なファイルの相対の参照をワークスペースの経路の下のパスにして返す。"""
    match = pattern.search(html)
    assert match is not None, html[:500]
    return f"/{match.group(1)}"


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """`/w/{workspace}/` で React の画面の `index.html` を返す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行
    result = http_request(url, PAGE_PATH, headers={"Host": f"127.0.0.1:{_port(url)}"})
    # 検証
    assert result.status == HTTPStatus.OK
    assert result.headers["content-type"] == "text/html; charset=utf-8"
    assert result.headers["cache-control"] == "no-store"
    assert 'id="root"' in result.text
    assert SCRIPT_SRC_PATTERN.search(result.text) is not None


def test_normal_when_asset(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """ビルドの出力の静的なファイルを拡張子に合う Content-Type で返す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    html = http_request(url, PAGE_PATH).text
    # 実行
    script = http_request(url, _asset_path(SCRIPT_SRC_PATTERN, html))
    stylesheet = http_request(url, _asset_path(STYLESHEET_HREF_PATTERN, html))
    # 検証
    assert script.status == HTTPStatus.OK
    assert script.headers["content-type"] == "text/javascript; charset=utf-8"
    assert stylesheet.status == HTTPStatus.OK
    assert stylesheet.headers["content-type"] == "text/css; charset=utf-8"


def test_normal_when_old_path(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """前の画面の URL は、search を残して `/w/{workspace}/` へ再送信する（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    base = urlsplit(url).path.rstrip("/")
    # 実行（再送信は辿らずに、1 回ずつ GET する）
    bare = http_request(url, base)
    old_page = http_request(url, "/mindstella.html")
    old_spa = http_request(url, "/spa/?tab=decisions&id=D-1")
    # 検証
    assert (bare.status, bare.headers["location"]) == (HTTPStatus.FOUND, f"{base}/")
    assert (old_page.status, old_page.headers["location"]) == (HTTPStatus.FOUND, f"{base}/")
    assert (old_spa.status, old_spa.headers["location"]) == (
        HTTPStatus.FOUND,
        f"{base}/?tab=decisions&id=D-1",
    )


def test_error_when_host_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """Host が端末の中の名前でなければ画面を返さない（異常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    script_path = _asset_path(SCRIPT_SRC_PATTERN, http_request(url, PAGE_PATH).text)
    host = {"Host": f"attacker.example:{_port(url)}"}
    # 実行
    page = http_request(url, PAGE_PATH, headers=host)
    script = http_request(url, script_path, headers=host)
    # 検証
    assert page.status == HTTPStatus.FORBIDDEN
    assert "<html" not in page.text.lower()
    assert script.status == HTTPStatus.FORBIDDEN
    assert "import" not in script.text


def test_error_when_path_unknown(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """決めたパス以外は 404 を返す（異常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行（`..` を正規化せずに送る）
    unknown = http_request(url, "/config.yaml")
    outside = http_request(url, "/assets/../config.yaml")
    # 検証
    for result in (unknown, outside):
        assert result.status == HTTPStatus.NOT_FOUND
        assert SETTINGS_MARK not in result.text


def test_normal_when_host_allowed(
    make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """許可したホスト名の Host は、入口のポートを問わず画面を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    server = start_server(extra_env={ALLOWED_HOSTS_ENV: ALLOWED_HOST})
    url = server.call("preview_url", workspace=str(root)).data["url"]
    # 実行
    plain = http_request(url, PAGE_PATH, headers={"Host": ALLOWED_HOST})
    with_port = http_request(url, PAGE_PATH, headers={"Host": "PREVIEW.example.test:8443"})
    other = http_request(url, PAGE_PATH, headers={"Host": "other.example.test"})
    # 検証
    for result in (plain, with_port):
        assert result.status == HTTPStatus.OK
        assert result.headers["content-type"] == "text/html; charset=utf-8"
    assert other.status == HTTPStatus.FORBIDDEN
    assert "<html" not in other.text.lower()


def test_error_when_workspace_not_served(session_world: SessionWorld) -> None:
    """配っていないワークスペースの経路は 404 を返す（異常系）。"""
    # 準備（A を作成し、B を作成してから削除する。B のフォルダは残す）
    world = session_world
    world.start()
    id_a = str(world.create_workspace("話し合いA")["id"])
    id_b = str(world.create_workspace("話し合いB")["id"])
    # 経路の ID はパーセントエンコードして送る
    path_a = f"/w/{quote(id_a)}"
    path_b = f"/w/{quote(id_b)}"
    assert world.api("POST", f"/workspaces/{id_b}/close")[0] == 200
    assert world.api("DELETE", f"/workspaces/{id_b}")[0] == 200
    origin = f"http://127.0.0.1:{world.port}"
    # 実行
    results = [
        http_request(origin, f"/w/{UNKNOWN_WORKSPACE_ID}{PAGE_PATH}"),
        http_request(origin, f"{path_b}{PAGE_PATH}"),
        http_request(origin, f"{path_b}/api/records"),
    ]
    # 検証
    for result in results:
        assert result.status == HTTPStatus.NOT_FOUND
        assert result.headers["content-type"].startswith("application/problem+json")
        assert '"decisions"' not in result.text
    assert http_request(origin, f"{path_a}{PAGE_PATH}").status == HTTPStatus.OK


def test_error_when_index_missing(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
) -> None:
    """ビルドの出力のフォルダに `index.html` が無いとき、画面を返さない（異常系）。"""
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
    result = http_request(url, PAGE_PATH)
    # 検証
    assert result.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert result.headers["content-type"].startswith("application/problem+json")
