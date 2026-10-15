"""コメントの画面の結合テストが共有する値と、選択・記録の読み取りの関数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page, Route
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from workspace_fixtures import RECORD_DIR

__all__ = [
    "BAND_COUNT",
    "BAND_RESULT",
    "CHECK_ALL",
    "COMMENTS_BUTTON",
    "COMMENTS_PANEL",
    "DETAIL_FORM",
    "DETAIL_MESSAGE",
    "DETAIL_TEXTAREA",
    "DRAFT_WAIT_MS",
    "FREE_FORM",
    "FREE_TEXTAREA",
    "PANEL_REVIEW",
    "PILL",
    "REVIEW_ENTRY",
    "REVIEW_HEAD",
    "ROW_CORNER_GAPS_JS",
    "ROW_CORNER_TOLERANCE_PX",
    "THREAD_ROWS",
    "THREE_LINE_BODY",
    "UPDATE_TIMEOUT_MS",
    "free_comment",
    "fulfill_problem",
    "open_list",
    "open_review",
    "open_thread",
    "read_workspace_yaml",
    "review_row",
    "select_text",
    "select_text_for_pill",
    "thread_row",
    "wait_thread_seen",
    "wait_until_focused",
]

# 3 行の段落を持つ資料の本文（2 行目が選ぶ文）
THREE_LINE_BODY = "最初の文\n言い換えたい文\n最後の文\n"

# 書き換えや送信の結果が画面に出るまで待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 書きかけを保つ待ち（画面の `DRAFT_SAVE_DELAY_MS`）を過ぎるまで待つミリ秒
DRAFT_WAIT_MS = 1_200

# 既読になるのを待つ間に、threads.yaml を読み直す間隔ミリ秒
SEEN_POLL_MS = 100

# トップバーのコメントのボタンと、コメントの一覧のパネル
COMMENTS_BUTTON = "header.topbar button.comments-btn"
COMMENTS_PANEL = "aside.comments-panel"

# 詳細パネルの下端のコメントの入力とその入力欄・結果
DETAIL_FORM = "aside.panel form.send"
DETAIL_TEXTAREA = "aside.panel form.send textarea"
DETAIL_MESSAGE = "aside.panel form.send .send-msg"

# コメントの一覧の下端の、項目を指さないコメントの入力とその入力欄
FREE_FORM = f"{COMMENTS_PANEL} .comments-free form.send"
FREE_TEXTAREA = f"{FREE_FORM} textarea"

# 詳細パネルの「レビュー中のコメント」の節
PANEL_REVIEW = "aside.panel .d-review"

# 選んだ箇所のコメントの入口
PILL = "button.selection-comment"

# コメントの一覧の見出しの帯の「レビュー中」の入口と、レビュー中の書き込みの画面の見出し
REVIEW_ENTRY = f"{COMMENTS_PANEL} .comments-head button.review-entry"
REVIEW_HEAD = f"{COMMENTS_PANEL} .review-head"

# 行の右上の操作が、行の右上の隅から離れてよい上限（px）
ROW_CORNER_TOLERANCE_PX = 24

# パネルの動きが終わってから、行の右上の隅と「修正」「削除」の組の隅との隙間（px）を返す
ROW_CORNER_GAPS_JS = """async (selector) => {
    await Promise.all(document.getAnimations().map(animation => animation.finished));
    const row = document.querySelector(selector).getBoundingClientRect();
    const actions = document.querySelector(`${selector} .row-actions`).getBoundingClientRect();
    return { right: row.right - actions.right, top: actions.top - row.top };
}"""

# スレッドの一覧の行
THREAD_ROWS = f"{COMMENTS_PANEL} ul.th-list > li"

# レビュー中の書き込みの画面の送る帯の要素
CHECK_ALL = f"{COMMENTS_PANEL} .send-band label.legend-all-check input"
BAND_COUNT = f"{COMMENTS_PANEL} .send-band .send-count"
BAND_RESULT = f"{COMMENTS_PANEL} .send-band .send-msg"

# 選んだ後に入口が出るまで待つ 1 回のミリ秒と、選び直す回数の上限（描き直しで選択が外れても選び直す）
PILL_WAIT_MS = 2_000
PILL_SELECT_ATTEMPTS = 5

# 要素の中の文を、始まりから終わりまで選ぶ
SELECT_TEXT_SCRIPT = """([selector, text]) => {
  const root = document.querySelector(selector);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const at = node.textContent.indexOf(text);
    if (at >= 0) {
      const range = document.createRange();
      range.setStart(node, at);
      range.setEnd(node, at + text.length);
      const selection = getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      return true;
    }
  }
  return false;
}"""


def select_text(page: Page, selector: str, text: str) -> None:
    """要素の中の文を選ぶ。文が見つからなければ例外にする。"""
    found = page.evaluate(SELECT_TEXT_SCRIPT, [selector, text])
    if found is not True:
        raise AssertionError(f"{selector} の中に選ぶ文がありません: {text}")


def select_text_for_pill(page: Page, selector: str, text: str) -> None:
    """要素の中の文を選び、選んだ箇所のコメントの入口が出るまで待つ。画面の描き直しで選択が外れたときは選び直す。"""
    for _ in range(PILL_SELECT_ATTEMPTS):
        select_text(page, selector, text)
        try:
            page.wait_for_selector(PILL, timeout=PILL_WAIT_MS)
        except PlaywrightTimeoutError:
            continue
        return
    raise AssertionError(f"選んだ後に入口が出ませんでした: {selector} / {text}")


def fulfill_problem(route: Route, status: int, detail: str) -> None:
    """要求に、理由つきのエラー（`application/problem+json`、RFC 9457）で答える。"""
    problem = {"type": "about:blank", "title": "error", "status": status, "detail": detail}
    route.fulfill(
        status=status,
        content_type="application/problem+json",
        body=json.dumps(problem, ensure_ascii=False),
    )


def review_row(host: str, comment_id: str) -> str:
    """host（パネル・全画面・コメントの一覧）の中の、コメントの行の選択子を返す。"""
    return f"{host} li[data-comment='{comment_id}']"


def wait_until_focused(page: Page, selector: str) -> None:
    """selector に当たる要素へフォーカスが移るのを待つ。"""
    page.wait_for_function(
        "selector => document.activeElement === document.querySelector(selector)",
        arg=selector,
        timeout=UPDATE_TIMEOUT_MS,
    )


def read_workspace_yaml(root: Path, name: str) -> dict[str, Any]:
    """ワークスペースの YAML を読む。"""
    return yaml.safe_load((root / RECORD_DIR / name).read_text(encoding="utf-8"))


def wait_thread_seen(page: Page, root: Path, thread_id: str) -> None:
    """threads.yaml のスレッドの全ての書き込みが利用者の既読になるのを待つ。"""
    for _ in range(UPDATE_TIMEOUT_MS // SEEN_POLL_MS):
        thread = next(item for item in read_workspace_yaml(root, "threads.yaml")["items"] if item["id"] == thread_id)
        if all(post["seen"] for post in thread["posts"]):
            return
        page.wait_for_timeout(SEEN_POLL_MS)
    raise AssertionError(f"{thread_id} が既読になりません")


def free_comment(comment: dict[str, Any]) -> dict[str, Any]:
    """向けた項目のキーを持たない（項目を指さない）コメントにする。"""
    return {key: value for key, value in comment.items() if key != "target"}


def open_list(page: Page) -> None:
    """トップバーのコメントのボタンで一覧（スレッドの一覧の画面）を開き、開くのを待つ。"""
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")


def open_review(page: Page) -> None:
    """一覧を開き、見出しの帯の「レビュー中」でレビュー中の書き込みの画面へ切り替える。"""
    open_list(page)
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)


def thread_row(thread_id: str) -> str:
    """スレッドの一覧の中の、スレッドの行の選択子を返す（まだ送っていない新しいスレッドは `new:{コメントの ID}`）。"""
    return f"{COMMENTS_PANEL} ul.th-list > li:has(> button[data-focus='thread:{thread_id}'])"


def open_thread(page: Page, thread_id: str) -> None:
    """一覧を開き、スレッドの行を押してスレッドの画面へ切り替える。"""
    open_list(page)
    page.click(f"{thread_row(thread_id)} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
