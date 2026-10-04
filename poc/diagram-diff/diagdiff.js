// 前後の記法を公開の mermaid.render で描き、SVG の要素どうしを突き合わせて今の SVG に色の class を付ける
(function () {
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  let seq = 0;

  async function renderSvg(src) {
    const id = "dd" + seq++;
    const { svg } = await mermaid.render(id, src);
    const host = document.createElement("div");
    host.innerHTML = svg;
    return { root: host.firstElementChild, prefix: id };
  }

  // ノード: g.node の id から「{描画の id}-」と末尾の「-{連番}」を外したものを鍵にする
  function nodeKey(el, prefix) {
    let id = el.id.startsWith(prefix + "-") ? el.id.slice(prefix.length + 1) : el.id;
    return id.replace(/-\d+$/, "");
  }

  function boxOf(el) {
    const b = el.getBBox();
    const m = el.transform && el.transform.baseVal.consolidate();
    const tx = m ? m.matrix.e : 0, ty = m ? m.matrix.f : 0;
    return { x: b.x + tx, y: b.y + ty, w: b.width, h: b.height };
  }

  function nearest(nodes, pt) {
    let best = null, bestD = Infinity;
    for (const n of nodes) {
      const b = n.box;
      const dx = Math.max(b.x - pt.x, 0, pt.x - (b.x + b.w));
      const dy = Math.max(b.y - pt.y, 0, pt.y - (b.y + b.h));
      const d = dx * dx + dy * dy;
      if (d < bestD) { bestD = d; best = n; }
    }
    return best ? best.key : "?";
  }

  // 1 枚の SVG から、鍵 → { 要素, 文字 } のノードと辺を取り出す
  function extract(root, prefix, type) {
    const nodes = [], edges = [];
    if (type === "sequence") {
      root.querySelectorAll('[data-et="participant"]').forEach((g) => {
        nodes.push({ key: g.getAttribute("data-id"), els: [g], text: norm(g.textContent) });
      });
      // 参加者は上下 2 つ描かれる。鍵ごとにまとめ、生命線の x を端点の判定に使う
      const lifelines = [...root.querySelectorAll('[data-et="life-line"]')].map((l) => ({ key: l.getAttribute("data-id"), x: +l.getAttribute("x1") }));
      const texts = [...root.querySelectorAll("text.messageText")];
      root.querySelectorAll('[data-et="message"]').forEach((line, i) => {
        const len = line.getTotalLength ? line.getTotalLength() : 0;
        const p0 = line.getPointAtLength(0), p1 = line.getPointAtLength(len);
        const near = (x) => lifelines.reduce((a, b) => (Math.abs(b.x - x) < Math.abs(a.x - x) ? b : a)).key;
        const text = norm(texts[i] ? texts[i].textContent : "");
        edges.push({ base: near(p0.x) + ">" + near(p1.x), text, els: [line, texts[i]].filter(Boolean) });
      });
    } else {
      root.querySelectorAll("g.node").forEach((g) => {
        nodes.push({ key: nodeKey(g, prefix), els: [g], text: norm(g.textContent), box: boxOf(g) });
      });
      const labels = {};
      root.querySelectorAll("g.label[data-id], g.edgeLabel [data-id]").forEach((l) => { labels[l.getAttribute("data-id")] = l; });
      root.querySelectorAll('path[data-et="edge"]').forEach((p) => {
        const did = p.getAttribute("data-id");
        let base;
        if (type === "state") {
          // 遷移の id は並び順の番号だけのため、線の端の座標から一番近い状態を端点にする
          const len = p.getTotalLength();
          base = nearest(nodes, p.getPointAtLength(0)) + ">" + nearest(nodes, p.getPointAtLength(len));
        } else {
          base = did.replace(/^(L_|id_)/, "").replace(/_\d+$/, "").replace(/-\d+(?=_|$)/g, "").replace(/_/, ">");
        }
        const lab = labels[did];
        edges.push({ base, text: lab ? norm(lab.textContent) : "", els: [p, lab].filter(Boolean) });
      });
    }
    // 同じ端点の辺が複数あるときは出てきた順の番号で分ける
    const count = {};
    for (const e of edges) { const n = (count[e.base] = (count[e.base] || 0)); count[e.base]++; e.key = e.base + "#" + n; }
    // 参加者のように同じ鍵が複数あるノードはまとめる
    const nodeMap = new Map();
    for (const n of nodes) { if (nodeMap.has(n.key)) nodeMap.get(n.key).els.push(...n.els); else nodeMap.set(n.key, n); }
    return { nodes: nodeMap, edges };
  }

  function compare(oldX, newX, type) {
    const result = { added: [], changed: [], removedNodes: [], removedEdges: [] };
    for (const [k, n] of newX.nodes) {
      const o = oldX.nodes.get(k);
      if (!o) result.added.push({ kind: "node", key: k, els: n.els });
      else if (o.text !== n.text) result.changed.push({ kind: "node", key: k, els: n.els });
    }
    for (const [k, o] of oldX.nodes) if (!newX.nodes.has(k)) result.removedNodes.push(o.text || k);
    if (type === "sequence") {
      // メッセージは並び順で番号が振られるため、端点と文字の並びを行の差分と同じ要領で揃える
      const sig = (e) => e.base + ":" + e.text;
      const parts = Diff.diffArrays(oldX.edges.map(sig), newX.edges.map(sig));
      let ni = 0;
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        if (p.added) {
          const prev = parts[i - 1];
          p.value.forEach((s, j) => {
            const e = newX.edges[ni + j];
            const pairedRemoved = prev && prev.removed && prev.value[j] && prev.value[j].split(":")[0] === e.base;
            (pairedRemoved ? result.changed : result.added).push({ kind: "edge", key: s, els: e.els });
          });
          ni += p.count;
        } else if (p.removed) {
          const next = parts[i + 1];
          p.value.forEach((s, j) => {
            const paired = next && next.added && next.value[j] && next.value[j].split(":")[0] === s.split(":")[0];
            if (!paired) result.removedEdges.push(s);
          });
        } else ni += p.count;
      }
    } else {
      const oldE = new Map(oldX.edges.map((e) => [e.key, e]));
      const newKeys = new Set(newX.edges.map((e) => e.key));
      for (const e of newX.edges) {
        const o = oldE.get(e.key);
        if (!o) result.added.push({ kind: "edge", key: e.key, els: e.els });
        else if (o.text !== e.text) result.changed.push({ kind: "edge", key: e.key, els: e.els });
      }
      for (const e of oldX.edges) if (!newKeys.has(e.key)) result.removedEdges.push(e.key);
    }
    return result;
  }

  function typeOf(src) {
    const head = src.trim().split(/\s/)[0];
    return { flowchart: "flowchart", graph: "flowchart", sequenceDiagram: "sequence", classDiagram: "class", erDiagram: "er", "stateDiagram-v2": "state", stateDiagram: "state" }[head] || null;
  }

  // 前後の記法から、色の class を付けた今の SVG と結果を返す。対象の種類でなければ null（枠の色付けへ落とす）
  // reuse が真なら、mountTo に描いてある今の版の SVG をそのまま使い、前の版だけを描く
  async function diagramDiff(oldSrc, newSrc, mountTo, { reuse = false } = {}) {
    const type = typeOf(newSrc);
    const o = await renderSvg(oldSrc);
    let n;
    if (reuse) {
      const root = mountTo.firstElementChild;
      n = { root, prefix: root.id };
    } else {
      n = await renderSvg(newSrc);
      // 文字の大きさを測るため、描いた SVG を一度ページへ置く
      mountTo.replaceChildren(n.root);
    }
    const scratch = document.createElement("div");
    scratch.style.cssText = "position:absolute;left:-99999px;top:0";
    scratch.append(o.root);
    document.body.append(scratch);
    if (!type) { scratch.remove(); return null; }
    const res = compare(extract(o.root, o.prefix, type), extract(n.root, n.prefix, type), type);
    scratch.remove();
    for (const a of res.added) a.els.forEach((el) => el.classList.add("diff-added"));
    for (const c of res.changed) c.els.forEach((el) => el.classList.add("diff-changed"));
    return { type, ...res };
  }

  window.DiagramDiff = { diagramDiff, renderSvg, typeOf };
})();
