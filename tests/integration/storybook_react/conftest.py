"""React の部品のストーリー（Storybook）の結合テストの共通 fixture。

`npm run build-storybook-react` の出力を一時の HTTP サーバーで配り、`iframe.html?id={ストーリー}` を開く。
"""

from __future__ import annotations

import functools
import http.server
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page

from .storybook_react_fixture_types import OpenStory

# このファイルから見たリポジトリの直下（tests/integration/storybook_react の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# `npm run build-storybook-react` の出力先
STORYBOOK_REACT_STATIC_DIR = REPO_ROOT / "storybook-react-static"

# ストーリーが描き終わるまで待つ上限ミリ秒
STORY_TIMEOUT_MS = 15_000


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """アクセスのログを標準エラーに出さない静的ファイルの配信。"""

    def log_message(self, format: str, *args: object) -> None:
        """ログを出さない。"""


@pytest.fixture(scope="session")
def storybook_react_url() -> Iterator[str]:
    """`storybook-react-static` を空きポートの一時の HTTP サーバーで配り、その URL を返す。終わったら止める。"""
    assert (STORYBOOK_REACT_STATIC_DIR / "iframe.html").is_file(), (
        "storybook-react-static がありません。先に `npm run build-storybook-react` を実行してください"
    )
    handler = functools.partial(_QuietHandler, directory=str(STORYBOOK_REACT_STATIC_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def page_errors(page: Page) -> list[str]:
    """ページを開く前から、ページで起きた例外の文言を集めるリストを返す。"""
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(error.message))
    return errors


@pytest.fixture
def open_story(page: Page, page_errors: list[str], storybook_react_url: str) -> OpenStory:
    """ストーリーの id（`shared-topbar--overview` の形）を開き、部品が描かれるまで待つ関数を返す。"""

    def _open(story_id: str) -> Page:
        """ストーリーの画面を開いて、ストーリーの根に中身が入るのを待つ。"""
        page.goto(f"{storybook_react_url}/iframe.html?id={story_id}&viewMode=story")
        page.wait_for_selector("#storybook-root > *", state="attached", timeout=STORY_TIMEOUT_MS)
        return page

    return _open
