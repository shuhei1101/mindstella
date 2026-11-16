import json, sys, threading, functools, http.server, socketserver, time
from playwright.sync_api import sync_playwright
web = "/tmp/poc551/web"
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=web)
H.log_message = lambda *a: None
srv = socketserver.TCPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
PROBE = """() => { const r = document.getElementById('root'); const q = s => r.querySelectorAll(s).length;
 return { rootClass: r.className, blocksWithSourceLine: q('[data-source-line]'), mdmarkHtml: q('div.mdmark-html'), paramCopy: q('.mdmark-param-copy'),
  paramCopyText: [...r.querySelectorAll('.mdmark-param-copy')].map(b=>b.textContent.trim()), alert: q('.markdown-alert'), pre: q('pre'),
  mermaidCode: q('code.language-mermaid'), mermaidSvg: q('svg[id^=mermaid], .mermaid svg, svg[aria-roledescription]'),
  sideToc: q('[class*=side-toc]'), backToTop: q('[class*=back-to-top]'), map: q('[class*=mdmark-map]'), mapNodes: q('[data-kind]'),
  mapKinds: [...new Set([...r.querySelectorAll('[data-kind]')].map(e=>e.getAttribute('data-kind')))].slice(0,12),
  notices: [...r.querySelectorAll('[class*=notice], [class*=error]')].map(e=>e.textContent.trim().slice(0,80)).slice(0,5),
  topClasses: [...new Set([...r.querySelectorAll('*')].map(e=>[...e.classList]).flat().filter(c=>c.startsWith('mdmark')))].sort() } }"""
out = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, qs in [("v080_sample","ver=v0.8.0&doc=sample.md"),("dev_sample","ver=develop&doc=sample.md"),
                     ("dev_map_noconfig","ver=develop&doc=map.md"),("dev_map_config","ver=develop&doc=map.md&map=1")]:
        pg = b.new_page(viewport={"width":1280,"height":900}); errs=[]
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
        pg.goto(f"http://127.0.0.1:{port}/test.html?{qs}"); pg.wait_for_function("window.__result", timeout=60000); time.sleep(4)
        r = pg.evaluate("window.__result"); r["probe"] = pg.evaluate(PROBE); r["errors"]=errs[:5]
        pg.screenshot(path=f"/tmp/poc551/{name}.png", full_page=True); out[name]=r; pg.close()
    b.close()
json.dump(out, open("/tmp/poc551/browser.json","w"), ensure_ascii=False, indent=1)
for k,v in out.items():
    pr=v.get("probe",{}); print(k, v.get("ok"), v.get("version"), v.get("error"), {x:pr.get(x) for x in ["rootClass","blocksWithSourceLine","mdmarkHtml","paramCopy","paramCopyText","alert","pre","mermaidCode","mermaidSvg","sideToc","backToTop","map","mapNodes","mapKinds","notices"]}, v["errors"])
