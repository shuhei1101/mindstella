"""リンクを押して開く新しいタブを確かめるテスト（結合・E2E）が共有する、タブの数え方・待ち方、`window.open` の記録、リンク先のページの配信。"""

from __future__ import annotations

import http.server
import threading
from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

__all__ = [
    "LINK_PAGE_TITLE",
    "NEW_TAB_TIMEOUT_MS",
    "WINDOW_OPEN_RECORDER_JS",
    "link_target",
    "new_tab_after",
    "opened_tabs",
    "recorded_window_opens",
]

# リンク先のページの題（新しいタブがこのページを開いたかを確かめる）
LINK_PAGE_TITLE = "リンク先のページ"

# 新しいタブが開くまで待つ上限ミリ秒
NEW_TAB_TIMEOUT_MS = 10_000

# 親の画面の `window.open` を、呼び出しを記録するものに差し替える
WINDOW_OPEN_RECORDER_JS = """() => {
    window.__opens = [];
    window.open = (...args) => { window.__opens.push(args.map(String)); return null; };
}"""


class _LinkPageHandler(http.server.BaseHTTPRequestHandler):
    """どのパスにも同じ小さなページを返す、リンク先の配信。"""

    def do_GET(self) -> None:  # http.server が呼ぶ名前
        """リンク先のページを返す。"""
        body = f"<!doctype html><title>{LINK_PAGE_TITLE}</title><p>リンク先</p>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """アクセスのログを出さない。"""


@pytest.fixture
def link_target() -> Iterator[str]:
    """プレビューとは別の空きポートでリンク先のページを配り、その URL（末尾の `/` なし）を返す。終わったら止める。"""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _LinkPageHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join()


def opened_tabs(page: Page) -> int:
    """ブラウザの文脈に開いているタブの数を返す。"""
    return len(page.context.pages)


def new_tab_after(page: Page, action: Callable[[], object]) -> Page:
    """`action` を実行して開いた新しいタブを、読み込み終わりまで待って返す。"""
    with page.context.expect_page(timeout=NEW_TAB_TIMEOUT_MS) as info:
        action()
    tab = info.value
    tab.wait_for_load_state()
    return tab


def recorded_window_opens(page: Page) -> list[list[str]]:
    """差し替えた `window.open` が受けた引数（文字列にしたもの）を、呼ばれた順に返す。"""
    return list(page.evaluate("window.__opens"))
