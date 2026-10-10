"""PoC: 成功条件を Playwright で測り、結果を JSON で書き出す。"""

from __future__ import annotations

import functools
import json
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Frame, Page, sync_playwright

from annotate import annotate, selection_matches

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
# 大きい資料の目安の大きさ（バイト）
LARGE_DOC_BYTES = 200_000
# 位置・高さの許す差（px）
TOLERANCE_PX = 1
# マウスで選ぶときの動かす回数と 1 回の幅（px）
DRAG_STEPS = 5
DRAG_STEP_PX = 12

# (名前, 選び始めの文, 選び終わりの文, 期待する行の範囲)。選び終わりの文の終わりまでを選ぶ
CASES: list[tuple[str, str, str, tuple[int, int]]] = [
    ("見出し", "見出しの文", "見出しの文", (12, 12)),
    ("段落の一行目", "一行目の文", "一行目の文", (13, 13)),
    ("段落の二行目", "二行目の文", "二行目の文", (14, 14)),
    ("段落の二行をまたぐ", "一行目の文", "二行目の文", (13, 14)),
    ("複数行の開きタグ", "複数行の開きタグの文", "複数行の開きタグの文", (16, 16)),
    ("閉じタグを省いた項目", "項目いち", "項目いち", (18, 18)),
    ("入れ子の項目", "入れ子の項目", "入れ子の項目", (19, 19)),
    ("項目をまたぐ", "項目いち", "入れ子の項目", (18, 19)),
    ("表の行", "表のさん", "表のよん", (23, 23)),
    ("改行の後", "あとの文", "あとの文", (26, 26)),
    ("ブロックをまたぐ", "見出しの文", "二行目の文", (12, 14)),
    ("コメント・スクリプトより後", "最後の文", "最後の文", (33, 33)),
]
# (名前, 行の範囲, 選んだ文)。原文に無い・描いた文に出ない文
NEGATIVE_CASES: list[tuple[str, tuple[int, int], str]] = [
    ("コメントの中の文", (11, 11), "コメントの中の段落"),
    ("スクリプトの中の文字列", (8, 8), "<p>x</p>"),
]

PAGE_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>PoC</title>
<style>
  body {{ font-family: sans-serif; margin: 0; padding: 16px; color: rgb(17, 17, 17); background: rgb(255, 255, 255); }}
  #probe {{ color: rgb(17, 17, 17); margin: 8px; }}
  #panel {{ width: 600px; }}
  dialog {{ width: 700px; }}
</style></head>
<body>
<p id="probe">親の画面の見本</p>
<div id="panel"></div>
<dialog id="full"><div id="full-holder"></div></dialog>
<script>{harness}</script>
<script>window.__docs = {docs};</script>
</body></html>
"""


def build_page() -> Path:
    """行の印を足した見本と大きい資料を埋め込んだ親の画面を書き出す。"""
    sample = (HERE / "sample.html").read_text(encoding="utf-8")
    # 大きい資料: 見本の body の中身を大きさの目安まで繰り返す
    body = sample.split("<body>", 1)[1].split("</body>", 1)[0]
    repeats = LARGE_DOC_BYTES // len(body.encode("utf-8")) + 1
    large = "<!doctype html><html><body>" + body * repeats + "</body></html>"
    docs = {"sample": annotate(sample), "large": annotate(large)}
    OUT.mkdir(exist_ok=True)
    page = OUT / "page.html"
    page.write_text(
        PAGE_TEMPLATE.format(
            harness=(HERE / "harness.js").read_text(encoding="utf-8"),
            # </script> で埋め込みが切れないよう、< を逃がす
            docs=json.dumps(docs, ensure_ascii=False).replace("<", "\\u003c"),
        ),
        encoding="utf-8",
    )
    return page


def private_memory_mb(pids: set[int]) -> float:
    """プロセスの私用メモリ（Private_Clean + Private_Dirty）の合計を MB で返す。"""
    total_kb = 0
    for pid in pids:
        rollup = Path(f"/proc/{pid}/smaps_rollup")
        # 測る間に終わったプロセスは数えない
        if not rollup.exists():
            continue
        for line in rollup.read_text().splitlines():
            if line.startswith(("Private_Clean:", "Private_Dirty:")):
                total_kb += int(line.split()[1])
    return total_kb / 1024


def chromium_pids() -> set[int]:
    """動いている Chromium（headless shell を含む）のプロセスの番号を返す。"""
    pids: set[int] = set()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if b"ms-playwright" in cmdline:
            pids.add(int(entry.name))
    return pids


def select_text(frame: Frame, start_text: str, end_text: str) -> None:
    """iframe の中で start_text の頭から end_text の終わりまでを選ぶ。"""
    frame.evaluate(
        """([startText, endText]) => {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let start = null, end = null;
          while (walker.nextNode()) {
            const node = walker.currentNode;
            if (!start && node.data.includes(startText)) start = [node, node.data.indexOf(startText)];
            if (start && node.data.includes(endText)) { end = [node, node.data.indexOf(endText) + endText.length]; break; }
          }
          const range = document.createRange();
          range.setStart(start[0], start[1]);
          range.setEnd(end[0], end[1]);
          const selection = getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
        }""",
        [start_text, end_text],
    )


def check_css(page: Page) -> dict[str, object]:
    """本文の CSS が親の画面の見本の要素に効いていないかを測る。"""
    style = page.evaluate(
        """() => { const s = getComputedStyle(document.getElementById('probe'));
                   const b = getComputedStyle(document.body);
                   return { color: s.color, margin: s.margin, bodyBg: b.backgroundColor, bodyColor: b.color }; }"""
    )
    expected = {"color": "rgb(17, 17, 17)", "margin": "8px", "bodyBg": "rgb(255, 255, 255)", "bodyColor": "rgb(17, 17, 17)"}
    return {"ok": style == expected, "measured": style}


def check_scripts(page: Page, frame: Frame) -> dict[str, object]:
    """本文のスクリプト・イベントの属性が動かないか（ボタンを押した後も印が 0 件か）を測る。"""
    frame.click("#click")
    page.wait_for_timeout(200)
    leaks = page.evaluate(
        "() => ({ parent: window.__leak || 0, frame: document.querySelector('#panel iframe').contentWindow.__leak || 0 })"
    )
    return {"ok": leaks == {"parent": 0, "frame": 0}, "measured": leaks}


def check_events(page: Page) -> dict[str, object]:
    """iframe の中をマウスで選んだとき、親が足した受け手が呼ばれるかを測る。"""
    # sandbox の iframe の上では page.mouse が返らないため、CDP で入力を送る
    box = page.evaluate(
        """() => { const f = document.querySelector('#panel iframe'); const el = f.contentDocument.getElementById('tail');
                   el.scrollIntoView({ block: 'center' }); const r = el.getBoundingClientRect(); const o = f.getBoundingClientRect();
                   return { x: o.left + r.left, y: o.top + r.top + r.height / 2 }; }"""
    )
    page.evaluate("() => { window.__events.pointerup = 0; window.__events.selectionchange = 0; }")
    cdp = page.context.new_cdp_session(page)

    def mouse(kind: str, x: float, buttons: int, **extra: object) -> None:
        cdp.send("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": box["y"], "button": "left", "buttons": buttons, **extra})

    mouse("mouseMoved", box["x"] + 2, 0)
    mouse("mousePressed", box["x"] + 2, 1, clickCount=1)
    for step in range(1, DRAG_STEPS + 1):
        mouse("mouseMoved", box["x"] + 2 + DRAG_STEP_PX * step, 1)
    mouse("mouseReleased", box["x"] + 2 + DRAG_STEP_PX * DRAG_STEPS, 0, clickCount=1)
    page.wait_for_timeout(300)
    counts = page.evaluate("() => ({ ...window.__events })")
    location = page.evaluate("() => poc.locate(document.querySelector('#panel iframe'))")
    return {"ok": counts["pointerup"] > 0 and counts["selectionchange"] > 0, "measured": counts, "location": location}


def check_rect(page: Page, frame: Frame, holder: str) -> dict[str, object]:
    """選択の位置（iframe の中の矩形 + iframe の位置）が、画面上の文の位置と合うかを測る。"""
    select_text(frame, "最後の文", "最後の文")
    computed = page.evaluate(f"() => poc.selectionRect(document.querySelector('{holder} iframe'))")
    box = page.frame_locator(f"{holder} iframe").locator("#tail").bounding_box()
    assert box is not None
    # #tail の文の頭は要素の内側の左上にある（本文の CSS の余白込み）
    actual = frame.evaluate(
        "() => { const r = document.createRange(); r.selectNodeContents(document.getElementById('tail')); const c = r.getClientRects()[0]; return { left: c.left, top: c.top }; }"
    )
    frame_box = page.locator(f"{holder} iframe").bounding_box()
    assert frame_box is not None
    expected = {"left": frame_box["x"] + actual["left"], "top": frame_box["y"] + actual["top"]}
    diff = max(abs(computed["left"] - expected["left"]), abs(computed["top"] - expected["top"]))
    return {"ok": diff <= TOLERANCE_PX, "diff_px": diff, "computed": computed, "expected": expected}


def check_height(page: Page, frame: Frame) -> dict[str, object]:
    """描いた直後と中身を足した後に、iframe の高さが中身の scrollHeight と合うかを測る。"""
    def gap() -> float:
        return page.evaluate(
            "() => { const f = document.querySelector('#panel iframe'); return Math.abs(f.getBoundingClientRect().height - f.contentDocument.documentElement.scrollHeight); }"
        )

    before = gap()
    frame.evaluate("() => { const p = document.createElement('p'); p.textContent = '足した段落'; p.style.height = '500px'; document.body.append(p); }")
    page.wait_for_timeout(300)
    after = gap()
    return {"ok": before <= TOLERANCE_PX and after <= TOLERANCE_PX, "before_px": before, "after_px": after}


def check_cases(page: Page, frame: Frame, source: str) -> dict[str, object]:
    """見本の選択ごとに、画面で求めた行の範囲とサーバー側の照らし合わせを測る。"""
    results = []
    for name, start_text, end_text, expected in CASES:
        select_text(frame, start_text, end_text)
        location = page.evaluate("() => poc.locate(document.querySelector('#panel iframe'))")
        got = (location["start"], location["end"])
        matched = selection_matches(source, got[0], got[1], location["text"])
        results.append({"name": name, "expected": expected, "got": got, "line_ok": got == expected, "server_ok": matched})
    negatives = [
        {"name": name, "matched": selection_matches(source, lines[0], lines[1], text)} for name, lines, text in NEGATIVE_CASES
    ]
    return {
        "lines_ok": sum(r["line_ok"] for r in results),
        "server_ok": sum(r["server_ok"] for r in results),
        "total": len(results),
        "negatives_rejected": sum(not n["matched"] for n in negatives),
        "cases": results,
        "negatives": negatives,
    }


def run_mode(page: Page, url: str, source: str) -> dict[str, object]:
    """1 つの開き方（http か file）で、全ての観点を測る。"""
    page.goto(url)
    page.evaluate("() => poc.mount(document.getElementById('panel'), window.__docs.sample).then(() => true)")
    frame = page.locator("#panel iframe").element_handle().content_frame()
    assert frame is not None
    result: dict[str, object] = {"css": check_css(page), "scripts": check_scripts(page, frame)}
    result["events"] = check_events(page)
    result["cases"] = check_cases(page, frame, source)
    result["rect_panel"] = check_rect(page, frame, "#panel")
    # 詳細の全画面と同じく、showModal の dialog の中の iframe でも位置を測る
    page.evaluate("() => { document.getElementById('full').showModal(); return poc.mount(document.getElementById('full-holder'), window.__docs.sample).then(() => true); }")
    full_frame = page.locator("#full-holder iframe").element_handle().content_frame()
    assert full_frame is not None
    result["rect_dialog"] = check_rect(page, full_frame, "#full-holder")
    page.evaluate("() => document.getElementById('full').close()")
    result["height"] = check_height(page, frame)
    return result


def run_memory(page: Page, url: str, others: set[int]) -> dict[str, object]:
    """大きい資料を描く前と後のブラウザ全体の私用メモリと、ページのヒープを測る。"""
    page.goto(url)
    page.wait_for_timeout(500)
    session = page.context.new_cdp_session(page)
    session.send("Performance.enable")

    def heap_mb() -> float:
        metrics = {m["name"]: m["value"] for m in session.send("Performance.getMetrics")["metrics"]}
        return metrics["JSHeapUsedSize"] / 1024 / 1024

    before = {"private_mb": private_memory_mb(chromium_pids() - others), "heap_mb": heap_mb()}
    size = page.evaluate("() => new Blob([window.__docs.large]).size")
    page.evaluate("() => poc.mount(document.getElementById('panel'), window.__docs.large).then(() => true)")
    page.wait_for_timeout(1000)
    after = {"private_mb": private_memory_mb(chromium_pids() - others), "heap_mb": heap_mb()}
    return {"doc_bytes": size, "before": before, "after": after, "delta_private_mb": after["private_mb"] - before["private_mb"]}


def main() -> int:
    """http と file の両方で測り、メモリを測って結果を書き出す。"""
    page_path = build_page()
    source = (HERE / "sample.html").read_text(encoding="utf-8")
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(OUT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    http_url = f"http://127.0.0.1:{server.server_address[1]}/page.html"
    results: dict[str, object] = {}
    with sync_playwright() as playwright:
        before_launch = chromium_pids()
        browser = playwright.chromium.launch()
        browser_pids = chromium_pids() - before_launch
        results["browser"] = {"name": "chromium", "version": browser.version, "pids": len(browser_pids)}
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        results["http"] = run_mode(page, http_url, source)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        results["file"] = run_mode(page, page_path.as_uri(), source)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        results["memory"] = run_memory(page, http_url, before_launch)
        browser.close()
    server.shutdown()
    (OUT / "result.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    os.chdir(HERE)
    sys.exit(main())
