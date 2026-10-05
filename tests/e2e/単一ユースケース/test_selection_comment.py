"""選んだ箇所へコメントする（詳細パネルで本文の文か項目の値を選び、その箇所を指すコメントをレビュー中に溜める）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_BUTTON,
    DETAIL_MESSAGE,
    DETAIL_TEXTAREA,
    PILL,
    OpenPreview,
    select_text,
    select_text_for_pill,
)
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

# 資料 A-1 の本文（段落の 2 行目と 3 行目が同じ文。2 行目のほうを選ぶ）
BODY_WITH_SAME_SENTENCE = "1 行目の文\n言い換えたい文\n言い換えたい文\n"

# 選ぶ文
SENTENCE = "言い換えたい文"

# 案 B の短所と、本文に図を持つ検討事項 D-1 の本文
CONS = "数が多いと長い"
BODY_WITH_DIAGRAM = "# 流れ\n\n```mermaid\nflowchart LR\n  開始 --> 終了\n```\n"

# 溜めた結果が画面に出るまで待つ上限ミリ秒と、図を描き終わるまで待つ上限ミリ秒
RESULT_TIMEOUT_MS = 10_000
DIAGRAM_TIMEOUT_MS = 20_000

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 500


def _serve(make_workspace: MakeWorkspace, call_tool: CallTool, *items: Any, **kwargs: Any) -> tuple[str, Path]:
    """ワークスペースを作り、`preview_url` が返した配信の URL とワークスペースのフォルダを返す。"""
    root = make_workspace(*items, **kwargs)
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    return str(served.data["url"]), root


def _read_comments(root: Path) -> list[dict[str, Any]]:
    """ワークスペースのレビュー中のコメントを読む（ファイルが無ければ 0 件）。"""
    path = root / "comments.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"] if path.exists() else []


def test_normal_when_body_text(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文の 2 行目の文を選ぶと入口が出て、箇所を添えたコメントを溜められる（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        make_item("A-1"),
        bodies={"A-1.md": BODY_WITH_SAME_SENTENCE},
    )
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md")
    # 実行
    select_text_for_pill(page, "aside.panel .md", SENTENCE)
    page.click(PILL)
    # 入口を押すと、選んだ文の引用と箇所を添えた入力になる
    assert page.inner_text("aside.panel .send-loc-name") == "本文 2 行目"
    assert page.inner_text("aside.panel .send-quote") == SENTENCE
    page.fill(DETAIL_TEXTAREA, "ここは言い換える")
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=RESULT_TIMEOUT_MS)
    # 検証
    comments = _read_comments(root)
    assert [(item["target"], item["body"]) for item in comments] == [("A-1", "ここは言い換える")]
    assert comments[0]["loc"] == {"kind": "body", "start": 2, "end": 2, "text": SENTENCE}
    assert page.locator(PILL).count() == 0
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"


def test_normal_when_value(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """案 B の短所を選んでも入口が出て、値のキーを添えたコメントを溜められる（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        make_item(
            "D-1",
            options=[
                {"key": "A", "content": "表で見せる"},
                {"key": "B", "content": "カードで見せる", "cons": [CONS]},
            ],
        ),
    )
    open_preview(url, "#tab=decisions&id=D-1")
    page.wait_for_selector("aside.panel .opt")
    # 実行
    select_text_for_pill(page, 'aside.panel dd[data-key="options[B].cons"]', CONS)
    page.click(PILL)
    page.fill(DETAIL_TEXTAREA, "絞り込めば短い")
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=RESULT_TIMEOUT_MS)
    # 検証
    comments = _read_comments(root)
    assert [(item["target"], item["body"]) for item in comments] == [("D-1", "絞り込めば短い")]
    assert comments[0]["loc"] == {"kind": "value", "key": "options[B].cons", "text": CONS}


def test_normal_when_title(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """見出しのタイトルを選んでも入口が出て、title のキーを添えたコメントを溜められる（正常系）。"""
    # 準備
    url, root = _serve(make_workspace, call_tool, make_item("D-1", title="表示の形"))
    open_preview(url, "#tab=decisions&id=D-1")
    page.wait_for_selector("aside.panel .d-title")
    # 実行
    select_text_for_pill(page, "aside.panel .d-title", "表示の形")
    page.click(PILL)
    page.fill(DETAIL_TEXTAREA, "題を具体的にする")
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=RESULT_TIMEOUT_MS)
    # 検証
    comments = _read_comments(root)
    assert [(item["target"], item["body"]) for item in comments] == [("D-1", "題を具体的にする")]
    assert comments[0]["loc"] == {"kind": "value", "key": "title", "text": "表示の形"}


def test_error_when_outside_body_and_value(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """関係する項目の節の見出しと図の中の文字を選んでも、入口を出さず、何も溜めない（異常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        make_item("D-2"),
        make_item("D-1", depends_on=["D-2"], body="D-1.md"),
        bodies={"D-1.md": BODY_WITH_DIAGRAM},
    )
    open_preview(url, "#tab=decisions&id=D-1")
    page.wait_for_selector("aside.panel .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行・検証（節の見出し「前提」）
    select_text(page, "aside.panel .detail", "前提")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    assert page.locator(PILL).count() == 0
    # 実行・検証（図の中の文字）
    select_text(page, "aside.panel .mermaid svg", "開始")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    assert page.locator(PILL).count() == 0
    assert _read_comments(root) == []
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "0"
