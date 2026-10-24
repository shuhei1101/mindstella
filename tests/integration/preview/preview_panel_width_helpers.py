"""詳細パネルの幅の区切りの結合テストが共有する、保存領域のキーと値、画面の幅、操作・読み取りの関数。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

__all__ = [
    "DEFAULT_WIDTH_PX",
    "MIN_WIDTH_PX",
    "PANEL",
    "PANEL_VIEWPORT",
    "PANEL_WIDTH_KEY",
    "RESIZER",
    "STEP_PX",
    "drag_resizer",
    "open_panel",
    "panel_state",
    "press_key_times",
    "read_stored_width",
    "seed_panel_width",
    "wait_for_value_now",
]

# そのタブで変えた詳細パネルの幅を残す sessionStorage のキー
PANEL_WIDTH_KEY = "mindmap-panel-width"

# 詳細パネルと、その左端の幅の区切り
PANEL = "aside.panel"
RESIZER = f"{PANEL} .panel-resizer"

# 既定の幅・ドラッグで狭められる下限・矢印キー 1 回の刻み（px）
DEFAULT_WIDTH_PX = 640
MIN_WIDTH_PX = 480
STEP_PX = 16

# 本文を寄せる幅（1100px 以上）に収まる画面の大きさ
PANEL_VIEWPORT = {"width": 1280, "height": 800}

# パネルのすべり込みと本文の寄せの動き（終わりのある動き）が終わるまで待つ。マップなど終わりのない動きは待たない
_SETTLED_JS = """async () => {
    await document.fonts.ready;
    const finite = document.getAnimations().filter((animation) => animation.effect.getComputedTiming().iterations !== Infinity);
    await Promise.all(finite.map((animation) => animation.finished));
}"""

# パネルと区切りの今の状態を返す（幅・本文の寄せ・区切りの属性と見え方）
_PANEL_STATE_JS = """() => {
    const panel = document.querySelector('aside.panel');
    const separator = panel.querySelector('.panel-resizer');
    const content = document.querySelector('.content');
    const rect = separator === null ? null : separator.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();
    return {
        panelWidth: panelRect.width,
        contentMargin: parseFloat(getComputedStyle(content).marginRight),
        separator: separator === null ? null : {
            role: separator.getAttribute('role'),
            orientation: separator.getAttribute('aria-orientation'),
            label: separator.getAttribute('aria-label'),
            min: separator.getAttribute('aria-valuemin'),
            max: separator.getAttribute('aria-valuemax'),
            now: separator.getAttribute('aria-valuenow'),
            tabindex: separator.getAttribute('tabindex'),
            edge: separator.dataset.edge,
            display: getComputedStyle(separator).display,
            cursor: getComputedStyle(separator).cursor,
            width: rect.width,
            leftInPanel: rect.left - panelRect.left - panel.clientLeft,
            focused: document.activeElement === separator,
        },
    };
}"""


def seed_panel_width(page: Page, width: int) -> None:
    """ページを開く前に、そのタブの保存領域へ変えた詳細パネルの幅を入れる。"""
    page.add_init_script(
        f"try {{ sessionStorage.setItem('{PANEL_WIDTH_KEY}', '{width}'); }} catch (e) {{}}"
    )


def read_stored_width(page: Page) -> str | None:
    """そのタブの保存領域に残した詳細パネルの幅を、文字列のまま読む。"""
    return page.evaluate(f"sessionStorage.getItem('{PANEL_WIDTH_KEY}')")


def panel_state(page: Page) -> dict[str, Any]:
    """パネルのすべり込みと本文の寄せの動きが終わってから、パネルの幅・本文の寄せ・区切りの状態を返す。"""
    page.evaluate(_SETTLED_JS)
    return page.evaluate(_PANEL_STATE_JS)


def press_key_times(page: Page, key: str, times: int) -> None:
    """幅の区切りにフォーカスを置いて、キーを続けて押す。"""
    page.focus(RESIZER)
    for _ in range(times):
        page.keyboard.press(key)


def drag_resizer(page: Page, delta_x: int) -> None:
    """パネルのすべり込みが終わってから、幅の区切りの縦の中央を押し、横へ動かして離す（左へ動かすと広がる）。"""
    page.evaluate(_SETTLED_JS)
    box = page.locator(RESIZER).bounding_box()
    assert box is not None
    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + delta_x, start_y, steps=5)
    page.mouse.up()


def wait_for_value_now(page: Page, now: int) -> None:
    """区切りの今の幅（`aria-valuenow`）が、窓の幅の変化を受けて変わるまで待つ。"""
    page.wait_for_function(
        f"document.querySelector('{RESIZER}')?.getAttribute('aria-valuenow') === '{now}'"
    )


def open_panel(page: Page, open_preview: Any, url: str, hash_text: str, viewport: dict[str, int]) -> Page:
    """画面の大きさを決めてから、ハッシュが指す項目の詳細パネルを開き、パネルが出るまで待つ。"""
    page.set_viewport_size(viewport)
    open_preview(url, hash_text)
    page.wait_for_selector(f"{PANEL}.open")
    return page
