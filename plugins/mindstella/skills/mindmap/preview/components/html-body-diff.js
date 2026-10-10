"use strict";
// HTML の本文の差分。差分の表示の間、HTML の本文を描いた結果の上で変わった行を含む要素に印を付け、「原文の差分」に切り替えると原文の行の差分を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 原文の差分で、同じ行がこの数を超えて続くときは前後だけを残して畳む（前後に残す行数） */
    const RAW_DIFF_CONTEXT = 3;
    /** 原文の行の差分。足した行・消した行に印を付け、変わっていない長い並びは前後 3 行を残して件数の行にする */
    function rawDiff({ parts }) {
        const lines = [];
        parts.forEach((part, position) => {
            if (part.kind !== "same" || part.lines.length <= RAW_DIFF_CONTEXT * 2) {
                lines.push(...MindmapPreview.rawDiffLines([part]));
                return;
            }
            // 先頭・末尾の並びは、変わった行の側だけを残す
            const head = position === 0 ? [] : part.lines.slice(0, RAW_DIFF_CONTEXT);
            const tail = position === parts.length - 1 ? [] : part.lines.slice(-RAW_DIFF_CONTEXT);
            const skipped = part.lines.length - head.length - tail.length;
            lines.push(...MindmapPreview.rawDiffLines([{ kind: "same", lines: head }]));
            lines.push(MindmapPreview.h({ tag: "span", attrs: { class: "df-line df-skip" }, children: [`変わっていない ${skipped} 行`] }));
            lines.push(...MindmapPreview.rawDiffLines([{ kind: "same", lines: tail }]));
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "html-diff" },
            children: [
                MindmapPreview.h({ tag: "p", attrs: { class: "html-diff-head" }, children: ["原文の差分"] }),
                MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw df-raw", tabindex: "0", "aria-label": "原文の差分" }, children: lines }),
            ],
        });
    }
    /** 凡例（足した・変わった）。消しただけの箇所があるときは、原文の差分で見られる旨を添える */
    function legend({ removedOnly }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "df-legend" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } }), "足した"] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "df-lg df-lg-chg" }, children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } }), "変わった"] }),
                removedOnly ? MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["消した箇所は原文の差分で見られます"] }) : null,
            ],
        });
    }
    /** HTML の本文の差分。差分を計算しきれなかったときは null */
    function htmlBodyDiff({ before, after, marked, beforeFormat = "html" }) {
        const parts = MindmapPreview.diffLineParts(before, after);
        if (parts === null)
            return null;
        const raw = rawDiff({ parts });
        // 選んだ時点の本文が Markdown: 描いた結果の印と切り替えを出さず、原文の差分だけを出す
        if (beforeFormat === "md")
            return raw;
        const changed = MindmapPreview.htmlChangedLines(before, after);
        if (changed === null)
            return null;
        // 選んだ箇所のコメントの入口は出さない（差分の表示の間は今の本文の行と合わない場合がある）
        const rendered = MindmapPreview.h({
            tag: "div",
            attrs: { class: "html-marked" },
            children: [MindmapPreview.htmlBodyFrame({ source: marked, selectable: false, marks: { added: changed.added, changed: changed.changed } })],
        });
        raw.hidden = true;
        const legendElement = legend({ removedOnly: changed.removedOnly });
        /** 描いた結果と原文の差分を切り替えるボタン */
        const toggle = (label, showRaw) => MindmapPreview.h({
            tag: "button",
            attrs: {
                type: "button",
                "aria-pressed": String(!showRaw),
                onclick: (event) => {
                    const pressed = event.currentTarget;
                    for (const button of pressed.parentElement?.children ?? [])
                        button.setAttribute("aria-pressed", String(button === pressed));
                    raw.hidden = !showRaw;
                    rendered.hidden = showRaw;
                    legendElement.hidden = showRaw;
                },
            },
            children: [label],
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "html-diff-c" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "html-diff-bar" },
                    children: [
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "segment", role: "group", "aria-label": "本文の差分の見せ方" },
                            children: [toggle("描いた結果", false), toggle("原文の差分", true)],
                        }),
                        legendElement,
                    ],
                }),
                rendered,
                raw,
            ],
        });
    }
    MindmapPreview.htmlBodyDiff = htmlBodyDiff;
})(MindmapPreview || (MindmapPreview = {}));
