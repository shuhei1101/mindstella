"""前回からの差分を見る（変更履歴から書き換えのまとまりを選び、印と詳細パネルで差分を読む）の E2E テスト。

モデルを呼ばず、MCP のツールで記録を書き換え、サーバーが配るプレビューを実際のブラウザで開いて確かめる。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from playwright.sync_api import Page
from preview_helpers import (
    HISTORY_DIALOG,
    HISTORY_REDRAW_TIMEOUT_MS,
    OPENED_TICK_MS,
    OpenPreview,
    pick_history_point,
    snapshot_records,
    visit_and_close,
)
from workspace_fixtures import RECORD_DIR, CallTool, MakeItem, MakeWorkspace, SnapshotTree

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import Replay

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 検討事項の表の行
TABLE_ROWS = "table.grid tbody tr"

# 差分を出せない旨の文言
NOTE_TRIMMED = "このまとまりの前後を組み立てられません。保持する回数を超えた古い変更履歴は消えています。今の内容を出しています。"
NOTE_BODY_UNAVAILABLE = "本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。今の本文を出しています。"

# まとまりの日時の表示（月/日 時:分）
WHEN_PATTERN = re.compile(r"\d{2}/\d{2} \d{2}:\d{2}")

# 変更の印と新規の印の class
MARK_CHANGED = "df-mark df-chg"
MARK_NEW = "df-mark df-new"

# モーダルの行の時点の識別子・名前・日時・件数を上から読む
ROWS_SCRIPT = """() => [...document.querySelectorAll('dialog.hist .hist-item')].map(row => ({
    sel: row.dataset.sel,
    name: row.querySelector('.hist-name').textContent,
    sub: row.querySelector('.hist-sub').textContent,
    n: row.querySelector('.hist-n')?.textContent ?? null,
}))"""

# 表の行ごとの印の class（印が無ければ null）を読む
MARKS_SCRIPT = """rows => Object.fromEntries(rows.map(
    r => [r.dataset.id, r.querySelector('.row-open + .df-mark')?.className ?? null]
))"""

# タブごとの件数の表示を読む
TAB_COUNTS_SCRIPT = """() => Object.fromEntries([...document.querySelectorAll('nav.tabbar a.tab')].map(
    a => [a.dataset.tab, a.querySelector('.count')?.textContent ?? null]
))"""

# 項目の位置（検討事項に付ける対象・カテゴリー・フェーズ）
PLACE = {"target": "mindmap", "category": "データ構造", "phase": "要件"}

# 書き換えのまとまりの説明
COMMIT_SUMMARY = "D-3 を見直し、D-6 を足す"

# 後から足す検討事項（D-6 になる）
NEW_DECISION: dict[str, Any] = {
    "title": "後から足した問い",
    "status": "未決定",
    "lead": "後から足した問い",
    "weight": "大",
    **PLACE,
}

# 検討事項 D-3 の書き換える前の本文（段落 3 つと flowchart の図）
BODY_D3_BEFORE = """# 検討メモ

最初の段落です。

消す段落です。

残す段落です。

```mermaid
flowchart TD
  A[開始] --> B[処理]
```
"""

# D-3 の書き換えた後の本文（段落を 1 つ書き換えて 1 つ消し、図のノードのラベルを 1 つ変える）
BODY_D3_AFTER = """# 検討メモ

書き換えた段落です。

残す段落です。

```mermaid
flowchart TD
  A[開始] --> B[処理を変えた]
```
"""

# 段落 1 つの本文の移り変わり
BODY_V0 = "# 検討メモ\n\n最初の本文です。\n"
BODY_V1 = "# 検討メモ\n\n1 回目に書き換えた本文です。\n"
BODY_V2 = "# 検討メモ\n\n2 回目に書き換えた本文です。\n"

# 資料 A-1 の書き換える前と後の本文
BODY_A1_BEFORE = "# 仕様\n\n直す前の仕様です。\n"
BODY_A1_AFTER = "# 仕様\n\n直した後の仕様です。\n"

# 資料 A-1 の本文の gantt（ノード・辺に色を付ける対象に入らない種類）の書き換える前と後
GANTT_BEFORE = """# 工程

```mermaid
gantt
  dateFormat YYYY-MM-DD
  section 準備
  設計 :a1, 2026-10-01, 3d
```
"""
GANTT_AFTER = GANTT_BEFORE.replace("3d", "5d")

# 手で書き換えた本文
HAND_WRITTEN_BODY = "手で書いた A\n\n手で書いた B\n"


def _serve(call_tool: CallTool, root: Path) -> str:
    """`preview_url` を呼んで配信を立て、その URL を返す。"""
    result = call_tool("preview_url", workspace=str(root))
    assert result.is_error is False, result.text
    assert result.data is not None
    return str(result.data["url"])


def _read_rows(page: Page) -> list[dict[str, Any]]:
    """「変更履歴」のモーダルを開いて時点の行を上から読み、閉じる。"""
    page.get_by_role("button", name="変更履歴").click()
    page.wait_for_selector(f"{HISTORY_DIALOG}[open]")
    rows: list[dict[str, Any]] = page.evaluate(ROWS_SCRIPT)
    page.keyboard.press("Escape")
    page.wait_for_selector(f"{HISTORY_DIALOG}[open]", state="detached")
    return rows


def _row_marks(page: Page) -> dict[str, str | None]:
    """検討事項の表の行ごとに、印の class（印が無ければ None）を返す。"""
    return page.eval_on_selector_all(TABLE_ROWS, MARKS_SCRIPT)


def _marked_tabs(page: Page) -> list[str]:
    """点（新規・変更の項目がある印）が付いたタブを左から返す。"""
    return page.eval_on_selector_all(
        "nav.tabbar a.tab:has(.df-dot)", "tabs => tabs.map(t => t.dataset.tab)"
    )


def _open_decision(page: Page, item_id: str) -> None:
    """検討事項の表の行を押して、詳細パネルが開くのを待つ。"""
    page.click(f'table.grid button.row-open[data-id="{item_id}"]')
    page.wait_for_selector("aside.panel.open .d-title")


def _block_texts(page: Page) -> tuple[str, str]:
    """詳細パネルの本文の足した段落と消した段落の文字を、それぞれつないで返す。"""
    added = "".join(page.locator("aside.panel .md ins.df-blk").all_inner_texts())
    removed = "".join(page.locator("aside.panel .md del.df-blk").all_inner_texts())
    return added, removed


def _decisions(make_item: MakeItem, *body_ids: str) -> list[dict[str, Any]]:
    """未決定の検討事項 D-1〜D-5 を返す。`body_ids` の項目だけ本文のファイルを持つ。"""
    return [
        make_item(
            f"D-{number}",
            status="未決定",
            **({"body": f"D-{number}.md"} if f"D-{number}" in body_ids else {}),
        )
        for number in range(1, 6)
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """変更履歴から「前回開いてから」を選び、印の付いた D-3 の詳細パネルで状態・本文・図・Raw の変更を読む（正常系）。"""
    # 準備
    root = make_workspace(
        *_decisions(make_item, "D-3"),
        make_item("T-1"),
        bodies={"D-3.md": BODY_D3_BEFORE},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    visit_and_close(page, url)
    replay(
        "update", workspace=ws, id="D-3", item={"status": "要見直し", "body_markdown": BODY_D3_AFTER}
    )
    replay("add", workspace=ws, kind="decision", item=NEW_DECISION)
    replay("commit", workspace=ws, summary=COMMIT_SUMMARY)
    before = snapshot_records(snapshot_tree(root))
    # 実行（開いて、差分の表示に入る前の画面を読む）
    open_preview(url, "#tab=overview")
    counts_before = page.evaluate(TAB_COUNTS_SCRIPT)
    # 検証（差分の表示に入る前は、どの項目にもタブにも印が無い）
    assert page.locator(".df-mark").count() == 0
    assert page.locator("nav.tabbar .df-dot").count() == 0
    # 実行・検証（変更履歴の一覧）
    rows = _read_rows(page)
    assert [row["name"] for row in rows[1:]] == ["前回開いてから", COMMIT_SUMMARY]
    assert WHEN_PATTERN.fullmatch(rows[2]["sub"])
    # 実行（「前回開いてから」を選ぶ）
    pick_history_point(page, "前回開いてから")
    # 検証（検討事項のタブにだけ印が付き、タブの件数は選ぶ前と同じ）
    assert _marked_tabs(page) == ["decisions"]
    assert page.evaluate(TAB_COUNTS_SCRIPT) == counts_before
    # 実行（検討事項の表を開く）
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector(TABLE_ROWS)
    # 検証（D-3 に変更、D-6 に新規の印が付き、文言の札は出ない）
    assert _row_marks(page) == {
        "D-1": None,
        "D-2": None,
        "D-3": MARK_CHANGED,
        "D-4": None,
        "D-5": None,
        "D-6": MARK_NEW,
    }
    assert page.locator("table.grid .df-badge").count() == 0
    # 実行（D-3 の詳細パネルを開く）
    _open_decision(page, "D-3")
    page.wait_for_selector("aside.panel figure.diagram.df-colored", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（状態の前の値と今の値）
    status = page.locator('aside.panel [data-key="status"] .df-kv')
    assert status.locator("del.df-was").inner_text().endswith("未決定")
    assert status.locator("ins.df-now").inner_text().endswith("要見直し")
    # 検証（本文は Markdown のまま、書き換えた段落に足した印、消した段落に消した印が付き、変えていない段落には付かない）
    assert page.inner_text('aside.panel .md [data-md-level="1"]') == "検討メモ"
    added, removed = _block_texts(page)
    assert "書き換えた段落です。" in added
    assert "最初の段落です。" in removed
    assert "消す段落です。" in removed
    assert "残す段落です。" in page.inner_text("aside.panel .md")
    assert "残す段落です。" not in added + removed
    # 検証（図は、ラベルを変えたノードにだけ変わった色が付き、ほかのノードと辺には付かない）
    figure = page.locator("aside.panel figure.diagram.df-colored")
    assert figure.locator("g.df-n-chg").count() == 1
    assert "処理を変えた" in (figure.locator("g.df-n-chg").text_content() or "")
    assert figure.locator(".df-n-add, .df-e-add, .df-e-chg").count() == 0
    # 実行（図の Raw を押す）
    figure.locator('[data-act="diagram-raw"]').click()
    # 検証（変えた行が消した行と足した行として出る）
    raw = figure.locator(".dg-raw.df-raw")
    removed_lines = raw.locator(".df-line.df-del").all_inner_texts()
    added_lines = raw.locator(".df-line.df-add").all_inner_texts()
    assert any("B[処理]" in line for line in removed_lines)
    assert any("B[処理を変えた]" in line for line in added_lines)
    # 実行（読み込み直す）
    page.reload()
    page.wait_for_selector(".df-chip", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    page.wait_for_selector(TABLE_ROWS)
    # 検証（同じ時点の差分の表示のままで、D-3 と D-6 の印が残る）
    assert page.inner_text(".df-chip-t").endswith("前回開いてから")
    assert _row_marks(page)["D-3"] == MARK_CHANGED
    assert _row_marks(page)["D-6"] == MARK_NEW
    # 実行（差分の表示から抜ける）
    page.get_by_role("button", name="差分の表示をやめる").click()
    page.wait_for_selector(".df-chip", state="detached", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    page.wait_for_function(
        "!document.querySelector('aside.panel .md ins.df-blk, aside.panel .md del.df-blk')"
    )
    # 検証（印と差分が消え、D-3 の本文は今の内容だけになる）
    assert page.locator(".df-mark").count() == 0
    assert page.locator("nav.tabbar .df-dot").count() == 0
    body = page.inner_text("aside.panel .md")
    assert "書き換えた段落です。" in body
    assert "消す段落です。" not in body
    # 検証（ワークスペースの YAML と本文の中身が、開く前と同じ）
    assert snapshot_records(snapshot_tree(root)) == before


def test_normal_when_older_change_set_selected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """古いまとまりを選ぶと、そのまとまりで変わった資料に印が付き、前後の本文の差分を読める（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", status="完成", kind="仕様書"),
        make_item("D-3", status="未決定", body="D-3.md"),
        bodies={"A-1.md": BODY_A1_BEFORE, "D-3.md": BODY_V0},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="A-1", item={"body_markdown": BODY_A1_AFTER})
    replay("commit", workspace=ws, summary="仕様書を直す")
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="検討事項を直す")
    open_preview(url, "#tab=docs")
    # 実行・検証（一覧に、まとまりが新しい順に日時と変わった項目の数つきで並ぶ）
    rows = [row for row in _read_rows(page) if row["sel"] not in ("", "since", "pending")]
    assert [row["name"] for row in rows] == ["検討事項を直す", "仕様書を直す"]
    assert [row["n"] for row in rows] == ["1 件", "1 件"]
    assert all(WHEN_PATTERN.fullmatch(row["sub"]) for row in rows)
    # 実行（「仕様書を直す」を選ぶ）
    pick_history_point(page, "仕様書を直す")
    # 検証（資料のタブと A-1 に印が付き、検討事項のタブと D-3 には付かない）
    assert _marked_tabs(page) == ["docs"]
    assert page.locator('.doc-card[data-id="A-1"] .df-mark').get_attribute("class") == MARK_CHANGED
    # 実行（A-1 の詳細パネルを開く）
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open .d-title")
    # 検証（そのまとまりの前後の本文の足した・消した印が出る）
    added, removed = _block_texts(page)
    assert "直した後の仕様です。" in added
    assert "直す前の仕様です。" in removed
    # 実行（検討事項の表を開く）
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector(TABLE_ROWS)
    # 検証（D-3 には印が付かない）
    assert page.locator(f"{TABLE_ROWS} .df-mark").count() == 0


def test_normal_when_pending_changes(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """`commit` を呼ばない書き換えは「まだまとめていない変更」として選べ、D-3 に印と本文の差分が出る（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="未決定", body="D-1.md"),
        make_item("D-3", status="未決定", body="D-3.md"),
        bodies={"D-1.md": BODY_V0, "D-3.md": BODY_V0},
    )
    url = _serve(call_tool, root)
    replay("update", workspace=str(root), id="D-3", item={"body_markdown": BODY_V1})
    open_preview(url, "#tab=decisions&view=table")
    # 実行・検証（一覧の先頭に「まだまとめていない変更」があり、変わった項目の数が 1）
    pending = _read_rows(page)[1]
    assert pending["sel"] == "pending"
    assert pending["name"] == "まだまとめていない変更"
    assert pending["n"] == "1 件"
    # 実行（選ぶ）
    pick_history_point(page, "まだまとめていない変更")
    # 検証（D-3 に変更の印が付き、D-1 には付かない）
    assert _row_marks(page) == {"D-1": None, "D-3": MARK_CHANGED}
    # 実行（D-3 の詳細パネルを開く）
    _open_decision(page, "D-3")
    page.wait_for_selector("aside.panel .md ins.df-blk", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（書き換えた本文の差分が出る）
    added, removed = _block_texts(page)
    assert "1 回目に書き換えた本文です。" in added
    assert "最初の本文です。" in removed


def test_normal_when_diagram_type_not_colored(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """ノード・辺に色を付けない種類の図は、図の枠に色を付け、Raw で記法の行の差分を読む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", status="完成", kind="仕様書"), bodies={"A-1.md": GANTT_BEFORE}
    )
    url = _serve(call_tool, root)
    replay("update", workspace=str(root), id="A-1", item={"body_markdown": GANTT_AFTER})
    replay("commit", workspace=str(root), summary="工程を直す")
    open_preview(url, "#tab=docs")
    pick_history_point(page, "工程を直す")
    # 実行（A-1 の詳細パネルを開く）
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector("aside.panel figure.diagram.df-frame", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（図の枠に変わった色が付き、図の中の要素には色が付かない）
    figure = page.locator("aside.panel figure.diagram.df-frame")
    assert figure.locator(".df-n-add, .df-n-chg, .df-e-add, .df-e-chg").count() == 0
    # 実行（図の Raw を押す）
    figure.locator('[data-act="diagram-raw"]').click()
    # 検証（期間を変えた行が消した行と足した行として出る）
    raw = figure.locator(".dg-raw.df-raw")
    assert any("3d" in line for line in raw.locator(".df-line.df-del").all_inner_texts())
    assert any("5d" in line for line in raw.locator(".df-line.df-add").all_inner_texts())


def test_normal_when_rewritten_while_open(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """開いたまま D-3 を書き換えて `commit` すると、再読み込みせずに印が付き、画面と URL は変わらない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="未決定", body="D-1.md"),
        make_item("D-3", status="未決定", body="D-3.md"),
        bodies={"D-1.md": BODY_V0, "D-3.md": BODY_V0},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    open_preview(url, "#tab=decisions&view=table")
    pick_history_point(page, "前回開いてから")
    assert _row_marks(page) == {"D-1": None, "D-3": None}
    url_before = page.url
    # タブを開いた日時より後に書き換える
    page.wait_for_timeout(OPENED_TICK_MS)
    # 実行（開いたまま書き換える）
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="検討事項を直す")
    page.wait_for_selector(
        'table.grid tbody tr[data-id="D-3"] .row-open + .df-mark.df-chg', timeout=HISTORY_REDRAW_TIMEOUT_MS
    )
    # 検証（D-3 に変更の印が付き、D-1 には付かない。同じ時点の差分の表示のままで、URL が変わらない）
    assert _row_marks(page) == {"D-1": None, "D-3": MARK_CHANGED}
    assert page.inner_text(".df-chip-t").endswith("前回開いてから")
    assert page.url == url_before
    # 実行（D-3 の詳細パネルを開く）
    _open_decision(page, "D-3")
    page.wait_for_selector("aside.panel .md ins.df-blk", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（書き換えた本文に足した・消した印がある）
    added, removed = _block_texts(page)
    assert "1 回目に書き換えた本文です。" in added
    assert "最初の本文です。" in removed


def test_normal_when_first_open(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """前回開いた日時が無い端末では、「前回開いてから」に印が付かず、書き換えのまとまりを選ぶと印と差分が出る（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="未決定", body="D-1.md"),
        make_item("D-3", status="未決定", body="D-3.md"),
        bodies={"D-1.md": BODY_V0, "D-3.md": BODY_V0},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="検討事項を直す")
    # 開いた日時より後に書き換えたことにならないよう、書き換えの後に待ってから開く
    page.wait_for_timeout(OPENED_TICK_MS)
    open_preview(url, "#tab=decisions&view=table")
    # 実行（「前回開いてから」を選ぶ）
    pick_history_point(page, "前回開いてから")
    # 検証（開く前に書き換えた D-3 にも、どのタブにも印が付かない）
    assert _row_marks(page) == {"D-1": None, "D-3": None}
    assert page.locator("nav.tabbar .df-dot").count() == 0
    # 実行（「検討事項を直す」を選ぶ）
    pick_history_point(page, "検討事項を直す")
    # 検証（D-3 に変更の印が付き、詳細パネルに本文の差分が出る）
    assert _row_marks(page) == {"D-1": None, "D-3": MARK_CHANGED}
    _open_decision(page, "D-3")
    page.wait_for_selector("aside.panel .md ins.df-blk", timeout=DIAGRAM_TIMEOUT_MS)
    added, removed = _block_texts(page)
    assert "1 回目に書き換えた本文です。" in added
    assert "最初の本文です。" in removed


def test_normal_when_history_limit_zero(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """保持する回数が 0 だと、書き換えた D-3 は変更履歴を持たず、足した D-6 にだけ新規の印が付く（正常系）。"""
    # 準備
    root = make_workspace(
        *_decisions(make_item, "D-3"),
        settings={**valid_settings, "history_limit": 0},
        bodies={"D-3.md": BODY_V0},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    visit_and_close(page, url)
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V1})
    replay("add", workspace=ws, kind="decision", item=NEW_DECISION)
    replay("commit", workspace=ws, summary=COMMIT_SUMMARY)
    open_preview(url, "#tab=decisions&view=table")
    # 実行
    pick_history_point(page, "前回開いてから")
    # 検証（D-6 に新規の印が付き、D-3 を含む D-1〜D-5 には印が付かない）
    assert _row_marks(page) == {
        "D-1": None,
        "D-2": None,
        "D-3": None,
        "D-4": None,
        "D-5": None,
        "D-6": MARK_NEW,
    }
    # 実行（D-3 の詳細パネルを開く）
    _open_decision(page, "D-3")
    # 検証（差分の印が無く、今の本文だけが出る）
    assert page.locator("aside.panel .df-kv").count() == 0
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    assert "1 回目に書き換えた本文です。" in page.inner_text("aside.panel .md")


def test_normal_when_change_set_history_trimmed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """保持する回数を超えて消えた古いまとまりを選ぶと、印は付き、詳細パネルは今の本文と差分を出せない旨を出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-3", status="未決定", body="D-3.md"),
        settings={**valid_settings, "history_limit": 1},
        bodies={"D-3.md": BODY_V0},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="1 回目")
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V2})
    replay("commit", workspace=ws, summary="2 回目")
    open_preview(url, "#tab=decisions&view=table")
    # 実行（「1 回目」を選ぶ）
    pick_history_point(page, "1 回目")
    # 検証（D-3 に変更の印が付く）
    assert _row_marks(page) == {"D-3": MARK_CHANGED}
    # 実行（D-3 の詳細パネルを開く）
    _open_decision(page, "D-3")
    page.wait_for_selector("aside.panel .df-note")
    # 検証（今の本文を出し、そのまとまりの差分を出せない旨が出る）
    assert page.inner_text("aside.panel .df-note") == NOTE_TRIMMED
    assert "2 回目に書き換えた本文です。" in page.inner_text("aside.panel .md")
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0


def test_error_when_previous_version_unavailable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文のファイルが手で書き換えられていると、本文の差分を出せない旨を出し、状態の前後は読める（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-3", status="未決定", body="D-3.md"), bodies={"D-3.md": BODY_V0}
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="D-3", item={"status": "要見直し", "body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="検討事項を直す")
    # ツールを通さずに、本文の全ての行を手で書き換える
    (root / RECORD_DIR / "docs" / "D-3.md").write_text(HAND_WRITTEN_BODY, encoding="utf-8")
    open_preview(url, "#tab=decisions&view=table")
    pick_history_point(page, "検討事項を直す")
    # 実行
    _open_decision(page, "D-3")
    page.wait_for_selector("aside.panel .df-note")
    # 検証（今の本文を差分の印なしで描き、本文の差分を出せない旨が出る）
    assert page.inner_text("aside.panel .df-note") == NOTE_BODY_UNAVAILABLE
    assert "手で書いた A" in page.inner_text("aside.panel .md")
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    # 検証（状態の前の値と今の値は、本文と関係なく見分けられる）
    status = page.locator('aside.panel [data-key="status"] .df-kv')
    assert status.locator("del.df-was").inner_text().endswith("未決定")
    assert status.locator("ins.df-now").inner_text().endswith("要見直し")


def test_normal_when_since_history_dropped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """前回開いてからの古い書き換えが消えた D-3 は前後を組み立てられない旨を出し、消えていない D-4 は差分を出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-3", status="未決定", body="D-3.md"),
        make_item("D-4", status="未決定", body="D-4.md"),
        settings={**valid_settings, "history_limit": 1},
        bodies={"D-3.md": BODY_V0, "D-4.md": BODY_V0},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    visit_and_close(page, url)
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="1 回目")
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V2})
    replay("update", workspace=ws, id="D-4", item={"body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="2 回目")
    open_preview(url, "#tab=decisions&view=table")
    # 実行（「前回開いてから」を選ぶ）
    pick_history_point(page, "前回開いてから")
    # 検証（D-3・D-4 に変更の印が付く）
    assert _row_marks(page) == {"D-3": MARK_CHANGED, "D-4": MARK_CHANGED}
    # 実行（D-3 の詳細パネルを開く）
    _open_decision(page, "D-3")
    page.wait_for_selector("aside.panel .df-note")
    # 検証（今の本文を出し、前後を組み立てられない旨が出る。2 回目だけの差分は出ない）
    assert page.inner_text("aside.panel .df-note") == NOTE_TRIMMED
    assert "2 回目に書き換えた本文です。" in page.inner_text("aside.panel .md")
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    # 実行（D-4 の詳細パネルを開く）
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    _open_decision(page, "D-4")
    page.wait_for_selector("aside.panel .md ins.df-blk", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（D-4 の本文の差分が出る）
    added, removed = _block_texts(page)
    assert "1 回目に書き換えた本文です。" in added
    assert "最初の本文です。" in removed
