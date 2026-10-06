"""プレビューの E2E テストが共有する型と、画面を操作する補助。"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from workspace_fixtures import RECORD_DIR

__all__ = [
    "HttpResult",
    "COMMENTS_BUTTON",
    "COMMENTS_PANEL",
    "DETAIL_FORM",
    "DETAIL_MESSAGE",
    "DETAIL_TEXTAREA",
    "DRAWER",
    "DRAWER_OPEN",
    "FILTER_BADGE",
    "FILTER_BUTTON",
    "FREE_FORM",
    "FREE_TEXTAREA",
    "HISTORY_DIALOG",
    "HISTORY_REDRAW_TIMEOUT_MS",
    "HISTORY_ROW",
    "PILL",
    "OpenPreview",
    "ServePreview",
    "ServeWorkspace",
    "badge_text",
    "checked_values",
    "clear_condition",
    "click_item_ball",
    "close_drawer",
    "count_balls",
    "drawer_counts",
    "fetch_records",
    "http_call",
    "open_drawer",
    "pick_history_point",
    "row_ids",
    "select_text",
    "select_text_for_pill",
    "shown_ball_item_ids",
    "snapshot_records",
    "toggle_value",
    "visit_and_close",
]

type ServePreview = Callable[..., str]
type OpenPreview = Callable[..., Page]
type ServeWorkspace = Callable[..., tuple[str, Path]]

# トップバーのコメントのボタンと、コメントの一覧のパネル
COMMENTS_BUTTON = "header.topbar button.comments-btn"
COMMENTS_PANEL = "aside.comments-panel"

# トップバーの絞り込みのボタンと、値を選んでいる条件の数のバッジ
FILTER_BUTTON = "header.topbar button[data-act='filter']"
FILTER_BADGE = f"{FILTER_BUTTON} .fbadge"

# 絞り込みのドロワー（開いているときだけ `open` 属性を持つ）
DRAWER = "dialog.drawer"
DRAWER_OPEN = f"{DRAWER}[open]"

# 詳細パネルの下端のコメントの入力とその入力欄・結果
DETAIL_FORM = "aside.panel form.send"
DETAIL_TEXTAREA = "aside.panel form.send textarea"
DETAIL_MESSAGE = "aside.panel form.send .send-msg"

# コメントの一覧の下端の、項目を指さないコメントの入力とその入力欄
FREE_FORM = f"{COMMENTS_PANEL} .comments-free form.send"
FREE_TEXTAREA = f"{FREE_FORM} textarea"

# 選んだ箇所のコメントの入口
PILL = "button.selection-comment"

# 選んだ後に入口が出るまで待つ 1 回のミリ秒と、選び直す回数の上限（描き直しで選択が外れても選び直す）
PILL_WAIT_MS = 2_000
PILL_SELECT_ATTEMPTS = 5

# 要素の中の文を、始まりから終わりまで選ぶ
SELECT_TEXT_SCRIPT = """([selector, text]) => {
  const root = document.querySelector(selector);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const at = node.textContent.indexOf(text);
    if (at >= 0) {
      const range = document.createRange();
      range.setStart(node, at);
      range.setEnd(node, at + text.length);
      const selection = getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      return true;
    }
  }
  return false;
}"""

# つながりのキャンバスの上を調べる間隔（px）。玉の当たりの半径（12px 前後）より細かくして、玉を取りこぼさない
BALL_SCAN_STEP = 4

# 近い位置を同じ玉とみなす距離（px）
BALL_MERGE_DISTANCE = 24

# キャンバスの縁を調べないための余白（px）
CANVAS_MARGIN = 6

# 向きを変えて探し直す回数の上限と、1 回にキャンバスを横へドラッグする量（px）
BALL_MAX_TURNS = 6
BALL_TURN_DRAG_DISTANCE = 120

# ドラッグの途中で動きを止めずに送るマウスの移動の回数
BALL_TURN_DRAG_STEPS = 10

# カメラが止まったとみなす条件: 走査を間を空けて 2 回続け、どの玉も動いた距離がこの値（px）以下
BALL_STILL_DISTANCE = 1.5

# 走査の間隔（ミリ秒）と、止まるのを待つ走査の回数の上限
BALL_STILL_INTERVAL_MS = 250
BALL_STILL_MAX_SCANS = 60

# 玉を押した後に詳細が開くのを待つ上限（ミリ秒）。玉に当たっていなければ開かない
BALL_OPEN_TIMEOUT_MS = 1_500

# 玉の上でマウスのカーソルが指の形になることを、キャンバスの上を調べて集める
SCAN_BALLS_SCRIPT = """([step, margin]) => {
    const canvas = document.getElementById('graph-canvas');
    const rect = canvas.getBoundingClientRect();
    const found = [];
    for (let y = rect.top + margin; y < rect.bottom - margin; y += step) {
        for (let x = rect.left + margin; x < rect.right - margin; x += step) {
            canvas.dispatchEvent(new PointerEvent('pointermove', {clientX: x, clientY: y, bubbles: true}));
            if (canvas.style.cursor === 'pointer') found.push([x, y]);
        }
    }
    canvas.dispatchEvent(new PointerEvent('pointerleave', {bubbles: true}));
    return found;
}"""


# プレビューを開くたびに今の日時へ書き換わる、前回開いた日時のファイル
OPENED_FILE_NAME = f"{RECORD_DIR}/.mindstella-opened"

# 前回開いた日時（秒の単位）より後に書き換えが入るよう、開いて閉じた後に待つミリ秒
OPENED_TICK_MS = 1_100

# 一度開く画面が描き終わるまで待つ上限ミリ秒
VISIT_RENDER_TIMEOUT_MS = 20_000


# 変更履歴のモーダルと、時点の行
HISTORY_DIALOG = "dialog.hist"
HISTORY_ROW = f"{HISTORY_DIALOG} .hist-item"

# 時点を選んだ後に描き直るのを待つ上限ミリ秒
HISTORY_REDRAW_TIMEOUT_MS = 10_000


def pick_history_point(page: Page, name: str) -> None:
    """トップバーの「変更履歴」から、名前の合う時点を選び、差分の表示になるまで待つ。"""
    page.get_by_role("button", name="変更履歴").click()
    page.wait_for_selector(f"{HISTORY_DIALOG}[open]")
    page.locator(HISTORY_ROW).filter(has_text=name).click()
    page.wait_for_selector(".df-chip", timeout=HISTORY_REDRAW_TIMEOUT_MS)


def snapshot_records(snapshot: dict[str, bytes]) -> dict[str, bytes]:
    """フォルダの写しから、開くたびに書き換わる前回開いた日時のファイルを除いて返す。"""
    return {path: content for path, content in snapshot.items() if path != OPENED_FILE_NAME}


def visit_and_close(page: Page, url: str) -> None:
    """新しいタブでプレビューを一度開いて閉じ、前回開いた日時を残す。後の書き換えがその日時より後になるまで待つ。"""
    tab = page.context.new_page()
    tab.goto(url)
    tab.wait_for_selector("main#main > *", state="attached", timeout=VISIT_RENDER_TIMEOUT_MS)
    tab.close()
    page.wait_for_timeout(OPENED_TICK_MS)


def fetch_records(url: str) -> dict[str, Any]:
    """配信の URL から記録（`/api/records`）を読み、JSON のオブジェクトにして返す。"""
    with urllib.request.urlopen(urljoin(url, "/api/records"), timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


# 1 回の HTTP を待つ上限秒数
HTTP_TIMEOUT_SEC = 10


@dataclass(frozen=True)
class HttpResult:
    """HTTP の応答（ステータス・ヘッダー名を小文字にしたヘッダー・本文）。"""

    status: int
    headers: dict[str, str]
    text: str

    def json(self) -> dict[str, Any]:
        """本文を JSON のオブジェクトとして読む。"""
        return json.loads(self.text)


def http_call(
    url: str, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None
) -> HttpResult:
    """配信の URL のページの路に依らず、パスを足して 1 回つなぐ。ステータスが 4xx・5xx でも例外にせず、応答を返す。"""
    request = urllib.request.Request(  # noqa: S310
        urljoin(url, path),
        method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:  # noqa: S310
            return HttpResult(
                response.status,
                {name.lower(): value for name, value in response.getheaders()},
                response.read().decode("utf-8"),
            )
    except urllib.error.HTTPError as error:
        # 4xx・5xx: 応答の本文とヘッダーを読んで返す
        with error:
            return HttpResult(
                error.code,
                {name.lower(): value for name, value in error.headers.items()},
                error.read().decode("utf-8"),
            )


def select_text(page: Page, selector: str, text: str) -> None:
    """要素の中で最初に出てくる文を選ぶ。文が見つからなければ例外にする。"""
    found = page.evaluate(SELECT_TEXT_SCRIPT, [selector, text])
    if found is not True:
        raise AssertionError(f"{selector} の中に選ぶ文がありません: {text}")


def select_text_for_pill(page: Page, selector: str, text: str) -> None:
    """要素の中の文を選び、選んだ箇所のコメントの入口が出るまで待つ。画面の描き直しで選択が外れたときは選び直す。"""
    for _ in range(PILL_SELECT_ATTEMPTS):
        select_text(page, selector, text)
        try:
            page.wait_for_selector(PILL, timeout=PILL_WAIT_MS)
        except PlaywrightTimeoutError:
            continue
        return
    raise AssertionError(f"選んだ後に入口が出ませんでした: {selector} / {text}")


def row_ids(page: Page) -> list[str]:
    """表に並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")


def open_drawer(page: Page) -> None:
    """トップバーの絞り込みのボタンを押し、ドロワーが開くのを待つ。"""
    page.click(FILTER_BUTTON)
    page.wait_for_selector(DRAWER_OPEN)


def close_drawer(page: Page) -> None:
    """ドロワーの見出しの × を押して閉じ、ドロワーが無くなるのを待つ（開いている間は本文が操作できないため）。"""
    page.click(f"{DRAWER} button[aria-label='絞り込みを閉じる']")
    page.wait_for_selector(DRAWER, state="detached")


def toggle_value(page: Page, key: str, value: str) -> None:
    """ドロワーの条件 `key` の値 `value` の行を押して、選ぶ・外す。"""
    page.click(f'{DRAWER} label.fd-opt:has(input[data-key="{key}"][value="{value}"])')


def clear_condition(page: Page, label: str) -> None:
    """ドロワーの条件の見出し `label` の右の「解除」を押す。"""
    page.click(f"{DRAWER} button[aria-label='{label}の条件を解除']")


def checked_values(page: Page, key: str) -> list[str]:
    """ドロワーの条件 `key` でチェックの入った値を並びの順に返す。"""
    return page.eval_on_selector_all(
        f'{DRAWER} input[data-key="{key}"]:checked', "inputs => inputs.map(i => i.value)"
    )


def drawer_counts(page: Page, key: str) -> dict[str, int]:
    """ドロワーの条件 `key` の値ごとの件数を返す。"""
    return page.eval_on_selector_all(
        f'{DRAWER} label.fd-opt:has(input[data-key="{key}"])',
        "opts => Object.fromEntries(opts.map(o => [o.querySelector('.fd-v').textContent, Number(o.querySelector('.n').textContent)]))",
    )


def badge_text(page: Page) -> str | None:
    """絞り込みのボタンのバッジの数を返す。バッジが無ければ None。"""
    if page.locator(FILTER_BADGE).count() == 0:
        return None
    return page.inner_text(FILTER_BADGE)


def _find_ball_centers(page: Page) -> list[tuple[float, float]]:
    """カーソルが指の形になった位置を、近いものどうしでまとめた中心にして返す。"""
    found = page.evaluate(SCAN_BALLS_SCRIPT, [BALL_SCAN_STEP, CANVAS_MARGIN])
    clusters: list[list[tuple[float, float]]] = []
    for x, y in found:
        for cluster in clusters:
            if any(abs(x - cx) + abs(y - cy) <= BALL_MERGE_DISTANCE for cx, cy in cluster):
                cluster.append((x, y))
                break
        else:
            clusters.append([(x, y)])
    return [
        (sum(x for x, _ in cluster) / len(cluster), sum(y for _, y in cluster) / len(cluster))
        for cluster in clusters
    ]


def _settled_ball_centers(page: Page) -> list[tuple[float, float]]:
    """カメラが止まる（玉の位置が走査 2 回で動かなくなる）まで待って、玉の中心を返す。"""
    previous = _find_ball_centers(page)
    for _ in range(BALL_STILL_MAX_SCANS):
        page.wait_for_timeout(BALL_STILL_INTERVAL_MS)
        current = _find_ball_centers(page)
        still = len(current) == len(previous) and all(
            abs(x - px) <= BALL_STILL_DISTANCE and abs(y - py) <= BALL_STILL_DISTANCE
            for (x, y), (px, py) in zip(current, previous, strict=True)
        )
        if still and current:
            return current
        previous = current
    raise AssertionError("つながりのカメラが止まりませんでした")


def _turn_camera(page: Page) -> None:
    """つながりのキャンバスを横にドラッグして、玉を見る向きを変える（玉の上から始めても、押しではなくドラッグになる）。"""
    box = page.locator("#graph-canvas").bounding_box()
    assert box is not None
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + BALL_TURN_DRAG_DISTANCE, y, steps=BALL_TURN_DRAG_STEPS)
    page.mouse.up()


def _click_ball_in_view(page: Page, item_id: str) -> bool:
    """今の向きで見える玉を 1 つずつ押し、指定した項目の詳細が開いたら True を返す（全て試して開かなければ False）。"""
    # 押すたびに玉の数や並びが変わりうるので、玉の数だけ数えて、押すたびに探し直す
    ball_count = len(_settled_ball_centers(page))
    for index in range(ball_count):
        centers = _settled_ball_centers(page)
        x, y = centers[index % len(centers)]
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.up()
        try:
            page.wait_for_selector(
                "aside.panel.open .panel-kind .mono", timeout=BALL_OPEN_TIMEOUT_MS
            )
        except PlaywrightTimeoutError:
            # 玉に当たらなかった: 次の玉へ
            continue
        # 押した玉が目的の項目なら、そこで終える。違えば閉じて、カメラが止まるのを待って次の玉を押す
        if page.locator("aside.panel.open .panel-kind .mono").inner_text() == item_id:
            return True
        page.keyboard.press("Escape")
        page.wait_for_function("!document.querySelector('aside.panel.open')")
    return False


def click_item_ball(page: Page, item_id: str) -> None:
    """つながりのキャンバスで、指定した項目の玉を探して押す（玉の位置は画面に出ないので、押して開いた詳細で確かめる）。

    他の玉に隠れて見つからないときは、キャンバスをドラッグして向きを変え、カメラが止まってから探し直す。
    詳細パネルが開いたままだと、押した玉が開いている項目と同じかを見分けられず、カメラもその項目へ寄っているので、
    先にパネルを閉じて全体を見る位置に戻す。
    """
    if page.locator("aside.panel.open").count() > 0:
        page.keyboard.press("Escape")
        page.wait_for_function("!document.querySelector('aside.panel.open')")
    for turn in range(BALL_MAX_TURNS + 1):
        # 開いた直後の向きを最初に探し、見つからなければ向きを変えて探し直す（向きを変えるのは上限まで）
        if turn > 0:
            _turn_camera(page)
        if _click_ball_in_view(page, item_id):
            return
    raise AssertionError(f"つながりに {item_id} の玉が見つかりませんでした")


def count_balls(page: Page) -> int:
    """つながりのキャンバスに出ている玉の数を返す（近い玉どうしは 1 つに数える）。"""
    return len(_find_ball_centers(page))


def shown_ball_item_ids(page: Page) -> set[str]:
    """つながりのキャンバスに出ている玉を順に押し、開いた詳細から項目の ID を集めて返す。

    押すとカメラがその玉へ寄るので、押すたびに閉じて、カメラが止まるのを待ってから次の玉を探す。
    """
    ids: set[str] = set()
    ball_count = len(_settled_ball_centers(page))
    for index in range(ball_count):
        centers = _settled_ball_centers(page)
        x, y = centers[index % len(centers)]
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.up()
        try:
            page.wait_for_selector(
                "aside.panel.open .panel-kind .mono", timeout=BALL_OPEN_TIMEOUT_MS
            )
        except PlaywrightTimeoutError:
            # 玉に当たらなかった: 次の玉へ
            continue
        ids.add(page.locator("aside.panel.open .panel-kind .mono").inner_text())
        page.keyboard.press("Escape")
        page.wait_for_function("!document.querySelector('aside.panel.open')")
    return ids
