"""書き込みのボタンの待つ間を確かめる画面の結合テストの補助（要求を留める・2 回押す・待つ間の見た目を確かめる）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import Locator, Page, Route, expect

__all__ = ["HeldRequests", "assert_waiting", "hold_requests", "press_twice"]

# 回るマーカーを出すまでの待ち（1 秒）を超えるミリ秒
SPINNER_SHOWN_MS = 1200

# 留めた要求の数が増えないことを確かめて待つミリ秒
SETTLE_MS = 500

# 回るマーカーの要素
SPINNER = "[data-part='pending-spinner']"


@dataclass
class HeldRequests:
    """留めた要求。`release` で全て通す。"""

    routes: list[Route] = field(default_factory=list)

    def release(self) -> None:
        """留めた要求を全て通す。"""
        for route in self.routes:
            route.continue_()
        self.routes.clear()


def hold_requests(page: Page, pattern: str, method: str) -> HeldRequests:
    """`pattern` の `method` の要求を留め、ほかの要求はそのまま通す。"""
    held = HeldRequests()

    def handle(route: Route) -> None:
        """書き込みの要求だけ留める。"""
        # 書き込みのメソッド: 留める（テストが release で通す）
        if route.request.method == method:
            held.routes.append(route)
            return
        # 読み取りなど: そのまま通す
        route.continue_()

    page.route(pattern, handle)
    return held


def press_twice(button: Locator) -> None:
    """再描画の前に同じボタンを 2 回押す（1 回目の後の state の更新を待たない）。"""
    button.evaluate("button => { button.click(); button.click(); }")


def assert_waiting(page: Page, button: Locator, held: HeldRequests, width: float) -> None:
    """要求が 1 件だけ届き、待つ間はボタンが押せず、1 秒を超えると回るマーカーを出し、幅が押す前と同じかを確かめる。"""
    # 1 秒未満: 押せないが、回るマーカーはまだ出さない
    page.wait_for_timeout(SETTLE_MS)
    assert len(held.routes) == 1
    expect(button).to_be_disabled()
    expect(button).to_have_attribute("aria-busy", "true")
    expect(button.locator(SPINNER)).to_have_count(0)
    # 1 秒を超えた: 回るマーカーを重ね、幅は変えない
    page.wait_for_timeout(SPINNER_SHOWN_MS - SETTLE_MS)
    expect(button.locator(SPINNER)).to_have_count(1)
    box = button.bounding_box()
    assert box is not None
    assert box["width"] == width
