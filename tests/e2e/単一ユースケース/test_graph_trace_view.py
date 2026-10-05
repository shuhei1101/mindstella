"""つながりを辿る（3D のつながりで玉を押して詳細を開き、ドロワーで種類・状態・タグを絞る）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from preview_helpers import (
    DRAWER,
    OpenPreview,
    ServePreview,
    badge_text,
    checked_values,
    clear_condition,
    click_item_ball,
    close_drawer,
    open_drawer,
    shown_ball_item_ids,
    toggle_value,
)
from workspace_fixtures import MakeItem

# ドロワーの種類の値の並び（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）
KIND_LABELS = ["検討事項", "タスク", "調査", "資料", "用語集", "メモ", "会話ログ"]

# 7 種類の項目を 1 つずつ指す ID（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）
ONE_ITEM_PER_KIND = ["D-1", "T-2", "R-1", "A-1", "G-1", "N-1", "L-1"]

# 検討事項の ID（記録の検討事項は D-1 と D-3）
DECISION_IDS = {"D-1", "D-3"}

# 検討事項とタスクの ID（記録のタスクは T-2）
DECISION_AND_TASK_IDS = {"D-1", "D-3", "T-2"}

# 種類の色の点を、ドロワーの種類の値ごとに読む
DOT_COLORS_SCRIPT = """() => [...document.querySelectorAll('dialog.drawer .fd-group:first-of-type .fd-opt')].map(
    l => getComputedStyle(l.querySelector('.kdot')).backgroundColor
)"""


def _records(make_item: MakeItem) -> list[dict[str, Any]]:
    """7 種類の項目を 1 件以上ずつ。D-3 は前提 D-1・進めるタスク T-2・関連 R-1 とつながる。"""
    return [
        make_item("D-1", status="決定済み"),
        make_item("D-3", status="要見直し", depends_on=["D-1"], related=["R-1"]),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("R-1", question="何を調べたか"),
        make_item("A-1"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
    ]


def test_normal(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """種類ごとの色で出し、D-3 の玉を押して詳細を開き、ドロワーで検討事項とタスクに絞る（正常系）。"""
    # 準備
    url = serve_preview(
        *_records(make_item), settings=valid_settings, bodies={"A-1.md": "資料の本文\n"}
    )
    page = open_preview(url)
    # 実行・検証（開く）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    open_drawer(page)
    kinds = page.eval_on_selector_all(
        f'{DRAWER} input[data-key="type"]', "inputs => inputs.map(i => i.value)"
    )
    assert kinds == KIND_LABELS
    counts = page.eval_on_selector_all(
        f'{DRAWER} .fd-group:first-of-type .fd-opt .n', "counts => counts.map(c => Number(c.textContent))"
    )
    assert all(count >= 1 for count in counts)
    colors = page.evaluate(DOT_COLORS_SCRIPT)
    assert len(set(colors)) == len(KIND_LABELS)
    close_drawer(page)
    # D-3 の玉を押すと、詳細パネルに D-3 が開き、URL のハッシュがつながりと D-3 を指す
    click_item_ball(page, "D-3")
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    hash_text = page.evaluate("location.hash")
    assert "tab=graph" in hash_text
    assert "id=D-3" in hash_text
    # ドロワーの種類で検討事項とタスクを選ぶと、その玉だけが残り、バッジが付く
    open_drawer(page)
    toggle_value(page, "type", "検討事項")
    toggle_value(page, "type", "タスク")
    assert checked_values(page, "type") == ["検討事項", "タスク"]
    assert badge_text(page) == "1"
    close_drawer(page)
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert shown_ball_item_ids(page) == DECISION_AND_TASK_IDS


def _click_ball_of_each_kind(page: Page) -> None:
    """7 種類の項目の玉を、種類ごとに 1 つずつ押して見つける（無ければ失敗する）。"""
    for item_id in ONE_ITEM_PER_KIND:
        click_item_ball(page, item_id)


def test_normal_when_kind_condition_cleared(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """ドロワーの種類で検討事項だけを選び、「解除」で全種類の玉に戻す（正常系）。"""
    # 準備
    url = serve_preview(
        *_records(make_item), settings=valid_settings, bodies={"A-1.md": "資料の本文\n"}
    )
    # 実行・検証（開く: 全種類の玉と線と、どの種類も選ばれていないドロワー）
    page = open_preview(url, "#tab=graph")
    page.wait_for_selector("#graph-canvas")
    open_drawer(page)
    assert checked_values(page, "type") == []
    assert badge_text(page) is None
    close_drawer(page)
    _click_ball_of_each_kind(page)
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    # 実行・検証（検討事項だけを選ぶ: 検討事項の玉だけ）
    open_drawer(page)
    toggle_value(page, "type", "検討事項")
    assert badge_text(page) == "1"
    close_drawer(page)
    decision_ids = shown_ball_item_ids(page)
    assert decision_ids
    assert decision_ids <= DECISION_IDS
    # 実行・検証（種類の「解除」: 全種類の玉に戻り、種類のチェックが全て外れ、バッジが消える）
    open_drawer(page)
    clear_condition(page, "種類")
    assert checked_values(page, "type") == []
    assert badge_text(page) is None
    close_drawer(page)
    _click_ball_of_each_kind(page)


def test_normal_when_filtered(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """ドロワーのタグで話題を選び、状態を足して、両方の条件に合う項目の玉だけにする（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("D-1", status="決定済み", tags=["保存"]),
        make_item("D-3", status="要見直し", tags=["保存"], depends_on=["D-1"], related=["R-1"]),
        make_item("T-2", status="進行中", tags=["通知"], **{"for": ["D-3"]}),
        make_item("R-1", question="何を調べたか"),
        settings=valid_settings,
    )
    page = open_preview(url, "#tab=graph")
    page.wait_for_selector("#graph-canvas")
    # 実行（タグ「保存」を選ぶ）
    open_drawer(page)
    toggle_value(page, "tags", "保存")
    statuses = page.eval_on_selector_all(
        f'{DRAWER} input[data-key="status"]', "inputs => inputs.map(i => i.value)"
    )
    close_drawer(page)
    tagged_ids = shown_ball_item_ids(page)
    # 実行（状態に「決定済み」を足す）
    open_drawer(page)
    toggle_value(page, "status", "決定済み")
    assert badge_text(page) == "2"
    close_drawer(page)
    decided_ids = shown_ball_item_ids(page)
    # 検証
    assert tagged_ids == {"D-1", "D-3"}
    # ドロワーの状態に、並んでいる項目の状態が出る
    assert statuses == ["要見直し", "決定済み", "進行中"]
    assert decided_ids == {"D-1"}
