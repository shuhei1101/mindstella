"""NFR-16『画面への反映の時間』の非機能要件テスト。"""

from __future__ import annotations

import time
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import Page, expect
from record_write_helpers import write_items
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

# 書き換えから画面の再描画までの上限（秒）
LIMIT_SEC = 1.0

# 測る回数
TIMES = 10

# 1 回の書き換えで行が出るのを待つ上限（ミリ秒）。上限を超えた回も最大に含めて判定する
ROW_TIMEOUT_MS = 10_000

# 画面の本文に中身が入るのを待つ上限（ミリ秒）
RENDER_TIMEOUT_MS = 15_000

# 検討事項を表で開く search
DECISIONS_TABLE = "?tab=decisions&view=table"


def _table_url(preview_url: str) -> str:
    """配信の URL に、検討事項を表で開く search を付ける。"""
    parts = urlsplit(preview_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, DECISIONS_TABLE.removeprefix("?"), ""))


def test_preview_reflect_time(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page
) -> None:
    """書き換えから画面の再描画までが 1 秒以内（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の検討事項", status="未決定"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    page.goto(_table_url(str(served.data["url"])))
    expect(page.get_by_role("row").filter(has_text="最初の検討事項")).to_be_visible(timeout=RENDER_TIMEOUT_MS)
    elapsed: list[float] = []
    # 実行（1 件ずつ追加し、呼ぶ直前から表に行が出るまでを測る）
    for count in range(1, TIMES + 1):
        title = f"追加した検討事項 {count}"
        item = {key: value for key, value in make_item("D-0", title=title).items() if key != "id"}
        started = time.monotonic()
        write_items(call_tool, str(root), add=[("decision", item)])
        expect(page.get_by_role("row").filter(has_text=title)).to_be_visible(timeout=ROW_TIMEOUT_MS)
        elapsed.append(time.monotonic() - started)
    # 検証
    assert max(elapsed) <= LIMIT_SEC, f"10 回の時間（秒）: {[round(value, 3) for value in elapsed]}"
