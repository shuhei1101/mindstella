"""PoC: プレビューの描画を mdmark v0.7.0 に置き換えられるかを、Chromium で成功条件ごとに測って JSON で出す。

Usage:
# リポジトリの直下で、tsc で poc/mdmark/build/loader.js を作ってから流す
npx tsc -p poc/mdmark
python poc/mdmark/run_poc.py --out poc/mdmark/result.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import traceback
import urllib.request
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Playwright, Route, sync_playwright

# このファイルから見たリポジトリの直下（poc/mdmark の 2 つ上）
REPO_ROOT = Path(__file__).resolve().parents[2]
POC_DIR = REPO_ROOT / "poc" / "mdmark"
PREVIEW_DIR = REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "preview"

# mdmark の配布物（タグを固定した jsDelivr の GitHub の URL）
MDMARK_BASE = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@v0.7.0/dist/"
MDMARK_JS = MDMARK_BASE + "index.js"
MDMARK_CSS = MDMARK_BASE + "index.css"

# 今のプレビューが読む描画のライブラリ（雛形と同じ URL）
MARKED_JS = "https://cdn.jsdelivr.net/npm/marked@18.0.14/lib/marked.umd.js"
DOMPURIFY_JS = "https://cdn.jsdelivr.net/npm/dompurify@3.4.16/dist/purify.min.js"

# 検証ページを開く仮のオリジン
ORIGIN = "https://poc.test/"

# 描く時間を測る資料の行数の目安と、測る回数
LONG_DOC_MIN_LINES = 300
WARMUP_RUNS = 3
MEASURE_RUNS = 15

# 描く時間の合否: mdmark の中央値が今の描画の何倍以内か
TIME_RATIO_LIMIT = 2.0

# 選んだ範囲の箇所の突き合わせ: (名前, 始まりの文字列, 終わりの文字列, 期待する開始行, 期待する終了行)
SELECTION_CASES = [
    ("見出し", "見出し 1", "見出し 1", 1, 1),
    ("複数行の段落", "段落の 2", "3 行目", 4, 5),
    ("段落からリストへまたぐ", "段落の 1", "項目 A", 3, 7),
    ("リストの項目の続きの行", "項目 B", "続きの行", 8, 9),
    ("表の行", "a2", "b2", 15, 15),
    ("表の行をまたぐ", "b1", "a2", 14, 15),
    ("フェンスのコード", "return 1", "print(f())", 19, 20),
    ("見出し 2", "見出し 2", "見出し 2", 23, 23),
    ("引用", "引用の 1", "引用の 2", 25, 26),
    ("番号付きリストの項目", "番号 2", "番号 2", 38, 38),
    ("インラインのコードを含む段落", "用語", "code", 40, 40),
    ("字下げのコード", "indent_a", "indent_b", 44, 45),
    ("チルダのフェンスのコード", "tilde_a", "tilde_b", 48, 49),
]

# 検証ページの HTML（スクリプトは add_script_tag で足す）
PAGE_HTML = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<link rel="stylesheet" href="{MDMARK_CSS}"></head>
<body><div id="cur"></div><div id="mdm" class="md"></div><div id="mdm-default"></div></body></html>"""

BLANK_HTML = '<!doctype html><html lang="ja"><head><meta charset="utf-8"></head><body></body></html>'

# ページの中で使う関数（選んだ範囲を作る・mdmark の行の属性を読み替える）
PAGE_HELPERS = """
window.poc = {
  // root の中で needle を含む最初の文の位置
  textPoint(root, needle, atEnd) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const index = node.data.indexOf(needle);
      if (index >= 0) return [node, atEnd ? index + needle.length : index];
    }
    throw new Error("見つからない: " + needle);
  },
  // from の先頭から to の末尾までを選んだ範囲の箇所
  locate(root, from, to) {
    const range = document.createRange();
    const [startNode, startOffset] = poc.textPoint(root, from, false);
    const [endNode, endOffset] = poc.textPoint(root, to, true);
    range.setStart(startNode, startOffset);
    range.setEnd(endNode, endOffset);
    return MindmapPreview.selectionLocation(range);
  },
  // mdmark の data-source-line（0 始まり・ブロックの開始行）を、今の data-line-start（1 始まり・フェンスは中身の行）に読み替える
  adaptLines(root, source, fenceOnly) {
    const lines = source.split("\\n");
    for (const el of root.querySelectorAll("[data-source-line]")) {
      const start = Number(el.getAttribute("data-source-line"));
      const isFence = /^ {0,3}(```|~~~)/.test(lines[start] ?? "");
      const fence = el.tagName === "PRE" && (isFence || !fenceOnly) ? 1 : 0;
      el.setAttribute(MindmapPreview.LINE_ATTR, String(start + 1 + fence));
    }
  },
  // 要素の中の mdmark- で始まる class の一覧
  mdmarkClasses(root) {
    const names = new Set();
    for (const el of root.querySelectorAll("[class]")) {
      for (const name of el.classList) if (name.startsWith("mdmark-")) names.add(name);
    }
    return [...names].sort();
  },
  // 重なる機能の観測
  overlap(root) {
    return {
      heading_links: root.querySelectorAll("h1 a, h2 a, h3 a, h4 a, h5 a, h6 a").length,
      anchors: root.querySelectorAll(".mdmark-anchor").length,
      sections: root.querySelectorAll("section").length,
      table_parents: [...root.querySelectorAll("table")].map((t) => t.parentElement.tagName + "." + t.parentElement.className),
      classes: poc.mdmarkClasses(root),
    };
  },
};
"""


def _route_local(route: Route) -> None:
    """仮のオリジンの要求を、検証ページとリポジトリのファイルで返す。"""
    path = route.request.url.removeprefix(ORIGIN)
    # 検証ページ
    if path == "page.html":
        route.fulfill(body=PAGE_HTML, content_type="text/html; charset=utf-8")
        return
    if path == "blank.html":
        route.fulfill(body=BLANK_HTML, content_type="text/html; charset=utf-8")
        return
    # リポジトリのファイル（直下の配下に限る）
    target = (REPO_ROOT / path).resolve()
    if not target.is_relative_to(REPO_ROOT) or not target.is_file():
        route.fulfill(status=404, body="")
        return
    route.fulfill(body=target.read_bytes(), content_type="text/javascript; charset=utf-8")


def _open_page(browser: Browser, errors: list[str]) -> Page:
    """検証ページを開き、今の描画と mdmark の読み込みのスクリプトを足す。"""
    page = browser.new_page()
    page.route(f"{ORIGIN}**", _route_local)
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(f"{ORIGIN}page.html")
    for url in (
        MARKED_JS,
        DOMPURIFY_JS,
        f"{ORIGIN}plugins/mindstella/skills/mindmap/preview/core/dom.js",
        f"{ORIGIN}plugins/mindstella/skills/mindmap/preview/core/libs.js",
        f"{ORIGIN}poc/mdmark/build/loader.js",
    ):
        page.add_script_tag(url=url)
    page.add_script_tag(content=PAGE_HELPERS)
    return page


def _long_doc(sample: str) -> str:
    """試料を繰り返して、描く時間を測る長さの資料にする。"""
    parts: list[str] = []
    while sum(part.count("\n") for part in parts) < LONG_DOC_MIN_LINES:
        parts.append(sample)
    return "\n".join(parts)


def check_render(page: Page, sample: str) -> dict[str, Any]:
    """読み込み・重なる機能・図と html のブロック・行のマーカーを確かめる。"""
    return page.evaluate(
        """async ({ url, sample, cases }) => {
          const mdmark = await MindmapPreview.loadMdmark(url);
          const off = document.getElementById("mdm");
          const def = document.getElementById("mdm-default");
          MindmapPreview.mountMdmark({ mdmark, el: off, markdown: sample });
          mdmark.mount(def, { markdown: sample });
          const cur = MindmapPreview.renderMarkdown(sample);
          document.getElementById("cur").append(cur);

          // 読み込み
          const load = {
            version: mdmark.version(),
            blocks: Object.fromEntries(["h1", "h2", "p", "ul", "ol", "table", "pre", "blockquote"].map((t) => [t, off.querySelectorAll(t).length])),
          };

          // 重なる機能: 止めた描画と既定の描画の差。見出しのリンクを押したときの URL のハッシュ
          const hashStart = "#id=D-3";
          location.hash = hashStart;
          const defaultAnchor = def.querySelector(".mdmark-anchor");
          defaultAnchor?.click();
          const hashAfterDefault = location.hash;
          location.hash = hashStart;
          off.querySelector("h1").click();
          const hashAfterOff = location.hash;
          const printBefore = { off: off.innerHTML, def: def.innerHTML };
          window.dispatchEvent(new Event("beforeprint"));
          const printChanged = { off: off.innerHTML !== printBefore.off, def: def.innerHTML !== printBefore.def };
          window.dispatchEvent(new Event("afterprint"));
          const overlap = {
            off: poc.overlap(off),
            default: poc.overlap(def),
            hash_start: hashStart,
            hash_after_default_anchor_click: hashAfterDefault,
            hash_after_off_heading_click: hashAfterOff,
            print_changes_dom: printChanged,
          };

          // 図と html のブロック
          const mermaid = off.querySelector("code.language-mermaid");
          const html = off.querySelector("code.language-html");
          const blocks = {
            mermaid: mermaid ? { in_pre: mermaid.parentElement.tagName === "PRE", text: mermaid.textContent } : null,
            html: html ? { in_pre: html.parentElement.tagName === "PRE", text: html.textContent } : null,
            python_pre: off.querySelector("code.language-python")?.closest("pre")?.outerHTML.slice(0, 300) ?? null,
            code_line_spans: off.querySelectorAll(".mdmark-code-line").length,
          };

          // 行のマーカー: 今の描画と、読み替えた mdmark の描画で同じ範囲を選ぶ
          poc.adaptLines(off, sample, false);
          const oldRule = cases.map(([, from, to]) => poc.locate(off, from, to));
          poc.adaptLines(off, sample, true);
          const lines = cases.map(([name, from, to, start, end], index) => {
            const current = poc.locate(cur, from, to);
            const viaMdmark = poc.locate(off, from, to);
            const old = oldRule[index];
            const pick = (loc) => (loc ? [loc.start, loc.end] : null);
            return {
              name,
              expected: [start, end],
              current: pick(current),
              mdmark: pick(viaMdmark),
              mdmark_pre_rule: pick(old),
              match: JSON.stringify(pick(viaMdmark)) === JSON.stringify([start, end]),
            };
          });
          return { load, overlap, blocks, lines };
        }""",
        {"url": MDMARK_JS, "sample": sample, "cases": SELECTION_CASES},
    )


def check_time(page: Page, doc: str) -> dict[str, Any]:
    """約 300 行の資料の描画にかかる時間の中央値を、今の描画と mdmark で比べる。"""
    result = page.evaluate(
        """async ({ url, doc, warmup, runs }) => {
          const mdmark = await MindmapPreview.loadMdmark(url);
          const host = document.createElement("div");
          document.body.append(host);
          const median = (xs) => xs.sort((a, b) => a - b)[Math.floor(xs.length / 2)];
          const measure = (draw) => {
            const times = [];
            for (let i = 0; i < warmup + runs; i++) {
              host.replaceChildren();
              const start = performance.now();
              draw();
              const took = performance.now() - start;
              if (i >= warmup) times.push(took);
            }
            return median(times);
          };
          const current = measure(() => host.append(MindmapPreview.renderMarkdown(doc)));
          const viaMdmark = measure(() => {
            const el = document.createElement("div");
            host.append(el);
            MindmapPreview.mountMdmark({ mdmark, el, markdown: doc });
          });
          return { lines: doc.split("\\n").length, current_ms: current, mdmark_ms: viaMdmark };
        }""",
        {"url": MDMARK_JS, "doc": doc, "warmup": WARMUP_RUNS, "runs": MEASURE_RUNS},
    )
    result["ratio"] = result["mdmark_ms"] / result["current_ms"]
    result["pass"] = result["ratio"] <= TIME_RATIO_LIMIT
    return result


def _descendants(pid: int) -> list[int]:
    """pid の子孫のプロセスの pid を返す。"""
    parents: dict[int, int] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        # 一覧の後に終わったプロセスは飛ばす
        try:
            stat = (entry / "stat").read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        # comm は括弧で囲まれ空白を含みうるので、最後の ) の後ろから読む
        fields = stat[stat.rindex(")") + 2 :].split()
        parents[int(entry.name)] = int(fields[1])
    found: list[int] = []
    frontier = [pid]
    while frontier:
        current = frontier.pop()
        children = [child for child, parent in parents.items() if parent == current]
        found.extend(children)
        frontier.extend(children)
    return found


def _browser_pss_kb() -> int:
    """このプロセスが起こしたブラウザのプロセスの私用メモリ（PSS）の合計を KB で返す。"""
    total = 0
    for pid in _descendants(os.getpid()):
        rollup = Path(f"/proc/{pid}/smaps_rollup")
        if not rollup.exists():
            continue
        match = re.search(r"^Pss:\s+(\d+) kB", rollup.read_text(encoding="utf-8"), re.MULTILINE)
        total += int(match.group(1)) if match else 0
    return total


def _heap_used(page: Page) -> int:
    """GC してから、ページの JavaScript のヒープの使用量を返す。"""
    session = page.context.new_cdp_session(page)
    session.send("HeapProfiler.collectGarbage")
    return int(session.send("Runtime.getHeapUsage")["usedSize"])


def check_memory(playwright: Playwright, doc: str, library: str) -> dict[str, Any]:
    """空のページから、ライブラリを読んで約 300 行の資料を 1 件描いた後までのメモリの増え分を測る。"""
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.route(f"{ORIGIN}**", _route_local)
    page.goto(f"{ORIGIN}blank.html")
    heap_before = _heap_used(page)
    pss_before = _browser_pss_kb()
    # 今の描画: marked と DOMPurify と今のプレビューの関数
    if library == "marked":
        for url in (
            MARKED_JS,
            DOMPURIFY_JS,
            f"{ORIGIN}plugins/mindstella/skills/mindmap/preview/core/dom.js",
            f"{ORIGIN}plugins/mindstella/skills/mindmap/preview/core/libs.js",
        ):
            page.add_script_tag(url=url)
        page.evaluate("(doc) => document.body.append(MindmapPreview.renderMarkdown(doc))", doc)
    # mdmark: CSS と JavaScript と PoC の読み込み
    else:
        page.add_style_tag(url=MDMARK_CSS)
        page.add_script_tag(url=f"{ORIGIN}poc/mdmark/build/loader.js")
        page.evaluate(
            """async ({ url, doc }) => {
              const mdmark = await MindmapPreview.loadMdmark(url);
              const el = document.createElement("div");
              document.body.append(el);
              MindmapPreview.mountMdmark({ mdmark, el, markdown: doc });
            }""",
            {"url": MDMARK_JS, "doc": doc},
        )
    heap_after = _heap_used(page)
    pss_after = _browser_pss_kb()
    browser.close()
    return {
        "js_heap_increase_kb": (heap_after - heap_before) // 1024,
        "browser_pss_increase_kb": pss_after - pss_before,
    }


def _fetch(url: str) -> str:
    """配布物を取る。"""
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def check_export(browser: Browser, sample: str, workdir: Path) -> dict[str, Any]:
    """mdmark の JavaScript と CSS を中に持つ 1 枚の HTML を、ネットを切ったブラウザで file:// で開いて描けるかを確かめる。"""
    js = _fetch(MDMARK_JS)
    css = _fetch(MDMARK_CSS)
    loader = (POC_DIR / "build" / "loader.js").read_text(encoding="utf-8")
    for text in (js, sample, loader):
        if re.search(r"</?script", text, re.IGNORECASE):
            raise ValueError("中に持つ文字列が script のタグを含みます")
    html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>{css}</style></head>
<body><div id="mdm" class="md"></div>
<script type="text/plain" id="mdmark-js">{js}</script>
<script type="text/plain" id="sample">{sample}</script>
<script>{loader}</script>
<script>
MindmapPreview.loadMdmarkFromSource(document.getElementById("mdmark-js").textContent)
  .then((mdmark) => {{
    MindmapPreview.mountMdmark({{ mdmark, el: document.getElementById("mdm"), markdown: document.getElementById("sample").textContent }});
    window.pocDone = "ok";
  }})
  .catch((error) => {{ window.pocDone = "error: " + error; }});
</script></body></html>"""
    path = workdir / "export.html"
    path.write_text(html, encoding="utf-8")
    context = browser.new_context(offline=True)
    page = context.new_page()
    external: list[str] = []
    page.on("request", lambda req: external.append(req.url) if not req.url.startswith(("file:", "blob:", "data:")) else None)
    page.goto(path.as_uri())
    page.wait_for_function("window.pocDone !== undefined")
    result = page.evaluate(
        """() => ({
          done: window.pocDone,
          headings: document.querySelectorAll("#mdm h1, #mdm h2").length,
          tables: document.querySelectorAll("#mdm table").length,
          css_rules: document.styleSheets[0].cssRules.length,
          mdmark_root_class: document.getElementById("mdm").classList.contains("mdmark"),
        })"""
    )
    context.close()
    result["external_requests"] = external
    result["css_non_data_urls"] = [u for u in re.findall(r"url\(([^)]*)\)", css) if not u.strip("\"'").startswith("data:")]
    result["css_has_import_or_font_face"] = bool(re.search(r"@import|@font-face", css))
    result["file_bytes"] = path.stat().st_size
    return result


def main() -> int:
    """成功条件ごとに測って JSON を書き出す。"""
    parser = argparse.ArgumentParser(description="mdmark v0.7.0 への置き換えの PoC")
    parser.add_argument("--out", type=Path, required=True, help="結果の JSON の書き出し先")
    args = parser.parse_args()
    sample = (POC_DIR / "sample.md").read_text(encoding="utf-8")
    doc = _long_doc(sample)
    try:
        with sync_playwright() as playwright, tempfile.TemporaryDirectory() as tmp:
            browser = playwright.chromium.launch()
            errors: list[str] = []
            page = _open_page(browser, errors)
            render = check_render(page, sample)
            time = check_time(page, doc)
            render["console_errors"] = errors
            export = check_export(browser, sample, Path(tmp))
            browser.close()
            memory = {name: check_memory(playwright, doc, name) for name in ("marked", "mdmark")}
    except Exception:
        traceback.print_exc()
        return 1
    result = {"render": render, "time": time, "export": export, "memory": memory}
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
