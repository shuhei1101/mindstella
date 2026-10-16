"""前回からの差分を見る（変更履歴から書き換えのまとまりを選び、印と詳細パネルで差分を読む）の E2E テスト。

モデルを呼ばず、MCP のツールで記録を書き換え、サーバーが配るプレビューを実際のブラウザで開いて確かめる。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from diff_minimap_helpers import (
    FULL_SCOPE,
    MINIMAP_COMMIT_SUMMARY,
    MINIMAP_TIMEOUT_MS,
    MINIMAP_VIEWPORT_WIDTH,
    PANEL_SCOPE,
    added_paragraph_in_view,
    block_kinds,
    build_minimap_workspace,
    mark_shapes,
    wait_added_paragraph_in_view,
)
from playwright.sync_api import Page
from preview_helpers import (
    HISTORY_DIALOG,
    HISTORY_REDRAW_TIMEOUT_MS,
    OpenInEmptyContext,
    OpenPreview,
    pick_history_point,
    snapshot_records,
    visit_and_close,
    wait_past_boundary,
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

# そのタブの「前回開いてから」の始まりの日時を残す sessionStorage のキーと、その値を読む
SINCE_KEY = "mindmap-since"
SINCE_SCRIPT = "key => sessionStorage.getItem(key)"

# 変更の印と新規の印の class
MARK_CHANGED = "df-mark df-chg"
MARK_NEW = "df-mark df-new"

# 消した項目の帯の項目と、取り下げの札
REMOVED_ITEMS = "section.rm-band li.rm-item"
WITHDRAWN_BADGE = ".wd-badge"

# 消した項目を押した後、詳細パネルが開かないことを確かめるまで待つミリ秒
PRESS_SETTLE_MS = 400

# 消した項目の帯の項目（ID・消したときのタイトル）を上から読む
REMOVED_ITEMS_SCRIPT = """items => items.map(
    i => [i.dataset.removedId, i.querySelector('.rm-ttl').textContent]
)"""

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
    "options": [{"key": "A", "content": "案 A"}],
    **PLACE,
}

# 検討事項 D-3 の書き換える前の本文（書き換える段落・変えない段落・消す段落の 3 つと flowchart の図）
BODY_D3_BEFORE = """# 検討メモ

要件は来週までに決める。

残す段落です。

消す段落です。

```mermaid
flowchart TD
  A[開始] --> B[処理]
```
"""

# D-3 の書き換えた後の本文（1 つ目の段落の語を書き換えて 3 つ目の段落を消し、図のノードのラベルを 1 つ変える）
BODY_D3_AFTER = """# 検討メモ

要件は今週までに決める。

残す段落です。

```mermaid
flowchart TD
  A[開始] --> B[処理を変えた]
```
"""

# D-3 の背景の書き換える前と後（書き換える語の前後に変えない語を残す。同じ部分が少ないと語の面が付かない）
LEAD_D3_BEFORE = "要件は来週までに決める。"
LEAD_D3_AFTER = "要件は今週までに決める。"

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


def _decisions(
    make_item: MakeItem, *body_ids: str, leads: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """未決定の検討事項 D-1〜D-5 を返す。`body_ids` の項目だけ本文のファイルを、`leads` の項目だけ背景を持つ。"""
    return [
        make_item(
            f"D-{number}",
            status="未決定",
            **({"body": f"D-{number}.md"} if f"D-{number}" in body_ids else {}),
            **({"lead": (leads or {})[f"D-{number}"]} if f"D-{number}" in (leads or {}) else {}),
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
        *_decisions(make_item, "D-3", leads={"D-3": LEAD_D3_BEFORE}),
        make_item("T-1"),
        bodies={"D-3.md": BODY_D3_BEFORE},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    visit_and_close(page, url, root)
    replay(
        "update",
        workspace=ws,
        id="D-3",
        item={"status": "要見直し", "lead": LEAD_D3_AFTER, "body_markdown": BODY_D3_AFTER},
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
    # 検証（背景の前の値と今の値で、書き換えた語にだけ濃い面が付く。前は消した色、今は足した色で、変えていない語には付かない）
    lead_words = 'aside.panel [data-key="lead"] span.df-word'
    assert page.locator(f"{lead_words}.df-del").all_inner_texts() == ["来週"]
    assert page.locator(f"{lead_words}.df-add").all_inner_texts() == ["今週"]
    assert page.locator(lead_words).count() == 2
    # 検証（本文は Markdown のまま、書き換えた段落に足した印、消した段落に消した印が付き、変えていない段落には付かない）
    assert page.inner_text('aside.panel .md [data-md-level="1"]') == "検討メモ"
    added, removed = _block_texts(page)
    assert "要件は今週までに決める。" in added
    assert "要件は来週までに決める。" in removed
    assert "消す段落です。" in removed
    assert "残す段落です。" in page.inner_text("aside.panel .md:not(.md-value)")
    assert "残す段落です。" not in added + removed
    # 検証（書き換えた語にだけ濃い面が付く。前は消した色、今は足した色で、変えていない語と消した段落には付かない）
    # 図の Raw の差分（隠して先に描いてある）の語の面は含めない。Raw の語の面は、Raw を押した後の確かめが見る
    body_words = "aside.panel .md:not(.md-value) span.df-word:not(figure *)"
    assert page.locator(f"{body_words}.df-del").all_inner_texts() == ["来週"]
    assert page.locator(f"{body_words}.df-add").all_inner_texts() == ["今週"]
    assert page.locator(body_words).count() == 2
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
    # 検証（変えたラベルの語にだけ濃い面が付く。消した行は語を消していないので付かず、足した行は足した語だけ）
    assert raw.locator(".df-line.df-del span.df-word").count() == 0
    assert raw.locator(".df-line.df-add span.df-word.df-add").all_inner_texts() == ["を変えた"]
    assert raw.locator("span.df-word").count() == 1
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
    body = page.inner_text("aside.panel .md:not(.md-value)")
    assert "要件は今週までに決める。" in body
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
    # タブを開いた日時より後の秒に書き換える
    wait_past_boundary(page.evaluate(SINCE_SCRIPT, SINCE_KEY))
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
    committed = replay("commit", workspace=ws, summary="検討事項を直す")
    # 開いた日時より後に書き換えたことにならないよう、まとまりの日時の先の秒に入ってから開く
    wait_past_boundary(committed["at"])
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
    visit_and_close(page, url, root)
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
    assert "1 回目に書き換えた本文です。" in page.inner_text("aside.panel .md:not(.md-value)")


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
    assert "2 回目に書き換えた本文です。" in page.inner_text("aside.panel .md:not(.md-value)")
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
    assert "手で書いた A" in page.inner_text("aside.panel .md:not(.md-value)")
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
    visit_and_close(page, url, root)
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
    assert "2 回目に書き換えた本文です。" in page.inner_text("aside.panel .md:not(.md-value)")
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


def _removed_items(page: Page) -> list[list[str]]:
    """画面の消した項目の帯の項目を、ID・消したときのタイトルで上から返す（帯が無ければ空）。"""
    items: list[list[str]] = page.eval_on_selector_all(REMOVED_ITEMS, REMOVED_ITEMS_SCRIPT)
    return items


def test_normal_when_removed_and_withdrawn(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """変更履歴から選んだまとまりで、消したメモが消した印で出て、取り下げた調査に変更と取り下げの印が付き、詳細パネルで取り下げと理由を読む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("N-1", title="残すメモ", content="同じ中身"),
        make_item("N-2", title="重複したメモ", content="同じ中身"),
        make_item("R-1", title="不要な調査"),
        make_item("R-2", title="続ける調査"),
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("remove", workspace=ws, id="N-2")
    replay("update", workspace=ws, id="R-1", item={"withdrawn": True, "reason": "別の調査で足りた"})
    replay("commit", workspace=ws, summary="重複と不要な調査を片付ける")
    open_preview(url, "#tab=overview")
    # 実行・検証（一覧のまとまりの件数は、変えた R-1 と消した N-2 の 2）
    rows = _read_rows(page)
    assert [row["n"] for row in rows if row["name"] == "重複と不要な調査を片付ける"] == ["2 件"]
    # 実行（まとまりを選ぶ）
    pick_history_point(page, "重複と不要な調査を片付ける")
    # 検証（メモと調査のタブに印が付き、メモのタブの件数は N-1 の 1 件のまま）
    assert _marked_tabs(page) == ["research", "notes"]
    assert page.evaluate(TAB_COUNTS_SCRIPT)["notes"] == "1"
    # 実行（メモの画面を開く）
    page.click('nav.tabbar a[data-tab="notes"]')
    page.wait_for_selector(TABLE_ROWS)
    # 検証（消した N-2 が ID・消したときのタイトルと消した印で出て、N-1 には印が無い）
    assert _removed_items(page) == [["N-2", "重複したメモ"]]
    assert page.locator(f"{REMOVED_ITEMS} .df-mark.df-del").count() == 1
    assert _row_marks(page) == {"N-1": None}
    # 実行（消した N-2 を押す）
    page.locator(REMOVED_ITEMS).click()
    page.wait_for_timeout(PRESS_SETTLE_MS)
    # 検証（詳細パネルは開かない）
    assert page.locator("aside.panel.open").count() == 0
    # 実行（調査の画面を開く）
    page.click('nav.tabbar a[data-tab="research"]')
    page.wait_for_selector(TABLE_ROWS)
    # 検証（R-1 に取り下げの印と変更の印が付き、R-2 には印が無い）
    assert page.locator(
        'table.grid tbody tr[data-id="R-1"] .row-open + .wd-badge + .df-mark.df-chg'
    ).count() == 1
    assert page.locator('table.grid tbody tr[data-id="R-2"] .df-mark, table.grid tbody tr[data-id="R-2"] .wd-badge').count() == 0
    # 実行（R-1 を押す）
    page.click('table.grid button.row-open[data-id="R-1"]')
    page.wait_for_selector("aside.panel.open .d-title")
    # 検証（取り下げの印と理由が出て、キーの差分で取り下げと理由が足した印で出る）
    assert page.locator(f"aside.panel .d-title {WITHDRAWN_BADGE}").inner_text() == "取り下げ"
    assert page.locator('aside.panel [data-key="reason"] ins.df-now').inner_text().endswith(
        "別の調査で足りた"
    )
    assert page.locator(f"aside.panel .d-meta dd.df-key ins.df-now {WITHDRAWN_BADGE}").count() == 1
    # 実行（差分の表示から抜ける）
    page.get_by_role("button", name="差分の表示をやめる").click()
    page.wait_for_selector(".df-chip", state="detached", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    # 検証（R-1 の変更の印は消え、取り下げの印は残る）
    assert page.locator(".df-mark").count() == 0
    assert page.locator(f'table.grid tbody tr[data-id="R-1"] {WITHDRAWN_BADGE}').count() == 1
    # 実行（メモの画面を開く）
    page.click('nav.tabbar a[data-tab="notes"]')
    page.wait_for_selector(TABLE_ROWS)
    # 検証（N-2 は画面から消える）
    assert _removed_items(page) == []


def test_normal_when_added_then_removed_since(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """「前回開いてから」の範囲で足して消したメモは、新規ではなく消した項目として出る（正常系）。"""
    # 準備
    root = make_workspace(make_item("N-1", title="残すメモ"))
    ws = str(root)
    url = _serve(call_tool, root)
    visit_and_close(page, url, root)
    replay("add", workspace=ws, kind="note", item={"title": "足すメモ", "content": "メモ"})
    replay("commit", workspace=ws, summary="メモを足す")
    replay("remove", workspace=ws, id="N-2")
    replay("commit", workspace=ws, summary="足したメモを消す")
    open_preview(url, "#tab=notes")
    # 実行・検証（「前回開いてから」の件数は、消した N-2 の 1）
    rows = _read_rows(page)
    assert [row["n"] for row in rows if row["sel"] == "since"] == ["1 件"]
    # 実行（「前回開いてから」を選ぶ）
    pick_history_point(page, "前回開いてから")
    page.wait_for_selector(TABLE_ROWS)
    # 検証（N-2 が消した印で出て、新規の印の付いた項目は無く、N-1 にも印が無い）
    assert _removed_items(page) == [["N-2", "足すメモ"]]
    assert page.locator(f"{REMOVED_ITEMS} .df-mark.df-del").count() == 1
    assert page.locator(".df-mark.df-new").count() == 0
    assert _row_marks(page) == {"N-1": None}


# 段落 3 つを 1 行ずつ持つ HTML の本文と、2 つ目の段落を書き換えた本文
HTML_BODY_BEFORE = "<p>1 つ目の段落</p>\n<p>2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"
HTML_BODY_AFTER = "<p>1 つ目の段落</p>\n<p>書き直した 2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"

# 詳細パネルの HTML の本文の枠と、差分の表示の間に描いた結果を入れる枠
HTML_BODY_FRAME = "aside.panel iframe.html-frame[data-html-body]"
HTML_MARKED_FRAME = "aside.panel .html-marked iframe.html-frame"

# 枠の描き終わり・高さ合わせが済むまで待つミリ秒
FRAME_SETTLE_MS = 400

# 段落の文と、その段落が持つ（または含まれる）差分の印の種類を返す
PARAGRAPH_MARKS_SCRIPT = "ps => ps.map(p => [p.textContent, p.closest('[data-df]')?.dataset.df ?? null])"


def _wait_frame_rendered(page: Page, selector: str) -> None:
    """枠が描き終わり、高さ合わせが済むまで待つ。"""
    page.wait_for_selector(f"{selector}[data-rendered]", state="attached", timeout=DIAGRAM_TIMEOUT_MS)
    page.wait_for_timeout(FRAME_SETTLE_MS)


def test_normal_when_html_body_changed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """HTML の本文の 2 つ目の段落を書き換えると、描いた本文の上で変わった段落に印を付け、「原文の差分」で原文の行の差分に切り替える（正常系）。"""
    # 準備（本文を HTML で持ち、段落 3 つを 1 行ずつ持つ資料 A-1 の、2 つ目の段落を書き換えて 1 つのまとまりにする）
    root = make_workspace(make_item("A-1", body="A-1.html"), bodies={"A-1.html": HTML_BODY_BEFORE})
    ws = str(root)
    url = _serve(call_tool, root)
    visit_and_close(page, url, root)
    replay("update", workspace=ws, id="A-1", item={"body_html": HTML_BODY_AFTER})
    replay("commit", workspace=ws, summary="段落を書き直す")
    before = snapshot_records(snapshot_tree(root))
    # 実行（変更履歴から書き換えのまとまりを選ぶ）
    open_preview(url, "#tab=overview")
    pick_history_point(page, "前回開いてから")
    # 検証（資料のタブに印が付き、A-1 に変更の印が付く）
    assert _marked_tabs(page) == ["docs"]
    page.click('nav.tabbar a[data-tab="docs"]')
    page.wait_for_selector(".doc-card")
    assert page.locator('.doc-card[data-id="A-1"] .df-mark.df-chg').count() == 1
    # 実行（資料のタブで A-1 を押す）
    page.click('.doc-card[data-id="A-1"]')
    _wait_frame_rendered(page, HTML_MARKED_FRAME)
    # 検証（描いた本文の上で、書き換えた 2 つ目の段落だけに変更の印が付く）
    marked = page.frame_locator(HTML_MARKED_FRAME).locator("p").evaluate_all(PARAGRAPH_MARKS_SCRIPT)
    assert marked == [
        ["1 つ目の段落", None],
        ["書き直した 2 つ目の段落", "chg"],
        ["3 つ目の段落", None],
    ]
    # 実行（「原文の差分」に切り替える）
    page.get_by_role("button", name="原文の差分").click()
    # 検証（2 つ目の段落の原文の行が、消した行と足した行で出る）
    removed = page.inner_text("aside.panel .df-raw .df-line.df-del")
    added = page.inner_text("aside.panel .df-raw .df-line.df-add")
    assert "<p>2 つ目の段落</p>" in removed
    assert "<p>書き直した 2 つ目の段落</p>" in added
    # 実行（差分の表示から抜ける）
    page.get_by_role("button", name="差分の表示をやめる").click()
    _wait_frame_rendered(page, HTML_BODY_FRAME)
    # 検証（A-1 の本文は、今の HTML を描いた結果だけになる）
    now = page.frame_locator(HTML_BODY_FRAME)
    assert now.locator("[data-df]").count() == 0
    assert now.locator("p").all_inner_texts() == [
        "1 つ目の段落",
        "書き直した 2 つ目の段落",
        "3 つ目の段落",
    ]
    assert page.locator("aside.panel .html-marked").count() == 0
    # ワークスペースの YAML と本文の中身が、開く前と同じ
    assert snapshot_records(snapshot_tree(root)) == before


def _hash_params(url: str) -> dict[str, list[str]]:
    """URL のハッシュを、キー → 値の並びで返す。"""
    return parse_qs(urlsplit(url).fragment)


def test_normal_when_opened_with_change_set_url(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    open_in_empty_context: OpenInEmptyContext,
    page: Page,
) -> None:
    """選んだまとまりが URL に残り、端末の保存領域が空のブラウザでその URL を開くと同じ差分の表示で開く（正常系）。"""
    # 準備（A-1 を直した V-1 と、D-3 を直した V-2）
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
    history_before = page.evaluate("history.length")
    # 実行（「仕様書を直す」を選ぶ）
    pick_history_point(page, "仕様書を直す")
    page.wait_for_function("location.hash.includes('diff=V-1')", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    # 検証（URL のハッシュが V-1 を持ち、履歴の数が増えていない）
    assert _hash_params(page.url)["diff"] == ["V-1"]
    assert page.evaluate("history.length") == history_before
    # 実行（端末の保存領域が空のブラウザで同じ URL を開く）
    opened = open_in_empty_context(page.url)
    opened.wait_for_selector(".df-chip", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    # 検証（「仕様書を直す」の札が出て、資料のタブと A-1 に印が付き、検討事項のタブには付かない）
    assert opened.inner_text(".df-chip-t").endswith("仕様書を直す")
    assert _marked_tabs(opened) == ["docs"]
    assert opened.locator('.doc-card[data-id="A-1"] .df-mark').get_attribute("class") == MARK_CHANGED
    # 実行（A-1 の詳細パネルを開く）
    opened.click('.doc-card[data-id="A-1"]')
    opened.wait_for_selector("aside.panel.open .d-title")
    # 検証（そのまとまりの前後の本文の足した・消した印が出る）
    added, removed = _block_texts(opened)
    assert "直した後の仕様です。" in added
    assert "直す前の仕様です。" in removed
    # 実行（検討事項の表を開く）
    opened.click('nav.tabbar a[data-tab="decisions"]')
    opened.click('.segment button[data-view="table"]')
    opened.wait_for_selector(TABLE_ROWS)
    # 検証（D-3 には印が付かない）
    assert _row_marks(opened) == {"D-3": None}
    # 実行（「差分を出さない（今の内容）」を選ぶ）
    opened.get_by_role("button", name="変更履歴").click()
    opened.wait_for_selector(f"{HISTORY_DIALOG}[open]")
    opened.locator("dialog.hist .hist-item[data-sel='']").click()
    opened.wait_for_selector(".df-chip", state="detached", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    # 検証（印が消え、URL のハッシュが時点を持たない）
    assert opened.locator(".df-mark").count() == 0
    assert opened.locator("nav.tabbar .df-dot").count() == 0
    assert "diff" not in _hash_params(opened.url)


def test_normal_when_url_points_missing_change_set(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_in_empty_context: OpenInEmptyContext,
) -> None:
    """記録に無いまとまりを指す URL では、差分を出さずに開き、URL のハッシュから時点を外す（正常系）。"""
    # 準備（まとまり V-1 だけを持つ）
    root = make_workspace(make_item("D-3", status="未決定", body="D-3.md"), bodies={"D-3.md": BODY_V0})
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_V1})
    replay("commit", workspace=ws, summary="検討事項を直す")
    # 実行（記録に無い V-99 を指す URL を、端末の保存領域が空のブラウザで開く）
    opened = open_in_empty_context(f"{url}#tab=decisions&view=table&diff=V-99")
    opened.wait_for_selector(TABLE_ROWS)
    opened.wait_for_function("!location.hash.includes('diff=')", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    # 検証（選んだ時点の札が無く、どのタブにも D-3 にも印が付かない）
    assert opened.locator(".df-chip").count() == 0
    assert opened.locator("nav.tabbar .df-dot").count() == 0
    assert _row_marks(opened) == {"D-3": None}
    # 検証（URL のハッシュが時点を持たない）
    assert "diff" not in _hash_params(opened.url)


# 本文のまとまりのリンクを持つ検討事項 D-3 の本文（リンクを頭に置き、見出し「決め方」を本文のスクロール領域の外に置く）
BODY_WITH_CHANGE_SET_LINKS = (
    "# 検討メモ\n\n"
    "[仕様書を直したところ](#diff=V-1)\n\n"
    "[決め方へ](#決め方)\n\n"
    + "\n\n".join(f"先頭の段落 {number}" for number in range(1, 41))
    + "\n\n## 決め方\n\n決め方の段落\n"
)

# まとまりを指さない値のリンクを持つ検討事項 D-3 の本文（V-99 は記録に無い）
BODY_WITH_MISSING_LINKS = (
    "# 検討メモ\n\n"
    "[古い直し](#diff=V-99)\n\n"
    "[前回から](#diff=since)\n\n"
    "[まとめる前](#diff=pending)\n"
)

# 見出しが詳細パネルの本文のスクロール領域の中で画面に入っているかを返す
HEADING_IN_VIEW_SCRIPT = """(slug) => {
    const area = document.querySelector('aside.panel .panel-body').getBoundingClientRect();
    const box = document.querySelector(`[data-heading="${slug}"]`).getBoundingClientRect();
    return box.top >= area.top - 1 && box.bottom <= area.bottom + 1;
}"""


def test_normal_when_body_link_to_change_set(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文の #diff= のリンクを押すと、開いた項目のままそのまとまりの差分の表示に切り替わり、見出しのリンクはその見出しまで送る（正常系）。"""
    # 準備（A-1 を直した V-1 と、D-3 の本文にリンクを書き足した V-2）
    root = make_workspace(
        make_item("A-1", status="完成", kind="仕様書"),
        make_item("D-3", status="未決定", body="D-3.md"),
        bodies={"A-1.md": BODY_A1_BEFORE, "D-3.md": BODY_V0},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="A-1", item={"body_markdown": BODY_A1_AFTER})
    replay("commit", workspace=ws, summary="仕様書を直す")
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_WITH_CHANGE_SET_LINKS})
    replay("commit", workspace=ws, summary="検討事項を直す")
    # 実行（差分を出さずに D-3 の詳細パネルを開き、「仕様書を直したところ」を押す）
    open_preview(url, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel.open .md a")
    assert page.locator(".df-chip").count() == 0
    history_before = page.evaluate("history.length")
    page.locator("aside.panel .md a", has_text="仕様書を直したところ").click()
    page.wait_for_selector(".df-chip", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    # 検証（「仕様書を直す」の札が出て、資料のタブに印が付き、検討事項のタブには付かない）
    assert page.inner_text(".df-chip-t").endswith("仕様書を直す")
    assert _marked_tabs(page) == ["docs"]
    # 検証（D-3 の詳細パネルが開いたままで、URL のハッシュが id=D-3 と diff=V-1 を持ち、履歴の数が増えていない）
    assert page.locator("aside.panel.open").count() == 1
    assert _hash_params(page.url)["id"] == ["D-3"]
    assert _hash_params(page.url)["diff"] == ["V-1"]
    assert page.evaluate("history.length") == history_before
    # 実行（「決め方へ」を押す）
    assert page.evaluate(HEADING_IN_VIEW_SCRIPT, "決め方") is False
    page.locator("aside.panel .md a", has_text="決め方へ").click()
    page.wait_for_function(
        "new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'",
        timeout=HISTORY_REDRAW_TIMEOUT_MS,
    )
    # 検証（本文が「決め方」の見出しまで送られ、h が「決め方」になり、選んだ時点は V-1 のまま）
    assert page.evaluate(HEADING_IN_VIEW_SCRIPT, "決め方") is True
    assert _hash_params(page.url)["h"] == ["決め方"]
    assert _hash_params(page.url)["diff"] == ["V-1"]
    assert page.evaluate("history.length") == history_before


def test_normal_when_body_link_not_to_change_set(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文のリンクが記録に無いまとまり・前回から・まとめる前を指すときは、押しても差分の表示を変えない（正常系）。"""
    # 準備（D-3 の本文にリンクを書き足した V-1 だけを持つ）
    root = make_workspace(make_item("D-3", status="未決定", body="D-3.md"), bodies={"D-3.md": BODY_V0})
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="D-3", item={"body_markdown": BODY_WITH_MISSING_LINKS})
    replay("commit", workspace=ws, summary="検討事項を直す")
    # 実行（V-1 を持つ URL で D-3 の詳細パネルを開く）
    open_preview(url, "#tab=decisions&view=table&id=D-3&diff=V-1")
    page.wait_for_selector(".df-chip", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    page.wait_for_selector("aside.panel.open .md a")
    history_before = page.evaluate("history.length")
    for text in ("古い直し", "前回から", "まとめる前"):
        page.locator("aside.panel .md a", has_text=text).click()
        page.wait_for_timeout(PRESS_SETTLE_MS)
        # 検証（札が「検討事項を直す」のままで、D-3 に変更の印が付いたまま）
        assert page.inner_text(".df-chip-t").endswith("検討事項を直す")
        assert _row_marks(page) == {"D-3": MARK_CHANGED}
        # 検証（URL のハッシュが diff=V-1 を持ち、h を持たず、履歴の数が増えていない）
        assert _hash_params(page.url)["diff"] == ["V-1"]
        assert "h" not in _hash_params(page.url)
        assert page.evaluate("history.length") == history_before


def test_normal_when_minimap_jump(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """差分の表示で長い資料の詳細を開くと変わった箇所の印を並べたミニマップが出て、印を押すとその箇所まで本文が送られ、全画面にも同じミニマップが出て、差分の表示から抜けると消える（正常系）。"""
    # 準備（本文に段落を 40 個持つ A-1 の 1 つ目の段落を消し、末尾に段落を足した V-1）
    root = build_minimap_workspace(make_workspace, make_item, call_tool)
    url = _serve(call_tool, root)
    open_preview(url, "#tab=docs", width=MINIMAP_VIEWPORT_WIDTH)
    pick_history_point(page, MINIMAP_COMMIT_SUMMARY)
    # 実行（資料のタブで A-2 を押す）
    page.click('.doc-card[data-id="A-2"]')
    page.wait_for_function(
        f"document.querySelector('{PANEL_SCOPE} .d-title')?.textContent.includes('A-2')"
    )
    # 検証（変わっていない A-2 にはミニマップが見えない）
    assert not page.locator(f"{PANEL_SCOPE} .df-map").is_visible()
    # 実行（資料のタブで A-1 を押す）
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector(f"{PANEL_SCOPE} .df-map .df-map-m", timeout=MINIMAP_TIMEOUT_MS)
    shapes = mark_shapes(page, PANEL_SCOPE)
    # 検証（消した段落と足した段落の印が、本文の中のその箇所と同じ上下の順で並び、形が違い、足した段落は見える範囲の外にある）
    assert block_kinds(page, PANEL_SCOPE) == ["del", "ins"]
    assert [shape["kind"] for shape in shapes] == ["df-del", "df-add"]
    assert shapes[0]["top"] < shapes[1]["top"]
    assert shapes[0]["border"] == "2px"
    assert shapes[1]["border"] == "0px"
    assert shapes[0]["fill"] != shapes[1]["fill"]
    assert not added_paragraph_in_view(page, PANEL_SCOPE)
    # 実行（ミニマップの下の印を押す）
    hash_before = page.evaluate("location.hash")
    page.locator(f"{PANEL_SCOPE} .df-map .df-map-m").nth(1).click()
    wait_added_paragraph_in_view(page, PANEL_SCOPE)
    # 検証（足した段落が見える範囲に入り、URL のハッシュは変わらない）
    assert added_paragraph_in_view(page, PANEL_SCOPE)
    assert page.evaluate("location.hash") == hash_before
    # 実行（全画面表示を押す）
    page.locator(PANEL_SCOPE).get_by_role("button", name="全画面表示").click()
    page.wait_for_selector(f"{FULL_SCOPE}[open] .df-map .df-map-m", timeout=MINIMAP_TIMEOUT_MS)
    # 検証（全画面にも消した段落と足した段落の印を並べたミニマップが出る）
    assert [shape["kind"] for shape in mark_shapes(page, FULL_SCOPE)] == ["df-del", "df-add"]
    # 実行（全画面は他の操作を受けないため元の大きさに戻してから、差分の表示から抜ける）
    page.locator(FULL_SCOPE).get_by_role("button", name="元の大きさに戻す").click()
    page.wait_for_selector(FULL_SCOPE, state="hidden")
    page.get_by_role("button", name="変更履歴").click()
    page.wait_for_selector(f"{HISTORY_DIALOG}[open]")
    page.locator("dialog.hist .hist-item[data-sel='']").click()
    page.wait_for_selector(".df-chip", state="detached", timeout=HISTORY_REDRAW_TIMEOUT_MS)
    # 検証（ミニマップが消える）
    page.wait_for_selector(f"{PANEL_SCOPE} .df-map", state="detached", timeout=MINIMAP_TIMEOUT_MS)
    assert page.locator(".df-map").count() == 0


# 本文を左右に並べるシナリオの値: 資料 A-1 の本文の書き換える前と後（1 つ目の段落を消して、末尾に段落を足す）
SIDE_BODY_A1_BEFORE = "1 つ目の段落です。\n\n2 つ目の段落です。\n\n3 つ目の段落です。\n"
SIDE_BODY_A1_AFTER = "2 つ目の段落です。\n\n3 つ目の段落です。\n\n4 つ目の段落です。\n"

# 詳細パネルで左右に並べるシナリオの値: 資料 A-1 の本文の書き換える前と後（2 つ目の段落を書き換える）
SIDE_PANEL_A1_BEFORE = "1 つ目の段落です。\n\n2 つ目の段落は、前の案です。\n\n3 つ目の段落です。\n"
SIDE_PANEL_A1_AFTER = "1 つ目の段落です。\n\n2 つ目の段落は、今の案です。\n\n3 つ目の段落です。\n"

# 検討事項 D-1 の本文の書き換える前と後（2 つ目の段落を書き換える）
SIDE_BODY_D1_BEFORE = "1 つ目の段落です。\n\n2 つ目の段落は、来週に決めます。\n\n3 つ目の段落です。\n"
SIDE_BODY_D1_AFTER = "1 つ目の段落です。\n\n2 つ目の段落は、今週に決めます。\n\n3 つ目の段落です。\n"

# 資料の詳細パネルの本文が 560px 以上になる画面の幅
SIDE_VIEWPORT_WIDTH = 1280

# 書き換えのまとまりの説明
SIDE_COMMIT_SUMMARY = "段落を直す"

# 切り替えのボタンの組と、左右に並べた本文、その左右の列（選んだ時点・今）
SWITCH = ".sbs-switch"
SIDE_BEFORE = ".sbs section.sbs-before"
SIDE_AFTER = ".sbs section.sbs-after"

# 切り替えのボタンごとに、並べ方と押している状態を返す
SWITCH_STATE_SCRIPT = """scope => [...document.querySelectorAll(`${scope} .sbs-switch button`)].map(
    button => [button.getAttribute('data-layout'), button.getAttribute('aria-pressed')]
)"""

# 左右の列ごとに、直下の行の上端の位置と、変えた行か、を返す
SIDE_ROWS_SCRIPT = """scope => [...document.querySelectorAll(`${scope} .sbs .sbs-col`)].map(
    column => [...column.querySelectorAll(':scope > .sbs-row')].map(
        row => [row.getBoundingClientRect().top, row.classList.contains('sbs-chg'), row.textContent.trim()]
    )
)"""

# 端末の保存領域の個人の上書きを読む
SAVED_PREFS_SCRIPT = "JSON.parse(localStorage.getItem('mindmap-preview') || 'null')"


def _switch_state(page: Page, scope: str) -> list[list[str]]:
    """切り替えの 2 つのボタンを、並べ方と押している状態の組で返す。"""
    state: list[list[str]] = page.evaluate(SWITCH_STATE_SCRIPT, scope)
    return state


def _wait_side_by_side(page: Page, scope: str) -> None:
    """左右に並べた本文が置かれるまで待つ。"""
    page.wait_for_selector(f"{scope} .sbs", timeout=DIAGRAM_TIMEOUT_MS)


def test_normal_when_side_by_side(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """全画面で「左右に並べる」を押すと本文の差分を左右に並べ、HTML の本文でも前後の描いた結果を左右に並べ、「インライン」を押すと今までの表示に戻る（正常系）。"""
    # 準備（Markdown の A-1 の 1 つ目の段落を消して末尾に段落を足し、HTML の A-2 の 2 つ目の段落を書き換えて 1 つのまとまりにする）
    root = make_workspace(
        make_item("A-1"),
        make_item("A-2", body="A-2.html"),
        bodies={"A-1.md": SIDE_BODY_A1_BEFORE, "A-2.html": HTML_BODY_BEFORE},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="A-1", item={"body_markdown": SIDE_BODY_A1_AFTER})
    replay("update", workspace=ws, id="A-2", item={"body_html": HTML_BODY_AFTER})
    replay("commit", workspace=ws, summary=SIDE_COMMIT_SUMMARY)
    before = snapshot_records(snapshot_tree(root))
    open_preview(url, "#tab=docs", width=SIDE_VIEWPORT_WIDTH)
    pick_history_point(page, SIDE_COMMIT_SUMMARY)
    # 実行（資料のタブで A-1 を押し、全画面表示を押す）
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector(f"{PANEL_SCOPE}.open {SWITCH}")
    page.locator(PANEL_SCOPE).get_by_role("button", name="全画面表示").click()
    page.wait_for_selector(f"{FULL_SCOPE}[open] {SWITCH}")
    hash_before = page.evaluate("location.hash")
    # 検証（本文の差分がインラインで出て、切り替えは「インライン」を押した状態）
    assert _switch_state(page, FULL_SCOPE) == [["inline", "true"], ["side", "false"]]
    assert page.locator(f"{FULL_SCOPE} .md:not(.md-value) del.df-blk").count() == 1
    assert page.locator(f"{FULL_SCOPE} .md:not(.md-value) ins.df-blk").count() == 1
    assert page.locator(f"{FULL_SCOPE} .sbs").is_visible() is False
    # 実行（「左右に並べる」を押す）
    page.locator(FULL_SCOPE).get_by_role("button", name="左右に並べる").click()
    _wait_side_by_side(page, FULL_SCOPE)
    # 検証（左に消した 1 つ目の段落、右に足した段落。変えていない 2 つ目・3 つ目の段落は左右の同じ高さに印なしで並ぶ）
    assert "1 つ目の段落です。" in page.inner_text(f"{FULL_SCOPE} {SIDE_BEFORE} del.df-blk")
    assert "4 つ目の段落です。" in page.inner_text(f"{FULL_SCOPE} {SIDE_AFTER} ins.df-blk")
    left, right = page.evaluate(SIDE_ROWS_SCRIPT, FULL_SCOPE)
    assert [row[0] for row in left] == [row[0] for row in right]
    assert [row[1] for row in left] == [True, False, False, True]
    assert [row[2] for row in left[1:3]] == ["2 つ目の段落です。", "3 つ目の段落です。"]
    assert _switch_state(page, FULL_SCOPE) == [["inline", "false"], ["side", "true"]]
    # 検証（左右に並べている間も、URL のハッシュは変わらない）
    assert page.evaluate("location.hash") == hash_before
    # 実行（元の大きさに戻し、資料のタブで A-2 を押し、全画面表示を押す）
    page.locator(FULL_SCOPE).get_by_role("button", name="元の大きさに戻す").click()
    page.wait_for_selector(FULL_SCOPE, state="hidden")
    page.click('.doc-card[data-id="A-2"]')
    page.wait_for_function(
        f"document.querySelector('{PANEL_SCOPE} .d-title')?.textContent.includes('A-2')"
    )
    page.locator(PANEL_SCOPE).get_by_role("button", name="全画面表示").click()
    page.wait_for_selector(f"{FULL_SCOPE}[open] .sbs-html")
    _wait_frame_rendered(page, f"{FULL_SCOPE} .sbs-after iframe.html-frame")
    _wait_frame_rendered(page, f"{FULL_SCOPE} .sbs-before iframe.html-frame")
    # 検証（切り替えは A-1 で選んだ「左右に並べる」を押した状態のまま。左に選んだ時点、右に今の描いた結果で、右の書き換えた 2 つ目の段落に変更の印が付く）
    assert _switch_state(page, FULL_SCOPE) == [["inline", "false"], ["side", "true"]]
    assert page.frame_locator(f"{FULL_SCOPE} .sbs-before iframe.html-frame").locator("p").all_inner_texts() == [
        "1 つ目の段落",
        "2 つ目の段落",
        "3 つ目の段落",
    ]
    marked = page.frame_locator(f"{FULL_SCOPE} .sbs-after iframe.html-frame").locator("p").evaluate_all(
        PARAGRAPH_MARKS_SCRIPT
    )
    assert marked == [
        ["1 つ目の段落", None],
        ["書き直した 2 つ目の段落", "chg"],
        ["3 つ目の段落", None],
    ]
    # 実行（「インライン」を押す）
    page.locator(FULL_SCOPE).get_by_role("button", name="インライン").click()
    page.wait_for_selector(f"{FULL_SCOPE} .sbs-html", state="detached")
    _wait_frame_rendered(page, f"{FULL_SCOPE} .html-marked iframe.html-frame")
    # 検証（A-2 の本文は、描いた本文の上で変わった段落に印を付けた今までの表示に戻る）
    marked = page.frame_locator(f"{FULL_SCOPE} .html-marked iframe.html-frame").locator("p").evaluate_all(
        PARAGRAPH_MARKS_SCRIPT
    )
    assert marked == [
        ["1 つ目の段落", None],
        ["書き直した 2 つ目の段落", "chg"],
        ["3 つ目の段落", None],
    ]
    # 実行（元の大きさに戻し、差分の表示から抜ける）
    page.locator(FULL_SCOPE).get_by_role("button", name="元の大きさに戻す").click()
    page.wait_for_selector(FULL_SCOPE, state="hidden")
    page.get_by_role("button", name="差分の表示をやめる").click()
    _wait_frame_rendered(page, HTML_BODY_FRAME)
    # 検証（切り替えは消え、A-2 の本文は今の内容を描いた結果だけになる）
    assert page.locator(f"{PANEL_SCOPE} {SWITCH}").count() == 0
    assert page.frame_locator(HTML_BODY_FRAME).locator("p").all_inner_texts() == [
        "1 つ目の段落",
        "書き直した 2 つ目の段落",
        "3 つ目の段落",
    ]
    # ワークスペースの YAML と本文の中身が、開く前と同じ
    assert snapshot_records(snapshot_tree(root)) == before


def test_normal_when_side_by_side_in_panel(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    replay: Replay,
    open_preview: OpenPreview,
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """幅の足りる資料の詳細パネルで「左右に並べる」を押すと上書きを残し、幅の足りない検討事項の詳細パネルでは切り替えを出さず、その全画面では上書きに従って左右に並べ、読み込み直しても保つ（正常系）。"""
    # 準備（Markdown の A-1 と D-1 の 2 つ目の段落をそれぞれ書き換えて 1 つのまとまりにする）
    root = make_workspace(
        make_item("A-1"),
        make_item("D-1", body="D-1.md"),
        bodies={"A-1.md": SIDE_PANEL_A1_BEFORE, "D-1.md": SIDE_BODY_D1_BEFORE},
    )
    ws = str(root)
    url = _serve(call_tool, root)
    replay("update", workspace=ws, id="A-1", item={"body_markdown": SIDE_PANEL_A1_AFTER})
    replay("update", workspace=ws, id="D-1", item={"body_markdown": SIDE_BODY_D1_AFTER})
    replay("commit", workspace=ws, summary=SIDE_COMMIT_SUMMARY)
    before = snapshot_records(snapshot_tree(root))
    open_preview(url, "#tab=docs", width=SIDE_VIEWPORT_WIDTH)
    pick_history_point(page, SIDE_COMMIT_SUMMARY)
    # 実行（資料のタブで A-1 を押す）
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector(f"{PANEL_SCOPE}.open {SWITCH}")
    # 検証（本文の差分がインラインで出て、切り替えは「インライン」を押した状態）
    assert _switch_state(page, PANEL_SCOPE) == [["inline", "true"], ["side", "false"]]
    assert page.locator(f"{PANEL_SCOPE} .sbs").is_visible() is False
    # 実行（「左右に並べる」を押す）
    page.locator(PANEL_SCOPE).get_by_role("button", name="左右に並べる").click()
    _wait_side_by_side(page, PANEL_SCOPE)
    # 検証（詳細パネルの中で、書き換えた 2 つ目の段落が左に消した印つき、右に足した印つきで同じ高さに並ぶ。端末の保存領域に上書きが残る）
    assert "前の案です" in page.inner_text(f"{PANEL_SCOPE} {SIDE_BEFORE} del.df-blk")
    assert "今の案です" in page.inner_text(f"{PANEL_SCOPE} {SIDE_AFTER} ins.df-blk")
    left, right = page.evaluate(SIDE_ROWS_SCRIPT, PANEL_SCOPE)
    assert [row[0] for row in left] == [row[0] for row in right]
    assert [row[1] for row in left] == [False, True, False]
    prefs = page.evaluate(SAVED_PREFS_SCRIPT)
    assert prefs["bodyLayout"] == "side"
    # 実行（検討事項のタブで D-1 を押す）
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.click('.segment button[data-view="table"]')
    _open_decision(page, "D-1")
    page.wait_for_selector(f"{PANEL_SCOPE} .md:not(.md-value) ins.df-blk:visible")
    # 検証（切り替えが無く、本文の差分はインラインで出る）
    assert page.locator(f"{PANEL_SCOPE} {SWITCH}").is_visible() is False
    assert page.locator(f"{PANEL_SCOPE} .sbs").is_visible() is False
    assert "来週に決めます" in page.inner_text(f"{PANEL_SCOPE} .md:not(.md-value) del.df-blk:visible")
    assert "今週に決めます" in page.inner_text(f"{PANEL_SCOPE} .md:not(.md-value) ins.df-blk:visible")
    # 実行（全画面表示を押す）
    page.locator(PANEL_SCOPE).get_by_role("button", name="全画面表示").click()
    page.wait_for_selector(f"{FULL_SCOPE}[open] .sbs", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（切り替えは「左右に並べる」を押した状態で、本文の差分が左右に並ぶ）
    assert _switch_state(page, FULL_SCOPE) == [["inline", "false"], ["side", "true"]]
    assert "来週に決めます" in page.inner_text(f"{FULL_SCOPE} {SIDE_BEFORE} del.df-blk")
    assert "今週に決めます" in page.inner_text(f"{FULL_SCOPE} {SIDE_AFTER} ins.df-blk")
    # 実行（画面を読み込み直す）
    page.reload()
    page.wait_for_selector(f"{FULL_SCOPE}[open] .sbs", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（読み込み直した後も、D-1 の詳細の全画面で本文の差分が左右に並ぶ）
    assert "来週に決めます" in page.inner_text(f"{FULL_SCOPE} {SIDE_BEFORE} del.df-blk")
    assert "今週に決めます" in page.inner_text(f"{FULL_SCOPE} {SIDE_AFTER} ins.df-blk")
    # ワークスペースの YAML と本文の中身が、開く前と同じ
    assert snapshot_records(snapshot_tree(root)) == before
