"""プレビューの配信（GET /）の結合テスト。"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from .fixture_types import MakeItem, MakeWorkspace, McpServer, StartMdmarkRefServer, StartServer
from .http_helpers import http_request
from .mdmark_ref_helpers import FAKE_HEAD_SHA, FakeMdmarkSource, fake_github, fake_jsdelivr
from .transcriber_helpers import bind_closed_port

# 許可するホスト名を渡す環境変数と、許可するホスト名
ALLOWED_HOSTS_ENV = "MINDSTELLA_ALLOWED_HOSTS"
ALLOWED_HOST = "preview.example.test"

# 画面のパス
PAGE_PATH = "/mindstella.html"

# 画面が読み込む mdmark の配布物の URL の頭（`{ref}/dist/{ファイル}` が続く）
MDMARK_DIST_BASE = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@"

# 画面の mdmark の CSS の link 要素の href と、読み込みの設定の要素の中身を取る正規表現
MDMARK_CSS_HREF = re.compile(r'<link rel="stylesheet" href="([^"]+/dist/index\.css)"')
MDMARK_CONFIG = re.compile(r'<script type="application/json" id="mindmap-mdmark-config">(.*?)</script>', re.S)

# 雛形の mdmark のタグの例
MDMARK_TAG = "v0.13.0"

# 画面の本文に出てはいけない `config.yaml` の中身の目印（設定の題名）
SETTINGS_MARK = "要件出しのスキル mindmap を設計する"


def _port(url: str) -> int:
    """配信の URL のポートを返す。"""
    port = urlsplit(url).port
    assert port is not None
    return port


def _mdmark_urls(html: str) -> tuple[str, str]:
    """画面の mdmark の CSS の link 要素の href と、読み込みの設定の JavaScript の URL を返す。"""
    css = MDMARK_CSS_HREF.search(html)
    config = MDMARK_CONFIG.search(html)
    assert css is not None and config is not None, html[:500]
    return css.group(1), json.loads(config.group(1))["js"]


def _open_page(server: McpServer, root: Path) -> str:
    """server で root の配信を立て、画面を 1 回 GET して本文を返す。"""
    served = server.call("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    url = str(served.data["url"])
    result = http_request(url, PAGE_PATH, headers={"Host": f"127.0.0.1:{_port(url)}"})
    assert result.status == HTTPStatus.OK
    return result.text


@pytest.fixture
def start_fake_source() -> Iterator[Callable[[FakeMdmarkSource], FakeMdmarkSource]]:
    """偽の GitHub・jsDelivr を立てる関数を返し、テストの後で全て止める。"""
    started: list[FakeMdmarkSource] = []

    def _start(source: FakeMdmarkSource) -> FakeMdmarkSource:
        source.start()
        started.append(source)
        return source

    yield _start
    for source in started:
        source.stop()


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """雛形に CSS と JavaScript を差し込んだ画面を返す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行
    result = http_request(url, PAGE_PATH, headers={"Host": f"127.0.0.1:{_port(url)}"})
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


def test_normal_when_root(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """`/` は画面のパスへ送り直す（正常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行（送り直しは辿らずに、1 回だけ GET する）
    result = http_request(url, "/")
    # 検証
    assert result.status == 302
    assert result.headers["location"] == PAGE_PATH
    assert result.text == ""


def test_error_when_host_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """Host が端末の中の名前でなければ、画面を返さない（異常系）。"""
    # 準備
    url = serve_preview(make_workspace(make_item("D-1")))
    # 実行
    result = http_request(url, PAGE_PATH, headers={"Host": f"attacker.example:{_port(url)}"})
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
    result = http_request(url, "/config.yaml")
    # 検証
    assert result.status == 404
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
        assert result.status == 200
        assert result.headers["content-type"] == "text/html; charset=utf-8"
    assert other.status == 403
    assert "<html" not in other.text.lower()


def test_normal_when_latest_resolved(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    start_mdmark_ref_server: StartMdmarkRefServer,
    start_fake_source: Callable[[FakeMdmarkSource], FakeMdmarkSource],
) -> None:
    """latest を GitHub に問い合わせた develop の先頭の commit にし、保持している間は問い合わせ直さない（正常系）。"""
    # 準備
    github = start_fake_source(fake_github())
    jsdelivr = start_fake_source(fake_jsdelivr())
    server = start_mdmark_ref_server(github.base_url, jsdelivr.base_url)
    root = make_workspace(settings={**valid_settings, "mdmark": {"version": "latest"}})
    # 実行
    first = _open_page(server, root)
    second = _open_page(server, root)
    # 検証
    expected = (f"{MDMARK_DIST_BASE}{FAKE_HEAD_SHA}/dist/index.css", f"{MDMARK_DIST_BASE}{FAKE_HEAD_SHA}/dist/index.js")
    assert _mdmark_urls(first) == expected
    assert _mdmark_urls(second) == expected
    assert len(github.paths) == 1


def test_normal_when_github_unreachable(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    start_mdmark_ref_server: StartMdmarkRefServer,
    start_fake_source: Callable[[FakeMdmarkSource], FakeMdmarkSource],
) -> None:
    """GitHub に届かないときは develop の URL で mdmark を読み込む画面を返す（正常系）。"""
    # 準備
    held = bind_closed_port()
    jsdelivr = start_fake_source(fake_jsdelivr())
    server = start_mdmark_ref_server(f"http://127.0.0.1:{held.getsockname()[1]}", jsdelivr.base_url)
    root = make_workspace(settings={**valid_settings, "mdmark": {"version": "latest"}})
    # 実行
    try:
        html = _open_page(server, root)
    finally:
        held.close()
    # 検証
    css_url, _ = _mdmark_urls(html)
    assert css_url == f"{MDMARK_DIST_BASE}develop/dist/index.css"
    warnings = [line for line in server.stderr_text().splitlines() if "mdmark の ref を問い合わせられない" in line]
    assert len(warnings) == 1, server.stderr_text()
    assert jsdelivr.paths == []


def test_normal_when_version_tag(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    start_mdmark_ref_server: StartMdmarkRefServer,
    start_fake_source: Callable[[FakeMdmarkSource], FakeMdmarkSource],
) -> None:
    """設定がタグのときは GitHub に問い合わせずにタグの URL で読み込む（正常系）。"""
    # 準備
    github = start_fake_source(fake_github())
    jsdelivr = start_fake_source(fake_jsdelivr())
    server = start_mdmark_ref_server(github.base_url, jsdelivr.base_url)
    root = make_workspace(settings={**valid_settings, "mdmark": {"version": MDMARK_TAG}})
    # 実行
    html = _open_page(server, root)
    # 検証
    css_url, _ = _mdmark_urls(html)
    assert css_url == f"{MDMARK_DIST_BASE}{MDMARK_TAG}/dist/index.css"
    assert github.paths == []
    assert jsdelivr.paths == []


def test_normal_when_dist_not_served(
    make_workspace: MakeWorkspace,
    start_mdmark_ref_server: StartMdmarkRefServer,
    start_fake_source: Callable[[FakeMdmarkSource], FakeMdmarkSource],
) -> None:
    """問い合わせた commit を jsDelivr が配らないときは develop で読み込む（正常系）。"""
    # 準備
    github = start_fake_source(fake_github())
    jsdelivr = start_fake_source(fake_jsdelivr(HTTPStatus.FORBIDDEN))
    server = start_mdmark_ref_server(github.base_url, jsdelivr.base_url)
    root = make_workspace()
    # 実行
    html = _open_page(server, root)
    # 検証
    css_url, js_url = _mdmark_urls(html)
    assert css_url == f"{MDMARK_DIST_BASE}develop/dist/index.css"
    assert js_url == f"{MDMARK_DIST_BASE}develop/dist/index.js"
    assert jsdelivr.paths == [f"/gh/shuhei1101/mdmark@{FAKE_HEAD_SHA}/dist/index.js"]
    warnings = [line for line in server.stderr_text().splitlines() if "jsDelivr が配らない" in line]
    assert len(warnings) == 1, server.stderr_text()
