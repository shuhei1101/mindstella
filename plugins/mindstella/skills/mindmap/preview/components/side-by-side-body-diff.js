"use strict";
// 左右に並べた本文の差分。Markdown の本文を左に選んだ時点、右に今で描き、変えていない塊を同じ高さで向かい合わせる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 列の名前（列の頭に出し、列の読み上げの名前にも使う） */
    const SIDE_COLUMN_NAMES = { before: "選んだ時点", after: "今" };
    /** 本文を行の並びにする（末尾の改行で出る空の最後の要素は行ではない） */
    function splitLines(text) {
        const lines = text.split("\n");
        if (lines.at(-1) === "")
            lines.pop();
        return lines;
    }
    /** 片側の描いたブロックの、変えた行を持つ要素に印を付ける（段落・見出し・コードは囲み、表の行と箇条書きの項目は行の印にする） */
    function markSideBlocks({ root, lines, changed, op }) {
        if (changed.size === 0)
            return;
        const blocks = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const owners = MindmapPreview.blockOwners({ now: lines, starts: blocks.map((block) => Number(block.getAttribute(MindmapPreview.LINE_ATTR))) });
        const marked = new Set();
        for (const line of changed) {
            const owner = owners[line - 1];
            if (owner !== null && owner !== undefined)
                marked.add(owner);
        }
        for (const block of blocks) {
            if (!marked.has(Number(block.getAttribute(MindmapPreview.LINE_ATTR))))
                continue;
            if (block.tagName === "TR") {
                block.classList.add("df-row", `df-${op}`);
                block.firstElementChild?.prepend(...MindmapPreview.signMarks(op));
            }
            else if (block.tagName === "LI") {
                block.classList.add(`df-li-${op}`);
            }
            else {
                // 囲みを元の位置に置いてから、ブロックを囲みの中へ移す
                const wrapper = MindmapPreview.diffBlock({ op, children: [] });
                block.replaceWith(wrapper);
                wrapper.append(block);
            }
        }
    }
    /** 片側の列の中で、語の面を付ける印の付いたブロック（文書の順） */
    function sideWordBlocks({ cell, op }) {
        const tag = op === "del" ? "del" : "ins";
        return [...cell.querySelectorAll(`${tag}.df-blk, tr.df-${op}, li.df-li-${op}`)].flatMap((element) => element.matches(".df-blk") ? MindmapPreview.wordBlocksIn(element) : [element]);
    }
    /** 左右の列の行の高さを揃える（変えていない部分を向かい合わせる）。描いた図・文字の読み込みで高さが変わったら、次のコマで 1 回だけ揃え直す */
    function alignSideRows(wrapper) {
        const [left, right] = wrapper.querySelectorAll(".sbs-col");
        if (left === undefined || right === undefined)
            return;
        let queued = false;
        const align = () => {
            queued = false;
            const pairs = [...left.children].flatMap((row, offset) => {
                const opposite = right.children[offset];
                return row instanceof HTMLElement && opposite instanceof HTMLElement ? [[row, opposite]] : [];
            });
            // いったん外してから測り、高い方に揃える
            for (const [a, b] of pairs) {
                a.style.minHeight = "";
                b.style.minHeight = "";
            }
            const heights = pairs.map(([a, b]) => Math.max(a.getBoundingClientRect().height, b.getBoundingClientRect().height));
            pairs.forEach(([a, b], offset) => {
                a.style.minHeight = `${heights[offset]}px`;
                b.style.minHeight = `${heights[offset]}px`;
            });
        };
        const schedule = () => {
            if (queued)
                return;
            queued = true;
            requestAnimationFrame(align);
        };
        const observer = new ResizeObserver(schedule);
        observer.observe(wrapper);
        for (const block of wrapper.querySelectorAll(".sbs-row > *"))
            observer.observe(block);
        schedule();
    }
    /** 前後の本文を、左に選んだ時点・右に今を描いて並べる。行の差分を打ち切ったら null */
    function sideBySideBodyDiff({ before, after, lined = true, deadline }) {
        const rows = MindmapPreview.sideBySideRows({ before, after });
        if (rows === null)
            return null;
        const beforeLines = splitLines(before);
        const afterLines = splitLines(after);
        const leftCol = MindmapPreview.h({ tag: "section", attrs: { class: "sbs-col sbs-before", "aria-label": `${SIDE_COLUMN_NAMES.before}の本文` } });
        const rightCol = MindmapPreview.h({ tag: "section", attrs: { class: "sbs-col sbs-after", "aria-label": `${SIDE_COLUMN_NAMES.after}の本文` } });
        // 行ごとに、左右の行の入れ物と、そこへ置く塊を描く
        const pending = [];
        const pieces = [];
        for (const row of rows) {
            const changed = row.changed && (row.left.some((block) => block.changed.size > 0) || row.right.some((block) => block.changed.size > 0) || row.left.length !== row.right.length);
            const cell = (blocks) => {
                const element = MindmapPreview.h({ tag: "div", attrs: { class: `sbs-row${changed ? " sbs-chg" : ""}` } });
                // 向かいにしか無い行: 同じ高さの空きを置く
                if (blocks.length === 0) {
                    element.classList.add("sbs-gap");
                    element.setAttribute("aria-hidden", "true");
                }
                return element;
            };
            const entry = { leftCell: cell(row.left), rightCell: cell(row.right), changed, left: row.left, right: row.right };
            pending.push(entry);
            // 前に空行を積んで、描いた要素の行の印を本文の中の行に揃える
            const render = (block) => MindmapPreview.renderMarkdown(`${"\n".repeat(block.start - 1)}${block.raw}`);
            for (const block of row.left)
                pieces.push({ cell: entry.leftCell, block, lines: beforeLines, op: "del", rendered: render(block) });
            for (const block of row.right)
                pieces.push({ cell: entry.rightCell, block, lines: afterLines, op: "add", rendered: render(block) });
        }
        // 見出しの段は、左右の全ての塊を合わせた最も上の段から 1 つの差を求めて全てに当てる
        const shift = MindmapPreview.headingShift(pieces.map((piece) => piece.rendered));
        for (const { cell, block, lines, op, rendered } of pieces) {
            MindmapPreview.lowerHeadings({ root: rendered, shift });
            markSideBlocks({ root: rendered, lines, changed: block.changed, op });
            // 変えた図は、左では枠の色だけを付ける（色付けは右の図にだけ付ける）
            if (op === "del" && block.changed.size > 0) {
                for (const figure of rendered.querySelectorAll("figure.diagram"))
                    figure.classList.add("sbs-was");
            }
            cell.append(rendered);
        }
        const wordPairsFound = [];
        const diagramPairs = [];
        const sourceOf = (figure) => figure?.querySelector(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
        for (const { leftCell, rightCell, changed } of pending) {
            // 左の列は選んだ時点の行なので、選んだ箇所のコメントを向けない
            MindmapPreview.withoutLineMarks(leftCell);
            if (!lined)
                MindmapPreview.withoutLineMarks(rightCell);
            leftCol.append(leftCell);
            rightCol.append(rightCell);
            if (!changed)
                continue;
            // 向かい合う変えたブロックの数が同じときだけ、語の面を付ける対にする
            const removed = sideWordBlocks({ cell: leftCell, op: "del" });
            const added = sideWordBlocks({ cell: rightCell, op: "add" });
            if (removed.length > 0 && removed.length === added.length) {
                removed.forEach((block, offset) => {
                    const opposite = added[offset];
                    if (opposite !== undefined)
                        wordPairsFound.push({ removed: block, added: opposite });
                });
            }
            // 変えた図: 同じ行の左右の図を並びの順で組にする（左に無ければ足した図）
            const leftFigures = [...leftCell.querySelectorAll("figure.diagram")];
            rightCell.querySelectorAll("figure.diagram").forEach((figure, offset) => {
                const beforeSource = sourceOf(leftFigures[offset]);
                if (beforeSource.trim() !== sourceOf(figure).trim())
                    diagramPairs.push({ figure, beforeSource });
            });
        }
        const root = MindmapPreview.h({
            tag: "div",
            attrs: { class: "sbs" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "sbs-head", "aria-hidden": "true" },
                    children: [MindmapPreview.h({ tag: "span", children: [SIDE_COLUMN_NAMES.before] }), MindmapPreview.h({ tag: "span", children: [SIDE_COLUMN_NAMES.after] })],
                }),
                MindmapPreview.h({ tag: "div", attrs: { class: "sbs-cols" }, children: [leftCol, rightCol] }),
            ],
        });
        alignSideRows(root);
        return {
            root,
            columns: [leftCol, rightCol],
            markWords: () => wordPairsFound.forEach((pair) => MindmapPreview.markWords({ pair, deadline })),
            decorate: () => diagramPairs.forEach(({ figure, beforeSource }) => void MindmapPreview.decorateDiagram({ figure, beforeSource })),
        };
    }
    MindmapPreview.sideBySideBodyDiff = sideBySideBodyDiff;
})(MindmapPreview || (MindmapPreview = {}));
