"""編集・保存待ちの画面の結合テストが共有する値と、操作・読み取りの関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from workspace_fixtures import RECORD_DIR

__all__ = [
    "ADDED_ITEM",
    "ADD_BUTTON",
    "ADD_PANEL",
    "ADD_TITLE_INPUT",
    "AI_UPDATED",
    "DETAIL_PANEL",
    "PENDING_BUTTON",
    "PENDING_PANEL",
    "SAVE_BUTTON",
    "SAVE_PATTERN",
    "SETTLE_MS",
    "STALE_BASE",
    "TAB_PRESS_LIMIT",
    "added_edit",
    "assert_topbar_pending",
    "block_by_saving",
    "edit_edits",
    "edit_items",
    "item_marks",
    "open_pending",
    "reached_by_tab",
    "read_edits_file",
    "read_items_file",
    "start_add",
    "wait_no_saved_edits",
    "wait_saved_edit",
]

# トップバーの保存待ちのボタン
PENDING_BUTTON = "header.topbar button.pending-btn"

# 保存待ちのパネル
PENDING_PANEL = "aside.pending-panel"

# 保存待ちのパネルの「まとめて保存する」
SAVE_BUTTON = f"{PENDING_PANEL} button.pe-save"

# 種類ごとの画面の「項目を追加」
ADD_BUTTON = "button.pe-add"

# 項目を追加する入力のパネル
ADD_PANEL = "aside.pe-add-panel"

# 詳細パネル
DETAIL_PANEL = "aside.panel"

# 保存の要求のパターン
SAVE_PATTERN = "**/api/edits/save"

# Tab キーで届くかを確かめるときに押す回数の上限
TAB_PRESS_LIMIT = 120


def open_pending(page: Page) -> None:
    """トップバーの保存待ちのボタンを押して、パネルが開くのを待つ。"""
    page.click(PENDING_BUTTON)
    page.wait_for_selector(PENDING_PANEL)


# 保存待ちの編集（/api/edits）に、指したキーの編集が値つきで溜まったかを読む。値はキーの並びによらず比べる
SAVED_EDIT_JS = """async ({op, key, value}) => {
  const canon = (v) => JSON.stringify(v, (_, x) =>
    x && typeof x === 'object' && !Array.isArray(x)
      ? Object.fromEntries(Object.keys(x).sort().map(k => [k, x[k]])) : x);
  const items = (await (await fetch('/api/edits')).json()).items;
  return items.some(e => e.key === key && (op === null || e.op === op) && canon(e.value) === canon(value));
}"""

# 保存待ちの編集（/api/edits）が空になったかを読む
NO_SAVED_EDITS_JS = "async () => (await (await fetch('/api/edits')).json()).items.length === 0"


def wait_saved_edit(page: Page, key: str, value: Any, op: str | None = None) -> None:
    """保存待ちの編集（/api/edits）に、キーの編集が値つきで溜まるのを待つ。"""
    page.wait_for_function(SAVED_EDIT_JS, arg={"op": op, "key": key, "value": value}, timeout=SETTLE_MS)


def wait_no_saved_edits(page: Page) -> None:
    """保存待ちの編集（/api/edits）が空になるのを待つ。"""
    page.wait_for_function(NO_SAVED_EDITS_JS, timeout=SETTLE_MS)


def read_edits_file(root: Path) -> dict[str, Any]:
    """ワークスペースの edits.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "edits.yaml").read_text(encoding="utf-8"))


def read_items_file(root: Path, file_name: str) -> list[dict[str, Any]]:
    """種類ごとの YAML の項目の並びを読む。"""
    return yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))["items"]


def added_edit(
    make_edit: Any, edit_id: str, temp: str, kind: str, **value: Any
) -> dict[str, Any]:
    """項目を足す保存待ちの編集（`item-add`）を作る。`value` は足す項目のキーと値。"""
    return make_edit(
        edit_id, target=temp, op="item-add", key=kind, value=value, before=None, base=None
    )


def reached_by_tab(page: Page, *selectors: str) -> list[str]:
    """ページの先頭から Tab キーを押していき、フォーカスが当たった要素のうち渡したセレクターに合うものを、当たった順に返す。"""
    page.evaluate("document.activeElement instanceof HTMLElement && document.activeElement.blur()")
    reached: list[str] = []
    for _ in range(TAB_PRESS_LIMIT):
        page.keyboard.press("Tab")
        for selector in selectors:
            if selector not in reached and page.evaluate(
                "selector => document.activeElement?.matches(selector) === true", selector
            ):
                reached.append(selector)
        if len(reached) == len(selectors):
            break
    return reached


# 一覧の「項目を追加」で足す項目の入力（追加の入力のパネルの最初の入力欄）
ADD_TITLE_INPUT = f"{ADD_PANEL} [data-first]"

# 追加する項目（ID を持たない）の要素の印
ADDED_ITEM = "[data-new-id]"

# 一覧の保存待ちの印を保存待ちの編集から作るための、AI が溜めた後に書き換えた日時と溜めたときの更新日時
AI_UPDATED = "2026-10-05T01:00:00+00:00"
STALE_BASE = "2026-09-01T00:00:00+00:00"

# 保存を待つ上限ミリ秒
SETTLE_MS = 10_000


def item_marks(page: Page, scope: str) -> dict[str, dict[str, Any]]:
    """`scope` の項目の要素にある保存待ちの印を、項目の ID → 印の種類・文字・印だけか・title にして返す。

    `scope` は項目の要素（`data-id` か `data-node` を持つ）を引くセレクター。印を持たない要素は含めない。
    """
    return page.evaluate(
        """scope => Object.fromEntries(
            [...document.querySelectorAll(scope)]
                .map(node => [node.dataset.id ?? node.dataset.node, node.querySelector('.pm')])
                .filter(([, mark]) => mark !== null)
                .map(([id, mark]) => [id, {
                    kind: [...mark.classList].find(name => /^pm-(pending|remove|blocked)$/.test(name)).slice(3),
                    text: mark.textContent.trim(),
                    compact: mark.classList.contains('pm-compact'),
                    title: mark.title,
                }])
        )""",
        scope,
    )


def block_by_saving(page: Page) -> None:
    """保存待ちのパネルから保存して、書き込めない編集がある旨を出させ、パネルを閉じる（異常系の準備）。"""
    open_pending(page)
    page.click(SAVE_BUTTON)
    page.wait_for_selector(f"{PENDING_PANEL} .pe-alert", timeout=SETTLE_MS)
    page.get_by_role("button", name="保存待ちの編集を閉じる").click()
    page.wait_for_selector(PENDING_PANEL, state="detached")


def start_add(page: Page, title: str) -> None:
    """「項目を追加」を押し、追加の入力にタイトルを書いて離れ、保存待ちに溜まるのを待つ。"""
    page.click(ADD_BUTTON)
    page.wait_for_selector(ADD_PANEL)
    page.locator(ADD_TITLE_INPUT).fill(title)
    page.locator(ADD_TITLE_INPUT).blur()
    page.wait_for_selector(f"{PENDING_BUTTON} .count", timeout=SETTLE_MS)


def edit_items(make_item: Any, prefix: str) -> tuple[dict[str, Any], ...]:
    """書き換える `{prefix}-1`・削除する `{prefix}-2`・溜めた後に AI が書き換えて書き込めなくなる `{prefix}-3` を返す。"""
    return (
        make_item(f"{prefix}-1", title="書き換える項目"),
        make_item(f"{prefix}-2", title="消す項目"),
        make_item(f"{prefix}-3", title="書き込めない項目", updated=AI_UPDATED),
    )


def edit_edits(make_edit: Any, prefix: str) -> tuple[dict[str, Any], ...]:
    """`edit_items` の `{prefix}-1` のタイトルの書き換え・`{prefix}-2` の削除・`{prefix}-3` のタイトルの書き換え（溜めた後に書き換わった）を返す。"""
    return (
        make_edit("E-1", target=f"{prefix}-1", key="title", value="書き換えた題", before="書き換える項目"),
        make_edit("E-2", target=f"{prefix}-2", op="item-remove", key=None, value=None, before=None),
        make_edit(
            "E-3",
            target=f"{prefix}-3",
            key="title",
            value="別の題",
            before="書き込めない項目",
            base=STALE_BASE,
        ),
    )


def assert_topbar_pending(page: Page) -> None:
    """トップバーの保存待ちのボタンが、件数・開閉・書き込めない編集の有無を出すことを確かめる（3 件を溜めた画面で呼ぶ）。"""
    button = page.locator(PENDING_BUTTON)
    # 溜めた 3 件
    assert button.get_attribute("aria-label") == "保存待ち（3 件）"
    assert button.locator(".count").inner_text() == "3"
    assert button.get_attribute("aria-expanded") == "false"
    assert "blocked" not in button.get_attribute("class")
    # 押すとパネルが開き、もう一度押すと閉じる
    page.click(PENDING_BUTTON)
    page.wait_for_selector(PENDING_PANEL)
    assert button.get_attribute("aria-expanded") == "true"
    page.click(PENDING_BUTTON)
    page.wait_for_selector(PENDING_PANEL, state="detached")
    assert button.get_attribute("aria-expanded") == "false"
    # 直前の保存で書き込めなかった編集が残ると、件数の横の印を警告にする
    block_by_saving(page)
    assert button.get_attribute("aria-label") == "保存待ち（3 件・書き込めない編集あり）"
    assert "blocked" in button.get_attribute("class")
