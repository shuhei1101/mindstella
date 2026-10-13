"""HTML の本文の枠の中のリンクを押す結合テストが共有する、リンク先のページの配信・タブの数え方・押し方。"""

from __future__ import annotations

import http.server
import threading
from collections.abc import Iterator

import pytest
from playwright.sync_api import Frame, Page

__all__ = [
    "LINK_PAGE_TITLE",
    "WINDOW_OPEN_RECORDER_JS",
    "frame_location",
    "html_with_links",
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

    def do_GET(self) -> None:  # noqa: N802 - http.server が呼ぶ名前
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


def html_with_links(*links: tuple[str, str, str]) -> str:
    """`(id, href の属性, 文)` から、リンクを 1 行ずつ持つ HTML の本文を作る（`href` の属性はそのまま書く）。"""
    lines = [f'<p><a id="{link_id}" {href}>{text}</a></p>' for link_id, href, text in links]
    return "\n".join(lines) + "\n"


def opened_tabs(page: Page) -> int:
    """ブラウザの文脈に開いているタブの数を返す。"""
    return len(page.context.pages)


def new_tab_after(page: Page, action: object) -> Page:
    """`action`（引数なしの関数）を実行して開いた新しいタブを、読み込み終わりまで待って返す。"""
    assert callable(action)
    with page.context.expect_page(timeout=NEW_TAB_TIMEOUT_MS) as info:
        action()
    tab = info.value
    tab.wait_for_load_state()
    return tab


def frame_location(frame: Frame) -> str:
    """枠の中の文書の場所（URL）を返す。"""
    return str(frame.evaluate("location.href"))


def recorded_window_opens(page: Page) -> list[list[str]]:
    """差し替えた `window.open` が受けた引数（文字列にしたもの）を、呼ばれた順に返す。"""
    return list(page.evaluate("window.__opens"))
