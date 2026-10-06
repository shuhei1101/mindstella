"""差分の表示の切り替えの時間を、案（環境変数 POC = A / D / E の組み合わせ。空は今の版）ごとに 5 回測る。tester の difftime2.py と同じ測り方に、内訳・差分の中身・load average・ヒープを足した"""
import json, os, statistics, sys
from playwright.sync_api import sync_playwright

url, variant, runs = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "", int(sys.argv[3]) if len(sys.argv) > 3 else 5
JS = """() => new Promise((resolve) => {
  const item = document.querySelector('.hist-item:not([data-sel=""]):not([data-sel=pending]):not([data-sel=since])');
  const done = () => document.querySelector('aside.panel .df-blk') && document.querySelector('aside.panel .df-changed .df-n-chg');
  globalThis.__pocT = []; globalThis.__pocDiff = [];
  const t0 = performance.now(); let tb=null, tf=null;
  const obs = new MutationObserver(() => { if (tb===null && document.querySelector('aside.panel .df-blk')) tb=performance.now()-t0; if (tf===null && document.querySelector('aside.panel .df-changed .df-n-chg')) tf=performance.now()-t0; if (done()) { obs.disconnect(); resolve({ms: performance.now() - t0, body: tb, fig: tf, label: item.textContent.trim().slice(0,30)}); } });
  obs.observe(document.body, {subtree: true, childList: true, attributes: true});
  item.click();
  setTimeout(() => { obs.disconnect(); resolve({ms: -1}); }, 10000);
})"""
res = []
with sync_playwright() as p:
    b = p.chromium.launch(); print("browser", b.version, "variant", repr(variant))
    for i in range(runs):
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.add_init_script(f"globalThis.__POC = {json.dumps(variant)};")
        cdp = pg.context.new_cdp_session(pg); cdp.send("Performance.enable")
        pg.goto(url + "#tab=decisions&view=table&id=D-7"); pg.wait_for_selector("aside.panel", timeout=20000)
        pg.evaluate("document.fonts.ready.then(()=>true)"); pg.wait_for_selector("aside.panel .mermaid svg", timeout=20000); pg.wait_for_timeout(500)
        pg.click(".hist-btn"); pg.wait_for_selector(".hist-item"); pg.wait_for_timeout(300)
        heap0 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}["JSHeapUsedSize"]
        load = os.getloadavg()[0]
        r = pg.evaluate(JS)
        pg.wait_for_timeout(300)
        r["parts"] = pg.evaluate("globalThis.__pocT"); r["diff"] = pg.evaluate("globalThis.__pocDiff")
        heap1 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}["JSHeapUsedSize"]
        r["load1"] = round(load, 2); r["heap_mb"] = round(heap1 / 1e6, 1); r["heap_delta_mb"] = round((heap1 - heap0) / 1e6, 2)
        print(i + 1, json.dumps(r, ensure_ascii=False), flush=True); res.append(r["ms"])
        pg.close()
    b.close()
print("median", round(statistics.median(res), 1))
