"use strict";
// 画面が共通で使う要素の組み立てと、アイコン・状態の印。
var MindmapPreview;
(function (MindmapPreview) {
    /** 要素を作る。属性とイベントのリスナーを付け、子を並べる */
    function h({ tag, attrs, children, }) {
        const element = document.createElement(tag);
        for (const [name, value] of Object.entries(attrs ?? {})) {
            // 値が無い・偽の属性は付けない
            if (value === null || value === undefined || value === false)
                continue;
            if (typeof value === "function") {
                // `onclick` → click のリスナー
                element.addEventListener(name.slice(2), value);
            }
            else if (name === "class") {
                element.className = String(value);
            }
            else {
                element.setAttribute(name, value === true ? "" : String(value));
            }
        }
        append({ parent: element, children: children ?? [] });
        return element;
    }
    MindmapPreview.h = h;
    /** 要素の中に子を足す（文字は textContent として入れる） */
    function append({ parent, children }) {
        for (const child of children) {
            if (child === null || child === undefined || child === false)
                continue;
            parent.append(typeof child === "number" ? String(child) : child);
        }
    }
    MindmapPreview.append = append;
    /** アイコンの名前 → SVG の中身（線の絵） */
    const ICONS = {
        search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
        sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
        moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>',
        x: '<path d="M18 6 6 18M6 6l12 12"/>',
        back: '<path d="m15 18-6-6 6-6"/>',
        chev: '<path d="m9 6 6 6-6 6"/>',
        filter: '<path d="M4 5h16l-6 7.5V19l-4-2v-4.5Z"/>',
        pin: '<path d="M9 4h6l-1 5 3 3v2H7v-2l3-3Z"/><path d="M12 14v6"/>',
        up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
        down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
        updown: '<path d="m8 9 4-4 4 4M8 15l4 4 4-4"/>',
        cols: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M9 4v16M15 4v16"/>',
        table: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M9 10v10"/>',
        board: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="11" rx="1"/><rect x="17" y="4" width="4" height="7" rx="1"/>',
        shrink: '<path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/>',
        hash: '<path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/>',
        expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
        check: '<path d="m5 12 5 5 9-10"/>',
        checked: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 5-6"/>',
        unchecked: '<rect x="4" y="4" width="16" height="16" rx="3"/>',
        copy: '<rect x="9" y="9" width="12" height="12" rx="1"/><path d="M5 15V4a1 1 0 0 1 1-1h11"/>',
        network: '<path d="M4 18.5 10 13.5l5 3M10 13.5 7.5 6.5M15 16.5l3.2-6.6" stroke-width="1.15"/><circle cx="4" cy="18.5" r="2" fill="currentColor" stroke="none"/><circle cx="10" cy="13.5" r="2.2" fill="currentColor" stroke="none"/><circle cx="15" cy="16.5" r="1.8" fill="currentColor" stroke="none"/><circle cx="7.5" cy="6.5" r="1.8" fill="currentColor" stroke="none"/><path d="m19 1.8 1.05 3.15L23.2 6l-3.15 1.05L19 10.2l-1.05-3.15L14.8 6l3.15-1.05Z" fill="currentColor" stroke="none"/>',
        lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
        unlock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
        cards: '<rect x="3" y="4" width="8" height="7" rx="1"/><rect x="13" y="4" width="8" height="7" rx="1"/><rect x="3" y="13" width="8" height="7" rx="1"/><rect x="13" y="13" width="8" height="7" rx="1"/>',
        map: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 12h3l4-5M11.5 12l4 5"/>',
        graph: '<circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="7" r="2"/><circle cx="6" cy="20" r="2"/><circle cx="19" cy="19" r="2"/><path d="M9.5 10.5 5.6 7.2M14.6 10.9l3.6-2.6M10 14.4l-2.6 4M14.3 14.2l3.3 3.4"/>',
        link: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
        pause: '<path d="M8 5v14M16 5v14"/>',
        play: '<path d="m7 5 12 7-12 7Z"/>',
        flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
        alert: '<path d="M12 3 2 20h20Z"/><path d="M12 10v4M12 17h.01"/>',
        next: '<circle cx="12" cy="12" r="9"/><path d="M10 8l4 4-4 4"/>',
        layers: '<path d="m12 3 9 5-9 5-9-5Z"/><path d="m3 13 9 5 9-5"/>',
        follow: '<path d="M5 5v6a4 4 0 0 0 4 4h10"/><path d="m15 11 4 4-4 4"/>',
        deps: '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 6H14a4 4 0 0 1 4 4v5.5"/>',
        box: '<path d="M3 7l9-4 9 4v10l-9 4-9-4Z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
        home: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>',
        decision: '<circle cx="12" cy="12" r="8"/><path d="m9 12 2 2 4-4"/>',
        task: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',
        research: '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/><path d="M8 10.5h5"/>',
        doc: '<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v4h4"/>',
        term: '<path d="M4 5h11a3 3 0 0 1 3 3v12H7a3 3 0 0 1-3-3Z"/><path d="M4 17a3 3 0 0 1 3-3h11"/>',
        note: '<path d="M5 4h14v12l-4 4H5Z"/><path d="M15 20v-4h4"/>',
        log: '<path d="M4 6h16v10H9l-5 4Z"/>',
        send: '<path d="M4 12 20 4l-4 16-4-6Z"/><path d="m12 14 8-10"/>',
        comment: '<path d="M4 5h16v11H10l-5 4v-4H4Z"/><path d="M8 9h8M8 12.5h5"/>',
        bubble: '<path d="M5 4h14a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-7l-5 4v-4H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z"/>',
        edit: '<path d="m4 20 1-4L16 5l3 3L8 19Z"/><path d="m14 7 3 3"/>',
        trash: '<path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13"/><path d="M10 11v6M14 11v6"/>',
        undo: '<path d="M9 7 4 12l5 5"/><path d="M4 12h10a5 5 0 0 1 0 10h-2"/>',
        history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
        plus: '<path d="M12 5v14M5 12h14"/>',
        minus: '<path d="M5 12h14"/>',
        changed: '<circle cx="12" cy="12" r="5"/>',
        arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
        save: '<path d="M5 4h11l3 3v13H5Z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
        sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
        star: '<path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9Z"/>',
        offline: '<path d="M3 3l18 18"/><path d="M8.5 8.6A4.5 4.5 0 0 0 7 17h10.5M16 10.2A4.5 4.5 0 0 1 20.2 16"/>',
    };
    /** 24px の枠に描いた線のアイコン（読み上げ名は付けず、装飾として隠す）。大きさは `svg.icon` の CSS が決め、無いときも広がらないよう既定の 16px を属性に持つ */
    function icon(name) {
        const holder = document.createElement("template");
        holder.innerHTML = `<svg class="icon" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
        return holder.content.firstElementChild;
    }
    MindmapPreview.icon = icon;
    /** 状態 → 10px の枠に描く印（色に加えて形でも区別する） */
    const MARKS = {
        決定済み: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
        完了: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/><path d="m2.8 5.1 1.5 1.5 3-3" stroke="var(--surface)" stroke-width="1.4" fill="none"/>',
        未決定: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/>',
        未着手: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6"/>',
        進行中: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
        要見直し: '<path d="M5 .3 9.7 5 5 9.7.3 5Z" fill="var(--st-review)"/>',
        保留: '<rect x="1.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/><rect x="6.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/>',
        未整理: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-loose)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
        取り下げ: '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
        対象外: '<path d="M1 5h8" stroke="var(--st-off)" stroke-width="1.8"/>',
        中止: '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
        下書き: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
        確認中: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
        完成: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
    };
    /** 状態の印。知らない状態は印なし（null） */
    function statusMark(status) {
        const body = status === undefined ? undefined : MARKS[status];
        if (body === undefined)
            return null;
        const holder = document.createElement("template");
        holder.innerHTML = `<svg class="mark" viewBox="0 0 10 10" aria-hidden="true">${body}</svg>`;
        return holder.content.firstElementChild;
    }
    MindmapPreview.statusMark = statusMark;
    /** 印と状態の名前を並べた表示。状態を持たない項目は空の断片 */
    function statusBadge(status) {
        if (status === undefined)
            return document.createDocumentFragment();
        return h({
            tag: "span",
            attrs: { class: "st", "data-st": status },
            children: [statusMark(status), status],
        });
    }
    MindmapPreview.statusBadge = statusBadge;
    /** 左から重ねるパネル（絞り込みのドロワー・コメントの一覧）が覆った本文の部品に `inert` を付け、外す関数を返す */
    function inertBehind(panel) {
        // 開く動き（`transform`）の途中でも、重なる先の位置で覆う範囲を決めるため、配置の位置から求める
        const covered = {
            left: panel.offsetLeft,
            top: panel.offsetTop,
            right: panel.offsetLeft + panel.offsetWidth,
            bottom: panel.offsetTop + panel.offsetHeight,
        };
        const attached = [];
        /** 要素がパネルの矩形に全体が収まるなら `inert` を付け、一部だけ重なるなら子をたどる */
        const visit = (element) => {
            // パネル自身と、始めから `inert` の要素（その子も止まっている）には付けない
            if (element === panel || element.inert)
                return;
            const rect = element.getBoundingClientRect();
            // 大きさを持たない要素（`display: contents` など）は、子をたどる
            if (rect.width === 0 || rect.height === 0) {
                for (const child of element.children)
                    if (child instanceof HTMLElement)
                        visit(child);
                return;
            }
            const overlaps = rect.left < covered.right && rect.right > covered.left && rect.top < covered.bottom && rect.bottom > covered.top;
            if (!overlaps)
                return;
            const inside = rect.left >= covered.left && rect.right <= covered.right && rect.top >= covered.top && rect.bottom <= covered.bottom;
            // 全体が収まり、パネルを中に持たない要素は、まとめて止める
            if (inside && !element.contains(panel)) {
                element.inert = true;
                attached.push(element);
                return;
            }
            for (const child of element.children)
                if (child instanceof HTMLElement)
                    visit(child);
        };
        const main = document.querySelector("main");
        if (main !== null)
            for (const child of main.children)
                if (child instanceof HTMLElement)
                    visit(child);
        return () => {
            for (const element of attached)
                element.inert = false;
        };
    }
    MindmapPreview.inertBehind = inertBehind;
    /** 影響度（大・中・小）の 3 本の目盛りと文字 */
    function impactBadge(weight, labeled = false) {
        const levels = ["大", "中", "小"];
        // 大・中・小のどれでもない値は、影響度を持たないものとして空の断片にする
        if (weight === undefined || !levels.includes(weight))
            return document.createDocumentFragment();
        const filled = 3 - levels.indexOf(weight);
        const bars = [0, 1, 2].map((index) => h({ tag: "i", attrs: { class: index < filled ? "on" : "" } }));
        return h({
            tag: "span",
            attrs: { class: "impact", title: `影響度 ${weight}` },
            children: [
                h({ tag: "span", attrs: { "aria-hidden": "true" }, children: [...bars] }),
                labeled ? `影響度 ${weight}` : weight,
            ],
        });
    }
    MindmapPreview.impactBadge = impactBadge;
    /** タグを並べる */
    function tagList(values) {
        const fragment = document.createDocumentFragment();
        for (const value of values ?? [])
            fragment.append(h({ tag: "span", attrs: { class: "tag" }, children: [value] }));
        return fragment;
    }
    MindmapPreview.tagList = tagList;
    /** 納品物の印（箱のアイコンと文字） */
    function deliverableBadge() {
        return h({ tag: "span", attrs: { class: "deliv-badge" }, children: [icon("box"), "納品物"] });
    }
    MindmapPreview.deliverableBadge = deliverableBadge;
    /** 「該当なし」など、空のときの 1 行 */
    function emptyNote(text) {
        return h({ tag: "p", attrs: { class: "empty" }, children: [text] });
    }
    MindmapPreview.emptyNote = emptyNote;
    /** 背景を押してから離すまでのポインターの移動（縦・横それぞれの px）がこの値以内なら、ドラッグではなく押したとみなす */
    const PRESS_SLOP_PX = 5;
    /** 背景（ボタンなどの上でない所）をつかんで、スクロールする要素を動かせるようにする。`onPress` は、背景を押して離したとき（ドラッグでないとき）に、離したときのイベントを渡して呼ぶ */
    function enableDragScroll(scroller, onPress) {
        let drag = null;
        scroller.addEventListener("pointerdown", (event) => {
            // 左ボタンで、押せるものの上でないとき
            if (event.button !== 0 || event.target.closest("button, a, input, label"))
                return;
            drag = { x: event.clientX, y: event.clientY, left: scroller.scrollLeft, top: scroller.scrollTop, moved: false };
            scroller.classList.add("dragging");
            scroller.setPointerCapture(event.pointerId);
        });
        scroller.addEventListener("pointermove", (event) => {
            if (drag === null)
                return;
            const dx = event.clientX - drag.x;
            const dy = event.clientY - drag.y;
            // 一度でも上限を超えて動いたら、離した位置が近くてもドラッグとして扱う
            if (Math.abs(dx) > PRESS_SLOP_PX || Math.abs(dy) > PRESS_SLOP_PX)
                drag.moved = true;
            scroller.scrollLeft = drag.left - dx;
            scroller.scrollTop = drag.top - dy;
        });
        const release = () => {
            drag = null;
            scroller.classList.remove("dragging");
        };
        scroller.addEventListener("pointerup", (event) => {
            const pressed = drag !== null && !drag.moved;
            release();
            if (pressed)
                onPress?.(event);
        });
        scroller.addEventListener("pointercancel", release);
    }
    MindmapPreview.enableDragScroll = enableDragScroll;
    /** 詳細パネルで開いている項目の ID（表の行・カード・マップの節に「選択中」の印を付けるために持つ） */
    let selectedItemId = null;
    /** 開いている項目の ID */
    function currentSelection() {
        return selectedItemId;
    }
    MindmapPreview.currentSelection = currentSelection;
    /** 開いている項目を変え、描いてある行・カード・節の「選択中」の印を付け替える */
    function markSelected(id) {
        selectedItemId = id;
        for (const element of document.querySelectorAll("main [data-id]")) {
            element.classList.toggle("selected", element.dataset["id"] === id);
        }
    }
    MindmapPreview.markSelected = markSelected;
})(MindmapPreview || (MindmapPreview = {}));
