"""ネットワークの 5 つの見た目の検証用ページを Chrome で開き、操作ごとのコマの落ち方・処理時間・メモリを測る。

前回の PoC（poc/graph3d/measure.py）の操作と集計をそのまま使い、見た目・ライト / ダークと、
1 つの星をロックしたままの拡大・縮小・回転を足す。
"""

from __future__ import annotations

import json
import math
import os
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

PAGE = Path(__file__).resolve().parent / "index.html"
# 既に立っている Chromium 系のブラウザへつなぐときの CDP の URL（無ければ Playwright の Chromium を開く）
CDP_URL = os.environ.get("CDP_URL")
# ブラウザから見たページの URL（Windows 側のブラウザでは、WSL のファイルの代わりに HTTP で配る）
PAGE_URL = os.environ.get("PAGE_URL", PAGE.as_uri())
# 計測用のブラウザのプロセスを見分ける --user-data-dir の一部（Windows のブラウザでメモリを測るとき）
MEM_PROFILE = os.environ.get("MEM_PROFILE")
# 描き方（baked は作り直した描き方。空は見本の描き方のまま）
DRAW = os.environ.get("DRAW", "")
# 線をまとめるか（0 はまとめず 1 本ずつ引く。作り直した描き方で使う）
BATCH = os.environ.get("BATCH", "")
MB = 1024 * 1024
# 画面のリフレッシュレートに合わせた落ちたコマ: 間隔の中央値のこの倍を超えたコマ
REL_DROP_FACTOR = 1.5

# 計測の条件（PoC の方針のとおり）
COUNT = 1000
LOOKS = ["glow", "starlight", "constellation", "deep", "dust"]
THEMES = ["dark", "light"]
VIEWPORTS = [(1280, 800), (1920, 1080)]
SCALES = [1, 2]

# 1 操作を続ける秒数
OP_SECONDS = 5.0
# 開いてから力学が落ち着くまで待つ秒数（前回の PoC と同じ）
SETTLE_SECONDS = 9.0
# ロックしてから、寄る動きが収まるまで待つ秒数
LOCK_SETTLE_SECONDS = 3.0
# 操作と操作の間に置く秒数
OP_GAP_SECONDS = 1.0
# 操作の入力を送る間隔（60Hz の 1 コマ）
INPUT_INTERVAL = 1 / 60
# 拡大・縮小の向きを入れ替える秒数
ZOOM_FLIP_SECONDS = 0.5
# ホイールの 1 回の量
WHEEL_DELTA = 40
# 回転のドラッグで描く円の半径（px）と 1 周の秒数
DRAG_RADIUS = 160
DRAG_PERIOD = 2.0
# 押下: 開く → 閉じる を繰り返す間隔（秒）
PRESS_STEP = 1.25
# 閉じるときに押す背景の、キャンバスの左上からのずれ（px）
BACKGROUND_OFFSET = 12
# ロック中に鍵を震わせる間隔（秒）。震えは 0.9 秒で収まるので、ほぼ途切れずに震わせ続ける
SHAKE_STEP = 1.0

# 合否の基準
DROP_MS = 25.0  # 1.5 コマ分
DROP_RATIO_MAX = 0.01
WORK_P95_MAX = 8.0
LONGTASK_MAX = 0
MEMORY_MAX_MB = 1706.0  # 決定値の 2GB を安全率 20% で割った値
PERCENTILE = 0.95


def percentile(values: list[float], q: float) -> float:
    """q 分位の値を返す（値が無ければ 0）。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1)]


def summarize(raw: dict[str, list[float]]) -> dict[str, Any]:
    """記録から、落ちたコマの割合・処理時間の p95・長いタスクの数と合否をまとめる。"""
    intervals = raw["intervals"]
    dropped = sum(1 for v in intervals if v > DROP_MS)
    ratio = dropped / len(intervals) if intervals else 1.0
    work95 = percentile(raw["work"], PERCENTILE)
    longtasks = len(raw["longtasks"])
    # リフレッシュレートが 60Hz でない画面向けに、間隔の中央値の 1.5 倍を超えたコマも数える
    median = statistics.median(intervals) if intervals else 0.0
    rel_dropped = sum(1 for v in intervals if v > median * REL_DROP_FACTOR)
    return {
        "frames": len(intervals),
        "interval_median": round(median, 2),
        "rel_drop_ratio": round(rel_dropped / len(intervals), 4) if intervals else 1.0,
        "dropped": dropped,
        "drop_ratio": round(ratio, 4),
        "work_p95": round(work95, 2),
        "work_max": round(max(raw["work"], default=0.0), 2),
        "longtasks": longtasks,
        "ok": ratio <= DROP_RATIO_MAX and work95 <= WORK_P95_MAX and longtasks <= LONGTASK_MAX,
    }


def canvas_box(page: Page) -> dict[str, float]:
    """キャンバスの画面上の位置と大きさを返す。"""
    box = page.locator("#fg3").bounding_box()
    # 描けていない: キャンバスが無ければ測れない
    if box is None:
        raise RuntimeError("キャンバスが画面にありません")
    return box


def keep_going(page: Page, start: float, shake: bool, last_shake: list[float]) -> bool:
    """操作を続けるかを返す。shake のときは、間隔ごとに鍵を震わせる。"""
    now = time.monotonic()
    # ロック中: 前に震わせてから間隔が経っていれば、もう一度震わせる
    if shake and now - last_shake[0] >= SHAKE_STEP:
        page.evaluate("window.__shake()")
        last_shake[0] = now
    return now - start < OP_SECONDS


def op_zoom(page: Page, shake: bool = False) -> None:
    """マウスを中心に置き、拡大と縮小を半秒ごとに入れ替えながらホイールを送り続ける。"""
    box = canvas_box(page)
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    start, last_shake = time.monotonic(), [-SHAKE_STEP]
    while keep_going(page, start, shake, last_shake):
        # 半秒ごとに、寄る（負）と離れる（正）を入れ替える
        sign = -1 if int((time.monotonic() - start) / ZOOM_FLIP_SECONDS) % 2 == 0 else 1
        page.mouse.wheel(0, sign * WHEEL_DELTA)
        time.sleep(INPUT_INTERVAL)


def op_rotate(page: Page, shake: bool = False) -> None:
    """押したまま、円を描くようにドラッグし続ける。"""
    box = canvas_box(page)
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx + DRAG_RADIUS, cy)
    page.mouse.down()
    start, last_shake = time.monotonic(), [-SHAKE_STEP]
    while keep_going(page, start, shake, last_shake):
        a = 2 * math.pi * (time.monotonic() - start) / DRAG_PERIOD
        page.mouse.move(cx + DRAG_RADIUS * math.cos(a), cy + DRAG_RADIUS * math.sin(a))
        time.sleep(INPUT_INTERVAL)
    page.mouse.up()


def op_press(page: Page) -> None:
    """中心に近い玉を押して開き、背景を押して閉じる、を繰り返す。"""
    box = canvas_box(page)
    start = time.monotonic()
    last_id: str | None = None
    step = 0
    while time.monotonic() - start < OP_SECONDS:
        # 偶数の段: 前と違う玉を押して開く / 奇数の段: 左上の背景を押して閉じる
        if step % 2 == 0:
            node = page.evaluate("(skip) => window.__pickNode(skip)", last_id)
            page.mouse.click(node["x"], node["y"])
            last_id = node["id"]
        else:
            page.mouse.click(box["x"] + BACKGROUND_OFFSET, box["y"] + BACKGROUND_OFFSET)
        step += 1
        time.sleep(max(0.0, start + step * PRESS_STEP - time.monotonic()))


# 操作の名前 → (ロックしたまま行うか, 操作)
OPS: dict[str, tuple[bool, Callable[[Page], None]]] = {
    "zoom": (False, op_zoom),
    "rotate": (False, op_rotate),
    "press": (False, op_press),
    "lock_zoom": (True, lambda page: op_zoom(page, shake=True)),
    "lock_rotate": (True, lambda page: op_rotate(page, shake=True)),
}


def measure_op(page: Page, op: str) -> dict[str, Any]:
    """1 つの操作の間だけ記録して、まとめを返す。ロックの操作は、ロックして寄り終えてから記録する。"""
    locked, run = OPS[op]
    # ロックの操作: つながりの多い玉をロックし、寄る動きが収まるのを待つ
    if locked:
        page.evaluate("window.__lockNode()")
        time.sleep(LOCK_SETTLE_SECONDS)
    page.evaluate("window.__startRec()")
    run(page)
    raw = page.evaluate("window.__stopRec()")
    # ロックの操作の後: ロックを外して詳細を閉じ、次の操作へ持ち越さない
    if locked:
        page.evaluate("window.__unlock()")
    return summarize(raw)


def js_heap_mb(page: Page) -> float:
    """ページの JavaScript のヒープの使用量（MB）を CDP の Performance.getMetrics で返す。"""
    cdp = page.context.new_cdp_session(page)
    cdp.send("Performance.enable")
    metrics = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    cdp.detach()
    return round(metrics["JSHeapUsedSize"] / MB, 1)


def browser_memory_mb() -> float | None:
    """計測に使うブラウザの全てのプロセスの私用メモリ（MB）の合計を返す。Windows のブラウザでないときは None。"""
    # MEM_PROFILE: 計測用のブラウザだけを拾うための、--user-data-dir に含まれる文字列
    if not MEM_PROFILE:
        return None
    script = (
        "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*" + MEM_PROFILE + "*' } "
        "| Measure-Object -Property PrivatePageCount -Sum).Sum"
    )
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, check=True)
    return round(float(out.stdout.strip()) / MB, 1)


def main() -> None:
    """全ての条件を測り、1 行 1 件の JSON を書き足す。引数: 書き出し先・見た目（カンマ区切り。任意）・ライト / ダーク（任意）。"""
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results.jsonl")
    looks = sys.argv[2].split(",") if len(sys.argv) > 2 else LOOKS
    themes = sys.argv[3].split(",") if len(sys.argv) > 3 else THEMES
    with sync_playwright() as pw, out.open("a", encoding="utf-8") as f:
        browser = pw.chromium.connect_over_cdp(CDP_URL) if CDP_URL else pw.chromium.launch(headless=False)
        for look in looks:
            for theme in themes:
                for width, height in VIEWPORTS:
                    for scale in SCALES:
                        base_mem = browser_memory_mb()
                        ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale)
                        page = ctx.new_page()
                        page.goto(f"{PAGE_URL}?n={COUNT}&theme={theme}&look={look}&draw={DRAW}&batch={BATCH}")
                        time.sleep(SETTLE_SECONDS)
                        for op in OPS:
                            row = {"look": look, "theme": theme, "n": COUNT, "viewport": f"{width}x{height}", "scale": scale, "op": op, **measure_op(page, op)}
                            # 操作の直後: ページの JavaScript のヒープと、ブラウザ全体の私用メモリ
                            row["js_heap_mb"] = js_heap_mb(page)
                            if base_mem is not None:
                                now_mem = browser_memory_mb()
                                row["browser_mem_mb"] = now_mem
                                row["browser_mem_delta_mb"] = round(now_mem - base_mem, 1)
                                row["mem_ok"] = now_mem <= MEMORY_MAX_MB
                            line = json.dumps(row, ensure_ascii=False)
                            print(line, flush=True)
                            f.write(line + "\n")
                            f.flush()
                            time.sleep(OP_GAP_SECONDS)
                        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
