"""プレビューで記録を読み返す（変更履歴から時点を選び、概要から項目の詳細を開き、つながりで関係を読み、URL に残す）の E2E テスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from playwright.sync_api import Page
from preview_helpers import (
    OpenPreview,
    click_item_ball,
    pick_history_point,
    snapshot_records,
    visit_and_close,
)
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree

if TYPE_CHECKING:
    from conftest import Replay

# 本文に mermaid の図を持つ Markdown
BODY_WITH_DIAGRAM = """# 納品物の本文

```mermaid
flowchart LR
  A --> B
```
"""

# 検討事項 D-3 の書き換える前と後の本文（段落 1 つと mermaid の図のノード 1 つを書き換える）
BODY_D3_BEFORE = """# D-3 の検討

最初の段落です。

```mermaid
flowchart TD
  A[開始] --> B[処理]
```
"""
BODY_D3_AFTER = """# D-3 の検討

書き換えた段落です。

```mermaid
flowchart TD
  A[開始] --> B[処理を変えた]
```
"""

# 書き換えのまとまりの説明
COMMIT_SUMMARY = "D-3 を見直し、D-6 を足す"

# 後から足す検討事項（D-6 になる）
NEW_DECISION: dict[str, Any] = {
    "title": "後から足した問い",
    "status": "未決定",
    "lead": "後から足した問い",
    "weight": "大",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "構成",
}

# 新しいタブで開き直した画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 20_000


def _settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """カテゴリー 2 つ・フェーズ 3 つ・納品物 1 つを持つ設定を返す。"""
    return {
        **valid_settings,
        "categories": [
            {"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"},
            {"name": "画面", "target": "mindmap", "summary": "プレビューの画面"},
        ],
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [{"title": "仕様書", "doc": "A-1"}],
        },
    }


def _records(make_item: MakeItem) -> list[dict[str, Any]]:
    """未決定・決定済み・要見直し・保留を含み、依存でつながる検討事項と、そのほかの種類の項目を返す。

    D-3 は書き換える前の状態（未決定）で、本文のファイルを持つ。
    """
    placed: dict[str, Any] = {"target": "mindmap"}
    return [
        make_item("D-1", status="決定済み", category="データ構造", phase="目的", **placed),
        make_item(
            "D-3",
            status="未決定",
            category="画面",
            phase="要件",
            depends_on=["D-1"],
            body="D-3.md",
            **placed,
        ),
        make_item(
            "D-5", status="未決定", category="画面", phase="構成", depends_on=["D-3"], **placed
        ),
        make_item("D-4", status="保留", category="データ構造", phase="構成", **placed),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("R-1", question="何を調べたか"),
        make_item("A-1", deliverable=True, status="完成", kind="仕様書"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """変更履歴から「前回開いてから」を選び、概要の要見直しから D-3 の詳細を開き、つながりで D-3 を押して、終えた URL を開き直す（正常系）。"""
    # 準備（プレビューを一度開いて閉じた後に、D-3 の状態と本文を書き換え、D-6 を足して 1 つのまとまりにする）
    root = make_workspace(
        *_records(make_item),
        settings=_settings(valid_settings),
        bodies={"A-1.md": BODY_WITH_DIAGRAM, "D-3.md": BODY_D3_BEFORE},
    )
    ws = str(root)
    served = call_tool("preview_url", workspace=ws)
    assert served.data is not None
    url = served.data["url"]
    visit_and_close(page, url)
    replay(
        "update", workspace=ws, id="D-3", item={"status": "要見直し", "body_markdown": BODY_D3_AFTER}
    )
    replay("add", workspace=ws, kind="decision", item=NEW_DECISION)
    replay("commit", workspace=ws, summary=COMMIT_SUMMARY)
    before = snapshot_records(snapshot_tree(root))
    # 実行（概要を開き、変更履歴から「前回開いてから」を選ぶ）
    open_preview(url)
    pick_history_point(page, "前回開いてから")
    # 実行（概要の要見直しのタイルで D-3 を押す）
    page.click('#tile-review button[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    # 実行（つながりを開く。開いている詳細パネルは閉じない）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    # 実行（D-3 の玉を押す）
    click_item_ball(page, "D-3")
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    final_url = page.url
    # 検証（終えたときの URL を新しいタブで開くと、つながりの画面と D-3 の詳細パネルが開く）
    reopened = page.context.new_page()
    reopened.goto(final_url)
    reopened.wait_for_selector("main#main > *", state="attached", timeout=RENDER_TIMEOUT_MS)
    reopened.wait_for_selector("aside.panel.open")
    assert reopened.get_attribute('nav.tabbar a[data-tab="graph"]', "aria-current") == "page"
    assert reopened.inner_text("aside.panel .d-title") == "D-3の題"
    assert reopened.locator("#graph-canvas").count() == 1
    # 検証（新しいタブで開いた画面でも、選んだ時点の差分の表示のままで、D-3 の本文に足した・消した印がある）
    assert reopened.locator(".df-chip").count() == 1
    reopened.wait_for_selector("aside.panel .md ins.df-blk", timeout=RENDER_TIMEOUT_MS)
    assert reopened.locator("aside.panel .md del.df-blk").count() >= 1
    # 検証（ワークスペースの YAML の中身が、開く前と同じ）
    assert snapshot_records(snapshot_tree(root)) == before
