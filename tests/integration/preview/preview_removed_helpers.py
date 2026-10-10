"""消した項目の帯・取り下げの札の結合テストが共有する、消した項目と取り下げた項目を持つワークスペースの作り方と値。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from preview_history_helpers import FIRST_SET_AT, SECOND_SET_AT, read_yaml
from workspace_fixtures import RECORD_DIR, CallTool, MakeItem, MakeWorkspace

__all__ = [
    "BAND",
    "BAND_ITEM",
    "OPENED_BEFORE_SETS_AT",
    "REMOVED_IN_PENDING_BY_TAB",
    "REMOVED_IN_V2_BY_TAB",
    "REMOVED_SINCE_BY_TAB",
    "REMOVED_TITLES",
    "WITHDRAWN_BADGE",
    "WITHDRAWN_REASONS",
    "assert_band_above",
    "assert_removed_band",
    "build_removed_workspace",
    "removed_band_items",
]

# 消した項目の帯（読み上げ名つきの section）と、その中の 1 件
BAND = "section.rm-band"
BAND_ITEM = f"{BAND} li.rm-item"

# 取り下げの札
WITHDRAWN_BADGE = ".wd-badge"

# 前回開いた日時（V-1 より前。「前回開いてから」が全てのまとまりを含む）
OPENED_BEFORE_SETS_AT = "2026-09-30T00:00:00+00:00"

# 消したときのタイトル（項目の ID → タイトル）。D-4 は足したまとまりより後のまとまりで消す
REMOVED_TITLES = {
    "D-3": "D-3の題",
    "D-4": "足してすぐ消す問い",
    "T-2": "T-2の題",
    "R-3": "R-3の題",
    "A-3": "A-3の題",
    "G-3": "G-3の題",
    "N-3": "N-3の題",
    "L-3": "L-3の題",
}

# 画面の種類ごとの、まとまり V-2 を選んだときに帯へ並べる（ID, タイトル）。ID の順（V-2 はタスクを消さない）
REMOVED_IN_V2_BY_TAB = {
    "decisions": [("D-3", REMOVED_TITLES["D-3"]), ("D-4", REMOVED_TITLES["D-4"])],
    "research": [("R-3", REMOVED_TITLES["R-3"])],
    "docs": [("A-3", REMOVED_TITLES["A-3"])],
    "terms": [("G-3", REMOVED_TITLES["G-3"])],
    "notes": [("N-3", REMOVED_TITLES["N-3"])],
    "logs": [("L-3", REMOVED_TITLES["L-3"])],
}

# 画面の種類ごとの、まだまとめていない変更を選んだときに帯へ並べる（ID, タイトル）
REMOVED_IN_PENDING_BY_TAB = {"tasks": [("T-2", REMOVED_TITLES["T-2"])]}

# 画面の種類ごとの、「前回開いてから」を選んだときに帯へ並べる（ID, タイトル）。V-2 とまだまとめていない変更を合わせる
REMOVED_SINCE_BY_TAB = {**REMOVED_IN_V2_BY_TAB, **REMOVED_IN_PENDING_BY_TAB}

# 取り下げた項目の ID → 取り下げた理由
WITHDRAWN_REASONS = {
    "R-2": "別の調査で足りた",
    "A-2": "別の資料に統合した",
    "G-2": "別の用語に寄せた",
    "N-2": "メモを別にまとめた",
    "L-2": "別の会話に移した",
}

# 実際のツールで足す検討事項（足したまとまりより後で消す）
ADDED_DECISION: dict[str, Any] = {
    "title": REMOVED_TITLES["D-4"],
    "status": "未決定",
    "options": [{"key": "A", "content": "案 A"}],
    "weight": "大",
    "category": "データ構造",
    "phase": "要件",
    "target": "mindmap",
}


def _call(call_tool: CallTool, name: str, **arguments: Any) -> dict[str, Any]:
    """ツールを呼び、エラーならテストを止めて結果を返す。"""
    result = call_tool(name, **arguments)
    assert result.is_error is False, result.text
    assert result.data is not None
    return result.data


def build_removed_workspace(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> Path:
    """実際のツールで、取り下げた項目と、まとまり V-1（足す・取り下げる）・V-2（消す）とまだまとめていない消した項目を持つワークスペースを作る。

    各種類の ID は 1 が通常、2 が V-1 で取り下げる項目、3 が V-2 で消す項目（タスクだけ T-2 をまとめていない変更で消す）。
    """
    root = make_workspace(
        make_item(
            "D-1",
            status="決定済み",
            options=[{"key": "A", "content": "案 A", "adopted": True}],
        ),
        make_item("D-2"),
        make_item("D-3"),
        make_item("T-1"),
        make_item("T-2"),
        make_item("R-1"),
        make_item("R-2"),
        make_item("R-3"),
        make_item("A-1"),
        make_item("A-2"),
        make_item("A-3"),
        make_item("G-1"),
        make_item("G-2"),
        make_item("G-3"),
        make_item("N-1"),
        make_item("N-2"),
        make_item("N-3"),
        make_item("L-1"),
        make_item("L-2"),
        make_item("L-3"),
        bodies={"A-1.md": "資料 1 の本文\n", "A-2.md": "資料 2 の本文\n", "A-3.md": "資料 3 の本文\n"},
    )
    workspace = str(root)
    # V-1: 検討事項とメモを足し、調査・資料・用語集・メモ・会話ログを取り下げる
    _call(call_tool, "add", workspace=workspace, kind="decision", item=ADDED_DECISION)
    _call(call_tool, "add", workspace=workspace, kind="note", item={"title": "残るメモ", "content": "メモ"})
    for item_id, reason in WITHDRAWN_REASONS.items():
        _call(
            call_tool,
            "update",
            workspace=workspace,
            id=item_id,
            item={"withdrawn": True, "reason": reason},
        )
    _call(call_tool, "commit", workspace=workspace, summary="取り下げる")
    # V-2: V-1 で足した検討事項と、各種類の ID 3 を消す
    for item_id in ("D-4", "D-3", "R-3", "A-3", "G-3", "N-3", "L-3"):
        _call(call_tool, "remove", workspace=workspace, id=item_id)
    _call(call_tool, "commit", workspace=workspace, summary="消す")
    # まだまとめていない変更: タスクを消す
    _call(call_tool, "remove", workspace=workspace, id="T-2")
    # まとまりの日時を固定し、前回開いた日時を V-1 より前に置く
    changes = read_yaml(root / RECORD_DIR / "changes.yaml")
    changes["sets"][1]["at"] = FIRST_SET_AT
    changes["sets"][0]["at"] = SECOND_SET_AT
    (root / RECORD_DIR / "changes.yaml").write_text(
        yaml.safe_dump(changes, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / RECORD_DIR / ".mindstella-opened").write_text(
        f"{OPENED_BEFORE_SETS_AT}\n", encoding="utf-8"
    )
    return root


def removed_band_items(page: Page) -> list[tuple[str, str]]:
    """画面に出ている消した項目の帯の項目を、並びのまま（ID, タイトル）で返す。"""
    items: list[list[str]] = page.eval_on_selector_all(
        BAND_ITEM,
        "items => items.map(i => [i.dataset.removedId, i.querySelector('.rm-ttl').textContent])",
    )
    return [(item_id, title) for item_id, title in items]


def assert_removed_band(page: Page, expected: list[tuple[str, str]]) -> None:
    """消した項目の帯が 1 つだけあり、読み上げ名と件数の見出しを持ち、expected を並びのまま出して、項目が押せない（押しても詳細を開かない）ことを確かめる。"""
    assert page.locator(BAND).count() == 1
    assert page.get_attribute(BAND, "aria-label") == "この時点で消した項目"
    heading = page.locator(f"{BAND} h2.rm-band-t")
    assert heading.inner_text().split("\n")[0] == "消した項目"
    assert heading.locator(".n").inner_text() == str(len(expected))
    assert removed_band_items(page) == expected
    # 項目の頭の印は消した（−）で、読み上げにも「消した」を残す
    marks = page.locator(f"{BAND_ITEM} > .df-mark.df-del")
    assert marks.count() == len(expected)
    assert marks.first.get_attribute("title") == "消した"
    assert marks.first.locator(".sr-only").inner_text() == "消した"
    # 項目は ul の li で、ボタン・リンク・キーボードの移動先を持たない
    assert page.locator(f"{BAND} ul.rm-list").count() == 1
    assert page.locator(f"{BAND} :is(button, a, [tabindex])").count() == 0
    # 項目を押しても詳細パネルを開かない
    page.locator(BAND_ITEM).first.click()
    assert page.locator("aside.panel.open").count() == 0


def assert_band_above(page: Page, selector: str) -> None:
    """消した項目の帯が、selector の要素の上（縦の位置が重ならず手前）にあることを確かめる。"""
    band_box = page.locator(BAND).bounding_box()
    below_box = page.locator(selector).first.bounding_box()
    assert band_box is not None
    assert below_box is not None
    assert band_box["y"] + band_box["height"] <= below_box["y"]
