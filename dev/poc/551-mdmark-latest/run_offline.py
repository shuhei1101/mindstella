import json,time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
  b=p.chromium.launch(); ctx=b.new_context(offline=True)
  for n in ["sample","map"]:
    pg=ctx.new_page(); errs=[]; reqs=[]
    pg.on("console",lambda m: errs.append(m.text) if m.type in ("error","warning") else None); pg.on("request",lambda r: reqs.append(r.url) if not r.url.startswith(("file:","blob:","data:")) else None)
    pg.goto(f"file:///tmp/poc551/offline-{n}.html"); pg.wait_for_function("window.__result",timeout=30000); time.sleep(4)
    r=pg.evaluate("window.__result"); pr=pg.evaluate("()=>{const r=document.getElementById('root');return {nodes:r.querySelectorAll('.mdmark-diagram-node').length, mermaidSvg:r.querySelectorAll('svg[aria-roledescription]').length, maps:r.querySelectorAll('.mdmark-map').length, text:r.textContent.length}}")
    pg.screenshot(path=f"/tmp/poc551/offline-{n}.png",full_page=True)
    print(n,r,pr,"external_requests:",sorted(set(reqs))[:6],"errors:",errs[:4]); pg.close()
  b.close()
