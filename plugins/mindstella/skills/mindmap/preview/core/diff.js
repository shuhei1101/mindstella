"use strict";
// 差分の表示の計算。変更履歴で選んだ時点から印を付ける項目を決め、項目の `history` から前の版を組み立て、本文・記法の行と図の要素を比べる。DOM は描かず、描くのは画面が持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** `Diff.diffLines` に渡す `timeout`（ミリ秒）。切り替えの 200ms のうち、図の描画に使った残りを本文 1 つの差分に充てる */
    MindmapPreview.LINE_DIFF_TIMEOUT_MS = 40;
    /** `Diff.diffArrays`（sequenceDiagram のメッセージの並び）に渡す `timeout`（ミリ秒） */
    MindmapPreview.ARRAY_DIFF_TIMEOUT_MS = 20;
    /** ノード・辺に色を付ける mermaid の図の種類（記法の 1 行目の語）。それ以外は図の枠に色を付ける */
    MindmapPreview.COLORED_DIAGRAM_TYPES = [
        "flowchart",
        "graph",
        "sequenceDiagram",
        "classDiagram",
        "erDiagram",
        "stateDiagram-v2",
    ];
    /** 消した項目の種類（`RemovedItem.kind`）から、その項目を出す画面の種類を引く */
    MindmapPreview.REMOVED_KIND_TAB = {
        decision: "decisions",
        task: "tasks",
        research: "research",
        doc: "docs",
        term: "terms",
        note: "notes",
        log: "logs",
    };
    /** 「まだまとめていない変更」の名前と補足 */
    const PENDING_NAME = "まだまとめていない変更";
    const PENDING_SUB = "AI がまだ区切っていない書き換え";
    /** 「前回開いてから」の名前 */
    const SINCE_NAME = "前回開いてから";
    /** 選んだ時点の名前・補足・印・範囲から、時点を組み立てる */
    function buildPoint({ sel, name, sub, groups, fromSeq, untilSeq, }) {
        // `removed` を持たないまとまりは、何も足さない
        const removed = new Map(groups.flatMap((group) => group.removed ?? []).map((item) => [item.id, item]));
        // 合わせた範囲で足して消した項目は、消した項目としてだけ出す
        const added = new Set(groups.flatMap((group) => group.added).filter((id) => !removed.has(id)));
        // 足した項目は、変えても変更の印にしない
        const changed = new Set(groups.flatMap((group) => group.changed).filter((id) => !added.has(id) && !removed.has(id)));
        return { sel, name, sub, added, changed, fromSeq, untilSeq, removed };
    }
    /** 選んだ時点で消した項目のうち、その画面の種類のものを ID の順に返す。時点が null のときは空 */
    function removedOf({ point, kind }) {
        if (point === null)
            return [];
        return [...point.removed.values()]
            .filter((item) => MindmapPreview.REMOVED_KIND_TAB[item.kind] === kind)
            .sort((a, b) => MindmapPreview.compareIds(a.id, b.id));
    }
    MindmapPreview.removedOf = removedOf;
    /** 選んだ時点の識別子から、印を付ける項目と変更履歴の範囲を決める。差分を出さないときは null */
    function resolveDiffPoint(changes, sel, since) {
        if (sel === null)
            return null;
        const sets = changes.sets;
        // 先頭のまとまりまでの変更履歴（それより後がまだまとめていない分）
        const latestSeq = sets[0]?.until_seq ?? 0;
        if (sel === "pending") {
            // まだまとめていない変更が無い
            const pending = changes.pending;
            if (pending.added.length === 0 && pending.changed.length === 0 && (pending.removed ?? []).length === 0)
                return null;
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
                sub: `${MindmapPreview.formatJst(since)} より後`,
                groups: [...inRange, changes.pending],
                fromSeq,
                untilSeq: null,
            });
        }
        const position = sets.findIndex((set) => set.id === sel);
        // 記録に無いまとまり
        if (position < 0)
            return null;
        const set = sets[position];
        if (set === undefined)
            return null;
        return buildPoint({
            sel,
            name: set.summary,
            sub: MindmapPreview.formatJst(set.at),
            groups: [set],
            fromSeq: sets[position + 1]?.until_seq ?? 0,
            untilSeq: set.until_seq,
        });
    }
    MindmapPreview.resolveDiffPoint = resolveDiffPoint;
    /** サーバーが本文を行に分けるのと同じ分け方（Python の `splitlines`）で、本文を行の並びにする */
    function bodyLines(text) {
        const lines = text.split(/\r\n|[\n\r\v\f\u001c\u001d\u001e\u0085\u2028\u2029]/);
        // 末尾の改行で出る空の最後の要素は、行ではない
        if (lines.at(-1) === "")
            lines.pop();
        return lines;
    }
    /** 本文に差分を後ろの箇所から当てて前の本文にする。`now` が当てる先の行と合わなければ null */
    function applyBodyDiff(text, hunks) {
        const lines = bodyLines(text);
        for (const hunk of [...hunks].sort((a, b) => b.line - a.line)) {
            const start = hunk.line - 1;
            const end = start + hunk.now.length;
            // 当てる先が本文の範囲を出るか、`now` と違う
            if (end > lines.length || hunk.now.some((line, offset) => lines[start + offset] !== line))
                return null;
            lines.splice(start, hunk.now.length, ...hunk.before);
        }
        return lines.length > 0 ? `${lines.join("\n")}\n` : "";
    }
    /** 変更履歴の 1 回分を版に当てる（前に無かったキーは消し、本文は差分で戻す）。本文を戻せなかったら本文を null にする */
    function undoEntry(version, entry) {
        const item = { ...version.item };
        let body = version.body;
        for (const [key, value] of Object.entries(entry.before)) {
            // 本文の名前は項目に残し、本文は差分で戻す
            if (key === "body") {
                // 本文を初めて足した回: 前は本文が無い
                if (value === null)
                    body = "";
                // 資料の本文の形式を替えた回: 前の形式のファイル名に戻す
                else if (typeof value === "string")
                    item["body"] = value;
                continue;
            }
            if (value === null)
                delete item[key];
            else
                item[key] = value;
        }
        if (entry.body_diff !== undefined && body !== null)
            body = applyBodyDiff(body, entry.body_diff);
        return { item: item, body };
    }
    /** 今の項目と本文に `history` を新しいものから当て、選んだ時点の前後の版を作る */
    function buildVersions(item, body, point) {
        const history = [...(item.history ?? [])].sort((a, b) => b.seq - a.seq);
        let after = { item, body };
        let before = { item, body };
        let inRange = false;
        for (const entry of history) {
            // 後の版: 選んだ時点の終わりより後の変更履歴を戻した形
            if (point.untilSeq !== null && entry.seq > point.untilSeq)
                after = undoEntry(after, entry);
            if (entry.seq <= point.fromSeq)
                continue;
            before = undoEntry(before, entry);
            if (point.untilSeq === null || entry.seq <= point.untilSeq)
                inRange = true;
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
    MindmapPreview.buildVersions = buildVersions;
    /** jsdiff が返した値（行の並びを `\n` でつないだもの）を、行の並びにする */
    function splitLines(value) {
        return (value.endsWith("\n") ? value.slice(0, -1) : value).split("\n");
    }
    /** 前後の文字列を行ごとに比べる。jsdiff が読めていないときと、打ち切ったときは null */
    function diffLineParts(before, after) {
        if (MindmapPreview.missingLibraries(["jsdiff"]).length > 0)
            return null;
        const parts = Diff.diffLines(before, after, { timeout: MindmapPreview.LINE_DIFF_TIMEOUT_MS });
        // 時間内に終わらなかった
        if (parts === undefined)
            return null;
        return parts.map((part) => ({
            kind: part.added ? "added" : part.removed ? "removed" : "same",
            lines: splitLines(part.value),
        }));
    }
    MindmapPreview.diffLineParts = diffLineParts;
    /** 前後の HTML の原文を行ごとに比べ、足した行・変えた行（消した行と入れ替えた行）と、足した行と隣り合わない消した行があるかを返す。差分を打ち切ったら null */
    function htmlChangedLines(before, after) {
        const parts = diffLineParts(before, after);
        if (parts === null)
            return null;
        const added = [];
        const changed = [];
        let removedOnly = false;
        let nowLine = 0;
        parts.forEach((part, position) => {
            const neighbors = [parts[position - 1]?.kind, parts[position + 1]?.kind];
            if (part.kind === "removed") {
                // 足した並びに隣らない消した並びは、描いた結果に印を付けられない
                if (!neighbors.includes("added"))
                    removedOnly = true;
                return;
            }
            if (part.kind === "added") {
                // 消した並びに隣る足した並びは変えた行、それ以外は足した行（空白だけの行は入れない）
                const target = neighbors.includes("removed") ? changed : added;
                part.lines.forEach((line, offset) => {
                    if (line.trim() !== "")
                        target.push(nowLine + offset + 1);
                });
            }
            nowLine += part.lines.length;
        });
        return { added, changed, removedOnly };
    }
    MindmapPreview.htmlChangedLines = htmlChangedLines;
    /** 行の差分の並びから、消した行のかたまりごとに、今の本文のどの行の前へ差し込むかを返す */
    function placeRemovedBlocks(parts) {
        const blocks = [];
        // 前の版の行を前から並べておく（表の見出しをさかのぼって引くため）
        const beforeLines = [];
        let nowCount = 0;
        parts.forEach((part, position) => {
            if (part.kind === "removed") {
                const start = beforeLines.length;
                const followsNowLine = parts.slice(position + 1).some((next) => next.kind !== "removed");
                const tableBody = part.lines.every((line) => line.startsWith("|")) && (beforeLines[start - 1] ?? "").startsWith("|");
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
            if (part.kind === "same")
                beforeLines.push(...part.lines);
        });
        return blocks;
    }
    MindmapPreview.placeRemovedBlocks = placeRemovedBlocks;
    /** 前の版の `start` 行目（0 始まり）から続く表の、頭までさかのぼった見出しの行と区切りの行 */
    function tableHeaderOf(beforeLines, start) {
        let top = start;
        while (top > 0 && (beforeLines[top - 1] ?? "").startsWith("|"))
            top -= 1;
        const header = beforeLines[top];
        const separator = beforeLines[top + 1];
        if (header === undefined || separator === undefined)
            return null;
        return [header, separator];
    }
    /** 図の種類（記法の 1 行目の語）から、突き合わせの方式を決める。色を付けない種類は null */
    function flavorOf(type) {
        if (!MindmapPreview.COLORED_DIAGRAM_TYPES.includes(type))
            return null;
        const flavors = {
            flowchart: "flowchart",
            graph: "flowchart",
            sequenceDiagram: "sequence",
            classDiagram: "class",
            erDiagram: "er",
            "stateDiagram-v2": "state",
        };
        return flavors[type] ?? null;
    }
    /** 空白を 1 つにして前後を除く */
    function normalized(text) {
        return (text ?? "").replace(/\s+/g, " ").trim();
    }
    /** ノードの要素の id から「{描画の id}-」と末尾の「-{連番}」を外したものを、ノードの鍵にする */
    function nodeKey(element, prefix) {
        const id = element.id.startsWith(`${prefix}-`) ? element.id.slice(prefix.length + 1) : element.id;
        return id.replace(/-\d+$/, "");
    }
    /** ノードの要素の、図の座標での枠 */
    function boxOf(element) {
        const box = element.getBBox();
        const matrix = element.transform.baseVal.consolidate()?.matrix;
        return new DOMRect(box.x + (matrix?.e ?? 0), box.y + (matrix?.f ?? 0), box.width, box.height);
    }
    /** 点に一番近い枠のノードの鍵 */
    function nearestKey(nodes, point) {
        let best = "?";
        let bestDistance = Number.POSITIVE_INFINITY;
        for (const node of nodes) {
            const box = node.box;
            if (box === undefined)
                continue;
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
    function edgeEnds(dataId, nodeKeys) {
        const rest = dataId.replace(/^(L_|id_)/, "").replace(/_\d+$/, "").replace(/-\d+(?=_|$)/g, "");
        const cuts = [...rest.matchAll(/_/g)].map((found) => found.index ?? 0);
        const matched = cuts.find((cut) => nodeKeys.has(rest.slice(0, cut)) && nodeKeys.has(rest.slice(cut + 1)));
        const cut = matched ?? cuts[0];
        return cut === undefined ? rest : `${rest.slice(0, cut)}>${rest.slice(cut + 1)}`;
    }
    /** 1 枚の SVG から、ノードと辺の材料を取り出す。同じ端点の辺は出てきた順の番号で分ける */
    function extractDiagram(root, flavor) {
        const prefix = root.id;
        const nodeList = [];
        const edges = [];
        if (flavor === "sequence") {
            for (const participant of root.querySelectorAll('[data-et="participant"]')) {
                nodeList.push({ key: participant.getAttribute("data-id") ?? "", text: normalized(participant.textContent), element: participant });
            }
            // 参加者は上下 2 つ描かれる。生命線の x を、メッセージの端点の判定に使う
            const lifelines = [...root.querySelectorAll('[data-et="life-line"]')].map((line) => ({
                key: line.getAttribute("data-id") ?? "",
                x: Number(line.getAttribute("x1")),
            }));
            const nearestLifeline = (x) => lifelines.reduce((best, line) => (Math.abs(line.x - x) < Math.abs(best.x - x) ? line : best), lifelines[0] ?? { key: "?", x }).key;
            const texts = [...root.querySelectorAll("text.messageText")];
            root.querySelectorAll('[data-et="message"]').forEach((line, position) => {
                const length = line.getTotalLength();
                const label = texts[position];
                // 色を付けるのはメッセージの文字（線は文字の直後の兄弟）
                if (label === undefined)
                    return;
                edges.push({
                    base: `${nearestLifeline(line.getPointAtLength(0).x)}>${nearestLifeline(line.getPointAtLength(length).x)}`,
                    text: normalized(label.textContent),
                    element: label,
                });
            });
        }
        else {
            for (const node of root.querySelectorAll("g.node")) {
                // 枠は端点を座標で決める stateDiagram-v2 だけが使う
                nodeList.push({ key: nodeKey(node, prefix), text: normalized(node.textContent), element: node, box: flavor === "state" ? boxOf(node) : undefined });
            }
            const nodeKeys = new Set(nodeList.map((node) => node.key));
            const labels = new Map();
            for (const label of root.querySelectorAll("g.label[data-id], g.edgeLabel [data-id]")) {
                labels.set(label.getAttribute("data-id") ?? "", label);
            }
            for (const path of root.querySelectorAll('path[data-et="edge"]')) {
                const dataId = path.getAttribute("data-id") ?? "";
                const base = flavor === "state"
                    ? // 遷移の id は並び順の番号だけのため、線の端の座標に一番近い状態を端点にする
                        `${nearestKey(nodeList, path.getPointAtLength(0))}>${nearestKey(nodeList, path.getPointAtLength(path.getTotalLength()))}`
                    : edgeEnds(dataId, nodeKeys);
                edges.push({ base, text: normalized(labels.get(dataId)?.textContent), element: path });
            }
        }
        const counts = new Map();
        const keyedEdges = edges.map((edge) => {
            const number = counts.get(edge.base) ?? 0;
            counts.set(edge.base, number + 1);
            return { key: `${edge.base}#${number}`, text: edge.text, element: edge.element };
        });
        // 参加者のように同じ鍵が複数あるノードは、先に出たものにまとめる
        const nodes = new Map();
        for (const node of nodeList)
            if (!nodes.has(node.key))
                nodes.set(node.key, node);
        return { nodes, edges: keyedEdges };
    }
    /** 辺の鍵 `{元}>{先}#{番号}` を、消したものの一覧に出す名前にする */
    function edgeName(edge) {
        const name = edge.name ?? edge.text;
        return name !== "" ? name : edge.key.replace(/#\d+$/, "").replace(">", " → ");
    }
    /** 前後の版で描いた SVG のノード・辺を鍵で突き合わせる。色を付けない種類と、突き合わせを打ち切ったときは null */
    function diffDiagram(type, beforeSvg, afterSvg) {
        const flavor = flavorOf(type);
        if (flavor === null)
            return null;
        return compareDiagrams({ flavor, previous: extractDiagram(beforeSvg, flavor), current: extractDiagram(afterSvg, flavor) });
    }
    MindmapPreview.diffDiagram = diffDiagram;
    /** 前後の版のノード・辺の材料を鍵で突き合わせて、足した・変えた・消したものに分ける。並びの突き合わせを打ち切ったときは null */
    function compareDiagrams({ flavor, previous, current, }) {
        const result = { added: [], changed: [], removed: [] };
        for (const [key, node] of current.nodes) {
            const old = previous.nodes.get(key);
            if (old === undefined)
                result.added.push(node.element);
            else if (old.text !== node.text)
                result.changed.push(node.element);
        }
        for (const [key, node] of previous.nodes) {
            if (!current.nodes.has(key))
                result.removed.push((node.name ?? node.text) !== "" ? (node.name ?? node.text) : key);
        }
        if (flavor === "sequence") {
            // メッセージは並び順で番号が振られるため、端点と文字の並びを行の差分と同じ要領で揃える
            const signature = (edge) => `${edge.key.replace(/#\d+$/, "")}:${edge.text}`;
            const parts = Diff.diffArrays(previous.edges.map(signature), current.edges.map(signature), { timeout: MindmapPreview.ARRAY_DIFF_TIMEOUT_MS });
            // 並びの突き合わせを打ち切った
            if (parts === undefined)
                return null;
            let nowPosition = 0;
            parts.forEach((part, position) => {
                if (part.added) {
                    const removedBefore = parts[position - 1];
                    part.value.forEach((_, offset) => {
                        const edge = current.edges[nowPosition + offset];
                        if (edge === undefined)
                            return;
                        const paired = removedBefore?.removed === true && (removedBefore.value[offset] ?? "").split(":")[0] === edge.key.replace(/#\d+$/, "");
                        (paired ? result.changed : result.added).push(edge.element);
                    });
                    nowPosition += part.count ?? part.value.length;
                }
                else if (part.removed) {
                    const addedAfter = parts[position + 1];
                    part.value.forEach((signed, offset) => {
                        const paired = addedAfter?.added === true && (addedAfter.value[offset] ?? "").split(":")[0] === signed.split(":")[0];
                        if (!paired)
                            result.removed.push(signed.slice(signed.indexOf(":") + 1) || signed);
                    });
                }
                else {
                    nowPosition += part.count ?? part.value.length;
                }
            });
            return result;
        }
        const previousEdges = new Map(previous.edges.map((edge) => [edge.key, edge]));
        const currentKeys = new Set(current.edges.map((edge) => edge.key));
        for (const edge of current.edges) {
            const old = previousEdges.get(edge.key);
            if (old === undefined)
                result.added.push(edge.element);
            else if (old.text !== edge.text)
                result.changed.push(edge.element);
        }
        for (const edge of previous.edges)
            if (!currentKeys.has(edge.key))
                result.removed.push(edgeName(edge));
        return result;
    }
    /** 解析した結果の種類（`Diagram.type`）のうち flowchart のもの */
    const PARSED_FLOWCHART_TYPES = ["flowchart-v2", "flowchart-elk"];
    /** ラベルを画面に出る文字にそろえる（Markdown の記号と前後の `` ` ``・`<br>`・ほかのタグ・文字参照・`fa:fa-…` を外す） */
    function displayText({ text, labelType }) {
        let shown = text;
        if (labelType === "markdown") {
            shown = shown
                .replace(/^`|`$/g, "")
                .replace(/(\*\*|__)(.+?)\1/g, "$2")
                .replace(/\*(.+?)\*/g, "$1")
                .replace(/(?<!\w)_(.+?)_(?!\w)/g, "$1");
        }
        shown = shown.replace(/<br\s*\/?>/gi, " ").replace(/<[^>]*>/g, "");
        // 文字参照（`&amp;` など）を戻す
        const decoder = document.createElement("textarea");
        decoder.innerHTML = shown;
        return normalized(decoder.value.replace(/\bfa[bsrl]?:fa-[\w-]+/g, ""));
    }
    /** 記法を mermaid で解析して、flowchart のノードと辺の鍵・文字（と消したものに出す名前）を取り出す。flowchart でないときは null */
    async function parseFlowchart(source) {
        const parser = mermaid;
        const parsed = await parser.mermaidAPI.getDiagramFromText(source);
        if (!PARSED_FLOWCHART_TYPES.includes(parsed.type))
            return null;
        const nodes = new Map();
        // SVG のノードの鍵は `flowchart-{id}`（`nodeKey` が描画の id と連番を外した残り）
        for (const [id, vertex] of parsed.db.getVertices()) {
            const text = vertex.text ?? id;
            nodes.set(`flowchart-${id}`, { key: `flowchart-${id}`, text: normalized(text), name: displayText({ text, labelType: vertex.labelType }) });
        }
        const counts = new Map();
        const edges = parsed.db.getEdges().map((edge) => {
            // 辺の鍵は `flowchart-` を付けない `{始点}>{終点}` に、同じ端点の中の並びの番号を付ける
            const base = `${edge.start}>${edge.end}`;
            const number = counts.get(base) ?? 0;
            counts.set(base, number + 1);
            const text = edge.text ?? "";
            return { id: edge.id, key: `${base}#${number}`, text: normalized(text), name: displayText({ text, labelType: edge.labelType }) };
        });
        return { nodes, edges };
    }
    /** flowchart の図の差分を、前の版を SVG に描かず、前後の記法の解析で突き合わせる。flowchart でない種類と解析できなかったときは null */
    async function diffDiagramFromSource(type, beforeSource, afterSource, afterSvg) {
        if (flavorOf(type) !== "flowchart")
            return null;
        let previous;
        let parsedNow;
        try {
            previous = await parseFlowchart(beforeSource);
            parsedNow = await parseFlowchart(afterSource);
        }
        catch {
            // 解析できない記法（書きかけ）と、版を上げて形が変わった `mermaidAPI`: 前の版を描いて突き合わせる側へ倒す
            return null;
        }
        if (previous === null || parsedNow === null)
            return null;
        // 色を付ける要素だけ今の版の SVG から引き、文字は前後とも解析した結果で比べる
        const drawn = extractDiagram(afterSvg, "flowchart");
        const nodes = new Map();
        for (const [key, node] of drawn.nodes)
            nodes.set(key, { ...node, text: parsedNow.nodes.get(key)?.text ?? node.text });
        // 辺は SVG の `data-id` を解析した辺の `id` と突き合わせ、解析した辺の鍵で引く（`edgeEnds` で `data-id` を切ると、id に `_` を含むノードや id を付けた辺で前後の鍵がずれる）
        const parsedEdges = new Map(parsedNow.edges.map((edge) => [edge.id, edge]));
        const edges = [];
        for (const edge of drawn.edges) {
            const parsedEdge = parsedEdges.get(edge.element.getAttribute("data-id") ?? "");
            // 解析した結果に無い辺: 版を上げて `data-id` の作り方が変わった
            if (parsedEdge === undefined)
                return null;
            edges.push({ ...edge, key: parsedEdge.key, text: parsedEdge.text });
        }
        return compareDiagrams({ flavor: "flowchart", previous, current: { nodes, edges } });
    }
    MindmapPreview.diffDiagramFromSource = diffDiagramFromSource;
})(MindmapPreview || (MindmapPreview = {}));
