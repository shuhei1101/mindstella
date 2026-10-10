"use strict";
// HTML の本文の枠。HTML の本文と Markdown の中の `html` のコードブロックを、スクリプトを動かさない枠（`sandbox="allow-same-origin"` の iframe の `srcdoc`）に描く。枠の高さは描いた中身に合わせ、枠の中で選んだ文を元の HTML の行の範囲にして使う側へ知らせる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 描く前の枠の高さ（px）。描いた後に中身の高さへ伸びる */
    const FRAME_INITIAL_HEIGHT = 120;
    /** 描き終えた枠が持つ属性（描き終えたかを呼び出し側が確かめる） */
    const RENDERED_ATTR = "data-rendered";
    /** 差分の印を付けた要素が持つ属性 */
    const MARK_ATTR = "data-df";
    /** 行の印（` data-line="n"`）を外して、原文に戻す */
    function withoutHtmlLineMarks(marked) {
        return marked.replace(/ data-line="\d+"/g, "");
    }
    /** 枠の文書の中で、行を含む最も内側の行の印を持つ要素（無ければ null） */
    function innermostAt({ doc, line }) {
        let found = null;
        for (const element of doc.body.querySelectorAll(`[${MindmapPreview.HTML_LINE_ATTR}]`)) {
            const start = Number(element.getAttribute(MindmapPreview.HTML_LINE_ATTR));
            const end = start + (element.outerHTML.split("\n").length - 1);
            if (start <= line && line <= end)
                found = element;
        }
        return found;
    }
    /** コメントの一覧から開いたとき、枠の中でその行を含む最も内側の行の印を持つ要素を印の色の地で示し、その要素が見える位置まで `scroller` を送る。枠を描いた後に呼ぶ */
    function highlightFrameLine({ frame, line, scroller }) {
        const show = () => {
            const doc = frame.contentDocument;
            const hit = doc === null ? null : innermostAt({ doc, line });
            if (doc === null || hit === null)
                return;
            const color = getComputedStyle(document.documentElement).getPropertyValue("--hit").trim();
            const style = doc.createElement("style");
            style.textContent = `[data-loc-hit]{background-color:${color} !important;border-radius:2px;box-shadow:0 0 0 2px ${color}}`;
            doc.head.append(style);
            hit.setAttribute("data-loc-hit", "");
            // 要素が本文の領域の中央に来るまで送る（枠の位置に枠の中の要素の位置を足す）
            if (scroller === null)
                return;
            const offset = frame.getBoundingClientRect().top + hit.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
            scroller.scrollTop += offset - scroller.clientHeight / 2;
        };
        // 描き終わっていれば今、そうでなければ描き終えてから
        if (frame.hasAttribute(RENDERED_ATTR))
            show();
        else
            frame.addEventListener("load", show, { once: true });
    }
    MindmapPreview.highlightFrameLine = highlightFrameLine;
    /** 描いた結果の上で、足した行・変わった行を含む要素に枠と地の色の印を付ける（色は画面の差分の色を枠の文書へ写す） */
    function paintMarks({ doc, marks }) {
        const css = getComputedStyle(document.documentElement);
        const color = (name) => css.getPropertyValue(name).trim();
        const style = doc.createElement("style");
        style.textContent =
            `[${MARK_ATTR}="add"]{outline:2px solid ${color("--df-add")} !important;outline-offset:2px;background-color:${color("--df-add-bg")} !important}` +
                `[${MARK_ATTR}="chg"]{outline:2px dashed ${color("--df-chg")} !important;outline-offset:2px;background-color:${color("--df-chg-bg")} !important}`;
        doc.head.append(style);
        for (const [mark, lines] of [
            ["add", marks.added],
            ["chg", marks.changed],
        ]) {
            for (const line of lines)
                innermostAt({ doc, line })?.setAttribute(MARK_ATTR, mark);
        }
    }
    /** 枠の文書で選んでいる範囲を、親の画面の座標の矩形つきの選択にする（空の選択・行の印の外は null） */
    function frameSelection({ frame, original }) {
        const selection = frame.contentWindow?.getSelection() ?? null;
        if (selection === null || selection.rangeCount === 0 || selection.isCollapsed)
            return null;
        const range = selection.getRangeAt(0);
        const location = MindmapPreview.htmlSelectionLocation(range, original);
        const rects = range.getClientRects();
        const first = rects[0];
        const last = rects[rects.length - 1];
        if (location === null || location.start === undefined || location.end === undefined)
            return null;
        if (first === undefined || last === undefined)
            return null;
        const outer = frame.getBoundingClientRect();
        const shift = (rect) => new DOMRect(rect.left + outer.left + frame.clientLeft, rect.top + outer.top + frame.clientTop, rect.width, rect.height);
        return { start: location.start, end: location.end, text: location.text, rects: { first: shift(first), last: shift(last) } };
    }
    /** HTML の本文の枠。スクリプトを動かさず（sandbox に `allow-scripts` を付けない）、高さを描いた中身に合わせる */
    function htmlBodyFrame({ source, selectable = true, label = "本文（HTML）", marks, on }) {
        const frame = MindmapPreview.h({
            tag: "iframe",
            attrs: {
                class: "html-frame",
                sandbox: "allow-same-origin",
                title: label,
                style: `height:${FRAME_INITIAL_HEIGHT}px`,
            },
        });
        const original = selectable ? withoutHtmlLineMarks(source) : source;
        frame.addEventListener("load", () => {
            const doc = frame.contentDocument;
            if (doc === null)
                return;
            frame.setAttribute(RENDERED_ATTR, "");
            // 高さを描いた中身に合わせる（中身が変わっても追う）。枠の線の分を足し、枠の中に縦のスクロールの帯を出さない
            doc.documentElement.style.overflowY = "hidden";
            new ResizeObserver(() => {
                frame.style.height = `${Math.ceil(doc.documentElement.getBoundingClientRect().height) + frame.offsetHeight - frame.clientHeight}px`;
            }).observe(doc.documentElement);
            if (marks !== undefined)
                paintMarks({ doc, marks });
            if (!selectable)
                return;
            // 選び終えた（空でない選択）・選びを外した（空になった）を知らせる
            let selected = false;
            const report = () => {
                const selection = frameSelection({ frame, original });
                if (selection !== null) {
                    selected = true;
                    on?.select?.(selection);
                }
                else if (selected) {
                    selected = false;
                    on?.clear?.();
                }
            };
            // ポインターを押している間は知らせず、選び終えてから知らせる（入口が選択の途中で出ない）
            let held = false;
            doc.addEventListener("pointerdown", () => {
                held = true;
            });
            doc.addEventListener("pointerup", () => {
                held = false;
                report();
            });
            doc.addEventListener("selectionchange", () => {
                if (!held)
                    report();
            });
        });
        frame.srcdoc = source;
        return frame;
    }
    MindmapPreview.htmlBodyFrame = htmlBodyFrame;
})(MindmapPreview || (MindmapPreview = {}));
