"""PoC: 図の差分の色付けの精度と、差分の表示の切り替えの時間・メモリを測る。

python3 poc/diagram-diff/run.py  （Playwright の Chromium で開き、結果を JSON で標準出力へ出す）
"""
import json
import statistics
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
BUILT = HERE / "built.html"


def build() -> None:
    html = (HERE / "page.template.html").read_text()
    for mark, name in (("JSDIFF", "diff-9.0.0.min.js"), ("DIAGDIFF", "diagdiff.js"), ("CASES", "cases.js")):
        html = html.replace(f"/*{mark}*/", (HERE / name).read_text())
    BUILT.write_text(html)


BODY_DIFF_JS = """
(oldText, newText) => {
  // 行ごとの差分を取り、marked で描いた今の本文のブロックのうち、足した行を含むものに印を付ける
  const parts = Diff.diffLines(oldText, newText);
  const addedLines = new Set();
  const removed = [];
  let line = 0;
  for (const p of parts) {
    if (p.added) { for (let i = 0; i < p.count; i++) addedLines.add(line + i); line += p.count; }
    else if (p.removed) removed.push(p.value);
    else line += p.count;
  }
  const tokens = marked.lexer(newText);
  let at = 0;
  const html = tokens.map((t) => {
    const n = (t.raw.match(/\\n/g) || []).length;
    let hit = false;
    for (let i = at; i < at + Math.max(n, 1); i++) if (addedLines.has(i)) { hit = true; break; }
    at += n;
    const inner = marked.parser([t]);
    return hit ? `<div class="diff-add">${inner}</div>` : inner;
  }).join("") + removed.map((r) => `<del class="diff-del">${r.replace(/</g, "&lt;")}</del>`).join("");
  const host = document.createElement("div");
  host.innerHTML = DOMPurify.sanitize(html);
  return host.querySelectorAll(".diff-add").length;
}
"""


def chain(n: int, *, changed: bool) -> str:
    """ノード n 個の flowchart。changed なら 1 つのラベルを変え、1 つ足し、1 つ消す。"""
    lines = ["flowchart TD"]
    for i in range(n):
        label = f"手順{i}" + ("改" if changed and i == n // 2 else "")
        if changed and i == n - 1:
            continue
        lines.append(f"  N{i}[{label}]")
    edges = [(i, i + 1) for i in range(n - 1)] + [(i, i + 3) for i in range(0, n - 3, 5)]
    for a, b in edges:
        if changed and (a == n - 1 or b == n - 1):
            continue
        lines.append(f"  N{a} --> N{b}")
    if changed:
        lines.append(f"  N0 --> X[足した手順]")
    return "\n".join(lines)


def body(lines: int, *, changed: bool) -> str:
    out = []
    for i in range(lines):
        if i % 20 == 0:
            out.append(f"## 見出し {i}")
        elif changed and i % 97 == 0:
            out.append(f"- 書き換えた箇条 {i}")
        else:
            out.append(f"本文の行 {i}。話し合いで決めたことを書く。")
    return "\n".join(out)


def heap(cdp) -> float:
    """ページの JavaScript のヒープの使用量（バイト）。"""
    cdp.send("HeapProfiler.collectGarbage")
    metrics = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    return metrics["JSHeapUsedSize"]


def main() -> int:
    build()
    report = {"accuracy": [], "scale": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        cdp = page.context.new_cdp_session(page)
        cdp.send("Performance.enable")
        page.goto(BUILT.as_uri())
        page.wait_for_function("window.mermaid && window.marked && window.DOMPurify && window.Diff && window.CASES")
        page.evaluate("mermaid.initialize({startOnLoad:false})")
        report["browser"] = browser.version
        # 精度: 5 種類それぞれで、色を付けた要素の文字と消したノードを期待値と突き合わせる
        for case in page.evaluate("CASES"):
            got = page.evaluate(
                """async (c) => {
                  const out = document.getElementById('out');
                  const r = await DiagramDiff.diagramDiff(c.before, c.after, out);
                  const text = (els) => els.map((e) => (e.textContent || '').replace(/\\s+/g, '').trim());
                  const colored = (cls) => [...out.querySelectorAll('.' + cls)].map((e) => (e.textContent || '').replace(/\\s+/g, '').trim()).filter(Boolean);
                  return { added: [...new Set(colored('diff-added'))].sort(), changed: [...new Set(colored('diff-changed'))].sort(),
                           removedNodes: r.removedNodes.map((t) => t.replace(/\\s+/g, '')).sort(), removedEdges: r.removedEdges };
                }""",
                case,
            )
            exp = {k: sorted(v) for k, v in case["expected"].items()}
            ok = all(got[k] == exp[k] for k in exp)
            report["accuracy"].append({"type": case["name"], "ok": ok, "got": got, "expected": exp})
        # 時間とメモリ: 図と本文の規模を 3 段で測る（中央値、5 回）
        for nodes, lines in ((10, 100), (50, 1000), (100, 5000)):
            old_d, new_d = chain(nodes, changed=False), chain(nodes, changed=True)
            old_b, new_b = body(lines, changed=False), body(lines, changed=True)
            runs = {"render_only": [], "toggle_A": [], "toggle_reuse": [], "parse_B_old": [], "body_diff": []}
            heap_before = heap(cdp)
            for _ in range(5):
                t = page.evaluate(
                    """async ([od, nd, ob, nb, bodyDiff]) => {
                      const f = eval(bodyDiff);
                      const out = document.getElementById('out');
                      let t0 = performance.now();
                      out.replaceChildren((await DiagramDiff.renderSvg(nd)).root);
                      const renderOnly = performance.now() - t0;
                      t0 = performance.now();
                      await DiagramDiff.diagramDiff(od, nd, out);
                      const b0 = performance.now();
                      f(ob, nb);
                      const bodyDiffMs = performance.now() - b0;
                      const toggle = performance.now() - t0;
                      // 差分の表示を切りで描いてある状態から入れる（今の版の SVG を使い回す）
                      out.replaceChildren((await DiagramDiff.renderSvg(nd)).root);
                      t0 = performance.now();
                      await DiagramDiff.diagramDiff(od, nd, out, { reuse: true });
                      f(ob, nb);
                      const toggleReuse = performance.now() - t0;
                      t0 = performance.now();
                      await mermaid.mermaidAPI.getDiagramFromText(od);
                      const parseB = performance.now() - t0;
                      return [renderOnly, toggle, toggleReuse, parseB, bodyDiffMs];
                    }""",
                    [old_d, new_d, old_b, new_b, BODY_DIFF_JS],
                )
                for k, v in zip(runs, t):
                    runs[k].append(v)
            heap_after = heap(cdp)
            report["scale"].append({
                "nodes": nodes, "edges": new_d.count("-->"), "body_lines": lines,
                **{k + "_ms": round(statistics.median(v), 1) for k, v in runs.items()},
                "heap_growth_mb": round((heap_after - heap_before) / 1e6, 1),
                "heap_after_mb": round(heap_after / 1e6, 1),
            })
        browser.close()
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if all(a["ok"] for a in report["accuracy"]) else 1


if __name__ == "__main__":
    sys.exit(main())
