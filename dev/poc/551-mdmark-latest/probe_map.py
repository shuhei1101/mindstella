import json, threading, functools, http.server, socketserver, time
from playwright.sync_api import sync_playwright
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory="/tmp/poc551/web"); H.log_message=lambda *a:None
srv=socketserver.TCPServer(("127.0.0.1",0),H); port=srv.server_address[1]; threading.Thread(target=srv.serve_forever,daemon=True).start()
J="""()=>{const r=document.getElementById('root'); const sv=r.querySelector('[class*=mdmark-map] svg, svg[class*=map]');
const nodes=[...r.querySelectorAll('[class*=map-node], g[data-id], [data-node]')].slice(0,8).map(e=>({cls:e.getAttribute('class'),kind:e.getAttribute('data-kind')||e.dataset.class||null, text:e.textContent.trim().slice(0,20)}));
const icons=r.querySelectorAll('[class*=map] [class*=icon], [class*=map] use').length;
const fills=[...new Set([...r.querySelectorAll('[class*=map-node] rect,[class*=map-node] path')].map(e=>getComputedStyle(e).fill))].slice(0,8);
return {nodes,icons,fills, mapHtml:(r.querySelector('[class*=mdmark-map]')||{}).outerHTML?.slice(0,600)}}"""
with sync_playwright() as p:
  b=p.chromium.launch()
  for m in ["0","1"]:
    pg=b.new_page(); pg.goto(f"http://127.0.0.1:{port}/test.html?ver=develop&doc=map.md&map={m}"); pg.wait_for_function("window.__result",timeout=60000); time.sleep(4)
    print("map=",m, json.dumps(pg.evaluate(J),ensure_ascii=False)[:1500]); pg.close()
  b.close()
