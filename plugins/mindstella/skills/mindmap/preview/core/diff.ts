// 差分の表示の計算。変更履歴で選んだ時点から印を付ける項目を決め、項目の `history` から前の版を組み立て、本文・記法の行と図の要素を比べる。DOM は描かず、描くのは画面が持つ。

namespace MindmapPreview {
  /** 変更履歴で選んだ時点と、その時点で印を付ける項目 */
  export type DiffPoint = {
    /** `since`・`pending`・まとまりの ID */
    sel: string;
    /** 札と詳細パネルに出す名前 */
    name: string;
    /** 日時（JST）。「前回開いてから」は `{日時} より後` */
    sub: string;
    /** 新規の印を付ける ID */
    added: Set<string>;
    /** 変更の印を付ける ID（`added` にある ID は入れない） */
    changed: Set<string>;
    /** この時点の変更履歴の始まりの `seq`（これより大きい `seq` を戻す） */
    fromSeq: number;
    /** この時点の終わりの `seq`。null は今まで（`since`・`pending`） */
    untilSeq: number | null;
  };

  /** 選んだ時点の前と後の項目・本文と、組み立てられなかったこと */
  export type VersionPair = {
    /** 前の版の項目。組み立てられないとき null */
    before: Item | null;
    /** 後の版の項目（古いまとまりなら、そのまとまりの直後の形） */
    after: Item;
    /** 前の本文。本文を持たなければ空文字列、組み立てられないとき null */
    beforeBody: string | null;
    /** 後の本文 */
    afterBody: string;
    /** その時点の変更履歴が、保持する回数を超えて消えている */
    trimmed: boolean;
    /** `body_diff` の `now` が当てる先の行と合わなかった */
    bodyUnavailable: boolean;
  };

  /** 行の差分の 1 つ（同じ・足した・消した行のまとまり） */
  export type LinePart = {
    kind: "same" | "added" | "removed";
    /** 行（改行を含まない） */
    lines: string[];
  };

  /** 消した行のかたまりと、差し込む場所 */
  export type RemovedBlock = {
    lines: string[];
    /** 直後に来る今の本文の 1 始まりの行。本文の最後なら null */
    beforeLine: number | null;
    /** かたまりが表の本体の行だけのとき、前の版のその表の見出しの行と区切りの行 */
    tableHeader: string[] | null;
  };

  /** 図の差分。今の版の図で色を付ける要素と、消したものの名前 */
  export type DiagramDiff = {
    /** 足したノード・辺の要素（sequenceDiagram はメッセージの文字の要素） */
    added: Element[];
    /** 文字が変わったノード・辺の要素 */
    changed: Element[];
    /** 前にだけあるノード・辺の文字（「消したもの」に並べる） */
    removed: string[];
  };

  /** `Diff.diffLines` に渡す `timeout`（ミリ秒）。切り替えの 200ms のうち、図の描画に使った残りを本文 1 つの差分に充てる */
  export const LINE_DIFF_TIMEOUT_MS = 40;

  /** `Diff.diffArrays`（sequenceDiagram のメッセージの並び）に渡す `timeout`（ミリ秒） */
  export const ARRAY_DIFF_TIMEOUT_MS = 20;

  /** ノード・辺に色を付ける mermaid の図の種類（記法の 1 行目の語）。それ以外は図の枠に色を付ける */
  export const COLORED_DIAGRAM_TYPES: readonly string[] = [
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "erDiagram",
    "stateDiagram-v2",
  ];

  /** 「まだまとめていない変更」の名前と補足 */
  const PENDING_NAME = "まだまとめていない変更";
  const PENDING_SUB = "AI がまだ区切っていない書き換え";

  /** 「前回開いてから」の名前 */
  const SINCE_NAME = "前回開いてから";

  /** 選んだ時点の名前・補足・印・範囲から、時点を組み立てる */
  function buildPoint({
    sel,
    name,
    sub,
    groups,
    fromSeq,
    untilSeq,
  }: {
    sel: string;
    name: string;
    sub: string;
    groups: { added: string[]; changed: string[] }[];
    fromSeq: number;
    untilSeq: number | null;
  }): DiffPoint {
    const added = new Set(groups.flatMap((group) => group.added));
    // 足した項目は、変えても変更の印にしない
    const changed = new Set(groups.flatMap((group) => group.changed).filter((id) => !added.has(id)));
    return { sel, name, sub, added, changed, fromSeq, untilSeq };
  }

  /** 選んだ時点の識別子から、印を付ける項目と変更履歴の範囲を決める。差分を出さないときは null */
  export function resolveDiffPoint(changes: Changes, sel: string | null, since: string): DiffPoint | null {
    if (sel === null) return null;
    const sets = changes.sets;
    // 先頭のまとまりまでの変更履歴（それより後がまだまとめていない分）
    const latestSeq = sets[0]?.until_seq ?? 0;
    if (sel === "pending") {
      // まだまとめていない変更が無い
      if (changes.pending.added.length === 0 && changes.pending.changed.length === 0) return null;
      return buildPoint({ sel, name: PENDING_NAME, sub: PENDING_SUB, groups: [changes.pending], fromSeq: latestSeq, untilSeq: null });
    }
    if (sel === "since") {
      const startedAt = Date.parse(since);
      const inRange = sets.filter((set) => Date.parse(set.at) > startedAt);
      const oldest = inRange.at(-1);
      // 範囲で一番古いまとまりの 1 つ前の `until_seq` から。範囲にまとまりが無ければ、先頭のまとまりの `until_seq` から
      const fromSeq = oldest === undefined ? latestSeq : (sets[sets.indexOf(oldest) + 1]?.until_seq ?? 0);
      return buildPoint({
        sel,
        name: SINCE_NAME,
        sub: `${formatJst(since)} より後`,
        groups: [...inRange, changes.pending],
        fromSeq,
        untilSeq: null,
      });
    }
    const position = sets.findIndex((set) => set.id === sel);
    // 記録に無いまとまり
    if (position < 0) return null;
    const set = sets[position];
    if (set === undefined) return null;
    return buildPoint({
      sel,
      name: set.summary,
      sub: formatJst(set.at),
      groups: [set],
      fromSeq: sets[position + 1]?.until_seq ?? 0,
      untilSeq: set.until_seq,
    });
  }

  /** サーバーが本文を行に分けるのと同じ分け方（Python の `splitlines`）で、本文を行の並びにする */
  function bodyLines(text: string): string[] {
    const lines = text.split(/\r\n|[\n\r\v\f\u001c\u001d\u001e\u0085\u2028\u2029]/);
    // 末尾の改行で出る空の最後の要素は、行ではない
    if (lines.at(-1) === "") lines.pop();
    return lines;
  }

  /** 本文に差分を後ろの箇所から当てて前の本文にする。`now` が当てる先の行と合わなければ null */
  function applyBodyDiff(text: string, hunks: BodyDiffHunk[]): string | null {
    const lines = bodyLines(text);
    for (const hunk of [...hunks].sort((a, b) => b.line - a.line)) {
      const start = hunk.line - 1;
      const end = start + hunk.now.length;
      // 当てる先が本文の範囲を出るか、`now` と違う
      if (end > lines.length || hunk.now.some((line, offset) => lines[start + offset] !== line)) return null;
      lines.splice(start, hunk.now.length, ...hunk.before);
    }
    return lines.length > 0 ? `${lines.join("\n")}\n` : "";
  }

  /** 項目の版（キーと本文）。変更履歴を当てる途中の形 */
  type Version = { item: Item; body: string | null };

  /** 変更履歴の 1 回分を版に当てる（前に無かったキーは消し、本文は差分で戻す）。本文を戻せなかったら本文を null にする */
  function undoEntry(version: Version, entry: HistoryEntry): Version {
    const item: Record<string, unknown> = { ...version.item };
    let body = version.body;
    for (const [key, value] of Object.entries(entry.before)) {
      // 本文の名前は項目に残し、本文は差分で戻す
      if (key === "body") {
        // 本文を初めて足した回: 前は本文が無い
        if (value === null) body = "";
        continue;
      }
      if (value === null) delete item[key];
      else item[key] = value;
    }
    if (entry.body_diff !== undefined && body !== null) body = applyBodyDiff(body, entry.body_diff);
    return { item: item as Item, body };
  }

  /** 今の項目と本文に `history` を新しいものから当て、選んだ時点の前後の版を作る */
  export function buildVersions(item: Item, body: string, point: DiffPoint): VersionPair {
    const history = [...(item.history ?? [])].sort((a, b) => b.seq - a.seq);
    let after: Version = { item, body };
    let before: Version = { item, body };
    let inRange = false;
    for (const entry of history) {
      // 後の版: 選んだ時点の終わりより後の変更履歴を戻した形
      if (point.untilSeq !== null && entry.seq > point.untilSeq) after = undoEntry(after, entry);
      if (entry.seq <= point.fromSeq) continue;
      before = undoEntry(before, entry);
      if (point.untilSeq === null || entry.seq <= point.untilSeq) inRange = true;
    }
    // 選んだ時点の範囲に変更履歴が 1 回も無いか、範囲の中の回が消えている（消した回の最大の `seq` が範囲の始まりより大きい）: 保持する回数を超えて消えた
    if (!inRange || (item.history_dropped_seq ?? 0) > point.fromSeq) {
      return { before: null, after: after.item, beforeBody: null, afterBody: after.body ?? body, trimmed: true, bodyUnavailable: false };
    }
    const bodyUnavailable = before.body === null || after.body === null;
    return {
      before: before.item,
      after: after.item,
      beforeBody: before.body,
      afterBody: after.body ?? body,
      trimmed: false,
      bodyUnavailable,
    };
  }

  /** jsdiff が返した値（行の並びを `\n` でつないだもの）を、行の並びにする */
  function splitLines(value: string): string[] {
    return (value.endsWith("\n") ? value.slice(0, -1) : value).split("\n");
  }

  /** 前後の文字列を行ごとに比べる。jsdiff が読めていないときと、打ち切ったときは null */
  export function diffLineParts(before: string, after: string): LinePart[] | null {
    if (missingLibraries(["jsdiff"]).length > 0) return null;
    const parts = Diff.diffLines(before, after, { timeout: LINE_DIFF_TIMEOUT_MS });
    // 時間内に終わらなかった
    if (parts === undefined) return null;
    return parts.map((part) => ({
      kind: part.added ? "added" : part.removed ? "removed" : "same",
      lines: splitLines(part.value),
    }));
  }

  /** 行の差分の並びから、消した行のかたまりごとに、今の本文のどの行の前へ差し込むかを返す */
  export function placeRemovedBlocks(parts: LinePart[]): RemovedBlock[] {
    const blocks: RemovedBlock[] = [];
    // 前の版の行を前から並べておく（表の見出しをさかのぼって引くため）
    const beforeLines: string[] = [];
    let nowCount = 0;
    parts.forEach((part, position) => {
      if (part.kind === "removed") {
        const start = beforeLines.length;
        const followsNowLine = parts.slice(position + 1).some((next) => next.kind !== "removed");
        const tableBody =
          part.lines.every((line) => line.startsWith("|")) && (beforeLines[start - 1] ?? "").startsWith("|");
        blocks.push({
          lines: part.lines,
          // 次に来る今の本文の行（無ければ本文の最後）
          beforeLine: followsNowLine ? nowCount + 1 : null,
          tableHeader: tableBody ? tableHeaderOf(beforeLines, start) : null,
        });
        beforeLines.push(...part.lines);
        return;
      }
      // 同じ・足した行は今の本文の行を、同じ行は前の版の行も数え進める
      nowCount += part.lines.length;
      if (part.kind === "same") beforeLines.push(...part.lines);
    });
    return blocks;
  }

  /** 前の版の `start` 行目（0 始まり）から続く表の、頭までさかのぼった見出しの行と区切りの行 */
  function tableHeaderOf(beforeLines: string[], start: number): string[] | null {
    let top = start;
    while (top > 0 && (beforeLines[top - 1] ?? "").startsWith("|")) top -= 1;
    const header = beforeLines[top];
    const separator = beforeLines[top + 1];
    if (header === undefined || separator === undefined) return null;
    return [header, separator];
  }

  /** 図の種類（記法の 1 行目の語）→ 突き合わせの方式 */
  type DiagramFlavor = "flowchart" | "sequence" | "class" | "er" | "state";

  /** 図の種類（記法の 1 行目の語）から、突き合わせの方式を決める。色を付けない種類は null */
  function flavorOf(type: string): DiagramFlavor | null {
    if (!COLORED_DIAGRAM_TYPES.includes(type)) return null;
    const flavors: Record<string, DiagramFlavor> = {
      flowchart: "flowchart",
      graph: "flowchart",
      sequenceDiagram: "sequence",
      classDiagram: "class",
      erDiagram: "er",
      "stateDiagram-v2": "state",
    };
    return flavors[type] ?? null;
  }

  /** 図のノード 1 つ・辺 1 本の、突き合わせの材料 */
  type DiagramPart = { key: string; text: string; element: Element; box?: DOMRect };

  /** 空白を 1 つにして前後を除く */
  function normalized(text: string | null | undefined): string {
    return (text ?? "").replace(/\s+/g, " ").trim();
  }

  /** ノードの要素の id から「{描画の id}-」と末尾の「-{連番}」を外したものを、ノードの鍵にする */
  function nodeKey(element: Element, prefix: string): string {
    const id = element.id.startsWith(`${prefix}-`) ? element.id.slice(prefix.length + 1) : element.id;
    return id.replace(/-\d+$/, "");
  }

  /** ノードの要素の、図の座標での枠 */
  function boxOf(element: SVGGraphicsElement): DOMRect {
    const box = element.getBBox();
    const matrix = element.transform.baseVal.consolidate()?.matrix;
    return new DOMRect(box.x + (matrix?.e ?? 0), box.y + (matrix?.f ?? 0), box.width, box.height);
  }

  /** 点に一番近い枠のノードの鍵 */
  function nearestKey(nodes: DiagramPart[], point: DOMPoint): string {
    let best = "?";
    let bestDistance = Number.POSITIVE_INFINITY;
    for (const node of nodes) {
      const box = node.box;
      if (box === undefined) continue;
      const dx = Math.max(box.x - point.x, 0, point.x - (box.x + box.width));
      const dy = Math.max(box.y - point.y, 0, point.y - (box.y + box.height));
      const distance = dx * dx + dy * dy;
      if (distance < bestDistance) {
        bestDistance = distance;
        best = node.key;
      }
    }
    return best;
  }

  /** 辺の `data-id` から端点の鍵を引く。端点はノードの鍵の一覧と突き合わせて決める（ノードの id に `_` を含んでも取り違えない） */
  function edgeEnds(dataId: string, nodeKeys: Set<string>): string {
    const rest = dataId.replace(/^(L_|id_)/, "").replace(/_\d+$/, "").replace(/-\d+(?=_|$)/g, "");
    const cuts = [...rest.matchAll(/_/g)].map((found) => found.index ?? 0);
    const matched = cuts.find((cut) => nodeKeys.has(rest.slice(0, cut)) && nodeKeys.has(rest.slice(cut + 1)));
    const cut = matched ?? cuts[0];
    return cut === undefined ? rest : `${rest.slice(0, cut)}>${rest.slice(cut + 1)}`;
  }

  /** 1 枚の SVG から、ノードと辺の材料を取り出す。同じ端点の辺は出てきた順の番号で分ける */
  function extractDiagram(root: SVGElement, flavor: DiagramFlavor): { nodes: Map<string, DiagramPart>; edges: DiagramPart[] } {
    const prefix = root.id;
    const nodeList: DiagramPart[] = [];
    const edges: { base: string; text: string; element: Element }[] = [];
    if (flavor === "sequence") {
      for (const participant of root.querySelectorAll('[data-et="participant"]')) {
        nodeList.push({ key: participant.getAttribute("data-id") ?? "", text: normalized(participant.textContent), element: participant });
      }
      // 参加者は上下 2 つ描かれる。生命線の x を、メッセージの端点の判定に使う
      const lifelines = [...root.querySelectorAll('[data-et="life-line"]')].map((line) => ({
        key: line.getAttribute("data-id") ?? "",
        x: Number(line.getAttribute("x1")),
      }));
      const nearestLifeline = (x: number): string =>
        lifelines.reduce((best, line) => (Math.abs(line.x - x) < Math.abs(best.x - x) ? line : best), lifelines[0] ?? { key: "?", x }).key;
      const texts = [...root.querySelectorAll("text.messageText")];
      root.querySelectorAll<SVGGeometryElement>('[data-et="message"]').forEach((line, position) => {
        const length = line.getTotalLength();
        const label = texts[position];
        // 色を付けるのはメッセージの文字（線は文字の直後の兄弟）
        if (label === undefined) return;
        edges.push({
          base: `${nearestLifeline(line.getPointAtLength(0).x)}>${nearestLifeline(line.getPointAtLength(length).x)}`,
          text: normalized(label.textContent),
          element: label,
        });
      });
    } else {
      for (const node of root.querySelectorAll<SVGGraphicsElement>("g.node")) {
        const skipBox = ((globalThis as unknown as { __POC?: string }).__POC ?? "").includes("E") && flavor !== "state";
        nodeList.push({ key: nodeKey(node, prefix), text: normalized(node.textContent), element: node, box: skipBox ? undefined : boxOf(node) });
      }
      const nodeKeys = new Set(nodeList.map((node) => node.key));
      const labels = new Map<string, Element>();
      for (const label of root.querySelectorAll("g.label[data-id], g.edgeLabel [data-id]")) {
        labels.set(label.getAttribute("data-id") ?? "", label);
      }
      for (const path of root.querySelectorAll<SVGGeometryElement>('path[data-et="edge"]')) {
        const dataId = path.getAttribute("data-id") ?? "";
        const base =
          flavor === "state"
            ? // 遷移の id は並び順の番号だけのため、線の端の座標に一番近い状態を端点にする
              `${nearestKey(nodeList, path.getPointAtLength(0))}>${nearestKey(nodeList, path.getPointAtLength(path.getTotalLength()))}`
            : edgeEnds(dataId, nodeKeys);
        edges.push({ base, text: normalized(labels.get(dataId)?.textContent), element: path });
      }
    }
    const counts = new Map<string, number>();
    const keyedEdges = edges.map((edge) => {
      const number = counts.get(edge.base) ?? 0;
      counts.set(edge.base, number + 1);
      return { key: `${edge.base}#${number}`, text: edge.text, element: edge.element };
    });
    // 参加者のように同じ鍵が複数あるノードは、先に出たものにまとめる
    const nodes = new Map<string, DiagramPart>();
    for (const node of nodeList) if (!nodes.has(node.key)) nodes.set(node.key, node);
    return { nodes, edges: keyedEdges };
  }

  /** 辺の鍵 `{元}>{先}#{番号}` を、消したものの一覧に出す名前にする */
  function edgeName(edge: { key: string; text: string }): string {
    return edge.text !== "" ? edge.text : edge.key.replace(/#\d+$/, "").replace(">", " → ");
  }

  /** 前後の版で描いた SVG のノード・辺を鍵で突き合わせる。色を付けない種類と、突き合わせを打ち切ったときは null */
  export function diffDiagram(type: string, beforeSvg: SVGElement, afterSvg: SVGElement): DiagramDiff | null {
    const flavor = flavorOf(type);
    if (flavor === null) return null;
    return compareDiagrams(flavor, extractDiagram(beforeSvg, flavor), extractDiagram(afterSvg, flavor));
  }

  /** PoC（#115）案 D: 前の版は SVG に描かず、記法を解析した結果からノードと辺の鍵と文字を取り出して突き合わせる（flowchart だけ） */
  export async function diffDiagramParsed(type: string, beforeSource: string, afterSvg: SVGElement): Promise<DiagramDiff | null> {
    const flavor = flavorOf(type);
    if (flavor !== "flowchart") return null;
    const api = (mermaid as unknown as { mermaidAPI: { getDiagramFromText: (text: string) => Promise<{ db: { getVertices: () => Map<string, { id: string; text?: string }>; getEdges: () => { start: string; end: string; text?: string }[] } }> } }).mermaidAPI;
    const parts = async (source: string): Promise<{ nodes: Map<string, DiagramPart>; edges: DiagramPart[] }> => {
      const parsed = await api.getDiagramFromText(source);
      const placeholder = afterSvg;
      const nodes = new Map<string, DiagramPart>();
      // SVG のノードの鍵は `flowchart-{id}`（nodeKey が描画の id と連番を外した残り）
      for (const [id, vertex] of parsed.db.getVertices()) nodes.set(`flowchart-${id}`, { key: `flowchart-${id}`, text: normalized(vertex.text ?? id), element: placeholder });
      const counts = new Map<string, number>();
      const edges = parsed.db.getEdges().map((edge) => {
        const base = `${edge.start}>${edge.end}`;
        const number = counts.get(base) ?? 0;
        counts.set(base, number + 1);
        return { key: `${base}#${number}`, text: normalized(edge.text ?? ""), element: placeholder };
      });
      return { nodes, edges };
    };
    const previous = await parts(beforeSource);
    const drawn = extractDiagram(afterSvg, flavor);
    if (!((globalThis as unknown as { __POC?: string }).__POC ?? "").includes("P")) return compareDiagrams(flavor, previous, drawn);
    // 案 D'（P）: 今の版も記法を解析し、文字は前後とも解析した結果で比べる。色を付ける要素だけ今の版の SVG から引く
    const parsedNow = await parts(afterSvg.closest("[data-source]")?.getAttribute("data-source") ?? (afterSvg as unknown as { __source?: string }).__source ?? "");
    const nodes = new Map<string, DiagramPart>();
    for (const [key, node] of drawn.nodes) nodes.set(key, { ...node, text: parsedNow.nodes.get(key)?.text ?? node.text });
    const nowEdges = new Map(parsedNow.edges.map((edge) => [edge.key, edge.text]));
    const edges = drawn.edges.map((edge) => ({ ...edge, text: nowEdges.get(edge.key) ?? edge.text }));
    return compareDiagrams(flavor, previous, { nodes, edges });
  }

  /** 前後の版のノード・辺の材料を鍵で突き合わせる */
  function compareDiagrams(
    flavor: DiagramFlavor,
    previous: { nodes: Map<string, DiagramPart>; edges: DiagramPart[] },
    current: { nodes: Map<string, DiagramPart>; edges: DiagramPart[] },
  ): DiagramDiff | null {
    const result: DiagramDiff = { added: [], changed: [], removed: [] };
    for (const [key, node] of current.nodes) {
      const old = previous.nodes.get(key);
      if (old === undefined) result.added.push(node.element);
      else if (old.text !== node.text) result.changed.push(node.element);
    }
    for (const [key, node] of previous.nodes) {
      if (!current.nodes.has(key)) result.removed.push(node.text !== "" ? node.text : key);
    }
    if (flavor === "sequence") {
      // メッセージは並び順で番号が振られるため、端点と文字の並びを行の差分と同じ要領で揃える
      const signature = (edge: { key: string; text: string }): string => `${edge.key.replace(/#\d+$/, "")}:${edge.text}`;
      const parts = Diff.diffArrays(previous.edges.map(signature), current.edges.map(signature), { timeout: ARRAY_DIFF_TIMEOUT_MS });
      // 並びの突き合わせを打ち切った
      if (parts === undefined) return null;
      let nowPosition = 0;
      parts.forEach((part, position) => {
        if (part.added) {
          const removedBefore = parts[position - 1];
          part.value.forEach((_, offset) => {
            const edge = current.edges[nowPosition + offset];
            if (edge === undefined) return;
            const paired = removedBefore?.removed === true && (removedBefore.value[offset] ?? "").split(":")[0] === edge.key.replace(/#\d+$/, "");
            (paired ? result.changed : result.added).push(edge.element);
          });
          nowPosition += part.count ?? part.value.length;
        } else if (part.removed) {
          const addedAfter = parts[position + 1];
          part.value.forEach((signed, offset) => {
            const paired = addedAfter?.added === true && (addedAfter.value[offset] ?? "").split(":")[0] === signed.split(":")[0];
            if (!paired) result.removed.push(signed.slice(signed.indexOf(":") + 1) || signed);
          });
        } else {
          nowPosition += part.count ?? part.value.length;
        }
      });
      return result;
    }
    const previousEdges = new Map(previous.edges.map((edge) => [edge.key, edge]));
    const currentKeys = new Set(current.edges.map((edge) => edge.key));
    for (const edge of current.edges) {
      const old = previousEdges.get(edge.key);
      if (old === undefined) result.added.push(edge.element);
      else if (old.text !== edge.text) result.changed.push(edge.element);
    }
    for (const edge of previous.edges) if (!currentKeys.has(edge.key)) result.removed.push(edgeName(edge));
    return result;
  }
}
