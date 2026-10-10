"""ネットワークの画面の結合テストが共有する値と、キャンバスを外から観測する関数。

玉・鍵・状態の印はキャンバスの絵なので、DOM では読めない。次の 2 つで観測する。

- 当たり判定: 玉の上ではカーソルが `pointer`、余白では `grab` になる。キャンバスへ `pointermove` を送って走査すれば、玉の位置が分かる
- 絵の比較: 動きを減らす設定にして画面を静止させ、領域の画素を取っておき、後の画素との違いの数を数える
"""

from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import Page

__all__ = [
    "CANVAS",
    "CENTER_REGION",
    "ball_at",
    "ball_centers",
    "blank_point",
    "canvas_center",
    "canvas_hash",
    "changed_pixels",
    "click_at",
    "free_point_near",
    "install_key_spy",
    "install_status_mark_spy",
    "is_moving",
    "key_draws",
    "nearest_ball",
    "other_ball",
    "remember_pixels",
    "settle",
    "status_marks",
]

# キャンバス
CANVAS = "#graph-canvas"

# 操作の後、少なくとも待つミリ秒（動きを減らす設定でも、視点と濃さが目標へ寄る動きはしばらく続く）
_MIN_SETTLE_MS = 1_500

# 画が止まったと見なす、2 回の読み取りの間隔と、その間に変わってよい画素の数
_STILL_INTERVAL_MS = 500
_STILL_PIXELS = 20

# 絵の比較に使う、キャンバスの中心から左右・上下へ取る半分の幅と高さ（CSS ピクセル）。名前・鍵・状態の印が入る
CENTER_REGION = {"half_width": 260, "half_height": 150}

# 玉の位置を探すときの、走査の間隔（CSS ピクセル）と、同じ玉と見なす距離
_SCAN_STEP = 10
_SAME_BALL_DISTANCE = 24

# 余白の点をキャンバスの隅から取る内側の距離と、中心の玉から離れた玉と見なす距離（CSS ピクセル）
_BLANK_MARGIN = 24
_OTHER_BALL_DISTANCE = 80

# 玉に当たらない点を探すときの、候補の点の間隔（CSS ピクセル）
_FREE_POINT_STEP = 2

# 絵の比較で、違いと見なす 1 色の差
_PIXEL_TOLERANCE = 8

# キャンバスの全面へ `pointermove` を送り、カーソルが `pointer`（玉の上）になった点を返す
_SCAN_SCRIPT = """(step) => {
    const canvas = document.getElementById('graph-canvas');
    const rect = canvas.getBoundingClientRect();
    const hits = [];
    for (let y = step / 2; y < rect.height; y += step) {
        for (let x = step / 2; x < rect.width; x += step) {
            canvas.dispatchEvent(new PointerEvent('pointermove', {clientX: rect.left + x, clientY: rect.top + y, bubbles: true}));
            if (canvas.style.cursor === 'pointer') hits.push([rect.left + x, rect.top + y]);
        }
    }
    canvas.dispatchEvent(new PointerEvent('pointerleave', {bubbles: true}));
    return hits;
}"""

# 1 点へ `pointermove` を送り、玉の上かを返す
_HIT_SCRIPT = """([x, y]) => {
    const canvas = document.getElementById('graph-canvas');
    canvas.dispatchEvent(new PointerEvent('pointermove', {clientX: x, clientY: y, bubbles: true}));
    const hit = canvas.style.cursor === 'pointer';
    canvas.dispatchEvent(new PointerEvent('pointerleave', {bubbles: true}));
    return hit;
}"""

# 点から `range` 未満の距離にある点を近い順に並べ、`pointermove` を送ってカーソルが `pointer`（玉の上）にならない最初の点を返す（無ければ null）
_FREE_POINT_SCRIPT = """([x, y, range, step]) => {
    const canvas = document.getElementById('graph-canvas');
    const offsets = [];
    for (let dy = -range; dy <= range; dy += step) {
        for (let dx = -range; dx <= range; dx += step) {
            if (Math.hypot(dx, dy) < range) offsets.push([dx, dy]);
        }
    }
    offsets.sort((a, b) => Math.hypot(a[0], a[1]) - Math.hypot(b[0], b[1]));
    let found = null;
    for (const [dx, dy] of offsets) {
        canvas.dispatchEvent(new PointerEvent('pointermove', {clientX: x + dx, clientY: y + dy, bubbles: true}));
        if (canvas.style.cursor !== 'pointer') {
            found = [x + dx, y + dy];
            break;
        }
    }
    canvas.dispatchEvent(new PointerEvent('pointerleave', {bubbles: true}));
    return found;
}"""

# 領域の画素を名前を付けて取っておく
_REMEMBER_SCRIPT = """([name, region]) => {
    const canvas = document.getElementById('graph-canvas');
    const ratio = canvas.width / canvas.clientWidth;
    const data = canvas.getContext('2d').getImageData(
        Math.max(0, Math.round(region.left * ratio)), Math.max(0, Math.round(region.top * ratio)),
        Math.round(region.width * ratio), Math.round(region.height * ratio),
    ).data;
    window.__shots = window.__shots ?? {};
    window.__shots[name] = data;
}"""

# キャンバスの全面を一定の間隔で 2 回読み、変わった画素が少ないかを返す
_STILL_SCRIPT = """async ({interval, limit, tolerance}) => {
    const canvas = document.getElementById('graph-canvas');
    const read = () => canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    const a = read();
    await new Promise((resolve) => setTimeout(resolve, interval));
    const b = read();
    let changed = 0;
    for (let i = 0; i < a.length; i += 4) {
        if (Math.abs(a[i] - b[i]) > tolerance || Math.abs(a[i + 1] - b[i + 1]) > tolerance
            || Math.abs(a[i + 2] - b[i + 2]) > tolerance || Math.abs(a[i + 3] - b[i + 3]) > tolerance) changed++;
    }
    return changed <= limit;
}"""

# キャンバスの全面の画素から求めた文字列（同じ絵なら同じ、違う絵なら違う）を返す
_HASH_SCRIPT = """() => {
    const canvas = document.getElementById('graph-canvas');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let hash = 2166136261;
    for (let i = 0; i < data.length; i++) hash = Math.imul(hash ^ data[i], 16777619);
    return String(hash >>> 0);
}"""

# 状態の印は SVG の画像を `drawImage` で置く（名前や光は別の種類の絵）。置いた画像の外形と出所を、コマごとに控える
_SPY_SCRIPT = """() => {
    window.__frame = 0;
    window.__statusMarks = [];
    const tick = () => { window.__frame++; requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    const original = CanvasRenderingContext2D.prototype.drawImage;
    CanvasRenderingContext2D.prototype.drawImage = function (image, ...rest) {
        if (image instanceof HTMLImageElement && image.src.startsWith('data:image/svg+xml')) {
            window.__statusMarks.push({
                frame: window.__frame, source: image.src, x: rest[0], y: rest[1], width: rest[2], height: rest[3], alpha: this.globalAlpha,
            });
        }
        return original.call(this, image, ...rest);
    };
}"""

# 印を置いた最後のコマの状態の印を返す。直近のコマで置いていなければ空
_MARKS_SCRIPT = """() => {
    const last = Math.max(0, ...window.__statusMarks.map((mark) => mark.frame));
    const current = window.__frame;
    return last >= current - 2 ? window.__statusMarks.filter((mark) => mark.frame === last) : [];
}"""

# 鍵は `Path2D` の線で描く。`Path2D` に元の文字列を持たせ、`stroke` へ渡された鍵の線（閉じた鍵・開いた鍵の輪）と、
# 札の円（半径 KEY_SIZE * 0.85）を、コマごとに控える
_KEY_SPY_SCRIPT = """() => {
    const LOCK = 'M7 11V7a5 5 0 0 1 10 0v4';
    const UNLOCK = 'M7 11V7a5 5 0 0 1 9.9-1';
    window.__keyFrame = 0;
    window.__keyDraws = [];
    window.__keyBadges = [];
    const tick = () => { window.__keyFrame++; requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    const Original = window.Path2D;
    window.Path2D = class extends Original {
        constructor(d) { super(d); this.__d = d; }
    };
    const proto = CanvasRenderingContext2D.prototype;
    const stroke = proto.stroke;
    proto.stroke = function (path) {
        if (path && (path.__d === LOCK || path.__d === UNLOCK)) {
            const t = this.getTransform();
            window.__keyDraws.push({
                frame: window.__keyFrame, closed: path.__d === LOCK, left: t.e, top: t.f, size: t.a * 24,
                alpha: this.globalAlpha, ratio: window.devicePixelRatio,
            });
        }
        return stroke.apply(this, arguments);
    };
    const arc = proto.arc;
    proto.arc = function (x, y, r) {
        if (Math.abs(r - 10.2) < 0.01) window.__keyBadges.push({frame: window.__keyFrame});
        return arc.apply(this, arguments);
    };
}"""

# 鍵を描いた最後のコマの鍵を返す（直近のコマで描いていなければ空）。左・上・一辺は CSS ピクセル
_KEY_DRAWS_SCRIPT = """() => {
    const draws = window.__keyDraws;
    const last = Math.max(0, ...draws.map((draw) => draw.frame));
    if (draws.length === 0 || last < window.__keyFrame - 2) return [];
    const badge = window.__keyBadges.some((item) => item.frame === last);
    return draws.filter((draw) => draw.frame === last).map((draw) => ({
        closed: draw.closed, left: draw.left / draw.ratio, top: draw.top / draw.ratio, size: draw.size / draw.ratio,
        alpha: draw.alpha, badge,
    }));
}"""

# 取っておいた画素と今の画素で、違う画素の数を返す
_CHANGED_SCRIPT = """([name, region, tolerance]) => {
    const canvas = document.getElementById('graph-canvas');
    const ratio = canvas.width / canvas.clientWidth;
    const now = canvas.getContext('2d').getImageData(
        Math.max(0, Math.round(region.left * ratio)), Math.max(0, Math.round(region.top * ratio)),
        Math.round(region.width * ratio), Math.round(region.height * ratio),
    ).data;
    const before = window.__shots[name];
    let changed = 0;
    for (let i = 0; i < now.length; i += 4) {
        if (Math.abs(now[i] - before[i]) > tolerance || Math.abs(now[i + 1] - before[i + 1]) > tolerance
            || Math.abs(now[i + 2] - before[i + 2]) > tolerance || Math.abs(now[i + 3] - before[i + 3]) > tolerance) changed++;
    }
    return changed;
}"""


def install_key_spy(page: Page) -> None:
    """鍵を描いた線を控える仕掛けを、ページを開く前に入れる。"""
    page.add_init_script(f"({_KEY_SPY_SCRIPT})()")


def key_draws(page: Page) -> list[dict[str, Any]]:
    """直近のコマで描いた鍵（閉じているか・左・上・一辺・濃さ・札の中か）を返す。描いていなければ空。"""
    draws: list[dict[str, Any]] = page.evaluate(_KEY_DRAWS_SCRIPT)
    return draws


def install_status_mark_spy(page: Page) -> None:
    """状態の印を置いた絵を控える仕掛けを、ページを開く前に入れる。"""
    page.add_init_script(f"({_SPY_SCRIPT})()")


def status_marks(page: Page) -> list[dict[str, Any]]:
    """直近のコマで置いた状態の印（出所・位置・大きさ・濃さ）を返す。"""
    marks: list[dict[str, Any]] = page.evaluate(_MARKS_SCRIPT)
    return marks


def canvas_center(page: Page) -> tuple[float, float]:
    """キャンバスの中心（画面の座標）を返す。項目を選ぶと、その玉が中心へ寄る。"""
    box = page.locator(CANVAS).bounding_box()
    assert box is not None
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _center_region(page: Page) -> dict[str, float]:
    """キャンバスの中心まわりの領域を、キャンバスの左上からの CSS ピクセルで返す。"""
    box = page.locator(CANVAS).bounding_box()
    assert box is not None
    return {
        "left": box["width"] / 2 - CENTER_REGION["half_width"],
        "top": box["height"] / 2 - CENTER_REGION["half_height"],
        "width": CENTER_REGION["half_width"] * 2,
        "height": CENTER_REGION["half_height"] * 2,
    }


def ball_centers(page: Page) -> list[tuple[float, float]]:
    """キャンバスを走査して、玉の位置（画面の座標。近い点を 1 つにまとめた中心）を返す。"""
    hits: list[list[float]] = page.evaluate(_SCAN_SCRIPT, _SCAN_STEP)
    groups: list[list[list[float]]] = []
    for point in hits:
        # 既にある玉の近くの点は、その玉の点として足す
        for group in groups:
            mean_x = sum(p[0] for p in group) / len(group)
            mean_y = sum(p[1] for p in group) / len(group)
            if abs(point[0] - mean_x) + abs(point[1] - mean_y) <= _SAME_BALL_DISTANCE:
                group.append(point)
                break
        else:
            groups.append([point])
    return [
        (sum(p[0] for p in group) / len(group), sum(p[1] for p in group) / len(group))
        for group in groups
    ]


def ball_at(page: Page, x: float, y: float) -> bool:
    """画面の点に玉があるか（カーソルが玉の上になるか）を返す。"""
    hit: bool = page.evaluate(_HIT_SCRIPT, [x, y])
    return hit


def blank_point(page: Page) -> tuple[float, float]:
    """キャンバスの余白（玉に当たらない点。右上の見た目のドロップダウンと重ならない隅）の画面の座標を返す。"""
    box = page.locator(CANVAS).bounding_box()
    assert box is not None
    corners = [
        (box["x"] + _BLANK_MARGIN, box["y"] + box["height"] - _BLANK_MARGIN),
        (box["x"] + box["width"] - _BLANK_MARGIN, box["y"] + box["height"] - _BLANK_MARGIN),
        (box["x"] + _BLANK_MARGIN, box["y"] + _BLANK_MARGIN),
    ]
    for x, y in corners:
        if not ball_at(page, x, y):
            return x, y
    raise AssertionError("余白の点が見つからない")


def other_ball(page: Page) -> tuple[float, float]:
    """キャンバスの中心にある玉から離れた玉の位置（画面の座標）を返す。"""
    cx, cy = canvas_center(page)
    for x, y in ball_centers(page):
        if abs(x - cx) + abs(y - cy) > _OTHER_BALL_DISTANCE:
            return x, y
    raise AssertionError("中心から離れた玉が見つからない")


def nearest_ball(page: Page, x: float, y: float) -> tuple[float, float]:
    """画面の点に最も近い玉の位置（画面の座標）を返す。押した後に少し動く玉を探し直すときに使う。"""
    centers = ball_centers(page)
    assert centers, "玉が見つからない"
    return min(centers, key=lambda center: abs(center[0] - x) + abs(center[1] - y))


def canvas_hash(page: Page) -> str:
    """キャンバスの全面の絵を表す文字列を返す。"""
    value: str = page.evaluate(_HASH_SCRIPT)
    return value


def click_at(page: Page, x: float, y: float) -> None:
    """画面の点を押す（動かさずに離すので、玉か余白を押した扱いになる）。押した後はマウスを動かさない。"""
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.up()


def free_point_near(page: Page, x: float, y: float, within: float) -> tuple[float, float]:
    """画面の点から `within` 未満の距離で、玉に当たらない最も近い点（画面の座標）を返す。玉に当たる点しか無ければ失敗する。"""
    point: list[float] | None = page.evaluate(_FREE_POINT_SCRIPT, [x, y, within, _FREE_POINT_STEP])
    if point is None:
        raise AssertionError("玉に当たらない点が見つからない")
    return point[0], point[1]


def remember_pixels(page: Page, name: str) -> None:
    """キャンバスの中心まわりの画素を、名前を付けて取っておく。"""
    page.evaluate(_REMEMBER_SCRIPT, [name, _center_region(page)])


def changed_pixels(page: Page, name: str) -> int:
    """取っておいた画素と今の画素で、違う画素の数を返す。"""
    count: int = page.evaluate(_CHANGED_SCRIPT, [name, _center_region(page), _PIXEL_TOLERANCE])
    return count


def is_moving(page: Page) -> bool:
    """間隔を空けた 2 回の読み取りで、キャンバスの画が（許容を超えて）変わっているかを返す。"""
    args = {"interval": _STILL_INTERVAL_MS, "limit": _STILL_PIXELS, "tolerance": _PIXEL_TOLERANCE}
    return not page.evaluate(_STILL_SCRIPT, args)


def settle(page: Page, *, timeout_ms: int = 20_000) -> None:
    """操作の後、視点と濃さが収まり、画がほぼ止まる（0.5 秒の間に変わる画素が少ない）まで待つ。動きを減らす設定で使う。"""
    deadline = time.monotonic() + timeout_ms / 1000
    page.wait_for_timeout(_MIN_SETTLE_MS)
    args = {"interval": _STILL_INTERVAL_MS, "limit": _STILL_PIXELS, "tolerance": _PIXEL_TOLERANCE}
    # 画が止まるまで、間隔を空けた 2 回の読み取りを繰り返す
    while not page.evaluate(_STILL_SCRIPT, args):
        assert time.monotonic() < deadline, "画が止まらない"
