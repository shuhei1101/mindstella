"""どの描き足しが重いかを切り分ける。描き足しを 1 つずつ外したページで、回転とロックしたままの回転を測る。

引数: 書き出し先・見た目:ライト / ダーク:表示の幅:倍率 の並び（カンマ区切り）・外す描き足しの組（`;` 区切り。空は何も外さない）。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from measure import CDP_URL, COUNT, OP_GAP_SECONDS, PAGE_URL, SETTLE_SECONDS, browser_memory_mb, js_heap_mb, measure_op

# 切り分けで測る操作: 操作の入力が軽く、描画の重さがそのまま出る回転と、ロックしたままの回転
OPS = ["rotate", "lock_rotate"]


def main() -> None:
    """条件と外す描き足しの組ごとに測り、1 行 1 件の JSON を書き足す。"""
    out = Path(sys.argv[1])
    cases = [c.split(":") for c in sys.argv[2].split(",")]
    offs = sys.argv[3].split(";")
    with sync_playwright() as pw, out.open("a", encoding="utf-8") as f:
        browser = pw.chromium.connect_over_cdp(CDP_URL)
        for look, theme, viewport, scale in cases:
            width, height = (int(v) for v in viewport.split("x"))
            for off in offs:
                base_mem = browser_memory_mb()
                ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=int(scale))
                page = ctx.new_page()
                page.goto(f"{PAGE_URL}?n={COUNT}&theme={theme}&look={look}&off={off}")
                time.sleep(SETTLE_SECONDS)
                for op in OPS:
                    row = {"look": look, "theme": theme, "viewport": viewport, "scale": int(scale), "off": off, "op": op, **measure_op(page, op)}
                    row["js_heap_mb"] = js_heap_mb(page)
                    # Windows のブラウザで測るとき: ブラウザ全体の私用メモリと、開く前からの増え分
                    if base_mem is not None:
                        now_mem = browser_memory_mb()
                        row["browser_mem_mb"] = now_mem
                        row["browser_mem_delta_mb"] = round(now_mem - base_mem, 1)
                    line = json.dumps(row, ensure_ascii=False)
                    print(line, flush=True)
                    f.write(line + "\n")
                    f.flush()
                    time.sleep(OP_GAP_SECONDS)
                ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
