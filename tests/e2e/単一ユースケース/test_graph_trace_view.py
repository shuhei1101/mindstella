"""ネットワークを辿る（3D のネットワークで玉を押して詳細を開き、ドロワーで種類・状態・タグを絞り、注目の起点の項目をロックして辿る）の E2E テスト。

見た目の描き分け・状態の印・鍵の震えの見え方はキャンバスの中の絵なので確かめず、画面設計の結合テストが確かめる。
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from playwright.sync_api import Page
from preview_helpers import (
    DRAWER,
    OpenPreview,
    ServePreview,
    badge_text,
    center_ball,
    checked_values,
    clear_condition,
    click_item_ball,
    close_drawer,
    closed_keys,
    install_closed_key_spy,
    open_drawer,
    press_ball_keeping_detail,
    press_blank,
    press_center_ball,
    shown_ball_item_ids,
    toggle_value,
    wait_camera_still,
    wait_closed_key,
)
from workspace_fixtures import ADOPTED_OPTIONS, MakeItem

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
        make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS),
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
    # D-3 の玉を押すと、詳細パネルに D-3 が開き、URL のハッシュがネットワークと D-3 を指す
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
        make_item("D-1", status="決定済み", tags=["保存"], options=ADOPTED_OPTIONS),
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


# 閉じた鍵の位置を比べるときに許す差（px。カメラが止まっていれば動かない）
KEY_POSITION_TOLERANCE_PX = 3

# 鍵の震えが収まるまで待つ時間（ms。震えは約 1 秒）
SHAKE_DONE_MS = 1_500


def _panel_title(page: Page) -> str:
    """詳細パネルの題を返す。"""
    return page.inner_text("aside.panel .d-title")


def _only_closed_key(page: Page) -> tuple[float, float]:
    """カメラが止まってから、描いている閉じた鍵が 1 つだけであることを確かめて、その位置を返す。"""
    wait_camera_still(page)
    keys = closed_keys(page)
    assert len(keys) == 1
    return keys[0]


def test_normal_when_locked(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """D-3 をロックして辿り、T-2 を開いても中心と強調は D-3 のまま、余白や開いた T-2 の二度押しでは鍵が震えるだけで、概要から戻ってもロックは残り、D-3 の二度押しでロックを外す（正常系）。"""
    # 準備（動きを減らす設定にして、カメラが自動で回らないようにする）
    page.emulate_media(reduced_motion="reduce")
    install_closed_key_spy(page)
    url = serve_preview(
        *_records(make_item), settings=valid_settings, bodies={"A-1.md": "資料の本文\n"}
    )
    open_preview(url, "#tab=graph")
    page.wait_for_selector("#graph-canvas")
    # 実行・検証（D-3 の玉を押すと、D-3 の詳細パネルが開く。まだロックしない）
    click_item_ball(page, "D-3")
    wait_camera_still(page)
    assert _panel_title(page) == "D-3の題"
    assert closed_keys(page) == []
    # 実行・検証（D-3 の玉をもう一度押すと、D-3 をロックして閉じた鍵を出し、詳細パネルは D-3 のまま）
    press_center_ball(page)
    wait_closed_key(page, shown=True)
    locked_key = _only_closed_key(page)
    assert _panel_title(page) == "D-3の題"
    # 実行・検証（T-2 の玉を押すと、詳細パネルは T-2 に替わり、中心と閉じた鍵はロックした D-3 のまま）
    t2_x, t2_y = press_ball_keeping_detail(page, "T-2")
    assert "id=T-2" in page.evaluate("location.hash")
    assert _only_closed_key(page) == pytest.approx(locked_key, abs=KEY_POSITION_TOLERANCE_PX)
    # 実行・検証（T-2 の玉をもう一度押しても、鍵が震えるだけで、ロックも詳細パネルも変わらない）
    page.mouse.move(t2_x, t2_y)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(SHAKE_DONE_MS)
    assert _panel_title(page) == "T-2の題"
    assert _only_closed_key(page) == pytest.approx(locked_key, abs=KEY_POSITION_TOLERANCE_PX)
    # 実行・検証（余白を押しても、鍵が震えるだけで、詳細パネルは T-2 のまま開いている）
    press_blank(page)
    page.wait_for_timeout(SHAKE_DONE_MS)
    assert page.is_visible("aside.panel.open")
    assert _panel_title(page) == "T-2の題"
    assert _only_closed_key(page) == pytest.approx(locked_key, abs=KEY_POSITION_TOLERANCE_PX)
    # 実行・検証（概要のタブへ移ってネットワークのタブへ戻っても、閉じた鍵が残る）
    page.click('nav.tabbar a[data-tab="overview"]')
    page.wait_for_selector(".overview")
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    wait_closed_key(page, shown=True)
    _only_closed_key(page)
    # 実行・検証（中心の玉 = ロックした D-3 を押すと、詳細パネルが D-3 に戻り、ロックは残る）
    press_center_ball(page)
    page.wait_for_function("location.hash.includes('id=D-3')")
    assert _panel_title(page) == "D-3の題"
    _only_closed_key(page)
    # 実行・検証（D-3 をもう一度押すと、ロックが外れて閉じた鍵が消え、詳細パネルは D-3 のまま）
    press_center_ball(page)
    wait_closed_key(page, shown=False)
    assert _panel_title(page) == "D-3の題"


def test_normal_when_opened_with_detail(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """検討事項で D-3 の詳細を開いたままタブの帯のネットワークへ移ると、詳細パネルは D-3 のまま開き、ネットワークも D-3 を選んだ項目として示す（正常系）。"""
    # 準備
    page.emulate_media(reduced_motion="reduce")
    url = serve_preview(
        *_records(make_item), settings=valid_settings, bodies={"A-1.md": "資料の本文\n"}
    )
    open_preview(url, "#tab=decisions")
    # 実行（検討事項のボードで D-3 を押し、詳細パネルを開く）
    page.click('.board .card[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open")
    # 実行（タブの帯のネットワークを押す）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    center_ball(page)
    # 検証
    # 詳細パネルに D-3 が開いたままで、ネットワークが D-3 を選んだ項目として示す（D-3 の玉がキャンバスの中心にある）
    assert page.is_visible("aside.panel.open")
    assert _panel_title(page) == "D-3の題"
    # URL のハッシュがネットワークと D-3 を指す
    hash_text = page.evaluate("location.hash")
    assert "tab=graph" in hash_text
    assert "id=D-3" in hash_text
    # 詳細パネルにネットワークへ移るボタンが無い
    moves = page.locator("aside.panel button, aside.panel a").filter(
        has_text=re.compile("ネットワーク|つながり")
    )
    assert moves.count() == 0
