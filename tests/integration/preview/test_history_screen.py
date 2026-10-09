"""画面設計『変更履歴』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_drawer_helpers import ALL_DECISION_STATUSES_HASH
from preview_fixture_types import OpenPreview, WriteReviewPreview
from preview_history_helpers import preselect_diff
from workspace_fixtures import CallTool

# 変更履歴のモーダルと、時点の行
DIALOG = "dialog.hist"
ROW = f"{DIALOG} .hist-item"

# 時点を選んだ後に描き直るのを待つ上限ミリ秒
REDRAW_TIMEOUT_MS = 10_000

# 端末の保存領域に残した選んだ時点を読む
SAVED_SEL_JS = "JSON.parse(localStorage.getItem('mindmap-preview') || '{}').diffSel ?? null"

# モーダルの行の時点の識別子・名前・件数を上から読む
ROWS_JS = """() => [...document.querySelectorAll('dialog.hist .hist-item')].map(row => ({
    sel: row.dataset.sel,
    name: row.querySelector('.hist-name').textContent,
    sub: row.querySelector('.hist-sub').textContent,
    n: row.querySelector('.hist-n')?.textContent ?? null,
    current: row.getAttribute('aria-current'),
}))"""


def _open_dialog(page: Page) -> None:
    """トップバーの「変更履歴」を押して、モーダルが開くのを待つ。"""
    page.get_by_role("button", name="変更履歴").click()
    page.wait_for_selector(f"{DIALOG}[open]")


def test_list(write_history_preview: WriteReviewPreview, open_preview: OpenPreview) -> None:
    """時点を、差分を出さない・まだまとめていない変更・前回開いてから・まとまりの順に、日時と件数つきで並べる（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    _open_dialog(page)
    # 検証
    rows = page.evaluate(ROWS_JS)
    assert [row["sel"] for row in rows] == ["", "pending", "since", "V-2", "V-1"]
    assert [row["name"] for row in rows] == [
        "差分を出さない（今の内容）",
        "まだまとめていない変更",
        "前回開いてから",
        "決める",
        "最初の書き込み",
    ]
    # まとまりの日時は JST。件数は足した項目と変えた項目の数
    assert rows[3]["sub"] == "10/02 09:00"
    assert rows[4]["sub"] == "10/01 09:00"
    assert rows[2]["sub"] == "10/01 21:00 より後"
    assert [row["n"] for row in rows] == [None, "3 件", "5 件", "3 件", "4 件"]
    # 差分を出していない間は、先頭の行を選んでいる
    assert [row["current"] for row in rows] == ["true", None, None, None, None]
    assert page.evaluate("document.activeElement.dataset.sel") == ""


def test_list_when_no_pending(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """まだまとめていない変更が無いと、その行を出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview(pending=False)
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    _open_dialog(page)
    # 検証
    assert [row["sel"] for row in page.evaluate(ROWS_JS)] == ["", "since", "V-2", "V-1"]


def test_pick(write_history_preview: WriteReviewPreview, open_preview: OpenPreview) -> None:
    """行を押すとモーダルを閉じ、どの画面もその時点の差分の表示で描き直し、選んだ時点を端末に残す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    # 決定済みの D-1 も出すため、全ての状態を選んで開く
    page = open_preview(url, f"#tab=decisions&view=table{ALL_DECISION_STATUSES_HASH}")
    _open_dialog(page)
    # 実行
    page.click(f"{ROW}[data-sel='V-2']")
    # 検証
    page.wait_for_selector(".df-chip", timeout=REDRAW_TIMEOUT_MS)
    assert page.locator(f"{DIALOG}[open]").count() == 0
    assert page.inner_text(".df-chip-t").endswith("決める")
    assert page.evaluate(SAVED_SEL_JS) == "V-2"
    # 表の変えた行に印が付き、変えていない行には付かない
    marks = page.eval_on_selector_all(
        "table.grid tbody tr",
        "rows => Object.fromEntries(rows.map(r => [r.dataset.id, !!r.querySelector('.row-open + .df-mark.df-chg')]))",
    )
    assert marks == {"D-1": True, "D-2": True}
    # 選んだ時点を押し直しても、記録を読み直さず履歴に積まない
    assert "view=table" in page.url
    # 開き直したモーダルは、選んだ時点の行にチェックを付ける
    _open_dialog(page)
    assert [row["current"] for row in page.evaluate(ROWS_JS)] == [None, None, None, "true", None]


def test_pick_off(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """「差分を出さない（今の内容）」を押すと、差分の表示をやめて印と札を外す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector(".df-chip")
    _open_dialog(page)
    # 実行
    page.click(f"{ROW}[data-sel='']")
    # 検証
    page.wait_for_selector(".df-chip", state="detached", timeout=REDRAW_TIMEOUT_MS)
    assert page.locator(".df-mark").count() == 0
    assert page.evaluate(SAVED_SEL_JS) is None


def test_close(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """閉じるボタン・Esc・外側の押下で閉じ、選んだ時点は変えず、「変更履歴」のボタンへフォーカスを戻す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector(".df-chip")
    for how in ("button", "escape", "backdrop"):
        _open_dialog(page)
        # 実行
        if how == "button":
            page.get_by_role("button", name="変更履歴を閉じる").click()
        elif how == "escape":
            page.keyboard.press("Escape")
        else:
            page.mouse.click(5, 5)
        # 検証
        page.wait_for_selector(f"{DIALOG}[open]", state="detached")
        assert page.evaluate(SAVED_SEL_JS) == "V-2", how
        assert page.inner_text(".df-chip-t").endswith("決める"), how
        assert page.evaluate("document.activeElement.dataset.act") == "hist", how


def test_selection_kept_when_reloaded_and_rewritten(
    write_history_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    call_tool: CallTool,
    page: Page,
) -> None:
    """選んだ時点は読み込み直しても、開いたまま記録が書き換わっても保たれ、新しい記録で印を引き直す（正常系）。"""
    # 準備
    url, root = write_history_preview()
    open_preview(url, "#tab=decisions&view=table")
    _open_dialog(page)
    page.click(f"{ROW}[data-sel='V-2']")
    page.wait_for_selector(".df-chip")
    # 実行（読み込み直す）
    page.reload()
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert page.inner_text(".df-chip-t").endswith("決める")
    # 読み込み直すと絞り込みは開いたときの既定に戻るので、決定済みの D-1 は出ず、印は D-2 だけに付く
    assert page.locator("table.grid .df-mark").count() == 1
    # 実行（開いたまま、まとまり V-2 に入る項目をまとめる前に別の項目を足す）
    result = call_tool(
        "add",
        workspace=str(root),
        kind="decision",
        item={
            "title": "後から足した問い",
            "status": "未決定",
            "options": [{"key": "A", "content": "案 A"}],
        },
    )
    assert result.is_error is False, result.text
    page.wait_for_selector("table.grid tbody tr[data-id='D-3']", timeout=REDRAW_TIMEOUT_MS)
    # 検証
    assert page.inner_text(".df-chip-t").endswith("決める")
    assert page.evaluate(SAVED_SEL_JS) == "V-2"
    assert page.locator("table.grid tbody tr[data-id='D-3'] .df-mark").count() == 0
