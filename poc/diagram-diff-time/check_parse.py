"""案 D の差分の中身を、ラベルの書き方を変えた図の組で確かめる。前の版を描いて突き合わせる今の方式（diffDiagram）と、記法を解析して突き合わせる案 D（diffDiagramParsed）の結果が一致するかを比べる"""
import json, sys
from playwright.sync_api import sync_playwright

CASES = {
    "br": ('flowchart TD\n  A["一行目<br>二行目"] --> B[次]\n', 'flowchart TD\n  A["一行目<br>三行目"] --> B[次]\n'),
    "markdown": ('flowchart TD\n  A["`**太字** の文字`"] --> B[次]\n', 'flowchart TD\n  A["`**太字** の言葉`"] --> B[次]\n'),
    "quoted": ('flowchart TD\n  A["引用 (括弧) と &quot;記号&quot;"] --> B[次]\n', 'flowchart TD\n  A["引用 (括弧) と &quot;記号&quot; 改"] --> B[次]\n'),
    "class": ('flowchart TD\n  A[ノード]:::hot --> B[次]\n  classDef hot fill:#f99\n', 'flowchart TD\n  A[ノード 改]:::hot --> B[次]\n  classDef hot fill:#f99\n'),
    "edge_label": ('flowchart TD\n  A[判定] -->|はい| B[次]\n  A -->|いいえ| C[別]\n', 'flowchart TD\n  A[判定] -->|はい| B[次]\n  A -->|いいえ!| C[別]\n  A --> B\n'),
    "add_remove": ('flowchart LR\n  A --> B --> C\n', 'flowchart LR\n  A --> B --> D\n'),
    "shapes": ('flowchart TD\n  A((丸)) --> B{判定}\n  B --> C[(DB)]\n', 'flowchart TD\n  A((丸い)) --> B{判定}\n  B --> C[(DB)]\n'),
    "subgraph": ('flowchart TD\n  subgraph S[枠]\n    A[中] --> B[外へ]\n  end\n  B --> C[先]\n', 'flowchart TD\n  subgraph S[枠]\n    A[中 改] --> B[外へ]\n  end\n  B --> C[先]\n  C --> A\n'),
    "br_same": ('flowchart TD\n  A["一行目<br>二行目"] --> B[次]\n', 'flowchart TD\n  A["一行目<br>二行目"] --> B[次 改]\n'),
    "markdown_same": ('flowchart TD\n  A["`**太字** の文字`"] --> B[次]\n', 'flowchart TD\n  A["`**太字** の文字`"] --> B[次 改]\n'),
    "quoted_same": ('flowchart TD\n  A["引用 (括弧) と &quot;記号&quot; &amp; &lt;b&gt;"] --> B[次]\n', 'flowchart TD\n  A["引用 (括弧) と &quot;記号&quot; &amp; &lt;b&gt;"] --> B[次 改]\n'),
    "class_same": ('flowchart TD\n  A[ノード]:::hot --> B[次]\n  classDef hot fill:#f99\n', 'flowchart TD\n  A[ノード]:::hot --> B[次 改]\n  classDef hot fill:#f99\n'),
    "edge_label_same": ('flowchart TD\n  A[判定] -->|"はい<br>そう"| B[次]\n', 'flowchart TD\n  A[判定 改] -->|"はい<br>そう"| B[次]\n'),
    "no_label_same": ('flowchart TD\n  A --> B\n  B --> C[三]\n', 'flowchart TD\n  A --> B\n  B --> C[三 改]\n'),
    "icon_same": ('flowchart TD\n  A["fa:fa-user 人"] --> B[次]\n', 'flowchart TD\n  A["fa:fa-user 人"] --> B[次 改]\n'),
    "br_removed": ('flowchart TD\n  A["一行目<br>二行目"] --> B[次]\n  B --> C["`**消す** 方`"]\n', 'flowchart TD\n  A["一行目<br>二行目"] --> B[次]\n'),
    "graph": ('graph LR\n  A[一] --> B[二]\n', 'graph LR\n  A[一] --> B[二 改]\n'),
}
JS = """async ([before, after]) => {
  const P = MindmapPreview;
  const label = (e) => `${e.tagName}#${(e.id || e.getAttribute('data-id') || '').replace(/^mindmap-diagram-\\d+-/, '')}:${(e.textContent ?? '').replace(/\\s+/g,' ').trim()}`;
  const shape = (d) => d === null ? null : ({added: d.added.map(label).sort(), changed: d.changed.map(label).sort(), removed: [...d.removed].sort()});
  const afterSvg = await P.renderDiagramSvg(after); afterSvg.__source = after;
  const host = document.createElement('div'); host.style.cssText = 'position:absolute;left:-99999px;width:1200px'; document.body.append(host); host.append(afterSvg);
  const beforeSvg = await P.renderDiagramSvg(before); host.append(beforeSvg);
  const type = after.trim().split(/\\s/)[0];
  const rendered = shape(P.diffDiagram(type, beforeSvg, afterSvg));
  const parsed = shape(await P.diffDiagramParsed(type, before, afterSvg));
  host.remove();
  return {rendered, parsed, same: JSON.stringify(rendered) === JSON.stringify(parsed)};
}"""
url = sys.argv[1]
variant = sys.argv[2] if len(sys.argv) > 2 else ""
ok = True
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 800}); pg.add_init_script(f"globalThis.__POC = {json.dumps(variant)};")
    pg.goto(url + "#tab=decisions&view=table&id=D-7"); pg.wait_for_selector("aside.panel .mermaid svg", timeout=20000)
    for name, pair in CASES.items():
        r = pg.evaluate(JS, list(pair))
        ok &= r["same"]
        print(name, "一致" if r["same"] else "不一致", json.dumps(r if not r["same"] else r["rendered"], ensure_ascii=False), flush=True)
    b.close()
print("all", "一致" if ok else "不一致あり")
