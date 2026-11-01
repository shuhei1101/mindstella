"use strict";
// develop のプレビューのスクリプト（tsc が生成した .js を build の順につないだもの）に、PR #390 の変更を当てたもの。
// #390 で当てた箇所には「390:」のコメントを付けた。
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
        download: '<path d="M12 4v11M7 10l5 5 5-5"/><path d="M5 20h14"/>',
        code: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>',
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
        spin: '<path d="M12 3a9 9 0 1 0 9 9"/>',
        offline: '<path d="M3 3l18 18"/><path d="M8.5 8.6A4.5 4.5 0 0 0 7 17h10.5M16 10.2A4.5 4.5 0 0 1 20.2 16"/>',
        main: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.5" fill="currentColor"/>',
        mainOff: '<circle cx="12" cy="12" r="8"/>',
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
    MindmapPreview.PRESS_SLOP_PX = 5;
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
            if (Math.abs(dx) > MindmapPreview.PRESS_SLOP_PX || Math.abs(dy) > MindmapPreview.PRESS_SLOP_PX)
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
// 記録の索引・関係する項目・検索・箇所の名前。次の候補・ゴールまでの進捗・カテゴリー別の進捗は build が計算した `derived` を使い、画面で計算し直さない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 項目の種類の並び（ID の頭の文字の順と同じ） */
    MindmapPreview.KIND_KEYS = [
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
        "logs",
    ];
    /** 種類 → 画面に出す名前 */
    MindmapPreview.KIND_LABEL = {
        decisions: "検討事項",
        tasks: "タスク",
        research: "調査",
        docs: "資料",
        terms: "用語集",
        notes: "メモ",
        logs: "会話ログ",
    };
    /** ID の頭の文字 → 種類 */
    const KIND_OF_PREFIX = {
        D: "decisions",
        T: "tasks",
        R: "research",
        A: "docs",
        G: "terms",
        N: "notes",
        L: "logs",
    };
    /** 検討事項の状態の並び（画面で状態を並べるときの順） */
    MindmapPreview.DECISION_STATUSES = [
        "要見直し",
        "未決定",
        "保留",
        "未整理",
        "決定済み",
        "対象外",
        "取り下げ",
    ];
    /** タスクの状態の並び */
    MindmapPreview.TASK_STATUSES = ["未着手", "進行中", "保留", "完了", "中止"];
    /** 資料の状態の並び */
    MindmapPreview.DOC_STATUSES = ["下書き", "確認中", "完成"];
    /** 項目が別の項目を指すキー */
    const REFERENCE_KEYS = ["depends_on", "for", "related", "sources"];
    /** 項目の `tags` から名前だけを並びの順に取り出す（文字列のタグはそのまま） */
    function tagNames(tags) {
        return (tags ?? []).map((tag) => (typeof tag === "string" ? tag : tag.name));
    }
    MindmapPreview.tagNames = tagNames;
    /** ID を種類の順 → 連番の順に比べる */
    function compareIds(a, b) {
        const rank = (id) => MindmapPreview.KIND_KEYS.indexOf(KIND_OF_PREFIX[id.slice(0, 1)] ?? "logs");
        return rank(a) - rank(b) || Number(a.slice(2)) - Number(b.slice(2));
    }
    MindmapPreview.compareIds = compareIds;
    // 390: 関連の 1 件は `{to, type, when}`。指す先は `to`（前の形式の ID の文字列もそのまま読む）
    function refTarget(value) {
        return typeof value === "string" ? value : value?.to;
    }
    MindmapPreview.refTarget = refTarget;
    // 390: 関連の種類 → 画面に出す名前と、名前の意味（読み上げの補足）
    MindmapPreview.RELATION_TYPES = {
        requires: { label: "必読", meaning: "読まずに進めると、この項目の決まりを外す" },
        references: { label: "参考", meaning: "読むと判断の材料が増える" },
        replaces: { label: "置き換え", meaning: "この項目が相手に取って代わる" },
        part_of: { label: "一部", meaning: "この項目は相手の一部" },
        change_together: { label: "同時に変更", meaning: "一方を修正したらもう一方も修正する" },
    };
    /** 埋め込みのデータから記録の索引を作る */
    function buildIndex(data) {
        const byId = new Map();
        for (const kind of MindmapPreview.KIND_KEYS) {
            for (const item of data[kind])
                byId.set(item.id, { kind, item });
        }
        // 各項目が指す先ごとに、指した側の ID を足す（記録に無い ID もそのまま持つ）
        const referencedBy = new Map();
        for (const { item } of byId.values()) {
            for (const key of REFERENCE_KEYS) {
                for (const raw of item[key] ?? []) {
                    // 390: 関連の要素は `to` を指す先にする
                    const target = refTarget(raw);
                    const sources = referencedBy.get(target) ?? [];
                    sources.push(item.id);
                    referencedBy.set(target, sources);
                }
            }
        }
        for (const sources of referencedBy.values())
            sources.sort(compareIds);
        const index = {
            data,
            byId,
            referencedBy,
            readyIds: new Set(data.derived.next.map((candidate) => candidate.id)),
        };
        // 390: 編集の関連の入力が、相手のタイトルと ID の候補を引くために持つ（モックだけ）
        MindmapPreview.mockIndex390 = index;
        return index;
    }
    MindmapPreview.buildIndex = buildIndex;
    /** 前提・後続・関連タスク・経緯・関連・参照している項目を返す */
    function relatedItems({ id, index }) {
        const entry = index.byId.get(id);
        const item = entry?.item;
        const referrers = index.referencedBy.get(id) ?? [];
        /** ID の項目が、キーで id を指しているか */
        const points = (referrer, key) => (index.byId.get(referrer)?.item[key] ?? []).map(refTarget).includes(id); // 390: 関連は `to` で比べる
        const kindOf = (referrer) => index.byId.get(referrer)?.kind;
        const successors = referrers.filter((referrer) => points(referrer, "depends_on"));
        const tasks = referrers.filter((referrer) => kindOf(referrer) === "tasks" && points(referrer, "for"));
        // 経緯: この項目を更新した会話ログと、この項目が経緯として指す会話ログ
        const incomingLogs = referrers.filter((referrer) => kindOf(referrer) === "logs" && points(referrer, "related"));
        const logs = [...new Set([...incomingLogs, ...(item?.sources ?? [])])].sort(compareIds);
        // 390: 関連は `to` の並び
        const related = (item?.related ?? []).map(refTarget);
        const shown = new Set([...successors, ...tasks, ...logs, ...related]);
        return {
            prerequisites: item?.depends_on ?? [],
            successors,
            tasks,
            logs,
            related,
            referencedBy: referrers.filter((referrer) => !shown.has(referrer)),
        };
    }
    MindmapPreview.relatedItems = relatedItems;
    /** 全体の検索の段の順 */
    const SEARCH_TIERS = [1, 2, 3];
    /** 項目の `body` の拡張子から本文の形式を返す（`body` を持たないか、知らない拡張子なら `null`） */
    function bodyFormatOf(body) {
        if (body === undefined)
            return null;
        if (body.endsWith(".html"))
            return "html";
        if (body.endsWith(".md"))
            return "md";
        return null;
    }
    MindmapPreview.bodyFormatOf = bodyFormatOf;
    /** 描いた文に出ない中身を持つ要素 */
    const HIDDEN_TEXT_SELECTOR = "style, script, template, title";
    /** HTML をスクリプトを動かさずに解析し、`style`・`script`・`template`・`title` の中身とコメントを除いた描いた文を返す */
    function htmlText(source) {
        const doc = new DOMParser().parseFromString(source, "text/html");
        for (const hidden of doc.querySelectorAll(HIDDEN_TEXT_SELECTOR))
            hidden.remove();
        return doc.documentElement.textContent ?? "";
    }
    MindmapPreview.htmlText = htmlText;
    /** Markdown の本文の中の言語指定 `html` のコードブロック（フェンスは ``` か ~~~） */
    const HTML_FENCE = /^(```|~~~)html[^\n]*\n([\s\S]*?)^\1[ \t]*$/gm;
    /** 検索で当てる本文の文。HTML の本文と Markdown の `html` のコードブロックは、タグではなく描いた文にする */
    function searchableBody(body, bodies) {
        const text = bodies[body ?? ""] ?? "";
        if (bodyFormatOf(body) === "html")
            return htmlText(text);
        return text.replace(HTML_FENCE, (_block, _fence, code) => htmlText(code));
    }
    /** 項目の ID・タイトル・文字の値・本文を 1 つの文字列にする（小文字） */
    function searchableText(item, bodies) {
        const parts = [];
        for (const value of Object.values(item)) {
            if (typeof value === "string")
                parts.push(value);
            else if (Array.isArray(value)) {
                for (const element of value)
                    if (typeof element === "string")
                        parts.push(element);
            }
        }
        parts.push(searchableBody(item.body, bodies));
        return parts.join("\n").toLowerCase();
    }
    /** 空白で区切った語を全て含む項目を、段（完全に一致 → タイトルに一致 → ほかの所に一致）の順に返す（大文字・小文字と前後の空白を区別しない） */
    function searchItems({ query, index }) {
        const whole = query.trim().toLowerCase();
        const terms = whole.split(/\s+/).filter(Boolean);
        // 言葉が空なら何も探さない
        if (terms.length === 0)
            return [];
        const hits = [];
        for (const kind of MindmapPreview.KIND_KEYS) {
            const items = [...index.data[kind]].sort((a, b) => compareIds(a.id, b.id));
            for (const item of items) {
                const text = searchableText(item, index.data.bodies);
                if (terms.every((term) => text.includes(term))) {
                    const title = item.title.trim().toLowerCase();
                    const exact = item.id.toLowerCase() === whole || title === whole;
                    const tier = exact ? 1 : terms.every((term) => title.includes(term)) ? 2 : 3;
                    hits.push({ id: item.id, kind, title: item.title, tier });
                }
            }
        }
        // 段の順にする（段の中は種類の順・連番の順のまま）
        return SEARCH_TIERS.flatMap((tier) => hits.filter((hit) => hit.tier === tier));
    }
    MindmapPreview.searchItems = searchItems;
    /** ID の項目のタイトル。記録に無いときは「（記録にありません）」 */
    function titleOf(index, id) {
        return index.byId.get(id)?.item.title ?? "（記録にありません）";
    }
    MindmapPreview.titleOf = titleOf;
    /** 項目のキー → 詳細パネルがそのキーに出す見出し（案の中のキーも同じ辞書） */
    const VALUE_HEADINGS = {
        title: "タイトル",
        status: "状態",
        lead: "問い",
        answer: "決定内容",
        reason: "理由",
        content: "内容",
        pros: "メリット",
        cons: "デメリット",
        note: "備考",
        question: "調べたこと",
        conclusion: "結論",
        meaning: "意味",
        result: "結果",
    };
    /** 案の中のキー（`options[C].cons`）の形 */
    const OPTION_KEY = /^options\[([^\]]+)\]\.(\w+)$/;
    /** 箇所を画面に出す名前にする。本文は行（範囲は「〜」でつなぐ）、値は詳細パネルがそのキーに出す見出し（案の中は「案 {key} の{見出し}」） */
    function locationLabel(loc) {
        if (loc.kind === "body") {
            const start = loc.start ?? 0;
            const end = loc.end ?? start;
            return start === end ? `本文 ${start} 行目` : `本文 ${start}〜${end} 行目`;
        }
        const key = loc.key ?? "";
        const option = OPTION_KEY.exec(key);
        // 案の中の値: 案の記号と見出し
        if (option !== null)
            return `案 ${option[1]} の${VALUE_HEADINGS[option[2] ?? ""] ?? option[2]}`;
        return VALUE_HEADINGS[key] ?? key;
    }
    MindmapPreview.locationLabel = locationLabel;
})(MindmapPreview || (MindmapPreview = {}));
// 描画のライブラリ（mdmark・marked・elkjs・mermaid）と差分のライブラリ（jsdiff）の読み込み・有無と呼び出し、選んだ範囲から箇所を求める処理。読めなかったときは名前を出し、代わりの読み込みはしない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 描画のライブラリの名前 → 読めたときに置かれるグローバルの名前 */
    MindmapPreview.LIBRARIES = {
        mdmark: "mdmark",
        marked: "marked",
        elkjs: "ELK",
        mermaid: "mermaid",
        jsdiff: "Diff",
    };
    /** 図の入れ物が原文を持つ属性の名前 */
    MindmapPreview.DIAGRAM_SOURCE_ATTR = "data-source";
    /** `mdmark.mount` の `config.features` に渡す、プレビューの画面と重なる機能と、コードの色付け（`syntax`。配信元から highlight.js を `integrity` なしで読む）のオフ（`code`・`html`・`diagrams` は既定のまま） */
    MindmapPreview.MDMARK_FEATURES = {
        glossary: false,
        backlinks: false,
        comments: false,
        print: false,
        anchors: false,
        sections: false,
        table: false,
        toc: false,
        views: false,
        syntax: false,
    };
    /** mdmark の操作できる部品の今の値をコピーするボタン（`.mdmark-param-copy`）に出す文言 */
    MindmapPreview.MDMARK_PARAM_COPY_LABEL = "今の値をコピー";
    /** 配る書き出しが mdmark の JavaScript を中身に持つ要素の id */
    MindmapPreview.MDMARK_EMBEDDED_ID = "mindmap-mdmark";
    /** 雛形の import map（`script[type="importmap"]`）の `integrity` のただ 1 つのキー（mdmark の JavaScript の URL）と、その `integrity` を返す。import map が無いか読めないか、キーが 1 つでないときは null */
    function mdmarkImportMapEntry() {
        const script = document.querySelector('script[type="importmap"]');
        if (script === null)
            return null;
        try {
            const entries = Object.entries(JSON.parse(script.textContent ?? "").integrity ?? {});
            const [only] = entries;
            return entries.length === 1 && only !== undefined ? { url: only[0], integrity: only[1] } : null;
        }
        catch {
            // JSON として読めない import map は、読めなかったものとして扱う
            return null;
        }
    }
    MindmapPreview.mdmarkImportMapEntry = mdmarkImportMapEntry;
    /** mdmark の JavaScript を読み、読めたらグローバルの `mdmark` に置く。配る書き出しは中身を持つ要素（`#mindmap-mdmark`）を Blob の URL にして読み、サーバーの配信は import map の URL をブラウザが `integrity` で確かめて読む。読めなくても拒否せず解決する（読めなかったことは `missingLibraries` が伝える） */
    async function loadMdmark() {
        const embedded = document.getElementById(MindmapPreview.MDMARK_EMBEDDED_ID);
        try {
            let loaded;
            if (embedded !== null) {
                const url = URL.createObjectURL(new Blob([embedded.textContent ?? ""], { type: "text/javascript" }));
                try {
                    loaded = (await import(url));
                }
                finally {
                    URL.revokeObjectURL(url);
                }
            }
            else {
                const entry = mdmarkImportMapEntry();
                // import map が無いか読めない
                if (entry === null)
                    return;
                loaded = (await import(entry.url));
            }
            Reflect.set(window, MindmapPreview.LIBRARIES.mdmark, loaded);
        }
        catch {
            // `import()` の拒否（取れない・`integrity` が合わない）は、グローバルを置かずに解決する
        }
    }
    MindmapPreview.loadMdmark = loadMdmark;
    /** 渡したライブラリのうち、グローバルが無いものの名前を返す（渡した順） */
    function missingLibraries(names) {
        return names.filter((name) => Reflect.get(window, MindmapPreview.LIBRARIES[name]) === undefined);
    }
    MindmapPreview.missingLibraries = missingLibraries;
    /** 読めなかったライブラリの名前を出す知らせの要素を返す */
    function libraryNotice({ names, what }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "lib-error", role: "alert" },
            children: [
                MindmapPreview.h({ tag: "span", children: [`${what}を表示できません。読み込めなかったライブラリ: ${names.join("・")}`] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["通信を確認して、ページを再読み込みしてください。"] }),
            ],
        });
    }
    MindmapPreview.libraryNotice = libraryNotice;
    // ─── 本文の行の印 ───
    /** 本文のブロックの要素が持つ、元の Markdown の先頭の行（1 始まり）の属性 */
    MindmapPreview.LINE_ATTR = "data-line-start";
    /** Markdown の中の `html` のコードブロックを置き換えた、HTML の本文の枠の入れ物の class */
    MindmapPreview.HTML_BLOCK_CLASS = "html-block";
    /** 本文の表を包む、表の中だけで横に送る入れ物の class */
    MindmapPreview.TABLE_WRAP_CLASS = "md-table-wrap";
    /** HTML の本文の開きタグが持つ、中身が始まる元の HTML の行（1 始まり）の属性。サーバーが足す */
    MindmapPreview.HTML_LINE_ATTR = "data-line";
    /** 開きタグの直後の改行を、解析のときに取り除く要素 */
    const LEADING_NEWLINE_TAGS = ["PRE", "TEXTAREA", "LISTING"];
    /** 項目の値を描いた要素が持つ、項目のキーのパスの属性 */
    MindmapPreview.VALUE_KEY_ATTR = "data-key";
    /** mdmark が描いたブロックが持つ、元の Markdown のブロックの開始の行（0 始まり）の属性 */
    const SOURCE_LINE_ATTR = "data-source-line";
    /** mdmark が描いた、埋め込んだ HTML の範囲の要素の class */
    MindmapPreview.EMBEDDED_HTML_CLASS = "mdmark-html";
    /** 埋め込んだ HTML の範囲の要素が持つ、範囲の始まりの印 `<!-- html -->` の行（1 始まり）の属性 */
    MindmapPreview.HTML_OPEN_ATTR = "data-html-open";
    /** 埋め込んだ HTML の範囲の要素が持つ、範囲の終わりの印 `<!-- /html -->` の行（1 始まり）の属性 */
    MindmapPreview.HTML_CLOSE_ATTR = "data-html-close";
    /** 行全体が `<!-- html -->` の範囲の始まりの印（間の空白を許す） */
    const EMBEDDED_HTML_OPEN_LINE = /^\s*<!--\s*html\s*-->\s*$/;
    /** 行全体が `<!-- /html -->` の範囲の終わりの印（間の空白を許す） */
    const EMBEDDED_HTML_CLOSE_LINE = /^\s*<!--\s*\/html\s*-->\s*$/;
    /** 元の行の印（`data-line-start`）を付けるブロックの要素 */
    const LINE_MARK_TAGS = new Set(["H1", "H2", "H3", "H4", "H5", "H6", "P", "LI", "TR", "PRE"]);
    /** 開始の行の行頭の空白・引用の `>`・リストのマーカーを除いた先が、フェンス（```` ``` ```` か `~~~`）で始まる行 */
    const FENCE_LINE = /^(?:[ \t]*(?:>|[-*+]|\d+[.)])[ \t]?)*[ \t]*(```|~~~)/;
    /** 改行の数を返す */
    function countNewlines(text) {
        return text.split("\n").length - 1;
    }
    /** mdmark が付けた `data-source-line`（0 始まり）を元の行の印 `data-line-start`（1 始まり。フェンスのコードは中身の最初の行）に読み替え、全ての `data-source-line` を外す。段落を持つリストの項目は中の段落が印を持つので付けない */
    function convertSourceLines({ root, source }) {
        const lines = source.split("\n");
        for (const element of root.querySelectorAll(`[${SOURCE_LINE_ATTR}]`)) {
            const start = Number(element.getAttribute(SOURCE_LINE_ATTR));
            element.removeAttribute(SOURCE_LINE_ATTR);
            if (!LINE_MARK_TAGS.has(element.tagName))
                continue;
            if (element.tagName === "LI" && element.querySelector(":scope > p") !== null)
                continue;
            const fence = element.tagName === "PRE" && FENCE_LINE.test(lines[start] ?? "") ? 1 : 0;
            element.setAttribute(MindmapPreview.LINE_ATTR, String(start + 1 + fence));
        }
    }
    /** 要素の中に、機能を止めた mdmark で Markdown を描く（描き直しは要素ごと作り直すので、返る `update`・`destroy` は使わない） */
    function mountMarkdown({ root, markdown }) {
        mdmark.mount(root, { markdown, config: { features: MindmapPreview.MDMARK_FEATURES } });
        trimBreakNewlines(root);
        relabelParamCopy(root);
    }
    /** 引用の `>` を除いた先が `[!{英字}]` だけの Alert の種類の行（後ろに `-` を許す）。mdmark はこの行の後ろが強制改行だと Alert にしない */
    const ALERT_MARKER_LINE = /^[ \t]*(?:>[ \t]*)+\[![A-Za-z]+\]-?[ \t]*$/;
    /** `br` の直後の改行の文字を取り除く（mdmark は強制改行を `<br>` と改行の文字で描くので、改行の数え方が `br` の分と二重になる） */
    function trimBreakNewlines(root) {
        for (const br of root.querySelectorAll("br")) {
            const next = br.nextSibling;
            if (next?.nodeType !== Node.TEXT_NODE || !(next.textContent ?? "").startsWith("\n"))
                continue;
            next.textContent = (next.textContent ?? "").slice(1);
            if (next.textContent === "")
                next.remove();
        }
    }
    /** フェンスと字下げのコードの外で、次の行が空行でない行の末尾に空白 2 つを足した Markdown を返す（mdmark は `breaks` を持たないため、段落の中の 1 つの改行を `br` にする。Alert の種類の行は足さない）。行の数は変えない */
    function withHardBreaks(source) {
        const lines = source.split("\n");
        // 開いているフェンスの記号と、閉じるのに要る数
        let fence = null;
        // 直前の行が空行か字下げのコードの行（字下げのコードを始められる）
        let codeMayStart = true;
        return lines
            .map((line, index) => {
            const stripped = line.replace(/^(?:[ \t]*(?:>|[-*+]|\d+[.)])[ \t]?)*[ \t]*/, "");
            // フェンスの中と、フェンスの行（開く行・閉じる行）はそのまま残す
            if (fence !== null) {
                if (new RegExp(`^${fence.symbol}{${fence.count},}[ \\t]*$`).test(stripped))
                    fence = null;
                return line;
            }
            const opened = /^(`{3,}|~{3,})/.exec(stripped);
            if (opened !== null) {
                fence = { symbol: opened[1][0], count: opened[1].length };
                return line;
            }
            // 字下げのコードの行はそのまま残す
            const indented = codeMayStart && /^( {4}|\t)/.test(line);
            codeMayStart = line.trim() === "" || indented;
            if (indented || line.trim() === "")
                return line;
            // Alert の種類の行はそのまま残す
            if (ALERT_MARKER_LINE.test(line))
                return line;
            // 次の行があり、空白だけの行でなければ強制改行にする
            const next = lines[index + 1];
            return next !== undefined && next.trim() !== "" ? `${line}  ` : line;
        })
            .join("\n");
    }
    MindmapPreview.withHardBreaks = withHardBreaks;
    /** Markdown の本文の中の `<!-- html -->` 〜 `<!-- /html -->` の範囲を、本文の中の並びの順に印の行（1 始まり）で返す。フェンスの中の印は範囲にせず、閉じていない始まりは範囲にしない */
    function embeddedHtmlRanges(source) {
        const ranges = [];
        // 開いているフェンスの記号と、閉じるのに要る数
        let fence = null;
        // 開いている範囲の始まりの行
        let open = null;
        source.split("\n").forEach((line, index) => {
            const stripped = line.replace(/^(?:[ \t]*(?:>|[-*+]|\d+[.)])[ \t]?)*[ \t]*/, "");
            // フェンスの中は印を探さない。閉じる行でフェンスを終える
            if (fence !== null) {
                if (new RegExp(`^${fence.symbol}{${fence.count},}[ \\t]*$`).test(stripped))
                    fence = null;
                return;
            }
            const opened = /^(`{3,}|~{3,})/.exec(stripped);
            if (opened !== null) {
                fence = { symbol: opened[1][0], count: opened[1].length };
                return;
            }
            if (open === null && EMBEDDED_HTML_OPEN_LINE.test(line))
                open = index + 1;
            else if (open !== null && EMBEDDED_HTML_CLOSE_LINE.test(line)) {
                ranges.push({ open, close: index + 1 });
                open = null;
            }
        });
        return ranges;
    }
    MindmapPreview.embeddedHtmlRanges = embeddedHtmlRanges;
    /** 見張りを付け済みの本文（同じ本文に 2 回当てても見張りを重ねない） */
    const relabeledRoots = new WeakSet();
    /** 今の値をコピーするボタンの文言を `MDMARK_PARAM_COPY_LABEL` に替える。アイコンの要素は残し、文字のノードだけを置き換える（文言が同じボタンは触らない） */
    function relabelButton(button) {
        const texts = [...button.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE);
        if (texts.length === 1 && texts[0].textContent === MindmapPreview.MDMARK_PARAM_COPY_LABEL)
            return;
        for (const text of texts)
            text.remove();
        button.append(document.createTextNode(MindmapPreview.MDMARK_PARAM_COPY_LABEL));
    }
    /** mdmark が描いた部品の今の値をコピーするボタンの文言を替える。部品が描き直したボタンにも当てるため、本文の子孫の追加を見張る */
    function relabelParamCopy(root) {
        for (const button of root.querySelectorAll(".mdmark-param-copy"))
            relabelButton(button);
        if (relabeledRoots.has(root))
            return;
        relabeledRoots.add(root);
        new MutationObserver((records) => {
            for (const record of records) {
                for (const added of record.addedNodes) {
                    if (!(added instanceof Element))
                        continue;
                    if (added.matches(".mdmark-param-copy"))
                        relabelButton(added);
                    for (const button of added.querySelectorAll(".mdmark-param-copy"))
                        relabelButton(button);
                }
            }
        }).observe(root, { childList: true, subtree: true });
    }
    MindmapPreview.relabelParamCopy = relabelParamCopy;
    /** 印を持つブロックの先頭から、選択の端までにある改行（文の \n と br）の数を返す */
    function linesBefore({ block, node, offset }) {
        // 表の行は 1 行で、セルの間の空白の改行は数えない
        if (block.tagName === "TR")
            return 0;
        const range = document.createRange();
        range.setStart(block, 0);
        range.setEnd(node, offset);
        const fragment = range.cloneContents();
        return countNewlines(fragment.textContent ?? "") + fragment.querySelectorAll("br").length;
    }
    /** 選択の端から、本文の中で印を持つ最も近いブロックを返す（本文の外なら null） */
    function lineBlock(node) {
        const element = node instanceof Element ? node : node.parentElement;
        const block = element?.closest(`[${MindmapPreview.LINE_ATTR}]`) ?? null;
        return block?.closest(".md") ? block : null;
    }
    /** 選択の端から、本文の中で行の印（`data-html-open`）を持つ埋め込んだ HTML の範囲の要素を返す（範囲の中でなければ null） */
    function embeddedHtmlElement(node) {
        const element = node instanceof Element ? node : node.parentElement;
        const range = element?.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}[${MindmapPreview.HTML_OPEN_ATTR}]`) ?? null;
        return range?.closest(".md") ? range : null;
    }
    /** 選んだ範囲を、本文なら元の Markdown の行の範囲、値ならキーのパスの箇所にする。本文と値の外・空の選択は null */
    function selectionLocation(range) {
        if (range.collapsed)
            return null;
        const text = range.toString().trim();
        // 文が空白だけ
        if (text === "")
            return null;
        // 始点と終点が同じ値の中: 値の箇所
        const startKey = keyElement(range.startContainer);
        if (startKey !== null && startKey === keyElement(range.endContainer)) {
            return { kind: "value", key: startKey.getAttribute(MindmapPreview.VALUE_KEY_ATTR) ?? "", text };
        }
        const startRange = embeddedHtmlElement(range.startContainer);
        const endRange = embeddedHtmlElement(range.endContainer);
        const startBlock = startRange === null ? lineBlock(range.startContainer) : null;
        const endBlock = endRange === null ? lineBlock(range.endContainer) : null;
        // 本文の外（端が埋め込んだ HTML の範囲の中なら、範囲の印の行がある）
        if ((startRange === null && !startBlock) || (endRange === null && !endBlock))
            return null;
        // 範囲の中の始点は範囲の始まりの印の行、終点は終わりの印の行にする。それ以外は、印を持つブロックの行に端までの改行の数を足す
        const start = startRange !== null
            ? Number(startRange.getAttribute(MindmapPreview.HTML_OPEN_ATTR))
            : Number(startBlock.getAttribute(MindmapPreview.LINE_ATTR)) + linesBefore({ block: startBlock, node: range.startContainer, offset: range.startOffset });
        const end = endRange !== null
            ? Number(endRange.getAttribute(MindmapPreview.HTML_CLOSE_ATTR))
            : Number(endBlock.getAttribute(MindmapPreview.LINE_ATTR)) + linesBefore({ block: endBlock, node: range.endContainer, offset: range.endOffset });
        return { kind: "body", start, end, text };
    }
    MindmapPreview.selectionLocation = selectionLocation;
    /** 文書の順で端より前にある、行の印（`data-line`）を持つ要素のうち最も後のものを返す（無ければ null） */
    function htmlLineElement({ doc, node, offset }) {
        const probe = doc.createRange();
        probe.setStart(node, offset);
        probe.collapse(true);
        let found = null;
        for (const element of doc.querySelectorAll(`[${MindmapPreview.HTML_LINE_ATTR}]`)) {
            // 要素の先頭が端より前（端と同じ位置を含む）にあるものだけが候補
            if (probe.comparePoint(element, 0) > 0)
                break;
            found = element;
        }
        return found;
    }
    /** 行の印を持つ要素の開きタグの直後から端までにある改行（文とコメントの中の改行。`br` は数えない）の数を返す */
    function htmlLinesBefore({ element, node, offset }) {
        const range = element.ownerDocument.createRange();
        range.setStart(element, 0);
        range.setEnd(node, offset);
        const fragment = range.cloneContents();
        let count = countNewlines(fragment.textContent ?? "");
        // コメントは textContent に入らないので、中の改行を足す
        const walker = element.ownerDocument.createTreeWalker(fragment, NodeFilter.SHOW_COMMENT);
        while (walker.nextNode())
            count += countNewlines(walker.currentNode.data);
        return count;
    }
    /** `pre`・`textarea`・`listing` の開きタグの直後に改行があるとき 1（その改行は解析のときに取り除かれる）を返す */
    function leadingNewlineBefore({ element, source }) {
        if (!LEADING_NEWLINE_TAGS.includes(element.tagName))
            return 0;
        const line = source.split("\n")[Number(element.getAttribute(MindmapPreview.HTML_LINE_ATTR)) - 1] ?? "";
        return /<(?:pre|textarea|listing)\b[^>]*>\r?$/i.test(line) ? 1 : 0;
    }
    /** HTML の本文の枠の中で選んだ範囲を、元の HTML の行の範囲の箇所にする。空の選択・端より前に行の印を持つ要素が無い選択は null */
    function htmlSelectionLocation(range, source) {
        if (range.collapsed)
            return null;
        const text = range.toString().trim();
        // 文が空白だけ
        if (text === "")
            return null;
        const doc = range.startContainer.ownerDocument ?? range.startContainer;
        const startElement = htmlLineElement({ doc, node: range.startContainer, offset: range.startOffset });
        const endElement = htmlLineElement({ doc, node: range.endContainer, offset: range.endOffset });
        // 端より前に行の印を持つ要素が無い
        if (startElement === null || endElement === null)
            return null;
        const lineOfBoundary = (element, node, offset) => Number(element.getAttribute(MindmapPreview.HTML_LINE_ATTR)) +
            htmlLinesBefore({ element, node, offset }) +
            leadingNewlineBefore({ element, source });
        return {
            kind: "body",
            start: lineOfBoundary(startElement, range.startContainer, range.startOffset),
            end: lineOfBoundary(endElement, range.endContainer, range.endOffset),
            text,
        };
    }
    MindmapPreview.htmlSelectionLocation = htmlSelectionLocation;
    /** HTML の本文の枠の中のリンクのうち、新しいタブで開く URL のスキーム（`URL` の `protocol` の形） */
    MindmapPreview.HTML_LINK_OPEN_SCHEMES = ["http:", "https:", "mailto:"];
    /** HTML の本文の枠の中のリンクの `href`（書かれたままの値）から、新しいタブで開く・本文の中の場所まで送る・何もしないのどれかを決める */
    function htmlLinkAction(href) {
        const value = href.trim();
        // `#` で始まる: 本文の中の場所を指す。`#` の後ろを戻した id を送り先にする
        if (value.startsWith("#")) {
            const encoded = value.slice(1);
            let id = encoded;
            try {
                id = decodeURIComponent(encoded);
            }
            catch {
                // 戻せない（`%` の後ろが不正）ときは、書かれたままを id にする
            }
            return id === "" ? { kind: "none" } : { kind: "anchor", id };
        }
        // それだけで絶対の URL として読めない（相対の URL）
        if (!URL.canParse(value))
            return { kind: "none" };
        const url = new URL(value);
        // 開くスキーム以外（`javascript:`・`data:`・`file:` ほか）
        if (!MindmapPreview.HTML_LINK_OPEN_SCHEMES.includes(url.protocol))
            return { kind: "none" };
        return { kind: "open", url: url.href };
    }
    MindmapPreview.htmlLinkAction = htmlLinkAction;
    /** 選択の端から、値のキーのパスを持つ最も近い要素を返す（無ければ null） */
    function keyElement(node) {
        const element = node instanceof Element ? node : node.parentElement;
        return element?.closest(`[${MindmapPreview.VALUE_KEY_ATTR}]`) ?? null;
    }
    /** 項目の文字列の値の Markdown を、段落の中の改行も改行にして mdmark で描いた要素にする。mdmark が読めないときは、改行を残した文字のままの要素にする（知らせは本文の描画が出す） */
    function renderValue(source) {
        if (missingLibraries(["mdmark"]).length > 0) {
            return MindmapPreview.h({ tag: "span", attrs: { class: "md-value-raw" }, children: [source] });
        }
        const root = MindmapPreview.h({ tag: "div", attrs: { class: "md md-value" } });
        // mdmark は描くときに無害化する（記録は利用者のもの）。行の印は付けず、mermaid のコードブロックも図にしない
        mountMarkdown({ root, markdown: withHardBreaks(source) });
        for (const element of root.querySelectorAll(`[${SOURCE_LINE_ATTR}]`))
            element.removeAttribute(SOURCE_LINE_ATTR);
        return root;
    }
    MindmapPreview.renderValue = renderValue;
    /** 本文の Markdown を mdmark で描いた要素にする（mdmark が描くときに無害化する）。ブロックに元の行の印を付け、mermaid のコードブロックは図の入れ物に、`html` のコードブロックは HTML の本文の枠の入れ物に置き換え、表は横に送れる要素で包む */
    function renderMarkdown(source) {
        const root = MindmapPreview.h({ tag: "div", attrs: { class: "md" } });
        const missing = missingLibraries(["mdmark"]);
        const hasDiagram = source.includes("```mermaid");
        // mdmark が読めていない: 知らせと原文を出す
        if (missing.length > 0) {
            const names = [...missing];
            if (hasDiagram && missingLibraries(["mermaid"]).length > 0)
                names.push("mermaid");
            root.append(libraryNotice({ names, what: "本文" }), MindmapPreview.h({ tag: "pre", attrs: { class: "md-raw" }, children: [source] }));
            return root;
        }
        // mdmark は描くときに無害化する（記録は利用者のもの）
        mountMarkdown({ root, markdown: source });
        convertSourceLines({ root, source });
        // 埋め込んだ HTML の範囲は `data-source-line` を持たないので、本文の中の n 番目の範囲に、n 番目の範囲の印の行を持たせる（範囲の中の要素には行の印を付けない）
        const ranges = embeddedHtmlRanges(source);
        root.querySelectorAll(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`).forEach((element, order) => {
            const range = ranges[order];
            if (range === undefined)
                return;
            element.setAttribute(MindmapPreview.HTML_OPEN_ATTR, String(range.open));
            element.setAttribute(MindmapPreview.HTML_CLOSE_ATTR, String(range.close));
        });
        // mermaid のコードブロックを、原文を持つ図の入れ物（拡大・Raw・コピーの道具つき）に置き換える（埋め込んだ HTML の範囲の外だけ）
        for (const code of root.querySelectorAll("code.language-mermaid")) {
            if (code.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`) !== null)
                continue;
            const original = code.textContent ?? "";
            const figure = MindmapPreview.h({
                tag: "figure",
                attrs: { class: "diagram" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "dg-tools" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "icon-btn", type: "button", "data-act": "diagram-zoom", "aria-label": "図を拡大表示", title: "拡大表示" },
                                children: [MindmapPreview.icon("expand")],
                            }),
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "btn ghost", type: "button", "data-act": "diagram-raw", "aria-pressed": "false" },
                                children: ["Raw"],
                            }),
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "icon-btn", type: "button", "data-act": "diagram-copy", "aria-label": "原文をコピー", title: "コピー" },
                                children: [MindmapPreview.icon("copy")],
                            }),
                        ],
                    }),
                    MindmapPreview.h({ tag: "div", attrs: { class: "mermaid", [MindmapPreview.DIAGRAM_SOURCE_ATTR]: original } }),
                    MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw", hidden: true }, children: [original] }),
                ],
            });
            (code.closest("pre") ?? code).replaceWith(figure);
        }
        // html のコードブロックを、原文と元の行の印を持つ HTML の本文の枠の入れ物に置き換える（枠を描くのは詳細の画面。埋め込んだ HTML の範囲の外だけ）
        for (const code of root.querySelectorAll("code.language-html")) {
            if (code.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`) !== null)
                continue;
            const pre = code.closest("pre") ?? code;
            const block = MindmapPreview.h({
                tag: "div",
                attrs: { class: MindmapPreview.HTML_BLOCK_CLASS, [MindmapPreview.DIAGRAM_SOURCE_ATTR]: code.textContent ?? "" },
            });
            const line = pre.getAttribute(MindmapPreview.LINE_ATTR);
            if (line !== null)
                block.setAttribute(MindmapPreview.LINE_ATTR, line);
            pre.replaceWith(block);
        }
        // 表を、表の中だけで横に送れる入れ物で包む（行の印は表の行に残し、入れ物には付けない）。埋め込んだ HTML の範囲の中の表は、書いた HTML のまま包まない
        for (const table of root.querySelectorAll("table")) {
            if (table.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`) !== null)
                continue;
            const wrap = MindmapPreview.h({
                tag: "div",
                attrs: { class: MindmapPreview.TABLE_WRAP_CLASS, tabindex: "0", role: "group", "aria-label": "本文の表" },
            });
            table.replaceWith(wrap);
            wrap.append(table);
        }
        return root;
    }
    MindmapPreview.renderMarkdown = renderMarkdown;
    /** 見出しの文言から、見出しを指す名前を作る（前後の空白を除き、間の空白の並びを `-` 1 つにする。同じ名前の 2 つ目から `-1`・`-2` を続ける）。`seen` は同じ本文でこれまでに作った名前 → 出た回数で、呼ぶたびに書き換える */
    function headingSlug({ text, seen }) {
        const base = text.trim().replace(/\s+/g, "-");
        const count = seen.get(base) ?? 0;
        seen.set(base, count + 1);
        return count === 0 ? base : `${base}-${count}`;
    }
    MindmapPreview.headingSlug = headingSlug;
    /** 今のハッシュの `id`・`h` を替えた URL のハッシュ（キーボードとリンクのコピーで使うリンク先。押したときは使う側の移動に替える） */
    function hashWith({ id, heading }) {
        const params = new URLSearchParams(location.hash.replace(/^#/, ""));
        if (id !== undefined)
            params.set("id", id);
        if (heading === null)
            params.delete("h");
        else
            params.set("h", heading);
        return `#${params.toString()}`;
    }
    MindmapPreview.hashWith = hashWith;
    /** 描いた本文の見出しに、見出しを指す名前（`data-heading`）と右の # のリンクを付け、本文の中の `#見出し` のリンクをその見出しへの移動に、`#diff=` のリンクをまとまりの知らせにする。押したときは既定の動作を止め、見出しの名前を `onHeading` に、`diff` の値を `onChangeSet` に知らせる */
    function linkHeadings({ root, onHeading, onChangeSet, }) {
        // 本文の中の `[文言](#...)` のリンク（# のリンクを足す前の分）。`diff` の引数を持つものはまとまりのリンク、持たないものは見出しのリンクで、同じ名前の見出しがあるときだけ知らせ、無ければ何もしない
        const bodyLinks = [...root.querySelectorAll("a[href^='#']")];
        const seen = new Map();
        for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
            const text = heading.textContent ?? "";
            const slug = headingSlug({ text, seen });
            heading.dataset["heading"] = slug;
            heading.append(MindmapPreview.h({
                tag: "a",
                attrs: {
                    class: "h-link",
                    href: hashWith({ heading: slug }),
                    "aria-label": `見出し「${text.trim()}」へのリンク`,
                    onclick: (event) => {
                        event.preventDefault();
                        onHeading(slug);
                    },
                },
                children: [MindmapPreview.icon("hash")],
            }));
        }
        for (const link of bodyLinks) {
            link.addEventListener("click", (event) => {
                event.preventDefault();
                const raw = (link.getAttribute("href") ?? "").slice(1);
                // まとまりのリンク: 見出しとしては扱わない。空・`since`・`pending` は知らせない（記録にあるまとまりかは使う側が確かめる）
                const changeSet = new URLSearchParams(raw).get("diff");
                if (changeSet !== null) {
                    if (changeSet !== "" && changeSet !== "since" && changeSet !== "pending")
                        onChangeSet(changeSet);
                    return;
                }
                let decoded = raw;
                try {
                    decoded = decodeURIComponent(raw);
                }
                catch {
                    // 戻せない文字列は、そのまま見出しの名前として探す
                }
                const slug = headingSlug({ text: decoded, seen: new Map() });
                if (root.querySelector(`[data-heading="${CSS.escape(slug)}"]`) !== null)
                    onHeading(slug);
            });
        }
    }
    MindmapPreview.linkHeadings = linkHeadings;
    /** 英数字だけの語か（前後が英数字のときと、後ろが `-` と数字のとき（`API-2` の `API`）は印にしない） */
    const ALPHANUMERIC_WORD = /^[A-Za-z0-9]+$/;
    /** 本文の印に当てる項目の種類（一致した項目とツールチップの並びもこの順） */
    MindmapPreview.MARK_KINDS = ["terms", "docs", "research"];
    /** 印を当てない祖先（`pre`・インラインコード・図・リンク・ボタン・見出しの中。インラインコードは中身がちょうど語のときだけ `code` ごと当てる） */
    const UNMARKED_ANCESTORS = "pre, code, figure, a, button, svg, .mermaid, h1, h2, h3, h4, h5, h6";
    /** 項目の ID（英大文字 - 数字。前後が英数字のものは当てない） */
    const ITEM_ID_PATTERN = /(?<![A-Za-z0-9-])[A-Z]+-[0-9]+(?![0-9])/g;
    /** 本文の中の、用語の印に当てられる文字のノード（祖先が `UNMARKED_ANCESTORS` でなく、本文のブロック `block` 自身の行を持つもの）を文書の順に返す */
    function markableTextNodes(block) {
        const own = block.classList.contains(MindmapPreview.EMBEDDED_HTML_CLASS);
        const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => {
                const parent = node.parentElement;
                if (parent === null || parent.closest(UNMARKED_ANCESTORS) !== null)
                    return NodeFilter.FILTER_REJECT;
                // 入れ子のブロック（リストの項目の中のリストの項目など）の文字は、そのブロックの行に任せる
                if (!own && parent.closest(`[${MindmapPreview.LINE_ATTR}]`) !== block)
                    return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            },
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        return nodes;
    }
    /** 描いた本文の文中（埋め込んだ HTML の範囲の中を含む）の、用語集の用語のタイトルと別名、資料・調査のエイリアスを印に、記録にある項目の ID をリンクにする。語の一致と一致の前の正規化は mdmark の `collectMatches` に任せる。`pre`・図・リンク・見出しの中は飛ばし、インラインコードは中身がちょうど語か ID のときだけ当てる。押したときは既定の動作を止め、ID のリンクと用語 1 件だけに一致した印はその項目の ID を `onOpen` に知らせる（用語 2 件以上か、資料・調査にも一致した印は知らせず、ツールチップを残す使う側に任せる） */
    function linkBody({ root, index, selfId, onOpen, source, }) {
        // 語 → 一致した項目の ID（用語 → 資料 → 調査の順）。項目自身・取り下げた資料と調査・空の語は当てない
        const byWord = new Map();
        for (const kind of MindmapPreview.MARK_KINDS) {
            for (const item of index.data[kind]) {
                if (item.id === selfId || (kind !== "terms" && item.withdrawn === true))
                    continue;
                const words = kind === "terms" ? [item.title, ...(item.aliases ?? [])] : (item.aliases ?? []);
                // 同じ項目の同じ語（用語のタイトルと同じ別名を含む）は 1 つにまとめる
                for (const word of new Set(words.map((value) => value.trim()).filter((value) => value !== ""))) {
                    byWord.set(word, [...(byWord.get(word) ?? []), item.id]);
                }
            }
        }
        // 項目の印と、押したときの動き。用語 2 件以上か、資料・調査にも一致した印は、ツールチップの中のリンクで移る先を選ぶ
        const termMark = ({ text, ids }) => {
            const multi = ids.length > 1 || ids.some((id) => index.byId.get(id)?.kind !== "terms");
            return MindmapPreview.h({
                tag: "a",
                attrs: {
                    class: "term",
                    href: hashWith({ id: ids[0], heading: null }),
                    "data-id": ids[0],
                    "data-ids": ids.join(" "),
                    "aria-describedby": multi ? null : MindmapPreview.TERM_TIP_ID,
                    "aria-details": multi ? MindmapPreview.TERM_TIP_ID : null,
                    onclick: (event) => {
                        event.preventDefault();
                        if (!multi)
                            onOpen(ids[0]);
                    },
                },
                children: [text],
            });
        };
        const idMark = (id) => MindmapPreview.h({
            tag: "a",
            attrs: {
                class: "idref",
                href: hashWith({ id, heading: null }),
                "data-id": id,
                onclick: (event) => {
                    event.preventDefault();
                    onOpen(id);
                },
            },
            children: [id],
        });
        // 文字のノードの中の [開始, 終了) を、印に置き換える
        const replaceRanges = ({ node, ranges }) => {
            const text = node.data;
            const parts = [];
            let last = 0;
            for (const range of ranges) {
                parts.push(text.slice(last, range.start), range.mark);
                last = range.end;
            }
            parts.push(text.slice(last));
            node.replaceWith(...parts.filter((part) => part !== ""));
        };
        // 本文の語の位置を mdmark に求める。語ごとの用語（`meaning` が空だと照合しない）と、本文と語そのものの文書を渡す
        const words = [...byWord.keys()];
        if (words.length > 0) {
            const documents = { "self.md": source };
            const docs = [{ id: "self", path: "self.md", title: "self" }];
            words.forEach((word, order) => {
                documents[`w${order}.md`] = word;
                docs.push({ id: `w${order}`, path: `w${order}.md`, title: `w${order}` });
            });
            const terms = words.map((word, order) => ({ id: `W-${order}`, term: word, meaning: word }));
            const { byDocument } = mdmark.collectMatches({ index: { docs, terms }, documents });
            // 正規化の後に同じになる語は、まとまる先の用語に項目の ID を寄せる（用語 → 資料 → 調査の順）
            const merged = new Map();
            words.forEach((word, order) => {
                const hit = byDocument[`w${order}`]?.find((match) => match.line === 1 && match.start === 0 && match.end === word.length);
                if (hit === undefined)
                    return;
                merged.set(hit.id, [...(merged.get(hit.id) ?? []), ...(byWord.get(word) ?? [])]);
            });
            for (const [id, ids] of merged) {
                const unique = [...new Set(ids)];
                const rank = (itemId) => MindmapPreview.MARK_KINDS.indexOf((index.byId.get(itemId)?.kind ?? "terms"));
                merged.set(id, unique.sort((a, b) => rank(a) - rank(b)));
            }
            // 一致が属するブロック（埋め込んだ HTML の範囲の中の行は範囲、それ以外は行を含む最も後の `data-line-start` の要素）
            const lines = source.split("\n");
            const lineBlocks = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
            const rangeBlocks = [...root.querySelectorAll(`.${MindmapPreview.EMBEDDED_HTML_CLASS}[${MindmapPreview.HTML_OPEN_ATTR}]`)];
            const blockOfLine = (line) => {
                const range = rangeBlocks.find((element) => Number(element.getAttribute(MindmapPreview.HTML_OPEN_ATTR)) <= line && line <= Number(element.getAttribute(MindmapPreview.HTML_CLOSE_ATTR)));
                if (range !== undefined)
                    return range;
                let found = null;
                let foundLine = 0;
                for (const element of lineBlocks) {
                    const start = Number(element.getAttribute(MindmapPreview.LINE_ATTR));
                    if (start <= line && start >= foundLine) {
                        found = element;
                        foundLine = start;
                    }
                }
                return found;
            };
            // ブロックごとの、印に当てられる文字のノードと、前の一致の後ろの位置
            const cursors = new Map();
            const planned = new Map();
            const matches = [...(byDocument["self"] ?? [])].sort((a, b) => a.line - b.line || a.start - b.start);
            for (const match of matches) {
                const ids = merged.get(match.id);
                const block = blockOfLine(match.line);
                if (ids === undefined || block === null)
                    continue;
                const original = (lines[match.line - 1] ?? "").slice(match.start, match.end);
                let cursor = cursors.get(block);
                if (cursor === undefined) {
                    cursor = { nodes: markableTextNodes(block), at: 0, offset: 0 };
                    cursors.set(block, cursor);
                }
                // 前の一致の後ろから、元の語を探す。英数字だけの語は、前後が英数字のときと、後ろが `-` と数字のときは印にせず、次の出現を探す
                const alphanumeric = ALPHANUMERIC_WORD.test(original);
                search: for (let at = cursor.at; at < cursor.nodes.length; at += 1) {
                    const node = cursor.nodes[at];
                    for (let found = node.data.indexOf(original, at === cursor.at ? cursor.offset : 0); found !== -1; found = node.data.indexOf(original, found + 1)) {
                        const before = node.data[found - 1] ?? "";
                        const after = node.data.slice(found + original.length, found + original.length + 2);
                        if (alphanumeric && (/[A-Za-z0-9]/.test(before) || /^[A-Za-z0-9]/.test(after) || /^-[0-9]/.test(after)))
                            continue;
                        cursor.at = at;
                        cursor.offset = found + original.length;
                        const ranges = planned.get(node) ?? [];
                        ranges.push({ start: found, end: found + original.length, mark: termMark({ text: original, ids }) });
                        planned.set(node, ranges);
                        break search;
                    }
                }
            }
            for (const [node, ranges] of planned)
                replaceRanges({ node, ranges });
        }
        // インラインコードは、中身が前後の空白を除いてちょうど語のときだけ当てる（パスや識別子の一部には付けない）
        for (const code of root.querySelectorAll("code")) {
            if (code.closest("pre, figure, a, button, h1, h2, h3, h4, h5, h6") !== null)
                continue;
            const only = code.childNodes.length === 1 && code.firstChild?.nodeType === Node.TEXT_NODE ? code.firstChild : null;
            const ids = only === null ? undefined : byWord.get(only.data.trim());
            if (only === null || ids === undefined)
                continue;
            only.replaceWith(termMark({ text: only.data.trim(), ids }));
        }
        // 項目の ID は、記録にあるものだけをリンクにする（コードの中は、中身がちょうど ID のときだけ）
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => node.parentElement?.closest("pre, figure, a, button, svg, .mermaid, h1, h2, h3, h4, h5, h6") !== null
                ? NodeFilter.FILTER_REJECT
                : NodeFilter.FILTER_ACCEPT,
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        for (const node of nodes) {
            const text = node.data;
            const inCode = node.parentElement?.closest("code") !== null;
            const ranges = [];
            for (const match of text.matchAll(ITEM_ID_PATTERN)) {
                const id = match[0];
                // 記録に無い ID・項目自身の ID・コードの一部は、そのままにする
                if (!index.byId.has(id) || id === selfId || (inCode && text.trim() !== id))
                    continue;
                ranges.push({ start: match.index ?? 0, end: (match.index ?? 0) + id.length, mark: idMark(id) });
            }
            if (ranges.length > 0)
                replaceRanges({ node, ranges });
        }
    }
    MindmapPreview.linkBody = linkBody;
    /** 用語のツールチップの要素の id（用語の印の `aria-describedby` が指す） */
    MindmapPreview.TERM_TIP_ID = "term-tip";
    /** mermaid を初期化したときの、地の色（変わったら初期化し直す） */
    let initializedFor = null;
    /** 図の ID を作る連番 */
    let diagramCounter = 0;
    /** 直前の `renderDiagrams` で描いた・写した図（記法 → mermaid の出力と、その SVG の ID） */
    let lastDrawn = new Map();
    /** 図の ID を新しく振る */
    function nextDiagramId() {
        return `mindmap-diagram-${(diagramCounter += 1)}`;
    }
    /** 色の値をトークンから引く */
    function token(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }
    /** 初めて描くとき（と、テーマが変わったとき）に、トークンの色で mermaid を初期化する */
    function initializeMermaid() {
        // 初めて描くとき（と、テーマが変わったとき）に、トークンの色で初期化する
        const surface = token("--surface");
        if (initializedFor !== surface) {
            // 図の変数 → 色のトークン（トークンが無い文書では、mermaid の既定の色に任せる）
            const colorTokens = {
                background: "--surface",
                primaryColor: "--surface-2",
                primaryTextColor: "--text",
                primaryBorderColor: "--border",
                secondaryColor: "--surface-2",
                tertiaryColor: "--surface",
                lineColor: "--text-2",
                textColor: "--text",
                edgeLabelBackground: "--surface",
                clusterBkg: "--surface-2",
                clusterBorder: "--border",
            };
            const themeVariables = Object.fromEntries(Object.entries(colorTokens)
                .map(([variable, name]) => [variable, token(name)])
                .filter(([, color]) => color !== ""));
            mermaid.initialize({
                startOnLoad: false,
                securityLevel: "strict",
                theme: "base",
                fontFamily: "Noto Sans JP, sans-serif",
                themeVariables,
            });
            initializedFor = surface;
            // 古いテーマの色で描いた SVG は使い回さない
            lastDrawn = new Map();
        }
    }
    /** 記法を mermaid で SVG に描いて返す（画面には出さない）。mermaid が読めていないか、描けないときは null */
    async function renderDiagramSvg(source) {
        if (missingLibraries(["mermaid"]).length > 0)
            return null;
        initializeMermaid();
        const id = nextDiagramId();
        try {
            const { svg } = await mermaid.render(id, source);
            const holder = document.createElement("template");
            holder.innerHTML = svg;
            return holder.content.firstElementChild;
        }
        catch {
            // 描けなかった図: mermaid が body に残した作業用の要素を消す
            document.getElementById(`d${id}`)?.remove();
            document.getElementById(id)?.remove();
            return null;
        }
    }
    MindmapPreview.renderDiagramSvg = renderDiagramSvg;
    /** 要素の中の図の入れ物を mermaid で SVG に描く。描けない図は原文を残し、ほかの図は続ける */
    async function renderDiagrams(root) {
        const containers = [...root.querySelectorAll(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)];
        // mermaid が読めていない: 各入れ物に知らせと原文を入れる
        if (missingLibraries(["mermaid"]).length > 0) {
            for (const container of containers) {
                container.replaceChildren(libraryNotice({ names: ["mermaid"], what: "図" }), MindmapPreview.h({
                    tag: "pre",
                    attrs: { class: "dg-raw" },
                    children: [container.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? ""],
                }));
            }
            return;
        }
        initializeMermaid();
        // この呼び出しで描いた・写した図だけを、次の呼び出しのために覚える
        const drawn = new Map();
        for (const container of containers) {
            const source = container.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
            const id = nextDiagramId();
            try {
                // 直前に描いた同じ記法の図: 描き直さず、新しい ID に置き換えて写す（同じ図が文書に 2 つあっても ID と参照が重ならない）
                const reused = lastDrawn.get(source);
                const svg = reused === undefined
                    ? (await mermaid.render(id, source)).svg
                    : reused.svg.replace(new RegExp(`${reused.id}(?![0-9])`, "g"), id);
                container.innerHTML = svg;
                drawn.set(source, { svg, id });
            }
            catch {
                // 描けなかった図: mermaid が body に残した作業用の要素を消し、描けなかったことと原文を入れる
                document.getElementById(`d${id}`)?.remove();
                document.getElementById(id)?.remove();
                container.replaceChildren(MindmapPreview.h({ tag: "p", attrs: { class: "md-error" }, children: ["この図は表示できませんでした。原文を表示します。"] }), MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }));
            }
        }
        lastDrawn = drawn;
    }
    MindmapPreview.renderDiagrams = renderDiagrams;
})(MindmapPreview || (MindmapPreview = {}));
// 資料のエクスポート。mdmark の CSS と JavaScript・用語の索引・本文を 1 枚の HTML にまとめる組み立てと、埋め込んだ HTML を除いた Markdown の組み立てと、ブラウザへのダウンロード。
var MindmapPreview;
(function (MindmapPreview) {
    /** エクスポートした 1 枚の HTML の `mdmark.mount` に渡す機能のオフ。用語と資料・調査のエイリアスのツールチップ（`glossary`・`backlinks`）は mdmark が描き、通信するコードの色付けと、ファイルの外を指す機能を止める */
    MindmapPreview.MDMARK_EXPORT_FEATURES = {
        comments: false,
        print: false,
        views: false,
        syntax: false,
    };
    /** 配る書き出しが mdmark の CSS を中身に持つ `<style>` の id */
    MindmapPreview.MDMARK_CSS_EMBEDDED_ID = "mindmap-mdmark-css";
    /** URL を `integrity` で確かめて読み、本文を返す。`integrity` が合わないか、200 台でないときは投げる */
    async function fetchChecked({ url, integrity }) {
        const response = await fetch(url, { integrity, mode: "cors", credentials: "omit" });
        if (!response.ok)
            throw new Error(`${url} が ${response.status} を返しました`);
        return response.text();
    }
    /** 1 枚の HTML に入れる mdmark の CSS と JavaScript の中身を取る。配る書き出しは中身を持つ要素の文字を返し、サーバーの配信は CSS の `link` と import map の URL を `integrity` で確かめて読む。取れないときは拒否せず理由を返す */
    async function mdmarkAssets() {
        const embeddedJs = document.getElementById(MindmapPreview.MDMARK_EMBEDDED_ID);
        const embeddedCss = document.getElementById(MindmapPreview.MDMARK_CSS_EMBEDDED_ID);
        // 配る書き出し: 中身を持つ要素の文字
        if (embeddedJs !== null && embeddedCss !== null) {
            return { ok: true, css: embeddedCss.textContent ?? "", js: embeddedJs.textContent ?? "" };
        }
        // サーバーの配信: import map の JavaScript の URL と、同じ場所の CSS の `link`
        const entry = MindmapPreview.mdmarkImportMapEntry();
        if (entry === null)
            return { ok: false, reason: "mdmark の JavaScript の URL を import map から読めませんでした" };
        const cssUrl = entry.url.replace(/index\.js$/, "index.css");
        const link = [...document.querySelectorAll('link[rel="stylesheet"]')].find((element) => element.getAttribute("href") === cssUrl);
        if (link === undefined)
            return { ok: false, reason: "mdmark の CSS の link を読めませんでした" };
        try {
            const [css, js] = await Promise.all([fetchChecked({ url: cssUrl, integrity: link.integrity }), fetchChecked(entry)]);
            return { ok: true, css, js };
        }
        catch (error) {
            return { ok: false, reason: `mdmark の CSS と JavaScript を読み込めませんでした（${error instanceof Error ? error.message : String(error)}）` };
        }
    }
    MindmapPreview.mdmarkAssets = mdmarkAssets;
    /** `script` 要素を閉じるタグ。このファイル自身が雛形の `script` 要素の中に入るため、閉じるタグをそのまま書かず、つないで作る */
    const SCRIPT_CLOSE = `<${"/"}script>`;
    /** HTML の文字として出す文字列にする（`&`・`<`・`>`・`"` を文字参照にする） */
    function escapeHtml(text) {
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
    /** エクスポートした HTML が起動のときに流す JavaScript。mdmark の中身から Blob の URL を作って `import()` し、本文を描き、今の値をコピーするボタンの文言を替える（`relabelParamCopy` と同じ置き換え） */
    const DOC_BOOT_SCRIPT = [
        "(async () => {",
        '  const data = JSON.parse(document.getElementById("doc-data").textContent);',
        '  const url = URL.createObjectURL(new Blob([document.getElementById("doc-mdmark").textContent], { type: "text/javascript" }));',
        "  let library;",
        "  try {",
        "    library = await import(url);",
        "  } finally {",
        "    URL.revokeObjectURL(url);",
        "  }",
        '  const root = document.getElementById("doc");',
        "  library.mount(root, { markdown: data.source, config: { features: data.features }, index: data.index });",
        "  const relabel = (button) => {",
        "    const texts = [...button.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE);",
        "    if (texts.length === 1 && texts[0].textContent === data.copyLabel) return;",
        "    texts.forEach((node) => node.remove());",
        "    button.append(document.createTextNode(data.copyLabel));",
        "  };",
        '  root.querySelectorAll(".mdmark-param-copy").forEach(relabel);',
        "  new MutationObserver((records) => {",
        "    for (const record of records) {",
        "      for (const added of record.addedNodes) {",
        "        if (added.nodeType !== Node.ELEMENT_NODE) continue;",
        '        if (added.matches(".mdmark-param-copy")) relabel(added);',
        '        added.querySelectorAll(".mdmark-param-copy").forEach(relabel);',
        "      }",
        "    }",
        "  }).observe(root, { childList: true, subtree: true });",
        "})();",
    ].join("\n");
    /** エクスポートした HTML の、本文を置く枠の幅と余白 */
    const DOC_PAGE_STYLE = "body{margin:0}.doc-page{max-width:60rem;margin:0 auto;padding:24px 16px}.doc-title{margin:0 0 16px}";
    /** 資料 1 件の本文を、mdmark の CSS と JavaScript を中に持ち、ネットにつながらなくても開ける 1 枚の HTML にする。`item` 自身と取り下げた資料・調査は、ツールチップの索引に入れない。JavaScript が `script` 要素を閉じるタグを含むときは組み立てずに投げる */
    function buildDocHtml({ item, source, index, assets, }) {
        if (/<\/script/i.test(assets.js))
            throw new Error("mdmark の JavaScript が script 要素を閉じるタグを含むため、1 枚の HTML に入れられません");
        if (/<\/style/i.test(assets.css))
            throw new Error("mdmark の CSS が </style を含むため、1 枚の HTML に入れられません");
        // mdmark に渡す索引。用語集の用語と、item 自身と取り下げたものを除いた資料・調査
        const documents = [...index.data.docs, ...index.data.research]
            .filter((entry) => entry.id !== item.id && entry.withdrawn !== true)
            .map((entry) => ({
            id: entry.id,
            path: `${entry.id}.md`,
            title: entry.title,
            ...(entry.aliases === undefined ? {} : { aliases: entry.aliases }),
            ...(entry.description === undefined ? {} : { description: entry.description }),
        }));
        const terms = index.data.terms.map((term) => ({
            id: term.id,
            term: term.title,
            meaning: term.meaning ?? "",
            ...(term.aliases === undefined ? {} : { aliases: term.aliases }),
        }));
        // 本文・索引・文言を 1 つの JSON にする。`<` は HTML を壊さないよう、エスケープした形で入れる
        const data = JSON.stringify({
            source,
            index: { docs: documents, terms },
            features: MindmapPreview.MDMARK_EXPORT_FEATURES,
            copyLabel: MindmapPreview.MDMARK_PARAM_COPY_LABEL,
        }).replace(/</g, "\\u003c");
        const title = escapeHtml(item.title);
        return [
            "<!doctype html>",
            '<html lang="ja">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            `<title>${title}</title>`,
            `<style>${assets.css}</style>`,
            `<style>${DOC_PAGE_STYLE}</style>`,
            "</head>",
            "<body>",
            '<main class="doc-page">',
            `<h1 class="doc-title">${title}</h1>`,
            '<div id="doc"></div>',
            "</main>",
            `<script type="application/json" id="doc-data">${data}${SCRIPT_CLOSE}`,
            `<script type="text/plain" id="doc-mdmark">${assets.js}${SCRIPT_CLOSE}`,
            `<script>${DOC_BOOT_SCRIPT}${SCRIPT_CLOSE}`,
            "</body>",
            "</html>",
            "",
        ].join("\n");
    }
    MindmapPreview.buildDocHtml = buildDocHtml;
    /** 本文から `<!-- html -->` 〜 `<!-- /html -->` の範囲を印の行ごと除き、空行が 3 つ以上続くところを 2 つにまとめた Markdown を返す */
    function stripEmbeddedHtml(source) {
        const removed = new Set();
        for (const { open, close } of MindmapPreview.embeddedHtmlRanges(source)) {
            for (let line = open; line <= close; line += 1)
                removed.add(line);
        }
        return source
            .split("\n")
            .filter((_line, position) => !removed.has(position + 1))
            .join("\n")
            .replace(/\n{4,}/g, "\n\n\n");
    }
    MindmapPreview.stripEmbeddedHtml = stripEmbeddedHtml;
    /** 文字をファイルとして端末に保存させる。`Blob` の URL を `download` を持つ `a` で開き、URL を解放する */
    function downloadText({ name, text, type }) {
        const url = URL.createObjectURL(new Blob([text], { type: `${type};charset=utf-8` }));
        const anchor = MindmapPreview.h({ tag: "a", attrs: { href: url, download: name } });
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
    }
    MindmapPreview.downloadText = downloadText;
})(MindmapPreview || (MindmapPreview = {}));
// 差分の表示の計算。変更履歴で選んだ時点から印を付ける項目を決め、項目の `history` から前の版を組み立て、本文・記法の行と図の要素を比べる。DOM は描かず、描くのは画面が持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** `Diff.diffLines` に渡す `timeout`（ミリ秒）。切り替えの 200ms のうち、図の描画に使った残りを本文 1 つの差分に充てる */
    MindmapPreview.LINE_DIFF_TIMEOUT_MS = 40;
    /** 変えた行の対で、同じ部分の文字数を 2 つのうち短い方の文字数で割った値がこれに満たないとき、語の面を付けない（ほとんど書き換えた行は、語の面が行のほぼ全体に付いて行の面と見分けられない） */
    MindmapPreview.WORD_PAIR_MIN_SAME_RATIO = 0.5;
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
            // 日時は比べず、開いた時点の通し番号より大きいまとまりを範囲にする
            const inRange = sets.filter((set) => set.until_seq > since.seq);
            const oldest = inRange.at(-1);
            // 範囲で一番古いまとまりの 1 つ前の `until_seq` から。範囲にまとまりが無ければ、先頭のまとまりの `until_seq` から
            const fromSeq = oldest === undefined ? latestSeq : (sets[sets.indexOf(oldest) + 1]?.until_seq ?? 0);
            return buildPoint({
                sel,
                name: SINCE_NAME,
                sub: `${MindmapPreview.formatJst(since.at)} より後`,
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
    /** 本文を、marked の最上位の token（空行の token を除く）ごとの塊に分ける。塊の変えた行は空で返す */
    function topBlocks(source) {
        const blocks = [];
        let line = 0;
        for (const token of marked.lexer(source)) {
            if (token.type !== "space") {
                const raw = token.raw.replace(/\n+$/, "");
                blocks.push({ start: line + 1, end: line + raw.split("\n").length, raw, changed: new Set() });
            }
            line += token.raw.split("\n").length - 1;
        }
        return blocks;
    }
    /** 行の差分から、前の版と今の版の各行の種類と、変えていない行の前の版 → 今の版の行の対応を作る */
    function sideLineKinds(parts) {
        const before = [null];
        const after = [null];
        const map = [null];
        for (const part of parts) {
            for (const _ of part.lines) {
                if (part.kind !== "added") {
                    before.push(part.kind);
                    map.push(part.kind === "same" ? after.length : null);
                }
                if (part.kind !== "removed")
                    after.push(part.kind);
            }
        }
        return { before, after, map };
    }
    /** 塊の範囲の行のうち、その種類（消した・足した）で空行でない行を塊の変えた行に入れる */
    function markChangedLines({ blocks, kinds, lines, kind, }) {
        for (const block of blocks) {
            for (let line = block.start; line <= block.end; line += 1) {
                if (kinds[line] === kind && (lines[line - 1] ?? "").trim() !== "")
                    block.changed.add(line);
            }
        }
    }
    /** 本文を行の並びにする（末尾の改行で出る空の最後の要素は行ではない） */
    function linesOfText(text) {
        const lines = text.split("\n");
        if (lines.at(-1) === "")
            lines.pop();
        return lines;
    }
    MindmapPreview.linesOfText = linesOfText;
    /** 前後の Markdown の本文を塊に分け、変えていない塊を向かい合わせた左右の列の行にする。行の差分を打ち切ったら null */
    function sideBySideRows({ before, after }) {
        const parts = diffLineParts(before, after);
        if (parts === null)
            return null;
        const kinds = sideLineKinds(parts);
        const beforeBlocks = topBlocks(before);
        const afterBlocks = topBlocks(after);
        markChangedLines({ blocks: beforeBlocks, kinds: kinds.before, lines: linesOfText(before), kind: "removed" });
        markChangedLines({ blocks: afterBlocks, kinds: kinds.after, lines: linesOfText(after), kind: "added" });
        /** 前の版の x 番目の塊と対になる、今の版の from 番目以降の変えていない同じ塊の番号。無ければ -1 */
        const anchorOf = (x, from) => {
            const block = beforeBlocks[x];
            if (block === undefined || block.changed.size > 0)
                return -1;
            const target = kinds.map[block.start];
            for (let k = from; k < afterBlocks.length; k += 1) {
                const other = afterBlocks[k];
                if (other === undefined || target === null || target === undefined)
                    return -1;
                // 対応する行から始まる塊で、変えておらず原文が同じときだけ対にする
                if (other.start === target)
                    return other.changed.size === 0 && other.raw === block.raw ? k : -1;
                if (other.start > target)
                    return -1;
            }
            return -1;
        };
        const rows = [];
        let i = 0;
        let j = 0;
        while (i < beforeBlocks.length || j < afterBlocks.length) {
            // 次の区切り（変えていない塊の対）を探す。無ければ末尾まで
            let ai = beforeBlocks.length;
            let aj = afterBlocks.length;
            for (let x = i; x < beforeBlocks.length; x += 1) {
                const k = anchorOf(x, j);
                if (k >= 0) {
                    ai = x;
                    aj = k;
                    break;
                }
            }
            const left = beforeBlocks.slice(i, ai);
            const right = afterBlocks.slice(j, aj);
            // 区切りの間の変えた塊: 数が両側で同じなら 1 つずつ、違えばまとめて 1 つの行にする
            if (left.length === right.length) {
                left.forEach((block, offset) => {
                    const opposite = right[offset];
                    if (opposite !== undefined)
                        rows.push({ changed: true, left: [block], right: [opposite] });
                });
            }
            else {
                rows.push({ changed: true, left, right });
            }
            const anchorLeft = beforeBlocks[ai];
            const anchorRight = afterBlocks[aj];
            if (anchorLeft !== undefined && anchorRight !== undefined)
                rows.push({ changed: false, left: [anchorLeft], right: [anchorRight] });
            i = ai + 1;
            j = aj + 1;
        }
        return rows;
    }
    MindmapPreview.sideBySideRows = sideBySideRows;
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
    /** 行の差分のうち、消した行のすぐ後に同じ行の数の足した行が続くところを、変えた行の対にして返す（`parts` の添え字の並び。前から 1 行ずつが対になる） */
    function pairedParts(parts) {
        const pairs = [];
        parts.forEach((part, position) => {
            const next = parts[position + 1];
            // 消した行のすぐ後に、同じ行の数の足した行が続く（間に変えない行を挟まない）
            if (part.kind === "removed" && next?.kind === "added" && next.lines.length === part.lines.length) {
                pairs.push({ removed: position, added: position + 1 });
            }
        });
        return pairs;
    }
    MindmapPreview.pairedParts = pairedParts;
    /** 語の区切りに使う分け方。ブラウザが `Intl.Segmenter` を持たなければ null（jsdiff の既定の区切りで比べる） */
    let wordSegmenter;
    /** 語の区切りに使う分け方を、最初に呼んだときに 1 つ作って使い回す */
    function segmenterOf() {
        if (wordSegmenter === undefined) {
            wordSegmenter = typeof Intl.Segmenter === "function" ? new Intl.Segmenter("ja", { granularity: "word" }) : null;
        }
        return wordSegmenter;
    }
    /** 部分の文字をつないだもの */
    function joinText(parts) {
        return parts.map((part) => part.text).join("");
    }
    /** 変えた行の対の前と今の文字を語の単位で比べる。jsdiff を読めていない・時刻を過ぎた・打ち切った・同じ部分が少ない・部分をつないでも元の文字に戻らないときは null */
    function diffInline(before, after, deadline) {
        if (MindmapPreview.missingLibraries(["jsdiff"]).length > 0)
            return null;
        const remaining = deadline - performance.now();
        if (remaining <= 0)
            return null;
        const segmenter = segmenterOf();
        const parts = Diff.diffWords(before, after, { timeout: remaining, ...(segmenter === null ? {} : { intlSegmenter: segmenter }) });
        // 時間内に終わらなかった
        if (parts === undefined)
            return null;
        const sameLength = parts.filter((part) => !part.added && !part.removed).reduce((total, part) => total + part.value.length, 0);
        const shorter = Math.min(before.length, after.length);
        // ほとんど書き換えた対には面を付けない
        if (shorter === 0 || sameLength / shorter < MindmapPreview.WORD_PAIR_MIN_SAME_RATIO)
            return null;
        const inline = {
            before: parts.filter((part) => !part.added).map((part) => ({ kind: part.removed ? "removed" : "same", text: part.value })),
            after: parts.filter((part) => !part.removed).map((part) => ({ kind: part.added ? "added" : "same", text: part.value })),
        };
        // 同じ部分の文字が空白の違いで片側の文字とずれたとき、範囲を元の文字に当てられない
        if (joinText(inline.before) !== before || joinText(inline.after) !== after)
            return null;
        return inline;
    }
    MindmapPreview.diffInline = diffInline;
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
    /** 範囲の印の行（1 始まり）の間にある行を、改行でつないだ文字列にする */
    function embeddedHtmlContent({ lines, open, close }) {
        return lines.slice(open, close - 1).join("\n");
    }
    /** 前後の Markdown の本文の埋め込んだ HTML の範囲を並びの順で対にし、中身が違う対だけを返す。選んだ時点に対になる範囲が無い今の範囲は入れない */
    function pairEmbeddedHtml({ before, after }) {
        const beforeLines = before.split("\n");
        const afterLines = after.split("\n");
        const beforeRanges = MindmapPreview.embeddedHtmlRanges(before);
        const pairs = [];
        MindmapPreview.embeddedHtmlRanges(after).forEach((range, order) => {
            const previous = beforeRanges[order];
            if (previous === undefined)
                return;
            const pair = {
                order,
                before: embeddedHtmlContent({ lines: beforeLines, ...previous }),
                after: embeddedHtmlContent({ lines: afterLines, ...range }),
            };
            if (pair.before !== pair.after)
                pairs.push(pair);
        });
        return pairs;
    }
    MindmapPreview.pairEmbeddedHtml = pairEmbeddedHtml;
    /** 描いた前後の範囲の直下の要素（`outerHTML`）を並びで比べ、今の要素ごとに足した・変わったのマーカーを返す。変えていない要素は null。比べるのを打ち切ったら null */
    function childMarks({ before, after }) {
        const parts = Diff.diffArrays(before, after, { timeout: MindmapPreview.ARRAY_DIFF_TIMEOUT_MS });
        // 打ち切り
        if (parts === undefined)
            return null;
        const marks = [];
        // 直前の消した並びのうち、足した要素と対にできる残りの数
        let removedLeft = 0;
        for (const part of parts) {
            if (part.removed) {
                removedLeft = part.count ?? part.value.length;
            }
            else if (part.added) {
                // 消した並びに続く足した並びは、前から 1 つずつ消した要素と対にして変わった、対にならない残りを足したにする
                for (let position = 0; position < (part.count ?? part.value.length); position += 1) {
                    marks.push(removedLeft > 0 ? "changed" : "added");
                    removedLeft = Math.max(0, removedLeft - 1);
                }
            }
            else {
                removedLeft = 0;
                for (let position = 0; position < (part.count ?? part.value.length); position += 1)
                    marks.push(null);
            }
        }
        return marks;
    }
    MindmapPreview.childMarks = childMarks;
})(MindmapPreview || (MindmapPreview = {}));
// URL のハッシュの読み書きと履歴。画面・表示形式・開いている項目・全画面・絞り込みを、`URLSearchParams` の形で持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** タブの帯に並べる画面（ネットワークは帯の右端に別に置く） */
    MindmapPreview.TAB_KEYS = [
        "overview",
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
        "logs",
    ];
    /** 画面ごとの既定の表示形式（書いていない画面は表） */
    MindmapPreview.DEFAULT_VIEW = {
        decisions: "board",
        tasks: "board",
        docs: "cards",
    };
    /** 画面が持つ表示形式（書いていない画面は表だけ） */
    MindmapPreview.VIEWS_OF = {
        decisions: ["board", "map", "table"],
        tasks: ["board", "table"],
        docs: ["cards", "board", "table"],
    };
    /** 画面の既定の表示形式 */
    function defaultView(tab) {
        return MindmapPreview.DEFAULT_VIEW[tab] ?? "table";
    }
    MindmapPreview.defaultView = defaultView;
    /** 画面が持つ表示形式 */
    function viewsOf(tab) {
        return MindmapPreview.VIEWS_OF[tab] ?? ["table"];
    }
    MindmapPreview.viewsOf = viewsOf;
    /** URL のハッシュを `Route` にする */
    function parseHash({ hash, index }) {
        const params = new URLSearchParams(hash.replace(/^#/, ""));
        const requestedTab = params.get("tab");
        const tab = ([...MindmapPreview.TAB_KEYS, "graph"].includes(requestedTab) ? requestedTab : "overview");
        const requestedView = params.get("view");
        const view = (viewsOf(tab).includes(requestedView) ? requestedView : defaultView(tab));
        // 記録に無い ID は開かない
        const requestedId = params.get("id");
        const id = requestedId !== null && index.byId.has(requestedId) ? requestedId : null;
        const filters = {};
        for (const [key, value] of params) {
            // `f.~{列}` は文字の条件で、`|` を含んでも分けない
            if (key.startsWith("f.~"))
                filters[key.slice(2)] = [value];
            else if (key.startsWith("f."))
                filters[key.slice(2)] = value.split("|");
        }
        const requestedHeading = params.get("h");
        const heading = id !== null && requestedHeading ? requestedHeading : null;
        // 空の `diff` は時点を指さない
        const diff = params.get("diff") || null;
        return { tab, view, id, full: id !== null && params.get("full") === "1", filters, heading, diff };
    }
    MindmapPreview.parseHash = parseHash;
    /** `Route` を URL のハッシュにする（既定の値と絞り込みは書かない） */
    function toHash(route) {
        const params = new URLSearchParams();
        if (route.tab !== "overview")
            params.set("tab", route.tab);
        if (route.view !== defaultView(route.tab))
            params.set("view", route.view);
        if (route.id !== null)
            params.set("id", route.id);
        if (route.full)
            params.set("full", "1");
        if (route.heading)
            params.set("h", route.heading);
        if (route.diff)
            params.set("diff", route.diff);
        const text = params.toString();
        return text === "" ? "" : `#${text}`;
    }
    MindmapPreview.toHash = toHash;
    /** ハッシュを書き換え、履歴に積むか置き換える。履歴の状態に、見てきた項目の並びを持てる */
    function navigate({ route, push, trail, }) {
        const url = `${location.pathname}${location.search}${toHash(route)}`;
        const state = trail ?? history.state;
        if (push)
            history.pushState(state, "", url);
        else
            history.replaceState(state, "", url);
    }
    MindmapPreview.navigate = navigate;
})(MindmapPreview || (MindmapPreview = {}));
// サーバーの配信とのやり取り。記録の取得・レビュー中のコメントと書きかけ・まとめて送る・スレッド・書き換えの知らせの購読。
var MindmapPreview;
(function (MindmapPreview) {
    /** 配信のパス（画面が開いた URL からの相対パス） */
    MindmapPreview.API_PATHS = {
        records: "api/records",
        events: "api/events",
        comments: "api/comments",
        commentsSend: "api/comments/send",
        drafts: "api/drafts",
        opened: "api/opened",
        configDisplay: "api/config/display",
        threads: "api/threads",
        edits: "api/edits",
        editsSave: "api/edits/save",
    };
    /** 応答の本文から、日本語の理由（`detail`）を取り出す。読めなければ null */
    async function detailOf(response) {
        try {
            const problem = (await response.json());
            return typeof problem.detail === "string" ? problem.detail : null;
        }
        catch {
            return null;
        }
    }
    /** 記録を読む。届かないときと、サーバーが読めないと返したときを分ける */
    async function fetchRecords(fetchFn = window.fetch.bind(window)) {
        let response;
        try {
            response = await fetchFn(MindmapPreview.API_PATHS.records, { cache: "no-store" });
        }
        catch {
            return { ok: false, reason: "unreachable", detail: null };
        }
        // 200 でない: サーバーが読めないと返した
        if (!response.ok)
            return { ok: false, reason: "invalid", detail: await detailOf(response) };
        return { ok: true, data: (await response.json()) };
    }
    MindmapPreview.fetchRecords = fetchRecords;
    /** 値が前回開いた時点の形（文字列の `at` と 0 以上の整数の `seq`）か。日時だけの文字列（前の版の形）は偽 */
    function isOpenedPoint(value) {
        if (typeof value !== "object" || value === null)
            return false;
        const { at, seq } = value;
        return typeof at === "string" && typeof seq === "number" && Number.isInteger(seq) && seq >= 0;
    }
    MindmapPreview.isOpenedPoint = isOpenedPoint;
    /** プレビューを開いたことを知らせ、前回開いた時点と今の時点を返す。届かない・200 でない・読めないときは null */
    async function postOpened(fetchFn = window.fetch.bind(window)) {
        try {
            const response = await fetchFn(MindmapPreview.API_PATHS.opened, { method: "POST" });
            if (!response.ok)
                return null;
            const body = (await response.json());
            // 今の時点が読めない（前の版の形）: 使わない
            if (!isOpenedPoint(body.opened))
                return null;
            return { previous: isOpenedPoint(body.previous) ? body.previous : null, opened: body.opened };
        }
        catch {
            return null;
        }
    }
    MindmapPreview.postOpened = postOpened;
    /** ワークスペースの既定として、見た目と表示する種類を保存する。200 なら `data` が書いた後の `{display}` */
    async function putDisplay(display, fetchFn = window.fetch.bind(window)) {
        return callApi("PUT", MindmapPreview.API_PATHS.configDisplay, display, fetchFn);
    }
    MindmapPreview.putDisplay = putDisplay;
    /** コメント・書きかけの API を 1 回呼ぶ。届かないときと、断られたときを分ける */
    async function callApi(method, path, body = null, fetchFn = window.fetch.bind(window)) {
        let response;
        try {
            response = await fetchFn(path, body === null
                ? { method, cache: "no-store" }
                : { method, cache: "no-store", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        }
        catch {
            return { ok: false, status: null, detail: null, stale: [] };
        }
        if (response.ok) {
            // 204 は本文を持たない
            return { ok: true, data: response.status === 204 ? null : (await response.json()) };
        }
        // 断られた: 理由が読めなければ、ステータスの文言を使う
        let stale = [];
        let blocked = [];
        let detail = null;
        try {
            const problem = (await response.json());
            detail = typeof problem.detail === "string" ? problem.detail : null;
            stale = Array.isArray(problem.stale) ? problem.stale : [];
            blocked = Array.isArray(problem.blocked) ? problem.blocked : [];
        }
        catch {
            // 本文が JSON でない
        }
        return {
            ok: false,
            status: response.status,
            detail: detail ?? (response.statusText || String(response.status)),
            stale,
            ...(blocked.length > 0 ? { blocked } : {}),
        };
    }
    MindmapPreview.callApi = callApi;
    /** コメント・書きかけの API の 6 つの呼び出しを束ねて返す */
    function commentApi(fetchFn = window.fetch.bind(window)) {
        return {
            read: () => callApi("GET", MindmapPreview.API_PATHS.comments, null, fetchFn),
            add: (input) => callApi("POST", MindmapPreview.API_PATHS.comments, input, fetchFn),
            update: (id, patch) => callApi("PATCH", `${MindmapPreview.API_PATHS.comments}/${encodeURIComponent(id)}`, patch, fetchFn),
            remove: (id) => callApi("DELETE", `${MindmapPreview.API_PATHS.comments}/${encodeURIComponent(id)}`, null, fetchFn),
            saveDraft: (draft) => callApi("PUT", MindmapPreview.API_PATHS.drafts, draft, fetchFn),
            send: (ids) => callApi("POST", MindmapPreview.API_PATHS.commentsSend, { ids }, fetchFn),
        };
    }
    MindmapPreview.commentApi = commentApi;
    /** 保存待ちの編集の読み取り・追加・取り消し・まとめて保存を束ねて返す */
    function editApi(fetchFn = window.fetch.bind(window)) {
        return {
            read: () => callApi("GET", MindmapPreview.API_PATHS.edits, null, fetchFn),
            add: (input) => callApi("POST", MindmapPreview.API_PATHS.edits, input, fetchFn),
            remove: (id) => callApi("DELETE", `${MindmapPreview.API_PATHS.edits}/${encodeURIComponent(id)}`, null, fetchFn),
            save: () => callApi("POST", MindmapPreview.API_PATHS.editsSave, null, fetchFn),
        };
    }
    MindmapPreview.editApi = editApi;
    /** スレッドの読み取り・状態の書き換え・利用者の既読を束ねて返す。理由が空白だけなら `null` を送る */
    function threadApi(fetchFn = window.fetch.bind(window)) {
        return {
            read: () => callApi("GET", MindmapPreview.API_PATHS.threads, null, fetchFn),
            setStatus: (id, status, reason) => callApi("PATCH", `${MindmapPreview.API_PATHS.threads}/${encodeURIComponent(id)}`, { status, reason: reason === null || reason.trim() === "" ? null : reason.trim() }, fetchFn),
            seen: (id) => callApi("POST", `${MindmapPreview.API_PATHS.threads}/${encodeURIComponent(id)}/seen`, null, fetchFn),
        };
    }
    MindmapPreview.threadApi = threadApi;
    /** 書き換えの知らせにつなぎ、`changed` と接続の状態の変化を知らせる。つなぎ直しは `EventSource` に任せる。返す関数でつながりを閉じる */
    function subscribeEvents({ onChanged, onConnection, EventSourceCtor = window.EventSource, }) {
        const source = new EventSourceCtor(MindmapPreview.API_PATHS.events);
        let last = null;
        /** 接続の状態が変わったときだけ知らせる */
        const report = (connected) => {
            if (last === connected)
                return;
            last = connected;
            onConnection(connected);
        };
        source.addEventListener("open", () => report(true));
        source.addEventListener("error", () => report(false));
        source.addEventListener("changed", () => onChanged());
        return () => source.close();
    }
    MindmapPreview.subscribeEvents = subscribeEvents;
})(MindmapPreview || (MindmapPreview = {}));
// 保存待ちの編集を記録に当てた表示の値と、項目・キー・案の保存待ちの印の種類。
var MindmapPreview;
(function (MindmapPreview) {
    /** 追加する項目の仮の ID の頭 */
    MindmapPreview.NEW_ID_PREFIX = "new-";
    /** 設定の編集の向け先 */
    MindmapPreview.SETTINGS_TARGET = "settings";
    /** 値の入った案（記号と中身）を作る */
    function optionOf(key, value) {
        return { key, content: "", ...value };
    }
    /** 記録の写しに保存待ちの編集を溜めた順に当て、画面に出す値を返す（元の記録は変えない） */
    function applyEdits(data, edits) {
        const applied = structuredClone(data);
        const find = (id) => {
            for (const kind of MindmapPreview.KIND_KEYS) {
                const found = applied[kind].find((item) => item.id === id);
                if (found !== undefined)
                    return found;
            }
            return undefined;
        };
        for (const edit of edits) {
            const key = edit.key ?? "";
            if (edit.op === "setting") {
                applied.settings[key] = edit.value;
            }
            else if (edit.op === "item-add") {
                const kind = key;
                if (!MindmapPreview.KIND_KEYS.includes(kind))
                    continue;
                const values = { ...edit.value };
                const item = { id: edit.target, created: edit.created, updated: edit.created, ...values };
                // 本文の文字列は、本文の置き場所に移す
                if (typeof values["body"] === "string") {
                    item.body = `${edit.target}.md`;
                    applied.bodies[item.body] = values["body"];
                }
                applied[kind].push(item);
            }
            else {
                const item = find(edit.target);
                if (item === undefined)
                    continue;
                if (edit.op === "set") {
                    if (key === "body") {
                        const name = item.body ?? `${item.id}.md`;
                        item.body = name;
                        applied.bodies[name] = String(edit.value ?? "");
                    }
                    else if (edit.value === null) {
                        delete item[key];
                    }
                    else {
                        item[key] = edit.value;
                    }
                }
                else if (edit.op === "option-add") {
                    item.options = [...(item.options ?? []), optionOf(key, edit.value)];
                }
                else if (edit.op === "option-edit") {
                    item.options = (item.options ?? []).map((option) => option.key === key ? { ...option, ...edit.value } : option);
                }
                else if (edit.op === "adopt") {
                    item.options = (item.options ?? []).map((option) => ({ ...option, adopted: option.key === edit.value }));
                }
            }
        }
        return applied;
    }
    MindmapPreview.applyEdits = applyEdits;
    /** 項目（`key` を渡せばそのキーか案）に付ける保存待ちの印の種類。当たる編集が無ければ null */
    function pendingMarkOf({ edits, blocked, target, key, }) {
        const hits = edits.filter((edit) => {
            if (edit.target !== target)
                return false;
            // キーを渡さないときは、その項目への編集の全て
            if (key === undefined)
                return true;
            return edit.key === key || (edit.op === "adopt" && edit.value === key);
        });
        if (hits.length === 0)
            return null;
        if (hits.some((edit) => blocked.has(edit.id)))
            return "blocked";
        if (key === undefined && hits.some((edit) => edit.op === "item-remove"))
            return "remove";
        return "pending";
    }
    MindmapPreview.pendingMarkOf = pendingMarkOf;
})(MindmapPreview || (MindmapPreview = {}));
// ロック。注目の起点を 1 つの項目に留める。押下の判定・2 回押しの読み替え・鍵の震えの量は、ネットワークと検討事項のマップで共通。
var MindmapPreview;
(function (MindmapPreview) {
    /** 2 回押しとみなす間隔（ms）。前に押してからこの時間未満に押した 2 回目を、前に押した項目への 2 回押しとみなす */
    MindmapPreview.DOUBLE_TAP_MS = 450;
    /** 2 回押しとみなす位置のずれ（px）。前に押した位置からの距離がこの値未満の 2 回目を 2 回押しとみなす */
    MindmapPreview.DOUBLE_TAP_PX = 24;
    /** 鍵が震え始めてから収まるまでの時間（ms） */
    MindmapPreview.SHAKE_MS = 1000;
    /** 震えの往復の回数 */
    const SHAKE_WAVES = 5;
    /** 鍵の左右の振れ幅（px） */
    MindmapPreview.SHAKE_SHIFT = 6;
    /** 鍵が上を軸に傾く角度（rad） */
    MindmapPreview.SHAKE_SWING = 0.45;
    /** 震え始めに鍵を大きくする割合 */
    MindmapPreview.SHAKE_GROW = 0.45;
    /** 赤い光のにじみの半径（px） */
    const SHAKE_GLOW = 4;
    /** ロックの判定をする幅（幅 900px 以下では詳細が全面に出るため、ネットワークも検討事項のマップもロックしない） */
    MindmapPreview.LOCK_QUERY = "(min-width: 901px)";
    /** 要素が文字を入力する欄か（`input`・`textarea`・`select`・編集できる要素。`L` キーを受けない判定に使う） */
    function isTyping(element) {
        return element instanceof HTMLElement && (element.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName));
    }
    MindmapPreview.isTyping = isTyping;
    /** 押した項目・詳細を開いている項目・ロックしている項目から、すること（と押した後のロック）を返す。余白を押したときは `pressed` が `null`。`L` キーは `pressed` に詳細を開いている項目を渡す */
    function lockTap({ locked, pressed, open, }) {
        if (locked !== null) {
            if (pressed === locked) {
                // ロックした項目は、詳細を開いている状態でもう一度押したときだけ外す。開いていなければ詳細を戻すだけ
                return open === pressed ? { action: "unlock", locked: null } : { action: "open", locked };
            }
            // 詳細を開いている別の項目をもう一度押した・余白を押したときは、ロック・詳細・表示を変えずに知らせる
            return { action: pressed === null || pressed === open ? "shake" : "open", locked };
        }
        if (pressed === null)
            return { action: "blank", locked: null };
        // ロックしていないとき: 詳細を開いている項目をもう一度押したらロックする
        return pressed === open ? { action: "lock", locked: pressed } : { action: "open", locked: null };
    }
    MindmapPreview.lockTap = lockTap;
    /** 今の押下が前の押下から `DOUBLE_TAP_MS` 未満かつ `DOUBLE_TAP_PX` 未満の位置なら、前に押した項目を押したものとして返す（詳細が開いて枠がずれても 2 回押しにする）。それ以外は今押した項目を返す */
    function resolvePress({ last, press }) {
        if (last === null)
            return press.id;
        const second = press.time - last.time < MindmapPreview.DOUBLE_TAP_MS && Math.hypot(press.x - last.x, press.y - last.y) < MindmapPreview.DOUBLE_TAP_PX;
        return second ? last.id : press.id;
    }
    MindmapPreview.resolvePress = resolvePress;
    /** 震え始めてからの時間（ms）から、収まり具合 `decay`（1 → 0）と振れ `wave`（-1〜1）を返す */
    function shakeAt(elapsed) {
        return { decay: 1 - elapsed / MindmapPreview.SHAKE_MS, wave: Math.sin((elapsed / MindmapPreview.SHAKE_MS) * Math.PI * 2 * SHAKE_WAVES) };
    }
    MindmapPreview.shakeAt = shakeAt;
    /** 震える鍵の赤（ライトは `--red-700`、ダークは `--red-300`） */
    function shakeColor() {
        const dark = document.documentElement.dataset["theme"] === "dark";
        return getComputedStyle(document.documentElement).getPropertyValue(dark ? "--red-300" : "--red-700").trim();
    }
    MindmapPreview.shakeColor = shakeColor;
    /** 震え始めた時刻（要素の鍵の震えが共有する。描き直しで鍵の要素が作り直されても続きから震わせる） */
    let elementShakeStart = Number.NEGATIVE_INFINITY;
    /** 要素の鍵を震わせる。毎コマ `find` が返す今の鍵へ `shakeAt` の量を当て、`SHAKE_MS` を過ぎたら外す。CSS のアニメーションを使わないので `prefers-reduced-motion` でも止まらない */
    function shakeKeyElement(find) {
        const running = performance.now() - elementShakeStart < MindmapPreview.SHAKE_MS;
        elementShakeStart = performance.now();
        // 震えている間に呼ばれたら、始まりを今にして続きから震わせる（毎コマの処理は 1 つだけにする）
        if (running)
            return;
        const step = (now) => {
            const key = find();
            const elapsed = Math.max(0, now - elementShakeStart);
            if (elapsed >= MindmapPreview.SHAKE_MS) {
                key?.removeAttribute("style");
                return;
            }
            if (key !== null) {
                const { decay, wave } = shakeAt(elapsed);
                // 南京錠のように上を軸に振れ、大きくなって赤く光り、だんだん収まる
                key.style.cssText = `transform-origin: 50% 0; transform: translateX(${wave * MindmapPreview.SHAKE_SHIFT * decay}px) rotate(${wave * MindmapPreview.SHAKE_SWING * decay}rad) scale(${1 + MindmapPreview.SHAKE_GROW * decay}); color: ${shakeColor()}; filter: drop-shadow(0 0 ${SHAKE_GLOW * decay}px ${shakeColor()})`;
            }
            requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }
    MindmapPreview.shakeKeyElement = shakeKeyElement;
})(MindmapPreview || (MindmapPreview = {}));
// 表示形式の切り替え。形式ごとに同じ幅のボタンを並べ、選んでいる形式を押された見た目にする。
var MindmapPreview;
(function (MindmapPreview) {
    /** 表示形式 → ボタンのアイコン */
    const VIEW_ICON = {
        map: "map",
        board: "board",
        cards: "cards",
        table: "table",
    };
    /** 表示形式を切り替えるセグメントを返す（描き直しは使う側が行う） */
    function viewSwitch({ views, current, onChange }) {
        const buttons = views.map(({ key, label }) => MindmapPreview.h({
            tag: "button",
            attrs: {
                type: "button",
                "data-view": key,
                "aria-pressed": String(key === current),
                onclick: () => {
                    // 選んでいる形式を押しても何もしない
                    if (key !== current)
                        onChange(key);
                },
            },
            children: [MindmapPreview.icon(VIEW_ICON[key]), label],
        }));
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "segment", role: "group", "aria-label": "表示形式" },
            children: [...buttons],
        });
    }
    MindmapPreview.viewSwitch = viewSwitch;
})(MindmapPreview || (MindmapPreview = {}));
// トップバー。話し合いの題名・全体の検索の入口・変更履歴・ライト / ダークの切り替え・表示の設定・絞り込み・コメントのボタンと、画面を移るタブの帯（右端にネットワークの入口）を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 件数の表示を揺らさない上限 */
    const COMMENT_COUNT_CAP = 99;
    /** 絞り込みのバッジが 2 桁に広がる条件の数 */
    const FILTER_BADGE_WIDE_FROM = 10;
    /** ブランドのマーク（木の形の線画） */
    function brandMark() {
        const holder = document.createElement("template");
        holder.innerHTML =
            '<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="16" r="4"/><path d="M12 16h5M17 16V7h5M17 16v9h5"/><circle cx="25" cy="7" r="2.6"/><circle cx="25" cy="25" r="2.6"/></svg>';
        return holder.content.firstElementChild;
    }
    /** 画面を移るリンク（ハッシュのリンクにして、押したときは使う側が移る） */
    function tabLink({ key, label, icon: iconName, count, marked = false }, current, onNavigate, extraClass = "") {
        return MindmapPreview.h({
            tag: "a",
            attrs: {
                class: `tab ${extraClass}`.trim(),
                href: `#${key === "overview" ? "" : `tab=${key}`}`,
                "data-tab": key,
                "aria-current": key === current ? "page" : null,
                onclick: (event) => {
                    event.preventDefault();
                    onNavigate(key);
                },
            },
            children: [
                MindmapPreview.icon(iconName),
                label,
                count === undefined ? null : MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [count] }),
                // 差分の表示の間、印の付いた項目を持つ種類に、件数を残したまま点を重ねる
                marked
                    ? MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "df-dot" },
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["新規・変更・消した項目があります"] })],
                    })
                    : null,
            ],
        });
    }
    /** 「変更履歴」のボタン（印と文言）。押すと変更履歴のモーダルを開く */
    function historyButton(onClick) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "hist-btn",
                type: "button",
                "data-act": "hist",
                "aria-haspopup": "dialog",
                "aria-label": "変更履歴",
                onclick: onClick,
            },
            children: [MindmapPreview.icon("history"), MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["変更履歴"] })],
        });
    }
    /** 選んだ時点の札と、差分の表示をやめる × */
    function diffChip({ point, onOff }) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "df-chip" },
            children: [
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "df-chip-t", title: `${point.name}（${point.sub}）` },
                    children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["差分の時点: "] }), point.name],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        type: "button",
                        "data-act": "diffoff",
                        "aria-label": "差分の表示をやめる",
                        title: "差分の表示をやめる",
                        onclick: () => onOff?.(),
                    },
                    children: [MindmapPreview.icon("x")],
                }),
            ],
        });
    }
    /** サーバーにつながらないときの表示。広い幅は読んだ日時つきの文言、狭い幅は短い文言で、日時は `title` に持つ */
    function connectionNotice(readAt) {
        const readAtText = readAt === null ? null : MindmapPreview.formatJst(readAt);
        return MindmapPreview.h({
            tag: "span",
            attrs: {
                class: "conn",
                role: "status",
                title: readAtText === null ? "サーバーにつながりません" : `${readAtText} に読んだ記録を出しています`,
            },
            children: [
                MindmapPreview.icon("offline"),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "conn-long" },
                    children: [
                        readAtText === null
                            ? "サーバーにつながりません"
                            : `サーバーにつながりません（${readAtText} に読んだ記録）`,
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "conn-short" }, children: ["つながりません"] }),
            ],
        });
    }
    /** コメントのボタン（印と「コメント」と件数）。押すとコメントの一覧を開く・閉じる */
    function commentsButton({ count, open, unread, onClick }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `comments-btn${open ? " open" : ""}`,
                type: "button",
                "data-act": "comments",
                "aria-label": `コメント（${unread ? "未読あり・" : ""}レビュー中 ${count} 件）`,
                "aria-expanded": String(open),
                onclick: () => onClick?.(),
            },
            children: [
                // 吹き出しの印の右上に、未読の点を重ねる（ボタンの幅を変えない。点は読み上げから外す）
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "cb-icon" },
                    children: [MindmapPreview.icon("comment"), unread ? MindmapPreview.h({ tag: "span", attrs: { class: "unread-dot", "aria-hidden": "true" } }) : null],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["コメント"] }),
                MindmapPreview.h({
                    tag: "span",
                    // 件数が `99+` に広がったときは、幅の広い中身の印を付ける（style.css が詰め方を切り替える）
                    attrs: { class: `count${count === 0 ? " zero" : ""}`, "data-wide": count > COMMENT_COUNT_CAP },
                    children: [count > COMMENT_COUNT_CAP ? `${COMMENT_COUNT_CAP}+` : count],
                }),
            ],
        });
    }
    /** 保存待ちのボタン（印と「保存待ち」と件数）。押すと保存待ちのパネルを開く・閉じる */
    function pendingButton({ count, open, blocked, onClick, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `pending-btn${open ? " open" : ""}${blocked ? " blocked" : ""}`,
                type: "button",
                "data-act": "pending",
                "aria-label": `保存待ち（${count} 件${blocked ? "・書き込めない編集あり" : ""}）`,
                "aria-expanded": String(open),
                "aria-controls": open && document.getElementById("pending-panel") !== null ? "pending-panel" : null,
                onclick: () => onClick?.(),
            },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "pb-icon" }, children: [MindmapPreview.icon(blocked ? "alert" : "layers")] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["保存待ち"] }),
                MindmapPreview.h({
                    tag: "span",
                    // 件数が `99+` に広がったときは、幅の広い中身の印を付ける（style.css が詰め方を切り替える）
                    attrs: { class: "count", "data-wide": count > COMMENT_COUNT_CAP },
                    children: [count > COMMENT_COUNT_CAP ? `${COMMENT_COUNT_CAP}+` : count],
                }),
            ],
        });
    }
    /** 表示の設定のボタン（印と「表示の設定」）。押すと表示の設定のパネルを開く・閉じる */
    function settingsButton({ open, onToggle }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `settings-btn${open ? " open" : ""}`,
                type: "button",
                "data-act": "settings",
                "aria-label": "表示の設定",
                "aria-expanded": String(open),
                onclick: () => onToggle(),
            },
            children: [MindmapPreview.icon("sliders"), MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["表示の設定"] })],
        });
    }
    /** 絞り込みのボタン（印と「絞り込み」と、値を選んでいる条件の数のバッジ）。押すと絞り込みのドロワーを開く・閉じる */
    function filterButton({ count, open, onClick }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `filter-btn${open ? " open" : ""}`,
                type: "button",
                "data-act": "filter",
                "aria-label": count === 0 ? "絞り込み" : `絞り込み（${count} つの条件で絞り込み中）`,
                "aria-expanded": String(open),
                // ドロワーを開いていて、指す先が文書にあるときだけ付ける（ドロワーを描いた後は、ドロワーが付け直す）
                "aria-controls": open && document.getElementById("drawer") !== null ? "drawer" : null,
                onclick: () => onClick?.(),
            },
            children: [
                MindmapPreview.icon("filter"),
                MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["絞り込み"] }),
                count === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "span",
                        // 2 桁に広がったときは、幅の広い中身の印を付ける（style.css が詰め方を切り替える）
                        attrs: { class: "fbadge", "aria-hidden": "true", "data-wide": count >= FILTER_BADGE_WIDE_FROM },
                        children: [count],
                    }),
            ],
        });
    }
    /** トップバーとタブの帯を返す */
    function topbar({ title, tabs, current, theme, onNavigate, onSearch, onTheme, connection = "online", readAt = null, comments = false, commentCount = 0, commentsOpen = false, commentsUnread = false, onComments, diffPoint = null, onHistory, onDiffOff, settingsOpen = false, onSettings, filter = false, filterCount = 0, filterOpen = false, onFilter, pending = false, pendingCount = 0, pendingOpen = false, pendingBlocked = false, onPending, }) {
        const nextTheme = theme === "dark" ? "light" : "dark";
        const bar = MindmapPreview.h({
            tag: "header",
            attrs: { class: comments ? "topbar has-comments" : "topbar" },
            children: [
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "brand" },
                    children: [
                        brandMark(),
                        MindmapPreview.h({ tag: "span", attrs: { class: "brand-name" }, children: ["mindstella"] }),
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "brand-sub", title }, children: [title] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                connection === "offline" ? connectionNotice(readAt) : null,
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "search-trigger",
                        type: "button",
                        "data-act": "search",
                        "aria-label": "すべての項目を検索",
                        "aria-keyshortcuts": "Control+K Meta+K",
                        onclick: () => onSearch(),
                    },
                    children: [
                        MindmapPreview.icon("search"),
                        MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["すべての項目を検索"] }),
                        MindmapPreview.h({ tag: "kbd", children: [/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘K" : "Ctrl+K"] }),
                    ],
                }),
                onHistory === undefined ? null : historyButton(onHistory),
                // 差分の表示の間は、選んだ時点の札と外すボタンを「変更履歴」の右に出す
                diffPoint === null ? null : diffChip({ point: diffPoint, onOff: onDiffOff }),
                // コメントのボタンを右端に置くとき、検索の入口を中央へ寄せる
                comments ? MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }) : null,
                onSettings === undefined ? null : settingsButton({ open: settingsOpen, onToggle: onSettings }),
                filter ? filterButton({ count: filterCount, open: filterOpen, onClick: onFilter }) : null,
                pending && pendingCount > 0
                    ? pendingButton({ count: pendingCount, open: pendingOpen, blocked: pendingBlocked, onClick: onPending })
                    : null,
                comments ? commentsButton({ count: commentCount, open: commentsOpen, unread: commentsUnread, onClick: onComments }) : null,
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "top-btn",
                        type: "button",
                        "data-theme": nextTheme,
                        "aria-label": theme === "dark" ? "ライトに切り替え" : "ダークに切り替え",
                        onclick: () => onTheme(nextTheme),
                    },
                    children: [MindmapPreview.icon(theme === "dark" ? "sun" : "moon")],
                }),
            ],
        });
        const tabbar = MindmapPreview.h({
            tag: "nav",
            attrs: { class: "tabbar", "aria-label": "項目の種類" },
            children: [
                ...tabs.map((tab) => tabLink(tab, current, onNavigate)),
                MindmapPreview.h({ tag: "span", attrs: { class: "tab-gap" } }),
                tabLink({ key: "graph", label: "ネットワーク", icon: "network" }, current, onNavigate, "tab-special"),
            ],
        });
        return MindmapPreview.h({ tag: "div", attrs: { class: "top" }, children: [bar, tabbar] });
    }
    MindmapPreview.topbar = topbar;
})(MindmapPreview || (MindmapPreview = {}));
// 差分の印。差分の表示の間、選んだ時点で足した項目に新規（太い +）、変えた項目に変更（塗った ●）、消した項目に消した（太い −）の印を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類 → 画面に出す名前 */
    const DIFF_LABEL = { new: "新規", changed: "変更", removed: "消した" };
    /** 種類 → 記号 */
    const DIFF_GLYPH = { new: "plus", changed: "changed", removed: "minus" };
    /** 種類 → 色の class */
    const DIFF_TONE = { new: "df-new", changed: "df-chg", removed: "df-del" };
    /** 差分の印。色だけでなく形（+ と ● と −）でも新規と変更と消したを分け、名前は読み上げに残す */
    function diffMark({ kind, labeled = false }) {
        const label = DIFF_LABEL[kind];
        const glyph = MindmapPreview.icon(DIFF_GLYPH[kind]);
        const tone = DIFF_TONE[kind];
        // 札: 記号と文言を見える形で出す
        if (labeled)
            return MindmapPreview.h({ tag: "span", attrs: { class: `df-badge ${tone}` }, children: [glyph, label] });
        // 一覧の印: 記号だけを見せ、名前を読み上げと title に持つ
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: `df-mark ${tone}`, title: label },
            children: [glyph, MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [label] })],
        });
    }
    MindmapPreview.diffMark = diffMark;
    /** 項目の ID に印があれば、一覧の印（文言なし）を返す。無ければ null */
    function markFor({ marks, id }) {
        const kind = marks?.[id];
        return kind === undefined ? null : diffMark({ kind });
    }
    MindmapPreview.markFor = markFor;
})(MindmapPreview || (MindmapPreview = {}));
// 消した項目の帯。差分の表示の間、選んだ時点で消したその種類の項目を、一覧の上に消した印・ID・消したときのタイトルで並べる。消した項目は中身が残らないので、押せる要素にしない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 消した項目の帯。項目が無ければ null */
    function removedBand({ items }) {
        if (items.length === 0)
            return null;
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "rm-band", "aria-label": "この時点で消した項目" },
            children: [
                MindmapPreview.h({
                    tag: "h2",
                    attrs: { class: "rm-band-t" },
                    children: ["消した項目", MindmapPreview.h({ tag: "span", attrs: { class: "n mono" }, children: [items.length] })],
                }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "rm-list" },
                    children: items.map((item) => MindmapPreview.h({
                        tag: "li",
                        attrs: { class: "rm-item", "data-removed-id": item.id },
                        children: [
                            MindmapPreview.diffMark({ kind: "removed" }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "rm-ttl" }, children: [item.title] }),
                        ],
                    })),
                }),
            ],
        });
    }
    MindmapPreview.removedBand = removedBand;
})(MindmapPreview || (MindmapPreview = {}));
// 取り下げの札。取り下げた調査・資料・用語集・メモ・会話ログのタイトルの右に、差分の表示によらず置く。検討事項の状態「取り下げ」と同じ × の印と文言に枠を付け、状態の札（枠なし）と見分ける。
var MindmapPreview;
(function (MindmapPreview) {
    /** 取り下げの札。× の印は読み上げに出さず、「取り下げ」の文字で伝える */
    function withdrawnBadge({ large = false } = {}) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: large ? "wd-badge wd-large" : "wd-badge" },
            children: [MindmapPreview.statusMark("取り下げ"), "取り下げ"],
        });
    }
    MindmapPreview.withdrawnBadge = withdrawnBadge;
})(MindmapPreview || (MindmapPreview = {}));
// コメントの印。コメントを書いた項目に、吹き出しの線と件数の小さなピルを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 画面に実数で出す件数の上限（これを超えると「99+」） */
    const COMMENT_MARK_SHOWN_MAX = 99;
    /** 印を置く場所を表す属性（値は項目の ID） */
    const COMMENT_TARGET_ATTR = "data-comment-target";
    /** コメントの印。数字は画面にだけ見せ、読み上げは実数の「コメント {件数} 件」を `sr-only` と `title` に持つ */
    function commentMark({ count }) {
        const spoken = `コメント ${count} 件`;
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "cmk", title: spoken },
            children: [
                MindmapPreview.icon("bubble"),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "cmk-n", "aria-hidden": "true" },
                    children: [count > COMMENT_MARK_SHOWN_MAX ? `${COMMENT_MARK_SHOWN_MAX}+` : String(count)],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [spoken] }),
            ],
        });
    }
    MindmapPreview.commentMark = commentMark;
    /** 本文の画面の中の印を置く場所ごとに、`counts` の件数で印を入れ替える。画面は描き直さない */
    function refreshCommentMarks({ root, counts, }) {
        for (const place of root.querySelectorAll(`[${COMMENT_TARGET_ATTR}]`)) {
            const count = counts[place.getAttribute(COMMENT_TARGET_ATTR) ?? ""] ?? 0;
            // 件数が無い場所は空にする
            if (count === 0)
                place.replaceChildren();
            else
                place.replaceChildren(commentMark({ count }));
        }
    }
    MindmapPreview.refreshCommentMarks = refreshCommentMarks;
    /** 項目の印を置く場所（`refreshCommentMarks` が差し替える）。件数があればその印を入れて返す */
    function commentPlace({ id, count }) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "cmk-place", [COMMENT_TARGET_ATTR]: id },
            children: [count === undefined || count === 0 ? null : commentMark({ count })],
        });
    }
    MindmapPreview.commentPlace = commentPlace;
})(MindmapPreview || (MindmapPreview = {}));
// タグの並び。主題のタグは名前の前に二重丸のマーカーを置く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 主題のタグの読み上げと `title` に出す文字 */
    const MAIN_TAG_LABEL = "主題";
    /** タグを記録の順のまま `span.tag` で並べる。文字列の要素は主題でないタグとして出す */
    function tagList(values) {
        const fragment = document.createDocumentFragment();
        for (const value of values ?? []) {
            const name = typeof value === "string" ? value : value.name;
            const isMain = typeof value !== "string" && value.main === true;
            if (!isMain) {
                fragment.append(MindmapPreview.h({ tag: "span", attrs: { class: "tag" }, children: [name] }));
                continue;
            }
            // 主題: マーカーは装飾として隠し、「主題」の文字は読み上げだけに出す
            const spoken = MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [MAIN_TAG_LABEL] });
            fragment.append(MindmapPreview.h({ tag: "span", attrs: { class: "tag is-main", title: MAIN_TAG_LABEL }, children: [MindmapPreview.icon("main"), spoken, name] }));
        }
        return fragment;
    }
    MindmapPreview.tagList = tagList;
})(MindmapPreview || (MindmapPreview = {}));
// チップの入力。値のチップと、値を追加する入力欄。項目のタグは主題のトグルを持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** 値を並べるキーの入力（チップと、追加する入力欄）。`mainToggle` が真のときは値を `{name, main?}` で持ち、チップに主題のトグルを置く */
    function chipsInput({ controlId, name, hint, values, suggestions, monospace, mainToggle = false, disabled, onChange, }) {
        let current = values.map((value) => typeof value === "string" ? { name: value } : value.main === true ? { name: value.name, main: true } : { name: value.name });
        /** `onChange` に渡す並び（トグルを持たないときは名前の文字列の並び） */
        const output = () => (mainToggle ? current.map((tag) => ({ ...tag })) : current.map((tag) => tag.name));
        const box = MindmapPreview.h({ tag: "div", attrs: { class: "pe-chips", role: "group", "aria-label": name } });
        const listId = `${controlId}-list`;
        const field = MindmapPreview.h({
            tag: "input",
            attrs: {
                id: controlId,
                class: "input pe-chip-input",
                type: "text",
                list: suggestions === null ? null : listId,
                placeholder: hint,
                "aria-label": `${name}を追加`,
                autocomplete: "off",
                disabled,
            },
        });
        /** 入力した値を並びに追加する（空と、もうある値は追加しない。追加したタグは主題でない） */
        const addValue = () => {
            const text = field.value.trim();
            field.value = "";
            if (text === "" || current.some((tag) => tag.name === text))
                return;
            current = [...current, { name: text }];
            draw();
            onChange(output(), null);
            box.querySelector(".pe-chip-input")?.focus();
        };
        field.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" || event.isComposing)
                return;
            event.preventDefault();
            addValue();
        });
        field.addEventListener("change", addValue);
        /** そのタグの主題のトグル */
        const toggleButton = (entry, index) => {
            const isMain = entry.main === true;
            return MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "pe-chip-main",
                    type: "button",
                    "aria-label": `${entry.name} を主題`,
                    "aria-pressed": isMain ? "true" : "false",
                    title: isMain ? "主題を外す" : "主題にする",
                    "data-index": index,
                    disabled,
                    onclick: () => {
                        current = current.map((tag, position) => position !== index ? tag : tag.main === true ? { name: tag.name } : { name: tag.name, main: true });
                        draw();
                        onChange(output(), null);
                        // 押した後も同じタグのトグルにフォーカスを残す
                        box.querySelector(`.pe-chip-main[data-index="${index}"]`)?.focus();
                    },
                },
                children: [MindmapPreview.icon(isMain ? "main" : "mainOff"), MindmapPreview.h({ tag: "span", attrs: { class: "tag-main-text" }, children: ["主題"] })],
            });
        };
        /** チップを描き直す */
        const draw = () => {
            box.replaceChildren(...current.map((entry, index) => MindmapPreview.h({
                tag: "span",
                attrs: {
                    class: `tag pe-chip${monospace ? " mono" : ""}${mainToggle ? " has-main" : ""}${mainToggle && entry.main === true ? " is-main" : ""}`,
                },
                children: [
                    mainToggle ? toggleButton(entry, index) : null,
                    entry.name,
                    MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "pe-chip-x",
                            type: "button",
                            "aria-label": `${entry.name} を外す`,
                            disabled,
                            onclick: () => {
                                current = current.filter((_, position) => position !== index);
                                draw();
                                onChange(output(), entry.name);
                            },
                        },
                        children: [MindmapPreview.icon("x")],
                    }),
                ],
            })), field, ...(suggestions === null
                ? []
                : [
                    MindmapPreview.h({
                        tag: "datalist",
                        attrs: { id: listId },
                        children: suggestions.map((tag) => MindmapPreview.h({ tag: "option", attrs: { value: tag } })),
                    }),
                ]));
        };
        draw();
        return box;
    }
    MindmapPreview.chipsInput = chipsInput;
})(MindmapPreview || (MindmapPreview = {}));
// 変更履歴のモーダル。差分の表示で比べる時点を、日時・説明・変わった項目の数つきで新しい順に並べ、1 つ選ばせる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 時点の行（押すと選ぶ。選んでいる行にチェックと `aria-current` を付ける） */
    function pointRow({ point, selected, onPick, }) {
        return MindmapPreview.h({
            tag: "li",
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "hist-item",
                        type: "button",
                        "data-sel": point.sel,
                        "aria-current": selected ? "true" : null,
                        // 開いたときのフォーカスは、選んでいる行に置く
                        autofocus: selected,
                        onclick: () => onPick(point.sel),
                    },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "hist-check", "aria-hidden": "true" }, children: [selected ? MindmapPreview.icon("check") : null] }),
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "hist-main" },
                            children: [
                                MindmapPreview.h({ tag: "span", attrs: { class: "hist-name" }, children: [point.name] }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "hist-sub" }, children: [point.sub] }),
                            ],
                        }),
                        point.count === undefined ? null : MindmapPreview.h({ tag: "span", attrs: { class: "hist-n mono" }, children: [`${point.count} 件`] }),
                    ],
                }),
            ],
        });
    }
    /** 変更履歴のモーダルを返す。文書に入れた後、呼ぶ側が `showModal()` で開く。外側の押下と Esc で閉じる */
    function historyDialog({ points, current, onPick, onClose }) {
        const dialog = MindmapPreview.h({
            tag: "dialog",
            attrs: { class: "hist", "aria-labelledby": "hist-title", closedby: "any" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "hist-head" },
                    children: [
                        MindmapPreview.h({ tag: "h2", attrs: { id: "hist-title" }, children: ["変更履歴"] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn",
                                type: "button",
                                "data-act": "hist-close",
                                "aria-label": "変更履歴を閉じる",
                                onclick: () => dialog.close(),
                            },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "hist-list" },
                    children: points.map((point) => pointRow({
                        point,
                        selected: point.sel === current,
                        onPick: (sel) => {
                            // 選んだら閉じてから知らせる（使う側が描き直しても、モーダルが残らない）
                            dialog.close();
                            onPick(sel);
                        },
                    })),
                }),
            ],
        });
        // 外側（後ろの幕）を押したときも閉じる（`closedby` が効かない環境のため）
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog)
                dialog.close();
        });
        dialog.addEventListener("close", () => {
            dialog.remove();
            onClose();
        });
        return dialog;
    }
    MindmapPreview.historyDialog = historyDialog;
})(MindmapPreview || (MindmapPreview = {}));
// 表と、並べ替え・絞り込みの計算。列の見出しで並べ替え・ピン留めでき、表の上に絞り込みの条件のチップを並べる。絞り込みの条件はドロワーで選ぶ。
var MindmapPreview;
(function (MindmapPreview) {
    /** 列が行から取る値を、文字の配列にする */
    function valuesOf(column, row) {
        const value = column.get(row);
        if (value === null || value === undefined)
            return [];
        return Array.isArray(value) ? value.map(String) : [String(value)];
    }
    /** 値を文字で比べる順（`order` を持つ列はその並びの順、無ければ日本語の順） */
    function compareValues(column, a, b) {
        if (column.order) {
            const rank = (value) => {
                const index = column.order?.indexOf(value) ?? -1;
                return index < 0 ? (column.order?.length ?? 0) : index;
            };
            return rank(a) - rank(b);
        }
        return a.localeCompare(b, "ja");
    }
    /** 文字の条件のキー（`~{列}`）の頭 */
    MindmapPreview.TEXT_FILTER_PREFIX = "~";
    /** 条件ごとに合う行を返す（条件の中はどれかに当たればよく、条件の間は全てに当たる）。`~{列}` は文字の条件で、その列の値のどれかが文字を含む行に当てる（大文字・小文字を区別しない） */
    function filterRows({ rows, columns, filters, }) {
        const active = Object.entries(filters).filter(([, values]) => values.length > 0);
        return rows.filter((row) => active.every(([key, wanted]) => {
            const isText = key.startsWith(MindmapPreview.TEXT_FILTER_PREFIX);
            const columnKey = isText ? key.slice(MindmapPreview.TEXT_FILTER_PREFIX.length) : key;
            const column = columns.find((candidate) => candidate.key === columnKey);
            // 知らない列の条件は無視する
            if (column === undefined)
                return true;
            const values = valuesOf(column, row);
            if (!isText)
                return values.some((value) => wanted.includes(value));
            const needles = wanted.map((text) => text.toLowerCase());
            return values.some((value) => needles.some((needle) => value.toLowerCase().includes(needle)));
        }));
    }
    MindmapPreview.filterRows = filterRows;
    /** 表の列のうち、絞り込みのドロワーに文字の欄を出す列（値を選ぶ列と数の列を除く。列の順のまま） */
    function textColumns(columns) {
        return columns.filter((column) => column.filterable !== true && column.num !== true);
    }
    MindmapPreview.textColumns = textColumns;
    /** 列の値で行を並べ替える（元の配列は変えない。同じ値は元の順） */
    function sortRows({ rows, columns, sort, }) {
        if (sort === null)
            return [...rows];
        const column = columns.find((candidate) => candidate.key === sort.key);
        if (column === undefined)
            return [...rows];
        const direction = sort.dir === "asc" ? 1 : -1;
        const compare = (a, b) => {
            const x = column.get(a);
            const y = column.get(b);
            // 数値は数の順
            if (typeof x === "number" && typeof y === "number")
                return x - y;
            return compareValues(column, valuesOf(column, a).join(" "), valuesOf(column, b).join(" "));
        };
        return rows
            .map((row, position) => ({ row, position }))
            .sort((a, b) => direction * compare(a.row, b.row) || a.position - b.position)
            .map(({ row }) => row);
    }
    MindmapPreview.sortRows = sortRows;
    /** 条件の値ごとの件数を返す（その条件以外の条件で絞った行で数える） */
    function filterCounts({ rows, columns, filters, key, }) {
        const column = columns.find((candidate) => candidate.key === key);
        if (column === undefined)
            return [];
        const others = withoutKey(filters, key);
        const counts = new Map();
        // 選べる値は全ての行の値（件数が 0 のものも出す）
        for (const row of rows)
            for (const value of valuesOf(column, row))
                counts.set(value, 0);
        for (const row of filterRows({ rows, columns, filters: others })) {
            for (const value of valuesOf(column, row))
                counts.set(value, (counts.get(value) ?? 0) + 1);
        }
        return [...counts]
            .map(([value, count]) => ({ value, count }))
            .sort((a, b) => compareValues(column, a.value, b.value));
    }
    MindmapPreview.filterCounts = filterCounts;
    /** ドロワーの条件を並べるとき、先に置くキー（この順） */
    const LEADING_CONDITION_KEYS = ["kind", "type", "status", "tags"];
    /** 検討事項を開いたときの絞り込みの状態 */
    const DEFAULT_DECISION_STATUSES = ["要見直し", "未決定", "未整理", "保留"];
    /** 絞り込みから、1 つの条件を除いたものを返す */
    function withoutKey(filters, key) {
        return Object.fromEntries(Object.entries(filters).filter(([name]) => name !== key));
    }
    MindmapPreview.withoutKey = withoutKey;
    /** 絞り込みのドロワーに並べる条件と、条件ごとの値・件数を組む（キーワードに一致した件数を `hit` で添えられる） */
    function drawerGroups({ rows, columns, filters, hit, }) {
        const rank = (key) => {
            const position = LEADING_CONDITION_KEYS.indexOf(key);
            return position < 0 ? LEADING_CONDITION_KEYS.length : position;
        };
        const ordered = [...columns].sort((a, b) => rank(a.key) - rank(b.key));
        const groups = [];
        for (const column of ordered) {
            const counts = filterCounts({ rows, columns, filters, key: column.key });
            // 値を 1 つも持たない条件は並べない
            if (counts.length === 0)
                continue;
            // キーワードに一致した件数は、その条件以外の条件で絞った行で数える
            const others = hit === undefined ? [] : filterRows({ rows, columns, filters: withoutKey(filters, column.key) });
            groups.push({
                key: column.key,
                label: column.label,
                values: counts.map(({ value, count }) => hit === undefined
                    ? { value, count }
                    : {
                        value,
                        count,
                        hit: others.filter((row) => hit(row) && valuesOf(column, row).includes(value)).length,
                    }),
                ...(column.key === "status" ? { mark: "status" } : {}),
                ...(column.key === "type" ? { mark: "kind" } : {}),
            });
        }
        return groups;
    }
    MindmapPreview.drawerGroups = drawerGroups;
    /** 値を 1 つ以上選んでいる条件の数を返す（絞り込みのボタンのバッジ） */
    function activeConditionCount(filters) {
        return Object.values(filters).filter((values) => values.length > 0).length;
    }
    MindmapPreview.activeConditionCount = activeConditionCount;
    /** 画面を開いたときの絞り込みを返す。URL のハッシュの `f.{列}` があればそれだけ、無ければ端末に残した条件、それも無ければ画面の既定 */
    function initialFilters(tab, fromHash, saved) {
        if (Object.keys(fromHash).length > 0)
            return { ...fromHash };
        // 残した条件は、全て外した状態（空）でも画面の既定に戻さない
        if (saved !== null)
            return { ...saved };
        return tab === "decisions" ? { status: [...DEFAULT_DECISION_STATUSES] } : {};
    }
    MindmapPreview.initialFilters = initialFilters;
    /** 端末に残した条件から、今の記録のどの行にも無い値を外す。文字の条件（`~{列}`）はそのまま残し、知らない列の条件は外す（渡した条件は変えない） */
    function pruneFilters({ rows, columns, saved, }) {
        const pruned = {};
        for (const [key, values] of Object.entries(saved)) {
            // 文字の条件は記録の値ではないので、そのまま写す
            if (key.startsWith(MindmapPreview.TEXT_FILTER_PREFIX)) {
                pruned[key] = [...values];
                continue;
            }
            const column = columns.find((candidate) => candidate.key === key);
            // 知らない列の条件は外す
            if (column === undefined)
                continue;
            const present = new Set(rows.flatMap((row) => valuesOf(column, row)));
            const kept = values.filter((value) => present.has(value));
            // 値が 1 つも残らない列はキーごと外す
            if (kept.length > 0)
                pruned[key] = kept;
        }
        return pruned;
    }
    MindmapPreview.pruneFilters = pruneFilters;
    /** ポップオーバーを開いた元のボタンの上か下に置く（収まる側に開き、どちらも収まらないときは広い側で高さを抑える） */
    function positionPopover(pop, anchor) {
        const gap = 6;
        const margin = 8;
        const rect = anchor.getBoundingClientRect();
        pop.style.maxHeight = "";
        const { offsetWidth: width, offsetHeight: height } = pop;
        pop.style.left = `${Math.max(margin, Math.min(rect.left, innerWidth - width - margin))}px`;
        const below = innerHeight - rect.bottom - gap - margin;
        const above = rect.top - gap - margin;
        const openBelow = height <= below || (height > above && below >= above);
        const room = openBelow ? below : above;
        if (height > room)
            pop.style.maxHeight = `${room}px`;
        pop.style.top = `${openBelow ? rect.bottom + gap : rect.top - gap - pop.offsetHeight}px`;
    }
    MindmapPreview.positionPopover = positionPopover;
    /** 表の入れ物（スクロールする要素）ごとの、大きさの観察（描き直すたびに前の観察を止める） */
    const wrapObservers = new WeakMap();
    /** 表の項目の見出しのアイコン */
    function sortIcon(direction) {
        if (direction === "asc")
            return MindmapPreview.icon("up");
        if (direction === "desc")
            return MindmapPreview.icon("down");
        return MindmapPreview.h({ tag: "span", attrs: { class: "sort-hint" }, children: [MindmapPreview.icon("updown")] });
    }
    /** 項目の表を返す。操作は引数のコールバックで知らせ、描き直しは使う側が行う */
    function table(props) {
        return buildTable({ props, previous: null });
    }
    MindmapPreview.table = table;
    /** 選んでいる値を `{列}: {値}` のチップにし、× と「すべて解除」で条件の解除を知らせる行を返す（条件が無いときは中身の無い行） */
    function filterChips({ filters, labels, onFilter, }) {
        const items = [];
        for (const [key, values] of Object.entries(filters)) {
            // 文字の条件（`~{列}`）は、列の名前に「文字を含む」の文言を続けたチップにする
            if (key.startsWith(MindmapPreview.TEXT_FILTER_PREFIX)) {
                const columnKey = key.slice(MindmapPreview.TEXT_FILTER_PREFIX.length);
                const name = labels[columnKey] ?? columnKey;
                // 英数字で終わる列名の後ろには空白を挟む（「ID に」のように読めるように）
                const joint = /[A-Za-z0-9]$/.test(name) ? " " : "";
                for (const value of values) {
                    const text = `${name}${joint}に「${value}」を含む`;
                    items.push(MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "chip" },
                        children: [
                            text,
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    type: "button",
                                    "aria-label": `${text} の条件を解除`,
                                    onclick: () => onFilter(withoutKey(filters, key)),
                                },
                                children: [MindmapPreview.icon("x")],
                            }),
                        ],
                    }));
                }
                continue;
            }
            const label = labels[key] ?? key;
            for (const value of values) {
                items.push(MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "chip" },
                    children: [
                        `${label}: ${value}`,
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                type: "button",
                                "aria-label": `${label}: ${value} の条件を解除`,
                                onclick: () => {
                                    // 押した値を外し、値が残らない条件は key ごと消す
                                    const rest = values.filter((candidate) => candidate !== value);
                                    onFilter(rest.length === 0 ? withoutKey(filters, key) : { ...filters, [key]: rest });
                                },
                            },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }));
            }
        }
        if (items.length > 0) {
            items.push(MindmapPreview.h({
                tag: "button",
                attrs: { class: "btn ghost", type: "button", onclick: () => onFilter({}) },
                children: ["すべて解除"],
            }));
        }
        return MindmapPreview.h({ tag: "div", attrs: { class: "chips" }, children: items });
    }
    MindmapPreview.filterChips = filterChips;
    /** 表を組み立てる。previous があれば、その表の入れ物（スクロールする要素）を作り直さず、中身だけ差し替える */
    function buildTable({ props: { kind, columns, rows, sort = null, filters = {}, pinTo = null, hiddenColumns, popover = null, marks, comments, edit = null, addInTable = false, on, }, previous, }) {
        const hidden = new Set(hiddenColumns ?? columns.filter((column) => column.hidden).map((column) => column.key));
        const visible = columns.filter((column) => !hidden.has(column.key));
        // 固定する列の数（左端から pinTo の列まで）
        const pinned = pinTo === null ? 0 : visible.findIndex((column) => column.key === pinTo) + 1;
        const shownRows = sortRows({ rows: filterRows({ rows, columns, filters }), columns, sort });
        // 描き直しでは前の入れ物をそのまま使い、スクロールの位置を失わない
        const root = previous ?? MindmapPreview.h({ tag: "div", attrs: { class: "table-block", "data-kind": kind } });
        const wrap = previous?.querySelector(".table-wrap") ??
            MindmapPreview.h({ tag: "div", attrs: { class: "table-wrap" } });
        // ===== 条件のチップと、列の表示のボタン =====
        const chipsRow = filterChips({
            filters,
            labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
            onFilter: on.filter,
        });
        // ポップオーバーの題の要素の id（`aria-labelledby` が指す。置かれる画面の見出しの深さを知らないので、見出しの要素にはしない）
        const popTitleId = `pop-title-${kind}`;
        const pop = MindmapPreview.h({
            tag: "div",
            attrs: { class: "pop", popover: "auto", "aria-labelledby": popTitleId },
        });
        /** ポップオーバーの題 */
        const popoverTitle = (text) => MindmapPreview.h({ tag: "p", attrs: { class: "pop-title", id: popTitleId }, children: [text] });
        /** ポップオーバーの中身を作り、元のボタンの近くに開く */
        const showPopover = () => {
            pop.replaceChildren(columnsPopoverBody());
            if (!pop.matches(":popover-open"))
                pop.showPopover();
            const anchor = root.querySelector('[data-popover="columns"]');
            if (anchor !== null)
                positionPopover(pop, anchor);
        };
        /** 列の表示のポップオーバーの中身 */
        const columnsPopoverBody = () => {
            const boxes = columns.map((column) => MindmapPreview.h({
                tag: "label",
                children: [
                    MindmapPreview.h({
                        tag: "input",
                        attrs: {
                            type: "checkbox",
                            checked: !hidden.has(column.key),
                            disabled: column.fixed === true,
                            onchange: (event) => {
                                const checked = event.target.checked;
                                on.columns(checked
                                    ? [...hidden].filter((key) => key !== column.key)
                                    : [...hidden, column.key]);
                            },
                        },
                    }),
                    column.label,
                ],
            }));
            return MindmapPreview.h({
                tag: "div",
                children: [
                    popoverTitle("列の表示"),
                    ...boxes,
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "pop-foot" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "btn ghost",
                                    type: "button",
                                    onclick: () => {
                                        on.reset();
                                    },
                                },
                                children: ["列・並べ替え・固定を初期設定に戻す"],
                            }),
                        ],
                    }),
                ],
            });
        };
        // ポップオーバーを閉じたら、使う側にも知らせる（描き直しで消えたときは知らせない）
        pop.addEventListener("toggle", (event) => {
            if (event.newState === "closed" && pop.isConnected)
                on.popover?.(null);
        });
        /** ポップオーバーを開き、使う側にも知らせる */
        const openPopover = () => {
            showPopover();
            on.popover?.({ type: "columns" });
        };
        const toolbar = MindmapPreview.h({
            tag: "div",
            attrs: { class: "table-toolbar" },
            children: [
                chipsRow,
                edit !== null && addInTable ? MindmapPreview.addItemButton({ kind, onAdd: edit.onAdd }) : null,
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "btn cols-btn-table",
                        type: "button",
                        "data-popover": "columns",
                        "aria-label": "列の表示",
                        onclick: openPopover,
                    },
                    children: [
                        MindmapPreview.icon("cols"),
                        MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: ["列の表示"] }),
                    ],
                }),
            ],
        });
        // ===== 見出し =====
        const headers = visible.map((column, position) => {
            const direction = sort !== null && sort.key === column.key ? sort.dir : null;
            const isPinned = position === pinned - 1;
            return MindmapPreview.h({
                tag: "th",
                attrs: {
                    scope: "col",
                    class: [column.num ? "num" : "", position < pinned ? "pinned" : ""].join(" ").trim(),
                    "data-col": position,
                    "data-pri": column.priority ?? 1,
                    "aria-sort": direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none",
                    style: column.minWidth === undefined ? null : `min-width:${column.minWidth}`,
                },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "th-in" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "th-sort",
                                    type: "button",
                                    "data-sort": column.key,
                                    onclick: () => {
                                        on.sort(column.key);
                                    },
                                },
                                children: [column.label, sortIcon(direction)],
                            }),
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "th-tool pin",
                                    type: "button",
                                    "data-pin": column.key,
                                    "aria-pressed": String(isPinned),
                                    "aria-label": `${column.label}まで固定`,
                                    onclick: () => {
                                        on.pin(column.key);
                                    },
                                },
                                children: [MindmapPreview.icon("pin")],
                            }),
                        ],
                    }),
                ],
            });
        });
        // ===== 行 =====
        /** セルの中身 */
        const cellContent = (column, row, fresh) => {
            // 追加する項目の ID は保存で決まるので、ID の列は「—」にする
            if (fresh && column.key === "id")
                return MindmapPreview.h({ tag: "span", attrs: { class: "pe-noid" }, children: ["—"] });
            const content = column.cell?.(row) ?? valuesOf(column, row).join(column.num === true ? "" : "、");
            if (column.fixed !== true)
                return content;
            // タイトルの列は、押すと詳細を開くボタンにし、取り下げの札・差分の印があれば右に置く
            const opener = MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "row-open",
                    type: "button",
                    ...(fresh ? { "data-new-id": row.id } : { "data-id": row.id }),
                    onclick: () => on.open(row.id),
                },
                children: [fresh && row["title"] === "" ? "（タイトル未入力）" : content],
            });
            // 取り下げた行は、差分の表示によらず差分の印より前に札を置く
            const badge = row["withdrawn"] === true ? MindmapPreview.withdrawnBadge() : null;
            const mark = MindmapPreview.markFor({ marks, id: row.id });
            const editMark = fresh ? MindmapPreview.pendingEditMark({ kind: edit?.marks[row.id] ?? "pending" }) : MindmapPreview.editMarkOf({ edit, id: row.id });
            const commentPlaceElement = comments === undefined ? null : MindmapPreview.commentPlace({ id: row.id, count: comments[row.id] });
            if (badge === null && mark === null && editMark === null && commentPlaceElement === null)
                return opener;
            const fragment = document.createDocumentFragment();
            fragment.append(...[opener, badge, mark, editMark, commentPlaceElement].filter((node) => node !== null));
            return fragment;
        };
        /** 表の 1 行（追加する項目の行は破線の枠で、ID を持たない） */
        const tableRow = (row, fresh) => MindmapPreview.h({
            tag: "tr",
            attrs: {
                ...(fresh ? { "data-new-id": row.id } : { "data-id": row.id }),
                // 取り下げた行は文字を薄くする。削除を溜めた行は取り消し線を引く
                class: [
                    !fresh && row.id === MindmapPreview.currentSelection() ? "selected" : "",
                    row["withdrawn"] === true ? "is-withdrawn" : "",
                    fresh ? "pe-new" : "",
                    edit?.marks[row.id] === "remove" ? "pe-removing" : "",
                ]
                    .join(" ")
                    .trim(),
            },
            children: [
                ...visible.map((column, position) => MindmapPreview.h({
                    tag: "td",
                    attrs: {
                        "data-col": position,
                        "data-pri": column.priority ?? 1,
                        class: [
                            column.num ? "num" : "",
                            column.nowrap ? "nowrap" : "",
                            position < pinned ? "pinned" : "",
                        ]
                            .join(" ")
                            .trim(),
                    },
                    children: [cellContent(column, row, fresh)],
                })),
            ],
        });
        const addedRows = (edit?.adds ?? []).map((row) => tableRow(row, true));
        const body = shownRows.length > 0 || addedRows.length > 0
            ? [...addedRows, ...shownRows.map((row) => tableRow(row, false))]
            : [
                MindmapPreview.h({
                    tag: "tr",
                    children: [
                        MindmapPreview.h({
                            tag: "td",
                            attrs: { colspan: visible.length, class: "no-match-cell" },
                            children: [
                                MindmapPreview.h({
                                    tag: "div",
                                    attrs: { class: "no-match" },
                                    children: [`該当する${MindmapPreview.KIND_LABEL[kind]}はありません。別の条件を試してください。`],
                                }),
                            ],
                        }),
                    ],
                }),
            ];
        const grid = MindmapPreview.h({
            tag: "table",
            attrs: { class: "grid" },
            children: [
                MindmapPreview.h({ tag: "thead", children: [MindmapPreview.h({ tag: "tr", children: [...headers] })] }),
                MindmapPreview.h({ tag: "tbody", children: [...body] }),
            ],
        });
        if (previous === null) {
            wrap.append(grid);
            root.append(toolbar, wrap, pop);
        }
        else {
            // 描き直し: 入れ物（スクロールする要素）は残し、同じ回のうちに中身だけを差し替える
            root.querySelector(".table-toolbar")?.replaceWith(toolbar);
            wrap.replaceChildren(grid);
            root.querySelector(".pop")?.replaceWith(pop);
        }
        // ===== 配置: 固定した列の左端の位置・該当なしの文言の幅 =====
        wrapObservers.get(wrap)?.disconnect();
        const observer = new ResizeObserver(() => {
            wrap.style.setProperty("--wrap-w", `${wrap.clientWidth}px`);
            let left = 0;
            headers.forEach((header, position) => {
                if (position >= pinned)
                    return;
                for (const cell of wrap.querySelectorAll(`[data-col="${position}"]`)) {
                    cell.style.left = `${left}px`;
                    cell.classList.toggle("pin-edge", position === pinned - 1);
                }
                left += header.getBoundingClientRect().width;
            });
        });
        wrapObservers.set(wrap, observer);
        observer.observe(wrap);
        // 開いたままにするポップオーバーを、表が文書に入った後に開く
        if (popover !== null)
            queueMicrotask(showPopover);
        return root;
    }
    // ───── 画面が共通で使う列 ─────
    /** 行から文字の値を取る */
    function text(row, key) {
        const value = row[key];
        return typeof value === "string" ? value : undefined;
    }
    /** 行から文字の配列を取る */
    function texts(row, key) {
        const value = row[key];
        return Array.isArray(value) ? value.map((entry) => String(MindmapPreview.refTarget(entry))) : []; // 390: 関連の要素は `to`
    }
    /** 行の `tags` の名前（主題かどうかによらない） */
    function rowTagNames(row) {
        const value = row.tags;
        return Array.isArray(value) ? MindmapPreview.tagNames(value) : [];
    }
    /** 項目の ID を並べたセル（押すと詳細を開く）。無ければ「—」 */
    function idLinksCell(ids, open) {
        if (ids.length === 0)
            return MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["—"] });
        const fragment = document.createDocumentFragment();
        for (const id of ids) {
            fragment.append(MindmapPreview.h({
                tag: "button",
                attrs: { class: "idlink", type: "button", onclick: () => open(id) },
                children: [id],
            }));
        }
        return fragment;
    }
    MindmapPreview.idLinksCell = idLinksCell;
    /** どの表にもある列（ID・タイトル・状態・対象・カテゴリー・フェーズ・タグ）を作る関数の集まり */
    function commonColumns(settings) {
        return {
            id: {
                key: "id",
                label: "ID",
                nowrap: true,
                get: (row) => row.id,
                cell: (row) => MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [row.id] }),
            },
            title: (label = "タイトル") => ({
                key: "title",
                label,
                fixed: true,
                minWidth: "16em",
                get: (row) => text(row, "title"),
            }),
            status: (order) => ({
                key: "status",
                label: "状態",
                nowrap: true,
                filterable: true,
                order,
                get: (row) => text(row, "status"),
                cell: (row) => MindmapPreview.statusBadge(text(row, "status")),
            }),
            target: {
                key: "target",
                label: settings.target_label,
                nowrap: true,
                filterable: true,
                priority: 4,
                get: (row) => text(row, "target"),
            },
            category: {
                key: "category",
                label: "カテゴリー",
                nowrap: true,
                filterable: true,
                priority: 2,
                get: (row) => text(row, "category"),
            },
            phase: {
                key: "phase",
                label: "フェーズ",
                nowrap: true,
                filterable: true,
                order: settings.phases,
                priority: 2,
                get: (row) => text(row, "phase"),
            },
            tags: {
                key: "tags",
                label: "タグ",
                filterable: true,
                priority: 4,
                get: (row) => rowTagNames(row),
                cell: (row) => MindmapPreview.tagList(rowTagNames(row)),
            },
            text: (key, label, options = {}) => ({
                key,
                label,
                priority: 3,
                get: (row) => text(row, key),
                ...options,
            }),
        };
    }
    MindmapPreview.commonColumns = commonColumns;
    /** 行から文字の配列を取る（画面の列の定義で使う） */
    function rowTexts(row, key) {
        return texts(row, key);
    }
    MindmapPreview.rowTexts = rowTexts;
    /** 種類ごとの表の状態 */
    const tableStates = new Map();
    /** 表示する列とピン留めを変えたときの知らせ先（null は初期設定に戻したとき） */
    let prefsListener = null;
    /** 端末に残した表示する列とピン留めを入れ、変わったときの知らせ先を決める */
    function restoreTablePrefs(saved, listener) {
        prefsListener = listener;
        for (const [kind, prefs] of Object.entries(saved)) {
            const state = tableState(kind);
            state.hidden = prefs.hidden;
            state.pinTo = prefs.pinTo;
        }
    }
    MindmapPreview.restoreTablePrefs = restoreTablePrefs;
    /** どの表の表示する列とピン留めも初期設定に戻す（「既定に戻す」で個人の上書きを外すとき） */
    function clearTablePrefs() {
        for (const state of tableStates.values()) {
            state.hidden = undefined;
            state.pinTo = null;
        }
    }
    MindmapPreview.clearTablePrefs = clearTablePrefs;
    /** 種類の表の状態（無ければ作る） */
    function tableState(kind) {
        let state = tableStates.get(kind);
        if (state === undefined) {
            state = { sort: null, popover: null, hidden: undefined, pinTo: null };
            tableStates.set(kind, state);
        }
        return state;
    }
    MindmapPreview.tableState = tableState;
    /** 状態を持つ表を返す。並べ替え・列・ピン留めの操作は自分で描き直し、表示する列とピン留めは端末に残す。絞り込みの条件は画面から受け、チップで変えたときは `onFilter` に新しい条件を渡す */
    function managedTable({ kind, columns, rows, filters, onFilter, open, marks, comments, edit, addInTable, }) {
        const state = tableState(kind);
        // 画面を描き直したときは、前のポップオーバーを開いたままにしない
        state.popover = null;
        const slot = MindmapPreview.h({ tag: "div", attrs: { class: "table-slot" } });
        /** 端末に残す値が変わったことを知らせる */
        const persist = () => {
            prefsListener?.(kind, { hidden: state.hidden ?? [], pinTo: state.pinTo });
        };
        /** 今の表（描き直すとき、入れ物を残して中身だけ差し替える） */
        let current = null;
        const render = () => {
            const next = buildTable({
                previous: current,
                props: {
                    kind,
                    columns,
                    rows,
                    sort: state.sort,
                    filters,
                    pinTo: state.pinTo,
                    hiddenColumns: state.hidden,
                    popover: state.popover,
                    ...(marks === undefined ? {} : { marks }),
                    ...(comments === undefined ? {} : { comments }),
                    ...(edit === undefined ? {} : { edit }),
                    ...(addInTable === undefined ? {} : { addInTable }),
                    on: {
                        sort: (key) => {
                            // 昇順 → 降順 → 解除
                            if (state.sort === null || state.sort.key !== key)
                                state.sort = { key, dir: "asc" };
                            else
                                state.sort = state.sort.dir === "asc" ? { key, dir: "desc" } : null;
                            render();
                        },
                        filter: onFilter,
                        pin: (key) => {
                            state.pinTo = state.pinTo === key ? null : key;
                            persist();
                            render();
                        },
                        columns: (hidden) => {
                            state.hidden = hidden;
                            persist();
                            render();
                        },
                        reset: () => {
                            state.sort = null;
                            state.hidden = undefined;
                            state.pinTo = null;
                            state.popover = null;
                            prefsListener?.(kind, null);
                            render();
                        },
                        open,
                        popover: (popover) => {
                            state.popover = popover;
                        },
                    },
                },
            });
            // 初めて描くときだけ、表を差し込む（描き直しでは同じ表の中身が入れ替わる）
            if (current === null) {
                current = next;
                slot.replaceChildren(next);
            }
        };
        render();
        return slot;
    }
    MindmapPreview.managedTable = managedTable;
})(MindmapPreview || (MindmapPreview = {}));
// 絞り込みのドロワー。条件ごとに値を件数つきのチェックボックスで並べ、タブの帯の下から左に重ねる非モーダルのパネルとして開く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 次に描いたドロワーでフォーカスを移す先（操作した部品が描き直しで消えても、フォーカスを失わないために持つ） */
    let pendingFocus = null;
    /** 文字の欄の入力を条件に当てるまで待つミリ秒（打ち終えるのを待つ長さ）と、そのタイマー */
    MindmapPreview.TEXT_DELAY_MS = 250;
    let textTimer = 0;
    /** フォーカスを移す先を返す（文字の欄で打っていたときはその欄、初めて開くときは先頭の文字の欄、無ければ値のチェックボックス。見つからなければ最初の値） */
    function focusTargetOf({ drawer, focus }) {
        if (focus.kind === "text")
            return drawer.querySelector(`input[data-text-key="${focus.key}"]`);
        const firstText = drawer.querySelector(".fd-text input");
        if (focus.kind === "first" && firstText !== null)
            return firstText;
        const inputs = [...drawer.querySelectorAll(".fd-body input[data-key]")];
        const found = focus.kind === "value"
            ? inputs.find((input) => input.dataset["key"] === focus.key && input.value === focus.value)
            : focus.kind === "group"
                ? inputs.find((input) => input.dataset["key"] === focus.key)
                : undefined;
        return found ?? inputs[0] ?? null;
    }
    /** 値の左に添える印（状態の印か、項目の種類の色の点） */
    function valueMark({ mark, value }) {
        if (mark === "status")
            return MindmapPreview.statusMark(value);
        if (mark !== "kind")
            return null;
        const kind = MindmapPreview.KIND_KEYS.find((key) => MindmapPreview.KIND_LABEL[key] === value);
        if (kind === undefined)
            return null;
        return MindmapPreview.h({ tag: "span", attrs: { class: "kdot", style: `background:var(${MindmapPreview.KIND_COLOR_VAR[kind]})` } });
    }
    /** 条件 1 つ（見出し・選んだ数と「解除」・値の並び） */
    function conditionGroup({ group, chosen, on }) {
        const values = group.values.map(({ value, count, hit }) => MindmapPreview.h({
            tag: "li",
            children: [
                MindmapPreview.h({
                    tag: "label",
                    attrs: { class: count === 0 ? "fd-opt zero" : "fd-opt" },
                    children: [
                        MindmapPreview.h({
                            tag: "input",
                            attrs: {
                                type: "checkbox",
                                value,
                                "data-key": group.key,
                                checked: chosen.includes(value),
                                onchange: (event) => {
                                    const checked = event.target.checked;
                                    pendingFocus = { kind: "value", key: group.key, value };
                                    on.select({ key: group.key, value, checked });
                                },
                            },
                        }),
                        valueMark({ mark: group.mark, value }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "fd-v" }, children: [value] }),
                        hit !== undefined && hit > 0
                            ? MindmapPreview.h({ tag: "span", attrs: { class: "hit-n", "aria-label": `キーワードに一致した項目 ${hit} 件` }, children: [hit] })
                            : null,
                        MindmapPreview.h({ tag: "span", attrs: { class: "n", "aria-label": `${count} 件` }, children: [count] }),
                    ],
                }),
            ],
        }));
        // 選んだ数は、ここに並ぶ値のうち選んでいるものだけを数える（見えているチェックの数と合わせる）
        const checkedCount = group.values.filter(({ value }) => chosen.includes(value)).length;
        return MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "fd-group" },
            children: [
                MindmapPreview.h({
                    tag: "legend",
                    children: [
                        group.label,
                        checkedCount > 0 ? MindmapPreview.h({ tag: "span", attrs: { class: "fd-sel" }, children: [`${checkedCount} 件を選択`] }) : null,
                    ],
                }),
                checkedCount > 0
                    ? MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "btn ghost fd-clear",
                            type: "button",
                            "aria-label": `${group.label}の条件を解除`,
                            onclick: () => {
                                pendingFocus = { kind: "group", key: group.key };
                                on.clear(group.key);
                            },
                        },
                        children: ["解除"],
                    })
                    : null,
                MindmapPreview.h({ tag: "ul", attrs: { class: "fd-opts" }, children: values }),
            ],
        });
    }
    /** ドロワーの操作（値の選択・条件の解除・すべて解除）を、新しい条件を `onFilter` に渡す形にする */
    function drawerCallbacks({ filters, onFilter, onClose, }) {
        return {
            select: ({ key, value, checked }) => {
                const current = filters[key] ?? [];
                const next = checked ? [...current, value] : current.filter((candidate) => candidate !== value);
                onFilter(next.length === 0 ? MindmapPreview.withoutKey(filters, key) : { ...filters, [key]: next });
            },
            // 文字の条件を入れ替える（前後の空白を除き、空なら外す）
            text: ({ key, value }) => {
                const name = `${MindmapPreview.TEXT_FILTER_PREFIX}${key}`;
                const trimmed = value.trim();
                onFilter(trimmed === "" ? MindmapPreview.withoutKey(filters, name) : { ...filters, [name]: [trimmed] });
            },
            clear: (key) => onFilter(MindmapPreview.withoutKey(filters, key)),
            clearAll: () => onFilter({}),
            close: onClose,
        };
    }
    /** 絞り込みのドロワーの狭い幅の境（これ以下はトップバーの下から全幅で重ねる） */
    const DRAWER_NARROW_QUERY = "(max-width: 900px)";
    /** 画面が持つ条件と絞り込みの結果から、ドロワーを組む（開いていなければ null）。キーワードに一致した件数を添える画面は `hit` を、文字の欄を出す画面は `textColumns` を渡す */
    function screenDrawer({ drawerOpen, rows, columns, textColumns = [], filters, shown, hit, onFilter, onClose, }) {
        if (!drawerOpen)
            return null;
        // 値を選ぶ条件の件数は、文字の条件で絞った行で数える
        const textFilters = Object.fromEntries(Object.entries(filters).filter(([key]) => key.startsWith(MindmapPreview.TEXT_FILTER_PREFIX)));
        const valueFilters = Object.fromEntries(Object.entries(filters).filter(([key]) => !key.startsWith(MindmapPreview.TEXT_FILTER_PREFIX)));
        const narrowed = MindmapPreview.filterRows({ rows, columns: textColumns, filters: textFilters });
        return filterDrawer({
            groups: MindmapPreview.drawerGroups({ rows: narrowed, columns, filters: valueFilters, ...(hit === undefined ? {} : { hit }) }),
            texts: textColumns.map((column) => ({
                key: column.key,
                label: column.label,
                value: filters[`${MindmapPreview.TEXT_FILTER_PREFIX}${column.key}`]?.[0] ?? "",
            })),
            selected: filters,
            total: rows.length,
            shown,
            narrow: matchMedia(DRAWER_NARROW_QUERY).matches,
            on: drawerCallbacks({ filters, onFilter, onClose }),
        });
    }
    MindmapPreview.screenDrawer = screenDrawer;
    /** 絞り込みのドロワーを返す。文書に入った後に非モーダルで開き、描き直しても中のスクロールの位置と押した値へのフォーカスを保つ */
    function filterDrawer({ groups, texts = [], selected, total, shown, narrow, on }) {
        // 描き直す前のドロワー（あれば、スクロールの位置とフォーカスを引き継ぐ）
        const previous = document.querySelector("dialog.drawer");
        const scrollTop = previous?.querySelector(".fd-body")?.scrollTop ?? 0;
        const before = document.activeElement;
        // 操作で決めたフォーカス先。無ければ、前のドロワーで値にあったフォーカスを同じ値へ戻す。初めて開くときは最初の値
        let focus = pendingFocus;
        pendingFocus = null;
        if (focus === null && previous !== null && before instanceof HTMLInputElement && previous.contains(before) && before.dataset["key"] !== undefined) {
            focus = { kind: "value", key: before.dataset["key"], value: before.value };
        }
        if (focus === null && previous === null)
            focus = { kind: "first" };
        const filtering = MindmapPreview.activeConditionCount(selected) > 0;
        // 値を選ぶ条件より上に、文字で絞れる列ごとの欄を並べる
        const textGroup = texts.length === 0
            ? null
            : MindmapPreview.h({
                tag: "fieldset",
                attrs: { class: "fd-group fd-text" },
                children: [
                    MindmapPreview.h({ tag: "legend", children: ["文字を含む"] }),
                    ...texts.map((text) => {
                        const inputId = `fd-text-${text.key}`;
                        return MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "fd-text-row" },
                            children: [
                                MindmapPreview.h({ tag: "label", attrs: { for: inputId }, children: [text.label] }),
                                MindmapPreview.h({
                                    tag: "input",
                                    attrs: {
                                        id: inputId,
                                        type: "search",
                                        value: text.value,
                                        autocomplete: "off",
                                        "data-text-key": text.key,
                                        // 打ち終えて少し待ってから当てる（描き直した後も、同じ欄の同じ位置に戻る）
                                        oninput: (event) => {
                                            const input = event.target;
                                            window.clearTimeout(textTimer);
                                            textTimer = window.setTimeout(() => {
                                                pendingFocus = { kind: "text", key: text.key, caret: input.selectionStart ?? input.value.length };
                                                on.text({ key: text.key, value: input.value });
                                            }, MindmapPreview.TEXT_DELAY_MS);
                                        },
                                    },
                                }),
                            ],
                        });
                    }),
                ],
            });
        const body = MindmapPreview.h({
            tag: "div",
            attrs: { class: "fd-body" },
            children: [textGroup, ...groups.map((group) => conditionGroup({ group, chosen: selected[group.key] ?? [], on }))],
        });
        const drawer = MindmapPreview.h({
            tag: "dialog",
            attrs: {
                id: "drawer",
                class: narrow ? "drawer narrow" : "drawer",
                closedby: "none",
                "aria-labelledby": "drawer-title",
            },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "fd-top" },
                    children: [
                        MindmapPreview.h({ tag: "p", attrs: { class: "fd-title", id: "drawer-title" }, children: ["絞り込み"] }),
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "fd-count", "aria-live": "polite" },
                            children: [filtering ? `${total} 件中 ${shown} 件` : `${total} 件`],
                        }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "絞り込みを閉じる", onclick: on.close },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                body,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "fd-foot" },
                    children: [
                        filtering
                            ? MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "btn ghost",
                                    type: "button",
                                    onclick: () => {
                                        pendingFocus = { kind: "first" };
                                        on.clearAll();
                                    },
                                },
                                children: ["すべて解除"],
                            })
                            : null,
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn primary", type: "button", onclick: on.close },
                            children: [`${shown} 件を表示`],
                        }),
                    ],
                }),
            ],
        });
        // ドロワーの中の Esc で閉じる（ほかの Esc の処理には渡さない）
        drawer.addEventListener("keydown", (event) => {
            if (event.key !== "Escape")
                return;
            event.preventDefault();
            event.stopPropagation();
            on.close();
        });
        // 文書に入った後に、幕を付けずに開く（開くとフォーカスが動くので、移す先を決め直す）
        queueMicrotask(() => {
            if (!drawer.isConnected)
                return;
            if (!drawer.open)
                drawer.show();
            // 指す先ができたので、トップバーの絞り込みのボタンから指す（ボタンはドロワーより先に描かれている）
            document.querySelector("[data-act='filter']")?.setAttribute("aria-controls", "drawer");
            body.scrollTop = scrollTop;
            const target = focus === null ? null : focusTargetOf({ drawer, focus });
            if (target !== null) {
                target.focus();
                // 文字の欄は、打っていた位置にカーソルを戻す
                if (focus?.kind === "text")
                    target.setSelectionRange(focus.caret, focus.caret);
            }
            else if (previous !== null && before instanceof HTMLElement && before.isConnected && !previous.contains(before)) {
                // 本文などにあったフォーカスは、開き直しで奪わない
                before.focus();
            }
        });
        return drawer;
    }
    MindmapPreview.filterDrawer = filterDrawer;
})(MindmapPreview || (MindmapPreview = {}));
// コメントの入力。詳細パネルと詳細の全画面の下端と、コメントの一覧の下端に留める、コメントをレビュー中に溜める入力欄と「レビューに追加」のボタン。選んだ箇所を添えられ、溜めた結果を入力の近くに出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 溜めている印と文言を出すまでの待ち（ミリ秒）。すぐ終わる処理では点滅させない */
    const SENDING_NOTICE_DELAY_MS = 1000;
    /** 項目を指さないコメントの入力欄の読み上げの名前 */
    const NO_TARGET_LABEL = "項目を指さないコメント";
    /** 入力欄の ID に付ける連番（同じ文書に複数置いても ID が重ならないように） */
    let sendFormSequence = 0;
    /** UTC のタイムゾーン付き ISO 8601 を JST の `MM/DD HH:mm` にする */
    function formatJst(iso) {
        const parts = new Intl.DateTimeFormat("ja-JP", {
            timeZone: "Asia/Tokyo",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
        }).formatToParts(new Date(iso));
        const part = (type) => parts.find((entry) => entry.type === type)?.value ?? "";
        return `${part("month")}/${part("day")} ${part("hour")}:${part("minute")}`;
    }
    MindmapPreview.formatJst = formatJst;
    /** 結果の要素の中身（状態ごとの印と文言） */
    function resultContent({ status, count, detail, onCopy, }) {
        if (status === "saved") {
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`レビューに追加しました（レビュー中 ${count ?? 0} 件）。`] })];
        }
        if (status === "empty") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: ["コメントを入れてから追加してください。"] })];
        }
        if (status === "failed") {
            // サーバーが理由を返した: 理由を出す
            if (detail !== null && detail !== undefined) {
                return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`レビューに追加できませんでした。${detail}`] })];
            }
            // サーバーに届かなかった: 立ち上げ直すと URL が変わり、書きかけは引き継がれないので、本文を写す手段を添える
            return [
                MindmapPreview.icon("alert"),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "send-msg-body" },
                    children: [
                        MindmapPreview.h({
                            tag: "span",
                            children: [
                                "レビューに追加できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから追加してください。",
                            ],
                        }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn ghost send-copy", type: "button", onclick: onCopy },
                            children: [MindmapPreview.icon("copy"), "本文を写す"],
                        }),
                    ],
                }),
            ];
        }
        return [];
    }
    /** 添えた箇所（名前・選んだ文・外す ×）の要素 */
    function locationChip({ loc, id, onUnquote }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "send-loc", id },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "send-loc-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "send-loc-name" }, children: [MindmapPreview.locationLabel(loc)] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn send-unquote", type: "button", "aria-label": "箇所を外す", title: "箇所を外す", onclick: onUnquote },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                MindmapPreview.h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [loc.text] }),
            ],
        });
    }
    /** 項目へのコメントをレビュー中に溜める入力欄と「レビューに追加」のボタン、結果を返す */
    function sendForm({ target, loc = null, body = "", status = "idle", count = null, detail = null, collapsed = false, label = NO_TARGET_LABEL, on, }) {
        sendFormSequence += 1;
        const fieldId = `send-${sendFormSequence}`;
        const messageId = `${fieldId}-msg`;
        const locId = `${fieldId}-loc`;
        /** 畳むのは、項目を指さない入力だけ */
        const folded = collapsed && target === null;
        /** 溜めている間は溜めない。それ以外は入力欄の中身そのままを渡す */
        const trySave = () => {
            if (status === "saving")
                return;
            on.save(textarea.value);
        };
        const textarea = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                id: fieldId,
                name: "body",
                rows: 1,
                "aria-label": target === null ? label : null,
                "aria-describedby": folded ? null : target !== null && loc !== null ? `${locId} ${messageId}` : messageId,
                "aria-keyshortcuts": "Control+Enter",
                // 溜めている間は書き換えられない
                readonly: status === "saving",
                // 本文が空で溜めようとした: 入力の誤りとして示す
                "aria-invalid": status === "empty" ? "true" : null,
                oninput: () => on.input(textarea.value),
                onfocus: () => on.focus(),
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では溜めない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        trySave();
                    }
                },
            },
            children: [body],
        });
        const message = MindmapPreview.h({
            tag: "p",
            attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" },
            children: resultContent({ status, count, detail, onCopy: () => on.copy(textarea.value) }),
        });
        // 溜めている印と文言は、待ちの後に入れる
        if (status === "saving") {
            window.setTimeout(() => {
                message.replaceChildren(MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["レビューに追加しています"] }));
            }, SENDING_NOTICE_DELAY_MS);
        }
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: `send send-footer${folded ? " collapsed" : ""}`,
                novalidate: true,
                "data-id": target,
                onsubmit: (event) => {
                    event.preventDefault();
                    trySave();
                },
                onfocusout: (event) => {
                    // フォーカスが部品の外へ出たときだけ知らせる
                    const next = event.relatedTarget;
                    if (next === null || !form.contains(next))
                        on.blur();
                },
            },
            children: [
                target === null
                    ? null
                    : MindmapPreview.h({
                        tag: "label",
                        attrs: { class: "send-label", for: fieldId },
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] }), " へのコメント"],
                    }),
                target !== null && loc !== null ? locationChip({ loc, id: locId, onUnquote: on.unquote }) : null,
                textarea,
                folded
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "send-row" },
                        children: [
                            message,
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "btn primary",
                                    type: "submit",
                                    title: "レビューに追加（Ctrl+Enter）",
                                    disabled: status === "saving",
                                },
                                children: [MindmapPreview.icon("comment"), "レビューに追加"],
                            }),
                        ],
                    }),
            ],
        });
        return form;
    }
    MindmapPreview.sendForm = sendForm;
})(MindmapPreview || (MindmapPreview = {}));
// 返信の入力。スレッドの下端に留める、返信をレビュー中に溜める入力欄と「レビューに追加」のボタン。
var MindmapPreview;
(function (MindmapPreview) {
    /** 入力欄の ID に付ける連番（同じ文書に複数置いても ID が重ならないように） */
    let replyFormSequence = 0;
    /** 結果の要素の中身（状態ごとの印と文言） */
    function replyResult({ status, count, detail }) {
        if (status === "saving") {
            return [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["レビューに追加しています"] })];
        }
        if (status === "saved") {
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`レビューに追加しました（レビュー中 ${count ?? 0} 件）。`] })];
        }
        if (status === "failed") {
            const reason = detail === null || detail === undefined
                ? "サーバーが止まっています。立ち上げ直してから追加してください。"
                : detail;
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`レビューに追加できませんでした。${reason}`] })];
        }
        return [];
    }
    /** 返信をレビュー中に溜める入力欄と「レビューに追加」のボタン、結果を返す */
    function replyForm({ thread, body = "", status = "idle", count = null, detail = null, on }) {
        replyFormSequence += 1;
        const fieldId = `reply-${replyFormSequence}`;
        const messageId = `${fieldId}-msg`;
        const saving = status === "saving";
        /** 空白だけの間と溜めている間は溜めない。それ以外は入力欄の中身そのままを渡す */
        const trySave = () => {
            if (saving || textarea.value.trim() === "")
                return;
            on.save(thread, textarea.value);
        };
        const textarea = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                id: fieldId,
                name: "body",
                rows: 1,
                maxlength: MindmapPreview.COMMENT_BODY_MAX_LENGTH,
                "aria-keyshortcuts": "Control+Enter",
                "aria-describedby": messageId,
                // 溜めている間は書き換えられない
                readonly: saving,
                oninput: () => {
                    on.input(textarea.value);
                    // 入力に合わせて、ボタンを押せるかを合わせる
                    submit.disabled = saving || textarea.value.trim() === "";
                },
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では溜めない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        trySave();
                    }
                    // Esc は入力から外れるだけにする（使う側の「一覧へ戻る」へ伝えない）
                    if (key.key === "Escape") {
                        key.preventDefault();
                        key.stopPropagation();
                        textarea.blur();
                    }
                },
            },
            children: [body],
        });
        const submit = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn primary",
                type: "submit",
                title: "レビューに追加（Ctrl+Enter）",
                "data-focus": "reply-send",
                disabled: saving || body.trim() === "",
            },
            children: [MindmapPreview.icon("comment"), "レビューに追加"],
        });
        return MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "send send-footer reply",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    trySave();
                },
            },
            children: [
                MindmapPreview.h({ tag: "label", attrs: { class: "send-label", for: fieldId }, children: ["返信"] }),
                textarea,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "send-row" },
                    children: [
                        MindmapPreview.h({ tag: "p", attrs: { class: status === "idle" ? "send-msg" : `send-msg ${status}`, id: messageId, role: "status" }, children: replyResult({ status, count, detail }) }),
                        submit,
                    ],
                }),
            ],
        });
    }
    MindmapPreview.replyForm = replyForm;
})(MindmapPreview || (MindmapPreview = {}));
// スレッドの行。スレッドの一覧に並べる 1 件で、状態の札・題・向けた項目・最後の書き手と日時・レビュー中の印・タグを出し、押すとそのスレッドを開く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 書き手の呼び名 */
    MindmapPreview.AUTHOR_LABELS = { user: "あなた", ai: "AI" };
    /** 状態の札の印と文言 */
    const STATE_LABELS = {
        open: { icon: "changed", label: "オープン" },
        closed: { icon: "check", label: "クローズ" },
        pending: { icon: "edit", label: "レビュー中" },
    };
    /** 本文の 1 行目 */
    function firstLine(body) {
        return body.split("\n")[0];
    }
    /** 行と見出しに出す題（要約。まだ無ければ最初の書き込みの 1 行目） */
    function threadTitle(thread) {
        return thread.summary ?? firstLine(thread.posts[0].body);
    }
    MindmapPreview.threadTitle = threadTitle;
    /** 状態の札（色に加えて印と文字で区別する） */
    function threadState(status) {
        const { icon: name, label } = STATE_LABELS[status];
        return MindmapPreview.h({ tag: "span", attrs: { class: `th-state ${status}` }, children: [MindmapPreview.icon(name), label] });
    }
    MindmapPreview.threadState = threadState;
    /** レビュー中の印（レビュー中の返信を持つスレッドの行と、スレッドの中のレビュー中の書き込みに出す） */
    function pendingMark() {
        return MindmapPreview.h({ tag: "span", attrs: { class: "th-pending" }, children: [MindmapPreview.icon("edit"), "レビュー中"] });
    }
    MindmapPreview.pendingMark = pendingMark;
    /** 利用者の未読の書き込み（`seen` が偽）を持つか。`seen` を持たない書き込みは未読にしない */
    function hasUnseen(thread) {
        return thread.posts.some((post) => post.seen === false);
    }
    MindmapPreview.hasUnseen = hasUnseen;
    /** トップバーの未読の点に渡す値（オープンのスレッドに利用者の未読があるか。クローズの未読は数えない） */
    function anyOpenUnseen(threads) {
        return threads.some((thread) => thread.status === "open" && hasUnseen(thread));
    }
    MindmapPreview.anyOpenUnseen = anyOpenUnseen;
    /** 指したスレッドの書き込みを全て既読にした新しい並び（渡した並びは書き換えない。ID が無ければ同じ中身の並び） */
    function withSeen({ threads, id }) {
        return threads.map((thread) => thread.id === id ? { ...thread, posts: thread.posts.map((post) => ({ ...post, seen: true })) } : thread);
    }
    MindmapPreview.withSeen = withSeen;
    /** 未読の札（塗りつぶしの形・点の印・「未読」の文字で示す。状態の札の線の枠、レビュー中の印の破線の枠と形で見分ける） */
    function unseenMark() {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "th-unread" },
            children: [MindmapPreview.h({ tag: "span", attrs: { class: "dot", "aria-hidden": "true" } }), "未読"],
        });
    }
    /** タグの札（行を開くボタンとは別のボタン。押すとそのタグで絞る） */
    function tagButton({ thread, tag, active, onTag }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `th-tag${active ? " on" : ""}`,
                type: "button",
                "aria-pressed": String(active),
                "aria-label": `タグ「${tag}」で絞る`,
                "data-focus": `tag:${thread.id}:${tag}`,
                onclick: () => onTag(tag),
            },
            children: [MindmapPreview.icon("hash"), tag],
        });
    }
    /** スレッドの行（`li`）を返す。送ったスレッドと、まだ送っていない新しいスレッドのどちらも同じ形で描く */
    function threadRow({ thread = null, pending = null, hasPendingReply = false, activeTag = null, on }) {
        const last = thread === null ? null : thread.posts[thread.posts.length - 1];
        const sent = thread !== null && last !== null;
        const id = sent ? thread.id : (pending?.id ?? "");
        const target = sent ? thread.target : (pending?.target ?? null);
        const author = sent ? last.author : "user";
        const created = sent ? last.created : (pending?.created ?? "");
        const title = sent ? threadTitle(thread) : firstLine(pending?.body ?? "");
        const summarized = sent && thread.summary !== null;
        const status = sent ? thread.status : "pending";
        const unseen = sent && hasUnseen(thread);
        // 未読の行は、読み上げの名前が状態の次に「未読」を読む
        const openLabel = unseen
            ? [STATE_LABELS[status].label, "未読", title, target, MindmapPreview.AUTHOR_LABELS[author], MindmapPreview.formatJst(created), hasPendingReply ? "レビュー中の返信あり" : null]
                .filter((part) => part !== null)
                .join("、")
            : null;
        return MindmapPreview.h({
            tag: "li",
            attrs: sent ? { class: `th-row${unseen ? " unread" : ""}`, "data-thread": id } : { class: "th-row pending", "data-pending": id },
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "th-open",
                        type: "button",
                        "aria-label": openLabel,
                        "data-focus": sent ? `thread:${id}` : `thread:new:${id}`,
                        onclick: () => on.open(id, !sent),
                    },
                    children: [
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "th-line1" },
                            children: [threadState(status), MindmapPreview.h({ tag: "span", attrs: { class: `th-title${summarized ? "" : " head"}` }, children: [title] })],
                        }),
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "th-line2" },
                            children: [
                                unseen ? unseenMark() : null,
                                target === null ? null : MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "th-author" }, children: [MindmapPreview.AUTHOR_LABELS[author]] }),
                                MindmapPreview.h({ tag: "time", attrs: { datetime: created }, children: [MindmapPreview.formatJst(created)] }),
                                hasPendingReply ? pendingMark() : null,
                            ],
                        }),
                    ],
                }),
                !sent || thread.tags.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "th-tags" },
                        children: thread.tags.map((tag) => tagButton({ thread, tag, active: tag === activeTag, onTag: on.tag })),
                    }),
            ],
        });
    }
    MindmapPreview.threadRow = threadRow;
})(MindmapPreview || (MindmapPreview = {}));
// スレッドの書き込み。スレッドの中に書いた順で並べる 1 件で、利用者と AI の書き込み・クローズとオープンへの戻しの記録・レビュー中の書き込みのどれか 1 つを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 本文の中の項目の ID（例 D-1・T-12・A-3） */
    const ITEM_ID_PATTERN = /\b[A-Z]{1,2}-\d+\b/g;
    /** 項目の ID をボタンにしない文字の置き場所（コード・リンク・ボタン・図・HTML の本文の枠の中） */
    const ITEM_ID_SKIPPED = `pre, code, a, button, figure.diagram, .${MindmapPreview.HTML_BLOCK_CLASS}`;
    /** 描いた本文の中の `#` で始まるリンクのうち、記録にあるまとまりを指すもの（`diff` の値を `changeSets` で引けたもの）をまとまりのリンクにし、それ以外は中の文字に置き換える。押したときは既定の動作を止め、まとまりの ID を `onChangeSet` に知らせる。`#` で始まらないリンクは触らない */
    function linkChangeSets({ root, changeSets, onChangeSet, }) {
        for (const link of root.querySelectorAll("a")) {
            const href = link.getAttribute("href") ?? "";
            if (!href.startsWith("#"))
                continue;
            // `diff` だけを読む（他の引数は無視する）
            const set = new URLSearchParams(href.slice(1)).get("diff");
            const summary = set === null ? null : changeSets(set);
            // 記録にあるまとまりを指さないリンクは、リンクにせず文言だけを出す
            if (set === null || summary === null) {
                link.replaceWith(...link.childNodes);
                continue;
            }
            link.className = "setlink";
            link.setAttribute("href", `#${new URLSearchParams({ diff: set }).toString()}`);
            link.title = summary;
            link.setAttribute("data-focus", `post-set:${set}`);
            link.addEventListener("click", (event) => {
                // ハッシュの書き換えは使う側に任せる
                event.preventDefault();
                onChangeSet(set);
            });
        }
    }
    /** 描いた本文の文字のうち、記録にある項目の ID を、その項目を開くボタンにする（コード・リンク・ボタン・図・HTML の本文の枠の中は飛ばす。記録に無い ID とスレッドの ID は文字のまま） */
    function buttonizeItemIds({ root, titles, onOpen, }) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => (node.parentElement?.closest(ITEM_ID_SKIPPED) !== null ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        for (const node of nodes) {
            const text = node.textContent ?? "";
            const parts = [];
            let last = 0;
            for (const match of text.matchAll(ITEM_ID_PATTERN)) {
                const title = titles(match[0]);
                // 記録に無い ID（スレッドの ID を含む）は文字のまま残す
                if (title === null)
                    continue;
                parts.push(text.slice(last, match.index), MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "idlink", type: "button", title, "data-focus": `post-id:${match[0]}`, onclick: () => onOpen(match[0]) },
                    children: [match[0]],
                }));
                last = match.index + match[0].length;
            }
            if (parts.length === 0)
                continue;
            parts.push(text.slice(last));
            node.replaceWith(...parts.filter((part) => part !== ""));
        }
    }
    /** 本文を、段落の中の改行を強制改行にして Markdown として描いた要素（項目の ID はその項目を開くボタン、記録にあるまとまりを指すリンクはまとまりのリンク）。mdmark が読めないときは、本文を文字のまま改行を保って持つ要素 */
    function postBody({ body, titles, changeSets, className, on, }) {
        // 読めない: 知らせは出さず、項目の ID とまとまりのリンクも作らない
        if (MindmapPreview.missingLibraries(["mdmark"]).length > 0)
            return MindmapPreview.h({ tag: "p", attrs: { class: className }, children: [body] });
        const root = MindmapPreview.withoutLineMarks(MindmapPreview.renderMarkdown(MindmapPreview.withHardBreaks(body)));
        root.classList.add(className);
        // 図は描き終えるのを待たずに返す
        void MindmapPreview.renderDiagrams(root);
        for (const block of root.querySelectorAll(`.${MindmapPreview.HTML_BLOCK_CLASS}`)) {
            const frame = MindmapPreview.htmlBodyFrame({ source: block.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "", selectable: false, label: "html のコードブロック" });
            frame.classList.add(MindmapPreview.HTML_BLOCK_CLASS);
            block.replaceWith(frame);
        }
        MindmapPreview.decorateMarkdown({ root, fold: false, tables: false });
        linkChangeSets({ root, changeSets, onChangeSet: on.changeSet });
        buttonizeItemIds({ root, titles, onOpen: on.openId });
        return root;
    }
    MindmapPreview.postBody = postBody;
    /** 状態の記録（枠の無い 1 行に、書き手・したこと・日時と、あれば理由） */
    function eventItem(event) {
        const closed = event.kind === "closed";
        const who = event.author === "ai" ? "AI が" : "あなたが";
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: `th-event ${event.author}`, "data-event": event.kind },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "th-event-line" },
                    children: [
                        MindmapPreview.icon(closed ? "check" : "undo"),
                        MindmapPreview.h({ tag: "span", children: [`${who}${closed ? "クローズにしました" : "オープンに戻しました"}`] }),
                        MindmapPreview.h({ tag: "time", attrs: { datetime: event.created }, children: [MindmapPreview.formatJst(event.created)] }),
                    ],
                }),
                event.reason === null ? null : MindmapPreview.h({ tag: "p", attrs: { class: "th-event-reason" }, children: [event.reason] }),
            ],
        });
    }
    /** レビュー中の書き込み（破線の枠と「レビュー中」の印を付け、右上に「修正」「削除」を置く） */
    function pendingItem({ item, titles, changeSets, editing, editBody, editError, on, }) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "post user pending", "data-comment": item.id },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "post-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "post-author" }, children: [MindmapPreview.AUTHOR_LABELS.user] }),
                        MindmapPreview.pendingMark(),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        editing ? null : MindmapPreview.reviewRowActions({ item, focus: "", on: { edit: on.edit, remove: on.remove } }),
                    ],
                }),
                editing
                    ? MindmapPreview.reviewEditForm({ item, body: editBody, error: editError, focus: "", on: { saveEdit: on.saveEdit, cancelEdit: on.cancelEdit } })
                    : postBody({ body: item.body, titles, changeSets, className: "post-body", on: { openId: on.openId, changeSet: on.changeSet } }),
            ],
        });
    }
    /** スレッドの書き込み・状態の記録・レビュー中の書き込みのどれか 1 つの `li` を返す */
    function threadPost({ post = null, event = null, pending = null, titles = () => null, changeSets = () => null, editing = false, editBody = null, editError = null, on, }) {
        // 状態の記録
        if (event !== null)
            return eventItem(event);
        // レビュー中の書き込み
        if (pending !== null)
            return pendingItem({ item: pending, titles, changeSets, editing, editBody, editError, on });
        // 書き込みが無い（渡し方の誤り）
        if (post === null)
            throw new Error("threadPost には post・event・pending のどれか 1 つを渡す");
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: `post ${post.author}` },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "post-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "post-author" }, children: [MindmapPreview.AUTHOR_LABELS[post.author]] }),
                        MindmapPreview.h({ tag: "time", attrs: { datetime: post.created }, children: [MindmapPreview.formatJst(post.created)] }),
                    ],
                }),
                postBody({ body: post.body, titles, changeSets, className: "post-body", on: { openId: on.openId, changeSet: on.changeSet } }),
            ],
        });
    }
    MindmapPreview.threadPost = threadPost;
})(MindmapPreview || (MindmapPreview = {}));
// レビュー中の書き込みの本文の折りたたみ。折り返した後の見た目の行で一定の行数までに本文を畳み、超えるときだけ開閉のボタンを出す。本文の要素と開閉のボタンを別々に返し、ボタンの置き場所は使う側が決める。
var MindmapPreview;
(function (MindmapPreview) {
    /** 畳んだときに出す、折り返した後の見た目の行の数 */
    MindmapPreview.REVIEW_FOLD_LINES = 5;
    /** 全文の高さが、行の高さ × 行数を超えたとみなす余裕（小数の丸め） */
    const FOLD_TOLERANCE_PX = 1;
    /** 開閉のボタンの文言・矢印・読み上げの名前を、開いているかに合わせる */
    function setToggle({ more, open, label }) {
        more.setAttribute("aria-expanded", String(open));
        more.setAttribute("aria-label", open ? `${label}の本文を折りたたむ` : `${label}の続きを読む`);
        more.replaceChildren(MindmapPreview.icon("chev"), MindmapPreview.h({ tag: "span", children: [open ? "折りたたむ" : "続きを読む"] }));
    }
    /** 全文が畳む行の数を超えるか */
    function exceedsLines({ body, lines }) {
        const lineHeight = parseFloat(getComputedStyle(body).lineHeight);
        // 畳んでいても scrollHeight は全文の高さを返す
        return body.scrollHeight > lineHeight * lines + FOLD_TOLERANCE_PX;
    }
    /** 本文を畳み、開閉のボタンを添えて返す */
    function reviewBodyFold({ id, label, body, changeSets = () => null, open = false, lines = MindmapPreview.REVIEW_FOLD_LINES, on }) {
        const bodyId = `review-body-${id}`;
        const text = MindmapPreview.postBody({
            body,
            titles: () => null,
            changeSets,
            className: "review-body",
            // 項目の ID は文字のまま出すので、押されることは無い
            on: { openId: () => undefined, changeSet: on.changeSet },
        });
        text.id = bodyId;
        text.style.setProperty("--fold-lines", String(lines));
        let opened = open;
        const more = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn ghost review-more",
                type: "button",
                // 測るまでは出さない
                hidden: true,
                "aria-controls": bodyId,
                "data-focus": `more:${id}`,
                onclick: () => {
                    opened = !opened;
                    text.classList.toggle("folded", !opened);
                    setToggle({ more, open: opened, label });
                    // 折りたたんだ行が画面から外れないように寄せる
                    if (!opened)
                        text.closest("li")?.scrollIntoView({ block: "nearest" });
                    on.toggle(id, opened);
                },
            },
        });
        setToggle({ more, open: opened, label });
        // 超えるときだけ畳んで開閉のボタンを出す
        const measure = () => {
            const exceeds = exceedsLines({ body: text, lines });
            text.classList.toggle("folded", exceeds && !opened);
            more.hidden = !exceeds;
        };
        // 描いた直後は、描画の前のフレームで測る
        requestAnimationFrame(measure);
        // 本文の幅が変わると折り返しが変わる。通知の中で本文の高さを変えると通知を送りきれないので、次のフレームで測り直す
        new ResizeObserver(() => requestAnimationFrame(measure)).observe(text);
        return { body: text, more };
    }
    MindmapPreview.reviewBodyFold = reviewBodyFold;
})(MindmapPreview || (MindmapPreview = {}));
// 選んだ箇所のコメントの入口。本文の文章か項目の値を選び終えたときに、選んだ範囲の近くに出す印だけの丸いボタン。
var MindmapPreview;
(function (MindmapPreview) {
    /** 入口の大きさ（位置を決めるため固定する）。押せる的は高さ 32px 以上 */
    const BUTTON_SIZE = 32;
    /** 選んだ範囲との間の空きと、画面の端から内側に収める幅 */
    const BUTTON_GAP = 6;
    const SCREEN_EDGE = 8;
    /** 入口の名前（読み上げとツールチップ） */
    const BUTTON_NAME = "選んだ箇所にコメント";
    /** 入口を返す。選んだ範囲の始まりの上に出し、上に収まらなければ終わりの下に出す。左右は画面の端から内側に収める */
    function selectionComment({ anchor, area, on }) {
        const above = anchor.first.top - BUTTON_GAP - BUTTON_SIZE;
        // 画面の端とスクロール領域の上端の内側に収まるか
        const fitsAbove = above >= Math.max(SCREEN_EDGE, area.scroller.top);
        const side = fitsAbove ? "above" : "below";
        const top = fitsAbove ? above : anchor.last.bottom + BUTTON_GAP;
        const edge = fitsAbove ? anchor.first.left : anchor.last.left;
        const left = Math.max(SCREEN_EDGE, Math.min(edge, area.viewport.width - SCREEN_EDGE - BUTTON_SIZE));
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "selection-comment",
                type: "button",
                "aria-label": BUTTON_NAME,
                "data-side": side,
                // 画面の右半分に出した入口は、ツールチップを入口の右端に揃える
                "data-tip": left + BUTTON_SIZE / 2 > area.viewport.width / 2 ? "end" : "start",
                style: `position:fixed;left:${left}px;top:${top}px;width:${BUTTON_SIZE}px;height:${BUTTON_SIZE}px`,
                // 押したときに選択が外れないよう、ポインターを押した既定の動き（選択の解除）を止める
                onpointerdown: (event) => event.preventDefault(),
                onclick: () => on.press(),
                onkeydown: (event) => {
                    if (event.key === "Escape") {
                        // 入口だけを閉じる。詳細パネルを閉じる Esc・モーダルを閉じる動きとして受けさせない
                        event.stopPropagation();
                        event.preventDefault();
                        on.close();
                    }
                },
            },
            children: [
                MindmapPreview.icon("comment"),
                // 名前のツールチップ。読み上げの名前は入口のボタンが持つので、二度読まれないよう読み上げから外す
                MindmapPreview.h({ tag: "span", attrs: { class: "sc-tip", "aria-hidden": "true" }, children: [BUTTON_NAME] }),
            ],
        });
    }
    MindmapPreview.selectionComment = selectionComment;
})(MindmapPreview || (MindmapPreview = {}));
// 本文の印のツールチップ。本文の印（用語のタイトルと別名・資料と調査のエイリアスに一致した語）に乗せる・フォーカスすると、一致した項目を用語 → 資料 → 調査の順に並べて印の上に出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類ごとの見出しの名前 */
    const KIND_LABELS = { terms: "用語", docs: "資料", research: "調査" };
    /** 印との間の空きと、画面の端から内側に収める幅（px） */
    const TIP_GAP = 6;
    const SCREEN_EDGE = 8;
    /** 要素の中のフォーカスできる要素 */
    function focusablesIn(parent) {
        return [...parent.querySelectorAll("a[href], button, [tabindex]:not([tabindex='-1'])")].filter((node) => node.closest("[hidden]") === null);
    }
    /** 項目 1 件。用語は用語・ID・意味、資料・調査はタイトル・ID・説明（無ければ出さない） */
    function tipItem({ entry }) {
        const { item } = entry;
        const text = entry.kind === "terms" ? item.meaning : item.description;
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "tt-item" },
            children: [
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "tt-head" },
                    children: [
                        MindmapPreview.h({ tag: "a", attrs: { class: "tt-link", href: MindmapPreview.hashWith({ id: item.id, heading: null }), "data-id": item.id }, children: [item.title] }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
                    ],
                }),
                text === undefined || text === "" ? null : MindmapPreview.h({ tag: "span", attrs: { class: "tt-body" }, children: [text] }),
            ],
        });
    }
    /** 用語と資料・調査を含むツールチップの中身。種類ごとの見出し（種類名と件数）とリストに分ける */
    function groupedContent(entries) {
        return MindmapPreview.MARK_KINDS.map((kind) => ({ kind, entries: entries.filter((entry) => entry.kind === kind) }))
            .filter((group) => group.entries.length > 0)
            .map((group) => MindmapPreview.h({
            tag: "div",
            attrs: { class: "tt-group" },
            children: [
                MindmapPreview.h({
                    tag: "p",
                    attrs: { class: "tt-kind", id: `tt-kind-${group.kind}` },
                    children: [KIND_LABELS[group.kind], " ", MindmapPreview.h({ tag: "span", attrs: { class: "tt-n" }, children: [String(group.entries.length)] })],
                }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "tt-items", "aria-labelledby": `tt-kind-${group.kind}` },
                    children: group.entries.map((entry) => tipItem({ entry })),
                }),
            ],
        }));
    }
    /** ツールチップを返す。使う側が文書に入れて `showPopover()` で開く。開くと印の上に置き、上に収まらなければ下に、どちらにも収まらなければ広い側の高さに縮める */
    function termTip({ entries, anchor, pinned = false, on }) {
        // 用語 2 件以上か、資料・調査を含むときは、種類ごとの見出しとリンクで並べる
        const multi = entries.length > 1 || entries.some((entry) => entry.kind !== "terms");
        const tip = MindmapPreview.h({
            tag: "div",
            attrs: {
                id: MindmapPreview.TERM_TIP_ID,
                class: multi ? "term-tip is-multi" : "term-tip",
                // リンクを持たない用語 1 件だけのツールチップは tooltip の役割にし、リンクを持つ方は印の aria-details で指す
                role: multi ? null : "tooltip",
                popover: "manual",
            },
        });
        if (multi) {
            tip.append(...groupedContent(entries));
        }
        else {
            // 用語 1 件だけに一致した印は、用語・ID・意味だけを出す
            const term = entries[0].item;
            tip.append(MindmapPreview.h({ tag: "span", attrs: { class: "tt-head" }, children: [term.title, MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [term.id] })] }), MindmapPreview.h({ tag: "span", attrs: { class: "tt-body" }, children: [term.meaning ?? ""] }));
        }
        /** 印の上に 6px 空けて下端を留める。上に収まらなければ下に出し、どちらにも収まらなければ広い側の余白（印との 6px と画面の端の 8px を除く）の高さに縮めて固定する */
        const place = () => {
            const rect = anchor.getBoundingClientRect();
            tip.style.height = "";
            tip.style.top = "auto";
            tip.style.bottom = "auto";
            const needed = tip.offsetHeight;
            const spaceAbove = rect.top - TIP_GAP - SCREEN_EDGE;
            const spaceBelow = innerHeight - rect.bottom - TIP_GAP - SCREEN_EDGE;
            const above = spaceAbove >= needed || (spaceBelow < needed && spaceAbove >= spaceBelow);
            const room = above ? spaceAbove : spaceBelow;
            // 収まらない: 縮めた高さで固定し、中身が変わっても大きさを変えない
            if (needed > room)
                tip.style.height = `${Math.max(room, 0)}px`;
            tip.style.left = `${Math.max(SCREEN_EDGE, Math.min(rect.left, innerWidth - tip.offsetWidth - SCREEN_EDGE))}px`;
            if (above)
                tip.style.bottom = `${innerHeight - rect.top + TIP_GAP}px`;
            else
                tip.style.top = `${rect.bottom + TIP_GAP}px`;
        };
        /** 押して残した状態で、ツールチップと印の外を押したら閉じる */
        const closeOnOutsidePress = (event) => {
            const target = event.target;
            if (target instanceof Node && (tip.contains(target) || anchor.contains(target)))
                return;
            on.close();
        };
        // 開いたとき（と、開いた直後の描画の前）に置き場所を決める。押して残した状態なら外の押下も見る
        tip.addEventListener("toggle", (event) => {
            if (event.newState === "open") {
                place();
                if (pinned)
                    document.addEventListener("pointerdown", closeOnOutsidePress, true);
            }
            else {
                document.removeEventListener("pointerdown", closeOnOutsidePress, true);
            }
        });
        requestAnimationFrame(() => {
            if (tip.matches(":popover-open"))
                place();
        });
        // 中の項目のリンクは、その項目へ移る
        tip.addEventListener("click", (event) => {
            const link = event.target.closest("a.tt-link");
            if (link === null)
                return;
            event.preventDefault();
            on.open(link.getAttribute("data-id") ?? "");
        });
        tip.addEventListener("keydown", (event) => {
            // Esc: ツールチップだけを閉じて印へフォーカスを戻す（全画面を閉じる Esc として受けさせない）
            if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                anchor.focus();
                on.close();
                return;
            }
            if (event.key !== "Tab")
                return;
            // 最初のリンクの Shift+Tab は印へ、最後のリンクの次は本文の印の次の要素へ移す
            const inside = focusablesIn(tip);
            const edge = event.shiftKey ? inside[0] : inside.at(-1);
            if (document.activeElement !== edge)
                return;
            event.preventDefault();
            if (event.shiftKey) {
                anchor.focus();
                return;
            }
            const after = focusablesIn(anchor.closest(".md") ?? document.body);
            const next = after[after.indexOf(anchor) + 1] ?? anchor;
            next.focus();
            // 印へ戻るときは focusout で閉じないため、ここで閉じる
            if (next === anchor)
                on.close();
        });
        // 中から印でもツールチップでもない所へフォーカスが出たら閉じる
        tip.addEventListener("focusout", (event) => {
            const to = event.relatedTarget;
            if (to instanceof Node && !tip.contains(to) && to !== anchor)
                on.close();
        });
        return tip;
    }
    MindmapPreview.termTip = termTip;
})(MindmapPreview || (MindmapPreview = {}));
// 表示の設定の中身。表示する種類と差分のミニマップと本文の表とセクションの見せ方を選び、この端末で変えている項目・既定に戻す・ワークスペースの既定にするを出す。見た目はネットワークのドロップダウンで選ぶので、ここでは選ばせない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 選べるネットワークの見た目 */
    MindmapPreview.NETWORK_LOOKS = [
        { key: "glow", label: "グロウ", note: "玉と流れる光に、やわらかい光のにじみ" },
        { key: "starlight", label: "星の光", note: "白い芯と色の光。明るい星に十字の光条" },
        { key: "constellation", label: "星図", note: "回転に合わせて回る天球の経緯線" },
        { key: "deep", label: "深宇宙", note: "星空と星雲の地に、光のにじむ星" },
        { key: "dust", label: "星屑", note: "色を抜いた細かな点と細い線" },
    ];
    /** ワークスペースの既定も個人の上書きも無いときの見た目 */
    MindmapPreview.BUILTIN_LOOK = "deep";
    /** 見た目の値 → 画面に出す名前 */
    function lookLabel(look) {
        return MindmapPreview.NETWORK_LOOKS.find((option) => option.key === look)?.label ?? look;
    }
    MindmapPreview.lookLabel = lookLabel;
    /** 差分のミニマップの呼び名（表示の設定の切り替えと「この端末で変えている項目」に出す名前） */
    MindmapPreview.MINIMAP_LABEL = "差分のミニマップ";
    /** 種類 → 種類の行に出す印 */
    const KIND_ICON = {
        decisions: "decision",
        tasks: "task",
        research: "research",
        docs: "doc",
        terms: "term",
        notes: "note",
        logs: "log",
    };
    /** 2 つの集合が同じ要素を持つか */
    function sameSet(a, b) {
        return a.size === b.size && [...a].every((value) => b.has(value));
    }
    /** 種類の並び（種類の定義の順）にそろえる */
    function orderedKinds(kinds) {
        return MindmapPreview.KIND_KEYS.filter((kind) => kinds.has(kind));
    }
    /** 端末に保存できない旨（パネルの先頭） */
    function storageNote() {
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: "st-note", role: "alert" },
            children: [
                MindmapPreview.icon("alert"),
                MindmapPreview.h({ tag: "span", children: ["この端末に保存できません。選んだ表示は、このページを開いている間だけ当たります。"] }),
            ],
        });
    }
    /** 概要・ネットワークの行（常に出す。チェックの箱を持たない） */
    function alwaysRow({ iconName, label }) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "st-always" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "st-always-box" }, children: [MindmapPreview.icon("check")] }),
                MindmapPreview.icon(iconName),
                MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: [label] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "st-always-note" }, children: ["常に表示"] }),
            ],
        });
    }
    /** 表示する種類の選び（先頭にまとめて選ぶチェック、概要とネットワークは常に出す行） */
    function kindsField({ kinds, counts, on }) {
        const shownCount = MindmapPreview.KIND_KEYS.filter((kind) => kinds.has(kind)).length;
        const allBox = MindmapPreview.h({
            tag: "input",
            attrs: {
                type: "checkbox",
                checked: shownCount === MindmapPreview.KIND_KEYS.length,
                "data-focus": "kinds-all",
                // 全て選んでいるときは全て外し、そうでなければ全て選ぶ
                onchange: () => on.kinds(shownCount === MindmapPreview.KIND_KEYS.length ? [] : [...MindmapPreview.KIND_KEYS]),
            },
        });
        // 一部だけを選んでいる途中の状態は、属性で持てないため要素に付ける
        allBox.indeterminate = shownCount > 0 && shownCount < MindmapPreview.KIND_KEYS.length;
        return MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "st-sec" },
            children: [
                MindmapPreview.h({ tag: "legend", children: ["表示する種類"] }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "st-kinds" },
                    children: [
                        MindmapPreview.h({
                            tag: "li",
                            attrs: { class: "st-all" },
                            children: [
                                MindmapPreview.h({
                                    tag: "label",
                                    children: [
                                        allBox,
                                        MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: ["すべて"] }),
                                        MindmapPreview.h({ tag: "span", attrs: { class: "n mono" }, children: [`${shownCount}/${MindmapPreview.KIND_KEYS.length}`] }),
                                    ],
                                }),
                            ],
                        }),
                        alwaysRow({ iconName: "home", label: "概要" }),
                        ...MindmapPreview.KIND_KEYS.map((kind) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                MindmapPreview.h({
                                    tag: "label",
                                    children: [
                                        MindmapPreview.h({
                                            tag: "input",
                                            attrs: {
                                                type: "checkbox",
                                                value: kind,
                                                checked: kinds.has(kind),
                                                "data-focus": `kind:${kind}`,
                                                // 押した種類だけを入れ替えた、変えた後の並びを知らせる
                                                onchange: () => {
                                                    const next = new Set(kinds);
                                                    if (next.has(kind))
                                                        next.delete(kind);
                                                    else
                                                        next.add(kind);
                                                    on.kinds(orderedKinds(next));
                                                },
                                            },
                                        }),
                                        MindmapPreview.icon(KIND_ICON[kind]),
                                        MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: [MindmapPreview.KIND_LABEL[kind]] }),
                                        MindmapPreview.h({ tag: "span", attrs: { class: "n mono" }, children: [counts[kind] ?? ""] }),
                                    ],
                                }),
                            ],
                        })),
                        alwaysRow({ iconName: "network", label: "ネットワーク" }),
                    ],
                }),
            ],
        });
    }
    /** 詳細に表示するものの 1 行（チェックと名前） */
    function detailCheck({ checked, focus, label, onChange }) {
        return MindmapPreview.h({
            tag: "li",
            children: [
                MindmapPreview.h({
                    tag: "label",
                    children: [
                        MindmapPreview.h({ tag: "input", attrs: { type: "checkbox", checked, "data-focus": focus, onchange: onChange } }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "st-k-label" }, children: [label] }),
                    ],
                }),
            ],
        });
    }
    /** 詳細に表示するものの選び（差分のミニマップと、本文の表とセクションの見せ方の 4 つのチェック） */
    function detailField({ minimap = true, bodyView = MindmapPreview.BODY_VIEW_DEFAULT, on }) {
        return MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "st-sec" },
            children: [
                MindmapPreview.h({ tag: "legend", children: ["詳細に表示するもの"] }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "st-kinds" },
                    children: [
                        detailCheck({ checked: minimap, focus: "minimap", label: MindmapPreview.MINIMAP_LABEL, onChange: () => on.minimap(!minimap) }),
                        ...MindmapPreview.BODY_VIEW_KEYS.map((key) => detailCheck({
                            checked: bodyView[key],
                            focus: `body-view:${key}`,
                            label: MindmapPreview.BODY_VIEW_LABELS[key],
                            onChange: () => on.bodyView({ key, value: !bodyView[key] }),
                        })),
                    ],
                }),
            ],
        });
    }
    /** この端末で変えている項目と「既定に戻す」。上書きが無いときはボタンを出さず、その旨を出す */
    function resetBlock({ overrides, on }) {
        if (overrides.length === 0) {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "st-reset" },
                children: [
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "st-over st-none", tabindex: "-1", "data-focus": "over" },
                        children: ["ワークスペースの既定のまま表示しています。"],
                    }),
                ],
            });
        }
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-reset" },
            children: [
                MindmapPreview.h({
                    tag: "p",
                    attrs: { class: "st-over" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "st-over-h" }, children: ["この端末で変えている項目"] }),
                        MindmapPreview.h({ tag: "span", children: [overrides.join("・")] }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn", type: "button", "data-focus": "reset", onclick: () => on.reset() },
                    children: [MindmapPreview.icon("undo"), "既定に戻す"],
                }),
            ],
        });
    }
    /** 「ワークスペースの既定にする」。選びが既定と同じときはボタンの代わりにその旨を出す */
    function saveBlock({ look, defaultLook, kinds, defaultKinds, on }) {
        const differs = look !== defaultLook || !sameSet(kinds, defaultKinds);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-save" },
            children: [
                differs
                    ? MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "btn",
                            type: "button",
                            "aria-haspopup": "dialog",
                            "data-focus": "save",
                            onclick: () => on.save(),
                        },
                        children: [MindmapPreview.icon("save"), "ワークスペースの既定にする"],
                    })
                    : MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "st-same", tabindex: "-1", "data-focus": "same" },
                        children: ["見た目と表示する種類は、ワークスペースの既定と同じです。"],
                    }),
            ],
        });
    }
    /** 下端に残す知らせ（`role="status"`） */
    function messageLine(message) {
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: `st-msg${message === null ? "" : ` ${message.kind}`}`, role: "status" },
            children: message === null ? [] : [MindmapPreview.icon(message.kind === "ok" ? "check" : "sliders"), MindmapPreview.h({ tag: "span", children: [message.text] })],
        });
    }
    /** ワークスペースの設定の入口（見出し・何を書き換えられるかの案内・「設定を編集する」） */
    function workspaceEntry(onWorkspace) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-ws-entry" },
            children: [
                MindmapPreview.h({ tag: "h3", children: ["ワークスペースの設定"] }),
                MindmapPreview.h({ tag: "p", attrs: { class: "pe-ws-sum" }, children: ["題名・フェーズ・ゴール・対象・カテゴリー"] }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn", type: "button", onclick: () => onWorkspace() },
                    children: [MindmapPreview.icon("edit"), "設定を編集する"],
                }),
            ],
        });
    }
    /** 表示の設定の中身を返す */
    function settingsPanel(props) {
        const { canSave, message = null, storageOk = true, onWorkspace = null } = props;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-wrap" },
            children: [
                storageOk ? null : storageNote(),
                kindsField(props),
                detailField(props),
                resetBlock(props),
                canSave ? saveBlock(props) : null,
                messageLine(message),
                onWorkspace === null ? null : workspaceEntry(onWorkspace),
            ],
        });
    }
    MindmapPreview.settingsPanel = settingsPanel;
})(MindmapPreview || (MindmapPreview = {}));
// 既定の保存の確かめ。ワークスペースの既定として保存する前に、今の既定と保存する値を並べるモーダル。
var MindmapPreview;
(function (MindmapPreview) {
    /** 表示する種類を、外した種類の名前で書く（全て出すときは「すべて表示」） */
    function kindsText(kinds) {
        const hidden = MindmapPreview.KIND_KEYS.filter((kind) => !kinds.has(kind)).map((kind) => MindmapPreview.KIND_LABEL[kind]);
        return hidden.length > 0 ? `${hidden.join("・")}を表示しない` : "すべて表示";
    }
    MindmapPreview.kindsText = kindsText;
    /** 確かめの 1 行。変える項目は今の既定と保存する値を、変えない項目は今の値と「変えない」を出す */
    function confirmRow({ label, from, to }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "sc-row" },
            children: [
                MindmapPreview.h({ tag: "dt", children: [label] }),
                MindmapPreview.h({
                    tag: "dd",
                    children: from === to
                        ? [
                            MindmapPreview.h({ tag: "span", attrs: { class: "sc-to" }, children: [to] }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "sc-same" }, children: ["変えない"] }),
                        ]
                        : [
                            MindmapPreview.h({
                                tag: "span",
                                attrs: { class: "sc-from" },
                                children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["今の既定 "] }), from],
                            }),
                            MindmapPreview.icon("arrow"),
                            MindmapPreview.h({
                                tag: "span",
                                attrs: { class: "sc-to" },
                                children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["保存する値 "] }), to],
                            }),
                        ],
                }),
            ],
        });
    }
    /** 既定の保存の確かめを返す。文書に入れた後、呼ぶ側が `showModal()` で開く。最初のフォーカスは「取り消す」 */
    function settingsConfirm({ from, to, busy = false, error = null, on }) {
        const dialog = MindmapPreview.h({
            tag: "dialog",
            attrs: { class: "confirm sconfirm", "aria-labelledby": "sc-h" },
            children: [
                MindmapPreview.h({ tag: "h2", attrs: { id: "sc-h" }, children: ["ワークスペースの既定を書き換えますか"] }),
                MindmapPreview.h({
                    tag: "p",
                    attrs: { class: "sc-lead" },
                    children: ["このワークスペースを開く全員の既定が変わります。表示の設定を自分で変えている人には、変えた項目は当たりません。"],
                }),
                MindmapPreview.h({
                    tag: "dl",
                    attrs: { class: "sc-list" },
                    children: [
                        confirmRow({ label: "ネットワークの見た目", from: MindmapPreview.lookLabel(from.look), to: MindmapPreview.lookLabel(to.look) }),
                        confirmRow({ label: "表示する種類", from: kindsText(from.kinds), to: kindsText(to.kinds) }),
                    ],
                }),
                error === null
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "sc-error", role: "alert" },
                        children: [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [error] })],
                    }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "cf-row" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn ghost",
                                type: "button",
                                autofocus: true,
                                disabled: busy,
                                "data-focus": "cancel",
                                onclick: () => on.cancel(),
                            },
                            children: ["取り消す"],
                        }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary",
                                type: "button",
                                disabled: busy,
                                "data-focus": "confirm",
                                onclick: () => on.save(),
                            },
                            children: busy ? [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), "保存しています"] : ["保存する"],
                        }),
                    ],
                }),
            ],
        });
        // Esc: 保存している間は閉じず、それ以外は取り消す（ブラウザの既定の閉じ方を止めて、使う側が閉じる）
        dialog.addEventListener("cancel", (event) => {
            event.preventDefault();
            if (!busy)
                on.cancel();
        });
        return dialog;
    }
    MindmapPreview.settingsConfirm = settingsConfirm;
})(MindmapPreview || (MindmapPreview = {}));
// 本文の形式の札。資料のカード・ボードのカードの種類の右と、表の「形式」の列と、詳細のヘッダーの種類と ID の右に置く。形式の名前を等幅の文字で出し、HTML は地の面を敷いて一覧で拾いやすくする。
var MindmapPreview;
(function (MindmapPreview) {
    /** 形式 → 札の文言 */
    const FORMAT_LABEL = { md: "MD", html: "HTML" };
    /** 形式 → 札の `title`（略語だけにしない） */
    const FORMAT_TITLE = { md: "本文は Markdown", html: "本文は HTML" };
    /** 本文の形式の札。色だけに頼らず、`MD` / `HTML` の文字で伝える */
    function bodyFormatBadge({ format }) {
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: `fmt-badge fmt-${format}`, title: FORMAT_TITLE[format] },
            children: [FORMAT_LABEL[format]],
        });
    }
    MindmapPreview.bodyFormatBadge = bodyFormatBadge;
    /** 資料の `body` から本文の形式の札を返す（`body` を持たないか知らない拡張子なら null） */
    function bodyFormatBadgeOf(body) {
        const format = MindmapPreview.bodyFormatOf(body);
        return format === null ? null : bodyFormatBadge({ format });
    }
    MindmapPreview.bodyFormatBadgeOf = bodyFormatBadgeOf;
})(MindmapPreview || (MindmapPreview = {}));
// HTML の本文の枠。HTML の本文と Markdown の中の `html` のコードブロックを、スクリプトを動かさない枠（`sandbox="allow-same-origin"` の iframe の `srcdoc`）に描く。枠の高さは描いた中身に合わせ、枠の中で選んだ文を元の HTML の行の範囲にして使う側へ知らせる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 描く前の枠の高さ（px）。描いた後に中身の高さへ伸びる */
    const FRAME_INITIAL_HEIGHT = 120;
    /** 描き終えた枠が持つ属性（描き終えたかを呼び出し側が確かめる） */
    const RENDERED_ATTR = "data-rendered";
    /** 差分の印を付けた要素が持つ属性 */
    const MARK_ATTR = "data-df";
    /** 要素が閉じる元の HTML の行（1 始まり）の属性。サーバーが足す */
    const HTML_LINE_END_ATTR = "data-line-end";
    /** 行の印（` data-line="n"`・` data-line-end="n"`）を外して、原文に戻す */
    function withoutHtmlLineMarks(marked) {
        return marked.replace(/ data-line(?:-end)?="\d+"/g, "");
    }
    /** 枠の文書の中で、行を含む最も内側の行の印を持つ要素（無ければ null）。要素の範囲は、始まりの行（`data-line`）から終わりの行（`data-line-end`）まで。範囲に行を含む要素のうち、文書の順で最後のもの */
    function innermostAt({ doc, line }) {
        let found = null;
        for (const element of doc.body.querySelectorAll(`[${MindmapPreview.HTML_LINE_ATTR}]`)) {
            // 文書の順で始まりの行は小さい順に並ぶので、行より後に始まる要素に着いたら終える
            if (Number(element.getAttribute(MindmapPreview.HTML_LINE_ATTR)) > line)
                break;
            // 行より前に閉じた要素は、行を含まない
            if (Number(element.getAttribute(HTML_LINE_END_ATTR)) >= line)
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
    /** 枠から親をたどって最初に当たる、縦にスクロールできる要素（計算した `overflow-y` が `auto` か `scroll`）。無ければ null */
    function verticalScroller(frame) {
        for (let element = frame.parentElement; element !== null; element = element.parentElement) {
            const overflowY = getComputedStyle(element).overflowY;
            if (overflowY === "auto" || overflowY === "scroll")
                return element;
        }
        return null;
    }
    /** 本文のスクロール領域を、枠の中の `id` の要素の上端が領域の上端に来る位置まで送る（要素か領域が無ければ送らない） */
    function scrollToAnchor({ frame, id }) {
        const target = frame.contentDocument?.getElementById(id) ?? null;
        const scroller = verticalScroller(frame);
        if (target === null || scroller === null)
            return;
        // 枠の位置に枠の中の要素の位置を足して、領域の上端からの距離を求める
        const offset = frame.getBoundingClientRect().top + frame.clientTop + target.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
        scroller.scrollTop += offset;
    }
    /** 枠の文書の `click`・`auxclick`（中ボタン）を受け、リンクの押下を枠の中で移らせず、`htmlLinkAction` の決めたとおりに開く・送る */
    function bindLinks({ frame, doc }) {
        const view = doc.defaultView;
        if (view === null)
            return;
        // ポインターを押してから離すまでの間に選択が変わったか（リンクの文をなぞって選んだ直後の `click` を見分ける）
        let pressed = false;
        let selectionChanged = false;
        doc.addEventListener("pointerdown", () => {
            pressed = true;
            selectionChanged = false;
        });
        doc.addEventListener("pointerup", () => {
            pressed = false;
        });
        doc.addEventListener("selectionchange", () => {
            if (pressed)
                selectionChanged = true;
        });
        const onPress = (event) => {
            // 枠の文書の要素は枠の文書の `Element` で見分ける（親の画面の `Element` とは別物）
            if (!(event.target instanceof view.Element))
                return;
            // 押された要素から最も近い `href` を持つリンク
            const link = event.target.closest("a[href], area[href]");
            if (link === null)
                return;
            // 枠の中では移らない
            event.preventDefault();
            // 選んだ直後は開かず送らない。キーボードからの `click`（`detail` が 0）は選択の有無によらず扱う
            const selection = view.getSelection();
            if (selectionChanged && event.detail > 0 && selection !== null && !selection.isCollapsed)
                return;
            const action = MindmapPreview.htmlLinkAction(link.getAttribute("href") ?? "");
            if (action.kind === "open")
                window.open(action.url, "_blank", "noopener,noreferrer");
            else if (action.kind === "anchor")
                scrollToAnchor({ frame, id: action.id });
        };
        doc.addEventListener("click", onPress);
        // 中ボタン以外の `auxclick`（右ボタンなど）はリンクの押下として扱わない
        doc.addEventListener("auxclick", (event) => {
            if (event.button === 1)
                onPress(event);
        });
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
            // 高さを描いた中身に合わせる（中身が変わっても追う）。測る間だけ枠の高さを 0 にし（本文が `100%`・`vh` で枠の高さを基準にしても、枠が伸び続けない）、ルート要素の `scrollHeight` に枠の線の分を足す。枠の中に縦のスクロールの帯を出さない
            const root = doc.documentElement;
            root.style.overflowY = "hidden";
            new ResizeObserver(() => {
                frame.style.height = "0px";
                frame.style.height = `${root.scrollHeight + frame.offsetHeight - frame.clientHeight}px`;
            }).observe(root);
            if (marks !== undefined)
                paintMarks({ doc, marks });
            bindLinks({ frame, doc });
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
// HTML の本文の差分。差分の表示の間、HTML の本文を描いた結果の上で変わった行を含む要素に印を付け、「原文の差分」に切り替えると原文の行の差分を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 原文の差分で、同じ行がこの数を超えて続くときは前後だけを残して畳む（前後に残す行数） */
    const RAW_DIFF_CONTEXT = 3;
    /** 原文の行の差分。足した行・消した行に印を付け、変わっていない長い並びは前後 3 行を残して件数の行にする */
    function rawDiff({ parts }) {
        const lines = [];
        const deadline = performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS;
        parts.forEach((part, position) => {
            // 消した並びのすぐ後の足した並びは、消した並びと対にして渡し、変わった語に面を付ける
            if (part.kind === "added" && parts[position - 1]?.kind === "removed")
                return;
            const next = parts[position + 1];
            if (part.kind === "removed" && next?.kind === "added") {
                lines.push(...MindmapPreview.rawDiffLines({ parts: [part, next], deadline }));
                return;
            }
            if (part.kind !== "same" || part.lines.length <= RAW_DIFF_CONTEXT * 2) {
                lines.push(...MindmapPreview.rawDiffLines({ parts: [part], deadline }));
                return;
            }
            // 先頭・末尾の並びは、変わった行の側だけを残す
            const head = position === 0 ? [] : part.lines.slice(0, RAW_DIFF_CONTEXT);
            const tail = position === parts.length - 1 ? [] : part.lines.slice(-RAW_DIFF_CONTEXT);
            const skipped = part.lines.length - head.length - tail.length;
            lines.push(...MindmapPreview.rawDiffLines({ parts: [{ kind: "same", lines: head }], deadline }));
            lines.push(MindmapPreview.h({ tag: "span", attrs: { class: "df-line df-skip" }, children: [`変わっていない ${skipped} 行`] }));
            lines.push(...MindmapPreview.rawDiffLines({ parts: [{ kind: "same", lines: tail }], deadline }));
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
    /** 左右に並べた表示の列の名前の行 */
    function sideHead() {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "sbs-head", "aria-hidden": "true" },
            children: [MindmapPreview.h({ tag: "span", children: ["選んだ時点"] }), MindmapPreview.h({ tag: "span", children: ["今"] })],
        });
    }
    /** 原文の行の差分を左右に並べる。左に選んだ時点の行（消した行に印）、右に今の行（足した行に印）を置き、片側にしか無い行の向かいは空けて高さを揃える */
    function rawSideDiff({ parts }) {
        const cells = [];
        const deadline = performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS;
        const gap = () => MindmapPreview.h({ tag: "span", attrs: { class: "df-line df-gap", "aria-hidden": "true" } });
        /** 左右の行の並びを、1 行ずつ向かい合わせて置く（短い側は空ける） */
        const place = (left, right) => {
            for (let offset = 0; offset < Math.max(left.length, right.length); offset += 1) {
                cells.push(left[offset] ?? gap(), right[offset] ?? gap());
            }
        };
        const sameLines = (lines) => MindmapPreview.rawDiffLines({ parts: [{ kind: "same", lines }], deadline });
        parts.forEach((part, position) => {
            if (part.kind === "same") {
                // 変わっていない長い並びは、前後の 3 行を残して件数の行にする
                const long = part.lines.length > RAW_DIFF_CONTEXT * 2;
                const head = !long ? part.lines : position === 0 ? [] : part.lines.slice(0, RAW_DIFF_CONTEXT);
                const tail = !long ? [] : position === parts.length - 1 ? [] : part.lines.slice(-RAW_DIFF_CONTEXT);
                place(sameLines(head), sameLines(head));
                if (long) {
                    cells.push(MindmapPreview.h({ tag: "span", attrs: { class: "df-line df-skip df-span" }, children: [`変わっていない ${part.lines.length - head.length - tail.length} 行`] }));
                    place(sameLines(tail), sameLines(tail));
                }
                return;
            }
            // 消した行のすぐ後の足した行は、消した行と同じ行の高さに向かい合わせて置いた
            if (part.kind === "added" && parts[position - 1]?.kind === "removed")
                return;
            const next = parts[position + 1];
            if (part.kind === "removed" && next?.kind === "added") {
                // 行の数が同じなら変わった語に面を付ける
                const spans = MindmapPreview.rawDiffLines({ parts: [part, next], deadline });
                place(spans.slice(0, part.lines.length), spans.slice(part.lines.length));
                return;
            }
            const spans = MindmapPreview.rawDiffLines({ parts: [part], deadline });
            if (part.kind === "removed")
                place(spans, []);
            else
                place([], spans);
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "html-diff sbs-only" },
            children: [
                MindmapPreview.h({ tag: "p", attrs: { class: "html-diff-head" }, children: ["原文の差分"] }),
                sideHead(),
                MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw df-raw df-split", tabindex: "0", "aria-label": "原文の差分（左に選んだ時点、右に今）" }, children: cells }),
            ],
        });
    }
    /** 選んだ時点の Markdown の本文を描き、見出しを節の見出し「本文」（h3）の次の段から並べる */
    function renderedMarkdown({ source }) {
        const root = MindmapPreview.renderMarkdown(source);
        MindmapPreview.lowerHeadings({ root, shift: MindmapPreview.headingShift({ roots: [root] }) });
        return root;
    }
    /** 描いた結果を左右に並べる。左は選んだ時点の本文（Markdown のときは Markdown として描く）、右は今の本文 */
    function renderedSide({ before, beforeFormat, right }) {
        const left = beforeFormat === "md" ? renderedMarkdown({ source: before }) : MindmapPreview.htmlBodyFrame({ source: before, selectable: false, label: "選んだ時点の本文" });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "sbs sbs-html" },
            children: [
                sideHead(),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "sbs-cols" },
                    children: [
                        MindmapPreview.h({ tag: "section", attrs: { class: "sbs-col sbs-before", "aria-label": "選んだ時点の本文" }, children: [left] }),
                        MindmapPreview.h({ tag: "section", attrs: { class: "sbs-col sbs-after", "aria-label": "今の本文" }, children: [right] }),
                    ],
                }),
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
    function htmlBodyDiff({ before, after, marked, beforeFormat = "html", layout = "inline", layoutSwitch = null, initial = "rendered", beforeView = null, afterView = null, heading = null, }) {
        const parts = MindmapPreview.diffLineParts(before, after);
        if (parts === null)
            return null;
        const raw = rawDiff({ parts });
        // 埋め込んだ HTML の範囲の差分: 変更前・変更後の描いた結果と原文の差分の 3 つを切り替える
        if (beforeView !== null)
            return rangeDiff({ raw, beforeView, afterView, marked, initial, heading });
        const side = layout === "side";
        // 選んだ時点の本文が Markdown で、インライン: 描いた結果の印と切り替えを出さず、原文の差分だけを出す
        if (beforeFormat === "md" && !side) {
            return layoutSwitch === null
                ? raw
                : MindmapPreview.h({ tag: "div", attrs: { class: "html-diff-c" }, children: [MindmapPreview.h({ tag: "div", attrs: { class: "html-diff-bar" }, children: [layoutSwitch] }), raw] });
        }
        const changed = MindmapPreview.htmlChangedLines(before, after);
        if (changed === null)
            return null;
        // 選んだ時点が Markdown のときは、右の今の本文に印を付けない
        const marks = beforeFormat === "md" ? undefined : { added: changed.added, changed: changed.changed };
        // 選んだ箇所のコメントの入口は出さない（差分の表示の間は今の本文の行と合わない場合がある）
        const rendered = MindmapPreview.h({
            tag: "div",
            attrs: { class: "html-marked" },
            children: [MindmapPreview.htmlBodyFrame({ source: marked, selectable: false, ...(marks === undefined ? {} : { marks }) })],
        });
        raw.hidden = true;
        // 左右に並べるときは、並べた描いた結果と原文の差分を持ち、本文の幅が足りないときはインラインの方を出す
        let rawSide = null;
        if (side) {
            rendered.firstElementChild?.classList.add("sbs-fallback");
            raw.classList.add("sbs-fallback");
            rendered.prepend(renderedSide({
                before,
                beforeFormat,
                right: MindmapPreview.htmlBodyFrame({ source: marked, selectable: false, label: "今の本文", ...(marks === undefined ? {} : { marks }) }),
            }));
            rawSide = rawSideDiff({ parts });
            rawSide.hidden = true;
        }
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
                    // 左右に並べた原文の差分も、原文の差分と一緒に出し分ける
                    if (rawSide !== null)
                        rawSide.hidden = !showRaw;
                },
            },
            children: [label],
        });
        const container = MindmapPreview.h({
            tag: "div",
            attrs: { class: "html-diff-c" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "html-diff-bar" },
                    children: [
                        // 並べ方の切り替えを、描いた結果と原文の差分の切り替えの前に別の組で置く
                        layoutSwitch,
                        headingLabel({ heading }),
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "segment", role: "group", "aria-label": viewGroupName({ heading }) },
                            children: [toggle("描いた結果", false), toggle("原文の差分", true)],
                        }),
                        legendElement,
                    ],
                }),
                rendered,
                rawSide,
                raw,
            ],
        });
        // 「原文の差分」を選んだ状態で開く
        if (initial === "raw")
            container.querySelector(".segment button:last-child")?.click();
        return container;
    }
    MindmapPreview.htmlBodyDiff = htmlBodyDiff;
    /** 見せ方の切り替えの組の読み上げの名前 */
    function viewGroupName({ heading }) {
        return heading === null ? "本文の差分の見せ方" : `${heading}の差分の見せ方`;
    }
    /** 切り替えの組の前に出す名前（無ければ null） */
    function headingLabel({ heading }) {
        return heading === null ? null : MindmapPreview.h({ tag: "span", attrs: { class: "html-diff-heading" }, children: [heading] });
    }
    /** 埋め込んだ HTML の範囲の差分。「描いた結果（変更前）」「描いた結果（変更後）」「原文の差分」を切り替える。凡例は「描いた結果（変更後）」でだけ出す */
    function rangeDiff({ raw, beforeView, afterView, marked, initial, heading, }) {
        const views = [
            { label: "描いた結果（変更前）", element: MindmapPreview.h({ tag: "div", attrs: { class: "html-marked" }, children: [beforeView] }), legended: false },
            {
                label: "描いた結果（変更後）",
                element: MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "html-marked" },
                    children: [afterView ?? MindmapPreview.htmlBodyFrame({ source: marked, selectable: false })],
                }),
                legended: true,
            },
            { label: "原文の差分", element: raw, legended: false },
        ];
        const legendElement = legend({ removedOnly: false });
        // 開いた時点の見せ方（`raw` は原文の差分、`rendered` は変更後の描いた結果）
        const first = initial === "raw" ? 2 : 1;
        const show = (position) => {
            views.forEach((view, at) => {
                view.element.hidden = at !== position;
            });
            legendElement.hidden = !views[position].legended;
        };
        show(first);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "html-diff-c html-diff-range" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "html-diff-bar" },
                    children: [
                        headingLabel({ heading }),
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "segment", role: "group", "aria-label": viewGroupName({ heading }) },
                            children: views.map((view, position) => MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    type: "button",
                                    "aria-pressed": String(position === first),
                                    onclick: (event) => {
                                        const pressed = event.currentTarget;
                                        for (const button of pressed.parentElement?.children ?? [])
                                            button.setAttribute("aria-pressed", String(button === pressed));
                                        show(position);
                                    },
                                },
                                children: [view.label],
                            })),
                        }),
                        legendElement,
                    ],
                }),
                ...views.map((view) => view.element),
            ],
        });
    }
})(MindmapPreview || (MindmapPreview = {}));
// Markdown の本文の見せ方。描いた本文に、表の列の幅と折り返し・右端のフェード・コードブロックの言語の札とコピー・GitHub の Alert の囲みを常に当て、表示の設定で切り替える表の列の固定・表の見出しの固定・表のしま模様・セクションの折りたたみを当てる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 本文の見せ方の項目（表示の設定に並べる順） */
    MindmapPreview.BODY_VIEW_KEYS = ["pin", "head", "stripes", "fold"];
    /** 表示の設定のチェックボックスと「この端末で変えている項目」に出す名前 */
    MindmapPreview.BODY_VIEW_LABELS = {
        pin: "表の列の固定",
        head: "表の見出しの固定",
        stripes: "表のしま模様",
        fold: "セクションの折りたたみ",
    };
    /** 個人の上書きが無いときの本文の見せ方（列の固定・見出しの固定・折りたたみはオン、しま模様はオフ） */
    MindmapPreview.BODY_VIEW_DEFAULT = { pin: true, head: true, stripes: false, fold: true };
    /** 全角を 1、半角を 0.5 と数えたセルの最大の文字数が `shortMax` 以下の列は短い列、`longMin` 以上の列は長文の列 */
    const COLUMN_BOUNDS = { shortMax: 8, longMin: 25 };
    /** 中くらいの列の最小の幅（em）の上限 */
    const MEDIUM_MIN_EM_MAX = 14;
    /** 中くらいの列の最小の幅を文字数の半分にこの値（em）を足した幅にする（文節の区切りでだけ折り返す分の余り） */
    const MEDIUM_MIN_EM_SLACK = 2;
    /** 長文の列を折り返す幅（em） */
    const LONG_COLUMN_EM = 24;
    /** 本文で使っている見出しの階層のうち、上からこの数の階層にだけ開閉を置く */
    const FOLD_LEVELS = 2;
    /** コードブロックのコピーのボタンを押した後、チェックのマーカーを出しておくミリ秒（図のコピーと同じ） */
    const CODE_COPIED_MS = 1400;
    /** mdmark が描いた Alert の囲みの種類（クラス `markdown-alert-{種類}`）→ 見出しの頭に置くアイコン */
    const CALLOUT_KINDS = {
        note: "note",
        tip: "star",
        important: "flag",
        warning: "alert",
        caution: "alert",
    };
    /** 半角として数える文字の符号位置の上限 */
    const HALF_WIDTH_MAX = 0xff;
    /** 表を送らない枠の class（右端のフェードの基準） */
    const TABLE_FRAME_CLASS = "md-table-frame";
    /** 節の中身の入れ物の class（畳むと `hidden="until-found"` にする） */
    const SECTION_BODY_CLASS = "md-section-body";
    /** 節の中身の入れ物に振る id の通し番号 */
    let sectionSeq = 0;
    /** 前後の空白を除いた文字列の幅を、符号位置が U+00FF 以下の文字を 0.5、それ以外を 1 として数える */
    function textWidth(text) {
        let width = 0;
        for (const char of text.trim())
            width += (char.codePointAt(0) ?? 0) <= HALF_WIDTH_MAX ? 0.5 : 1;
        return width;
    }
    MindmapPreview.textWidth = textWidth;
    /** 列のセルの最大の文字の幅から、列の種類と最小の幅（em。中くらいの列だけ持つ）を決める */
    function columnSize(maxWidth) {
        if (maxWidth <= COLUMN_BOUNDS.shortMax)
            return { kind: "short", minEm: null };
        if (maxWidth >= COLUMN_BOUNDS.longMin)
            return { kind: "long", minEm: null };
        return { kind: "medium", minEm: Math.min(Math.ceil(maxWidth / 2) + MEDIUM_MIN_EM_SLACK, MEDIUM_MIN_EM_MAX) };
    }
    MindmapPreview.columnSize = columnSize;
    /** 表の列ごとにセルの最大の文字の幅を数え、列のセルに種類（`data-col-size`）と中くらいの列の最小の幅（`--md-col-min`）を付ける */
    function sizeColumns(table) {
        const widths = [];
        for (const row of table.rows) {
            [...row.cells].forEach((cell, column) => {
                widths[column] = Math.max(widths[column] ?? 0, textWidth(cell.textContent ?? ""));
            });
        }
        for (const row of table.rows) {
            [...row.cells].forEach((cell, column) => {
                const size = columnSize(widths[column] ?? 0);
                cell.dataset["colSize"] = size.kind;
                if (size.minEm !== null)
                    cell.style.setProperty("--md-col-min", `${size.minEm}em`);
            });
        }
        table.style.setProperty("--md-col-long", `${LONG_COLUMN_EM}em`);
    }
    /** 表の入れ物を送らない枠で包み、右へまだ送れる間だけ枠に `data-fade` を付ける */
    function frameTable(wrap) {
        if (wrap.parentElement?.classList.contains(TABLE_FRAME_CLASS) === true)
            return;
        const frame = MindmapPreview.h({ tag: "div", attrs: { class: TABLE_FRAME_CLASS } });
        wrap.replaceWith(frame);
        frame.append(wrap);
        const update = () => {
            frame.toggleAttribute("data-fade", wrap.scrollLeft + wrap.clientWidth < wrap.scrollWidth - 1);
        };
        wrap.addEventListener("scroll", update, { passive: true });
        const observer = new ResizeObserver(update);
        observer.observe(wrap);
        const table = wrap.querySelector("table");
        if (table !== null)
            observer.observe(table);
        update();
    }
    /** 見出しのセルの文言（固定のボタンを除く） */
    function headText(cell) {
        return [...cell.childNodes]
            .filter((node) => !(node instanceof HTMLElement && node.classList.contains("md-pin")))
            .map((node) => node.textContent ?? "")
            .join("")
            .trim();
    }
    /** 表の固定した列（左から `pinTo` 列目まで）に、左の位置と右端の影のマーカーを付ける。`pinTo` が -1 なら固定しない */
    function applyPins(table) {
        const pinTo = Number(table.dataset["pinTo"] ?? "-1");
        const head = table.tHead?.rows[0];
        if (head === undefined)
            return;
        // 列ごとの左の位置（見出しのセルの幅を積む）
        const lefts = [];
        let left = 0;
        for (const cell of head.cells) {
            lefts.push(left);
            left += cell.getBoundingClientRect().width;
        }
        for (const row of table.rows) {
            [...row.cells].forEach((cell, column) => {
                const pinned = column <= pinTo;
                cell.classList.toggle("md-pinned", pinned);
                cell.classList.toggle("md-pin-edge", column === pinTo);
                cell.style.left = pinned ? `${lefts[column] ?? 0}px` : "";
            });
        }
        head.querySelectorAll(".md-pin").forEach((button, column) => {
            button.setAttribute("aria-pressed", String(column === pinTo));
        });
    }
    /** 表の見出し（最後の列を除く）に固定のボタンを置く。押した列より左を固定し、もう一度押すと外す。押すまで固定しない */
    function addPinButtons(table) {
        const head = table.tHead?.rows[0];
        if (head === undefined || head.cells.length < 2 || head.querySelector(".md-pin") !== null)
            return;
        table.classList.add("md-has-pin");
        [...head.cells].slice(0, -1).forEach((cell, column) => {
            const label = headText(cell);
            cell.append(MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "th-tool md-pin",
                    type: "button",
                    "aria-pressed": "false",
                    "aria-label": `${label === "" ? `${column + 1} 列目` : label}まで固定`,
                    title: "この列まで固定",
                    onclick: () => {
                        table.dataset["pinTo"] = String(Number(table.dataset["pinTo"] ?? "-1") === column ? -1 : column);
                        applyPins(table);
                    },
                },
                children: [MindmapPreview.icon("pin")],
            }));
        });
        // 文字の読み込み・幅の変化で列の幅が変わったら、固定した列の位置を直す
        new ResizeObserver(() => applyPins(table)).observe(table);
    }
    /** 見出しの階層（元の Markdown の階層。無ければ要素の階層） */
    function headingLevel(element) {
        return Number(element.dataset["mdLevel"] ?? element.tagName.slice(1));
    }
    /** 見出しの要素か */
    function isHeading(element) {
        return /^H[1-6]$/.test(element.tagName);
    }
    /** 見出しの節の中身（次の同じか上の階層の見出しまで）を入れ物で包んで返す。中身が無ければ null */
    function wrapSection(heading) {
        const level = headingLevel(heading);
        const items = [];
        for (let node = heading.nextElementSibling; node !== null && !(isHeading(node) && headingLevel(node) <= level); node = node.nextElementSibling) {
            items.push(node);
        }
        if (items.length === 0)
            return null;
        const body = MindmapPreview.h({ tag: "div", attrs: { class: SECTION_BODY_CLASS, id: `md-section-${(sectionSeq += 1)}` } });
        heading.after(body);
        body.append(...items);
        return body;
    }
    /** 見出しを開く・畳む。畳んだ中身は `hidden="until-found"` にし、ページ内の検索の対象に残す */
    function setFolded({ heading, folded }) {
        const body = heading.nextElementSibling;
        if (body === null || !body.classList.contains(SECTION_BODY_CLASS))
            return;
        heading.dataset["folded"] = String(folded);
        heading.querySelector(".md-fold")?.setAttribute("aria-expanded", String(!folded));
        if (folded)
            body.setAttribute("hidden", "until-found");
        else
            body.removeAttribute("hidden");
        // 本文の高さが変わったので、表の見出しの固定の位置を直す
        heading.closest(".panel-body")?.dispatchEvent(new Event("scroll"));
    }
    /** 本文の見出しの文言（# のリンクと開閉のボタンを除く） */
    function headingLabel(heading) {
        return [...heading.childNodes]
            .filter((node) => !(node instanceof HTMLElement && node.matches(".h-link, .md-fold")))
            .map((node) => node.textContent ?? "")
            .join("")
            .trim();
    }
    /** 本文の見出しに開閉の矢印のボタンを置く（上位の `FOLD_LEVELS` 階層だけ）。節の中身を入れ物で包み、開いた状態で描く */
    function addFoldButtons(root) {
        if (root.querySelector(".md-fold") !== null)
            return;
        const levels = [...new Set([...root.children].filter(isHeading).map(headingLevel))]
            .sort((a, b) => a - b)
            .slice(0, FOLD_LEVELS);
        // 上の階層から包む（下の階層の見出しは、上の階層の入れ物の中で包む）
        for (const level of levels) {
            for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
                // その階層の見出しのうち、本文の直下か上の階層の入れ物の直下にあるものだけ
                const parent = heading.parentElement;
                if (headingLevel(heading) !== level || (parent !== root && parent?.classList.contains(SECTION_BODY_CLASS) !== true))
                    continue;
                const body = wrapSection(heading);
                if (body === null)
                    continue;
                heading.dataset["folded"] = "false";
                heading.prepend(MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "md-fold",
                        type: "button",
                        "aria-expanded": "true",
                        "aria-controls": body.id,
                        "aria-label": `${headingLabel(heading)}を開閉`,
                        onclick: () => setFolded({ heading, folded: heading.dataset["folded"] !== "true" }),
                    },
                    children: [MindmapPreview.icon("chev")],
                }));
                // ページ内の検索・リンクで畳んだ中身に当たった: ブラウザが開く前に、見出しの開閉の状態を開いたにそろえる
                body.addEventListener("beforematch", () => setFolded({ heading, folded: false }));
            }
        }
    }
    /** 本文の中の見出しへ移る前に、その見出しを包む畳んだ入れ物を全て開く（開閉の矢印の `aria-expanded` も合わせる） */
    function revealHeading({ root, slug }) {
        for (const target of root.querySelectorAll(`[data-heading="${CSS.escape(slug)}"]`)) {
            for (let body = target.closest(`.${SECTION_BODY_CLASS}`); body !== null; body = body.parentElement?.closest(`.${SECTION_BODY_CLASS}`) ?? null) {
                const heading = body.previousElementSibling;
                if (heading instanceof HTMLElement && heading.dataset["folded"] === "true")
                    setFolded({ heading, folded: false });
            }
        }
    }
    MindmapPreview.revealHeading = revealHeading;
    /** 要素が、埋め込んだ HTML の範囲（`.mdmark-html`）の中にあるか（範囲の中の要素には、表・コードブロック・Alert の見せ方を当てない） */
    function inEmbeddedHtml(element) {
        return element.closest(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`) !== null;
    }
    /** コードブロックを入れ物で包み、右上にコピーのボタン、言語を書いたものは左上に言語の札を置く（札とボタンはコードの文字に入れない） */
    function decorateCodeBlocks(root) {
        for (const code of root.querySelectorAll("pre > code")) {
            const pre = code.parentElement;
            if (pre.parentElement?.classList.contains("md-code") === true || inEmbeddedHtml(code))
                continue;
            const lang = [...code.classList].find((name) => name.startsWith("language-"))?.slice("language-".length) ?? null;
            const status = MindmapPreview.h({ tag: "span", attrs: { class: "sr-only", role: "status" } });
            const copy = MindmapPreview.h({
                tag: "button",
                attrs: { class: "icon-btn code-copy", type: "button", "aria-label": "コードをコピー", title: "コピー" },
                children: [MindmapPreview.icon("copy")],
            });
            copy.addEventListener("click", () => {
                void navigator.clipboard?.writeText(code.textContent ?? "").then(() => {
                    copy.replaceChildren(MindmapPreview.icon("check"));
                    status.textContent = "コピーしました";
                    window.setTimeout(() => {
                        copy.replaceChildren(MindmapPreview.icon("copy"));
                        status.textContent = "";
                    }, CODE_COPIED_MS);
                });
            });
            const box = MindmapPreview.h({ tag: "div", attrs: { class: lang === null ? "md-code" : "md-code has-lang" } });
            pre.replaceWith(box);
            box.append(...(lang === null ? [] : [MindmapPreview.h({ tag: "span", attrs: { class: "code-lang" }, children: [lang] })]), pre, copy, status);
        }
    }
    /** mdmark が描いた Alert の囲み（`div.markdown-alert`）の見出し（`p.markdown-alert-title`）の頭に、種類のアイコンを置く（置いてあれば重ねない） */
    function decorateCallouts(root) {
        for (const callout of root.querySelectorAll("div.markdown-alert")) {
            if (inEmbeddedHtml(callout))
                continue;
            const title = callout.querySelector(":scope > p.markdown-alert-title");
            const kind = [...callout.classList].find((name) => name.startsWith("markdown-alert-") && name !== "markdown-alert-title")?.slice("markdown-alert-".length);
            const name = kind === undefined ? undefined : CALLOUT_KINDS[kind];
            if (title === null || name === undefined || title.firstElementChild?.matches("svg.icon") === true)
                continue;
            title.prepend(MindmapPreview.icon(name));
        }
    }
    /** 描いた本文に見せ方を当てる。`display` は表示の設定の値、`fold` は開閉を置ける本文か（本文の差分では偽にする）、`tables` は表の見せ方を当てるか（スレッドの書き込みでは偽にし、表は mdmark の共通のスタイルのまま描く） */
    function decorateMarkdown({ root, display = MindmapPreview.BODY_VIEW_DEFAULT, fold = true, tables = true, }) {
        for (const table of tables ? root.querySelectorAll("table") : []) {
            // 埋め込んだ HTML の範囲の中の表には当てない
            if (inEmbeddedHtml(table))
                continue;
            sizeColumns(table);
            const wrap = table.closest(`.${MindmapPreview.TABLE_WRAP_CLASS}`);
            if (wrap !== null)
                frameTable(wrap);
            if (display.pin)
                addPinButtons(table);
            table.classList.toggle("md-head-stick", display.head && table.tHead !== null);
            table.classList.toggle("md-stripes", display.stripes);
        }
        if (fold && display.fold)
            addFoldButtons(root);
        decorateCodeBlocks(root);
        decorateCallouts(root);
    }
    MindmapPreview.decorateMarkdown = decorateMarkdown;
    /** 本文のスクロール領域を縦に送っても、見出しを固定した表の見出しの行を領域の上端に残す。受け取りを外す関数を返す（表の入れ物が横に送るため CSS の sticky では残せず、領域の送り量を見出しのセルへ縦のずらしとして入れる） */
    function bindTableHeads(scroller) {
        let frame = 0;
        const update = () => {
            frame = 0;
            const top = scroller.getBoundingClientRect().top;
            for (const table of scroller.querySelectorAll("table.md-head-stick")) {
                const head = table.tHead;
                if (head === null)
                    continue;
                const rect = table.getBoundingClientRect();
                // 表の上端が領域の上端より上にある分だけ下げる（見出しの行が表の下端を越えない）
                const max = Math.max(rect.height - head.offsetHeight, 0);
                const offset = Math.min(Math.max(top - rect.top, 0), max);
                for (const cell of head.rows[0]?.cells ?? [])
                    cell.style.setProperty("--head-offset", `${offset}px`);
                table.classList.toggle("md-head-stuck", offset > 0);
            }
        };
        const onScroll = () => {
            if (frame === 0)
                frame = requestAnimationFrame(update);
        };
        scroller.addEventListener("scroll", onScroll, { passive: true });
        update();
        return () => {
            scroller.removeEventListener("scroll", onScroll);
            if (frame !== 0)
                cancelAnimationFrame(frame);
        };
    }
    MindmapPreview.bindTableHeads = bindTableHeads;
})(MindmapPreview || (MindmapPreview = {}));
// 資料のエクスポートのメニュー。詳細パネル・詳細の全画面の見出しの「エクスポート」で開き、形式を選ぶ並び・Markdown の警告・HTML を組み立てている間・組み立てられなかったときを、同じメニューの中身を替えて出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** メニューが開いたときにフォーカスを置く要素が持つ属性 */
    MindmapPreview.DOC_EXPORT_FOCUS_ATTR = "data-dx-focus";
    /** メニューの見出しの `id` を作る連番 */
    let docExportMenuCounter = 0;
    /** 形式の 1 行（アイコン・名前・説明）。行の全体が押せる */
    function formatRow({ format, iconName, name, sub, disabled, busy, focused, on, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: busy ? "dx-item dx-busy" : "dx-item",
                type: "button",
                "data-format": format,
                // 処理中は押せなくするが、フォーカスは残す
                "aria-disabled": disabled ? "true" : null,
                [MindmapPreview.DOC_EXPORT_FOCUS_ATTR]: focused ? "" : null,
                onclick: () => {
                    if (!disabled)
                        on.format(format);
                },
            },
            children: [
                MindmapPreview.icon(iconName),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "dx-text" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "dx-name" }, children: [name] }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "dx-sub", role: busy ? "status" : null }, children: [sub] }),
                    ],
                }),
            ],
        });
    }
    /** 警告・エラーの下に置く「戻る」と右のボタン（右のボタンにフォーカスを置く） */
    function footer({ primary, on }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pop-foot dx-foot" },
            children: [
                MindmapPreview.h({ tag: "button", attrs: { class: "btn", type: "button", "data-dx-act": "back", onclick: on.back }, children: ["戻る"] }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "btn primary",
                        type: "button",
                        "data-dx-act": primary.act,
                        [MindmapPreview.DOC_EXPORT_FOCUS_ATTR]: "",
                        onclick: primary.act === "confirm" ? on.confirm : on.retry,
                    },
                    children: [primary.label],
                }),
            ],
        });
    }
    /** 資料のエクスポートのメニューを返す。`popover="auto"` の要素で、使う側が文書に入れて `showPopover()` で開く（開閉と、エクスポートの処理は使う側が持つ）。Esc かメニューの外を押して閉じたとき `on.close` を呼ぶ */
    function docExportMenu({ view = "choose", focus = "html", on }) {
        docExportMenuCounter += 1;
        const titleId = `doc-export-title-${docExportMenuCounter}`;
        const titles = {
            choose: "エクスポート",
            busy: "エクスポート",
            warn: "Markdown でエクスポートしますか?",
            error: "エクスポートできませんでした",
        };
        let content;
        if (view === "choose" || view === "busy") {
            const busy = view === "busy";
            content = [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "dx-list", role: "group", "aria-labelledby": titleId },
                    children: [
                        formatRow({
                            format: "html",
                            iconName: "code",
                            name: "HTML でエクスポート",
                            sub: busy ? "エクスポートしています…" : "スタイルと用語のツールチップを含む 1 つのファイル",
                            disabled: busy,
                            busy,
                            focused: busy || focus === "html",
                            on,
                        }),
                        formatRow({
                            format: "md",
                            iconName: "doc",
                            name: "Markdown でエクスポート",
                            sub: "本文の Markdown だけ",
                            disabled: busy,
                            busy: false,
                            focused: !busy && focus === "md",
                            on,
                        }),
                    ],
                }),
            ];
        }
        else if (view === "warn") {
            content = [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "dx-warn" },
                    children: [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "p", children: ["埋め込んだ HTML・チャート・操作できる部品は含まれず、共通のスタイルも外れます。"] })],
                }),
                footer({ primary: { label: "エクスポート", act: "confirm" }, on }),
            ];
        }
        else {
            content = [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "dx-warn dx-error", role: "alert" },
                    children: [
                        MindmapPreview.icon("alert"),
                        MindmapPreview.h({ tag: "p", children: ["mdmark のスタイルとスクリプトを読み込めませんでした。ネットワークにつながっているか確かめて、再試行してください。"] }),
                    ],
                }),
                footer({ primary: { label: "再試行", act: "retry" }, on }),
            ];
        }
        const menu = MindmapPreview.h({
            tag: "div",
            attrs: {
                class: "pop doc-export",
                role: "dialog",
                popover: "auto",
                "aria-labelledby": titleId,
                "aria-busy": view === "busy" ? "true" : null,
            },
            children: [MindmapPreview.h({ tag: "p", attrs: { class: "pop-title", id: titleId }, children: [titles[view]] }), ...content],
        });
        // Esc かメニューの外を押して閉じたとき
        menu.addEventListener("toggle", (event) => {
            if (event.newState === "closed")
                on.close();
        });
        return menu;
    }
    MindmapPreview.docExportMenu = docExportMenu;
})(MindmapPreview || (MindmapPreview = {}));
// 本文の差分の並べ方の切り替え。差分の表示の間、本文の差分の頭に「インライン」「左右に並べる」のボタンの組を置く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 切り替えの読み上げの名前と、表示の設定の「この端末で変えている項目」に出す名前 */
    MindmapPreview.BODY_LAYOUT_LABEL = "本文の差分の並べ方";
    /** 並べ方 → ボタンの文言 */
    const BODY_LAYOUT_BUTTON = { inline: "インライン", side: "左右に並べる" };
    /** 本文の差分の並べ方を切り替えるボタンの組を返す（描き直しは使う側が行う） */
    function bodyDiffLayoutSwitch({ layout, on }) {
        const button = (value) => MindmapPreview.h({
            tag: "button",
            attrs: {
                type: "button",
                "data-layout": value,
                "aria-pressed": String(layout === value),
                onclick: () => {
                    // 選んでいる並べ方を押しても何もしない
                    if (layout !== value)
                        on.change(value);
                },
            },
            children: [BODY_LAYOUT_BUTTON[value]],
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "segment sbs-switch", role: "group", "aria-label": MindmapPreview.BODY_LAYOUT_LABEL },
            children: [button("inline"), button("side")],
        });
    }
    MindmapPreview.bodyDiffLayoutSwitch = bodyDiffLayoutSwitch;
})(MindmapPreview || (MindmapPreview = {}));
// 左右に並べた本文の差分。Markdown の本文を左に選んだ時点、右に今で描き、変えていない塊を同じ高さで向かい合わせる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 列の名前（列の頭に出し、列の読み上げの名前にも使う） */
    const SIDE_COLUMN_NAMES = { before: "選んだ時点", after: "今" };
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
        const beforeLines = MindmapPreview.linesOfText(before);
        const afterLines = MindmapPreview.linesOfText(after);
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
            // 描いた要素の行の印は塊の先頭を 1 行目として数えるので、塊の開始行から 1 を引いた数を足して本文の行に揃える
            const render = (block) => {
                const rendered = MindmapPreview.renderMarkdown(block.raw);
                for (const element of rendered.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)) {
                    element.setAttribute(MindmapPreview.LINE_ATTR, String(Number(element.getAttribute(MindmapPreview.LINE_ATTR)) + block.start - 1));
                }
                return rendered;
            };
            for (const block of row.left)
                pieces.push({ cell: entry.leftCell, block, lines: beforeLines, op: "del", rendered: render(block) });
            for (const block of row.right)
                pieces.push({ cell: entry.rightCell, block, lines: afterLines, op: "add", rendered: render(block) });
        }
        // 見出しの段は、左右の全ての塊を合わせた最も上の段から 1 つの差を求めて全てに当てる
        const shift = MindmapPreview.headingShift({ roots: pieces.map((piece) => piece.rendered) });
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
// 差分のミニマップ。差分の表示の間、詳細の本文のスクロール領域を包み、スクロールバーの外側に変わった箇所の印を並べた縦の帯を置く。印・印の無い所を押す・帯を押したまま上下に動かすと、履歴とハッシュを変えずに本文を送る。
var MindmapPreview;
(function (MindmapPreview) {
    /** 印の帯の向きの最小の長さ（px）。押せる的を保つ */
    const MINIMAP_MARK_MIN_PX = 12;
    /** 印が帯に収まらないほど多いときに縮める、最小の長さの下限（px） */
    const MINIMAP_MARK_FLOOR_PX = 4;
    /** 重なる印をずらすときに空ける間（px） */
    const MINIMAP_MARK_GAP_PX = 2;
    /** 印を押したとき、その箇所の上端を置く本文のスクロール領域の高さに対する割合 */
    const MINIMAP_JUMP_RATIO = 0.25;
    /** 飛んだ箇所に枠を付けておくミリ秒 */
    const MINIMAP_HIT_MS = 1600;
    /** 印の種類 → 読み上げの名前と `title` の頭 */
    const MINIMAP_KIND_NAME = {
        add: "足した箇所",
        del: "消した箇所",
        chg: "変わった箇所",
    };
    /** 印にする要素（キーの差分の行・本文の足した / 消した塊・箇条書きの足した項目・表の行・図の差分の枠・Raw の行・埋め込んだ HTML の範囲の差分） */
    const MINIMAP_TARGET_SELECTOR = [
        ".df-kv",
        ".md ins.df-blk",
        ".md del.df-blk",
        ".md li.df-li-add",
        ".md tr.df-add",
        ".md tr.df-del",
        ".diagram.df-changed",
        ".diagram.df-frame",
        ".df-raw .df-line.df-add",
        ".df-raw .df-line.df-del",
        ".html-diff-range",
    ].join(", ");
    /** 要素が見えているか（畳んだ Raw などは矩形を持たない） */
    function isRendered(element) {
        return element.getClientRects().length > 0;
    }
    MindmapPreview.isRendered = isRendered;
    /** 前に無かったキーの差分の行か（前の値が「（なし）」） */
    function isNewKey(row) {
        const was = row.querySelector("del.df-was");
        if (was === null)
            return false;
        // 読み上げだけに残した「前の値: 」は除く
        const text = [...was.childNodes]
            .filter((node) => !(node instanceof Element && node.classList.contains("sr-only")))
            .map((node) => node.textContent ?? "")
            .join("")
            .trim();
        return text === MindmapPreview.NO_VALUE;
    }
    /** 印にする要素の種類 */
    function minimapKindOf(element) {
        if (element.matches(".diagram, .html-diff-range"))
            return "chg";
        if (element.matches(".df-kv"))
            return isNewKey(element) ? "add" : "chg";
        return element.matches("del, .df-del") ? "del" : "add";
    }
    /** 本文のスクロール領域の中の差分の印を、文書の順にミニマップの印にまとめて返す */
    function minimapTargets(body) {
        const found = [];
        for (const element of body.querySelectorAll(MINIMAP_TARGET_SELECTOR)) {
            // 見えていない印と、Raw を出している図の枠（Raw の行を並べる）は飛ばす。Raw を畳んだ図は枠を印にする
            if (!isRendered(element))
                continue;
            if (element.matches(".diagram") && [...element.querySelectorAll(".df-raw")].some(isRendered))
                continue;
            // 埋め込んだ HTML の範囲の差分は、中の Raw の行を拾わず、範囲の差分の高さに印を 1 つ置く
            if (element.matches(".df-line") && element.closest(".html-diff-range") !== null)
                continue;
            const kind = minimapKindOf(element);
            const previous = found.at(-1);
            const follows = previous !== undefined && previous.frame === null && previous.last.nextElementSibling === element;
            if (previous !== undefined && follows && previous.kind === "del" && kind === "add" && element.matches(".df-blk") && previous.last.matches(".df-blk")) {
                // 消した塊のすぐ後ろの足した塊: 書き換えた箇所
                previous.kind = "chg";
                previous.last = element;
            }
            else if (previous !== undefined && follows && previous.kind === kind && !element.matches(".html-diff-range")) {
                // 続く同じ種類の塊・行
                previous.last = element;
            }
            else {
                found.push({ kind, first: element, last: element, frame: null });
            }
        }
        // 左右に並べた本文の印は列ごとに文書の順に並ぶので、高さの順に並べ直し、向かい合う消した塊と足した塊を「変わった」1 つにする
        if (body.querySelector(".sbs") !== null) {
            const topOf = (target) => target.first.getBoundingClientRect().top;
            found.sort((a, b) => topOf(a) - topOf(b));
            for (let position = found.length - 1; position > 0; position -= 1) {
                const upper = found[position - 1];
                const lower = found[position];
                if (upper === undefined || lower === undefined)
                    continue;
                const kinds = [upper.kind, lower.kind].sort().join();
                // 上の印の下端より上で始まる、もう片側の印
                if (kinds === "add,del" && topOf(lower) < upper.last.getBoundingClientRect().bottom) {
                    upper.kind = "chg";
                    found.splice(position, 1);
                }
            }
        }
        // HTML の本文の枠の中の印
        for (const frame of body.querySelectorAll("iframe.html-frame")) {
            if (!isRendered(frame))
                continue;
            for (const element of frame.contentDocument?.querySelectorAll("[data-df]") ?? []) {
                found.push({ kind: element.getAttribute("data-df") === "add" ? "add" : "chg", first: element, last: element, frame });
            }
        }
        return found;
    }
    MindmapPreview.minimapTargets = minimapTargets;
    /** 印が指す箇所の、本文の中身の上端からの位置と高さ */
    function minimapExtent({ body, target }) {
        const base = body.getBoundingClientRect().top - body.scrollTop;
        // 枠の中の要素の位置は枠の上端から測るため、枠の上端を足す
        const shift = target.frame === null ? 0 : target.frame.getBoundingClientRect().top;
        const top = target.first.getBoundingClientRect().top + shift - base;
        const bottom = target.last.getBoundingClientRect().bottom + shift - base;
        return { top, size: bottom - top };
    }
    /** 印の本文の中の位置と高さから、帯の中の印の始まりと長さを決める。位置と長さは本文の全体の高さに対する割合で置き、最小の長さと重なりを直す */
    function minimapLayout({ extents, total, length }) {
        // 印が多いときは最小の長さを詰める
        const min = Math.max(MINIMAP_MARK_FLOOR_PX, Math.min(MINIMAP_MARK_MIN_PX, Math.floor(length / Math.max(extents.length, 1)) - MINIMAP_MARK_GAP_PX));
        const placed = [];
        let end = 0;
        for (const extent of extents) {
            const size = Math.max(min, (extent.size / total) * length);
            const start = Math.max((extent.top / total) * length, end);
            placed.push({ start, size });
            end = start + size + MINIMAP_MARK_GAP_PX;
        }
        // 帯の終わりを出た印は、後ろから前へ詰める
        let limit = length;
        for (const mark of [...placed].reverse()) {
            mark.start = Math.max(0, Math.min(mark.start, limit - mark.size));
            limit = mark.start - MINIMAP_MARK_GAP_PX;
        }
        return placed;
    }
    MindmapPreview.minimapLayout = minimapLayout;
    /** 印の箇所まで本文を送り、その箇所を少しの間だけ枠で示す（履歴にもハッシュにも触れない） */
    function jumpToTarget({ body, target }) {
        const { top } = minimapExtent({ body, target });
        const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
        body.scrollTo({ top: Math.max(0, top - body.clientHeight * MINIMAP_JUMP_RATIO), behavior: reduce ? "auto" : "smooth" });
        // 枠の中の要素には枠の外のスタイルが当たらないため、示すのは枠の外の箇所だけ
        if (target.frame !== null)
            return;
        const hits = [];
        for (let element = target.first; element !== null; element = element.nextElementSibling) {
            hits.push(element);
            if (element === target.last)
                break;
        }
        for (const element of hits)
            element.classList.add("df-map-hit");
        window.setTimeout(() => hits.forEach((element) => element.classList.remove("df-map-hit")), MINIMAP_HIT_MS);
    }
    /** 帯のマウスの操作。押したまま上下に動かすと本文をスクロールバーと同じように送り、印の無い所を押すとその位置まで本文をすぐ送る */
    function bindMinimapPointer({ map, view, body }) {
        let drag = null;
        let dragged = false;
        /** ドラッグの間の指の位置に、見えている範囲の面が来るまで本文を送る */
        const dragTo = (clientY) => {
            if (drag === null)
                return;
            const rect = map.getBoundingClientRect();
            body.scrollTop = ((clientY - rect.top - drag.grab) / rect.height) * body.scrollHeight;
        };
        /** ドラッグを終える（離した・取り消された・押していない動きを受けた） */
        const endDrag = (event) => {
            if (drag === null || event.pointerId !== drag.id)
                return;
            drag = null;
            map.classList.remove("is-dragging");
            document.body.classList.remove("df-map-dragging");
            // 離した直後の click まで印を押した扱いにしないよう、次のコマで戻す
            requestAnimationFrame(() => {
                dragged = false;
            });
        };
        map.addEventListener("pointerdown", (event) => {
            // マウスの左ボタンだけ（タッチの端末ではドラッグしない）。本文が送れないときは何もしない
            if (event.pointerType !== "mouse" || event.button !== 0 || view.hidden)
                return;
            const face = view.getBoundingClientRect();
            const inside = event.clientY >= face.top && event.clientY <= face.bottom;
            // 面の中を押したときはつかんだ位置を保ち、外を押したときは面の中央を押した所に合わせる
            drag = { id: event.pointerId, startY: event.clientY, grab: inside ? event.clientY - face.top : face.height / 2 };
            dragged = false;
        });
        map.addEventListener("pointermove", (event) => {
            if (drag === null || event.pointerId !== drag.id)
                return;
            // ボタンを押していない動き（帯の外で離して pointerup が届かなかった）は、ドラッグを終えて送らない
            if ((event.buttons & 1) === 0) {
                endDrag(event);
                return;
            }
            // 押した位置から少し動くまでは、印を押しただけとして扱う
            if (!dragged && Math.abs(event.clientY - drag.startY) <= MindmapPreview.PRESS_SLOP_PX)
                return;
            if (!dragged) {
                dragged = true;
                map.setPointerCapture(event.pointerId);
                map.classList.add("is-dragging");
                document.body.classList.add("df-map-dragging");
            }
            dragTo(event.clientY);
        });
        map.addEventListener("pointerup", endDrag);
        map.addEventListener("pointercancel", endDrag);
        // ドラッグの間に帯が文書から外れたときも、ドラッグの見た目を戻す
        map.addEventListener("lostpointercapture", endDrag);
        // 印の無い所を動かさずに押して離すと、押した位置に見えている範囲の面の中央を合わせるまで本文をすぐ送る（タッチの端末も同じ）
        map.addEventListener("click", (event) => {
            if (dragged || view.hidden || event.target.closest(".df-map-m") !== null)
                return;
            const rect = map.getBoundingClientRect();
            body.scrollTop = ((event.clientY - rect.top) / rect.height) * body.scrollHeight - body.clientHeight / 2;
        });
        return { justDragged: () => dragged };
    }
    /** 本文のスクロール領域を `div.panel-scroll` で包んで返す。`shown` が真なら本文の右に帯を並べ、印があるときだけ出す */
    function diffMinimapFrame({ body, shown }) {
        const frame = MindmapPreview.h({ tag: "div", attrs: { class: "panel-scroll" }, children: [body] });
        if (!shown)
            return frame;
        // 見えている範囲の面
        const view = MindmapPreview.h({ tag: "span", attrs: { class: "df-map-view", "aria-hidden": "true" } });
        const map = MindmapPreview.h({
            tag: "div",
            attrs: { class: "df-map", role: "toolbar", "aria-orientation": "vertical", "aria-label": "変わった箇所", hidden: true },
            children: [view],
        });
        const pointer = bindMinimapPointer({ map, view, body });
        let targets = [];
        // タブの止まりにする印（最後に選んだ印）
        let current = 0;
        /** 見えている範囲の面を、本文の送りに合わせて置く */
        const placeView = () => {
            const scrollable = body.scrollHeight > body.clientHeight;
            view.hidden = !scrollable;
            if (!scrollable)
                return;
            view.style.top = `${(body.scrollTop / body.scrollHeight) * 100}%`;
            view.style.height = `${(body.clientHeight / body.scrollHeight) * 100}%`;
        };
        /** 印を集め直して並べ直す。印が無ければ帯ごと出さない */
        const rebuild = () => {
            const focused = map.contains(document.activeElement);
            // 後から足された子の高さの変化も見張る（同じ要素を重ねて見張っても 1 回だけ数える）
            for (const child of body.children)
                resized.observe(child);
            targets = minimapTargets(body);
            map.hidden = targets.length === 0;
            frame.classList.toggle("has-map", targets.length > 0);
            if (targets.length === 0) {
                map.replaceChildren(view);
                return;
            }
            current = Math.min(current, targets.length - 1);
            const placed = minimapLayout({
                extents: targets.map((target) => minimapExtent({ body, target })),
                total: body.scrollHeight,
                length: map.clientHeight,
            });
            const marks = targets.map((target, at) => {
                const name = `${MINIMAP_KIND_NAME[target.kind]}（${at + 1} / ${targets.length}）`;
                const { start, size } = placed[at];
                return MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: `df-map-m df-${target.kind}`,
                        type: "button",
                        "aria-label": name,
                        title: name,
                        tabindex: at === current ? "0" : "-1",
                        style: `top:${start}px;height:${size}px`,
                        onclick: () => {
                            // ドラッグで送った後に離した印は、飛ばない
                            if (pointer.justDragged())
                                return;
                            current = at;
                            jumpToTarget({ body, target });
                            rebuild();
                            map.querySelectorAll(".df-map-m")[at]?.focus();
                        },
                    },
                    children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } })],
                });
            });
            map.replaceChildren(view, ...marks);
            placeView();
            if (focused)
                marks[current]?.focus();
        };
        // 上下の矢印と Home / End で印の間を移る
        map.addEventListener("keydown", (event) => {
            const moves = { ArrowUp: current - 1, ArrowDown: current + 1, Home: 0, End: targets.length - 1 };
            const next = moves[event.key];
            if (next === undefined || next < 0 || next >= targets.length)
                return;
            event.preventDefault();
            current = next;
            const marks = [...map.querySelectorAll(".df-map-m")];
            marks.forEach((mark, at) => mark.setAttribute("tabindex", at === current ? "0" : "-1"));
            marks[current]?.focus();
        });
        frame.append(map);
        // 本文の高さが変わったとき（図の描き終わり・HTML の本文の枠の高さ・Raw の切り替え・パネルの幅）だけ置き直す
        let queued = false;
        const schedule = () => {
            if (queued)
                return;
            queued = true;
            requestAnimationFrame(() => {
                queued = false;
                rebuild();
            });
        };
        const resized = new ResizeObserver(schedule);
        resized.observe(body);
        new MutationObserver(schedule).observe(body, { childList: true, subtree: true });
        body.addEventListener("load", schedule, true);
        // 送るたびに動かすのは、見えている範囲の面だけ
        body.addEventListener("scroll", placeView, { passive: true });
        schedule();
        return frame;
    }
    MindmapPreview.diffMinimapFrame = diffMinimapFrame;
})(MindmapPreview || (MindmapPreview = {}));
// 保存待ちの印。保存待ちの編集がある項目・キー・案に、破線の枠と印と文字の札を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類 → 札の文字とアイコン */
    const PENDING_MARKS = {
        pending: { label: "保存待ち", icon: "layers" },
        remove: { label: "保存で削除", icon: "trash" },
        blocked: { label: "書き込めない", icon: "alert" },
    };
    /** 保存待ちの印。差分の印・コメントの印と形で見分けられるよう、破線の枠（書き込めない編集は実線）にする */
    function pendingEditMark({ kind, compact = false }) {
        const { label, icon: name } = PENDING_MARKS[kind];
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: `pm pm-${kind}${compact ? " pm-compact" : ""}`, title: compact ? label : null },
            children: [
                MindmapPreview.icon(name),
                compact ? MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [label] }) : label,
            ],
        });
    }
    MindmapPreview.pendingEditMark = pendingEditMark;
    /** 項目の保存待ちの印（無ければ null）。カードと表の行は文字つき、マップの節は印だけ */
    function editMarkOf({ edit, id, compact = false, }) {
        const kind = edit?.marks[id];
        return kind === undefined ? null : pendingEditMark({ kind, compact });
    }
    MindmapPreview.editMarkOf = editMarkOf;
    /** 一覧の上の帯に置く「項目を追加」。幅 480px 以下は印だけにし、文字を読み上げに残す */
    function addItemButton({ kind, onAdd }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn pe-add",
                type: "button",
                "data-kind": kind,
                "aria-label": `${MindmapPreview.KIND_LABEL[kind]}の項目を追加`,
                title: "項目を追加",
                onclick: () => onAdd(),
            },
            children: [MindmapPreview.icon("plus"), MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: ["項目を追加"] })],
        });
    }
    MindmapPreview.addItemButton = addItemButton;
    /** 追加する項目のタイトル（まだ書いていなければ「（タイトル未入力）」） */
    function addedTitle(item) {
        return item.title === "" ? "（タイトル未入力）" : item.title;
    }
    MindmapPreview.addedTitle = addedTitle;
    /** 追加する項目のカード（ボード・資料のカード）。ID の場所に「ID は保存で決まる」を置く破線の枠 */
    function addedCard({ item, mark, open, doc = false, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `card${doc ? " doc-card" : ""} pe-new`,
                type: "button",
                "data-new-id": item.id,
                onclick: () => open(item.id),
            },
            children: [
                MindmapPreview.h({ tag: doc ? "span" : "div", attrs: { class: "c-ttl" }, children: [addedTitle(item)] }),
                MindmapPreview.h({
                    tag: doc ? "span" : "div",
                    attrs: { class: "c-meta" },
                    children: [MindmapPreview.h({ tag: "span", attrs: { class: "pe-noid" }, children: ["ID は保存で決まる"] }), pendingEditMark({ kind: mark })],
                }),
            ],
        });
    }
    MindmapPreview.addedCard = addedCard;
})(MindmapPreview || (MindmapPreview = {}));
// 概要。次に検討する項目・ゴールまでの進捗・要見直し・保留・進行中のタスク・カテゴリー別の進捗のタイルを並べる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 縦に積む幅で出す、次に検討する項目の件数 */
    const NEXT_STACKED_COUNT = 3;
    /** 納品物のチェックリストに出す件数（これを超えたら資料を納品物で絞って開く） */
    const DELIVERABLE_LIMIT = 5;
    /** 小さなタイルに出す件数 */
    const MINI_LIMIT = 3;
    /** 次に検討する項目をタイルに横に並べる幅 */
    const WIDE_QUERY = "(min-width: 1101px)";
    /** 種類を表示するか（`visibleKinds` を渡さないときは全ての種類を表示する） */
    function isShown(props, kind) {
        return props.visibleKinds === undefined || props.visibleKinds.has(kind);
    }
    /** 絞った表へ移る `Route`（画面の既定の表示形式で開く） */
    function tableRoute(tab, filters, view = "table") {
        return { tab, view, id: null, full: false, filters, heading: null, diff: null };
    }
    /** 「すべて表示（N 件）」のボタン */
    function showAll(count, onClick) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "t-link", type: "button", onclick: onClick },
            children: [`すべて表示（${count} 件）`],
        });
    }
    /** 見出し（アイコンと名前）と、右端の「すべて表示」 */
    function tileHead(id, iconName, title, link) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "t-head" },
            children: [MindmapPreview.h({ tag: "h2", attrs: { id }, children: [MindmapPreview.icon(iconName), title] }), link],
        });
    }
    /** 1 行が項目のボタンの一覧（押すと詳細を開く） */
    function miniList(items, emptyText, open, marks) {
        if (items.length === 0)
            return MindmapPreview.emptyNote(emptyText);
        return MindmapPreview.h({
            tag: "ul",
            attrs: { class: "mini" },
            children: [
                ...items.slice(0, MINI_LIMIT).map((item) => MindmapPreview.h({
                    tag: "li",
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { type: "button", "data-id": item.id, onclick: () => open(item.id) },
                            children: [
                                MindmapPreview.statusMark(item.status),
                                MindmapPreview.h({ tag: "span", attrs: { class: "mt" }, children: [item.title] }),
                                MindmapPreview.markFor({ marks, id: item.id }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [MindmapPreview.icon("chev")] }),
                            ],
                        }),
                    ],
                })),
            ],
        });
    }
    /** 決定済みの数の棒（0〜100%） */
    function bar(settled, total) {
        const ratio = total === 0 ? 0 : (settled / total) * 100;
        return MindmapPreview.h({ tag: "i", children: [MindmapPreview.h({ tag: "b", attrs: { style: `width:${ratio}%` } })] });
    }
    /** 次に検討する項目のタイル */
    function nextTile(props) {
        const { index, on, marks } = props;
        const candidates = index.data.derived.next;
        const list = MindmapPreview.h({
            tag: "ol",
            attrs: { class: "next-list" },
            children: [
                ...candidates.map((candidate) => {
                    const item = index.byId.get(candidate.id)?.item;
                    return MindmapPreview.h({
                        tag: "li",
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { type: "button", "data-id": candidate.id, onclick: () => on.open(candidate.id) },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "nl-ttl" }, children: [candidate.title] }),
                                    MindmapPreview.h({
                                        tag: "span",
                                        attrs: { class: "nl-meta" },
                                        children: [
                                            MindmapPreview.markFor({ marks, id: candidate.id }),
                                            MindmapPreview.h({ tag: "span", children: [[item?.category, candidate.phase].filter(Boolean).join(" · ")] }),
                                            MindmapPreview.impactBadge(candidate.weight ?? undefined, true),
                                            MindmapPreview.h({
                                                tag: "span",
                                                attrs: { class: "fol", title: "後続の件数" },
                                                children: [MindmapPreview.icon("follow"), candidate.followers],
                                            }),
                                        ],
                                    }),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [MindmapPreview.icon("chev")] }),
                                ],
                            }),
                        ],
                    });
                }),
            ],
        });
        const tile = MindmapPreview.h({
            tag: "section",
            attrs: { id: "tile-next", class: "tile t-next", "aria-labelledby": "h-next" },
            children: [
                tileHead("h-next", "next", "次に検討する項目", candidates.length > 0 && isShown(props, "decisions")
                    ? showAll(candidates.length, () => on.navigate(tableRoute("decisions", { status: ["未決定"], ready: ["着手可能"] })))
                    : null),
                candidates.length > 0 ? list : MindmapPreview.emptyNote("次に検討する項目はありません。"),
            ],
        });
        // 横に並べる幅ではタイルの枠に収まるだけ、縦に積む幅では上位の数件だけを出す
        const fit = () => {
            const items = [...list.children];
            for (const item of items)
                item.hidden = false;
            if (matchMedia(WIDE_QUERY).matches) {
                const limit = tile.getBoundingClientRect().bottom - Number.parseFloat(getComputedStyle(tile).paddingBottom);
                for (const item of items)
                    if (item.getBoundingClientRect().bottom > limit)
                        item.hidden = true;
            }
            else {
                items.forEach((item, position) => {
                    item.hidden = position >= NEXT_STACKED_COUNT;
                });
            }
        };
        new ResizeObserver(fit).observe(tile);
        return tile;
    }
    /** ゴールまでの進捗のタイル（決定済みの数・フェーズごとの棒・納品物のチェックリスト）。ゴールが無いときはフェーズ別の進捗だけ */
    function goalTile(props) {
        const { index, on } = props;
        const { goal } = index.data.derived;
        const settled = goal.phase_progress.reduce((sum, cell) => sum + cell.settled, 0);
        const total = goal.phase_progress.reduce((sum, cell) => sum + cell.total, 0);
        const stageRows = goal.phase_progress.map((cell) => MindmapPreview.h({
            tag: "li",
            children: [
                MindmapPreview.h({ tag: "span", children: [cell.phase] }),
                bar(cell.settled, cell.total),
                MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [`${cell.settled}/${cell.total}`] }),
            ],
        }));
        // ゴールが無い: 見出しを替え、ゴールが無いことと全フェーズの決着の数だけを出す（納品物は出さない）
        if (!goal.has_goal) {
            return MindmapPreview.h({
                tag: "section",
                attrs: { id: "tile-goal", class: "tile t-goal", "aria-labelledby": "h-goal" },
                children: [
                    MindmapPreview.h({ tag: "h2", attrs: { id: "h-goal" }, children: [MindmapPreview.icon("flag"), "フェーズ別の進捗"] }),
                    MindmapPreview.h({ tag: "p", attrs: { class: "goal-none" }, children: ["ゴールは決まっていません"] }),
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "big" },
                        children: [settled, MindmapPreview.h({ tag: "small", children: [` / ${total}`] })],
                    }),
                    MindmapPreview.h({ tag: "p", attrs: { class: "big-sub" }, children: ["決定済み"] }),
                    MindmapPreview.h({ tag: "ul", attrs: { class: "stage-rows" }, children: [...stageRows] }),
                ],
            });
        }
        // ゴールがあるとき、設定のゴールは必ずある
        const deliverables = index.data.settings.goal?.deliverables ?? [];
        const remaining = new Set(goal.remaining_deliverables.map((entry) => entry.title));
        const doneCount = deliverables.filter((entry) => !remaining.has(entry.title)).length;
        const checklist = deliverables.slice(0, DELIVERABLE_LIMIT).map((entry) => {
            const done = !remaining.has(entry.title);
            const label = entry.doc !== undefined && index.byId.has(entry.doc)
                ? MindmapPreview.h({
                    tag: "button",
                    attrs: { type: "button", onclick: () => on.open(entry.doc) },
                    children: [entry.title],
                })
                : MindmapPreview.h({ tag: "span", children: [entry.title] });
            return MindmapPreview.h({
                tag: "li",
                attrs: { class: done ? "done" : "" },
                children: [MindmapPreview.icon(done ? "checked" : "unchecked"), label],
            });
        });
        return MindmapPreview.h({
            tag: "section",
            attrs: { id: "tile-goal", class: "tile t-goal", "aria-labelledby": "h-goal" },
            children: [
                MindmapPreview.h({ tag: "h2", attrs: { id: "h-goal" }, children: [MindmapPreview.icon("flag"), "ゴールまでの進捗"] }),
                MindmapPreview.h({
                    tag: "p",
                    attrs: { class: "big" },
                    children: [settled, MindmapPreview.h({ tag: "small", children: [` / ${total}`] })],
                }),
                MindmapPreview.h({ tag: "p", attrs: { class: "big-sub" }, children: ["決定済み"] }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "stage-rows" },
                    children: [...stageRows],
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "deliv" },
                    children: [
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "deliv-head" },
                            children: [
                                MindmapPreview.icon("box"),
                                "納品物",
                                MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [`${doneCount}/${deliverables.length}`] }),
                                deliverables.length > DELIVERABLE_LIMIT && isShown(props, "docs")
                                    ? showAll(deliverables.length, () => on.navigate(tableRoute("docs", { deliverable: ["納品物"] }, "cards")))
                                    : null,
                            ],
                        }),
                        MindmapPreview.h({ tag: "ul", attrs: { class: "checklist" }, children: [...checklist] }),
                    ],
                }),
            ],
        });
    }
    /** 件数と名前の小さなタイル（要見直し・保留・進行中のタスク） */
    function smallTile({ tileId, id, iconName, title, items, emptyText, link, open, marks, linked, }) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { id: tileId, class: "tile t-small", "aria-labelledby": id },
            children: [
                tileHead(id, iconName, title, items.length > 0 && linked ? showAll(items.length, link) : null),
                MindmapPreview.h({ tag: "p", attrs: { class: "num" }, children: [items.length] }),
                miniList(items, emptyText, open, marks),
            ],
        });
    }
    /** カテゴリー別の進捗の表（カテゴリーを行、フェーズを列にする） */
    function progressTile(props) {
        const { index, on } = props;
        const { settings, derived } = index.data;
        // 検討事項を表示しないときは、セルと行の見出しを押せなくする（数と棒は残す）
        const linked = isShown(props, "decisions");
        const rowOf = (entry) => MindmapPreview.h({
            tag: "tr",
            children: [
                MindmapPreview.h({
                    tag: "th",
                    attrs: { scope: "row" },
                    children: [
                        linked
                            ? MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "cat-link",
                                    type: "button",
                                    onclick: () => on.navigate(tableRoute("decisions", { category: [entry.category] })),
                                },
                                children: [entry.category],
                            })
                            : MindmapPreview.h({ tag: "span", attrs: { class: "cat-link" }, children: [entry.category] }),
                    ],
                }),
                ...entry.cells.map((cell) => cell.total === 0
                    ? MindmapPreview.h({ tag: "td", children: [MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["—"] })] })
                    : MindmapPreview.h({
                        tag: "td",
                        children: [
                            MindmapPreview.h({
                                tag: linked ? "button" : "span",
                                attrs: {
                                    class: "cell",
                                    type: linked ? "button" : null,
                                    "aria-label": `${entry.category} の ${cell.phase}: ${cell.settled}/${cell.total} 件決定済み`,
                                    onclick: linked
                                        ? () => on.navigate(tableRoute("decisions", {
                                            category: [entry.category],
                                            phase: [cell.phase],
                                        }))
                                        : null,
                                },
                                children: [
                                    bar(cell.settled, cell.total),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [`${cell.settled}/${cell.total}`] }),
                                ],
                            }),
                        ],
                    })),
                MindmapPreview.h({ tag: "td", attrs: { class: "tot mono" }, children: [`${entry.settled}/${entry.total}`] }),
            ],
        });
        // 対象ごとに見出しの行を立て、その対象のカテゴリーを続ける
        const groups = settings.targets.flatMap((target) => {
            const entries = derived.progress.filter((entry) => entry.total > 0 &&
                settings.categories.some((category) => category.name === entry.category && category.target === target.name));
            return entries.length === 0
                ? []
                : [
                    MindmapPreview.h({
                        tag: "tbody",
                        children: [
                            MindmapPreview.h({
                                tag: "tr",
                                attrs: { class: "tgt" },
                                children: [
                                    MindmapPreview.h({
                                        tag: "th",
                                        attrs: { colspan: settings.phases.length + 2, scope: "rowgroup" },
                                        children: [`${settings.target_label}: ${target.name}`],
                                    }),
                                ],
                            }),
                            ...entries.map(rowOf),
                        ],
                    }),
                ];
        });
        return MindmapPreview.h({
            tag: "section",
            attrs: { id: "tile-progress", class: "tile t-cat", "aria-labelledby": "h-cat" },
            children: [
                MindmapPreview.h({ tag: "h2", attrs: { id: "h-cat" }, children: [MindmapPreview.icon("layers"), "カテゴリー別の進捗"] }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "cat-wrap" },
                    children: [
                        MindmapPreview.h({
                            tag: "table",
                            attrs: { class: "cat-table" },
                            children: [
                                MindmapPreview.h({
                                    tag: "thead",
                                    children: [
                                        MindmapPreview.h({
                                            tag: "tr",
                                            children: [
                                                MindmapPreview.h({ tag: "th", attrs: { scope: "col" }, children: ["カテゴリー"] }),
                                                ...settings.phases.map((phase) => MindmapPreview.h({ tag: "th", attrs: { scope: "col" }, children: [phase] })),
                                                MindmapPreview.h({ tag: "th", attrs: { scope: "col", class: "tot" }, children: ["決定済み"] }),
                                            ],
                                        }),
                                    ],
                                }),
                                ...groups,
                            ],
                        }),
                    ],
                }),
            ],
        });
    }
    /** 概要の画面を返す */
    function overviewScreen(props) {
        const { index, on } = props;
        const { settings } = index.data;
        const decisions = index.data.decisions;
        const review = decisions.filter((item) => item.status === "要見直し");
        const hold = decisions.filter((item) => item.status === "保留");
        const running = index.data.tasks.filter((item) => item.status === "進行中");
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "overview" },
            children: [
                MindmapPreview.h({
                    tag: "header",
                    attrs: { class: "hero" },
                    children: [
                        // 話し合いの概要があるときだけ、題名の上に出す
                        settings.description !== undefined
                            ? MindmapPreview.h({
                                tag: "p",
                                attrs: { id: "overview-description", class: "hero-sub hero-desc" },
                                children: [settings.description],
                            })
                            : null,
                        MindmapPreview.h({ tag: "h1", children: [settings.summary] }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "bento" },
                    children: [
                        nextTile(props),
                        goalTile(props),
                        smallTile({
                            tileId: "tile-review",
                            id: "h-review",
                            iconName: "alert",
                            title: "要見直し",
                            items: review,
                            emptyText: "要見直しの検討事項はありません。",
                            link: () => on.navigate(tableRoute("decisions", { status: ["要見直し"] })),
                            open: on.open,
                            marks: props.marks,
                            linked: isShown(props, "decisions"),
                        }),
                        smallTile({
                            tileId: "tile-hold",
                            id: "h-hold",
                            iconName: "pause",
                            title: "保留",
                            items: hold,
                            emptyText: "保留の検討事項はありません。",
                            link: () => on.navigate(tableRoute("decisions", { status: ["保留"] })),
                            open: on.open,
                            marks: props.marks,
                            linked: isShown(props, "decisions"),
                        }),
                        smallTile({
                            tileId: "tile-running",
                            id: "h-run",
                            iconName: "play",
                            title: "進行中のタスク",
                            items: running,
                            emptyText: "進行中のタスクはありません。",
                            link: () => on.navigate(tableRoute("tasks", { status: ["進行中"] })),
                            open: on.open,
                            marks: props.marks,
                            linked: isShown(props, "tasks"),
                        }),
                        progressTile(props),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.overviewScreen = overviewScreen;
})(MindmapPreview || (MindmapPreview = {}));
// 検討事項。マップ（既定）・ボード・表で見る。マップは対象 → カテゴリー → フェーズ → 検討事項の木を ELK で配置して描く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 節の種類ごとの大きさ（幅・高さ） */
    const NODE_SIZE = {
        target: [130, 40],
        category: [150, 34],
        phase: [118, 26],
        item: [268, 48],
    };
    /** 設定に無い対象・カテゴリー・フェーズに付ける名前 */
    const UNSET = "（未設定）";
    /** 木を左から右へ、直角の枝で並べる ELK の設定 */
    const ELK_OPTIONS = {
        "elk.algorithm": "layered",
        "elk.direction": "RIGHT",
        "elk.edgeRouting": "ORTHOGONAL",
        "elk.layered.spacing.nodeNodeBetweenLayers": "36",
        "elk.spacing.nodeNode": "10",
        "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
        "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
        "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED",
        "elk.padding": "[top=24,left=24,bottom=24,right=24]",
    };
    /** 拡大・縮小 1 回の倍率の幅と、倍率の範囲 */
    const ZOOM_STEP = 0.15;
    const ZOOM_MIN = 0.4;
    const ZOOM_MAX = 1.5;
    /** ホイール 1 回の倍率の掛け率（図の拡大と同じ刻み） */
    const WHEEL_FACTOR = 1.12;
    /** マップの狭い幅の境（これ以下は字下げした縦の一覧） */
    const NARROW_QUERY = "(max-width: 900px)";
    /** 絞り込みの条件に合う検討事項が 1 件も無いときに、マップの枠と字下げの一覧に出す文 */
    const NO_SHOWN_DECISIONS_TEXT = "表示する検討事項はありません。";
    /** 対象 → カテゴリー → フェーズ → 検討事項の木を、渡した検討事項だけで組んで返す（ELK に渡す節と枝の形） */
    function buildDecisionTree({ index, decisions, }) {
        const { settings } = index.data;
        const shown = [...decisions].sort((a, b) => MindmapPreview.compareIds(a.id, b.id));
        /** 設定の並びの順（設定に無いものは最後） */
        const rankIn = (list, name) => {
            const position = list.indexOf(name);
            return position < 0 ? list.length : position;
        };
        const targetOf = (item) => settings.categories.find((category) => category.name === item.category)?.target ??
            item.target ??
            UNSET;
        const categoryOf = (item) => item.category ?? UNSET;
        const phaseOf = (item) => item.phase ?? UNSET;
        const unique = (values) => [...new Set(values)];
        const children = [];
        const edges = [];
        const add = (id, kind, label, parent, item) => {
            const [width, height] = NODE_SIZE[kind];
            children.push({ id, width, height, kind, label, item });
            if (parent !== null)
                edges.push({ id: `${parent}>${id}`, sources: [parent], targets: [id] });
        };
        const targets = unique(shown.map(targetOf)).sort((a, b) => rankIn(settings.targets.map((target) => target.name), a) -
            rankIn(settings.targets.map((target) => target.name), b));
        for (const target of targets) {
            const targetId = `target:${target}`;
            add(targetId, "target", target, null);
            const ofTarget = shown.filter((item) => targetOf(item) === target);
            const categories = unique(ofTarget.map(categoryOf)).sort((a, b) => rankIn(settings.categories.map((category) => category.name), a) -
                rankIn(settings.categories.map((category) => category.name), b));
            for (const category of categories) {
                const categoryId = `category:${target}/${category}`;
                add(categoryId, "category", category, targetId);
                const ofCategory = ofTarget.filter((item) => categoryOf(item) === category);
                const phases = unique(ofCategory.map(phaseOf)).sort((a, b) => rankIn(settings.phases, a) - rankIn(settings.phases, b));
                for (const phase of phases) {
                    const phaseId = `phase:${target}/${category}/${phase}`;
                    add(phaseId, "phase", phase, categoryId);
                    for (const item of ofCategory.filter((candidate) => phaseOf(candidate) === phase)) {
                        add(item.id, "item", item.title, phaseId, item);
                    }
                }
            }
        }
        return { id: "graph", layoutOptions: ELK_OPTIONS, children, edges };
    }
    MindmapPreview.buildDecisionTree = buildDecisionTree;
    // ───── マップの状態（描き直しても保つ） ─────
    /** マップの状態 */
    const mapState = {
        keyword: "",
        zoom: "fit",
        scroll: null,
        selected: null,
        lastPress: null,
    };
    /** 配置の結果（絞り込みの条件に合う検討事項の組み合わせごと） */
    const layoutCache = new Map();
    /** 配置を計算する（同じ状態の組み合わせは取っておく） */
    async function layoutOf(graph, key) {
        const cached = layoutCache.get(key);
        if (cached !== undefined)
            return cached;
        const laid = (await new ELK().layout(graph));
        layoutCache.set(key, laid);
        return laid;
    }
    /** 前提 → 後続の線の道筋（同じ列どうしは、節の右側にふくらむ弧でつなぐ） */
    function dependencyPath(from, to) {
        const fromX = (from.x ?? 0) + from.width;
        const fromY = (from.y ?? 0) + from.height / 2;
        // 同じ列
        if (Math.abs((from.x ?? 0) - (to.x ?? 0)) < 10) {
            const toY = (to.y ?? 0) + to.height / 2;
            const bulge = 28 + Math.min(60, Math.abs(toY - fromY) / 6);
            return `M${fromX},${fromY} C${fromX + bulge},${fromY} ${fromX + bulge},${toY} ${fromX},${toY}`;
        }
        const toX = to.x ?? 0;
        const toY = (to.y ?? 0) + to.height / 2;
        const reach = Math.max(60, Math.abs(toX - fromX) / 2);
        return `M${fromX},${fromY} C${fromX + reach},${fromY} ${toX - reach},${toY} ${toX},${toY}`;
    }
    /** SVG の要素を作る */
    function svg(tag, attrs) {
        const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
        for (const [name, value] of Object.entries(attrs))
            element.setAttribute(name, value);
        return element;
    }
    /** 木の節と枝を、配置された座標で描く。注目の起点（ロックした節、ロックしていなければ詳細を開いている節）の根までの枝と依存の線を強調し、ほかを薄くする */
    function drawMap({ laid, canvas, selected, lockedId, press, marks, comments, edit, }) {
        const positions = new Map(laid.children.map((node) => [node.id, node]));
        const parentOf = new Map(laid.edges.map((edge) => [edge.targets[0], edge.sources[0]]));
        // 強調の起点はロックした節。ロックしていなければ、詳細を開いている節
        const opened = selected;
        const lockedHere = lockedId !== null && positions.has(lockedId);
        if (lockedHere)
            selected = lockedId;
        // 選んだ項目から根までの節
        const chain = new Set();
        for (let id = selected; id !== null && id !== undefined; id = parentOf.get(id) ?? null)
            chain.add(id);
        const edgeSvg = svg("svg", {
            class: "edges",
            width: String(laid.width ?? 0),
            height: String(laid.height ?? 0),
            "aria-hidden": "true",
        });
        for (const edge of laid.edges) {
            const section = edge.sections?.[0];
            if (section === undefined)
                continue;
            const points = [section.startPoint, ...(section.bendPoints ?? []), section.endPoint];
            const [source, target] = [edge.sources[0], edge.targets[0]];
            edgeSvg.append(svg("path", {
                class: `edge-tree${chain.has(source) && chain.has(target) ? " rel" : ""}`,
                d: `M${points.map((point) => `${point.x},${point.y}`).join(" L")}`,
            }));
        }
        // 依存の線: 前提 → 後続。選んだ項目に関わる線を強め、その上を小さな玉が流れる
        const near = new Set(chain);
        let flowId = 0;
        for (const node of laid.children) {
            if (node.kind !== "item" || node.item === undefined)
                continue;
            for (const prerequisite of node.item.depends_on ?? []) {
                const from = positions.get(prerequisite);
                if (from === undefined)
                    continue;
                const related = selected !== null && (selected === prerequisite || selected === node.id);
                const id = `dep-${(flowId += 1)}`;
                edgeSvg.append(svg("path", { id, class: `edge-dep${related ? " rel" : ""}`, d: dependencyPath(from, node) }));
                if (related) {
                    near.add(prerequisite);
                    near.add(node.id);
                    // 選んだ項目から外へ向かって、玉をゆっくり流す（入ってくる線は向きを逆にする）
                    const incoming = node.id === selected;
                    for (const begin of [0, 1.6]) {
                        const dot = svg("circle", { class: "flow-dot", r: "2.6" });
                        const motion = svg("animateMotion", {
                            dur: "3.2s",
                            begin: `${begin}s`,
                            repeatCount: "indefinite",
                            ...(incoming ? { keyPoints: "1;0", keyTimes: "0;1", calcMode: "linear" } : {}),
                        });
                        motion.append(svg("mpath", { href: `#${id}` }));
                        dot.append(motion);
                        edgeSvg.append(dot);
                    }
                }
            }
        }
        const keyword = mapState.keyword.toLowerCase();
        const nodes = laid.children.map((node) => {
            const style = `left:${node.x ?? 0}px;top:${node.y ?? 0}px;width:${node.width}px;height:${node.height}px`;
            const rel = near.has(node.id) ? " rel" : "";
            if (node.kind !== "item" || node.item === undefined) {
                return MindmapPreview.h({
                    tag: "div",
                    attrs: { class: `map-node n-${node.kind}${rel}`, "data-node": node.id, style },
                    children: [MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: [node.label] })],
                });
            }
            const item = node.item;
            const hit = keyword !== "" && item.title.toLowerCase().includes(keyword);
            return MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: `map-node n-item${opened === item.id ? " sel" : ""}${lockedHere && lockedId === item.id ? " locked" : ""}${hit ? " hit" : ""}${rel}${edit?.marks[item.id] === "remove" ? " pe-removing" : ""}`,
                    type: "button",
                    "data-node": item.id,
                    style,
                    title: `${item.title}（${item.status ?? ""}）`,
                    onclick: (event) => press(item.id, event),
                },
                children: [
                    // 鍵は節の右上の内側に置く。開いた鍵は詳細を開いている節にカーソルを乗せたときだけ、閉じた鍵はロック中いつも出す（出し分けは CSS）
                    MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "lk", "aria-hidden": "true" },
                        children: [MindmapPreview.icon(lockedHere && lockedId === item.id ? "lock" : "unlock")],
                    }),
                    MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "r1" },
                        children: [
                            MindmapPreview.statusMark(item.status),
                            MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: [item.title] }),
                        ],
                    }),
                    MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "r2" },
                        children: [
                            MindmapPreview.markFor({ marks, id: item.id }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
                            MindmapPreview.h({ tag: "span", children: [item.status ?? ""] }),
                            item.weight === undefined ? null : MindmapPreview.h({ tag: "span", children: [`影響度 ${item.weight}`] }),
                            MindmapPreview.editMarkOf({ edit, id: item.id, compact: true }),
                            comments === undefined ? null : MindmapPreview.commentPlace({ id: item.id, count: comments[item.id] }),
                        ],
                    }),
                ],
            });
        });
        canvas.classList.toggle("focusing", selected !== null);
        // ロック中は、開いた鍵を出さない
        canvas.classList.toggle("has-lock", lockedHere);
        canvas.style.width = `${laid.width ?? 0}px`;
        canvas.style.height = `${laid.height ?? 0}px`;
        canvas.replaceChildren(edgeSvg, ...nodes);
    }
    /** 狭い幅で使う、字下げした縦の一覧 */
    function outline({ index, decisions, open, marks, comments, edit, }) {
        const tree = buildDecisionTree({ index, decisions });
        const nodeOf = new Map(tree.children.map((node) => [node.id, node]));
        const childrenOf = new Map();
        for (const edge of tree.edges) {
            const list = childrenOf.get(edge.sources[0]) ?? [];
            const child = nodeOf.get(edge.targets[0]);
            if (child !== undefined)
                list.push(child);
            childrenOf.set(edge.sources[0], list);
        }
        /** 節と、その下の節を字下げして並べる */
        const entry = (node) => {
            const label = node.kind === "item" && node.item !== undefined
                ? MindmapPreview.h({
                    tag: "button",
                    attrs: { type: "button", "data-id": node.id, onclick: () => open(node.id) },
                    children: [
                        MindmapPreview.statusMark(node.item.status),
                        MindmapPreview.h({ tag: "span", children: [node.label] }),
                        MindmapPreview.markFor({ marks, id: node.id }),
                        MindmapPreview.editMarkOf({ edit, id: node.id, compact: true }),
                        comments === undefined ? null : MindmapPreview.commentPlace({ id: node.id, count: comments[node.id] }),
                    ],
                })
                : MindmapPreview.h({ tag: "div", attrs: { class: `o-${node.kind}` }, children: [node.label] });
            const below = childrenOf.get(node.id) ?? [];
            return MindmapPreview.h({
                tag: "li",
                children: [
                    label,
                    below.length > 0 ? MindmapPreview.h({ tag: "ul", children: [...below.map(entry)] }) : null,
                ],
            });
        };
        const roots = tree.children.filter((node) => node.kind === "target");
        return MindmapPreview.h({
            tag: "nav",
            attrs: { class: "map-outline", "aria-label": "検討事項の一覧" },
            // 絞り込みの条件に合う検討事項が無いときは、対象の見出しを並べず空の旨を出す
            children: [roots.length > 0 ? MindmapPreview.h({ tag: "ul", children: [...roots.map(entry)] }) : MindmapPreview.emptyNote(NO_SHOWN_DECISIONS_TEXT)],
        });
    }
    /** ホイール 1 回で変えた後のマップの倍率と、マウスの下の点を残す枠のスクロールの位置を返す */
    function wheelZoom({ scale, deltaY, point, scroll, }) {
        // 奥へ回すと拡大、手前へ回すと縮小。下限は、全体を表示の倍率が ZOOM_MIN を下回っているときにその倍率で止める
        const factor = deltaY < 0 ? WHEEL_FACTOR : 1 / WHEEL_FACTOR;
        const next = Math.min(ZOOM_MAX, Math.max(Math.min(ZOOM_MIN, scale), scale * factor));
        // マウスの下の点が、倍率を変えた後も同じ位置に残るようにスクロールの位置を求める
        const ratio = next / scale;
        return {
            scale: next,
            scroll: {
                left: (scroll.left + point.x) * ratio - point.x,
                top: (scroll.top + point.y) * ratio - point.y,
            },
        };
    }
    MindmapPreview.wheelZoom = wheelZoom;
    /** マップの道具の行（表示形式・キーワード）と、マップの枠・拡大の道具・絞り込みのドロワーを作る */
    function mapView({ index, route, on, marks, comments, lockedId, removed = [], edit = null }, { shown, chips, makeDrawer, }) {
        const root = MindmapPreview.h({ tag: "div", attrs: { class: "map-view-root" } });
        const frame = MindmapPreview.h({ tag: "div", attrs: { class: "map-frame" } });
        // 絞り込みの条件に合う検討事項が無いときに、マップの枠の中央に出す文
        const emptyNotice = MindmapPreview.h({ tag: "p", attrs: { class: "empty map-empty", hidden: true }, children: [NO_SHOWN_DECISIONS_TEXT] });
        const canvas = MindmapPreview.h({ tag: "div", attrs: { id: "decision-map", class: "map-canvas", role: "group", "aria-label": "検討事項のマップ" } });
        const sizer = MindmapPreview.h({ tag: "div", attrs: { class: "map-sizer" }, children: [canvas] });
        const wrap = MindmapPreview.h({ tag: "div", attrs: { class: "map-wrap" }, children: [sizer] });
        // 全体を表示のボタン（押された状態を見た目に出す）
        const fitButton = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn ghost",
                type: "button",
                "aria-pressed": "false",
                onclick: () => {
                    mapState.zoom = mapState.zoom === "fit" ? 1 : "fit";
                    applyZoom();
                },
            },
            children: ["全体を表示"],
        });
        let outlineElement = outline({ index, decisions: shown, open: on.open, marks, comments, edit });
        let current = null;
        /** キーワードに当たった検討事項か */
        const isHit = (item) => mapState.keyword !== "" && item.title.toLowerCase().includes(mapState.keyword.toLowerCase());
        /** 絞り込みのドロワー（キーワードに一致した件数を値ごとに添える） */
        const drawerHit = (row) => isHit(row);
        let drawerElement = makeDrawer(drawerHit);
        /** キーワードが変わったとき、ドロワーの件数だけを組み直す */
        const refreshDrawer = () => {
            if (drawerElement === null)
                return;
            const next = makeDrawer(drawerHit);
            if (next === null)
                return;
            drawerElement.replaceWith(next);
            drawerElement = next;
        };
        /** 拡大率を決めて、マップの大きさと拡大を当てる（全体を表示は、枠に木の全体が収まる倍率） */
        const applyZoom = () => {
            if (current === null)
                return;
            const width = current.width ?? 0;
            const height = current.height ?? 0;
            const scale = mapState.zoom === "fit"
                ? Math.min(1, (wrap.clientWidth - 16) / width, (wrap.clientHeight - 16) / height)
                : mapState.zoom;
            // 全体を表示は右と下に決まった余白、数値の倍率は枠の幅・高さの分の余白（マップが枠より小さくても、ホイールで拡大した点を残せるだけ送れる）
            const marginRight = mapState.zoom === "fit" ? 240 : wrap.clientWidth;
            const marginBottom = mapState.zoom === "fit" ? 160 : wrap.clientHeight;
            sizer.style.width = `${width * scale + marginRight}px`;
            sizer.style.height = `${height * scale + marginBottom}px`;
            canvas.style.transform = `scale(${scale})`;
            fitButton.setAttribute("aria-pressed", String(mapState.zoom === "fit"));
        };
        /** 今当たっているマップの倍率（全体を表示は、求めて当てた倍率） */
        const shownScale = () => mapState.zoom === "fit" ? Number.parseFloat(canvas.style.transform.slice(6)) : mapState.zoom;
        /** 効いているロック（幅 900px 以下では詳細が全面に出るので、ロックしない） */
        const lockedNow = () => (matchMedia(MindmapPreview.LOCK_QUERY).matches ? lockedId : null);
        /** ロックした節の鍵（描き直しても今の要素を引く） */
        const lockedKey = () => canvas.querySelector(".n-item.locked .lk");
        /** 節（余白なら `null`）を押した。素早い 2 回目は、描き直しで節が消えた位置でも前に押した節への 2 回押しとして、ネットワークと同じ規則で入口へ渡す */
        const press = (hit, event) => {
            // 幅 900px 以下の字下げの一覧ではロックせず、節を開く
            if (!matchMedia(MindmapPreview.LOCK_QUERY).matches) {
                if (hit !== null)
                    on.open(hit);
                return;
            }
            const pressInfo = { time: performance.now(), x: event.clientX, y: event.clientY, id: hit };
            const pressed = MindmapPreview.resolvePress({ last: mapState.lastPress, press: pressInfo });
            mapState.lastPress = pressInfo;
            if (on.lock(pressed) === "shake")
                MindmapPreview.shakeKeyElement(lockedKey);
        };
        /** 配置を求めて、マップを描く。注目の起点（ロックした節、ロックしていなければ詳細を開いている節）が変わってその節があるときは、その節が中央に来るようにマップを送り、それ以外は描き直す前のスクロールの位置へ戻す */
        const draw = async () => {
            outlineElement.replaceWith((outlineElement = outline({ index, decisions: shown, open: on.open, marks, comments, edit })));
            if (MindmapPreview.missingLibraries(["elkjs"]).length > 0)
                return;
            const key = shown.map((item) => item.id).join(",");
            const graph = buildDecisionTree({ index, decisions: shown });
            emptyNotice.hidden = graph.children.length > 0;
            current = await layoutOf(graph, key);
            drawMap({ laid: current, canvas, selected: route.id, lockedId: lockedNow(), press, marks, comments, edit });
            applyZoom();
            // 中央へ送る節は、ロックした節。ロックしていなければ詳細を開いている節（ロック中にほかの節を開いても送り直さない）
            const locked = lockedNow();
            const anchorId = locked !== null && current.children.some((n) => n.id === locked) ? locked : route.id;
            const node = anchorId === null ? undefined : current.children.find((n) => n.id === anchorId);
            const scale = shownScale();
            if (node !== undefined && anchorId !== mapState.selected) {
                wrap.scrollTo({
                    left: ((node.x ?? 0) + node.width / 2) * scale - wrap.clientWidth / 2,
                    top: ((node.y ?? 0) + node.height / 2) * scale - wrap.clientHeight / 2,
                });
            }
            else if (mapState.scroll !== null) {
                wrap.scrollTo(mapState.scroll);
            }
            mapState.selected = anchorId;
        };
        // ===== 道具の行 =====
        const keyword = MindmapPreview.h({
            tag: "input",
            attrs: {
                class: "input map-q",
                type: "search",
                placeholder: "タイトルで強調",
                value: mapState.keyword,
                "aria-label": "タイトルで強調するキーワード",
            },
        });
        let timer;
        keyword.addEventListener("input", () => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => {
                mapState.keyword = keyword.value;
                // 当たった節の色と、ドロワーの一致した件数だけを更新する
                for (const button of canvas.querySelectorAll("button.n-item")) {
                    const item = index.byId.get(button.dataset["node"] ?? "")?.item;
                    button.classList.toggle("hit", item !== undefined && isHit(item));
                }
                refreshDrawer();
            }, 150);
        });
        const toolbarElement = MindmapPreview.toolbar([
            { key: "board", label: "ボード" },
            { key: "map", label: "マップ" },
            { key: "table", label: "表" },
        ], route, on.view, edit === null ? null : MindmapPreview.addItemButton({ kind: "decisions", onAdd: edit.onAdd }));
        toolbarElement.insertBefore(keyword, toolbarElement.querySelector(".pe-add"));
        /** 拡大・縮小・全体を表示のボタン（マップの枠の外に置く） */
        const zoomBar = MindmapPreview.h({
            tag: "div",
            attrs: { class: "zoom", role: "group", "aria-label": "拡大率" },
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": "縮小",
                        onclick: () => {
                            const base = mapState.zoom === "fit" ? 0.6 : mapState.zoom;
                            mapState.zoom = Math.max(ZOOM_MIN, Math.round((base - ZOOM_STEP) * 100) / 100);
                            applyZoom();
                        },
                    },
                    children: ["−"],
                }),
                fitButton,
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": "拡大",
                        onclick: () => {
                            const base = mapState.zoom === "fit" ? 0.6 : mapState.zoom;
                            mapState.zoom = Math.min(ZOOM_MAX, Math.round((base + ZOOM_STEP) * 100) / 100);
                            applyZoom();
                        },
                    },
                    children: ["＋"],
                }),
            ],
        });
        wrap.addEventListener("scroll", () => {
            mapState.scroll = { left: wrap.scrollLeft, top: wrap.scrollTop };
        });
        // ホイールで拡大・縮小する（ページを動かさないよう既定の動作を止め、マウスの下の点を残す）
        wrap.addEventListener("wheel", (event) => {
            // 横にだけ回したときは、枠の横スクロールに任せる
            if (event.deltaY === 0)
                return;
            event.preventDefault();
            // マップを描く前は、倍率が無い
            if (current === null)
                return;
            const box = wrap.getBoundingClientRect();
            const next = wheelZoom({
                scale: shownScale(),
                deltaY: event.deltaY,
                point: { x: event.clientX - box.left - wrap.clientLeft, y: event.clientY - box.top - wrap.clientTop },
                scroll: { left: wrap.scrollLeft, top: wrap.scrollTop },
            });
            // 数値の倍率にして（「全体を表示」の押された状態を外す）、スクロールの位置を当てる
            mapState.zoom = next.scale;
            applyZoom();
            wrap.scrollTo(next.scroll);
        }, { passive: false });
        // 余白を押したとき: 押した節が描き直しで消えた位置への素早い 2 回目は、その節への 2 回押しとして扱う。ロックの規則で、全体の表示へ戻す（`blank`）か鍵を震わせる
        MindmapPreview.enableDragScroll(wrap, (event) => press(null, event));
        // elkjs が読めない: 知らせを出し、表示形式を表に切り替えると読めることを伝える
        const notice = MindmapPreview.missingLibraries(["elkjs"]).length > 0
            ? MindmapPreview.h({
                tag: "div",
                children: [
                    MindmapPreview.libraryNotice({ names: ["elkjs"], what: "マップ" }),
                    MindmapPreview.emptyNote("表示形式を「表」に切り替えると、検討事項を表示できます。"),
                ],
            })
            : null;
        frame.append(emptyNotice, wrap);
        if (notice !== null)
            frame.hidden = true;
        MindmapPreview.append({
            parent: root,
            children: [
                toolbarElement,
                chips,
                notice,
                MindmapPreview.removedBand({ items: removed }),
                frame,
                zoomBar,
                outlineElement,
                drawerElement,
            ],
        });
        // 拡大率が「全体を表示」のときは、枠の大きさが変わるたびに倍率を求め直す
        new ResizeObserver(() => {
            if (mapState.zoom === "fit")
                applyZoom();
        }).observe(wrap);
        void draw();
        return root;
    }
    /** 検討事項の表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
    function decisionColumns({ index, open }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        return [
            common.id,
            common.title(),
            common.status(MindmapPreview.DECISION_STATUSES),
            common.target,
            common.category,
            common.phase,
            {
                key: "weight",
                label: "影響度",
                nowrap: true,
                filterable: true,
                order: ["大", "中", "小"],
                priority: 3,
                get: (row) => (typeof row["weight"] === "string" ? row["weight"] : undefined),
                cell: (row) => MindmapPreview.impactBadge(typeof row["weight"] === "string" ? row["weight"] : undefined),
            },
            {
                key: "ready",
                label: "着手可否",
                nowrap: true,
                filterable: true,
                order: ["着手可能", "前提待ち", "なし"],
                priority: 2,
                // 前提が全て決着した未決定（build が計算した次の候補）は着手可能、ほかの未決定は前提待ち、未決定以外はなし
                get: (row) => (row.status !== "未決定" ? "なし" : index.readyIds.has(row.id) ? "着手可能" : "前提待ち"),
            },
            {
                key: "depends_on",
                label: "前提",
                priority: 3,
                get: (row) => MindmapPreview.rowTexts(row, "depends_on"),
                cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.rowTexts(row, "depends_on"), open),
            },
            common.tags,
        ];
    }
    MindmapPreview.decisionColumns = decisionColumns;
    /** 絞り込みの条件に合う検討事項の ID（マップが描く節。ロックした節を描いているかの判定にも使う） */
    function shownDecisionIds({ index, filters }) {
        const columns = decisionColumns({ index, open: () => undefined });
        return new Set(MindmapPreview.filterRows({ rows: index.data.decisions, columns, filters }).map((row) => row.id));
    }
    MindmapPreview.shownDecisionIds = shownDecisionIds;
    /** 検討事項の画面を返す */
    function decisionsScreen(props) {
        const { index, route, on, marks, comments, filters, drawerOpen, removed = [], edit = null } = props;
        const columns = decisionColumns({ index, open: on.open });
        // 絞り込みの条件に合う検討事項を、マップ・ボード・表に同じ結果で渡す
        const shown = MindmapPreview.filterRows({ rows: index.data.decisions, columns, filters });
        // 表以外の表示形式では、ツールバーの下に条件のチップの行を置く
        const chips = MindmapPreview.activeConditionCount(filters) > 0
            ? MindmapPreview.filterChips({
                filters,
                labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
                onFilter: on.filter,
            })
            : null;
        const makeDrawer = (hit) => MindmapPreview.screenDrawer({
            drawerOpen,
            rows: index.data.decisions,
            columns: columns.filter((column) => column.filterable === true),
            textColumns: MindmapPreview.textColumns(columns),
            filters,
            shown: shown.length,
            hit,
            onFilter: on.filter,
            onClose: on.closeDrawer,
        });
        if (route.view === "map") {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "screen decisions" },
                children: [mapView(props, { shown, chips, makeDrawer })],
            });
        }
        const toolbarElement = MindmapPreview.toolbar([
            { key: "board", label: "ボード" },
            { key: "map", label: "マップ" },
            { key: "table", label: "表" },
        ], route, on.view, edit === null ? null : MindmapPreview.addItemButton({ kind: "decisions", onAdd: edit.onAdd }));
        if (route.view === "board") {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "screen decisions" },
                children: [
                    toolbarElement,
                    chips,
                    MindmapPreview.removedBand({ items: removed }),
                    MindmapPreview.board({
                        columns: MindmapPreview.boardColumns({
                            items: shown,
                            statuses: [...MindmapPreview.DECISION_STATUSES],
                            statusFilter: filters["status"] ?? [],
                        }),
                        card: (item) => MindmapPreview.boardCard({
                            index,
                            item,
                            meta: [item.category, item.phase],
                            links: item.depends_on ?? [],
                            open: on.open,
                            mark: marks?.[item.id],
                            comments,
                            edit,
                        }),
                        emptyText: "検討事項はありません。",
                        added: MindmapPreview.addedCards({ edit, statuses: MindmapPreview.DECISION_STATUSES, open: on.open }),
                    }),
                    makeDrawer(),
                ],
            });
        }
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen decisions" },
            children: [
                toolbarElement,
                MindmapPreview.removedBand({ items: removed }),
                MindmapPreview.managedTable({
                    kind: "decisions",
                    columns,
                    rows: shown,
                    filters,
                    onFilter: on.filter,
                    open: on.open,
                    marks,
                    ...(comments === undefined ? {} : { comments }),
                    ...(edit === null ? {} : { edit }),
                }),
                makeDrawer(),
            ],
        });
    }
    MindmapPreview.decisionsScreen = decisionsScreen;
})(MindmapPreview || (MindmapPreview = {}));
// タスク。ボード（既定）と表で見る。
var MindmapPreview;
(function (MindmapPreview) {
    /** 状態の並びの順に、状態ごとの項目を返す（項目が 0 件の列も返す。列の中は連番の順）。`excluded` は状態の条件で外した列 */
    function boardColumns({ items, statuses, statusFilter = [], }) {
        return statuses.map((status) => ({
            status,
            items: items
                .filter((item) => item.status === status)
                .sort((a, b) => MindmapPreview.compareIds(a.id, b.id)),
            excluded: statusFilter.length > 0 && !statusFilter.includes(status),
        }));
    }
    MindmapPreview.boardColumns = boardColumns;
    /** ボードのカード（押すと詳細を開く）。`links` が項目を指す ID の並びなら、その題を添える */
    function boardCard({ index, item, meta, links, open, mark, comments, edit, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `${item.id === MindmapPreview.currentSelection() ? "card selected" : "card"}${edit?.marks[item.id] === "remove" ? " pe-removing" : ""}`,
                type: "button",
                "data-id": item.id,
                onclick: () => open(item.id),
            },
            children: [
                MindmapPreview.h({ tag: "div", attrs: { class: "c-ttl" }, children: [item.title] }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "c-meta" },
                    children: [
                        mark === undefined ? null : MindmapPreview.diffMark({ kind: mark }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
                        ...meta.filter(Boolean).map((value) => MindmapPreview.h({ tag: "span", children: [value] })),
                        MindmapPreview.editMarkOf({ edit, id: item.id }),
                        comments === undefined ? null : MindmapPreview.commentPlace({ id: item.id, count: comments[item.id] }),
                    ],
                }),
                links.length > 0
                    ? MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "c-for" },
                        children: [
                            ...links.map((id) => MindmapPreview.h({
                                tag: "div",
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
                                    ` ${MindmapPreview.titleOf(index, id)}`,
                                ],
                            })),
                        ],
                    })
                    : null,
            ],
        });
    }
    MindmapPreview.boardCard = boardCard;
    /** 状態ごとの列にカードを並べたボード。横に送れ、背景のドラッグで動かせる */
    function board({ columns, card, emptyText, added, }) {
        const element = MindmapPreview.h({
            tag: "div",
            attrs: { class: "board", style: `--cols:${columns.length}` },
            children: [
                ...columns.map(({ status, items, excluded = false }) => MindmapPreview.h({
                    tag: "section",
                    attrs: { class: "board-col", "aria-label": status },
                    children: [
                        MindmapPreview.h({
                            tag: "h2",
                            children: [
                                MindmapPreview.statusMark(status),
                                status,
                                MindmapPreview.h({ tag: "span", attrs: { class: "n" }, children: [items.length] }),
                            ],
                        }),
                        // 状態の条件で外した列は、列を残して外した旨を出す
                        ...(excluded
                            ? [MindmapPreview.emptyNote("状態の条件で外しています。")]
                            : [
                                ...(added?.(status) ?? []),
                                ...(items.length > 0 ? items.map(card) : (added?.(status) ?? []).length > 0 ? [] : [MindmapPreview.emptyNote(emptyText)]),
                            ]),
                    ],
                })),
            ],
        });
        MindmapPreview.enableDragScroll(element);
        return element;
    }
    MindmapPreview.board = board;
    /** 表示形式の切り替えを置いた道具の行 */
    function toolbar(views, route, onView, 
    /** 右端に置く「項目を追加」（編集の入口があるとき） */
    addButton = null) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "toolbar" },
            children: [MindmapPreview.viewSwitch({ views, current: route.view, onChange: onView }), addButton],
        });
    }
    MindmapPreview.toolbar = toolbar;
    /** 追加する項目が属する状態の列（状態を持たない・並びに無い状態は最初の列）に置く、追加する項目のカード */
    function addedCards({ edit, statuses, open, doc = false, }) {
        if (edit === null || edit === undefined || edit.adds.length === 0)
            return undefined;
        return (status) => edit.adds
            .filter((item) => (statuses.includes(item.status ?? "") ? item.status : statuses[0]) === status)
            .map((item) => MindmapPreview.addedCard({ item, mark: edit.marks[item.id] ?? "pending", open, doc }));
    }
    MindmapPreview.addedCards = addedCards;
    /** タスクの表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
    function taskColumns({ index, open }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        return [
            common.id,
            common.title(),
            common.status(MindmapPreview.TASK_STATUSES),
            common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
            {
                key: "for",
                label: "進める検討事項",
                priority: 3,
                get: (row) => MindmapPreview.rowTexts(row, "for"),
                cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.rowTexts(row, "for"), open),
            },
            common.target,
            common.category,
            common.phase,
            common.tags,
        ];
    }
    MindmapPreview.taskColumns = taskColumns;
    /** タスクの画面を返す */
    function tasksScreen({ index, route, on, marks, comments, filters, drawerOpen, removed = [], edit = null }) {
        const columns = taskColumns({ index, open: on.open });
        // 絞り込みの条件に合うタスクを、ボードと表に同じ結果で渡す
        const shown = MindmapPreview.filterRows({ rows: index.data.tasks, columns, filters });
        // ボードでは、ツールバーの下に条件のチップの行を置く（表は表の上に持つ）
        const chips = route.view === "board" && MindmapPreview.activeConditionCount(filters) > 0
            ? MindmapPreview.filterChips({
                filters,
                labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
                onFilter: on.filter,
            })
            : null;
        const content = route.view === "board"
            ? board({
                columns: boardColumns({
                    items: shown,
                    statuses: [...MindmapPreview.TASK_STATUSES],
                    statusFilter: filters["status"] ?? [],
                }),
                card: (item) => boardCard({
                    index,
                    item,
                    meta: [item.kind, item.category],
                    links: item.for ?? [],
                    open: on.open,
                    mark: marks?.[item.id],
                    comments,
                    edit,
                }),
                emptyText: "タスクはありません。",
                added: addedCards({ edit, statuses: MindmapPreview.TASK_STATUSES, open: on.open }),
            })
            : MindmapPreview.managedTable({
                kind: "tasks",
                columns,
                rows: shown,
                filters,
                onFilter: on.filter,
                open: on.open,
                marks,
                ...(comments === undefined ? {} : { comments }),
                ...(edit === null ? {} : { edit }),
            });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen tasks" },
            children: [
                toolbar([
                    { key: "board", label: "ボード" },
                    { key: "table", label: "表" },
                ], route, on.view, edit === null ? null : MindmapPreview.addItemButton({ kind: "tasks", onAdd: edit.onAdd })),
                chips,
                MindmapPreview.removedBand({ items: removed }),
                content,
                MindmapPreview.screenDrawer({
                    drawerOpen,
                    rows: index.data.tasks,
                    columns: columns.filter((column) => column.filterable === true),
                    textColumns: MindmapPreview.textColumns(columns),
                    filters,
                    shown: shown.length,
                    onFilter: on.filter,
                    onClose: on.closeDrawer,
                }),
            ],
        });
    }
    MindmapPreview.tasksScreen = tasksScreen;
})(MindmapPreview || (MindmapPreview = {}));
// 資料。カード（既定）・ボード・表で見る。納品物を先頭に印付きで並べ、資料の状態を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 納品物を先頭に、それぞれ連番の順に並べた資料を返す */
    function orderDocs(docs) {
        return [...docs].sort((a, b) => Number(b.deliverable === true) - Number(a.deliverable === true) || MindmapPreview.compareIds(a.id, b.id));
    }
    MindmapPreview.orderDocs = orderDocs;
    /** 納品物の列の値 */
    const DELIVERABLE_VALUES = ["納品物", "納品物以外"];
    /** 形式の列の値（札の文言と同じ） */
    const BODY_FORMAT_VALUES = ["MD", "HTML"];
    /** 形式の列の値。`body` の拡張子から決め、本文を持たなければ空にする */
    function bodyFormatLabel(body) {
        const format = MindmapPreview.bodyFormatOf(typeof body === "string" ? body : undefined);
        return format === null ? "" : format === "html" ? "HTML" : "MD";
    }
    /** 資料の表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
    function docColumns(index) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        return [
            common.id,
            common.title(),
            {
                key: "deliverable",
                label: "納品物",
                nowrap: true,
                filterable: true,
                order: DELIVERABLE_VALUES,
                priority: 2,
                get: (row) => (row["deliverable"] === true ? "納品物" : "納品物以外"),
                cell: (row) => row["deliverable"] === true ? MindmapPreview.deliverableBadge() : MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["—"] }),
            },
            common.status(MindmapPreview.DOC_STATUSES),
            common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
            {
                key: "body_format",
                label: "形式",
                nowrap: true,
                filterable: true,
                order: BODY_FORMAT_VALUES,
                priority: 2,
                get: (row) => bodyFormatLabel(row["body"]),
                cell: (row) => MindmapPreview.bodyFormatBadgeOf(typeof row["body"] === "string" ? row["body"] : undefined) ??
                    MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["—"] }),
            },
            common.target,
            common.category,
            common.phase,
            common.tags,
        ];
    }
    MindmapPreview.docColumns = docColumns;
    /** 資料の画面を返す */
    function docsScreen({ index, route, on, marks, comments, filters, drawerOpen, removed = [], edit = null }) {
        const columns = docColumns(index);
        const toolbarElement = MindmapPreview.toolbar([
            { key: "cards", label: "カード" },
            { key: "board", label: "ボード" },
            { key: "table", label: "表" },
        ], route, on.view, edit === null ? null : MindmapPreview.addItemButton({ kind: "docs", onAdd: edit.onAdd }));
        // 絞り込みの条件に合う資料を、カード・ボード・表に同じ結果で渡す
        const shown = MindmapPreview.filterRows({ rows: index.data.docs, columns, filters });
        const drawer = MindmapPreview.screenDrawer({
            drawerOpen,
            rows: index.data.docs,
            columns: columns.filter((column) => column.filterable === true),
            textColumns: MindmapPreview.textColumns(columns),
            filters,
            shown: shown.length,
            onFilter: on.filter,
            onClose: on.closeDrawer,
        });
        if (route.view === "table") {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "screen docs" },
                children: [
                    toolbarElement,
                    MindmapPreview.removedBand({ items: removed }),
                    MindmapPreview.managedTable({
                        kind: "docs",
                        columns,
                        rows: shown,
                        filters,
                        onFilter: on.filter,
                        open: on.open,
                        marks,
                        ...(comments === undefined ? {} : { comments }),
                        ...(edit === null ? {} : { edit }),
                    }),
                    drawer,
                ],
            });
        }
        // カード・ボードでは、ツールバーの下に条件のチップの行を置く
        const chips = MindmapPreview.activeConditionCount(filters) > 0
            ? MindmapPreview.filterChips({
                filters,
                labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
                onFilter: on.filter,
            })
            : null;
        const content = route.view === "board"
            ? // 列ごとに納品物を先頭に並べ直す
                MindmapPreview.board({
                    columns: MindmapPreview.boardColumns({
                        items: shown,
                        statuses: [...MindmapPreview.DOC_STATUSES],
                        statusFilter: filters["status"] ?? [],
                    }).map((column) => ({ ...column, items: orderDocs(column.items) })),
                    card: (item) => docCard({ index, doc: item, open: on.open, inBoard: true, mark: marks?.[item.id], comments, edit }),
                    emptyText: "資料はありません。",
                    added: MindmapPreview.addedCards({ edit, statuses: MindmapPreview.DOC_STATUSES, open: on.open, doc: true }),
                })
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "doc-grid" },
                children: [
                    ...(edit?.adds ?? []).map((item) => MindmapPreview.addedCard({ item, mark: edit?.marks[item.id] ?? "pending", open: on.open, doc: true })),
                    ...(shown.length > 0
                        ? orderDocs(shown).map((row) => docCard({ index, doc: row, open: on.open, inBoard: false, mark: marks?.[row.id], comments, edit }))
                        : (edit?.adds ?? []).length > 0
                            ? []
                            : [MindmapPreview.h({ tag: "p", attrs: { class: "no-match" }, children: ["該当する資料はありません。別の条件を試してください。"] })]),
                ],
            });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen docs" },
            children: [toolbarElement, chips, MindmapPreview.removedBand({ items: removed }), content, drawer],
        });
    }
    MindmapPreview.docsScreen = docsScreen;
    /** 資料のカード（納品物の印・種類・状態・カテゴリー・フェーズ・タグ）。ボードの中では列で状態が分かるので状態の印を出さず、開いている資料に選択の印を付ける */
    function docCard({ index, doc, open, inBoard, mark, comments, edit, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `card doc-card${doc.deliverable === true ? " deliv-card" : ""}${inBoard && doc.id === MindmapPreview.currentSelection() ? " selected" : ""}${doc.withdrawn === true ? " is-withdrawn" : ""}${edit?.marks[doc.id] === "remove" ? " pe-removing" : ""}`,
                type: "button",
                "data-id": doc.id,
                onclick: () => open(doc.id),
            },
            children: [
                doc.deliverable === true ? MindmapPreview.deliverableBadge() : null,
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "doc-kind" },
                    children: [MindmapPreview.icon(doc.kind === "図" ? "graph" : "cards"), doc.kind ?? "", MindmapPreview.bodyFormatBadgeOf(doc.body)],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "c-ttl" }, children: [doc.title] }),
                // 取り下げた資料は、差分の表示によらず差分の印より前に札を置く
                doc.withdrawn === true ? MindmapPreview.withdrawnBadge() : null,
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "c-meta" },
                    children: [
                        mark === undefined ? null : MindmapPreview.diffMark({ kind: mark }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [doc.id] }),
                        inBoard ? null : MindmapPreview.statusBadge(doc.status),
                        MindmapPreview.h({ tag: "span", children: [[doc.category, doc.phase].filter(Boolean).join(" · ")] }),
                        MindmapPreview.editMarkOf({ edit, id: doc.id }),
                        comments === undefined ? null : MindmapPreview.commentPlace({ id: doc.id, count: comments[doc.id] }),
                    ],
                }),
                (doc.tags ?? []).length > 0 ? MindmapPreview.h({ tag: "span", attrs: { class: "c-tags" }, children: [MindmapPreview.tagList(doc.tags)] }) : null,
            ],
        });
    }
})(MindmapPreview || (MindmapPreview = {}));
// 調査・用語集・メモ・会話ログ。種類ごとの列を持つ表だけを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 調査・用語集・メモ・会話ログの表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
    function recordColumns({ index, kind, open, }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        const related = (label) => ({
            key: "related",
            label,
            priority: 3,
            get: (row) => MindmapPreview.rowTexts(row, "related"),
            cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.rowTexts(row, "related"), open),
        });
        const columnsOf = {
            research: [
                common.id,
                common.title(),
                common.text("question", "問い", { minWidth: "16em" }),
                common.text("conclusion", "結論", { minWidth: "18em" }),
                common.text("confidence", "確度", {
                    filterable: true,
                    nowrap: true,
                    priority: 2,
                    order: ["高", "中", "低"],
                }),
                common.tags,
            ],
            terms: [
                common.id,
                common.title("用語"),
                common.text("meaning", "意味", { minWidth: "18em", priority: 1 }),
                {
                    key: "aliases",
                    label: "別名",
                    priority: 3,
                    get: (row) => MindmapPreview.rowTexts(row, "aliases"),
                    cell: (row) => MindmapPreview.tagList(MindmapPreview.rowTexts(row, "aliases")),
                },
                {
                    key: "avoid",
                    label: "使わない表記",
                    priority: 3,
                    get: (row) => MindmapPreview.rowTexts(row, "avoid"),
                    cell: (row) => MindmapPreview.tagList(MindmapPreview.rowTexts(row, "avoid")),
                },
                common.tags,
            ],
            notes: [
                common.id,
                common.title(),
                common.text("content", "内容", { minWidth: "18em", priority: 2 }),
                common.tags,
                related("関連"),
            ],
            logs: [
                common.id,
                common.text("date", "日付", { nowrap: true, priority: 2 }),
                common.title(),
                common.tags,
                related("更新した項目"),
            ],
        };
        return columnsOf[kind];
    }
    MindmapPreview.recordColumns = recordColumns;
    /** 調査・用語集・メモ・会話ログの画面を返す。種類は `route.tab` で決まる */
    function recordsScreen({ index, route, on, filters, drawerOpen, marks, comments, removed = [], edit = null, }) {
        const kind = route.tab;
        const columns = recordColumns({ index, kind, open: on.open });
        // 絞り込みの条件に合う項目を表に渡す
        const shown = MindmapPreview.filterRows({ rows: index.data[kind], columns, filters });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen records" },
            children: [
                MindmapPreview.removedBand({ items: removed }),
                MindmapPreview.managedTable({
                    kind,
                    columns,
                    rows: shown,
                    filters,
                    onFilter: on.filter,
                    open: on.open,
                    marks,
                    ...(comments === undefined ? {} : { comments }),
                    ...(edit === null ? {} : { edit, addInTable: true }),
                }),
                MindmapPreview.screenDrawer({
                    drawerOpen,
                    rows: index.data[kind],
                    columns: columns.filter((column) => column.filterable === true),
                    textColumns: MindmapPreview.textColumns(columns),
                    filters,
                    shown: shown.length,
                    onFilter: on.filter,
                    onClose: on.closeDrawer,
                }),
            ],
        });
    }
    MindmapPreview.recordsScreen = recordsScreen;
})(MindmapPreview || (MindmapPreview = {}));
// 詳細パネル・詳細の全画面の編集の表示。キーごとの入力と、検討事項の案の入力、項目の削除。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類ごとに編集の表示へ並べるキー（読む表示と同じ順） */
    const EDITABLE_KEYS = {
        decisions: [
            { key: "status", input: "select" },
            { key: "title", input: "text" },
            { key: "target", input: "select" },
            { key: "category", input: "select" },
            { key: "phase", input: "select" },
            { key: "tags", input: "tags" },
            { key: "depends_on", input: "refs" },
            { key: "related", input: "refs" }, // 390: 検討事項にも関連の入力を置く
            { key: "options", input: "options" },
            { key: "answer", input: "textarea" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        tasks: [
            { key: "status", input: "select" },
            { key: "title", input: "text" },
            { key: "target", input: "select" },
            { key: "kind", input: "select" },
            { key: "tags", input: "tags" },
            { key: "related", input: "refs" }, // 390: タスクにも関連の入力を置く
            { key: "result", input: "textarea" },
            { key: "body", input: "body" },
        ],
        research: [
            { key: "title", input: "text" },
            { key: "question", input: "textarea" },
            { key: "conclusion", input: "textarea" },
            { key: "confidence", input: "select" },
            { key: "tags", input: "tags" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        docs: [
            { key: "status", input: "select" },
            { key: "title", input: "text" },
            { key: "kind", input: "text" },
            { key: "deliverable", input: "check" },
            { key: "tags", input: "tags" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        terms: [
            { key: "title", input: "text" },
            { key: "meaning", input: "textarea" },
            { key: "aliases", input: "refs" },
            { key: "tags", input: "tags" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        notes: [
            { key: "title", input: "text" },
            { key: "content", input: "textarea" },
            { key: "tags", input: "tags" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        logs: [
            { key: "title", input: "text" },
            { key: "date", input: "text" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
    };
    /** 項目を追加する入力に並べるキー（スキーマで必須のキーと、状態・タグ・本文。検討事項は案も） */
    const ADD_KEYS = {
        decisions: ["status", "title", "options", "tags", "body"],
        tasks: ["status", "title", "kind", "tags", "body"],
        research: ["title", "question", "tags", "body"],
        docs: ["status", "title", "kind", "deliverable", "tags", "body"],
        terms: ["title", "meaning", "tags", "body"],
        notes: ["title", "content", "tags", "body"],
        logs: ["title", "date", "body"],
    };
    /** 追加する項目の最初の値（スキーマで必須のキーを、保存で弾かれない値で埋める） */
    function addDefaults({ kind, today }) {
        switch (kind) {
            case "decisions":
                return { status: "未整理" };
            case "tasks":
                return { status: "未着手", kind: "作業" };
            case "research":
                return { question: "" };
            case "docs":
                return { status: "下書き", kind: "文書", deliverable: false, body: "" };
            case "terms":
                return { meaning: "" };
            case "notes":
                return { content: "" };
            case "logs":
                return { date: today };
        }
    }
    MindmapPreview.addDefaults = addDefaults;
    /** タスクの種類の選択肢 */
    const TASK_KINDS = ["作業", "調査", "検証"];
    /** 調査の確からしさの選択肢 */
    const CONFIDENCES = ["高", "中", "低"];
    /** 空にできない文字のキー（空のときは溜めず、誤りを出す） */
    const REQUIRED_TEXT_KEYS = new Set(["title"]);
    /** 値を並べるキーの入力欄に出す案内 */
    const CHIP_HINTS = {
        tags: "タグを入れる",
        depends_on: "ID を入れる",
        related: "ID を入れる",
        aliases: "別名を入れる",
    };
    /** 種類ごとに編集の表示へ並べるキーと入力の種類（`id`・`created`・`updated` は含めない） */
    function editableKeys(kind) {
        return EDITABLE_KEYS[kind].map((entry) => ({ ...entry }));
    }
    MindmapPreview.editableKeys = editableKeys;
    /** キーの呼び名（用語のタイトルは「用語」、取り下げる項目の理由は「取り下げた理由」） */
    function labelOf({ kind, key }) {
        if (key === "title" && kind === "terms")
            return "用語";
        if (key === "reason" && kind !== "decisions" && kind !== "tasks")
            return "取り下げた理由";
        return MindmapPreview.KEY_LABELS[key] ?? key;
    }
    /** 要素の id に使えない文字を外す */
    function safeId(text) {
        return text.replace(/[^A-Za-z0-9]/g, "");
    }
    MindmapPreview.safeId = safeId;
    /** 書き込めない理由（警告の印と文言）。`changed` は AI が書き換えた日時を添える */
    function blockedNote({ blocked, updated, onOpen, }) {
        if (blocked.reason === "changed") {
            const when = updated === null ? "" : `${MindmapPreview.formatJst(updated)} `;
            return MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-blocked-note" },
                children: [MindmapPreview.icon("alert"), `溜めた後の ${when}に AI がこの項目を書き換えたため、書き込めません。取り消してから入れ直してください。`],
            });
        }
        if (blocked.reason === "referenced" && blocked.refs.length > 0) {
            const refs = blocked.refs.flatMap((ref, position) => [
                position > 0 ? "・" : null,
                onOpen === undefined
                    ? MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [ref] })
                    : MindmapPreview.h({ tag: "button", attrs: { class: "idlink", type: "button", onclick: () => onOpen(ref) }, children: [ref] }),
            ]);
            return MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-blocked-note" },
                children: [MindmapPreview.icon("alert"), ...refs, " が指しているため削除できません。指している項目から外してください。"],
            });
        }
        return MindmapPreview.h({ tag: "p", attrs: { class: "pe-blocked-note" }, children: [MindmapPreview.icon("alert"), blocked.detail] });
    }
    MindmapPreview.blockedNote = blockedNote;
    /** 項目とスレッドが使っているタグを、サーバーの `normalize_tag` と同じく NFKC と小文字にそろえ、重なりを除いて件数の多い順（同じ件数は名前の順）に並べる */
    function usedTags({ index, threads }) {
        const counts = new Map();
        /** 1 つの項目かスレッドの `tags` を数える（同じタグを表記を変えて 2 回持っても 1 件） */
        const count = (tags) => {
            for (const name of new Set(tags.map((tag) => tag.normalize("NFKC").toLowerCase()))) {
                counts.set(name, (counts.get(name) ?? 0) + 1);
            }
        };
        for (const { item } of index.byId.values())
            count(MindmapPreview.tagNames(item.tags));
        for (const thread of threads)
            count(thread.tags);
        return [...counts.keys()].sort((left, right) => (counts.get(right) ?? 0) - (counts.get(left) ?? 0) || (left < right ? -1 : left > right ? 1 : 0));
    }
    MindmapPreview.usedTags = usedTags;
    /** 編集の表示（`form`）を返す。入力欄を離れたとき（選ぶ・チェックは選んだとき）に `on.change` で溜める編集を知らせる */
    function detailEditForm(props) {
        const { kind, item, removing, on } = props;
        const adding = item.id.startsWith(MindmapPreview.NEW_ID_PREFIX);
        const keys = adding
            ? EDITABLE_KEYS[kind].filter((entry) => ADD_KEYS[kind].includes(entry.key))
            : EDITABLE_KEYS[kind];
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "pe-form",
                "data-id": item.id,
                novalidate: true,
                "aria-label": adding ? `${MindmapPreview.KIND_LABEL[kind]}を追加` : `${item.id} を編集`,
                onsubmit: (event) => event.preventDefault(),
            },
        });
        if (removing) {
            form.append(MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-hint", role: "status" },
                children: [MindmapPreview.icon("trash"), "削除を溜めています。削除を取り消すと編集できます。"],
            }));
        }
        // 編集できないキー（ID・作成・更新・編集した人）
        form.append(MindmapPreview.h({
            tag: "dl",
            attrs: { class: "pe-fixed" },
            children: [
                MindmapPreview.h({ tag: "dt", children: ["ID"] }),
                MindmapPreview.h({ tag: "dd", attrs: { class: "mono" }, children: [adding ? "保存で決まる" : item.id] }),
                ...(adding
                    ? []
                    : [
                        MindmapPreview.h({ tag: "dt", children: ["作成"] }),
                        MindmapPreview.h({ tag: "dd", children: [MindmapPreview.formatJst(item.created)] }),
                        MindmapPreview.h({ tag: "dt", children: ["更新"] }),
                        MindmapPreview.h({
                            tag: "dd",
                            children: [`${MindmapPreview.formatJst(item.updated)}（${item.updated_by === "user" ? "利用者" : "AI"}）`],
                        }),
                    ]),
            ],
        }));
        for (const { key, input } of keys) {
            form.append(input === "options" ? optionsField(props) : keyField({ props, key, input }));
        }
        if (!adding)
            form.append(removeSection(props));
        // 溜めた知らせ（読み上げにも伝える。使う側が文言を入れる）
        form.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-form-msg", role: "status" } }));
        return form;
    }
    MindmapPreview.detailEditForm = detailEditForm;
    /** キーの名前の行（名前と、必須の印・保存待ちの印） */
    function labelRow({ props, key, controlId, name, }) {
        const mark = props.marks[key];
        const required = REQUIRED_TEXT_KEYS.has(key);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-label-row" },
            children: [
                MindmapPreview.h({
                    tag: "label",
                    attrs: { for: controlId },
                    children: [name, required ? MindmapPreview.h({ tag: "span", attrs: { class: "pe-req" }, children: ["必須"] }) : null],
                }),
                mark === undefined ? null : MindmapPreview.pendingEditMark({ kind: mark, compact: true }),
            ],
        });
    }
    /** キー 1 つの入力欄 */
    function keyField({ props, key, input, }) {
        const { kind, item, settings, removing, on } = props;
        const controlId = `pe-${safeId(item.id)}-${key}`;
        const name = labelOf({ kind, key });
        const mark = props.marks[key];
        const wrap = MindmapPreview.h({
            tag: "div",
            attrs: {
                class: `pe-field${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}${input === "check" ? " pe-check" : ""}`,
                "data-key": key,
            },
        });
        const record = item;
        const value = key === "body" ? (props.body ?? "") : record[key];
        let control;
        /** キーの編集を知らせる。空のタイトルは溜めず、失敗の赤の枠と誤りを出す */
        const commit = (next) => {
            if (key === "title") {
                const empty = typeof next !== "string" || next.trim() === "";
                if (empty)
                    control.setAttribute("aria-invalid", "true");
                else
                    control.removeAttribute("aria-invalid");
                wrap.classList.toggle("is-invalid", empty);
                if (empty)
                    return;
            }
            on.change({ op: "set", key, value: next });
        };
        if (input === "select") {
            const options = selectOptions({ kind, key, settings });
            const optional = !(key === "status" || key === "kind");
            const select = MindmapPreview.h({
                tag: "select",
                attrs: { id: controlId, name: key, class: "input", disabled: removing },
                children: [
                    optional ? MindmapPreview.h({ tag: "option", attrs: { value: "", selected: value === undefined || value === null }, children: ["（なし）"] }) : null,
                    ...options.map((option) => MindmapPreview.h({ tag: "option", attrs: { value: option, selected: option === value }, children: [option] })),
                ],
            });
            select.addEventListener("change", () => commit(select.value === "" ? null : select.value));
            control = select;
        }
        else if (input === "check") {
            const box = MindmapPreview.h({
                tag: "input",
                attrs: { id: controlId, name: key, type: "checkbox", checked: value === true, disabled: removing },
            });
            box.addEventListener("change", () => commit(box.checked));
            control = box;
        }
        else if (key === "related") {
            // 390: 関連は、相手・種類・いつ読むかを 1 件ずつ入れる（案 A は 1 件 1 行、案 B は ID のチップから開く）
            control = (document.body.dataset.rel === "b" ? relatedChipsInput : relatedRowsInput)({
                controlId,
                name,
                item,
                values: Array.isArray(value) ? value : [],
                disabled: removing,
                onChange: (next) => commit(next),
            });
        }
        else if (input === "tags" || input === "refs") {
            control = MindmapPreview.chipsInput({
                controlId,
                name,
                hint: CHIP_HINTS[key] ?? `${name}を入れる`,
                values: Array.isArray(value) ? value : [],
                suggestions: key === "tags" ? props.usedTags : null,
                monospace: key !== "tags",
                mainToggle: key === "tags",
                disabled: removing,
                onChange: (next) => commit(next),
            });
        }
        else if (input === "textarea" || input === "body") {
            const area = MindmapPreview.h({
                tag: "textarea",
                attrs: {
                    id: controlId,
                    name: key,
                    class: `input pe-text${input === "body" ? " pe-body" : ""}`,
                    rows: input === "body" ? 8 : 3,
                    disabled: removing,
                },
            });
            area.value = typeof value === "string" ? value : "";
            area.addEventListener("change", () => {
                // 本文は空の文字列で書く。そのほかは空にして離れたらキーを消す
                commit(area.value === "" && input !== "body" ? null : area.value);
            });
            control = area;
        }
        else {
            const text = MindmapPreview.h({
                tag: "input",
                attrs: {
                    id: controlId,
                    name: key,
                    class: "input",
                    type: key === "date" ? "date" : "text",
                    value: typeof value === "string" ? value : "",
                    autocomplete: "off",
                    disabled: removing,
                },
            });
            text.addEventListener("change", () => commit(text.value === "" && !REQUIRED_TEXT_KEYS.has(key) ? null : text.value));
            control = text;
        }
        wrap.append(labelRow({ props, key, controlId, name }));
        if (key === "title") {
            // 空のタイトルは溜めず、離れたときに失敗の赤の枠と誤りを出す
            const errorId = `${controlId}-error`;
            const error = MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-error", id: errorId },
                children: [MindmapPreview.icon("alert"), "タイトルを書いてください。"],
            });
            control.setAttribute("required", "");
            control.setAttribute("aria-describedby", errorId);
            // 追加の入力を開いたとき、最初にフォーカスを置く入力欄
            control.setAttribute("data-first", "");
            wrap.append(control, error);
        }
        else {
            wrap.append(control);
        }
        const blocked = props.blocked[key];
        if (blocked !== undefined)
            wrap.append(blockedNote({ blocked, updated: item.updated }));
        const failure = props.errors[key];
        if (failure !== undefined) {
            wrap.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [MindmapPreview.icon("alert"), failure] }));
        }
        return wrap;
    }
    /** 390: 関連の 1 件を `{to, type, when}` にそろえる（前の形式の ID の文字列は相手だけ） */
    function relationValue(raw) {
        return typeof raw === "string" ? { to: raw, type: "", when: "" } : { to: raw.to ?? "", type: raw.type ?? "", when: raw.when ?? "" };
    }
    /** 390: 関連の 1 件の誤り（無ければ null）。`others` は同じ並びのほかの行の相手 */
    function relationError(entry, itemId, others) {
        const index = MindmapPreview.mockIndex390;
        if (entry.to.trim() === "")
            return "相手の ID を入れてください。";
        if (entry.to === itemId)
            return "この項目自身は指せません。";
        if (index !== undefined && !index.byId.has(entry.to))
            return `${entry.to} の項目が見つかりません。`;
        if (others.includes(entry.to))
            return `${entry.to} はほかの行で指しています。`;
        if (entry.type === "")
            return "種類を選んでください。";
        if (entry.when.trim() === "")
            return "いつ読むかを 1 文で書いてください。";
        return null;
    }
    /** 390: 種類を選ぶ入力欄 */
    function relationTypeSelect({ id, value, label, disabled }) {
        return MindmapPreview.h({
            tag: "select",
            attrs: { id, class: "input", "aria-label": label, disabled },
            children: [
                MindmapPreview.h({ tag: "option", attrs: { value: "", selected: value === "" }, children: ["（選択）"] }),
                ...Object.entries(MindmapPreview.RELATION_TYPES).map(([type, spec]) => MindmapPreview.h({
                    tag: "option",
                    attrs: { value: type, selected: type === value },
                    children: [spec.label],
                })),
            ],
        });
    }
    /** 390: 相手の ID の候補（ID とタイトル） */
    function relationIdList(listId, itemId) {
        const index = MindmapPreview.mockIndex390;
        const ids = index === undefined ? [] : [...index.byId.keys()].filter((id) => id !== itemId).sort(MindmapPreview.compareIds);
        return MindmapPreview.h({
            tag: "datalist",
            attrs: { id: listId },
            children: ids.map((id) => MindmapPreview.h({ tag: "option", attrs: { value: id, label: index.byId.get(id).item.title } })),
        });
    }
    /** 390: 全ての行がそろったら並びを知らせ、そろったかを返す（中身が全て空の行は外す） */
    function commitRelations(entries, itemId, onChange) {
        const filled = entries.filter((entry) => !(entry.to === "" && entry.type === "" && entry.when.trim() === ""));
        const ok = filled.every((entry, at) => relationError(entry, itemId, filled.filter((_, other) => other !== at).map((other) => other.to)) === null);
        if (ok)
            onChange(filled.map((entry) => ({ to: entry.to, type: entry.type, when: entry.when.trim() })));
        return ok;
    }
    /** 390 案 A: 関連 1 件を 1 行にし、相手の ID・種類・いつ読むかと削除を並べ、末尾に「関連を追加」を置く */
    function relatedRowsInput({ controlId, name, item, values, disabled, onChange }) {
        const entries = values.map(relationValue);
        const listId = `${controlId}-ids`;
        const index = MindmapPreview.mockIndex390;
        const group = MindmapPreview.h({ tag: "div", attrs: { class: "rel-edit", id: controlId, role: "group", "aria-label": name } });
        const head = MindmapPreview.h({
            tag: "div",
            attrs: { class: "rel-edit-head", "aria-hidden": "true" },
            children: ["相手", "種類", "いつ読むか"].map((text) => MindmapPreview.h({ tag: "span", children: [text] })),
        });
        const rows = MindmapPreview.h({ tag: "ul", attrs: { class: "rel-rows" } });
        const empty = MindmapPreview.h({ tag: "p", attrs: { class: "rel-empty" }, children: ["関連はありません。"] });
        /** 行ごとの誤り（触った行だけ）・相手のタイトル・同時に変更の補足を今の値で描き直す */
        const refresh = () => {
            [...rows.children].forEach((row, at) => {
                const entry = entries[at];
                const others = entries.filter((_, other) => other !== at).map((other) => other.to);
                const error = row.classList.contains("is-touched") ? relationError(entry, item.id, others) : null;
                row.querySelector(".pe-error").lastChild.textContent = error ?? "";
                row.classList.toggle("is-invalid", error !== null);
                for (const control of row.querySelectorAll("input, select"))
                    control.removeAttribute("aria-invalid");
                // 誤りのある入力欄だけを赤の枠にする
                if (error !== null) {
                    const target = error.startsWith("種類") ? "select" : error.startsWith("いつ") ? ".rel-when-input" : ".rel-to-input";
                    row.querySelector(target).setAttribute("aria-invalid", "true");
                }
                row.querySelector(".rel-to-title").textContent = entry.to === "" ? "" : (index?.byId.get(entry.to)?.item.title ?? "");
                row.querySelector(".rel-together").hidden = entry.type !== "change_together";
            });
            empty.hidden = entries.length > 0;
            head.hidden = entries.length === 0;
        };
        const add = MindmapPreview.h({
            tag: "button",
            attrs: { type: "button", class: "btn ghost rel-add", disabled },
            children: [MindmapPreview.icon("plus"), "関連を追加"],
        });
        /** 1 件の行を末尾に置く */
        const addRow = (entry) => {
            const at = rows.children.length;
            const base = `${controlId}-${at}`;
            const toInput = MindmapPreview.h({
                tag: "input",
                attrs: { id: `${base}-to`, class: "input mono rel-to-input", list: listId, value: entry.to, autocomplete: "off", "aria-label": `${at + 1} 件目の相手`, "aria-describedby": `${base}-error`, disabled },
            });
            const typeSelect = relationTypeSelect({ id: `${base}-type`, value: entry.type, label: `${at + 1} 件目の種類`, disabled });
            // いつ読むかは 1 文。長い文は折り返して全文を見せる（Enter で改行しない）
            const whenInput = MindmapPreview.h({
                tag: "textarea",
                attrs: { id: `${base}-when`, class: "input rel-when-input", rows: 1, "aria-label": `${at + 1} 件目のいつ読むか`, "aria-describedby": `${base}-error`, disabled },
            });
            whenInput.value = entry.when;
            whenInput.addEventListener("keydown", (event) => {
                if (event.key === "Enter")
                    event.preventDefault();
            });
            const remove = MindmapPreview.h({
                tag: "button",
                attrs: { type: "button", class: "icon-btn rel-remove", "aria-label": `${at + 1} 件目の関連を削除`, disabled },
                children: [MindmapPreview.icon("trash")],
            });
            const cell = (label, control, extra) => MindmapPreview.h({
                tag: "div",
                attrs: { class: "rel-cell" },
                children: [MindmapPreview.h({ tag: "span", attrs: { class: "rel-lab", "aria-hidden": "true" }, children: [label] }), control, extra ?? null],
            });
            const row = MindmapPreview.h({
                tag: "li",
                attrs: { class: "rel-edit-row" },
                children: [
                    cell("相手", toInput, MindmapPreview.h({ tag: "span", attrs: { class: "rel-to-title" } })),
                    cell("種類", typeSelect),
                    cell("いつ読むか", whenInput),
                    remove,
                    MindmapPreview.h({ tag: "p", attrs: { class: "pe-error", id: `${base}-error`, role: "alert" }, children: [MindmapPreview.icon("alert"), ""] }),
                    MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint rel-together", hidden: true }, children: ["相手の項目の関連にも、この項目への「同時に変更」を書いてください。"] }),
                ],
            });
            /** 行の値を読み直す。入力を終えた（touched）ときだけ誤りを出し、そろえば知らせる */
            const update = (touched) => {
                entries[[...rows.children].indexOf(row)] = { to: toInput.value.trim(), type: typeSelect.value, when: whenInput.value };
                if (touched)
                    row.classList.add("is-touched");
                refresh();
                if (touched)
                    commitRelations(entries, item.id, onChange);
            };
            toInput.addEventListener("input", () => update(false));
            toInput.addEventListener("change", () => update(true));
            whenInput.addEventListener("change", () => update(true));
            typeSelect.addEventListener("change", () => update(true));
            remove.addEventListener("click", () => {
                entries.splice([...rows.children].indexOf(row), 1);
                // 削除した行の次 → 前 → 「関連を追加」へフォーカスを移す
                const next = row.nextElementSibling ?? row.previousElementSibling;
                row.remove();
                refresh();
                (next?.querySelector("input") ?? add).focus();
                commitRelations(entries, item.id, onChange);
            });
            rows.append(row);
            return row;
        };
        add.addEventListener("click", () => {
            entries.push({ to: "", type: "", when: "" });
            const row = addRow(entries[entries.length - 1]);
            refresh();
            row.querySelector("input").focus();
        });
        for (const entry of entries)
            addRow(entry);
        group.append(head, rows, empty, add, relationIdList(listId, item.id));
        refresh();
        return group;
    }
    /** 390 案 B: 今の ID のチップで相手を選び、選んだ相手ごとに種類といつ読むかを入れる欄を開く */
    function relatedChipsInput({ controlId, name, item, values, disabled, onChange }) {
        let entries = values.map(relationValue);
        const index = MindmapPreview.mockIndex390;
        const group = MindmapPreview.h({ tag: "div", attrs: { class: "rel-edit is-chips", role: "group", "aria-label": name } });
        const details = MindmapPreview.h({ tag: "ul", attrs: { class: "rel-details" } });
        /** 種類かいつ読むかを入れ終えた相手（入れ終えるまで誤りを出さない） */
        const touched = new Set();
        /** 相手ごとの開く欄を描き直す。誤りのある相手と openId の相手は開いておく */
        const renderDetails = (openId) => {
            details.replaceChildren(...entries.map((entry, at) => {
                const base = `${controlId}-${MindmapPreview.safeId(entry.to)}`;
                const found = relationError(entry, item.id, entries.filter((_, other) => other !== at).map((other) => other.to));
                const error = touched.has(entry.to) ? found : null;
                const typeSelect = relationTypeSelect({ id: `${base}-type`, value: entry.type, label: `${entry.to} の種類`, disabled });
                const whenInput = MindmapPreview.h({
                    tag: "input",
                    attrs: { id: `${base}-when`, class: "input", value: entry.when, autocomplete: "off", disabled },
                });
                const update = () => {
                    touched.add(entry.to);
                    entries[at] = { ...entry, type: typeSelect.value, when: whenInput.value };
                    if (!commitRelations(entries, item.id, onChange))
                        renderDetails(entry.to);
                };
                typeSelect.addEventListener("change", update);
                whenInput.addEventListener("change", update);
                const spec = MindmapPreview.RELATION_TYPES[entry.type];
                const box = MindmapPreview.h({
                    tag: "details",
                    attrs: { class: `rel-detail${error === null ? "" : " is-invalid"}`, open: found !== null || entry.to === openId },
                    children: [
                        MindmapPreview.h({
                            tag: "summary",
                            children: [
                                MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [entry.to] }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [index?.byId.get(entry.to)?.item.title ?? ""] }),
                                spec === undefined
                                    ? MindmapPreview.h({ tag: "span", attrs: { class: "rel-missing" }, children: [MindmapPreview.icon("alert"), "未入力"] })
                                    : MindmapPreview.h({ tag: "span", attrs: { class: "rel-type", "data-type": entry.type }, children: [spec.label] }),
                            ],
                        }),
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "rel-detail-body" },
                            children: [
                                MindmapPreview.h({ tag: "label", attrs: { for: `${base}-type` }, children: ["種類"] }),
                                typeSelect,
                                MindmapPreview.h({ tag: "label", attrs: { for: `${base}-when` }, children: ["いつ読むか"] }),
                                whenInput,
                                error === null ? null : MindmapPreview.h({ tag: "p", attrs: { class: "pe-error", role: "alert" }, children: [MindmapPreview.icon("alert"), error] }),
                            ],
                        }),
                    ],
                });
                return MindmapPreview.h({ tag: "li", children: [box] });
            }));
        };
        const chips = MindmapPreview.chipsInput({
            controlId,
            name,
            hint: "ID を入れる",
            values: entries.map((entry) => entry.to),
            suggestions: null,
            monospace: true,
            mainToggle: false,
            disabled,
            onChange: (next) => {
                // 選んだ相手の並びに合わせ、前から入れていた種類といつ読むかは残す
                const ids = next.map((value) => MindmapPreview.refTarget(value));
                const added = ids.find((id) => !entries.some((entry) => entry.to === id));
                entries = ids.map((id) => entries.find((entry) => entry.to === id) ?? { to: id, type: "", when: "" });
                if (!commitRelations(entries, item.id, onChange))
                    renderDetails(added);
            },
        });
        group.append(chips, details);
        renderDetails(null);
        return group;
    }
    /** 選ぶキーの選択肢 */
    function selectOptions({ kind, key, settings }) {
        switch (key) {
            case "status":
                return kind === "decisions" ? MindmapPreview.DECISION_STATUSES : kind === "tasks" ? MindmapPreview.TASK_STATUSES : MindmapPreview.DOC_STATUSES;
            case "kind":
                return TASK_KINDS;
            case "confidence":
                return CONFIDENCES;
            case "target":
                return settings.targets.map((target) => target.name);
            case "category":
                return settings.categories.map((category) => category.name);
            default:
                return settings.phases;
        }
    }
    /** 検討事項の案（1 案 1 枚。中身の書き換え・採用する案の切り替え・削除と、案を足す） */
    function optionsField(props) {
        const { item, removing, removedOptions, on } = props;
        const section = MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "pe-field pe-options", "data-key": "options" },
            children: [MindmapPreview.h({ tag: "legend", children: ["案"] })],
        });
        const idPart = safeId(item.id);
        const options = item.options ?? [];
        // 追加の入力では、採用している案は削除できない（採用をほかの案へ移すと削除できる）
        const adding = item.id.startsWith(MindmapPreview.NEW_ID_PREFIX);
        for (const option of options) {
            const removed = removedOptions.includes(option.key);
            const mark = props.marks[option.key];
            const textId = `pe-${idPart}-opt-${option.key}`;
            const area = MindmapPreview.h({
                tag: "textarea",
                attrs: {
                    id: textId,
                    class: "input pe-text",
                    rows: 2,
                    "aria-label": `案 ${option.key} の中身`,
                    disabled: removing || removed,
                },
            });
            area.value = option.content;
            area.addEventListener("change", () => on.change({ op: "option-edit", key: option.key, value: { content: area.value } }));
            const blocked = props.blocked[option.key];
            section.append(MindmapPreview.h({
                tag: "div",
                attrs: {
                    class: `pe-opt${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}${removed ? " is-removed" : ""}`,
                    "data-key": option.key,
                },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "pe-opt-head" },
                        children: [
                            MindmapPreview.h({ tag: "span", attrs: { class: "key", "aria-hidden": "true" }, children: [option.key] }),
                            MindmapPreview.h({
                                tag: "label",
                                attrs: { class: "pe-adopt" },
                                children: [
                                    MindmapPreview.h({
                                        tag: "input",
                                        attrs: {
                                            id: `pe-${idPart}-adopt-${option.key}`,
                                            type: "radio",
                                            name: `${item.id}-adopt`,
                                            value: option.key,
                                            checked: option.adopted === true,
                                            disabled: removing || removed,
                                            onchange: () => on.change({ op: "adopt", key: option.key, value: option.key }),
                                        },
                                    }),
                                    "採用",
                                ],
                            }),
                            mark === undefined ? null : MindmapPreview.pendingEditMark({ kind: mark, compact: true }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                            removed || (adding && option.adopted === true)
                                ? null
                                : MindmapPreview.h({
                                    tag: "button",
                                    attrs: {
                                        class: "icon-btn",
                                        type: "button",
                                        "aria-label": `案 ${option.key} を削除`,
                                        title: `案 ${option.key} を削除`,
                                        disabled: removing,
                                        onclick: () => on.change({ op: "option-remove", key: option.key, value: null }),
                                    },
                                    children: [MindmapPreview.icon("trash")],
                                }),
                        ],
                    }),
                    area,
                    blocked === undefined ? null : blockedNote({ blocked, updated: item.updated }),
                ],
            }));
        }
        // 書きかけの案（項目の案に同じ記号が載ったものは描かない）
        const drafts = props.optionDrafts.filter((draft) => !options.some((option) => option.key === draft.key));
        for (const draft of drafts) {
            const area = MindmapPreview.h({
                tag: "textarea",
                attrs: {
                    id: `pe-${idPart}-opt-${draft.key}`,
                    class: "input pe-text",
                    rows: 2,
                    "aria-label": `案 ${draft.key} の中身`,
                    disabled: removing,
                },
            });
            area.value = draft.content;
            // 打つたびに書きかけを知らせ、空でない中身で離れたら溜める
            area.addEventListener("input", () => on.draft({ key: draft.key, content: area.value }));
            area.addEventListener("change", () => {
                if (area.value.trim() === "")
                    return;
                on.change({ op: "option-add", key: draft.key, value: { content: area.value } });
            });
            section.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-opt", "data-key": draft.key, "data-draft": "" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "pe-opt-head" },
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "key", "aria-hidden": "true" }, children: [draft.key] })],
                    }),
                    area,
                ],
            }));
        }
        const add = MindmapPreview.h({
            tag: "button",
            attrs: { class: "btn pe-opt-add", type: "button", disabled: removing },
            children: [MindmapPreview.icon("plus"), "案を追加"],
        });
        add.addEventListener("click", () => {
            // 次の記号（今ある案と、書きかけの案の記号の次）の空の書きかけを置く。描くのは使う側が状態から描き直したとき
            const symbols = [...options.map((option) => option.key), ...drafts.map((draft) => draft.key)];
            const next = String.fromCharCode(Math.max(64, ...symbols.map((symbol) => symbol.charCodeAt(0))) + 1);
            on.draft({ key: next, content: "" });
        });
        section.append(add);
        // 案の編集を溜められなかった理由は、案の入力の下にまとめて出す
        const failure = props.errors["options"];
        if (failure !== undefined) {
            section.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [MindmapPreview.icon("alert"), failure] }));
        }
        return section;
    }
    /** 項目を削除する区画（削除を溜める・取り消す。ほかの項目が指しているときは警告を出す） */
    function removeSection(props) {
        const { removing, referrers, on } = props;
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "pe-remove-sec" },
            children: [
                MindmapPreview.h({ tag: "h2", children: ["項目を削除"] }),
                removing
                    ? MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "btn", type: "button", onclick: () => on.cancelRemove() },
                        children: [MindmapPreview.icon("undo"), "削除を取り消す"],
                    })
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "btn pe-danger", type: "button", onclick: () => on.remove() },
                        children: [MindmapPreview.icon("trash"), "項目を削除"],
                    }),
                referrers.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-hint" },
                        children: [
                            MindmapPreview.icon("alert"),
                            `${referrers.join("・")} が指しているため、保存のときに削除できません。指している項目から外すと削除できます。`,
                        ],
                    }),
            ],
        });
    }
})(MindmapPreview || (MindmapPreview = {}));
// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。差分の表示の間は、選んだ時点の前後の差分も出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 前の値が無いときに出す文字（差分のミニマップが、前に無かったキーを見分けるのにも使う） */
    MindmapPreview.NO_VALUE = "（なし）";
    /** 詳細パネルのレビュー中のコメントの行の `data-focus` の接頭辞（コメントの一覧と同時に開いても、描き直した後のフォーカスの戻し先を分ける） */
    MindmapPreview.REVIEW_FOCUS = "detail-";
    /** 差分に並べるキーから外す、ツールが付けるキーと本文の名前 */
    const UNDIFFED_KEYS = new Set(["id", "created", "updated", "updated_by", "history", "history_dropped_seq", "body"]);
    /** 前後を組み立てられない旨・本文の差分を出せない旨の文言 */
    const NOTE_TRIMMED = "このまとまりの前後を組み立てられません。保持する回数を超えた古い変更履歴は消えています。今の内容を出しています。";
    const NOTE_BODY_UNAVAILABLE = "本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。今の本文を出しています。";
    const NOTE_BODY_TOO_LARGE = "本文の差分を出せません。書き換えが大きく、差分を計算しきれませんでした。今の本文を出しています。";
    /** 図の前の版の記法を、図の要素に持たせる属性の名前（図の拡大が Raw の差分に読む） */
    const BEFORE_SOURCE_ATTR = "data-before-source";
    /** 前の版の図を描いて突き合わせる間、描いた SVG を置く画面の外の位置（px）と幅（px） */
    const OFFSCREEN_LEFT_PX = -10000;
    const OFFSCREEN_WIDTH_PX = 800;
    /** 差分の記号と、読み上げに残す名前 */
    const SIGNS = {
        add: { glyph: "+", name: "追加: " },
        del: { glyph: "−", name: "削除: " },
        same: { glyph: " ", name: "" },
    };
    /** 項目の ID を、押すと開くボタンにする */
    function idButton(id, open) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "idlink", type: "button", onclick: () => open(id) },
            children: [id],
        });
    }
    /** 項目の ID の並びを、ID・題・状態の一覧にする */
    function itemList(index, ids, open) {
        return MindmapPreview.h({
            tag: "ul",
            attrs: { class: "d-list" },
            children: [
                ...ids.map((id) => MindmapPreview.h({
                    tag: "li",
                    children: [
                        idButton(id, open),
                        MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [MindmapPreview.titleOf(index, id)] }),
                        MindmapPreview.statusBadge(index.byId.get(id)?.item.status),
                    ],
                })),
            ],
        });
    }
    /** 390: ツールチップの要素の ID の連番 */
    let relationTipSeq = 0;
    /** 390: 関連の種類のバッジ。案 A は文字だけのバッジ、案 B は押せるバッジで `when` をツールチップに出す */
    function relationBadge(entry, incoming) {
        const spec = MindmapPreview.RELATION_TYPES[entry.type];
        // 種類を持たない参照（依存先・経緯など）は、列をそろえる空きだけを置く
        if (spec === undefined)
            return MindmapPreview.h({ tag: "span", attrs: { class: "rel-type is-none", "aria-hidden": "true" } });
        // 参照元: 相手の項目が書いた関連なので、向きの矢印を付け、読み上げは「相手から」
        const children = [
            incoming ? MindmapPreview.h({ tag: "span", attrs: { class: "rel-dir", "aria-hidden": "true" }, children: ["←"] }) : null,
            spec.label,
            MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [incoming ? `（相手から: ${spec.meaning}）` : `（${spec.meaning}）`] }),
        ];
        if (document.body.dataset.rel !== "b" || entry.when === undefined)
            return MindmapPreview.h({ tag: "span", attrs: { class: "rel-type", "data-type": entry.type }, children });
        const tipId = `rel-tip-${++relationTipSeq}`;
        const button = MindmapPreview.h({
            tag: "button",
            attrs: { type: "button", class: "rel-type is-trigger", "data-type": entry.type, "aria-describedby": tipId },
            children,
        });
        // Esc でツールチップを閉じる（フォーカスは残す）。離れたら次に出せるよう戻す
        button.addEventListener("keydown", (event) => {
            if (event.key === "Escape")
                button.classList.add("tip-off");
        });
        button.addEventListener("blur", () => button.classList.remove("tip-off"));
        button.addEventListener("mouseleave", () => button.classList.remove("tip-off"));
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "rel-type-wrap" },
            children: [button, MindmapPreview.h({ tag: "span", attrs: { class: "rel-tip", id: tipId, role: "tooltip" }, children: [entry.when] })],
        });
    }
    /** 390: 関連の並び（`{id, type?, when?}`）を、種類・ID・題・状態と、案 A は行の下の `when` の一覧にする */
    function relationList(index, entries, open, incoming) {
        return MindmapPreview.h({
            tag: "ul",
            attrs: { class: "d-list rel-list" },
            children: entries.map((entry) => MindmapPreview.h({
                tag: "li",
                children: [
                    relationBadge(entry, incoming),
                    idButton(entry.id, open),
                    MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [MindmapPreview.titleOf(index, entry.id)] }),
                    MindmapPreview.statusBadge(index.byId.get(entry.id)?.item.status),
                    document.body.dataset.rel === "b" || entry.when === undefined
                        ? null
                        : MindmapPreview.h({ tag: "p", attrs: { class: "rel-when" }, children: [entry.when] }),
                ],
            })),
        });
    }
    /** 390: この項目の関連（ids なし）か、参照元の ids それぞれがこの項目を指す関連の並び */
    function relationEntries({ index, id, ids }) {
        const toEntry = (target, raw) => raw === undefined || typeof raw === "string" ? { id: target } : { id: target, type: raw.type, when: raw.when };
        if (ids === undefined)
            return (index.byId.get(id)?.item.related ?? []).map((raw) => toEntry(MindmapPreview.refTarget(raw), raw));
        return ids.map((referrer) => toEntry(referrer, (index.byId.get(referrer)?.item.related ?? []).find((value) => MindmapPreview.refTarget(value) === id)));
    }
    /** 見出しの付いた節 */
    function section(label, content) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "d-sec" },
            children: [MindmapPreview.h({ tag: "h3", children: [label] }), content],
        });
    }
    /** 値を描いた要素。選んだ箇所のコメントが、描いた要素のキーのパスで値を指せるようにする */
    function valueSpan(key, children) {
        return MindmapPreview.h({ tag: "span", attrs: { [MindmapPreview.VALUE_KEY_ATTR]: key }, children });
    }
    /** 文字列の値を Markdown で描き、見出しは最も上の段を top にして並べる（値が無ければ何も描かない。ライブラリを読めないときは改行を残した文字のまま） */
    function markdownValue({ value, top }) {
        if (value === undefined)
            return undefined;
        const rendered = MindmapPreview.renderValue(value);
        // 文字のままの要素には、下げる見出しが無い
        if (rendered.classList.contains("md-value-raw"))
            return rendered;
        lowerHeadings({ root: rendered, shift: headingShift({ roots: [rendered], top }) });
        return rendered;
    }
    /** Markdown で描く値の入れ物。選んだ箇所のコメント・示す箇所・キーの差分が、キーのパスで値を指せるようにする */
    function valueBlock(key, children) {
        return MindmapPreview.h({ tag: "div", attrs: { class: "d-value", [MindmapPreview.VALUE_KEY_ATTR]: key }, children });
    }
    /** 読み上げにだけ残す文字 */
    function srOnly(text) {
        return MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [text] });
    }
    /** 差分の記号（見えるのは記号だけで、名前は読み上げに残す） */
    function signMarks(op) {
        const { glyph, name } = SIGNS[op];
        return [MindmapPreview.h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: [glyph] }), ...(name === "" ? [] : [srOnly(name)])];
    }
    MindmapPreview.signMarks = signMarks;
    /** 変わったキーの前の値と今の値を並べる。前の値は取り消し線、今の値は下線。plain は面を塗らず、線と矢印だけで示す。pairs を渡すと、前後がどちらも空でない文字のとき、並べた対を語の面を付ける対として pairs に足す */
    function keyDiff({ was, now, plain = false, pairs, }) {
        const empty = (value) => value === null || value === undefined || value === false || value === "";
        const wasElement = MindmapPreview.h({ tag: "del", attrs: { class: "df-was" }, children: [srOnly("前の値: "), empty(was) ? MindmapPreview.NO_VALUE : was] });
        const nowElement = MindmapPreview.h({ tag: "ins", attrs: { class: "df-now" }, children: [srOnly("今の値: "), empty(now) ? MindmapPreview.NO_VALUE : now] });
        if (typeof was === "string" && typeof now === "string" && !empty(was) && !empty(now))
            pairs?.push({ was: wasElement, now: nowElement });
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: plain ? "df-kv df-plain" : "df-kv" },
            children: [wasElement, MindmapPreview.h({ tag: "span", attrs: { class: "df-arrow", "aria-hidden": "true" }, children: ["→"] }), nowElement],
        });
    }
    /** 控えたキーの値の対の文字（読み上げの文字を除く） */
    function keyWordNodes(root) {
        return wordTextNodes(root).filter((node) => node.parentElement?.closest(".sr-only") == null);
    }
    /** 控えたキーの値の対の前後の文字を語の単位で比べ、変わった語を濃い面で囲む。比べられなかった対には付けない */
    function markKeyWords({ pairs, deadline }) {
        for (const pair of pairs) {
            const wasNodes = keyWordNodes(pair.was);
            const nowNodes = keyWordNodes(pair.now);
            const inline = MindmapPreview.diffInline(wasNodes.map((node) => node.data).join(""), nowNodes.map((node) => node.data).join(""), deadline);
            if (inline === null)
                continue;
            wrapWords({ nodes: wasNodes, parts: inline.before, mark: "del" });
            wrapWords({ nodes: nowNodes, parts: inline.after, mark: "add" });
        }
    }
    /** キーの値を、差分に並べる文字にする。値が無ければ null */
    function valueText(value) {
        if (value === undefined || value === null || value === "")
            return null;
        if (Array.isArray(value))
            return value.length === 0 ? null : value.join("、");
        return String(value);
    }
    /** 案の値（文字列か文字列の配列）を、Markdown で描く 1 つの文字列にする。配列は「、」でつなぐ。空なら undefined */
    function optionText(value) {
        if (Array.isArray(value))
            return value.length === 0 ? undefined : value.join("、");
        return value;
    }
    /** 前の版と後の版を比べ、値が変わったキー（ツールが付けるキーと本文の名前を除く）の見せ方を返す */
    function keyDiffs(before, after) {
        const left = { ...before };
        const right = { ...after };
        const changed = new Set([...new Set([...Object.keys(left), ...Object.keys(right)])].filter((key) => !UNDIFFED_KEYS.has(key) && JSON.stringify(left[key]) !== JSON.stringify(right[key])));
        const pairs = [];
        return {
            has: (key) => changed.has(key),
            show: (key, render = valueText, plain = false) => changed.has(key) ? keyDiff({ was: render(left[key]), now: render(right[key]), plain }) : render(right[key]),
            showWords: (key) => changed.has(key) ? keyDiff({ was: valueText(left[key]), now: valueText(right[key]), pairs }) : valueText(right[key]),
            pairs,
            before,
        };
    }
    /** タグの値（`{name, main?}` の並び）を、主題のマーカーを付けたタグの並びにする。空なら null */
    function tagsOf(value) {
        return Array.isArray(value) && value.length > 0 ? MindmapPreview.tagList(value) : null;
    }
    /** 状態の値（文字）を、印と名前の表示にする。状態を持たなければ null */
    function statusOf(value) {
        return typeof value === "string" ? MindmapPreview.statusBadge(value) : null;
    }
    /** 選んだ時点で、開いた項目が足されたか変わったときの、前後の版と画面に出す内容。そうでなければ null */
    function resolveDiffView({ id, index, diff }) {
        const entry = index.byId.get(id);
        if (diff === null || entry === undefined)
            return null;
        const { item } = entry;
        const body = index.data.bodies[item.body ?? ""];
        if (diff.added.has(id))
            return { point: diff, kind: "new", versions: null, keys: null, shown: item, body };
        if (!diff.changed.has(id))
            return null;
        const versions = MindmapPreview.buildVersions(item, body ?? "", diff);
        // 前後を組み立てられない: 今の内容を差分なしで出す
        if (versions.trimmed || versions.before === null) {
            return { point: diff, kind: "changed", versions, keys: null, shown: item, body };
        }
        return {
            point: diff,
            kind: "changed",
            versions,
            keys: keyDiffs(versions.before, versions.after),
            shown: versions.after,
            body: body === undefined ? undefined : versions.afterBody,
        };
    }
    /** 差分の表示の冒頭の帯。選んだ時点の名前と日時 */
    function diffHead(point) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "df-head" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "df-head-t" }, children: [MindmapPreview.icon("history"), point.name] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "df-when" }, children: [point.sub] }),
            ],
        });
    }
    /** 前後を組み立てられない旨・本文の差分を出せない旨の知らせ */
    function noteBox(text) {
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: "df-note", role: "note" },
            children: [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [text] })],
        });
    }
    /** 案の採用の状態の名前（採用でも不採用でもない案は null） */
    function optionResult(option) {
        if (option === undefined)
            return null;
        return option.adopted === true ? "採用" : option.adopted === false ? "不採用" : null;
    }
    /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由、採用した案が無いときは推奨の印を出す）。previous があれば、変わった値に前の値を並べる */
    function optionCards({ options, previous, pairs }) {
        const compare = previous !== null;
        const removed = (previous ?? []).filter((entry) => !options.some((option) => option.key === entry.key));
        // 採用した案があれば採用の表示を優先し、推奨の印は出さない
        const decided = options.some((option) => option.adopted === true);
        return MindmapPreview.h({
            tag: "div",
            children: [
                ...options.map((option) => {
                    const before = previous?.find((entry) => entry.key === option.key);
                    const result = optionResult(option);
                    const recommended = option.recommended === true && !decided;
                    const rows = [
                        ["メリット", "pros", optionText(option.pros)],
                        ["デメリット", "cons", optionText(option.cons)],
                        ["備考", "note", option.note],
                        ["理由", "reason", option.reason],
                    ];
                    // 前の値と違う値は前の値と今の値を並べる。前に無かった案は全ての値を足した印にする
                    const beforeOf = (field) => optionText(before?.[field]);
                    const shown = rows.filter(([, field, value]) => (value !== undefined && value !== "") || (compare && beforeOf(field) !== undefined));
                    const valueOf = (field, value) => compare && beforeOf(field) !== value
                        ? keyDiff({ was: beforeOf(field) ?? null, now: value ?? null, pairs })
                        : markdownValue({ value, top: SECTION_TOP_HEADING_LEVEL });
                    const resultChild = compare && optionResult(before) !== result ? keyDiff({ was: optionResult(before), now: result, plain: true }) : result;
                    return MindmapPreview.h({
                        tag: "div",
                        attrs: {
                            class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}${recommended ? " recommended" : ""}`,
                        },
                        children: [
                            MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "o-head" },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                                    valueBlock(`options[${option.key}].content`, [
                                        compare && before?.content !== option.content
                                            ? keyDiff({ was: before?.content ?? null, now: option.content, pairs })
                                            : markdownValue({ value: option.content, top: SECTION_TOP_HEADING_LEVEL }),
                                    ]),
                                    recommended ? MindmapPreview.h({ tag: "span", attrs: { class: "rec-badge" }, children: [MindmapPreview.icon("star"), "推奨"] }) : null,
                                    resultChild === null ? null : MindmapPreview.h({ tag: "span", attrs: { class: "res" }, children: [resultChild] }),
                                ],
                            }),
                            shown.length > 0
                                ? MindmapPreview.h({
                                    tag: "dl",
                                    children: [
                                        ...shown.flatMap(([label, field, value]) => [
                                            MindmapPreview.h({ tag: "dt", children: [label] }),
                                            MindmapPreview.h({ tag: "dd", attrs: { [MindmapPreview.VALUE_KEY_ATTR]: `options[${option.key}].${field}` }, children: [valueOf(field, value)] }),
                                        ]),
                                    ],
                                })
                                : null,
                        ],
                    });
                }),
                // 後の版で消えた案: 全ての値を消した印で並べる
                ...removed.map((option) => MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "opt" },
                    children: [
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "o-head" },
                            children: [
                                MindmapPreview.h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                                MindmapPreview.h({ tag: "del", attrs: { class: "df-was" }, children: [srOnly("消した案: "), option.content] }),
                            ],
                        }),
                    ],
                })),
            ],
        });
    }
    /** 見出しの下の、項目のキー（対象・カテゴリー・フェーズ・影響度・種類・確度・日付・更新日・タグ）の一覧。変わったキーは前の値と今の値を並べる */
    function metaList({ item, settings, diff }) {
        const pairs = [
            [settings.target_label, "target", item.target],
            ["カテゴリー", "category", item.category],
            ["フェーズ", "phase", item.phase],
            ["影響度", "weight", item.weight],
            ["種類", "kind", item.kind],
            ["確度", "confidence", item.confidence],
            ["日付", "date", item.date],
            ["更新日", "updated", item.updated],
            // 取り下げは値をここに出さず（題の右の札が示す）、差分の表示で変わったときだけ前後を並べる
            ["取り下げ", "withdrawn", undefined],
        ];
        const rows = pairs.flatMap(([label, key, value]) => {
            const changed = diff?.has(key) === true;
            // 値が無く、変わってもいないキーは出さない
            if ((value === undefined || value === "") && !changed)
                return [];
            const shown = diff === null
                ? value
                : key === "withdrawn"
                    ? diff.show(key, (flag) => (flag === true ? MindmapPreview.withdrawnBadge() : null))
                    : diff.show(key);
            return [
                MindmapPreview.h({ tag: "dt", attrs: { class: changed ? "df-key" : null }, children: [label] }),
                MindmapPreview.h({ tag: "dd", attrs: { class: changed ? "df-key" : null }, children: [shown] }),
            ];
        });
        const tagsChanged = diff?.has("tags") === true;
        if ((item.tags ?? []).length > 0 || tagsChanged) {
            rows.push(MindmapPreview.h({ tag: "dt", attrs: { class: tagsChanged ? "df-key" : null }, children: ["タグ"] }), MindmapPreview.h({ tag: "dd", attrs: { class: tagsChanged ? "df-key" : null }, children: [tagsChanged ? diff?.show("tags", tagsOf) : MindmapPreview.tagList(item.tags)] }));
        }
        return MindmapPreview.h({ tag: "dl", attrs: { class: "d-meta" }, children: [...rows] });
    }
    /** この項目へのレビュー中のコメントの節（各行の右上の「修正」「削除」で、その場で直す・消す・戻す。チェックとまとめて送るはコメントの一覧で行う） */
    function reviewSection({ items, edit }) {
        // 消した行は元の場所（溜めた順）に「元に戻す」と共に残す
        const rows = [...items.map((item) => ({ item, gone: false })), ...edit.removed.map((item) => ({ item, gone: true }))].sort((a, b) => MindmapPreview.commentNumber(a.item.id) - MindmapPreview.commentNumber(b.item.id));
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "d-sec d-review" },
            children: [
                MindmapPreview.h({
                    tag: "h3",
                    children: ["レビュー中のコメント", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })],
                }),
                rows.length === 0
                    ? MindmapPreview.emptyNote("レビュー中のコメントはありません。")
                    : MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "d-list review-list" },
                        children: rows.map(({ item, gone }) => {
                            if (gone)
                                return MindmapPreview.removedReviewRow({ item, focus: MindmapPreview.REVIEW_FOCUS, on: { restore: edit.on.restore } });
                            const editing = edit.editing === item.id;
                            // 入力欄は修正を始めた場所だけに描く。コメントの一覧で始めた行は、ここでは本文だけにして「修正」「削除」も出さない
                            const editingHere = editing && edit.editingIn === "detail";
                            return MindmapPreview.h({
                                tag: "li",
                                attrs: { class: `review-row${editing ? " editing" : ""}`, "data-comment": item.id },
                                children: [
                                    MindmapPreview.h({
                                        tag: "div",
                                        attrs: { class: "review-main" },
                                        children: [
                                            item.loc === null
                                                ? null
                                                : MindmapPreview.h({
                                                    tag: "div",
                                                    attrs: { class: "review-loc" },
                                                    children: [
                                                        MindmapPreview.h({ tag: "span", attrs: { class: "review-loc-name" }, children: [MindmapPreview.locationLabel(item.loc)] }),
                                                        MindmapPreview.h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [item.loc.text] }),
                                                    ],
                                                }),
                                            editingHere
                                                ? MindmapPreview.reviewEditForm({
                                                    item,
                                                    body: edit.editBody,
                                                    error: edit.editError,
                                                    focus: MindmapPreview.REVIEW_FOCUS,
                                                    on: { saveEdit: edit.on.saveEdit, cancelEdit: edit.on.cancelEdit },
                                                })
                                                : MindmapPreview.h({ tag: "p", attrs: { class: "review-body" }, children: [item.body] }),
                                        ],
                                    }),
                                    // 書き換えている行には「修正」「削除」を出さない（入力欄の「キャンセル」「修正」と並べない）
                                    editing ? null : MindmapPreview.reviewRowActions({ item, focus: MindmapPreview.REVIEW_FOCUS, on: { edit: edit.on.edit, remove: edit.on.remove } }),
                                ],
                            });
                        }),
                    }),
            ],
        });
    }
    // ─── 本文の差分 ───
    /** 本文を行の並びにする（末尾の改行で出る空の最後の要素は行ではない） */
    function linesOf(text) {
        const lines = text.split("\n");
        if (lines.at(-1) === "")
            lines.pop();
        return lines;
    }
    /** 今の本文の行（1 始まり）のうち、差分で足した行 */
    function addedLines({ parts, now }) {
        const added = new Set();
        let line = 0;
        for (const part of parts) {
            if (part.kind === "removed")
                continue;
            for (const _ of part.lines) {
                line += 1;
                // 空行だけの足しは段落の間の空きで、どの塊も足したことにしない
                if (part.kind === "added" && (now[line - 1] ?? "").trim() !== "")
                    added.add(line);
            }
        }
        return added;
    }
    /** 今の本文の各行が属するブロックの先頭の行を求める。図のコードブロックの中は null（図の差分が示す）。それ以外のコードブロックの中は、中身の最初の行を持つブロックに属する */
    function blockOwners({ now, starts }) {
        const owners = [];
        let fence = null;
        now.forEach((text, offset) => {
            const line = offset + 1;
            const opening = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
            if (fence !== null) {
                owners.push(fence.owner);
                // 閉じるフェンス（言語を持たない行）で、コードブロックを出る
                if (opening !== null && opening[2] === "")
                    fence = null;
                return;
            }
            if (opening !== null) {
                fence = { owner: opening[2] === "mermaid" ? null : line + 1 };
                owners.push(fence.owner);
                return;
            }
            // 印を持つブロックのうち、この行以前で最も後ろのもの
            owners.push(starts.filter((start) => start <= line).at(-1) ?? null);
        });
        return owners;
    }
    MindmapPreview.blockOwners = blockOwners;
    /** 差分の記号を頭に置いた、足した塊・消した塊の囲み */
    function diffBlock({ op, children }) {
        return MindmapPreview.h({
            tag: op === "add" ? "ins" : "del",
            attrs: { class: "df-blk" },
            children: [...signMarks(op), ...children],
        });
    }
    MindmapPreview.diffBlock = diffBlock;
    /** 本文の足した部分の印を、今の本文の要素に付ける（段落・見出し・コードは囲み、表の行と箇条書きの項目は行の印にする） */
    function markAddedBlocks({ root, parts, source }) {
        const now = linesOf(source);
        const added = addedLines({ parts, now });
        if (added.size === 0)
            return;
        const blocks = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(MindmapPreview.LINE_ATTR))) });
        const marked = new Set();
        for (const line of added) {
            const owner = owners[line - 1];
            if (owner !== null && owner !== undefined)
                marked.add(owner);
        }
        for (const block of blocks) {
            if (!marked.has(Number(block.getAttribute(MindmapPreview.LINE_ATTR))))
                continue;
            if (block.tagName === "TR") {
                block.classList.add("df-row", "df-add");
                block.firstElementChild?.prepend(...signMarks("add"));
            }
            else if (block.tagName === "LI") {
                block.classList.add("df-li-add");
                block.prepend(...signMarks("add"));
            }
            else {
                // 囲みを元の位置に置いてから、ブロックを囲みの中へ移す
                const wrapper = diffBlock({ op: "add", children: [] });
                block.replaceWith(wrapper);
                wrapper.append(block);
            }
        }
    }
    /** 消した行を別に描いた要素から、行の印を外す（今の本文の行に対応づけない） */
    function withoutLineMarks(root) {
        for (const element of root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`))
            element.removeAttribute(MindmapPreview.LINE_ATTR);
        return root;
    }
    MindmapPreview.withoutLineMarks = withoutLineMarks;
    /** 消した行の図のコードブロックを、記法の原文だけにする（描かない） */
    function plainDiagrams(root) {
        for (const figure of root.querySelectorAll("figure.diagram")) {
            const source = figure.querySelector(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
            figure.replaceWith(MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }));
        }
    }
    /** 消した行のかたまりを、別に Markdown として描いた要素にする */
    function renderRemoved(block) {
        const lines = block.tableHeader === null ? block.lines : [...block.tableHeader, ...block.lines];
        const rendered = withoutLineMarks(MindmapPreview.renderMarkdown(lines.join("\n")));
        plainDiagrams(rendered);
        return rendered;
    }
    /** 描いた消した行のかたまりを、今の本文の差し込む場所の前（無ければ本文の最後）へ差し込む。かたまりごとに、差し込んだ語の面を付ける対象のブロックを返す */
    function insertRemovedBlocks({ root, blocks }) {
        // 差し込む前の、行の印を持つ今のブロック（差し込む要素は印を持たない）
        const stamped = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const lineOf = (element) => Number(element.getAttribute(MindmapPreview.LINE_ATTR));
        const placed = [];
        for (const { block, rendered } of blocks) {
            const target = block.beforeLine === null ? undefined : stamped.find((element) => lineOf(element) >= (block.beforeLine ?? 0));
            const previous = target === undefined ? stamped.at(-1) : stamped[stamped.indexOf(target) - 1];
            // 表の本体の行だけ: 今の表の行の間（表の最後の後も）へ、消した行の印を付けた行として差し込む
            if (block.tableHeader !== null) {
                const rows = [...rendered.querySelectorAll("tbody tr")].map((row) => {
                    row.classList.add("df-row", "df-del");
                    row.firstElementChild?.prepend(...signMarks("del"));
                    return row;
                });
                if (target?.tagName === "TR") {
                    target.before(...rows);
                    placed.push(rows);
                    continue;
                }
                if (previous?.tagName === "TR") {
                    previous.after(...rows);
                    placed.push(rows);
                    continue;
                }
            }
            // 囲みの中へ移す前に、語の面を付ける対象のブロックを引く
            placed.push(wordBlocksIn(rendered));
            const piece = diffBlock({ op: "del", children: [...rendered.childNodes] });
            if (target === undefined) {
                root.append(piece);
                continue;
            }
            // 足した塊の囲みの中・箇条書きや表の中ではなく、その外側の前へ差し込む（表は包む入れ物ごと外側にする）
            const outer = target.parentElement?.matches("ins.df-blk") === true ? target.parentElement : target;
            const container = outer.closest("ul, ol, table") ?? outer;
            (container.parentElement?.matches(`.${MindmapPreview.TABLE_WRAP_CLASS}`) === true ? container.parentElement : container).before(piece);
        }
        return placed;
    }
    /** 前の本文の図のコードブロック（開く行から閉じる行まで。1 始まり）。閉じていないコードブロックは本文の最後まで */
    function diagramFenceRanges(lines) {
        const ranges = [];
        let open = null;
        lines.forEach((text, offset) => {
            const fence = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
            if (fence === null)
                return;
            if (open === null) {
                if (fence[2] === "mermaid")
                    open = offset + 1;
            }
            else if (fence[2] === "") {
                ranges.push({ open, close: offset + 1 });
                open = null;
            }
        });
        if (open !== null)
            ranges.push({ open, close: lines.length });
        return ranges;
    }
    /** 消した行のうち、図のコードブロックの一部だけを消した分を外す（図の差分が示すので、本文には消した行として差し込まない）。図を丸ごと消した分は残す */
    function withoutDiagramEdits({ parts, before }) {
        const ranges = diagramFenceRanges(linesOf(before));
        if (ranges.length === 0)
            return parts;
        let line = 0;
        return parts.flatMap((part) => {
            if (part.kind === "added")
                return [part];
            const first = line + 1;
            line += part.lines.length;
            if (part.kind === "same")
                return [part];
            const last = line;
            // この消した部分に丸ごと入っていない図のコードブロックの行
            const partial = ranges.filter((range) => range.open < first || range.close > last);
            const kept = part.lines.filter((_, offset) => !partial.some((range) => first + offset >= range.open && first + offset <= range.close));
            return kept.length === 0 ? [] : [{ kind: part.kind, lines: kept }];
        });
    }
    /** 語の面を付ける対象になる、描いたブロック（段落・見出し・箇条書きの項目・表の本体の行）の選び方 */
    const WORD_BLOCK_SELECTOR = "p, h1, h2, h3, h4, h5, h6, li, tbody tr";
    /** 語の面を付ける対象のブロックか（ほかの対象のブロックを中に持たないもの） */
    function isWordBlock(element) {
        return element.matches(WORD_BLOCK_SELECTOR) && element.querySelector(WORD_BLOCK_SELECTOR) === null;
    }
    /** 要素の中の、語の面を付ける対象のブロック（文書の順） */
    function wordBlocksIn(root) {
        return [...root.querySelectorAll(WORD_BLOCK_SELECTOR)].filter(isWordBlock);
    }
    MindmapPreview.wordBlocksIn = wordBlocksIn;
    /** 足した部分ごとの、足した行（空行を除く）を持つ今のブロックのうち、語の面を付ける対象のもの（足した行の順） */
    function addedBlocksByPart({ root, parts, now }) {
        const blocks = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(MindmapPreview.LINE_ATTR))) });
        const byStart = new Map(blocks.map((block) => [Number(block.getAttribute(MindmapPreview.LINE_ATTR)), block]));
        const found = new Map();
        let line = 0;
        parts.forEach((part, position) => {
            if (part.kind === "removed")
                return;
            const here = [];
            for (const _ of part.lines) {
                line += 1;
                // 空行だけの足しは段落の間の空きで、どのブロックも足したことにしない
                if (part.kind !== "added" || (now[line - 1] ?? "").trim() === "")
                    continue;
                const owner = owners[line - 1];
                const block = owner === null || owner === undefined ? undefined : byStart.get(owner);
                if (block !== undefined && isWordBlock(block) && !here.includes(block))
                    here.push(block);
            }
            if (part.kind === "added")
                found.set(position, here);
        });
        return found;
    }
    /** 変えた行の対（`pairedParts`）ごとに、消した部分から描いたブロックと、足した部分の行を持つ今のブロックを前から順に並べ、両方の数が同じときだけ 1 つずつ対にする */
    function wordPairs({ root, parts, now, placed, }) {
        // 消した部分の並びの何番目か（`placed` は消した部分の順）
        const removedOrder = parts.flatMap((part, position) => (part.kind === "removed" ? [position] : []));
        const addedBlocks = addedBlocksByPart({ root, parts, now });
        return MindmapPreview.pairedParts(parts).flatMap(({ removed, added }) => {
            const removedList = placed[removedOrder.indexOf(removed)] ?? [];
            const addedList = addedBlocks.get(added) ?? [];
            if (removedList.length === 0 || removedList.length !== addedList.length)
                return [];
            return removedList.map((block, offset) => ({ removed: block, added: addedList[offset] }));
        });
    }
    /** 要素の中の、行の印（`signMarks` が入れる記号と読み上げの文字）と、表・リストの構造の間の整形の空白を除いた文字のノード（文書の順） */
    function wordTextNodes(root) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => {
                const parent = node.parentElement;
                const isSign = parent?.closest(".df-sign") != null || parent?.matches(".df-sign + .sr-only") === true;
                const isLayoutSpace = (node.textContent ?? "").trim() === "" && parent?.matches("table, thead, tbody, tr, ul, ol") === true;
                return isSign || isLayoutSpace ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
            },
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        return nodes;
    }
    /** 変わった語の面の要素 */
    function wordMark({ mark, text }) {
        return MindmapPreview.h({ tag: "span", attrs: { class: `df-word df-${mark}` }, children: [text] });
    }
    /** 文字のノードの並びのうち、語の差分の足した・消した部分を面の要素で囲む（ノードをまたぐ部分はノードごとに囲み、ノードの外の要素は分けない） */
    function wrapWords({ nodes, parts, mark }) {
        // 同じでない部分の、文字の頭からの範囲
        const ranges = [];
        let offset = 0;
        for (const part of parts) {
            if (part.kind !== "same")
                ranges.push({ start: offset, end: offset + part.text.length });
            offset += part.text.length;
        }
        let nodeStart = 0;
        for (const node of nodes) {
            const text = node.data;
            const nodeEnd = nodeStart + text.length;
            const pieces = [];
            // ノードの中で、ここまでを pieces に入れた位置
            let cursor = 0;
            for (const range of ranges) {
                const from = Math.max(range.start, nodeStart) - nodeStart;
                const to = Math.min(range.end, nodeEnd) - nodeStart;
                if (from >= to)
                    continue;
                if (from > cursor)
                    pieces.push(text.slice(cursor, from));
                pieces.push(wordMark({ mark, text: text.slice(from, to) }));
                cursor = to;
            }
            nodeStart = nodeEnd;
            if (pieces.length === 0)
                continue;
            if (cursor < text.length)
                pieces.push(text.slice(cursor));
            node.replaceWith(...pieces);
        }
    }
    /** 対の 2 つのブロックの、行の印を除いた文字を語の単位で比べ、変わった語を濃い面で囲む。比べられなかった対には付けない */
    function markWords({ pair, deadline }) {
        const removedNodes = wordTextNodes(pair.removed);
        const addedNodes = wordTextNodes(pair.added);
        const inline = MindmapPreview.diffInline(removedNodes.map((node) => node.data).join(""), addedNodes.map((node) => node.data).join(""), deadline);
        if (inline === null)
            return;
        wrapWords({ nodes: removedNodes, parts: inline.before, mark: "del" });
        wrapWords({ nodes: addedNodes, parts: inline.after, mark: "add" });
    }
    MindmapPreview.markWords = markWords;
    /** 埋め込んだ HTML の範囲の中の行の差分を、本文の行の差分から外す（範囲の差分は範囲ごとの部品が出す）。前の版の範囲の中の消した行は落とし、今の範囲の中の足した行は変えていない行にして、今の本文の行の数は変えない */
    function withoutEmbeddedHtmlEdits({ parts, before, after }) {
        /** 範囲の印の行を含む、範囲の中の行（1 始まり） */
        const linesInRanges = (source) => {
            const lines = new Set();
            for (const { open, close } of MindmapPreview.embeddedHtmlRanges(source))
                for (let line = open; line <= close; line += 1)
                    lines.add(line);
            return lines;
        };
        const inBefore = linesInRanges(before);
        const inAfter = linesInRanges(after);
        const result = [];
        /** 同じ種類が続くときは 1 つの並びにまとめて足す */
        const push = (kind, line) => {
            const last = result[result.length - 1];
            if (last?.kind === kind)
                last.lines.push(line);
            else
                result.push({ kind, lines: [line] });
        };
        let beforeLine = 1;
        let afterLine = 1;
        for (const part of parts) {
            for (const line of part.lines) {
                if (part.kind === "removed") {
                    if (!inBefore.has(beforeLine))
                        push("removed", line);
                    beforeLine += 1;
                }
                else if (part.kind === "added") {
                    push(inAfter.has(afterLine) ? "same" : "added", line);
                    afterLine += 1;
                }
                else {
                    push("same", line);
                    beforeLine += 1;
                    afterLine += 1;
                }
            }
        }
        return result;
    }
    /** 範囲の直下の要素を並びで比べるための文字列にする（描くたびに変わる部品の連番は揃える） */
    function childSignature(element) {
        return element.outerHTML.replace(/mdmark-(diagram|param)-\d+-\d+/g, "mdmark-$1");
    }
    /** 差分の表示の間、変わった埋め込んだ HTML の範囲を、範囲の差分（変更前・変更後の描いた結果と原文の差分）に置き換える。範囲の直下の要素のうち、足した要素と変えた要素にマーカーを付けた今の範囲を、変更後の描いた結果にする */
    function replaceChangedRanges({ root, before, after }) {
        const ranges = [...root.querySelectorAll(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`)];
        for (const pair of MindmapPreview.pairEmbeddedHtml({ before, after })) {
            const element = ranges[pair.order];
            if (element === undefined)
                continue;
            // 選んだ時点の範囲を、範囲の印で包んで描く
            const beforeView = MindmapPreview.renderMarkdown(`<!-- html -->\n${pair.before}\n<!-- /html -->\n`);
            const beforeRange = beforeView.querySelector(`.${MindmapPreview.EMBEDDED_HTML_CLASS}`);
            if (beforeRange === null)
                continue;
            const marks = MindmapPreview.childMarks({ before: [...beforeRange.children].map(childSignature), after: [...element.children].map(childSignature) });
            marks?.forEach((mark, position) => {
                if (mark !== null)
                    element.children[position]?.setAttribute("data-df", mark === "added" ? "add" : "chg");
            });
            // 今の範囲を差分の部品へ移す間、置き場所を残す。差分を計算しきれなかったら今の範囲のまま戻す
            const placeholder = document.createComment("");
            element.replaceWith(placeholder);
            const diff = MindmapPreview.htmlBodyDiff({ before: pair.before, after: pair.after, marked: "", initial: "raw", heading: "埋め込んだ HTML", beforeView, afterView: element });
            placeholder.replaceWith(diff ?? element);
        }
    }
    /** 前後の本文を行ごとに比べ、今の本文を描いて足した部分と消した部分に印を付ける。差分を計算しきれなかったら null */
    function renderBodyDiff({ before, after, deadline }) {
        const compared = MindmapPreview.diffLineParts(before, after);
        if (compared === null)
            return null;
        const parts = withoutDiagramEdits({ parts: withoutEmbeddedHtmlEdits({ parts: compared, before, after }), before });
        const rendered = MindmapPreview.renderMarkdown(after);
        const removed = MindmapPreview.placeRemovedBlocks(parts).map((block) => ({ block, rendered: renderRemoved(block) }));
        // 今の本文と消した部分の見出しを合わせた最も上の段から、段の差を 1 つ求める
        const shift = headingShift({ roots: [rendered, ...removed.map((piece) => piece.rendered)] });
        lowerHeadings({ root: rendered, shift });
        for (const piece of removed)
            lowerHeadings({ root: piece.rendered, shift });
        markAddedBlocks({ root: rendered, parts, source: after });
        const placed = insertRemovedBlocks({ root: rendered, blocks: removed });
        const pairs = wordPairs({ root: rendered, parts, now: linesOf(after), placed });
        return { root: rendered, markWords: () => pairs.forEach((pair) => markWords({ pair, deadline })) };
    }
    // ─── 図の差分 ───
    /** 記法の 1 行目の語（図の種類）。先頭の設定の行（`%%`）と空行は読み飛ばす */
    function diagramType(source) {
        const first = source
            .split("\n")
            .map((line) => line.trim())
            .find((line) => line !== "" && !line.startsWith("%%"));
        return first?.split(/\s+/)[0] ?? "";
    }
    /** 行の差分を比べやすいよう、記法の末尾を改行 1 つにそろえる */
    function withTrailingNewline(source) {
        return source.endsWith("\n") ? source : `${source}\n`;
    }
    /** 記法の行ごとの差分を、足した行（+）・消した行（−）の印つきの行にする。変えた行の対は、変わった語を濃い面で囲む（`deadline` は、行の差分を呼ぶ直前の時刻に `LINE_DIFF_TIMEOUT_MS` を足した時刻） */
    function rawDiffLines({ parts, deadline }) {
        const op = { added: "add", removed: "del", same: "same" };
        // 対の行ごとの語の差分（`parts` の添え字 → 行ごと）。対の行ごとに 1 回だけ比べ、消した側と足した側に同じ結果を使う
        const inlines = new Map();
        for (const { removed, added } of MindmapPreview.pairedParts(parts)) {
            const removedLines = parts[removed]?.lines ?? [];
            const addedLines = parts[added]?.lines ?? [];
            const compared = removedLines.map((text, offset) => MindmapPreview.diffInline(text, addedLines[offset] ?? "", deadline));
            inlines.set(removed, compared);
            inlines.set(added, compared);
        }
        return parts.flatMap((part, position) => part.lines.map((text, offset) => {
            const inline = inlines.get(position)?.[offset] ?? null;
            const pieces = inline === null ? null : part.kind === "removed" ? inline.before : inline.after;
            return MindmapPreview.h({
                tag: "span",
                attrs: { class: `df-line${part.kind === "same" ? "" : ` df-${op[part.kind]}`}` },
                children: [
                    ...signMarks(op[part.kind]),
                    ...(pieces === null ? [text] : pieces.map((piece) => (piece.kind === "same" ? piece.text : wordMark({ mark: part.kind === "removed" ? "del" : "add", text: piece.text })))),
                ],
            });
        }));
    }
    MindmapPreview.rawDiffLines = rawDiffLines;
    /** 前後の版の図の記法の並びから、今の図ごとの前の版の記法を決める。前の版と同じ図は null、前に無い図は空文字列。同じ記法の図を先に組にし、残りを並びの順で組にする */
    function pairDiagrams({ before, after }) {
        const free = new Set(before.keys());
        const unchanged = after.map((source) => {
            const match = [...free].find((candidate) => (before[candidate] ?? "").trim() === source.trim());
            if (match === undefined)
                return false;
            free.delete(match);
            return true;
        });
        const rest = [...free];
        return after.map((_, position) => {
            if (unchanged[position] === true)
                return null;
            const next = rest.shift();
            return next === undefined ? "" : (before[next] ?? "");
        });
    }
    /** 図の下に出す、凡例と「消したもの」 */
    function diagramNotes({ colored, removed }) {
        const legend = colored
            ? MindmapPreview.h({
                tag: "div",
                attrs: { class: "df-legend" },
                children: [
                    MindmapPreview.h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } }), "足した"] }),
                    MindmapPreview.h({ tag: "span", attrs: { class: "df-lg df-lg-chg" }, children: [MindmapPreview.h({ tag: "i", attrs: { "aria-hidden": "true" } }), "変わった"] }),
                ],
            })
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "df-legend" },
                children: [
                    MindmapPreview.h({ tag: "span", attrs: { class: "df-badge df-chg" }, children: [MindmapPreview.icon("changed"), "変わった図"] }),
                    MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["図の中の変更は Raw で見られます"] }),
                ],
            });
        return MindmapPreview.h({
            tag: "figcaption",
            attrs: { class: "df-notes" },
            children: [
                legend,
                removed.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "df-removed" },
                        children: [
                            MindmapPreview.h({ tag: "span", attrs: { class: "df-removed-t" }, children: ["消したもの"] }),
                            MindmapPreview.h({
                                tag: "ul",
                                children: removed.map((name) => MindmapPreview.h({ tag: "li", children: [MindmapPreview.h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: ["−"] }), srOnly("消した: "), name] })),
                            }),
                        ],
                    }),
            ],
        });
    }
    /** 図の差分で見つけた要素に色の印を付ける（ノードは枠と面、辺は線、メッセージは文字と線） */
    function paintDiagramElement({ element, mode }) {
        if (element.matches("text")) {
            element.classList.add(`df-t-${mode}`);
            element.nextElementSibling?.classList.add(`df-e-${mode}`);
            return;
        }
        element.classList.add(element.matches("path") ? `df-e-${mode}` : `df-n-${mode}`);
    }
    /** 前の版の図を `renderDiagramSvg` で描き、今の版の図と `diffDiagram` で突き合わせる。前の版の図を描けないときと、色を付けない種類・突き合わせを打ち切ったときは null */
    async function diffByRenderedBefore({ type, beforeSource, afterSvg }) {
        const beforeSvg = await MindmapPreview.renderDiagramSvg(beforeSource);
        if (beforeSvg === null)
            return null;
        // 前の版の図は、座標を取れるよう画面の外に置いて突き合わせる
        const offscreen = MindmapPreview.h({
            tag: "div",
            attrs: {
                "aria-hidden": "true",
                style: `position:absolute;top:0;left:${OFFSCREEN_LEFT_PX}px;width:${OFFSCREEN_WIDTH_PX}px`,
            },
            children: [beforeSvg],
        });
        document.body.append(offscreen);
        const diagram = MindmapPreview.diffDiagram(type, beforeSvg, afterSvg);
        offscreen.remove();
        return diagram;
    }
    /** 変わった図に、色・凡例と消したもの・Raw の行ごとの差分を付ける。前の版の図を描けない・色を付けない種類・突き合わせを打ち切ったときは、図の枠に色を付ける */
    async function decorateDiagram({ figure, beforeSource }) {
        const holder = figure.querySelector(".mermaid");
        const afterSource = holder?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
        figure.classList.add("df-changed", "df-frame");
        // Raw: 記法の行ごとの差分（打ち切ったときは今の記法のまま）
        const raw = figure.querySelector(":scope > .dg-raw");
        const deadline = performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS;
        const parts = MindmapPreview.diffLineParts(withTrailingNewline(beforeSource), withTrailingNewline(afterSource));
        if (raw !== null && parts !== null) {
            raw.classList.add("df-raw");
            raw.replaceChildren(...rawDiffLines({ parts, deadline }));
        }
        const type = diagramType(afterSource);
        const afterSvg = holder?.querySelector("svg") ?? null;
        let colored = false;
        let removed = [];
        if (afterSvg !== null && MindmapPreview.COLORED_DIAGRAM_TYPES.includes(type) && beforeSource.trim() !== "") {
            // flowchart は前後の記法の解析で突き合わせ、前の版を描かない。null（flowchart でない・解析できない）の図だけ前の版を描く
            const diagram = (await MindmapPreview.diffDiagramFromSource(type, beforeSource, afterSource, afterSvg)) ?? (await diffByRenderedBefore({ type, beforeSource, afterSvg }));
            if (diagram !== null) {
                for (const element of diagram.added)
                    paintDiagramElement({ element, mode: "add" });
                for (const element of diagram.changed)
                    paintDiagramElement({ element, mode: "chg" });
                removed = diagram.removed;
                colored = true;
            }
        }
        figure.classList.toggle("df-frame", !colored);
        figure.classList.toggle("df-colored", colored);
        figure.append(diagramNotes({ colored, removed }));
        // 図の拡大が、同じ凡例と Raw の差分を出せるようになる
        figure.setAttribute(BEFORE_SOURCE_ATTR, beforeSource);
    }
    MindmapPreview.decorateDiagram = decorateDiagram;
    /** 差分の表示の間、今の本文の図のうち前の版から変わったものを、色・凡例・Raw の差分で示す */
    function decorateDiagrams({ root, before }) {
        const afterFigures = [...root.querySelectorAll("figure.diagram")];
        if (afterFigures.length === 0)
            return;
        const sourceOf = (figure) => figure.querySelector(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
        const beforeSources = [...MindmapPreview.renderMarkdown(before).querySelectorAll("figure.diagram")].map(sourceOf);
        const pairs = pairDiagrams({ before: beforeSources, after: afterFigures.map(sourceOf) });
        afterFigures.forEach((figure, position) => {
            const beforeSource = pairs[position];
            // 前の版と同じ図は印を付けない
            if (beforeSource === null || beforeSource === undefined)
                return;
            void decorateDiagram({ figure, beforeSource });
        });
    }
    /** 資料の HTML の本文の枠が持つ属性（コメントの一覧から開いたとき、示す箇所を求める枠を引く） */
    const HTML_BODY_ATTR = "data-html-body";
    /** Markdown の本文の中の `html` のコードブロックの入れ物を、枠に置き換える。差分の表示の間の足した・消した部分は、枠に描かず原文に印を付けたまま出す */
    function drawHtmlBlocks(root) {
        for (const block of root.querySelectorAll(`.${MindmapPreview.HTML_BLOCK_CLASS}`)) {
            const source = block.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
            if (block.closest(".df-blk") !== null) {
                block.replaceWith(MindmapPreview.h({ tag: "pre", attrs: { class: "html-block-src" }, children: [source] }));
            }
            else {
                const frame = MindmapPreview.htmlBodyFrame({ source, selectable: false, label: "html のコードブロック" });
                frame.classList.add(MindmapPreview.HTML_BLOCK_CLASS);
                const line = block.getAttribute(MindmapPreview.LINE_ATTR);
                if (line !== null)
                    frame.setAttribute(MindmapPreview.LINE_ATTR, line);
                block.replaceWith(frame);
            }
        }
    }
    /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
    function detailBody({ id, index, on, review, view, bodyLayout, bodyView }) {
        const entry = index.byId.get(id);
        const body = MindmapPreview.h({ tag: "div", attrs: { class: "detail" } });
        if (entry === undefined)
            return body;
        const { kind } = entry;
        const item = view?.shown ?? entry.item;
        const keys = view?.keys ?? null;
        const related = MindmapPreview.relatedItems({ id, index });
        /** キーの値。変わっていれば前の値と今の値を並べる */
        const textOf = (key, value) => (keys?.has(key) === true ? keys.showWords(key) : value);
        const labelled = ({ label, key, value, top }) => {
            const changed = keys?.has(key) === true;
            if ((value === undefined || value === "") && !changed)
                return null;
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: changed ? "d-answer df-key" : "d-answer" },
                children: [MindmapPreview.h({ tag: "b", children: [label] }), valueBlock(key, [changed ? textOf(key, value) : markdownValue({ value, top })])],
            });
        };
        /** 資料・調査の説明の節（値があるとき、または値が変わったときだけ）。値が変わっていれば、前の値と今の値を並べる */
        const descriptionSection = () => {
            const changed = keys?.has("description") === true;
            if ((item.description === undefined || item.description === "") && !changed)
                return null;
            const described = section("説明", valueBlock("description", [changed ? textOf("description", item.description) : markdownValue({ value: item.description, top: SECTION_TOP_HEADING_LEVEL })]));
            // 見た目は結論と同じ、灰色の面に小さな名前を添えた形
            described.classList.add("d-answer");
            return described;
        };
        /** 取り下げた理由の節（検討事項・タスクの `reason` は別の節が持つ）。値が変わっていれば、前の値と今の値を並べる */
        const withdrawnReason = () => {
            if (kind === "decisions" || kind === "tasks")
                return null;
            const changed = keys?.has("reason") === true;
            if ((item.reason === undefined || item.reason === "") && !changed)
                return null;
            return section("取り下げた理由", valueBlock("reason", [changed ? textOf("reason", item.reason) : markdownValue({ value: item.reason, top: SECTION_TOP_HEADING_LEVEL })]));
        };
        /** 見出しの下の 1 段落 */
        const lead = (key, value, className) => {
            if ((value === undefined || value === "") && keys?.has(key) !== true)
                return null;
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: className, [MindmapPreview.VALUE_KEY_ATTR]: key },
                children: [keys?.has(key) === true ? textOf(key, value) : markdownValue({ value, top: TITLE_TOP_HEADING_LEVEL })],
            });
        };
        let keysMarked = false;
        /** キーの値の語の面を、1 回だけ付ける。deadline は本文の語の差分と共有する（本文の差分を描かないときは、比べる直前の時刻に `LINE_DIFF_TIMEOUT_MS` を足した時刻） */
        const markKeys = (deadline) => {
            if (keys === null || keysMarked)
                return;
            keysMarked = true;
            markKeyWords({ pairs: keys.pairs, deadline });
        };
        /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす。差分の表示の間は、本文と図の差分を重ねる */
        const bodySection = (label) => {
            const source = view?.body ?? index.data.bodies[item.body ?? ""];
            if (source === undefined)
                return null;
            if (MindmapPreview.bodyFormatOf(item.body) === "html")
                return htmlBodySection({ label, source });
            let rendered = null;
            let markBodyWords = null;
            let bodyDeadline = null;
            let notice = null;
            let diagramBefore = null;
            // 左右に並べた本文（並べ方が「左右に並べる」のとき）と、並べ方の切り替え
            let side = null;
            let layoutBar = null;
            const versions = view?.versions ?? null;
            if (versions !== null && versions.before !== null && !versions.trimmed) {
                if (MindmapPreview.missingLibraries(["jsdiff"]).length > 0) {
                    // jsdiff を読めない: 本文・図・Raw は今の版を差分なしで描く
                    notice = MindmapPreview.libraryNotice({ names: ["jsdiff"], what: "本文と図の差分" });
                }
                else if (versions.beforeBody === null) {
                    notice = noteBox(NOTE_BODY_UNAVAILABLE);
                }
                else {
                    diagramBefore = versions.beforeBody;
                    // 語の差分は、行の差分を呼ぶ前に決めたこの時刻の内に収める（行の差分を打ち切ったときも、キーの値の語の差分と共有する）
                    bodyDeadline = performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS;
                    const bodyDiff = renderBodyDiff({ before: versions.beforeBody, after: source, deadline: bodyDeadline });
                    rendered = bodyDiff?.root ?? null;
                    markBodyWords = bodyDiff?.markWords ?? null;
                    if (rendered === null) {
                        notice = noteBox(NOTE_BODY_TOO_LARGE);
                    }
                    else if (versions.beforeBody !== source) {
                        // 本文が選んだ時点から変わっていて差分を描けたときだけ、並べ方の切り替えを置く
                        side =
                            bodyLayout === "side"
                                ? MindmapPreview.sideBySideBodyDiff({ before: versions.beforeBody, after: source, lined: source === index.data.bodies[item.body ?? ""], deadline: bodyDeadline })
                                : null;
                        if (bodyLayout === "side" && side === null) {
                            notice = noteBox(NOTE_BODY_TOO_LARGE);
                        }
                        else {
                            layoutBar = MindmapPreview.h({ tag: "div", attrs: { class: "body-diff-bar" }, children: [MindmapPreview.bodyDiffLayoutSwitch({ layout: bodyLayout, on: { change: on.layout } })] });
                        }
                    }
                }
            }
            const root = rendered ?? MindmapPreview.renderMarkdown(source);
            if (rendered === null)
                lowerHeadings({ root, shift: headingShift({ roots: [root] }) });
            // 本文の差分（インライン）の間は、変わった埋め込んだ HTML の範囲を範囲の差分に置き換える
            if (rendered !== null && diagramBefore !== null)
                replaceChangedRanges({ root, before: diagramBefore, after: source });
            // 古いまとまりを選び、その後に本文を直した: 描いた本文は今の本文の行と合わないので、行の印を外す（選んだ箇所のコメントも示す箇所も今の行に向けない）
            if (source !== index.data.bodies[item.body ?? ""])
                withoutLineMarks(root);
            // 見出しのリンクと、本文の用語・項目の ID の印を付ける
            MindmapPreview.linkHeadings({
                root,
                onHeading: (slug) => {
                    scrollToHeading({ root, slug });
                    on.heading(slug);
                },
                onChangeSet: on.changeSet,
            });
            MindmapPreview.linkBody({ root, index, selfId: id, onOpen: on.open, source });
            drawHtmlBlocks(root);
            // 表の列の固定・見出しの固定・しま模様と、見出しの開閉を当てる（本文の差分には開閉を置かない）
            MindmapPreview.decorateMarkdown({ root, display: bodyView, fold: rendered === null });
            // 左右に並べた本文にも、見出しのリンクと本文の印を付ける（右の列だけが今の本文の行を持つ）
            for (const [position, column] of (side?.columns ?? []).entries()) {
                MindmapPreview.linkHeadings({
                    root: column,
                    onHeading: (slug) => {
                        scrollToHeading({ root: column, slug });
                        on.heading(slug);
                    },
                    onChangeSet: on.changeSet,
                });
                // 左の列は選んだ時点の本文、右の列は今の本文を描いたもの
                MindmapPreview.linkBody({ root: column, index, selfId: id, onOpen: on.open, source: position === 0 ? (diagramBefore ?? source) : source });
                drawHtmlBlocks(column);
                MindmapPreview.decorateMarkdown({ root: column, display: bodyView, fold: false });
            }
            // 語の面は、リンクと用語の印を付けた後に付ける（印の要素は分けず、中の文字だけを囲む）。キーの値の語の面を先に付ける
            if (bodyDeadline !== null)
                markKeys(bodyDeadline);
            markBodyWords?.();
            side?.markWords();
            const drawn = MindmapPreview.renderDiagrams(root);
            if (diagramBefore !== null) {
                const before = diagramBefore;
                void drawn.then(() => decorateDiagrams({ root, before }));
            }
            // 左右に並べた本文の図を描き、右の変えた図に色・凡例・Raw の差分を付ける
            if (side !== null) {
                const sideView = side;
                void MindmapPreview.renderDiagrams(sideView.root).then(() => sideView.decorate());
            }
            const onDiagramTool = (event) => {
                const button = event.target.closest("[data-act]");
                const figure = button?.closest(".diagram");
                if (button === null || button === undefined || figure === null || figure === undefined)
                    return;
                const act = button.dataset["act"];
                const original = figure.querySelector(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? "";
                if (act === "diagram-zoom") {
                    const svgElement = figure.querySelector(".mermaid svg");
                    const beforeSource = figure.getAttribute(BEFORE_SOURCE_ATTR);
                    if (svgElement !== null)
                        on.diagram(svgElement, beforeSource === null ? null : { beforeSource });
                }
                else if (act === "diagram-raw") {
                    // 図と mermaid の原文を切り替える
                    const pressed = button.getAttribute("aria-pressed") !== "true";
                    button.setAttribute("aria-pressed", String(pressed));
                    figure.querySelector(".mermaid").hidden = pressed;
                    figure.querySelector(".dg-raw").hidden = !pressed;
                }
                else if (act === "diagram-copy") {
                    void navigator.clipboard?.writeText(original).then(() => {
                        button.replaceChildren(MindmapPreview.icon("check"));
                        window.setTimeout(() => button.replaceChildren(MindmapPreview.icon("copy")), 1400);
                    });
                }
            };
            root.addEventListener("click", onDiagramTool);
            const content = document.createDocumentFragment();
            // 左右に並べるときは、本文の幅が足りないときに出すインラインの本文も持つ
            if (side !== null) {
                side.root.addEventListener("click", onDiagramTool);
                root.classList.add("sbs-fallback");
            }
            content.append(...(notice === null ? [] : [notice]), ...(layoutBar === null ? [] : [layoutBar]), ...(side === null ? [] : [side.root]), root);
            return section(label, content);
        };
        /** HTML の本文の節。本文を枠に描く。差分の表示の間は、描いた結果の上の印と原文の差分で前後を見せる */
        const htmlBodySection = ({ label, source }) => {
            const current = index.data.bodies[entry.item.body ?? ""];
            const marked = index.data.marked_bodies?.[entry.item.body ?? ""];
            // 選んだ時点が今の本文のとき、行の印つきの HTML を使う（古いまとまりを選び、その後に本文を直したときは、今の行と合わない）
            const lined = source === current && marked !== undefined;
            const drawn = lined ? marked : source;
            let notice = null;
            let content = null;
            const versions = view?.versions ?? null;
            if (versions !== null && versions.before !== null && !versions.trimmed) {
                if (MindmapPreview.missingLibraries(["jsdiff"]).length > 0) {
                    notice = MindmapPreview.libraryNotice({ names: ["jsdiff"], what: "本文の差分" });
                }
                else if (versions.beforeBody === null) {
                    notice = noteBox(NOTE_BODY_UNAVAILABLE);
                }
                else if (versions.beforeBody !== source) {
                    content = MindmapPreview.htmlBodyDiff({
                        before: versions.beforeBody,
                        after: source,
                        marked: drawn,
                        beforeFormat: MindmapPreview.bodyFormatOf(versions.before.body) === "md" ? "md" : "html",
                        layout: bodyLayout,
                        layoutSwitch: MindmapPreview.bodyDiffLayoutSwitch({ layout: bodyLayout, on: { change: on.layout } }),
                    });
                    if (content === null)
                        notice = noteBox(NOTE_BODY_TOO_LARGE);
                }
            }
            const frame = content ??
                MindmapPreview.htmlBodyFrame({
                    source: drawn,
                    // 配る書き出しと、今の本文の行と合わない本文では、選んだ箇所のコメントの入口を出さない
                    selectable: review !== null && lined,
                    ...(on.frame === undefined ? {} : { on: { select: on.frame.select, clear: on.frame.clear } }),
                });
            if (frame instanceof HTMLIFrameElement)
                frame.setAttribute(HTML_BODY_ATTR, "");
            const wrapped = document.createDocumentFragment();
            wrapped.append(...(notice === null ? [] : [notice]), frame);
            return section(label, wrapped);
        };
        /** 採用した案と理由の節（決定内容・理由のどちらかがあるときだけ） */
        const adoptedSection = () => {
            const rows = [
                labelled({ label: "決定内容", key: "answer", value: item.answer, top: SECTION_TOP_HEADING_LEVEL }),
                labelled({ label: "理由", key: "reason", value: item.reason, top: SECTION_TOP_HEADING_LEVEL }),
            ].filter((row) => row !== null);
            if (rows.length === 0)
                return null;
            const content = document.createDocumentFragment();
            content.append(...rows);
            return section("採用した案と理由", content);
        };
        /** 関係する項目の節（1 件以上あるときだけ） */
        const relation = (label, ids) => ids.length === 0 ? null : section(label, itemList(index, ids, on.open));
        // 390: 種類と `when` を持つ関連の節（1 件以上あるときだけ）
        const relatedSection = (label, entries, incoming) => entries.length === 0 ? null : section(label, relationList(index, entries, on.open, incoming));
        /** タグなどの一覧の節。値が変わっていれば、前の値と今の値を並べる */
        const listSection = (label, key, values) => {
            if (keys?.has(key) === true)
                return section(label, valueSpan(key, [keys.show(key)]));
            return (values ?? []).length > 0 ? section(label, MindmapPreview.tagList(values)) : null;
        };
        MindmapPreview.append({
            parent: body,
            children: [
                view === null ? null : diffHead(view.point),
                view?.versions?.trimmed === true ? noteBox(NOTE_TRIMMED) : null,
                valueSpan("status", [keys?.has("status") === true ? keys.show("status", statusOf, true) : MindmapPreview.statusBadge(item.status)]),
                MindmapPreview.h({
                    tag: "h2",
                    attrs: { class: "d-title", [MindmapPreview.VALUE_KEY_ATTR]: "title" },
                    children: [
                        keys?.has("title") === true ? keys.showWords("title") : item.title,
                        item.deliverable === true ? MindmapPreview.deliverableBadge() : null,
                        view?.kind === "new" ? MindmapPreview.diffMark({ kind: "new", labeled: true }) : null,
                        // 取り下げた項目は、差分の表示によらず題の右に札を置く
                        item.withdrawn === true ? MindmapPreview.withdrawnBadge({ large: true }) : null,
                    ],
                }),
                metaList({ item, settings: index.data.settings, diff: keys }),
                withdrawnReason(),
            ],
        });
        if (kind === "decisions") {
            const previous = keys?.has("options") === true ? (keys.before.options ?? []) : null;
            MindmapPreview.append({
                parent: body,
                children: [
                    lead("lead", item.lead, "d-lead"),
                    (item.options ?? []).length > 0 || previous !== null ? section("案", optionCards({ options: item.options ?? [], previous, ...(keys === null ? {} : { pairs: keys.pairs }) })) : null,
                    adoptedSection(),
                    bodySection("本文"),
                    relation("前提", related.prerequisites),
                    relation("後続の項目", related.successors),
                    relation("関連タスク", related.tasks),
                    relation("経緯（会話ログ）", related.logs),
                ],
            });
        }
        else if (kind === "tasks") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled({ label: "理由", key: "reason", value: item.reason, top: TITLE_TOP_HEADING_LEVEL }),
                    relation("進める検討事項", item.for ?? []),
                    relation("前提", related.prerequisites),
                    relation("結果", item.result === undefined ? [] : [item.result]),
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "research") {
            MindmapPreview.append({
                parent: body,
                children: [
                    lead("question", item.question, "d-lead"),
                    descriptionSection(),
                    labelled({ label: "結論", key: "conclusion", value: item.conclusion, top: TITLE_TOP_HEADING_LEVEL }),
                    listSection("エイリアス", "aliases", item.aliases),
                    listSection("調査の観点", "angles", item.angles),
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "docs") {
            MindmapPreview.append({ parent: body, children: [descriptionSection(), listSection("エイリアス", "aliases", item.aliases), bodySection("本文")] });
        }
        else if (kind === "terms") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled({ label: "意味", key: "meaning", value: item.meaning, top: TITLE_TOP_HEADING_LEVEL }),
                    listSection("別名", "aliases", item.aliases),
                    listSection("使わない表記", "avoid", item.avoid),
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "notes") {
            MindmapPreview.append({ parent: body, children: [lead("content", item.content, null), bodySection("本文")] });
        }
        else {
            MindmapPreview.append({ parent: body, children: [bodySection("要約")] });
        }
        if ((item.links ?? []).length > 0) {
            MindmapPreview.append({
                parent: body,
                children: [
                    section("リンク", MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "d-list" },
                        children: [
                            ...(item.links ?? []).map((link) => MindmapPreview.h({
                                tag: "li",
                                children: [
                                    MindmapPreview.icon("link"),
                                    MindmapPreview.h({
                                        tag: "a",
                                        attrs: { href: link.url, target: "_blank", rel: "noopener" },
                                        children: [link.title],
                                    }),
                                ],
                            })),
                        ],
                    })),
                ],
            });
        }
        MindmapPreview.append({
            parent: body,
            children: [
                // 390: 関連と参照元は、関連ごとに種類と `when` を出す
                relatedSection(kind === "logs" ? "更新した項目" : "関連", relationEntries({ index, id }), false),
                relatedSection("参照元", relationEntries({ index, id, ids: related.referencedBy }), true),
                review === null ? null : reviewSection(review),
            ],
        });
        // 本文の差分を描かなかったとき、キーの値の語の面をここで付ける
        markKeys(performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS);
        return body;
    }
    /** 読む表示のキーの名前（メタの行の見出し）。キー → 見出しの文字 */
    function metaLabelOf({ key, settings }) {
        const labels = {
            target: settings.target_label,
            category: "カテゴリー",
            phase: "フェーズ",
            kind: "種類",
            confidence: "確度",
            date: "日付",
            withdrawn: "取り下げ",
            tags: "タグ",
        };
        return labels[key];
    }
    /** 読む表示のキー・案の名前の後ろに、保存待ちの印（印だけ）を置く。置き場所は、メタの行の見出し・値の名前（太字）・節の見出し・題・案の見出しの順で探す */
    function markEditedKeys({ root, marks, settings }) {
        for (const [key, kind] of Object.entries(marks)) {
            // 項目の印は見出しに置く
            if (/^[A-Z]-\d+$/.test(key))
                continue;
            const badge = MindmapPreview.pendingEditMark({ kind, compact: true });
            // 案の記号
            if (/^[A-Z]$/.test(key)) {
                const head = root.querySelector(`[${MindmapPreview.VALUE_KEY_ATTR}="options[${key}].content"]`)?.closest(".opt")?.querySelector(".o-head");
                if (head !== null && head !== undefined && head.querySelector(".pm") === null)
                    head.append(badge);
                continue;
            }
            const label = metaLabelOf({ key, settings });
            const dt = label === undefined ? undefined : [...root.querySelectorAll("dt")].find((node) => node.textContent === label);
            const value = root.querySelector(`[${MindmapPreview.VALUE_KEY_ATTR}="${key}"]`);
            const named = value?.closest(".d-answer")?.querySelector(":scope > b") ?? null;
            const heading = [...root.querySelectorAll(".d-sec > h3")].find((node) => node.textContent?.startsWith(MindmapPreview.KEY_LABELS[key] ?? "\u0000") === true || (key === "body" && /^(本文|要約)/.test(node.textContent ?? "")));
            const target = dt ?? named ?? heading ?? (value?.matches(".d-title") === true ? value : null);
            if (target !== null && target !== undefined)
                target.append(badge);
            else if (value !== null && value !== undefined)
                value.after(badge);
        }
    }
    /** 見出し（前へ・次へ・全画面・閉じる）を作る */
    function detailHead({ id, index, full, on, edit = null }) {
        const entry = index.byId.get(id);
        const trail = history.state;
        const position = trail?.position ?? 0;
        const length = trail?.items.length ?? 1;
        // 本文が Markdown の資料は、編集の表示の間を除いて、エクスポートの入口を置く
        const exportSource = entry?.kind === "docs" && MindmapPreview.bodyFormatOf(entry.item.body) === "md" && edit?.editing !== true ? index.data.bodies[entry.item.body ?? ""] : undefined;
        const arrow = (label, glyph, disabled, handler) => MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "icon-btn",
                type: "button",
                "data-act": glyph === "←" ? "back" : "forward",
                "aria-label": label,
                title: label,
                disabled,
                onclick: handler,
            },
            children: [glyph],
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-head" },
            children: [
                full
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: on.close },
                        children: [MindmapPreview.icon("back")],
                    }),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "panel-kind" },
                    children: [
                        // 狭い幅でタイトルに幅を譲るとき、種類の名前だけを見た目から外せるよう包む
                        entry === undefined ? "" : MindmapPreview.h({ tag: "span", attrs: { class: "panel-kind-label" }, children: [`${MindmapPreview.KIND_LABEL[entry.kind]} `] }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
                    ],
                }),
                entry?.kind === "docs" ? MindmapPreview.bodyFormatBadgeOf(entry.item.body) : null,
                // 保存待ちの編集がある項目は、種類と ID の右に印だけを置く（幅 480px 以下は出さず、キー・案の印に任せる）
                MindmapPreview.editMarkOf({ edit, id, compact: true }),
                // 本文の先頭のタイトルと二重に読ませないよう読み上げから外す。収まらない分は省略し、乗せると全文が読める
                entry === undefined
                    ? null
                    : MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "panel-title", "aria-hidden": "true", title: entry.item.title },
                        children: [entry.item.title],
                    }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                edit === null
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "btn pe-edit-toggle",
                            type: "button",
                            "data-act": "edit",
                            "aria-pressed": String(edit.editing),
                            title: edit.editing ? "編集を終える" : "編集する",
                            onclick: () => edit.onToggle(),
                        },
                        children: [MindmapPreview.icon("edit"), MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: [edit.editing ? "編集を終える" : "編集する"] })],
                    }),
                exportSource === undefined || entry === undefined ? null : docExportControl({ item: entry.item, source: exportSource, index }),
                arrow("前の項目へ戻る", "←", position <= 0, on.back),
                arrow("次の項目へ進む", "→", position >= length - 1, on.forward),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn panel-full",
                        type: "button",
                        "data-act": "full",
                        // 全画面の間は、縮小のアイコンと元に戻す名前にする（色は変えず、押された状態は持たない）
                        "aria-label": full ? "元の大きさに戻す" : "全画面表示",
                        title: full ? "元の大きさに戻す" : "全画面表示",
                        onclick: () => on.full(!full),
                    },
                    children: [MindmapPreview.icon(full ? "shrink" : "expand")],
                }),
                full
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "icon-btn panel-close-x",
                            type: "button",
                            "data-act": "close",
                            "aria-label": "詳細を閉じる",
                            onclick: on.close,
                        },
                        children: [MindmapPreview.icon("x")],
                    }),
            ],
        });
    }
    /** エクスポートのメニューと画面の左右の端との間に空ける余白（px） */
    const EXPORT_MENU_MARGIN_PX = 8;
    /** 資料のエクスポートの入口と、形式を選ぶメニュー。入口を押すとメニューを入口の下に右端を揃えて開き、「HTML でエクスポート」は mdmark を取って 1 枚の HTML を組み立てて保存させ、「Markdown でエクスポート」は警告の後に埋め込んだ HTML を除いた本文を保存させる。閉じたら入口へフォーカスを戻す */
    function docExportControl({ item, source, index }) {
        // 組み立てている間にメニューを閉じたとき、組み立て終えたファイルを保存させないための世代
        let generation = 0;
        let view = "choose";
        const entry = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "icon-btn panel-export",
                type: "button",
                "data-act": "export",
                "aria-label": "エクスポート",
                title: "エクスポート",
                "aria-haspopup": "dialog",
                "aria-expanded": "false",
            },
            children: [MindmapPreview.icon("download")],
        });
        /** メニューの中身を替える（開いたまま、中身とフォーカスだけを替える） */
        const setView = ({ next, focus }) => {
            view = next;
            const fresh = MindmapPreview.docExportMenu({ view: next, ...(focus === undefined ? {} : { focus }), on });
            menu.replaceChildren(...fresh.childNodes);
            menu.setAttribute("aria-labelledby", fresh.getAttribute("aria-labelledby") ?? "");
            if (next === "busy")
                menu.setAttribute("aria-busy", "true");
            else
                menu.removeAttribute("aria-busy");
            menu.querySelector(`[${MindmapPreview.DOC_EXPORT_FOCUS_ATTR}]`)?.focus();
        };
        /** HTML のエクスポート。mdmark を取って組み立て、保存させて閉じる。取れないか組み立てられなければエラーの中身にする */
        const exportHtml = async () => {
            setView({ next: "busy" });
            generation += 1;
            const mine = generation;
            const assets = await MindmapPreview.mdmarkAssets();
            // 組み立てている間に閉じた
            if (mine !== generation)
                return;
            if (!assets.ok) {
                setView({ next: "error" });
                return;
            }
            let html;
            try {
                html = MindmapPreview.buildDocHtml({ item, source, index, assets });
            }
            catch {
                // 1 枚に入れられない中身（script 要素を閉じるタグを含む JavaScript など）
                setView({ next: "error" });
                return;
            }
            MindmapPreview.downloadText({ name: `${item.id}.html`, text: html, type: "text/html" });
            menu.hidePopover();
        };
        const on = {
            format: (format) => {
                if (format === "html")
                    void exportHtml();
                else
                    setView({ next: "warn" });
            },
            confirm: () => {
                MindmapPreview.downloadText({ name: `${item.id}.md`, text: MindmapPreview.stripEmbeddedHtml(source), type: "text/markdown" });
                menu.hidePopover();
            },
            back: () => setView({ next: "choose", focus: view === "warn" ? "md" : "html" }),
            retry: () => void exportHtml(),
            close: () => {
                generation += 1;
                entry.setAttribute("aria-expanded", "false");
                entry.focus();
            },
        };
        const menu = MindmapPreview.docExportMenu({ on });
        // 入口の押下が開閉を決める。開くたびに形式を選ぶ中身へ戻し、入口の下に右端を揃えて置く
        entry.popoverTargetElement = menu;
        entry.popoverTargetAction = "toggle";
        menu.addEventListener("beforetoggle", (event) => {
            if (event.newState !== "open")
                return;
            setView({ next: "choose" });
            entry.setAttribute("aria-expanded", "true");
            // 入口の右端にメニューの右端を揃え、左端が画面の左右の余白より外に出るときは余白まで寄せる
            const rect = entry.getBoundingClientRect();
            const width = Math.min(parseFloat(getComputedStyle(menu).width), window.innerWidth - EXPORT_MENU_MARGIN_PX * 2);
            menu.style.top = `${rect.bottom + 4}px`;
            menu.style.left = `${Math.min(Math.max(rect.right - width, EXPORT_MENU_MARGIN_PX), window.innerWidth - EXPORT_MENU_MARGIN_PX - width)}px`;
            menu.style.right = "auto";
        });
        // 開いたら、最初の行にフォーカスを置く
        menu.addEventListener("toggle", (event) => {
            if (event.newState === "open")
                menu.querySelector(`[${MindmapPreview.DOC_EXPORT_FOCUS_ATTR}]`)?.focus();
        });
        return MindmapPreview.h({ tag: "span", attrs: { class: "panel-export-host" }, children: [entry, menu] });
    }
    /** 本文の先頭のタイトルが本文のスクロール領域の上へ出ている間だけ、見出しのタイトルに `is-shown` を付ける */
    function bindHeadTitle({ head, body }) {
        const headTitle = head.querySelector(".panel-title");
        const bodyTitle = body.querySelector(".d-title");
        if (headTitle === null || bodyTitle === null)
            return;
        const observer = new IntersectionObserver((entries) => {
            // 描き直されて文書から外れた見出しの見張りは外す
            if (!head.isConnected) {
                observer.disconnect();
                return;
            }
            const last = entries[entries.length - 1];
            // 領域の上へ出たときだけ出す（下にあるときは出さない）
            headTitle.classList.toggle("is-shown", !last.isIntersecting && last.boundingClientRect.top < (last.rootBounds?.top ?? 0));
        }, { root: body, threshold: 0 });
        observer.observe(bodyTitle);
    }
    /** 節の見出し（h3）の次に置く、本文・値の見出しのうち最も上の段 */
    const SECTION_TOP_HEADING_LEVEL = 4;
    /** 題（h2）の次に置く、値の見出しのうち最も上の段 */
    const TITLE_TOP_HEADING_LEVEL = 3;
    /** 見出しの要素の最も下の段（h6） */
    const LOWEST_HEADING_LEVEL = 6;
    /** 見出しの要素の段（h1〜h6 の数字） */
    function headingLevel(heading) {
        return Number(heading.tagName.slice(1));
    }
    /** 見出しのうち最も上の段を top（省略すると節の見出しの次の段）にするための、全ての見出しに足す段の差。見出しが無ければ 0 */
    function headingShift({ roots, top = SECTION_TOP_HEADING_LEVEL }) {
        const levels = roots.flatMap((root) => [...root.querySelectorAll("h1, h2, h3, h4, h5, h6")].map(headingLevel));
        return levels.length === 0 ? 0 : top - Math.min(...levels);
    }
    MindmapPreview.headingShift = headingShift;
    /** 本文・値の見出しに渡された段の差を足して並べる（`headingShift` が求めた差なら h3〜h6 になる）。見た目は元の段のまま（`data-md-level`） */
    function lowerHeadings({ root, shift }) {
        for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
            const level = headingLevel(heading);
            const lowered = Math.min(level + shift, LOWEST_HEADING_LEVEL);
            const replacement = MindmapPreview.h({
                tag: `h${lowered}`,
                attrs: {
                    "data-md-level": level,
                    // 元の Markdown の行の印を引き継ぐ
                    [MindmapPreview.LINE_ATTR]: heading.getAttribute(MindmapPreview.LINE_ATTR),
                    // h6 を超える段は、読み上げの段で伝える
                    "aria-level": level + shift > LOWEST_HEADING_LEVEL ? level + shift : null,
                },
                children: [...heading.childNodes],
            });
            heading.replaceWith(replacement);
        }
    }
    MindmapPreview.lowerHeadings = lowerHeadings;
    /** 本文の見出しを、本文のスクロール領域の中で画面に入れる（見えている見出しが本文に無ければ false。左右に並べるときは同じ見出しが 3 か所にあるので、矩形を持つ最初のものへ送る） */
    function scrollToHeading({ root, slug }) {
        // 畳んだ節の中の見出しは、包む入れ物を開いてから送る
        MindmapPreview.revealHeading({ root, slug });
        const target = [...root.querySelectorAll(`[data-heading="${CSS.escape(slug)}"]`)].find(MindmapPreview.isRendered);
        if (target === undefined)
            return false;
        target.scrollIntoView({ block: "start" });
        return true;
    }
    /** 本文の印のツールチップを隠すまで待つミリ秒（印からツールチップへポインターを動かす間に消さない） */
    const TIP_HIDE_DELAY_MS = 150;
    /** ツールチップを隠す待ちのタイマー */
    let tipTimer = 0;
    /** 今出している（出していた）ツールチップの印と、押して残しているか */
    let tipState = null;
    /** Esc で閉じて印へフォーカスを戻すとき、その印のフォーカスでツールチップを出し直さない */
    let refocused = null;
    /** 今のツールチップの要素（使い回す 1 つ。隠していても文書に残る） */
    function currentTip() {
        return document.getElementById(MindmapPreview.TERM_TIP_ID);
    }
    /** 押して残しているか。ツールチップがまだ文書にあって開いているときに限る（詳細パネルの描き直しで外れたものは残していないとみなす） */
    function isPinned() {
        return tipState?.pinned === true && currentTip()?.matches(":popover-open") === true;
    }
    /** ツールチップを隠す（`now` が偽のときは、少し待ってから） */
    function hideTermTip(now) {
        window.clearTimeout(tipTimer);
        const hide = () => {
            const tip = currentTip();
            if (tip?.matches(":popover-open") === true)
                tip.hidePopover();
            tipState = null;
        };
        if (now)
            hide();
        else
            tipTimer = window.setTimeout(hide, TIP_HIDE_DELAY_MS);
    }
    /** 印の上に、一致した項目のツールチップを出す。重ねる面の上にも出せるよう、印のある詳細パネル・全画面のモーダルの中に置く（モーダルの外は操作できない） */
    function showTermTip({ mark, entries, pinned, onOpen, }) {
        window.clearTimeout(tipTimer);
        const previous = currentTip();
        // 同じ印を同じ出し方で出しているときは出し直さない（中のスクロールを保つ）
        if (tipState?.mark === mark && tipState.pinned === pinned && previous?.matches(":popover-open") === true)
            return;
        if (previous !== null) {
            if (previous.matches(":popover-open"))
                previous.hidePopover();
            previous.remove();
        }
        const tip = MindmapPreview.termTip({
            entries,
            anchor: mark,
            pinned,
            on: {
                open: (id) => {
                    hideTermTip(true);
                    onOpen(id);
                },
                close: () => hideTermTip(true),
            },
        });
        // ツールチップに乗せている間は消さない。押して残した間は、外れても消さない
        tip.addEventListener("mouseenter", () => window.clearTimeout(tipTimer));
        tip.addEventListener("mouseleave", () => {
            if (!pinned)
                hideTermTip(false);
        });
        (mark.closest("dialog, aside") ?? document.body).append(tip);
        tip.showPopover();
        tipState = { mark, pinned };
    }
    /** Esc でツールチップを隠す。中にフォーカスがあれば印へ戻し、全画面の Esc（元の大きさに戻す）を起こさない */
    document.addEventListener("keydown", (event) => {
        const tip = currentTip();
        // 詳細パネルが出したツールチップだけを対象にする
        if (event.key !== "Escape" || tipState === null || tip?.matches(":popover-open") !== true)
            return;
        const back = tip.contains(document.activeElement) ? tipState.mark : null;
        event.preventDefault();
        event.stopPropagation();
        hideTermTip(true);
        refocused = back;
        back?.focus();
        refocused = null;
    }, true);
    /** 本文の印に乗せる・フォーカスするとツールチップを出し、外れると隠す（本文の要素に委ねて付ける）。用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残し、Tab で中へ移れる */
    function attachTermTips({ root, index, onOpen }) {
        /** イベントの先の印と、一致した項目（用語 → 資料 → 調査の順）。用語 2 件以上か、資料・調査を含むか */
        const markOf = (event) => {
            const mark = event.target.closest?.("a.term") ?? null;
            if (mark === null)
                return null;
            const ids = (mark.getAttribute("data-ids") ?? mark.getAttribute("data-id") ?? "").split(" ");
            const entries = ids.flatMap((id) => {
                const found = index.byId.get(id);
                return found === undefined ? [] : [{ kind: found.kind, item: found.item }];
            });
            return entries.length === 0 ? null : { mark, entries, multi: entries.length > 1 || entries.some((entry) => entry.kind !== "terms") };
        };
        root.addEventListener("mouseover", (event) => {
            const found = markOf(event);
            // 押して残している間は、ほかの印に乗せても替えない
            if (found !== null && !isPinned())
                showTermTip({ ...found, pinned: false, onOpen });
        });
        root.addEventListener("focusin", (event) => {
            const found = markOf(event);
            if (found !== null && found.mark !== refocused)
                showTermTip({ ...found, pinned: false, onOpen });
        });
        root.addEventListener("mouseout", (event) => {
            if (markOf(event) !== null && !isPinned())
                hideTermTip(false);
        });
        root.addEventListener("focusout", (event) => {
            const to = event.relatedTarget;
            // ツールチップの中へ移るときは残す。押して残している間は、フォーカスの行き先が無い（余白を押した）ときも残す
            if (markOf(event) === null || (to instanceof Node && currentTip()?.contains(to) === true))
                return;
            if (to === null && isPinned())
                return;
            hideTermTip(true);
        });
        // 用語 2 件以上か、資料・調査にも一致した印から Tab で、ツールチップの中の最初のリンクへ移る
        root.addEventListener("keydown", (event) => {
            const found = markOf(event);
            const tip = currentTip();
            if (event.key !== "Tab" || event.shiftKey || found === null || !found.multi || tip?.matches(":popover-open") !== true)
                return;
            const first = tip.querySelector("a[href]");
            if (first === null)
                return;
            event.preventDefault();
            first.focus();
        });
        root.addEventListener("click", (event) => {
            const found = markOf(event);
            if (found === null)
                return;
            // 用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残す（移る先は中のリンクで選ぶ）
            if (found.multi) {
                showTermTip({ ...found, pinned: true, onOpen });
                return;
            }
            // 用語 1 件だけに一致した印を押して項目へ移るときは、ツールチップを残さない
            hideTermTip(true);
        });
    }
    /** コメントの一覧から開いたとき、そのコメントの箇所に印の色の地を付け、描いた後にその箇所までスクロールする。合わなければ示さず、項目の先頭を出す */
    function applyHighlight({ root, loc }) {
        let hits = [];
        if (loc.kind === "value") {
            hits = [...root.querySelectorAll(`[${MindmapPreview.VALUE_KEY_ATTR}]`)].filter((element) => element.getAttribute(MindmapPreview.VALUE_KEY_ATTR) === loc.key);
        }
        else {
            const start = loc.start ?? 0;
            const end = loc.end ?? start;
            // HTML の本文: 枠の中で、始まりの行を含む最も内側の要素を示す
            const frame = root.querySelector(`iframe[${HTML_BODY_ATTR}]`);
            if (frame !== null) {
                MindmapPreview.highlightFrameLine({ frame, line: start, scroller: root.querySelector(".panel-body") });
                return;
            }
            const blocks = [...root.querySelectorAll(`.md [${MindmapPreview.LINE_ATTR}]`)];
            const lineOf = (element) => Number(element.getAttribute(MindmapPreview.LINE_ATTR));
            // 始まりの行を含む（始まりの行以前で最も後ろの）ブロックから、終わりの行までのブロック
            const first = blocks.filter((element) => lineOf(element) <= start).at(-1);
            if (first !== undefined)
                hits = blocks.filter((element) => lineOf(element) >= lineOf(first) && lineOf(element) <= end);
        }
        for (const element of hits)
            element.classList.add("loc-hit");
        // 文書に入れた後でないとスクロールできない
        const target = hits[0];
        if (target !== undefined)
            requestAnimationFrame(() => target.scrollIntoView({ block: "center" }));
    }
    /** 詳細パネルの幅の決まり（px）。既定の幅・ドラッグで変えられる下限・上限を決める残す幅（本文を寄せる幅は本文に、重ねる幅は左に）・矢印キー 1 回の刻み・幅を変えられる表示の幅の下限・本文を寄せる表示の幅の下限（`style.css` の境目と同じ値） */
    MindmapPreview.PANEL_WIDTH = { default: 640, min: 480, keepBody: 400, keepLeft: 160, step: 16, resizableFrom: 901, sideFrom: 1100 };
    /** 表示の幅と、本文を寄せるかから、詳細パネルの幅の上限を返す */
    function panelWidthMax({ viewport, mapView }) {
        // 本文を寄せる幅（マップは幅を変えられる幅ならいつも寄せる）は本文に残す幅、重ねる幅は左に残す幅を、表示の幅から引く
        const aligned = viewport >= MindmapPreview.PANEL_WIDTH.sideFrom || (mapView && viewport >= MindmapPreview.PANEL_WIDTH.resizableFrom);
        return viewport - (aligned ? MindmapPreview.PANEL_WIDTH.keepBody : MindmapPreview.PANEL_WIDTH.keepLeft);
    }
    MindmapPreview.panelWidthMax = panelWidthMax;
    /** 詳細パネルの幅を下限以上・上限以下に収め、整数に丸めて返す */
    function clampPanelWidth({ width, max }) {
        return Math.round(Math.max(MindmapPreview.PANEL_WIDTH.min, Math.min(width, max)));
    }
    MindmapPreview.clampPanelWidth = clampPanelWidth;
    /** ドラッグ中の幅。ドラッグしていない間は `null`。ドラッグ中に描き直した区切りは、残した幅の代わりにこの幅から始める */
    let draggingPanelWidth = null;
    /** 詳細パネルの左端に置く幅の区切り。ドラッグと矢印キーで幅を変え、ドラッグを終えたときとキーで変えたときに `onChange` で知らせる */
    function panelResizer({ stored, mapView, onChange }) {
        const separator = MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-resizer", role: "separator", tabindex: "0", "aria-orientation": "vertical", "aria-label": "詳細パネルの幅", "aria-valuemin": MindmapPreview.PANEL_WIDTH.min },
        });
        // 持っている幅。上限を超える残した幅は、窓を広げ直したときに戻せるよう収めずに持つ（幅を変えたら、収めた幅にそろえる）
        let wanted = draggingPanelWidth ?? stored ?? MindmapPreview.PANEL_WIDTH.default;
        // 画面へ当てている幅
        let shown = wanted;
        const maxWidth = () => panelWidthMax({ viewport: innerWidth, mapView: mapView() });
        /** 持っている幅を今の上限に収めて画面へ当てる（詳細パネルの幅と本文の寄せは `--panel-w` を読む）。当てた幅を返す */
        const apply = () => {
            const max = maxWidth();
            shown = clampPanelWidth({ width: wanted, max });
            document.documentElement.style.setProperty("--panel-w", `${shown}px`);
            separator.setAttribute("aria-valuemax", String(max));
            separator.setAttribute("aria-valuenow", String(shown));
            // 下限・上限で止まっている間は、広げる・狭める片方だけのカーソルにする
            separator.dataset.edge = shown <= MindmapPreview.PANEL_WIDTH.min ? "min" : shown >= max ? "max" : "";
            return shown;
        };
        /** 幅を変えて画面へ当て、当てた幅を知らせる */
        const change = (width) => {
            wanted = width;
            wanted = apply();
            onChange(wanted);
        };
        apply();
        // 窓の幅が変わったら、持っている幅を新しい上限で当て直す。文書から外れた区切りの分は受け取らない
        const onResize = () => {
            if (!separator.isConnected) {
                removeEventListener("resize", onResize);
                return;
            }
            apply();
        };
        addEventListener("resize", onResize);
        separator.addEventListener("pointerdown", (event) => {
            if (event.button !== 0)
                return;
            // 本文の文字を選ばず、区切りの外へポインターが出ても動きを受け取り続ける
            event.preventDefault();
            separator.focus({ preventScroll: true });
            separator.setPointerCapture(event.pointerId);
            const { pointerId } = event;
            const startX = event.clientX;
            // 知らせるかは押したときに持っていた幅と比べ、動かす量は押したときに当てていた幅から測る
            const startWanted = wanted;
            const startWidth = apply();
            // 予約した当て直しのフレーム。予約していない間は `null`
            let frame = null;
            draggingPanelWidth = startWidth;
            document.body.classList.add("is-panel-resizing");
            // 左端をつかんでいるので、左へ動かすほど広がる。持っている幅だけを変え、当て直しは次のフレームに 1 回だけ予約する
            const move = (moved) => {
                wanted = clampPanelWidth({ width: startWidth + startX - moved.clientX, max: maxWidth() });
                draggingPanelWidth = wanted;
                if (frame !== null)
                    return;
                frame = requestAnimationFrame(() => {
                    frame = null;
                    apply();
                });
            };
            // 離した・中断したときは区切りから泡立って、区切りが文書から外れたときは document に直接、捕捉が外れたことが届く
            const end = (lost) => {
                if (lost.pointerId !== pointerId)
                    return;
                separator.removeEventListener("pointermove", move);
                document.removeEventListener("lostpointercapture", end);
                if (frame !== null)
                    cancelAnimationFrame(frame);
                draggingPanelWidth = null;
                document.body.classList.remove("is-panel-resizing");
                // 外れた区切りは、描き直した区切りが当てた幅を書き換えない
                if (separator.isConnected)
                    apply();
                if (wanted !== startWanted)
                    onChange(wanted);
            };
            separator.addEventListener("pointermove", move);
            document.addEventListener("lostpointercapture", end);
        });
        separator.addEventListener("keydown", (event) => {
            // ←: 広げる / →: 狭める / Home: 下限 / End: 上限
            const targets = { ArrowLeft: shown + MindmapPreview.PANEL_WIDTH.step, ArrowRight: shown - MindmapPreview.PANEL_WIDTH.step, Home: MindmapPreview.PANEL_WIDTH.min, End: maxWidth() };
            if (!Object.hasOwn(targets, event.key))
                return;
            event.preventDefault();
            change(targets[event.key] ?? shown);
        });
        return separator;
    }
    MindmapPreview.panelResizer = panelResizer;
    /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
    function detailPanel(props) {
        const { id, index, full, on, comment, highlight = null, diff = null, heading = null, minimap = true, bodyLayout = "inline", bodyView = MindmapPreview.BODY_VIEW_DEFAULT, edit = null, resizer = null } = props;
        const editing = edit?.editing === true;
        // 編集の表示の間は、読む表示の代わりに編集の入力を並べる
        const content = editing && edit !== null ? MindmapPreview.detailEditForm(edit.form) : detailBody({ id, index, on, review: comment === null ? null : { items: comment.reviews, edit: comment.edit }, view: resolveDiffView({ id, index, diff }), bodyLayout, bodyView });
        if (!editing && edit !== null)
            markEditedKeys({ root: content, marks: edit.marks, settings: index.data.settings });
        // 中にフォーカスできる要素が無い項目でも、キーボードで送れるように領域ごとフォーカスできるようにする
        const body = MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "詳細の本文" },
            children: [content],
        });
        // 本文を縦に送っても、見出しを固定した表の見出しの行を領域の上端に残す
        MindmapPreview.bindTableHeads(body);
        const head = detailHead(props);
        bindHeadTitle({ head, body });
        // 見出しと下端の入力の間の本文だけをスクロールする。差分の表示の間で、表示の設定で外していなければ、本文の右にミニマップを並べる。編集の表示の間は下端のコメントの入力を隠す
        const footer = comment === null || editing ? null : MindmapPreview.sendForm(comment.form);
        const scroller = MindmapPreview.diffMinimapFrame({ body, shown: diff !== null && minimap });
        let root;
        if (!full) {
            root = MindmapPreview.h({
                tag: "aside",
                attrs: { class: `panel${editing ? " pe-editing" : ""}`, "aria-label": "詳細" },
                children: [resizer, head, scroller, footer],
            });
        }
        else {
            const dialog = MindmapPreview.h({ tag: "dialog", attrs: { class: `full${editing ? " pe-editing" : ""}`, "aria-label": "詳細の全画面" }, children: [head, scroller, footer] });
            // Esc は閉じずに元の大きさ（詳細パネル）に戻す。外側（後ろの幕）を押したときも同じ
            dialog.addEventListener("cancel", (event) => {
                event.preventDefault();
                on.full(false);
            });
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog)
                    on.full(false);
            });
            root = dialog;
        }
        if (highlight !== null)
            applyHighlight({ root, loc: highlight });
        attachTermTips({ root: body, index, onOpen: on.open });
        // 見出しを指して開いた: 描いた後にその見出しを本文の領域の中で画面に入れる（本文に無ければ、本文の頭で開き、ハッシュから外させる）
        if (heading !== null) {
            requestAnimationFrame(() => {
                if (!scrollToHeading({ root: body, slug: heading }))
                    on.heading(null);
            });
        }
        return root;
    }
    MindmapPreview.detailPanel = detailPanel;
})(MindmapPreview || (MindmapPreview = {}));
// コメントの一覧。見ている画面に重ねて左から出すパネルで、スレッドの一覧・スレッド 1 件・レビュー中の書き込みの 3 つの画面を切り替える。
var MindmapPreview;
(function (MindmapPreview) {
    /** コメントの本文の長さの上限（サーバーが受け付ける文字数と同じ） */
    MindmapPreview.COMMENT_BODY_MAX_LENGTH = 10000;
    /** 状態を変える理由の長さの上限（サーバーが受け付ける文字数と同じ） */
    const REASON_MAX_LENGTH = 400;
    /** コメントの ID の連番 */
    function commentNumber(id) {
        return Number(id.replace(/^\D+-/, ""));
    }
    MindmapPreview.commentNumber = commentNumber;
    /** スレッドの ID の連番 */
    function threadNumber(id) {
        return Number(id.replace(/^\D+-/, ""));
    }
    /** 日時の前後（ISO 8601 を時刻として比べる） */
    function byTime(a, b) {
        return Date.parse(a) - Date.parse(b);
    }
    /** スレッドの最後の書き込みの日時 */
    function lastCreated(thread) {
        return thread.posts[thread.posts.length - 1].created;
    }
    /** スレッドを状態とタグで絞り、最後の書き込みの新しい順に並べる（渡した配列は変えない） */
    function visibleThreads(threads, filter, tag) {
        return threads
            .filter((thread) => filter === "all" || thread.status === filter)
            .filter((thread) => tag === null || thread.tags.includes(tag))
            .sort((a, b) => byTime(lastCreated(b), lastCreated(a)) || threadNumber(b.id) - threadNumber(a.id));
    }
    MindmapPreview.visibleThreads = visibleThreads;
    /** タグで絞ったスレッドの、状態の絞り込みに出す件数 */
    function threadCounts(threads, tag) {
        const tagged = tag === null ? threads : threads.filter((thread) => thread.tags.includes(tag));
        const open = tagged.filter((thread) => thread.status === "open").length;
        return { open, closed: tagged.length - open, all: tagged.length };
    }
    MindmapPreview.threadCounts = threadCounts;
    /** レビュー中の書き込みのうち、一覧の先頭に出す新しいスレッドの最初の書き込み（クローズの絞り込みとタグの絞り込みでは出さない） */
    function pendingThreads(items, filter, tag) {
        if (filter === "closed" || tag !== null)
            return [];
        return items.filter((item) => item.thread === null);
    }
    MindmapPreview.pendingThreads = pendingThreads;
    /** レビュー中の書き込みが、クローズのスレッドへの返信か（スレッドが見つからなければ偽。サーバーが 409 で返す） */
    function isBlockedReply(item, threads) {
        if (item.thread === null)
            return false;
        return threads.find((thread) => thread.id === item.thread)?.status === "closed";
    }
    MindmapPreview.isBlockedReply = isBlockedReply;
    /** スレッドの書き込みと状態の記録を、日時の順の 1 本の並びにする（同じ日時は書き込みを先にし、それぞれの中の並びを保つ） */
    function threadTimeline(thread) {
        const entries = [
            ...thread.posts.map((post) => ({ post, at: post.created, rank: 0 })),
            ...thread.events.map((event) => ({ event, at: event.created, rank: 1 })),
        ];
        return entries.sort((a, b) => byTime(a.at, b.at) || a.rank - b.rank);
    }
    MindmapPreview.threadTimeline = threadTimeline;
    /** 送った結果の文言（印と文）。結果が無いときは null */
    function outcomeContent({ result, checkedCount }) {
        if (result === null) {
            // チェックが 0 件
            return checkedCount === 0 ? [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: ["送る書き込みにチェックを付けてください。"] })] : null;
        }
        if (result.kind === "sending") {
            return [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["送っています"] })];
        }
        if (result.kind === "sent") {
            const time = result.at === undefined ? "" : MindmapPreview.formatJst(result.at).slice(-5);
            const count = result.count ?? 0;
            // Claude Code に入力できなかった: 送った内容は残り、次の話し合いの取り込みに任せる
            if (result.entered !== true) {
                return [
                    MindmapPreview.icon("alert"),
                    MindmapPreview.h({
                        tag: "span",
                        children: [
                            `${count} 件を送りましたが、Claude Code には入力できませんでした（${time}）。送った内容は保存されていて、次に話し合いを始めたときに取り込まれます。`,
                        ],
                    }),
                ];
            }
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`${count} 件を送り、Claude Code に入力しました（${time}）。`] })];
        }
        if (result.kind === "stale") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`送れませんでした。送れない書き込みが ${result.count ?? 0} 件あります。`] })];
        }
        const detail = result.detail ?? null;
        return [
            MindmapPreview.icon("alert"),
            MindmapPreview.h({
                tag: "span",
                children: [
                    detail === null
                        ? "送れませんでした。サーバーが止まっています。立ち上げ直してから送ってください。"
                        : `送れませんでした。${detail}`,
                ],
            }),
        ];
    }
    /** レビュー中の書き込みの読み上げの名前の頭（返信は「{スレッドの ID} への返信」、新しいスレッドは「{向けた項目の ID} へのコメント」） */
    function reviewLabel(item) {
        // 詳細パネルへ渡す行には `thread` を持たないものもある
        if (item.thread !== null && item.thread !== undefined)
            return `${item.thread} への返信`;
        return item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
    }
    /** 行の向けた項目（押すとその項目を開く。消えた項目は押せない。項目を指さないときは何も出さない） */
    function targetCell(item, props) {
        // 項目を指さない
        if (item.target === null)
            return null;
        const title = props.titleOf(item.target);
        // 項目が消えた: 押せない ID だけを出す
        if (title === null) {
            return MindmapPreview.h({ tag: "span", attrs: { class: "row-target gone" }, children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.target] })] });
        }
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "row-target idlink", type: "button", "data-focus": `open:${item.id}`, onclick: () => props.on.open(item) },
            children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.target] }), MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [title] })],
        });
    }
    /** 本文をその場で書き換える入力欄と「キャンセル」「修正」（コメントの一覧と詳細パネルが使う） */
    function reviewEditForm({ item, body, error, focus, on, }) {
        const field = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                name: "body",
                rows: 2,
                maxlength: MindmapPreview.COMMENT_BODY_MAX_LENGTH,
                "aria-label": `${item.id} へのコメントの本文`,
                "aria-keyshortcuts": "Control+Enter",
                "data-focus": `${focus}edit:${item.id}`,
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では確定しない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        form.requestSubmit();
                    }
                    if (key.key === "Escape") {
                        // 詳細の全画面の `dialog` の `cancel` を起こさない
                        event.preventDefault();
                        event.stopPropagation();
                        on.cancelEdit();
                    }
                },
            },
            children: [body ?? item.body],
        });
        // 理由があるときだけ `role="alert"` を持たせる（空のまま警告として読み上げさせない）
        const message = MindmapPreview.h({ tag: "p", attrs: { class: "send-msg failed", role: error ? "alert" : null }, children: error ? [MindmapPreview.icon("alert"), error] : [] });
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "row-edit",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    // 空白だけは送らない
                    if (field.value.trim() === "") {
                        field.setAttribute("aria-invalid", "true");
                        message.setAttribute("role", "alert");
                        message.replaceChildren(MindmapPreview.icon("alert"), "コメントを入れてから直してください。");
                        field.focus();
                        return;
                    }
                    on.saveEdit(item.id, field.value);
                },
            },
            children: [
                field,
                message,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-edit-actions" },
                    children: [
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn ghost", type: "button", onclick: on.cancelEdit }, children: ["キャンセル"] }),
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn primary", type: "submit", title: "修正（Ctrl+Enter）" }, children: ["修正"] }),
                    ],
                }),
            ],
        });
        return form;
    }
    MindmapPreview.reviewEditForm = reviewEditForm;
    /** 行の右上に置く、鉛筆の印の「修正」とごみ箱の印の「削除」（コメントの一覧と詳細パネルが使う） */
    function reviewRowActions({ item, focus, on, }) {
        const label = reviewLabel(item);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "row-actions" },
            children: [
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": `${label}を修正`,
                        title: "修正",
                        "data-focus": `${focus}edit-open:${item.id}`,
                        onclick: () => on.edit(item.id),
                    },
                    children: [MindmapPreview.icon("edit")],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn",
                        type: "button",
                        "aria-label": `${label}を削除`,
                        title: "削除",
                        "data-focus": `${focus}remove:${item.id}`,
                        onclick: () => on.remove(item.id),
                    },
                    children: [MindmapPreview.icon("trash")],
                }),
            ],
        });
    }
    MindmapPreview.reviewRowActions = reviewRowActions;
    /** 消した行（元の場所に「コメントを削除しました。」と「元に戻す」を出す。コメントの一覧と詳細パネルが使う） */
    function removedReviewRow({ item, focus, on, }) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "row removed", "data-comment": item.id },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "removed-msg", role: "status" }, children: ["コメントを削除しました。"] }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn ghost", type: "button", "data-focus": `${focus}restore:${item.id}`, onclick: () => on.restore(item.id) },
                    children: [MindmapPreview.icon("undo"), "元に戻す"],
                }),
            ],
        });
    }
    MindmapPreview.removedReviewRow = removedReviewRow;
    /** 行の頭（返信は返信先のスレッドの状態の札と題、新しいスレッドは向けた項目） */
    function rowHead(item, props) {
        const thread = item.thread === null ? undefined : props.threads.find((entry) => entry.id === item.thread);
        // 新しいスレッド: 向けた項目
        if (item.thread === null) {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "row-head" },
                children: [MindmapPreview.h({ tag: "span", attrs: { class: "row-kind" }, children: ["新しいスレッド"] }), targetCell(item, props)],
            });
        }
        // 返信: 返信先のスレッド（読めていなければ ID だけ）
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "row-head" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "row-kind" }, children: ["返信"] }),
                thread === undefined
                    ? MindmapPreview.h({ tag: "span", attrs: { class: "row-target gone" }, children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [item.thread] })] })
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "row-target idlink-like",
                            type: "button",
                            "data-focus": `open:${item.id}`,
                            onclick: () => props.on.openThread(thread.id, false),
                        },
                        children: [MindmapPreview.threadState(thread.status), MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [MindmapPreview.threadTitle(thread)] })],
                    }),
            ],
        });
    }
    /** 「スレッドを開く」の入口（新しいスレッドの行は、まだ送っていないそのスレッドを開く。クローズのスレッドへの返信の行は、そのスレッドを開く） */
    function openThreadButton({ item, id, pending, className }, props) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: className, type: "button", "data-focus": `thread-open:${item.id}`, onclick: () => props.on.openThread(id, pending) },
            children: ["スレッドを開く"],
        });
    }
    /** レビュー中の書き込みの行 */
    function reviewRow(item, props) {
        const reason = props.stale.get(item.id);
        const label = reviewLabel(item);
        const blocked = isBlockedReply(item, props.threads);
        // 詳細パネルで書き換えている行は、入力欄を出さず、「修正」「削除」も出さない
        const editingInDetail = props.editing === item.id && props.editingIn === "detail";
        const editingInList = props.editing === item.id && !editingInDetail;
        const focused = item.id === props.selected || (props.reviewFocus !== null && item.thread === props.reviewFocus);
        // 書き換えていない行の本文は、折り返した後の見た目の行で畳む
        const fold = editingInList
            ? null
            : MindmapPreview.reviewBodyFold({
                id: item.id,
                label,
                body: item.body,
                changeSets: props.changeSetOf,
                open: props.expanded.has(item.id),
                on: { toggle: props.on.fold, changeSet: props.on.changeSet },
            });
        return MindmapPreview.h({
            tag: "li",
            attrs: {
                class: `row${focused ? " selected" : ""}${reason === undefined ? "" : " stale"}${blocked ? " blocked" : ""}`,
                "data-comment": item.id,
            },
            children: [
                MindmapPreview.h({
                    tag: "input",
                    attrs: {
                        type: "checkbox",
                        class: "row-check",
                        checked: !blocked && props.checked.has(item.id),
                        disabled: blocked,
                        "aria-label": `${label}を送る`,
                        "data-focus": `check:${item.id}`,
                        onchange: (event) => props.on.check(item.id, event.target.checked),
                    },
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-main" },
                    children: [
                        rowHead(item, props),
                        item.loc === null
                            ? null
                            : MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "review-loc" },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "review-loc-name" }, children: [MindmapPreview.locationLabel(item.loc)] }),
                                    MindmapPreview.h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [item.loc.text] }),
                                ],
                            }),
                        editingInList
                            ? reviewEditForm({
                                item,
                                body: props.editBody ?? null,
                                error: props.editError ?? null,
                                focus: "",
                                on: { saveEdit: props.on.saveEdit, cancelEdit: props.on.cancelEdit },
                            })
                            : fold?.body ?? null,
                        // クローズのスレッドへの返信: 送れない理由と、そのスレッドを開く入口
                        blocked && item.thread !== null
                            ? MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "row-stale row-blocked" },
                                children: [
                                    MindmapPreview.icon("alert"),
                                    MindmapPreview.h({ tag: "span", children: ["クローズのスレッドへの返信は送れません。オープンに戻すと送れます。"] }),
                                    openThreadButton({ item, id: item.thread, pending: false, className: "btn ghost" }, props),
                                ],
                            })
                            : null,
                        // 新しいスレッド: 開閉のボタンと、まだ送っていないそのスレッドを開く入口
                        item.thread === null
                            ? MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "row-thread-open" },
                                children: [fold?.more ?? null, openThreadButton({ item, id: item.id, pending: true, className: "btn ghost" }, props)],
                            })
                            : null,
                        // 返信: 開閉のボタンだけの行（ボタンを出さないときは行ごと出さない）
                        item.thread !== null && fold !== null ? MindmapPreview.h({ tag: "div", attrs: { class: "review-more-row" }, children: [fold.more] }) : null,
                        reason === undefined
                            ? null
                            : MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "row-stale", role: "alert" },
                                children: [
                                    MindmapPreview.icon("alert"),
                                    MindmapPreview.h({ tag: "span", children: [reason] }),
                                    // 項目が記録にあるときだけ、箇所を外して項目へのコメントにできる
                                    item.loc !== null && item.target !== null && props.titleOf(item.target) !== null
                                        ? MindmapPreview.h({
                                            tag: "button",
                                            attrs: { class: "btn ghost", type: "button", "data-focus": `unloc:${item.id}`, onclick: () => props.on.unloc(item.id) },
                                            children: ["箇所を外す"],
                                        })
                                        : null,
                                ],
                            }),
                    ],
                }),
                editingInDetail ? null : reviewRowActions({ item, focus: "", on: { edit: props.on.edit, remove: props.on.remove } }),
            ],
        });
    }
    /** 送る帯の先頭に置く、文字を添えない三状態のチェックの箱。押すと、全てチェックしていれば全て外し、それ以外は全てチェックする */
    function selectAllBox({ ids, checked, onChange, }) {
        const count = ids.filter((id) => checked.has(id)).length;
        const checkbox = MindmapPreview.h({
            tag: "input",
            attrs: {
                type: "checkbox",
                checked: count === ids.length,
                "aria-label": "すべて選ぶ",
                onchange: () => onChange(count < ids.length),
            },
        });
        // 一部だけチェックしているときの横棒は、属性でなくプロパティで付ける
        checkbox.indeterminate = count > 0 && count < ids.length;
        return MindmapPreview.h({ tag: "label", attrs: { class: "legend-all-check", title: "すべて選ぶ" }, children: [checkbox] });
    }
    /** 見出しの帯（見出し・レビュー中の入口・閉じる） */
    function panelHead(props) {
        const count = props.items.length;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "comments-head" },
            children: [
                MindmapPreview.h({ tag: "h2", children: ["コメント"] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                // レビュー中の書き込みの画面では、入口を出さない（押しても何も変わらない）
                props.view === "review"
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: `btn review-entry${count === 0 ? " zero" : ""}`,
                            type: "button",
                            "aria-label": `レビュー中の書き込みを確かめる（${count} 件）`,
                            "data-focus": "review",
                            onclick: () => props.on.review(),
                        },
                        children: ["レビュー中", MindmapPreview.h({ tag: "span", attrs: { class: "count", "aria-hidden": "true" }, children: [count] })],
                    }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "icon-btn", type: "button", "aria-label": "コメントの一覧を閉じる", "data-focus": "close", onclick: props.on.close },
                    children: [MindmapPreview.icon("x")],
                }),
            ],
        });
    }
    /** 状態の絞り込みの選択肢 */
    const THREAD_FILTERS = [
        { value: "open", label: "オープン" },
        { value: "closed", label: "クローズ" },
        { value: "all", label: "すべて" },
    ];
    /** 0 件のときの文言 */
    function emptyThreadsText({ filter, tag }) {
        const state = { open: "オープンの", closed: "クローズの", all: "" }[filter];
        return tag === null ? `${state}スレッドはありません。` : `タグ「${tag}」の${state}スレッドはありません。`;
    }
    /** スレッドを読めなかった理由の文言 */
    function threadsErrorText(error) {
        return `スレッドを読めませんでした。${error.detail ?? "サーバーが止まっています。立ち上げ直してから開いてください。"}`;
    }
    /** 一覧の下端の、新しいスレッドを立てる入口と入力 */
    function newThreadBox(props) {
        if (!props.composing) {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-free talk-new" },
                children: [
                    MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "btn", type: "button", "data-focus": "compose", onclick: () => props.on.compose(true) },
                        children: [MindmapPreview.icon("plus"), "新しいスレッド"],
                    }),
                ],
            });
        }
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "comments-free talk-new open" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "talk-new-head" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "send-label" }, children: ["新しいスレッド"] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "新しいスレッドの入力を閉じる", "data-focus": "compose-close", onclick: () => props.on.compose(false) },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                MindmapPreview.sendForm({ ...props.free, collapsed: false }),
            ],
        });
    }
    /** スレッドの一覧（絞り込みの帯・行・下端の新しいスレッド）を返す */
    function threadListView(props) {
        const { threads, items, filter, tag, on } = props;
        const counts = threadCounts(threads, tag);
        const rows = visibleThreads(threads, filter, tag);
        const pending = pendingThreads(items, filter, tag);
        const total = threads.filter((thread) => filter === "all" || thread.status === filter).length;
        const empty = rows.length + pending.length === 0;
        return [
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "talk-band" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "segment talk-filter", role: "group", "aria-label": "スレッドの状態で絞る" },
                        children: THREAD_FILTERS.map((entry) => MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                type: "button",
                                "aria-pressed": String(entry.value === filter),
                                "data-focus": `filter:${entry.value}`,
                                onclick: () => on.filter(entry.value),
                            },
                            children: [entry.label, MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [counts[entry.value]] })],
                        })),
                    }),
                    tag === null
                        ? null
                        : MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "chips talk-chips" },
                            children: [
                                MindmapPreview.h({
                                    tag: "span",
                                    attrs: { class: "chip" },
                                    children: [
                                        MindmapPreview.icon("hash"),
                                        tag,
                                        MindmapPreview.h({
                                            tag: "button",
                                            attrs: { type: "button", "aria-label": `タグ「${tag}」の絞り込みを外す`, "data-focus": "clear-tag", onclick: () => on.clearTag() },
                                            children: [MindmapPreview.icon("x")],
                                        }),
                                    ],
                                }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "hint" }, children: [`${rows.length} / ${total} 件`] }),
                            ],
                        }),
                ],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body" },
                children: [
                    // 読めなかった理由は、並べる行の上に出す（まだ送っていない新しいスレッドは並べる）
                    props.threadsError === null
                        ? null
                        : MindmapPreview.h({ tag: "p", attrs: { class: "send-msg failed", role: "alert" }, children: [MindmapPreview.icon("alert"), threadsErrorText(props.threadsError)] }),
                    empty
                        ? props.threadsError === null
                            ? MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("comment"), emptyThreadsText({ filter, tag })] })
                            : null
                        : MindmapPreview.h({
                            tag: "ul",
                            attrs: { class: "th-list" },
                            children: [
                                ...pending.map((item) => MindmapPreview.threadRow({ pending: item, on: { open: on.openThread, tag: on.tag } })),
                                ...rows.map((thread) => MindmapPreview.threadRow({
                                    thread,
                                    hasPendingReply: items.some((item) => item.thread === thread.id),
                                    activeTag: tag,
                                    on: { open: on.openThread, tag: on.tag },
                                })),
                            ],
                        }),
                ],
            }),
            newThreadBox(props),
        ];
    }
    MindmapPreview.threadListView = threadListView;
    /** スレッドの見出し（戻る・状態を変える・理由の入力と失敗の理由・題・向けた項目とタグ） */
    function threadHead({ status, title, target, loc, tags, statusButton, extra, props, }) {
        const targetTitle = target === null ? null : props.titleOf(target);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "th-head" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "th-head-bar" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn ghost th-back", type: "button", "data-focus": "back", onclick: () => props.on.back() },
                            children: [MindmapPreview.icon("back"), "一覧へ戻る"],
                        }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        statusButton,
                    ],
                }),
                ...extra,
                MindmapPreview.h({ tag: "h3", attrs: { class: "th-heading" }, children: [MindmapPreview.threadState(status), MindmapPreview.h({ tag: "span", children: [title] })] }),
                target === null && tags.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "th-meta" },
                        children: [
                            target === null
                                ? null
                                : targetTitle === null
                                    ? MindmapPreview.h({ tag: "span", attrs: { class: "row-target gone" }, children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] })] })
                                    : MindmapPreview.h({
                                        tag: "button",
                                        attrs: {
                                            class: "row-target",
                                            type: "button",
                                            "data-focus": "target",
                                            onclick: () => (loc === null ? props.on.openId(target) : props.on.openId(target, loc)),
                                        },
                                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [target] }), MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [targetTitle] })],
                                    }),
                            ...tags.map((entry) => MindmapPreview.h({ tag: "span", attrs: { class: "th-tag static" }, children: [MindmapPreview.icon("hash"), MindmapPreview.h({ tag: "span", children: [entry] })] })),
                        ],
                    }),
            ],
        });
    }
    /** 理由の入力（任意）。状態を変える前に出し、確定で変えた後の状態と理由を 1 回で送る */
    function reasonForm({ closing, props }) {
        const { reason, on } = props;
        const saving = reason.status === "saving";
        const verb = closing ? "クローズにする" : "オープンに戻す";
        const field = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                id: "reason-body",
                name: "reason",
                rows: 2,
                maxlength: REASON_MAX_LENGTH,
                "aria-keyshortcuts": "Control+Enter",
                "data-focus": "reason",
                readonly: saving,
                // 打つたびには知らせず、確定のときに中身を渡す（描き直すときは、入口が入力欄から読む）
                onchange: () => on.reasonInput(field.value),
                onkeydown: (event) => {
                    const key = event;
                    // 変換の確定の Enter では確定しない
                    if (key.key === "Enter" && (key.ctrlKey || key.metaKey) && !key.isComposing) {
                        key.preventDefault();
                        form.requestSubmit();
                    }
                    // Esc は理由の入力をやめる（一覧へは戻らない）
                    if (key.key === "Escape") {
                        key.preventDefault();
                        key.stopPropagation();
                        on.reasonOpen(false);
                    }
                },
            },
            children: [reason.body],
        });
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "th-reason",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    if (saving)
                        return;
                    on.setStatus(closing ? "closed" : "open", field.value);
                },
            },
            children: [
                MindmapPreview.h({ tag: "label", attrs: { class: "send-label", for: "reason-body" }, children: ["理由（任意）"] }),
                field,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-edit-actions" },
                    children: [
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn ghost", type: "button", "data-focus": "reason-cancel", onclick: () => on.reasonOpen(false) }, children: ["キャンセル"] }),
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn primary", type: "submit", "data-focus": "reason-ok", disabled: saving }, children: [verb] }),
                    ],
                }),
            ],
        });
        return form;
    }
    /** 状態を変えられなかった理由 */
    function statusFailure({ closing, detail }) {
        const head = closing ? "クローズにできませんでした。" : "オープンに戻せませんでした。";
        return MindmapPreview.h({
            tag: "p",
            attrs: { class: "send-msg failed th-action-msg", role: "alert" },
            children: [MindmapPreview.icon("alert"), `${head}${detail ?? "サーバーが止まっています。立ち上げ直してから押してください。"}`],
        });
    }
    /** レビュー中の書き込みの `li`（スレッドの中のレビュー中の書き込み） */
    function pendingPostItem(item, props) {
        return MindmapPreview.threadPost({
            pending: item,
            titles: props.titleOf,
            changeSets: props.changeSetOf,
            editing: props.editing === item.id && props.editingIn !== "detail",
            editBody: props.editBody ?? null,
            editError: props.editError ?? null,
            on: {
                openId: (id) => props.on.openId(id),
                changeSet: props.on.changeSet,
                edit: props.on.edit,
                saveEdit: props.on.saveEdit,
                cancelEdit: props.on.cancelEdit,
                remove: props.on.remove,
            },
        });
    }
    /** まだ送っていない新しいスレッド（最初の書き込みをレビュー中の形で出し、状態を変えると返信の入力を出さない） */
    function pendingThreadView(commentId, props) {
        const item = props.items.find((entry) => entry.id === commentId);
        const gone = props.removed.find((entry) => entry.id === commentId);
        const shown = item ?? gone;
        return [
            threadHead({
                status: "pending",
                title: shown === undefined ? "" : shown.body.split("\n")[0],
                target: shown?.target ?? null,
                loc: shown?.loc ?? null,
                tags: [],
                statusButton: null,
                extra: [],
                props,
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body th-body" },
                children: [
                    MindmapPreview.h({
                        tag: "ol",
                        attrs: { class: "posts", "aria-label": "書き込み" },
                        children: [
                            item !== undefined
                                ? pendingPostItem(item, props)
                                : gone === undefined
                                    ? null
                                    : removedReviewRow({ item: gone, focus: "", on: { restore: props.on.restore } }),
                        ],
                    }),
                ],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-free" },
                children: [MindmapPreview.h({ tag: "p", attrs: { class: "th-closed-note" }, children: [MindmapPreview.icon("edit"), "まだ送っていないスレッドです。"] })],
            }),
        ];
    }
    /** スレッド 1 件（見出し・書き込みの並び・下端）を返す。まだ送っていない新しいスレッドも開く */
    function threadView(props) {
        const { opened } = props;
        if (opened !== null && opened.pending)
            return pendingThreadView(opened.id, props);
        const thread = props.threads.find((entry) => entry.id === opened?.id);
        // 開いているスレッドが無い（呼ぶ側が一覧へ戻す）
        if (thread === undefined)
            return [];
        const { reason, on } = props;
        const open = thread.status === "open";
        const saving = reason.status === "saving";
        // 理由の入力を出している間は、状態を変えるボタンを出さない
        const statusButton = reason.open
            ? null
            : MindmapPreview.h({
                tag: "button",
                attrs: { class: "btn", type: "button", "data-focus": "status", disabled: saving, onclick: () => on.reasonOpen(true) },
                children: open ? [MindmapPreview.icon("check"), "クローズにする"] : [MindmapPreview.icon("undo"), "オープンに戻す"],
            });
        // レビュー中の返信と、消した返信（元の場所に「元に戻す」を出す）を溜めた順に並べる
        const replies = [
            ...props.items.filter((item) => item.thread === thread.id).map((item) => ({ item, gone: false })),
            ...props.removed.filter((item) => item.thread === thread.id).map((item) => ({ item, gone: true })),
        ].sort((a, b) => commentNumber(a.item.id) - commentNumber(b.item.id));
        return [
            threadHead({
                status: thread.status,
                title: MindmapPreview.threadTitle(thread),
                target: thread.target,
                loc: thread.loc,
                tags: thread.tags,
                statusButton,
                extra: [
                    reason.open ? reasonForm({ closing: open, props }) : null,
                    reason.status === "failed" ? statusFailure({ closing: open, detail: reason.detail }) : null,
                ],
                props,
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body th-body" },
                children: [
                    MindmapPreview.h({
                        tag: "ol",
                        attrs: { class: "posts", "aria-label": "書き込み" },
                        children: [
                            ...threadTimeline(thread).map((entry) => "post" in entry
                                ? MindmapPreview.threadPost({ post: entry.post, titles: props.titleOf, changeSets: props.changeSetOf, on: { openId: (id) => on.openId(id), changeSet: on.changeSet, edit: on.edit, saveEdit: on.saveEdit, cancelEdit: on.cancelEdit, remove: on.remove } })
                                : MindmapPreview.threadPost({ event: entry.event, on: { openId: (id) => on.openId(id), changeSet: on.changeSet, edit: on.edit, saveEdit: on.saveEdit, cancelEdit: on.cancelEdit, remove: on.remove } })),
                            ...replies.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : pendingPostItem(item, props))),
                        ],
                    }),
                ],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-free" },
                children: [
                    open
                        ? MindmapPreview.replyForm({ thread: thread.id, ...props.reply, on: { input: on.replyInput, save: on.reply } })
                        : MindmapPreview.h({ tag: "p", attrs: { class: "th-closed-note" }, children: [MindmapPreview.icon("check"), "クローズにしたスレッドです。"] }),
                ],
            }),
        ];
    }
    MindmapPreview.threadView = threadView;
    /** レビュー中の書き込み（見出し・送る帯・行・空の状態）を返す */
    function reviewView(props) {
        const { items, removed, checked, result, on } = props;
        // 送れる書き込み（クローズのスレッドへの返信を除く）
        const sendable = items.filter((item) => !isBlockedReply(item, props.threads));
        const checkedCount = sendable.filter((item) => checked.has(item.id)).length;
        const isEmpty = items.length === 0 && removed.length === 0;
        // 送る帯は一覧の上端に留める。送っている間とチェックが 0 件のときは押せない
        const sending = result?.kind === "sending";
        const message = outcomeContent({ result, checkedCount });
        // 送った直後は、送るものが無くなっても結果を出す
        const band = isEmpty && result === null
            ? null
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "send-band" },
                children: [
                    sendable.length === 0
                        ? null
                        : selectAllBox({ ids: sendable.map((item) => item.id), checked, onChange: on.checkAll }),
                    sendable.length === 0
                        ? null
                        : MindmapPreview.h({ tag: "span", attrs: { class: "send-count" }, children: [`${checkedCount} / ${sendable.length} 件`] }),
                    isEmpty
                        ? null
                        : MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary",
                                type: "button",
                                "data-focus": "send",
                                disabled: checkedCount === 0 || sending,
                                onclick: () => on.send(),
                            },
                            children: [MindmapPreview.icon("send"), `まとめて送る（${checkedCount} 件）`],
                        }),
                    MindmapPreview.h({ tag: "p", attrs: { class: `send-msg${result === null ? "" : ` ${result.kind}`}`, role: "status" }, children: message ?? [] }),
                ],
            });
        // 消した書き込みは元の場所（ID の連番の順）に出す
        const rows = [...items.map((item) => ({ item, gone: false })), ...removed.map((item) => ({ item, gone: true }))].sort((a, b) => commentNumber(a.item.id) - commentNumber(b.item.id));
        const nodes = [
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "th-head review-head" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "th-head-bar" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "btn ghost th-back", type: "button", "data-focus": "back", onclick: () => on.back() },
                                children: [MindmapPreview.icon("back"), "戻る"],
                            }),
                            MindmapPreview.h({ tag: "h3", attrs: { class: "review-title" }, children: ["レビュー中の書き込み", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })] }),
                        ],
                    }),
                ],
            }),
            band,
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "comments-body" },
                children: [
                    isEmpty
                        ? MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("comment"), "レビュー中の書き込みはありません。"] })
                        : MindmapPreview.h({
                            tag: "ul",
                            attrs: { class: "comments-list" },
                            children: rows.map(({ item, gone }) => (gone ? removedReviewRow({ item, focus: "", on: { restore: on.restore } }) : reviewRow(item, props))),
                        }),
                ],
            }),
        ];
        return nodes.filter((node) => node !== null);
    }
    MindmapPreview.reviewView = reviewView;
    /** コメントの一覧を返す */
    function commentsPanel(props) {
        // 開いているスレッドが無いときは、スレッドの一覧を出す
        const threadScreen = props.view === "thread" ? threadView(props) : [];
        const screen = props.view === "review" ? reviewView(props) : threadScreen.length > 0 ? threadScreen : threadListView(props);
        return MindmapPreview.h({
            tag: "aside",
            attrs: { class: "comments-panel", "aria-label": "コメントの一覧" },
            children: [panelHead(props), ...screen],
        });
    }
    MindmapPreview.commentsPanel = commentsPanel;
})(MindmapPreview || (MindmapPreview = {}));
// 保存待ちのパネル。保存待ちの編集を項目ごとに並べ、1 件ずつ取り消し、まとめて保存する。コメントの一覧と同じ左から出すパネル。
var MindmapPreview;
(function (MindmapPreview) {
    /** 設定のキーの呼び名 */
    const SETTING_LABELS = {
        summary: "題名",
        description: "説明",
        playbooks: "プレイブック",
        phases: "フェーズ",
        target_label: "最上位の軸の呼び名",
        goal: "ゴール",
        targets: "対象",
        categories: "カテゴリー",
        links: "関連する場所",
        history_limit: "保持する回数",
    };
    /** 項目のキーの呼び名（詳細パネルの見出しと同じ言葉） */
    MindmapPreview.KEY_LABELS = {
        status: "状態",
        title: "タイトル",
        target: "機能",
        category: "カテゴリー",
        phase: "フェーズ",
        tags: "タグ",
        depends_on: "依存先",
        answer: "決定内容",
        reason: "理由",
        body: "本文",
        result: "結果",
        kind: "種類",
        question: "問い",
        conclusion: "結論",
        confidence: "確からしさ",
        related: "関連",
        withdrawn: "取り下げ",
        meaning: "意味",
        aliases: "別名",
        content: "内容",
        date: "日付",
        deliverable: "納品物",
        description: "説明",
    };
    /** 値を 1 行の文字にする（空は「（空）」、配列は「、」でつなぐ） */
    function flat(value) {
        if (value === undefined || value === null || value === "")
            return "（空）";
        if (Array.isArray(value))
            return value.length === 0 ? "（空）" : value.map((entry) => flat(entry)).join("、");
        if (value === true)
            return "はい";
        if (value === false)
            return "いいえ";
        // 390: 関連の要素は「ID（種類）」にする
        if (typeof value === "object" && typeof value.to === "string")
            return `${value.to}（${MindmapPreview.RELATION_TYPES[value.type]?.label ?? "種類なし"}）`;
        if (typeof value === "object")
            return JSON.stringify(value);
        return String(value).replace(/\s+/g, " ");
    }
    /** 1 件の編集の「何を」と「前 → 後」。本文・削除は値を出さず、追加は前を持たない */
    function editRowText(edit) {
        const key = edit.key ?? "";
        switch (edit.op) {
            case "item-add":
                return { what: "項目を追加", before: null, after: flat(edit.value?.title) };
            case "item-remove":
                return { what: "項目を削除", before: null, after: null };
            case "setting":
                return { what: SETTING_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
            case "option-add":
                return {
                    what: `案 ${key} を追加`,
                    before: null,
                    after: flat(edit.value?.content),
                };
            case "option-remove":
                return { what: `案 ${key} を削除`, before: null, after: null };
            case "option-edit":
                return {
                    what: `案 ${key}`,
                    before: flat(edit.before?.content ?? edit.before),
                    after: flat(edit.value?.content),
                };
            case "adopt":
                return { what: "採用する案", before: flat(edit.before ?? "なし"), after: flat(edit.value) };
            default:
                if (key === "body")
                    return { what: "本文", before: null, after: null };
                // タグは前後を `{name, main?}` の並びのまま返す（行は tagList で描く）
                if (key === "tags") {
                    return { what: MindmapPreview.KEY_LABELS[key], before: tagsOrFlat(edit.before), after: tagsOrFlat(edit.value) };
                }
                return { what: MindmapPreview.KEY_LABELS[key] ?? key, before: flat(edit.before), after: flat(edit.value) };
        }
    }
    MindmapPreview.editRowText = editRowText;
    /** 編集を向け先ごとに、最初に溜めた順にまとめる */
    function groupEdits(edits) {
        const groups = [];
        for (const edit of edits) {
            const found = groups.find((group) => group.target === edit.target);
            if (found === undefined)
                groups.push({ target: edit.target, edits: [edit] });
            else
                found.edits.push(edit);
        }
        return groups;
    }
    MindmapPreview.groupEdits = groupEdits;
    /** まとまりの見出しに出す、項目の種類・ID・タイトル（設定は「設定」、追加する項目は「{種類}を追加」） */
    function describeTarget({ target, edits, index, }) {
        if (target === MindmapPreview.SETTINGS_TARGET)
            return { kind: "設定", id: null, title: index.data.settings.summary };
        const added = edits.find((edit) => edit.op === "item-add");
        if (added !== undefined) {
            const kind = MindmapPreview.KIND_LABEL[(added.key ?? "")] ?? added.key ?? "";
            return { kind: `${kind}を追加`, id: null, title: added.value.title ?? "" };
        }
        const entry = index.byId.get(target);
        if (entry === undefined)
            return { kind: "項目", id: target, title: "" };
        return { kind: MindmapPreview.KIND_LABEL[entry.kind], id: target, title: entry.item.title };
    }
    /** タグの値は並びのまま、それ以外は `flat` の文字にする */
    function tagsOrFlat(value) {
        return Array.isArray(value) ? value : flat(value);
    }
    /** 前後の値の表示（タグの並びは tagList で描き、空の並びは「（空）」） */
    function valueView(value) {
        if (typeof value === "string")
            return value;
        return value.length === 0 ? flat(value) : MindmapPreview.tagList(value);
    }
    /** 読み上げ用の「前:」「後:」を添えた前 → 後の値 */
    function changeView(text) {
        if (text.after === null)
            return null;
        if (text.before === null) {
            return MindmapPreview.h({ tag: "span", attrs: { class: "pe-change" }, children: [MindmapPreview.h({ tag: "ins", children: [valueView(text.after)] })] });
        }
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: "pe-change" },
            children: [
                MindmapPreview.h({ tag: "del", children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["前: "] }), valueView(text.before)] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "pe-arrow", "aria-hidden": "true" }, children: ["→"] }),
                MindmapPreview.h({ tag: "ins", children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["後: "] }), valueView(text.after)] }),
            ],
        });
    }
    /** 保存待ちのパネル（開閉は使う側が `open` のクラスで決める） */
    function pendingEditsPanel({ edits, blocked, index, status, rejected = null, on }) {
        const removals = edits.filter((edit) => edit.op === "item-remove").length;
        const saving = status === "saving";
        const blockedBy = new Map(blocked.map((entry) => [entry.id, entry]));
        const blockedEdits = edits.filter((edit) => blockedBy.has(edit.id));
        /** 書き込めない編集の行の名前（「{ID か種類} の{何を}」） */
        const nameOf = (edit) => {
            const who = describeTarget({
                target: edit.target,
                edits: edits.filter((other) => other.target === edit.target),
                index,
            });
            return `${who.id ?? who.kind} の${editRowText(edit).what}`;
        };
        const list = MindmapPreview.h({ tag: "div", attrs: { class: "comments-body pe-list" } });
        if (blockedEdits.length > 0) {
            list.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
                children: [
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-title" },
                        children: [MindmapPreview.icon("alert"), `${blockedEdits.length} 件の編集を書き込めないため、何も保存していません。`],
                    }),
                    MindmapPreview.h({
                        tag: "ul",
                        children: blockedEdits.map((edit) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                MindmapPreview.h({
                                    tag: "a",
                                    attrs: {
                                        href: `#pe-row-${edit.id}`,
                                        onclick: (event) => {
                                            event.preventDefault();
                                            document.getElementById(`pe-row-${edit.id}`)?.querySelector("button")?.focus();
                                        },
                                    },
                                    children: [nameOf(edit)],
                                }),
                            ],
                        })),
                    }),
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-next" },
                        children: ["書き込めない編集を取り消してから、もう一度保存してください。"],
                    }),
                ],
            }));
        }
        if (rejected !== null) {
            list.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
                children: [
                    MindmapPreview.h({ tag: "p", attrs: { class: "pe-alert-title" }, children: [MindmapPreview.icon("alert"), `保存できませんでした。${rejected}`] }),
                ],
            }));
        }
        if (status === "offline") {
            list.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-alert", role: "alert", tabindex: "-1", "data-focus": "alert" },
                children: [
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-title" },
                        children: [MindmapPreview.icon("alert"), "サーバーにつながらないため、保存できませんでした。"],
                    }),
                    MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-alert-next" },
                        children: ["保存待ちの編集は残っています。サーバーを立ち上げ直してから、もう一度保存してください。"],
                    }),
                ],
            }));
        }
        if (edits.length === 0)
            list.append(MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("layers"), "保存待ちの編集はありません。"] }));
        for (const group of groupEdits(edits)) {
            const who = describeTarget({ target: group.target, edits: group.edits, index });
            const isBlocked = group.edits.some((edit) => blockedBy.has(edit.id));
            list.append(MindmapPreview.h({
                tag: "section",
                attrs: { class: `pe-group${isBlocked ? " is-blocked" : ""}` },
                children: [
                    MindmapPreview.h({
                        tag: "h3",
                        attrs: { class: "pe-group-head" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "pe-open",
                                    type: "button",
                                    "aria-label": `${who.id ?? who.kind}「${who.title}」を開く`,
                                    onclick: () => on.open(group.target),
                                },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "pe-kind" }, children: [who.kind] }),
                                    who.id === null ? null : MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [who.id] }),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "pe-title" }, children: [who.title] }),
                                ],
                            }),
                        ],
                    }),
                    MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "pe-rows" },
                        children: group.edits.map((edit) => editRow({ edit, who, blockedEdit: blockedBy.get(edit.id), index, on })),
                    }),
                ],
            }));
        }
        const label = saving ? "保存しています…" : removals > 0 ? `まとめて保存する（${removals} 件を削除）` : "まとめて保存する";
        return MindmapPreview.h({
            tag: "aside",
            attrs: { class: "pending-panel", "aria-label": "保存待ちの編集", id: "pending-panel" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-head" },
                    children: [
                        MindmapPreview.h({
                            tag: "h2",
                            attrs: { tabindex: "-1" },
                            children: ["保存待ち", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [`${edits.length} 件`] })],
                        }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn",
                                type: "button",
                                "aria-label": "保存待ちの編集を閉じる",
                                "data-focus": "close",
                                onclick: () => on.close(),
                            },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                list,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-free pe-foot" },
                    children: [
                        edits.length === 0
                            ? null
                            : MindmapPreview.h({
                                tag: "p",
                                attrs: { class: "pe-foot-sum" },
                                children: [`${edits.length} 件${removals > 0 ? `（うち削除 ${removals} 件）` : ""}をワークスペースに書きます`],
                            }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "btn primary pe-save",
                                type: "button",
                                disabled: saving || edits.length === 0,
                                "aria-busy": saving ? "true" : null,
                                onclick: () => on.save(),
                            },
                            children: [saving ? MindmapPreview.h({ tag: "span", attrs: { class: "pe-spin" }, children: [MindmapPreview.icon("spin")] }) : MindmapPreview.icon("save"), label],
                        }),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.pendingEditsPanel = pendingEditsPanel;
    /** 編集の行（何を・前 → 後・書き込めない理由と、取り消すボタン） */
    function editRow({ edit, who, blockedEdit, index, on, }) {
        const text = editRowText(edit);
        const name = `${who.id ?? who.kind} の${text.what}`;
        return MindmapPreview.h({
            tag: "li",
            attrs: {
                class: `pe-row${blockedEdit === undefined ? "" : " is-blocked"}${edit.op === "item-remove" ? " is-remove" : ""}`,
                id: `pe-row-${edit.id}`,
            },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "pe-row-main" },
                    children: [
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "pe-what" },
                            children: [edit.op === "item-remove" ? MindmapPreview.icon("trash") : null, text.what],
                        }),
                        changeView(text),
                        blockedEdit === undefined
                            ? null
                            : MindmapPreview.blockedNote({
                                blocked: blockedEdit,
                                updated: index.byId.get(edit.target)?.item.updated ?? null,
                                onOpen: on.open,
                            }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "btn ghost pe-undo",
                        type: "button",
                        "data-focus": `undo:${edit.id}`,
                        "aria-label": `${name}の編集を取り消す`,
                        onclick: () => on.undo(edit.id),
                    },
                    children: [MindmapPreview.icon("undo"), MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: ["取り消す"] })],
                }),
            ],
        });
    }
    /** まとめて保存できたときに画面の下に出す知らせ（`role="status"`）。消すのは使う側 */
    function savedNotice({ count }) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-toast", role: "status" },
            children: [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`${count} 件を保存しました。`] })],
        });
    }
    MindmapPreview.savedNotice = savedNotice;
})(MindmapPreview || (MindmapPreview = {}));
// 設定の画面。ワークスペースの設定を、キーごとの入力で書き換える別の画面。
var MindmapPreview;
(function (MindmapPreview) {
    /** 1 行ずつの表で書き換える設定のキーと、列 */
    const TABLES = {
        targets: {
            label: "対象",
            columns: [
                { key: "name", title: "名前", type: "text" },
                { key: "summary", title: "説明", type: "text" },
            ],
        },
        categories: {
            label: "カテゴリー",
            columns: [
                { key: "name", title: "名前", type: "text" },
                { key: "target", title: "対象", type: "text" },
                { key: "summary", title: "説明", type: "text" },
            ],
        },
        links: {
            label: "関連する場所",
            columns: [
                { key: "title", title: "表示名", type: "text" },
                { key: "url", title: "URL", type: "url" },
            ],
        },
    };
    /** 設定のまとまり（見出しとキー） */
    const GROUPS = [
        { title: "話し合い", keys: ["summary", "description", "playbooks", "goal"] },
        { title: "進め方", keys: ["phases", "target_label", "targets", "categories"] },
        { title: "関連", keys: ["links"] },
        { title: "変更履歴", keys: ["history_limit"] },
    ];
    /** 設定のキーの入力欄の名前 */
    const SETTING_NAMES = {
        summary: "題名",
        description: "説明",
        playbooks: "プレイブック",
        goal: "ゴール",
        phases: "フェーズ",
        target_label: "最上位の軸の呼び名",
        targets: "対象",
        categories: "カテゴリー",
        links: "関連する場所",
        history_limit: "保持する回数",
    };
    /** フェーズ・対象・カテゴリーの 1 つの値を持つ項目の件数 */
    function usageCount({ index, key, value, }) {
        let count = 0;
        for (const { item } of index.byId.values()) {
            if (key === "phases" && item.phase === value)
                count += 1;
            if (key === "targets" && item.target === value)
                count += 1;
            if (key === "categories" && item.category === value)
                count += 1;
        }
        if (key === "targets")
            count += index.data.settings.categories.filter((category) => category.target === value).length;
        return count;
    }
    MindmapPreview.usageCount = usageCount;
    /** 設定の画面（見出しの帯と、まとまりごとの入力）を返す */
    function workspaceSettings(props) {
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "pe-form pe-ws-form",
                novalidate: true,
                "aria-label": "ワークスペースの設定",
                onsubmit: (event) => event.preventDefault(),
            },
            children: GROUPS.map((group) => MindmapPreview.h({
                tag: "fieldset",
                attrs: { class: "pe-ws-group" },
                children: [MindmapPreview.h({ tag: "legend", children: [group.title] }), ...group.keys.map((key) => settingField({ props, key }))],
            })),
        });
        form.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-form-msg", role: "status" } }));
        return MindmapPreview.h({
            tag: "main",
            attrs: { class: "content pe-ws pe-screen" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "pe-screen-head" },
                    children: [
                        MindmapPreview.h({ tag: "h1", attrs: { tabindex: "-1" }, children: ["設定"] }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn", type: "button", onclick: () => props.on.close() },
                            children: [MindmapPreview.icon("x"), "閉じる"],
                        }),
                    ],
                }),
                form,
            ],
        });
    }
    MindmapPreview.workspaceSettings = workspaceSettings;
    /** 設定のキー 1 つの入力欄（名前の行・入力・誤り） */
    function settingField({ props, key }) {
        const { settings, marks, errors, on } = props;
        const name = SETTING_NAMES[key] ?? key;
        const controlId = `pe-ws-${key}`;
        const mark = marks[key];
        const wrap = MindmapPreview.h({
            tag: "div",
            attrs: {
                class: `pe-field${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}`,
                "data-key": key,
            },
        });
        const record = settings;
        const value = record[key];
        wrap.append(MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-label-row" },
            children: [
                key === "goal" || key in TABLES || key === "playbooks" || key === "phases"
                    ? MindmapPreview.h({ tag: "span", attrs: { class: "pe-label", id: `${controlId}-label` }, children: [name] })
                    : MindmapPreview.h({ tag: "label", attrs: { for: controlId, id: `${controlId}-label` }, children: [name] }),
                mark === undefined ? null : MindmapPreview.pendingEditMark({ kind: mark, compact: true }),
            ],
        }));
        /** 設定のキーを溜める */
        const commit = (next, map) => on.change(map === undefined ? { key, value: next } : { key, value: next, map });
        if (key === "summary" || key === "target_label") {
            const input = MindmapPreview.h({
                tag: "input",
                attrs: { id: controlId, class: "input", type: "text", value: typeof value === "string" ? value : "", autocomplete: "off" },
            });
            input.addEventListener("change", () => commit(input.value));
            wrap.append(input);
        }
        else if (key === "description") {
            const area = MindmapPreview.h({ tag: "textarea", attrs: { id: controlId, class: "input pe-text", rows: 2 } });
            area.value = typeof value === "string" ? value : "";
            // 空にして離れたら、説明を消す
            area.addEventListener("change", () => commit(area.value === "" ? null : area.value));
            wrap.append(area);
        }
        else if (key === "history_limit") {
            const input = MindmapPreview.h({
                tag: "input",
                attrs: {
                    id: controlId,
                    class: "input pe-num",
                    type: "number",
                    min: 1,
                    step: 1,
                    inputmode: "numeric",
                    value: typeof value === "number" ? value : "",
                },
            });
            input.addEventListener("change", () => {
                const next = Number(input.value);
                if (input.value.trim() === "" || !Number.isInteger(next) || next < 1)
                    return;
                commit(next);
            });
            wrap.append(input, MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint" }, children: ["変更履歴に残す書き換えのまとまりの数"] }));
        }
        else if (key === "playbooks" || key === "phases") {
            const names = Array.isArray(value) ? value : [];
            wrap.append(chipsSetting({ props, key, wrap, controlId, name, values: names, commit }));
        }
        else if (key === "goal") {
            wrap.append(...goalInputs({ props, controlId, commit }));
        }
        else if (key in TABLES) {
            wrap.append(...tableInputs({ props, key: key, controlId, commit }));
        }
        const failure = errors[key];
        if (failure !== undefined) {
            wrap.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [MindmapPreview.icon("alert"), failure] }));
        }
        return wrap;
    }
    /** 使われている値を外したときの付け替え先の選択（選ぶまで溜めない） */
    function moveSelect({ key, removed, count, next, done, }) {
        const remaining = (Array.isArray(next) ? next : []).map((entry) => typeof entry === "string" ? entry : String(entry.name));
        const id = `pe-ws-${key}-move-${MindmapPreview.safeId(removed)}`;
        const select = MindmapPreview.h({
            tag: "select",
            attrs: { id, class: "input" },
            children: [
                MindmapPreview.h({ tag: "option", attrs: { value: "", selected: true }, children: ["選んでください"] }),
                ...remaining.map((entry) => MindmapPreview.h({ tag: "option", attrs: { value: entry }, children: [entry] })),
            ],
        });
        select.addEventListener("change", () => {
            if (select.value === "")
                return;
            done(select.value);
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-sub pe-move", "data-moving": removed },
            children: [
                MindmapPreview.h({ tag: "label", attrs: { class: "pe-sub-label", for: id }, children: [`${removed} を使っている ${count} 件の付け替え先`] }),
                select,
                MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint" }, children: [MindmapPreview.icon("alert"), "付け替え先を選ぶと保存待ちに入ります。"] }),
            ],
        });
    }
    /** プレイブック・フェーズ（チップ）。使われているフェーズを外したときは付け替え先を選ばせる */
    function chipsSetting({ props, key, wrap, controlId, name, values, commit, }) {
        const box = MindmapPreview.h({ tag: "div", attrs: { class: "pe-chips-set" } });
        box.append(MindmapPreview.chipsInput({
            controlId,
            name,
            hint: `${name}を入れる`,
            values,
            suggestions: null,
            monospace: false,
            disabled: false,
            onChange: (names, removed) => {
                const used = removed !== null && key !== "playbooks"
                    ? usageCount({ index: props.index, key, value: removed })
                    : 0;
                if (removed === null || used === 0) {
                    commit(names);
                    return;
                }
                // 使われている値を外した: 付け替え先を選んだときに、対応つきで溜める
                wrap.querySelector(`[data-moving="${removed}"]`)?.remove();
                wrap.append(moveSelect({
                    key: key,
                    removed,
                    count: used,
                    next: names,
                    done: (target) => commit(names, { [removed]: target }),
                }));
            },
        }));
        return box;
    }
    /** ゴール（届けるフェーズ・ゴールの中身を書き換え、納品物は読むだけで並べる） */
    function goalInputs({ props, controlId, commit, }) {
        const { settings } = props;
        const goal = settings.goal ?? { phase: settings.phases[0] ?? "", summary: "", deliverables: [] };
        const phase = MindmapPreview.h({
            tag: "select",
            attrs: { id: `${controlId}-phase`, class: "input" },
            children: settings.phases.map((entry) => MindmapPreview.h({ tag: "option", attrs: { value: entry, selected: entry === goal.phase }, children: [entry] })),
        });
        const summary = MindmapPreview.h({ tag: "textarea", attrs: { id: `${controlId}-summary`, class: "input pe-text", rows: 2 } });
        summary.value = goal.summary;
        const change = () => commit({ ...goal, phase: phase.value, summary: summary.value });
        phase.addEventListener("change", change);
        summary.addEventListener("change", change);
        return [
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-sub" },
                children: [MindmapPreview.h({ tag: "label", attrs: { class: "pe-sub-label", for: `${controlId}-phase` }, children: ["届けるフェーズ"] }), phase],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-sub" },
                children: [MindmapPreview.h({ tag: "label", attrs: { class: "pe-sub-label", for: `${controlId}-summary` }, children: ["ゴールの中身"] }), summary],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-sub" },
                children: [
                    MindmapPreview.h({ tag: "span", attrs: { class: "pe-sub-label" }, children: ["納品物"] }),
                    MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "pe-rowsx" },
                        children: goal.deliverables.map((entry) => MindmapPreview.h({
                            tag: "li",
                            children: [entry.doc === undefined ? null : MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [entry.doc] }), entry.doc === undefined ? null : " ", entry.title],
                        })),
                    }),
                ],
            }),
        ];
    }
    /** 対象・カテゴリー・関連する場所（1 行ずつの表）。行の名前を書き換えたら古い名前 → 新しい名前の対応を付け、使われている行を消したら付け替え先を選ばせる */
    function tableInputs({ props, key, controlId, commit, }) {
        const { label, columns } = TABLES[key];
        const rows = (props.settings[key] ?? []);
        const wrap = MindmapPreview.h({ tag: "div", attrs: { class: "pe-mini-wrap" } });
        const holder = MindmapPreview.h({ tag: "div", attrs: { class: "pe-moves" } });
        const body = MindmapPreview.h({ tag: "tbody" });
        rows.forEach((row, at) => {
            const cells = columns.map((column) => {
                const input = MindmapPreview.h({
                    tag: "input",
                    attrs: {
                        id: `${controlId}-${at}-${column.key}`,
                        class: "input",
                        type: column.type,
                        value: row[column.key] ?? "",
                        "aria-label": `${at + 1} 行目の${column.title}`,
                    },
                });
                input.addEventListener("change", () => {
                    const next = rows.map((entry, position) => (position === at ? { ...entry, [column.key]: input.value } : entry));
                    // 対象・カテゴリーの名前を書き換えた: 古い名前 → 新しい名前の対応を付ける
                    const renamed = column.key === "name" && (key === "targets" || key === "categories") && row["name"] !== input.value;
                    commit(next, renamed ? { [row["name"] ?? ""]: input.value } : undefined);
                });
                return MindmapPreview.h({ tag: "td", children: [input] });
            });
            const remove = MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "icon-btn",
                    type: "button",
                    "aria-label": `${at + 1} 行目を削除`,
                    onclick: () => {
                        const next = rows.filter((_, position) => position !== at);
                        const used = key === "links"
                            ? 0
                            : usageCount({ index: props.index, key, value: row["name"] ?? "" });
                        if (used === 0) {
                            commit(next);
                            return;
                        }
                        // 使われている行を消した: 付け替え先を選んだときに、対応つきで溜める
                        const removed = row["name"] ?? "";
                        holder.querySelector(`[data-moving="${removed}"]`)?.remove();
                        holder.append(moveSelect({
                            key: key,
                            removed,
                            count: used,
                            next,
                            done: (target) => commit(next, { [removed]: target }),
                        }));
                    },
                },
                children: [MindmapPreview.icon("trash")],
            });
            body.append(MindmapPreview.h({ tag: "tr", children: [...cells, MindmapPreview.h({ tag: "td", children: [remove] })] }));
        });
        wrap.append(MindmapPreview.h({
            tag: "table",
            attrs: { class: "pe-mini", "aria-labelledby": `${controlId}-label` },
            children: [
                MindmapPreview.h({
                    tag: "thead",
                    children: [
                        MindmapPreview.h({
                            tag: "tr",
                            children: [
                                ...columns.map((column) => MindmapPreview.h({ tag: "th", attrs: { scope: "col" }, children: [column.title] })),
                                MindmapPreview.h({ tag: "th", children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["操作"] })] }),
                            ],
                        }),
                    ],
                }),
                body,
            ],
        }));
        return [
            wrap,
            holder,
            MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "btn pe-row-add",
                    type: "button",
                    onclick: () => commit([...rows, Object.fromEntries(columns.map((column) => [column.key, ""]))]),
                },
                children: [MindmapPreview.icon("plus"), `${label}を追加`],
            }),
        ];
    }
})(MindmapPreview || (MindmapPreview = {}));
// 表示の設定。見ている画面に重ねて左から出すパネルに表示の設定の中身を入れ、既定が変わったときは画面の下に知らせを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 既定が変わった知らせの文言 */
    const NOTICE_TEXT = "ワークスペースの既定が変わりました。";
    /** 出している知らせと、消すタイマー（続けて呼ばれたら前のものを消して出し直す） */
    let currentNotice = null;
    /** 表示の設定のパネル（見出しの帯と ×、中身）を返す。開閉は使う側が `open` のクラスで決める */
    function settingsDrawer({ panel }) {
        return MindmapPreview.h({
            tag: "aside",
            attrs: { class: "settings-drawer", id: "sdrawer", "aria-label": "表示の設定" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-head" },
                    children: [
                        MindmapPreview.h({ tag: "h2", children: ["表示の設定"] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn",
                                type: "button",
                                "aria-label": "表示の設定を閉じる",
                                "data-focus": "close",
                                onclick: () => panel.on.close(),
                            },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                MindmapPreview.settingsPanel(panel),
            ],
        });
    }
    MindmapPreview.settingsDrawer = settingsDrawer;
    /** 画面の下に「ワークスペースの既定が変わりました。」を `role="status"` で出し、`durationMs` 経ったら消す */
    function settingsNotice({ durationMs }) {
        // 続けて呼ばれた: 前の知らせを消して出し直す
        if (currentNotice !== null) {
            window.clearTimeout(currentNotice.timer);
            currentNotice.element.remove();
        }
        const element = MindmapPreview.h({
            tag: "div",
            attrs: { class: "stoast", role: "status" },
            children: [MindmapPreview.icon("sliders"), MindmapPreview.h({ tag: "span", children: [NOTICE_TEXT] })],
        });
        document.body.append(element);
        // 次のコマで出し、すべり込ませる
        requestAnimationFrame(() => element.classList.add("show"));
        const timer = window.setTimeout(() => {
            element.remove();
            if (currentNotice?.element === element)
                currentNotice = null;
        }, durationMs);
        currentNotice = { element, timer };
        return element;
    }
    MindmapPreview.settingsNotice = settingsNotice;
})(MindmapPreview || (MindmapPreview = {}));
// 全体の検索。ID・タイトル・本文で、全種類の項目を探すモーダル。
var MindmapPreview;
(function (MindmapPreview) {
    /** 段ごとの見出し */
    const TIER_LABEL = { 1: "完全に一致", 2: "タイトルに一致", 3: "ほかの所に一致" };
    /** 結果 1 件に添える、項目の要約 */
    function summaryOf(item) {
        return item.answer ?? item.conclusion ?? item.meaning ?? item.content ?? item.lead ?? "";
    }
    /** 全体の検索のモーダルを返す。文書に入れた後、`showModal()` で開く */
    function searchDialog({ index, on }) {
        const input = MindmapPreview.h({
            tag: "input",
            attrs: {
                type: "text",
                placeholder: "ID・タイトル・本文で検索",
                autocomplete: "off",
                "aria-label": "検索キーワード",
            },
        });
        const results = MindmapPreview.h({ tag: "div", attrs: { class: "search-results" } });
        const dialog = MindmapPreview.h({
            tag: "dialog",
            attrs: { class: "search", closedby: "any", "aria-label": "すべての項目を検索" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "search-head" },
                    children: [
                        MindmapPreview.icon("search"),
                        input,
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "検索を閉じる", onclick: () => dialog.close() },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                results,
            ],
        });
        /** 結果のボタン */
        const buttons = () => [...results.querySelectorAll(".sr-item")];
        /** 検索の言葉で結果を描き直す */
        const render = () => {
            const query = input.value.trim();
            if (query === "") {
                results.replaceChildren(MindmapPreview.emptyNote("ID・タイトル・本文で、すべての項目を検索します。"));
                return;
            }
            const hits = MindmapPreview.searchItems({ query, index });
            if (hits.length === 0) {
                results.replaceChildren(MindmapPreview.h({ tag: "p", attrs: { class: "no-match" }, children: ["該当する項目はありません。別の条件を試してください。"] }));
                return;
            }
            /** 結果 1 件のボタン。種類の札を添える */
            const resultButton = (hit) => {
                const item = index.byId.get(hit.id)?.item;
                return MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "sr-item", type: "button", "data-id": hit.id, onclick: () => on.open(hit.id) },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [hit.id] }),
                        MindmapPreview.h({
                            tag: "span",
                            children: [
                                MindmapPreview.statusMark(item?.status),
                                ` ${hit.title}`,
                                MindmapPreview.h({ tag: "span", attrs: { class: "sr-kind" }, children: [MindmapPreview.KIND_LABEL[hit.kind]] }),
                                MindmapPreview.h({ tag: "br" }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "sr-sub" }, children: [item === undefined ? "" : summaryOf(item)] }),
                            ],
                        }),
                    ],
                });
            };
            // 段ごとの見出しの下に並べる（当たった項目の無い段の見出しは出さない）
            const tiers = [1, 2, 3].flatMap((tier) => {
                const ofTier = hits.filter((hit) => hit.tier === tier);
                return ofTier.length === 0
                    ? []
                    : [MindmapPreview.h({ tag: "h2", attrs: { class: "sr-tier" }, children: [TIER_LABEL[tier]] }), ...ofTier.map(resultButton)];
            });
            results.replaceChildren(...tiers);
        };
        input.addEventListener("input", render);
        // Enter で先頭の結果を開き、↓ で結果へ移る。結果の中は ↑ ↓ で選ぶ
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter")
                buttons()[0]?.click();
            if (event.key === "ArrowDown") {
                event.preventDefault();
                buttons()[0]?.focus();
            }
        });
        results.addEventListener("keydown", (event) => {
            const list = buttons();
            const position = list.indexOf(document.activeElement);
            if (event.key === "ArrowDown") {
                event.preventDefault();
                list[Math.min(list.length - 1, position + 1)]?.focus();
            }
            else if (event.key === "ArrowUp") {
                event.preventDefault();
                if (position <= 0)
                    input.focus();
                else
                    list[position - 1]?.focus();
            }
        });
        // 閉じたら（Esc・外側の押下・閉じるボタン）、使う側にも知らせる
        dialog.addEventListener("close", on.close);
        dialog.addEventListener("toggle", () => {
            if (dialog.open)
                input.select();
        });
        render();
        return dialog;
    }
    MindmapPreview.searchDialog = searchDialog;
})(MindmapPreview || (MindmapPreview = {}));
// 図の拡大。ホイールで拡大・縮小し、背景のドラッグで動かす。図の文字は選んでコピーできる（文字の上のドラッグは選択に任せる）。差分の表示の間は、色・凡例と消したもの・Raw の行ごとの差分も出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 拡大率の範囲と、ボタン 1 回の倍率 */
    const SCALE_MIN = 0.2;
    const SCALE_MAX = 6;
    const BUTTON_FACTOR = 1.25;
    const WHEEL_FACTOR = 1.12;
    /** 開いたときに図の周りに空ける余白（px） */
    const FIT_MARGIN = 64;
    /** 開いたときの拡大率の上限 */
    const FIT_MAX_SCALE = 3;
    /** Raw で出す記法。差分の表示の間は記法の行ごとの差分（jsdiff を読めないときと打ち切ったときは、今の記法のまま） */
    function rawElement({ source, before }) {
        const raw = MindmapPreview.h({ tag: "pre", attrs: { class: "dg-raw v-raw", hidden: true, tabindex: "0", role: "region", "aria-label": "図の記法" }, children: [source] });
        if (before === null)
            return raw;
        // 語の差分は、行の差分を呼んでからこの時間の内に収める
        const deadline = performance.now() + MindmapPreview.LINE_DIFF_TIMEOUT_MS;
        const parts = MindmapPreview.diffLineParts(before.endsWith("\n") ? before : `${before}\n`, source.endsWith("\n") ? source : `${source}\n`);
        if (parts === null)
            return raw;
        raw.classList.add("df-raw");
        raw.replaceChildren(...MindmapPreview.rawDiffLines({ parts, deadline }));
        return raw;
    }
    /** 図の拡大の中身（道具の行と、図を置く窓）を返す。モーダルか全画面の中に入れて使う */
    function diagramViewer({ svg, on, diff = null }) {
        const stage = MindmapPreview.h({ tag: "div", attrs: { class: "v-stage" } });
        const canvas = MindmapPreview.h({ tag: "div", attrs: { class: "v-canvas" }, children: [stage] });
        const percent = MindmapPreview.h({ tag: "span", attrs: { class: "v-pct mono" }, children: ["100%"] });
        const view = { scale: 1, x: 0, y: 0 };
        /** 位置と拡大率を図に当てる */
        const apply = () => {
            stage.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`;
            percent.textContent = `${Math.round(view.scale * 100)}%`;
        };
        /** 窓の中心を保って拡大率を変える */
        const zoomAt = (factor, originX, originY) => {
            const next = Math.max(SCALE_MIN, Math.min(SCALE_MAX, view.scale * factor));
            view.x = originX - (originX - view.x) * (next / view.scale);
            view.y = originY - (originY - view.y) * (next / view.scale);
            view.scale = next;
            apply();
        };
        const centerZoom = (factor) => {
            const box = canvas.getBoundingClientRect();
            zoomAt(factor, box.width / 2, box.height / 2);
        };
        // 図の写しを置く（文字を選べるよう、写しの大きさは元の viewBox に合わせる）
        const copy = svg.cloneNode(true);
        const viewBox = svg.viewBox.baseVal;
        copy.removeAttribute("style");
        copy.setAttribute("width", String(viewBox.width));
        copy.setAttribute("height", String(viewBox.height));
        stage.append(copy);
        canvas.addEventListener("wheel", (event) => {
            event.preventDefault();
            const box = canvas.getBoundingClientRect();
            zoomAt(event.deltaY < 0 ? WHEEL_FACTOR : 1 / WHEEL_FACTOR, event.clientX - box.left, event.clientY - box.top);
        }, { passive: false });
        // 背景のドラッグで動かす（図の文字・ボタンの上は選択やクリックに任せる）
        let drag = null;
        canvas.addEventListener("pointerdown", (event) => {
            if (event.target.closest("button, text, foreignObject, .nodeLabel, .edgeLabel, .label"))
                return;
            event.preventDefault();
            drag = { x: event.clientX - view.x, y: event.clientY - view.y };
            canvas.classList.add("dragging");
            canvas.setPointerCapture(event.pointerId);
        });
        canvas.addEventListener("pointermove", (event) => {
            if (drag === null)
                return;
            view.x = event.clientX - drag.x;
            view.y = event.clientY - drag.y;
            apply();
        });
        const release = () => {
            drag = null;
            canvas.classList.remove("dragging");
        };
        canvas.addEventListener("pointerup", release);
        canvas.addEventListener("pointercancel", release);
        // Raw: 図の代わりに記法を出す（記法は、図を描いた入れ物が持つ原文）
        const source = svg.closest(`[${MindmapPreview.DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(MindmapPreview.DIAGRAM_SOURCE_ATTR) ?? null;
        const raw = source === null ? null : rawElement({ source, before: diff === null ? null : diff.beforeSource });
        const rawButton = raw === null
            ? null
            : MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "btn ghost",
                    type: "button",
                    "data-act": "viewer-raw",
                    "aria-pressed": "false",
                    onclick: () => {
                        const pressed = rawButton?.getAttribute("aria-pressed") !== "true";
                        rawButton?.setAttribute("aria-pressed", String(pressed));
                        canvas.hidden = pressed;
                        raw.hidden = !pressed;
                    },
                },
                children: ["Raw"],
            });
        // 差分の表示の間: 詳細パネルの図と同じ凡例と「消したもの」を窓の下端に置き、色を付けない種類は窓に枠の色を付ける
        const figure = diff === null ? null : svg.closest("figure.diagram");
        const notes = figure?.querySelector(":scope > .df-notes")?.cloneNode(true);
        notes?.classList.add("v-notes");
        const root = MindmapPreview.h({
            tag: "div",
            attrs: { class: `viewer-body${figure?.classList.contains("df-frame") === true ? " df-frame" : ""}` },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "v-bar" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "縮小", onclick: () => centerZoom(1 / BUTTON_FACTOR) },
                            children: ["−"],
                        }),
                        percent,
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "拡大", onclick: () => centerZoom(BUTTON_FACTOR) },
                            children: ["＋"],
                        }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        rawButton,
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn ghost", type: "button", "data-act": "diagram-close", onclick: on.close },
                            children: [MindmapPreview.icon("back"), MindmapPreview.h({ tag: "span", attrs: { class: "v-back-label" }, children: ["本文へ戻る"] })],
                        }),
                    ],
                }),
                canvas,
                raw,
                notes,
            ],
        });
        // 開いたときは、窓に収まる大きさで中央に置く（窓の大きさが決まってから）
        let placed = false;
        new ResizeObserver(() => {
            if (placed || canvas.clientWidth === 0)
                return;
            placed = true;
            const box = canvas.getBoundingClientRect();
            const size = copy.getBoundingClientRect();
            view.scale = Math.min(FIT_MAX_SCALE, (box.width - FIT_MARGIN) / size.width, (box.height - FIT_MARGIN) / size.height);
            view.x = (box.width - size.width * view.scale) / 2;
            view.y = (box.height - size.height * view.scale) / 2;
            apply();
        }).observe(canvas);
        apply();
        return root;
    }
    MindmapPreview.diagramViewer = diagramViewer;
})(MindmapPreview || (MindmapPreview = {}));
// ネットワークの 5 つの見た目の描き方。毎コマ graph.ts が計算した玉・線を受け取り、見た目ごとに地・線・流れる光・星の順に描く。
// starlight・deep の線は両端の色の中間の単色で 1 本ずつ引き、光の玉と光条は色ごとに一度だけ絵に焼いて置く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 透視の基準の長さ */
    MindmapPreview.FOCAL = 700;
    /** 線の種類 → 見た目（実線・点線・破線・一点鎖線） */
    MindmapPreview.LINK_DASH = {
        depends: [],
        related: [1.5, 3],
        source: [6, 4],
        for: [10, 3, 2, 3],
    };
    const TAU = Math.PI * 2;
    /** 線の上を玉が流れる 1 周の時間（ms） */
    const FLOW_PERIOD = 4200;
    /** 星のまたたきの周期（ms） */
    const TWINKLE_PERIOD = 1900;
    /** 選んだ星から広がる輪の周期（ms） */
    const PULSE_PERIOD = 3600;
    /** 光の玉・光条の絵の一辺（px） */
    const SPRITE = 128;
    /** 光条の絵の筋の太さ（px） */
    const RAY_WIDTH = 3;
    /** 光の玉の絵の、減衰の曲線を近似する段数 */
    const GLOW_STEPS = 12;
    /** 星屑の点の半径の上限（px） */
    const DUST_MAX = 2.6;
    /** 星屑の灯る星の半径の上限（px） */
    const DUST_LIT_MAX = 3.8;
    /** 手前すぎて描かない深さ */
    const NEAR_CLIP = 10;
    /** 見た目ごとの、名前を玉の上へ持ち上げる倍率（星図は星が小さいので少し高く） */
    MindmapPreview.LABEL_LIFT = { constellation: 1.1 };
    // ───── 小さな道具 ─────
    /** 文字列から 0〜1 の決まった値を作る（玉ごとのまたたきの位相に使う） */
    function hashUnit(text) {
        let hash = 2166136261;
        for (const char of text)
            hash = Math.imul(hash ^ (char.codePointAt(0) ?? 0), 16777619);
        return ((hash >>> 0) % 10000) / 10000;
    }
    MindmapPreview.hashUnit = hashUnit;
    /** 種を決めた乱数を返す（空の星の配置を毎回同じにする） */
    function seeded(seed) {
        let a = seed;
        return () => {
            a = (a + 0x6d2b79f5) | 0;
            let t = Math.imul(a ^ (a >>> 15), 1 | a);
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }
    /** `#rrggbb` を `[r, g, b]` にする */
    function rgb(hex) {
        const [r, g, b] = [1, 3, 5].map((start) => Number.parseInt(hex.slice(start, start + 2), 16));
        return [r ?? 0, g ?? 0, b ?? 0];
    }
    /** `#rrggbb` に透明度を付けた色を返す */
    function rgba(hex, alpha) {
        const [r, g, b] = rgb(hex);
        return `rgba(${r},${g},${b},${alpha})`;
    }
    /** `[r, g, b]` を `#rrggbb` にする */
    function toHex(channels) {
        return `#${channels.map((value) => Math.round(value).toString(16).padStart(2, "0")).join("")}`;
    }
    /** 色を白へ寄せる（星の芯の色に使う） */
    function whiten(hex, ratio) {
        return toHex(rgb(hex).map((value) => value + (255 - value) * ratio));
    }
    /** 両端の星の色（`#rrggbb`）の、成分ごとの平均を四捨五入した色を返す */
    function midColor({ from, to }) {
        const a = rgb(from);
        const b = rgb(to);
        return toHex(a.map((value, position) => (value + (b[position] ?? 0)) / 2));
    }
    MindmapPreview.midColor = midColor;
    /** 中心が明るく外へ薄れる光の玉の絵を、色と減衰ごとに一度だけ作って返す */
    const glowCache = new Map();
    function bakeGlow({ color, falloff }) {
        const key = `${color}|${falloff}`;
        const cached = glowCache.get(key);
        if (cached !== undefined)
            return cached;
        const image = document.createElement("canvas");
        image.width = image.height = SPRITE;
        const context = image.getContext("2d");
        const half = SPRITE / 2;
        const gradient = context.createRadialGradient(half, half, 0, half, half, half);
        const [r, g, b] = rgb(color);
        // 減衰の曲線 (1 − t)^falloff を段で近似する
        for (let step = 0; step <= GLOW_STEPS; step += 1) {
            const t = step / GLOW_STEPS;
            gradient.addColorStop(t, `rgba(${r},${g},${b},${(1 - t) ** falloff})`);
        }
        context.fillStyle = gradient;
        context.fillRect(0, 0, SPRITE, SPRITE);
        glowCache.set(key, image);
        return image;
    }
    MindmapPreview.bakeGlow = bakeGlow;
    /** 十字の光の筋の絵を、色ごとに一度だけ作って返す（毎コマはグラデーションを作らず置くだけにする） */
    const rayCache = new Map();
    function bakeRay(color) {
        const cached = rayCache.get(color);
        if (cached !== undefined)
            return cached;
        const image = document.createElement("canvas");
        image.width = image.height = SPRITE;
        const context = image.getContext("2d");
        const half = SPRITE / 2;
        for (const [dx, dy] of [
            [1, 0],
            [0, 1],
        ]) {
            const gradient = context.createLinearGradient(half - dx * half, half - dy * half, half + dx * half, half + dy * half);
            gradient.addColorStop(0, rgba(color, 0));
            gradient.addColorStop(0.5, rgba(color, 1));
            gradient.addColorStop(1, rgba(color, 0));
            context.fillStyle = gradient;
            context.fillRect(dx === 1 ? 0 : half - RAY_WIDTH / 2, dy === 1 ? 0 : half - RAY_WIDTH / 2, dx === 1 ? SPRITE : RAY_WIDTH, dy === 1 ? SPRITE : RAY_WIDTH);
        }
        rayCache.set(color, image);
        return image;
    }
    MindmapPreview.bakeRay = bakeRay;
    /** 焼いた絵を、中心と半径を指定して置く */
    function blit({ context, image, x, y, radius }) {
        context.drawImage(image, x - radius, y - radius, radius * 2, radius * 2);
    }
    /** 2 点を結ぶ線を引く（`dash` は線の種類の見分け） */
    function line({ context, from, to, dash }) {
        context.setLineDash(dash);
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.stroke();
    }
    /** 塗りの円を描く */
    function circle({ context, x, y, radius }) {
        context.beginPath();
        context.arc(x, y, radius, 0, TAU);
        context.fill();
    }
    /** 4 方向へとがった星の形（アストロイド）を塗る */
    function star4({ context, x, y, radius }) {
        context.beginPath();
        context.moveTo(x, y - radius);
        context.quadraticCurveTo(x, y, x + radius, y);
        context.quadraticCurveTo(x, y, x, y + radius);
        context.quadraticCurveTo(x, y, x - radius, y);
        context.quadraticCurveTo(x, y, x, y - radius);
        context.fill();
    }
    /** 明るい星の光条（十字の光の筋）を、焼いた絵を長さに合わせて置いて描く */
    function spikes({ context, x, y, length, color, alpha }) {
        context.globalAlpha = alpha;
        blit({ context, image: bakeRay(color), x, y, radius: length });
    }
    /** 注目している線の上を流れる玉の位置（0〜1）を、1 本に 2 つずつ返す。動きを減らす設定では流さない */
    function flows({ frame, position }) {
        if (frame.reducedMotion)
            return [];
        return [0, 0.5].map((offset) => (frame.now / FLOW_PERIOD + offset + (position % 7) * 0.13) % 1);
    }
    /** 線の位置 t の画面座標を返す */
    function at({ link, t }) {
        return { x: link.from.x + (link.to.x - link.from.x) * t, y: link.from.y + (link.to.y - link.from.y) * t };
    }
    /** 選んだ玉・カーソルを乗せた玉に輪を付ける */
    function ring({ frame, star, gap = 4 }) {
        if (!star.selected && !star.hover)
            return;
        const { context } = frame;
        context.setLineDash([]);
        context.globalAlpha = 0.9;
        context.strokeStyle = frame.colors.ring;
        context.lineWidth = 1.5;
        context.beginPath();
        context.arc(star.x, star.y, star.radius + gap, 0, TAU);
        context.stroke();
    }
    /** 星のまたたき（ゆっくり明るさが揺れる）。動きを減らす設定では揺れの中ほどの明るさで止める */
    function twinkle({ frame, star, amplitude }) {
        if (frame.reducedMotion)
            return 1 - amplitude;
        return 1 - amplitude + amplitude * Math.sin(frame.now / TWINKLE_PERIOD + star.seed * TAU);
    }
    /** 選んだ玉から、ゆっくり広がって消える輪を描く。動きを減らす設定では描かない */
    function pulse({ frame, star, color }) {
        if (frame.reducedMotion)
            return;
        const phase = (frame.now % PULSE_PERIOD) / PULSE_PERIOD;
        const { context } = frame;
        context.setLineDash([]);
        context.globalAlpha = (1 - phase) ** 2 * 0.55;
        context.strokeStyle = color;
        context.lineWidth = 1;
        context.beginPath();
        context.arc(star.x, star.y, star.radius * (1.4 + phase * 5), 0, TAU);
        context.stroke();
    }
    /** 両端の星の色の中間の単色で線を 1 本引く（線ごとのグラデーションは作らない） */
    function midLine({ context, link, alpha }) {
        context.strokeStyle = rgba(midColor({ from: link.fromColor, to: link.toColor }), alpha);
        line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
    }
    /** 玉が見える深さか（手前すぎない） */
    function visible(depth) {
        return depth > NEAR_CLIP;
    }
    /** 球面の一様な向きを返す */
    function randomDirection(random) {
        const u = random() * 2 - 1;
        const theta = random() * TAU;
        const s = Math.sqrt(1 - u * u);
        return { x: s * Math.cos(theta), y: u, z: s * Math.sin(theta) };
    }
    /** 深宇宙の空の素材（星の向き・明るさ・色、天の川の帯、星雲の絵）を、種を決めた乱数で一度だけ作って返す（2 回目からは同じもの） */
    let skyCache = null;
    function deepSky() {
        if (skyCache !== null)
            return skyCache;
        const random = seeded(20261002);
        const tints = ["#ffffff", "#cfe0ff", "#fff1d6", "#ffd9c2", "#d9f2ff"];
        const stars = [];
        // 遠い星: 空全体に散らし、暗い星ほど多くする
        for (let i = 0; i < 900; i += 1) {
            const direction = randomDirection(random);
            stars.push({ ...direction, magnitude: random() ** 3, color: tints[Math.floor(random() * tints.length)] ?? "#ffffff", seed: random(), band: false });
        }
        // 天の川: 傾けた大円のまわりに、緯度方向へ正規分布で寄せて置く
        const tilt = 0.5;
        for (let i = 0; i < 1600; i += 1) {
            const angle = random() * TAU;
            const latitude = (random() + random() + random() - 1.5) * 0.16;
            const x = Math.cos(angle) * Math.cos(latitude);
            const y0 = Math.sin(latitude);
            const z0 = Math.sin(angle) * Math.cos(latitude);
            stars.push({
                x,
                y: y0 * Math.cos(tilt) - z0 * Math.sin(tilt),
                z: y0 * Math.sin(tilt) + z0 * Math.cos(tilt),
                magnitude: random() ** 2.5 * 0.8,
                color: tints[Math.floor(random() * 3)] ?? "#ffffff",
                seed: random(),
                band: true,
            });
        }
        // 星雲: 色のにじみを重ねた絵を 4 枚作り、正四面体の 4 方向に貼る（どちらを向いても 1 枚は見える）
        const palettes = [
            ["#2dd4bf", "#6366f1", "#0ea5e9"],
            ["#a855f7", "#ec4899", "#6366f1"],
            ["#14b8a6", "#22d3ee", "#8b5cf6"],
            ["#6366f1", "#0ea5e9", "#a855f7"],
        ];
        const k3 = 1 / Math.sqrt(3);
        const anchors = [
            { x: k3, y: k3, z: k3 },
            { x: -k3, y: -k3, z: k3 },
            { x: -k3, y: k3, z: -k3 },
            { x: k3, y: -k3, z: -k3 },
        ];
        const nebulae = palettes.map((palette, position) => {
            const image = document.createElement("canvas");
            image.width = image.height = 512;
            const context = image.getContext("2d");
            context.globalCompositeOperation = "lighter";
            // 大小のにじみを 14 個重ねて雲の形にする
            for (let i = 0; i < 14; i += 1) {
                const cx = 256 + (random() - 0.5) * 260;
                const cy = 256 + (random() - 0.5) * 200;
                const radius = 60 + random() * 170;
                const color = palette[i % palette.length] ?? "#ffffff";
                const gradient = context.createRadialGradient(cx, cy, 0, cx, cy, radius);
                gradient.addColorStop(0, rgba(color, 0.22 + random() * 0.14));
                gradient.addColorStop(1, rgba(color, 0));
                context.fillStyle = gradient;
                context.fillRect(0, 0, 512, 512);
            }
            return { image, direction: anchors[position], scale: 1.5 + position * 0.2 };
        });
        skyCache = { stars, nebulae };
        return skyCache;
    }
    MindmapPreview.deepSky = deepSky;
    /** 無限に遠い向きを画面へ写す（回転だけ。手前側に無ければ null） */
    function projectDirection({ frame, direction }) {
        const q = frame.rotate(direction);
        return q.z <= 0.02 ? null : { x: frame.width / 2 + (q.x / q.z) * MindmapPreview.FOCAL, y: frame.height / 2 + (q.y / q.z) * MindmapPreview.FOCAL, z: q.z };
    }
    /** 近くの塵: 群れの周りに浮かび、寄ると視差で動く。単位球の中に 260 個を一度だけ置く */
    let dustCache = null;
    function dustCloud() {
        if (dustCache !== null)
            return dustCache;
        const random = seeded(7);
        dustCache = Array.from({ length: 260 }, () => {
            const direction = randomDirection(random);
            const radius = Math.cbrt(random());
            return { x: direction.x * radius, y: direction.y * radius, z: direction.z * radius };
        });
        return dustCache;
    }
    /** 見た目と、ライト / ダークの組ごとの、名前の文字の色を返す。`deep` の夜は星空になじむ青白、`dust` は無彩色、ほかは `fallback`（`tokens.css` の名前の色） */
    function lookLabelColor({ look, dark, fallback }) {
        if (look === "deep")
            return dark ? "#dfe6ff" : fallback;
        if (look === "dust")
            return dark ? "#c9ced6" : "#2a2f36";
        return fallback;
    }
    MindmapPreview.lookLabelColor = lookLabelColor;
    // ───── 見た目ごとの描き方 ─────
    /** `glow`: 今の円に、やわらかい光のにじみを足す。夜は光を足し合わせて明るく重ねる */
    function drawGlow(frame) {
        const { context, colors, dark } = frame;
        context.lineWidth = 0.6;
        context.strokeStyle = colors.line;
        for (const link of frame.links) {
            context.globalAlpha = (dark ? 0.3 : 0.22) * link.alpha;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
        }
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 1;
            context.strokeStyle = colors.line;
            context.lineWidth = 1;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            if (dark)
                context.globalCompositeOperation = "lighter";
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = Math.sin(Math.PI * t);
                blit({ context, image: bakeGlow({ color: colors.dot, falloff: 1.8 }), x: spot.x, y: spot.y, radius: 7 });
            }
            context.globalCompositeOperation = "source-over";
        }
        for (const star of frame.stars) {
            if (dark)
                context.globalCompositeOperation = "lighter";
            context.globalAlpha = star.alpha * (dark ? 0.4 : 0.22);
            blit({ context, image: bakeGlow({ color: star.color, falloff: 2 }), x: star.x, y: star.y, radius: star.radius * 3.4 });
            context.globalCompositeOperation = "source-over";
            context.globalAlpha = star.alpha;
            context.fillStyle = star.color;
            circle({ context, x: star.x, y: star.y, radius: star.radius });
            if (dark) {
                context.globalAlpha = star.alpha * 0.55;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x, y: star.y, radius: star.radius * 0.35 });
            }
            ring({ frame, star });
        }
    }
    /** `starlight`: 夜は白い芯と色のにじみと光条、昼は 4 方向にとがった星形 */
    function drawStarlight(frame) {
        const { context, colors, dark } = frame;
        context.lineWidth = 0.7;
        if (dark)
            context.globalCompositeOperation = "lighter";
        for (const link of frame.links) {
            if (dark) {
                midLine({ context, link, alpha: 0.2 * link.alpha });
            }
            else {
                context.strokeStyle = colors.line;
                context.globalAlpha = 0.22 * link.alpha;
                line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            }
        }
        context.globalAlpha = 1;
        for (const [position, link] of frame.focusLinks.entries()) {
            context.lineWidth = 1.1;
            if (dark) {
                midLine({ context, link, alpha: 0.75 });
            }
            else {
                context.strokeStyle = colors.line;
                line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            }
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = Math.sin(Math.PI * t);
                blit({ context, image: bakeGlow({ color: dark ? "#ffffff" : colors.dot, falloff: 2 }), x: spot.x, y: spot.y, radius: dark ? 6 : 4 });
            }
        }
        for (const star of frame.stars) {
            const tw = twinkle({ frame, star, amplitude: 0.18 });
            const big = star.degree >= 4 || star.strong;
            if (dark) {
                context.globalAlpha = star.alpha * 0.28 * tw;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2.2 }), x: star.x, y: star.y, radius: star.radius * 4.6 });
                context.globalAlpha = star.alpha * 0.95;
                blit({ context, image: bakeGlow({ color: whiten(star.color, 0.25), falloff: 1.3 }), x: star.x, y: star.y, radius: star.radius * 1.8 });
                if (big) {
                    spikes({ context, x: star.x, y: star.y, length: star.radius * (2.4 + Math.min(6, star.degree) * 0.45) * tw, color: whiten(star.color, 0.5), alpha: star.alpha * 0.55 });
                }
                context.globalAlpha = star.alpha * tw;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x, y: star.y, radius: star.radius * 0.42 });
            }
            else {
                context.globalAlpha = star.alpha * 0.22;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2 }), x: star.x, y: star.y, radius: star.radius * 2.8 });
                context.globalAlpha = star.alpha;
                context.fillStyle = star.color;
                star4({ context, x: star.x, y: star.y, radius: star.radius * (big ? 1.9 : 1.5) });
            }
            ring({ frame, star, gap: dark ? 5 : 6 });
        }
        context.globalCompositeOperation = "source-over";
    }
    /** `constellation`: 天球の経線・緯線が回転に合わせて回る星図。線は星の手前で切り、選ぶと照準の輪 */
    function drawConstellation(frame) {
        const { context, colors, dark } = frame;
        const sphereRadius = frame.spread * 2.1;
        const grid = dark ? "170,195,255" : "35,55,105";
        // 球の中心までの視点からの距離（奥ほど薄くするのに使う）
        const distance = frame.project({ x: 0, y: 0, z: 0 }).depth;
        // 天球の網: 経線 12 本と緯線 5 本を、奥ほど薄く描く
        context.lineWidth = 0.6;
        /** 球面上の点の列を、奥行きで濃さを変えながらつなぐ */
        const path = ({ points, base }) => {
            for (let i = 1; i < points.length; i += 1) {
                const a = frame.project(points[i - 1]);
                const b = frame.project(points[i]);
                if (!visible(a.depth) || !visible(b.depth))
                    continue;
                const far = Math.max(0.15, Math.min(1, 1.3 - (a.depth + b.depth) / 2 / (distance * 2)));
                context.strokeStyle = `rgba(${grid},${base * far})`;
                line({ context, from: a, to: b, dash: [] });
            }
        };
        const steps = 48;
        for (let meridian = 0; meridian < 12; meridian += 1) {
            const phi = (meridian / 12) * Math.PI;
            const points = [];
            for (let i = 0; i <= steps; i += 1) {
                const theta = (i / steps) * TAU;
                points.push({ x: sphereRadius * Math.cos(theta) * Math.cos(phi), y: sphereRadius * Math.sin(theta), z: sphereRadius * Math.cos(theta) * Math.sin(phi) });
            }
            path({ points, base: dark ? 0.09 : 0.08 });
        }
        for (const latitude of [-60, -30, 0, 30, 60]) {
            const lat = (latitude * Math.PI) / 180;
            const points = [];
            for (let i = 0; i <= steps; i += 1) {
                const phi = (i / steps) * TAU;
                points.push({ x: sphereRadius * Math.cos(lat) * Math.cos(phi), y: sphereRadius * Math.sin(lat), z: sphereRadius * Math.cos(lat) * Math.sin(phi) });
            }
            path({ points, base: latitude === 0 ? (dark ? 0.2 : 0.16) : dark ? 0.09 : 0.08 });
        }
        // 線: 星に触れないよう両端を少し手前で切る
        const ink = dark ? "#c8d4ff" : "#26365e";
        /** 星の半径ぶん両端を詰めた線を引く */
        const gapLine = ({ from, to, fromRadius, toRadius, dash }) => {
            const dx = to.x - from.x;
            const dy = to.y - from.y;
            const length = Math.hypot(dx, dy);
            if (length < fromRadius + toRadius + 4)
                return;
            const ux = dx / length;
            const uy = dy / length;
            context.setLineDash(dash);
            context.beginPath();
            context.moveTo(from.x + ux * (fromRadius + 3), from.y + uy * (fromRadius + 3));
            context.lineTo(to.x - ux * (toRadius + 3), to.y - uy * (toRadius + 3));
            context.stroke();
        };
        /** 玉の半径から、星図の小さく締まった星の半径を求める */
        const starRadius = (point) => (point.radius ?? 0) * 0.55;
        context.strokeStyle = ink;
        context.lineWidth = 0.6;
        for (const link of frame.links) {
            context.globalAlpha = (dark ? 0.32 : 0.3) * link.alpha;
            gapLine({ from: link.from, to: link.to, fromRadius: starRadius(link.from), toRadius: starRadius(link.to), dash: MindmapPreview.LINK_DASH[link.type] });
        }
        const focusStar = frame.stars.find((star) => star.id === frame.focusId);
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 0.9;
            context.lineWidth = 1.1;
            context.strokeStyle = colors.ring;
            gapLine({ from: link.from, to: link.to, fromRadius: (focusStar === undefined ? 4 : starRadius(focusStar)) + 6, toRadius: starRadius(link.to), dash: MindmapPreview.LINK_DASH[link.type] });
            context.setLineDash([]);
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = 0.9 * Math.sin(Math.PI * t);
                context.fillStyle = colors.ring;
                circle({ context, x: spot.x, y: spot.y, radius: 1.4 });
            }
        }
        // 星: 小さく締まった点と、種類の色の細い輪
        context.setLineDash([]);
        if (dark)
            context.globalCompositeOperation = "lighter";
        for (const star of frame.stars) {
            const radius = star.radius * 0.55;
            if (dark) {
                context.globalAlpha = star.alpha * 0.5;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 3 }), x: star.x, y: star.y, radius: star.radius * 2.4 });
            }
            context.globalAlpha = star.alpha;
            context.fillStyle = dark ? whiten(star.color, 0.7) : ink;
            circle({ context, x: star.x, y: star.y, radius });
            context.globalAlpha = star.alpha * 0.7;
            context.strokeStyle = star.color;
            context.lineWidth = 1;
            context.beginPath();
            context.arc(star.x, star.y, radius + 2.5, 0, TAU);
            context.stroke();
        }
        context.globalCompositeOperation = "source-over";
        // 選んだ星の照準: ゆっくり回る 4 本の目盛りと、点線の外輪。動きを減らす設定では回さない
        for (const star of frame.stars) {
            if (!star.selected && !star.hover)
                continue;
            const radius = star.radius * 0.55 + 8;
            const turn = frame.reducedMotion ? 0 : frame.now / 9000;
            context.globalAlpha = 0.95;
            context.strokeStyle = colors.ring;
            context.lineWidth = 1.2;
            context.beginPath();
            context.arc(star.x, star.y, radius, 0, TAU);
            context.stroke();
            for (let i = 0; i < 4; i += 1) {
                const angle = turn + (i * TAU) / 4;
                context.beginPath();
                context.moveTo(star.x + Math.cos(angle) * (radius + 2), star.y + Math.sin(angle) * (radius + 2));
                context.lineTo(star.x + Math.cos(angle) * (radius + 7), star.y + Math.sin(angle) * (radius + 7));
                context.stroke();
            }
            if (star.selected) {
                context.setLineDash([2, 4]);
                context.globalAlpha = 0.6;
                context.beginPath();
                context.arc(star.x, star.y, radius + 13, 0, TAU);
                context.stroke();
                context.setLineDash([]);
            }
        }
    }
    /** `deep`: 回転に合わせて動く星空・天の川・星雲の地に、光のにじむ星。選ぶと彗星が線を流れ、輪が広がる。昼は夜明けの空 */
    function drawDeep(frame) {
        const { context, dark, width, height } = frame;
        const sky = deepSky();
        // 地: 夜は深い紺から黒へ、昼は淡い青から生成りへ
        const ground = dark
            ? context.createRadialGradient(width / 2, height * 0.45, 0, width / 2, height / 2, Math.max(width, height) * 0.75)
            : context.createLinearGradient(0, 0, 0, height);
        if (dark) {
            ground.addColorStop(0, "#0d1428");
            ground.addColorStop(0.6, "#070a16");
            ground.addColorStop(1, "#030409");
        }
        else {
            ground.addColorStop(0, "#e8edf8");
            ground.addColorStop(0.55, "#f3f1f6");
            ground.addColorStop(1, "#f8f4ec");
        }
        context.globalAlpha = 1;
        context.fillStyle = ground;
        context.fillRect(0, 0, width, height);
        // 星雲: 空の向きに貼ってあり、回すと一緒に流れる
        context.globalCompositeOperation = dark ? "lighter" : "source-over";
        for (const nebula of sky.nebulae) {
            const spot = projectDirection({ frame, direction: nebula.direction });
            if (spot === null)
                continue;
            const size = Math.max(width, height) * nebula.scale;
            context.globalAlpha = (dark ? 0.75 : 0.35) * Math.min(1, spot.z * 2.5);
            context.drawImage(nebula.image, spot.x - size / 2, spot.y - size / 2, size, size);
        }
        // 遠い星と天の川（夜だけ）。ゆっくりまたたく
        if (dark) {
            for (const far of sky.stars) {
                const spot = projectDirection({ frame, direction: far });
                if (spot === null || spot.x < -2 || spot.y < -2 || spot.x > width + 2 || spot.y > height + 2)
                    continue;
                const tw = frame.reducedMotion ? 0.75 : 0.75 + 0.25 * Math.sin(frame.now / (1400 + far.seed * 1800) + far.seed * TAU);
                context.globalAlpha = (far.band ? 0.25 + far.magnitude * 0.6 : 0.2 + far.magnitude * 0.8) * tw;
                context.fillStyle = far.color;
                const size = far.band ? 0.5 + far.magnitude * 0.6 : 0.45 + far.magnitude * 1.1;
                context.fillRect(spot.x - size / 2, spot.y - size / 2, size, size);
                if (far.magnitude > 0.75 && !far.band) {
                    context.globalAlpha = 0.35 * tw;
                    blit({ context, image: bakeGlow({ color: far.color, falloff: 2.5 }), x: spot.x, y: spot.y, radius: 5 });
                }
            }
        }
        // 近くの塵: 群れの周りに浮かび、寄ると視差で動く
        const distance = frame.project({ x: 0, y: 0, z: 0 }).depth;
        const reach = frame.spread * 1.8;
        context.fillStyle = dark ? "#b9c8ff" : "#4a5878";
        for (const dust of dustCloud()) {
            const spot = frame.project({ x: dust.x * reach, y: dust.y * reach, z: dust.z * reach });
            if (!visible(spot.depth))
                continue;
            const far = Math.max(0, Math.min(1, 1.3 - spot.depth / (distance * 2)));
            context.globalAlpha = (dark ? 0.35 : 0.18) * far;
            context.fillRect(spot.x, spot.y, 1, 1);
        }
        // 線: 両端の星の色の中間の単色
        context.lineWidth = 0.7;
        context.globalCompositeOperation = dark ? "lighter" : "source-over";
        for (const link of frame.links)
            midLine({ context, link, alpha: 0.3 * link.alpha });
        // 注目している線: 光の帯と、尾を引いて流れる彗星（動きを減らす設定では強調した線だけ）
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 1;
            context.lineWidth = 6;
            midLine({ context, link, alpha: dark ? 0.07 : 0.1 });
            context.lineWidth = 1.2;
            midLine({ context, link, alpha: dark ? 0.8 : 0.7 });
            for (const t of flows({ frame, position })) {
                const fade = Math.sin(Math.PI * t);
                // 尾: 少し前の位置に、だんだん小さく薄い玉を並べる
                for (let i = 7; i >= 1; i -= 1) {
                    const tail = at({ link, t: Math.max(0, t - i * 0.012) });
                    context.globalAlpha = fade * (1 - i / 8) * 0.5;
                    context.fillStyle = dark ? whiten(link.toColor, 0.6) : link.toColor;
                    circle({ context, x: tail.x, y: tail.y, radius: 1.6 * (1 - i / 9) });
                }
                const head = at({ link, t });
                context.globalAlpha = fade;
                blit({ context, image: bakeGlow({ color: dark ? "#ffffff" : link.toColor, falloff: 2 }), x: head.x, y: head.y, radius: dark ? 7 : 5 });
            }
        }
        // 星: 夜は大きなにじみ・色の光・白い芯、昼は光沢のある色の玉
        for (const star of frame.stars) {
            const tw = twinkle({ frame, star, amplitude: 0.12 });
            if (dark) {
                context.globalAlpha = star.alpha * 0.2 * tw;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2.6 }), x: star.x, y: star.y, radius: star.radius * 7.5 });
                context.globalAlpha = star.alpha * 0.8;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 1.4 }), x: star.x, y: star.y, radius: star.radius * 2.3 });
                if (star.strong || star.degree >= 5) {
                    spikes({ context, x: star.x, y: star.y, length: star.radius * (3 + Math.min(6, star.degree) * 0.5) * tw, color: whiten(star.color, 0.6), alpha: star.alpha * 0.5 });
                }
                context.globalAlpha = star.alpha * tw;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x, y: star.y, radius: star.radius * 0.5 });
            }
            else {
                context.globalCompositeOperation = "source-over";
                context.globalAlpha = star.alpha * 0.3;
                blit({ context, image: bakeGlow({ color: star.color, falloff: 2 }), x: star.x, y: star.y, radius: star.radius * 3.2 });
                context.globalAlpha = star.alpha;
                context.fillStyle = star.color;
                circle({ context, x: star.x, y: star.y, radius: star.radius });
                context.globalAlpha = star.alpha * 0.6;
                context.fillStyle = "#ffffff";
                circle({ context, x: star.x - star.radius * 0.3, y: star.y - star.radius * 0.3, radius: star.radius * 0.35 });
            }
        }
        context.globalCompositeOperation = "source-over";
        for (const star of frame.stars) {
            ring({ frame, star, gap: dark ? 6 : 4 });
            if (star.selected)
                pulse({ frame, star, color: dark ? whiten(star.color, 0.4) : star.color });
        }
    }
    /** `dust`: 色を抜いた細かな点と髪の毛ほどの線だけ。注目の起点とつながる星にだけ種類の色を灯す */
    function drawDust(frame) {
        const { context, dark, width, height } = frame;
        const ink = dark ? "#dfe3ea" : "#24282e";
        const ground = context.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, Math.max(width, height) * 0.7);
        if (dark) {
            ground.addColorStop(0, "#101114");
            ground.addColorStop(1, "#060607");
        }
        else {
            ground.addColorStop(0, "#fbfaf7");
            ground.addColorStop(1, "#efeee9");
        }
        context.globalAlpha = 1;
        context.fillStyle = ground;
        context.fillRect(0, 0, width, height);
        context.strokeStyle = ink;
        context.lineWidth = 0.45;
        for (const link of frame.links) {
            context.globalAlpha = 0.16 * link.alpha;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
        }
        for (const [position, link] of frame.focusLinks.entries()) {
            context.globalAlpha = 0.6;
            context.lineWidth = 0.8;
            line({ context, from: link.from, to: link.to, dash: MindmapPreview.LINK_DASH[link.type] });
            for (const t of flows({ frame, position })) {
                const spot = at({ link, t });
                context.globalAlpha = Math.sin(Math.PI * t);
                context.fillStyle = link.toColor;
                circle({ context, x: spot.x, y: spot.y, radius: 1.3 });
            }
        }
        for (const star of frame.stars) {
            const lit = star.strong || star.selected || (frame.focusId !== null && frame.near.has(star.id));
            context.globalAlpha = star.alpha * (lit ? 1 : 0.85);
            context.fillStyle = lit ? star.color : ink;
            // 寄っても細かな点のままにする（灯る星だけ少し大きく）。名前・輪・鍵もこの点の大きさに合わせて置く
            star.radius = Math.max(1, Math.min(star.radius * (lit ? 0.7 : 0.5), lit ? DUST_LIT_MAX : DUST_MAX));
            circle({ context, x: star.x, y: star.y, radius: star.radius });
            ring({ frame, star, gap: 3 });
        }
    }
    /** 1 コマ分の玉と線を、`look` の見た目で地・線・注目の線を流れる光・星の順に描く（名前・状態の印・鍵・コメントの印は描かない） */
    function drawLook({ look, frame }) {
        frame.context.globalCompositeOperation = "source-over";
        switch (look) {
            case "glow":
                drawGlow(frame);
                break;
            case "starlight":
                drawStarlight(frame);
                break;
            case "constellation":
                drawConstellation(frame);
                break;
            case "deep":
                drawDeep(frame);
                break;
            case "dust":
                drawDust(frame);
                break;
        }
        frame.context.globalCompositeOperation = "source-over";
        frame.context.setLineDash([]);
    }
    MindmapPreview.drawLook = drawLook;
})(MindmapPreview || (MindmapPreview = {}));
// ネットワーク。全種類の項目を、関連（依存・関連・根拠・進めるタスク）でつないで 3D で描く。ライブラリを使わず、星をキャンバスへ透視で描く。見た目ごとの描き方は looks.ts、ロックの判定は core/lock.ts が持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** 項目が別の項目を指すキー → 線の種類 */
    const LINK_KEYS = [
        ["depends_on", "depends"],
        ["for", "for"],
        ["sources", "source"],
        ["related", "related"],
    ];
    /** 渡した ID の項目を玉に、関連を線にして返す（両端のどちらかが渡していない項目か記録に無い線は含めない） */
    function buildGraph({ index, shownIds, }) {
        const nodes = [];
        for (const [id, { kind }] of index.byId)
            if (shownIds.has(id))
                nodes.push({ id, kind });
        const shown = new Set(nodes.map((node) => node.id));
        const links = [];
        const seen = new Set();
        for (const { id: source } of nodes) {
            const item = index.byId.get(source)?.item;
            if (item === undefined)
                continue;
            for (const [key, type] of LINK_KEYS) {
                for (const raw of item[key] ?? []) {
                    const target = MindmapPreview.refTarget(raw); // 390: 関連の要素は `to`
                    const identity = `${type}|${source}|${target}`;
                    // 自分自身へ・渡していないか記録に無い項目へ・同じ線の重なりは作らない
                    if (source === target || !shown.has(target) || seen.has(identity))
                        continue;
                    seen.add(identity);
                    links.push({ source, target, type });
                }
            }
        }
        return { nodes, links };
    }
    MindmapPreview.buildGraph = buildGraph;
    /** 状態を持つ種類（検討事項・タスク・資料）の状態を重ねた並び（ネットワークの状態の条件の値の順） */
    const GRAPH_STATUS_ORDER = [
        ...new Set([...MindmapPreview.DECISION_STATUSES, ...MindmapPreview.TASK_STATUSES, ...MindmapPreview.DOC_STATUSES]),
    ];
    /** 絞り込みの条件に合う項目の ID（ネットワークが描く玉。ロックした項目を描いているかの判定にも使う） */
    function shownGraphIds({ index, filters }) {
        const rows = [...index.byId].map(([id, entry]) => ({ id, ...entry }));
        return new Set(MindmapPreview.filterRows({ rows, columns: graphConditions(), filters }).map((row) => row.id));
    }
    MindmapPreview.shownGraphIds = shownGraphIds;
    /** ネットワークで絞る条件（種類・状態・タグ）の定義を返す。値は索引の項目（`{kind, item}`）から取る */
    function graphConditions() {
        // 行は索引の項目に ID を足したもの。列の定義が行の型を `Row` と受けるので、ここで読み替える
        const entry = (row) => row;
        return [
            {
                key: "type",
                label: "種類",
                order: MindmapPreview.KIND_KEYS.map((kind) => MindmapPreview.KIND_LABEL[kind]),
                get: (row) => MindmapPreview.KIND_LABEL[entry(row).kind],
            },
            {
                key: "status",
                label: "状態",
                order: GRAPH_STATUS_ORDER,
                get: (row) => entry(row).item.status,
            },
            { key: "tags", label: "タグ", get: (row) => MindmapPreview.tagNames(entry(row).item.tags) },
        ];
    }
    MindmapPreview.graphConditions = graphConditions;
    /** 項目の種類 → 色のトークン */
    MindmapPreview.KIND_COLOR_VAR = {
        decisions: "--k-dec",
        tasks: "--k-task",
        research: "--k-res",
        docs: "--k-doc",
        terms: "--k-term",
        notes: "--k-note",
        logs: "--k-log",
    };
    /** 文字の書体（太さつき）。倍率は描くときにかけるので、10px で持つ */
    const FONT_NORMAL = '400 10px "JetBrains Mono", "Noto Sans JP", monospace';
    const FONT_BOLD = '500 10px "JetBrains Mono", "Noto Sans JP", monospace';
    /** 玉の上の文字を画像に描くときの、元の大きさに対する倍率 */
    const LABEL_RESOLUTION = 4;
    /** 文字の画像の高さ（10px の文字に対する px） */
    const LABEL_HEIGHT = 14;
    /** 寄せる先: 乗せた玉との距離の 1 割だけ近づいたところ（残す割合） */
    const PULL_KEEP = 0.9;
    /** 毎コマ、目標へ寄せる割合 */
    const PULL_EASE = 0.03;
    /** 操作が止まってから自動で回り始めるまでの時間（ms） */
    const IDLE_BEFORE_ROTATE_MS = 2500;
    /** 自動の回転の速さ（毎コマの角度） */
    const AUTO_ROTATE_STEP = 0.00018;
    /** 色をトークンから引く */
    function readColors() {
        const style = getComputedStyle(document.documentElement);
        const read = (name) => style.getPropertyValue(name).trim();
        return {
            kind: Object.fromEntries(Object.entries(MindmapPreview.KIND_COLOR_VAR).map(([kind, name]) => [kind, read(name)])),
            label: read("--g-label"),
            line: read("--g-line"),
            dot: read("--g-dot"),
            ring: read("--accent"),
        };
    }
    /** 玉を球面上に黄金角の螺旋で散らして置き、線の数から半径を決める */
    function placeBalls(index, graph) {
        const balls = graph.nodes.map((node, position, all) => {
            const t = (position + 0.5) / all.length;
            const phi = Math.acos(1 - 2 * t);
            const theta = Math.PI * (1 + Math.sqrt(5)) * position;
            const title = index.byId.get(node.id)?.item.title ?? node.id;
            const x = 120 * Math.sin(phi) * Math.cos(theta);
            const y = 120 * Math.cos(phi);
            const z = 120 * Math.sin(phi) * Math.sin(theta);
            return {
                ...node,
                x,
                y,
                z,
                title,
                label: title.length > 22 ? `${title.slice(0, 21)}…` : title,
                degree: 0,
                radius: 4,
                home: { x, y, z },
                fade: 1,
                seed: MindmapPreview.hashUnit(node.id),
            };
        });
        const byId = new Map(balls.map((ball) => [ball.id, ball]));
        for (const link of graph.links) {
            const from = byId.get(link.source);
            const to = byId.get(link.target);
            if (from !== undefined)
                from.degree += 1;
            if (to !== undefined)
                to.degree += 1;
        }
        for (const ball of balls)
            ball.radius = 4 + Math.sqrt(ball.degree) * 2.2;
        return balls;
    }
    /** 互いに離れ、線でつながったものは引き合い、中心へ寄る力を、玉が落ち着くまで繰り返して位置を整える */
    function settle(balls, links) {
        // 玉が多いほど繰り返しを減らす（総当たりの計算が増えるため）
        const steps = Math.max(40, Math.min(260, Math.floor(120000 / Math.max(1, balls.length))));
        const velocity = new Map(balls.map((ball) => [ball.id, { x: 0, y: 0, z: 0 }]));
        let alpha = 1;
        for (let step = 0; step < steps; step += 1) {
            for (let i = 0; i < balls.length; i += 1) {
                for (let j = i + 1; j < balls.length; j += 1) {
                    const a = balls[i];
                    const b = balls[j];
                    const dx = a.x - b.x;
                    const dy = a.y - b.y;
                    const dz = a.z - b.z;
                    const force = (4400 / (dx * dx + dy * dy + dz * dz + 1)) * alpha;
                    const va = velocity.get(a.id);
                    const vb = velocity.get(b.id);
                    va.x += dx * force;
                    va.y += dy * force;
                    va.z += dz * force;
                    vb.x -= dx * force;
                    vb.y -= dy * force;
                    vb.z -= dz * force;
                }
            }
            for (const link of links) {
                const want = link.type === "depends" ? 84 : link.type === "related" ? 140 : 110;
                const dx = link.t.x - link.s.x;
                const dy = link.t.y - link.s.y;
                const dz = link.t.z - link.s.z;
                const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
                const pull = ((distance - want) / distance) * 0.03 * alpha;
                const vs = velocity.get(link.s.id);
                const vt = velocity.get(link.t.id);
                vs.x += dx * pull;
                vs.y += dy * pull;
                vs.z += dz * pull;
                vt.x -= dx * pull;
                vt.y -= dy * pull;
                vt.z -= dz * pull;
            }
            for (const ball of balls) {
                const v = velocity.get(ball.id);
                v.x -= ball.x * 0.012 * alpha;
                v.y -= ball.y * 0.012 * alpha;
                v.z -= ball.z * 0.012 * alpha;
                v.x *= 0.9;
                v.y *= 0.9;
                v.z *= 0.9;
                ball.x += v.x * 0.28;
                ball.y += v.y * 0.28;
                ball.z += v.z * 0.28;
            }
            alpha *= 0.994;
        }
        // 整えた位置を、注目が外れたときに戻る位置として覚える
        for (const ball of balls)
            ball.home = { x: ball.x, y: ball.y, z: ball.z };
    }
    /** 画面の外へ出る前に描き続ける余白を足した、画面の中か */
    function onScreen(x, y, width, height, margin) {
        return x > -margin && y > -margin && x < width + margin && y < height + margin;
    }
    /** 名前の横の印を出す、名前の文字の大きさの下限（px。これより小さい名前の玉には出さない） */
    const COMMENT_MARK_MIN_FONT = 8;
    /** 名前の右端と印の間の隙間（px） */
    const COMMENT_MARK_GAP = 4;
    /** 鍵の一辺（px） */
    const KEY_SIZE = 12;
    /** 名前と鍵の間の隙間（px） */
    const KEY_GAP = 3;
    /** 状態の印の大きさ（名前の文字の高さに対する割合） */
    const STATUS_MARK_SCALE = 0.8;
    /** 状態の印と名前の間（名前の文字の高さに対する割合） */
    const STATUS_MARK_GAP = 0.4;
    /** 鍵の線画（24 の枠）: 閉じた鍵と開いた鍵の輪の部分 */
    const LOCK_PATH = new Path2D("M7 11V7a5 5 0 0 1 10 0v4");
    const UNLOCK_PATH = new Path2D("M7 11V7a5 5 0 0 1 9.9-1");
    /** 鍵のマーク（24 の枠の線画）を、中心と一辺を指定してキャンバスに描く。振れは鍵の上端を軸にする */
    function drawKeyIcon({ context, x, y, size, closed, color, alpha, swing, }) {
        context.save();
        context.setLineDash([]);
        context.globalAlpha = alpha;
        context.strokeStyle = color;
        context.lineWidth = 2;
        context.lineCap = "round";
        context.lineJoin = "round";
        context.translate(x, y - size / 2);
        context.rotate(swing);
        context.translate(-size / 2, 0);
        context.scale(size / 24, size / 24);
        context.beginPath();
        context.roundRect(3, 11, 18, 11, 2);
        context.stroke();
        context.stroke(closed ? LOCK_PATH : UNLOCK_PATH);
        context.restore();
    }
    /** 状態の印（一覧と同じ SVG）と資料の成果物の箱を、今の配色で絵にして取っておく（テーマごと） */
    const statusImages = new Map();
    /** 項目の状態の印の絵を返す。読み込み中は null */
    function statusImage({ item, ringColor }) {
        const theme = document.documentElement.dataset["theme"] ?? "";
        const deliverable = item.deliverable === true;
        const cacheKey = `${deliverable ? "deliverable" : (item.status ?? "")}|${theme}`;
        if (!statusImages.has(cacheKey)) {
            const source = deliverable ? MindmapPreview.icon("box") : MindmapPreview.statusMark(item.status);
            if (source === null)
                return null;
            source.setAttribute("xmlns", "http://www.w3.org/2000/svg");
            source.setAttribute("width", "24");
            source.setAttribute("height", "24");
            if (deliverable) {
                source.setAttribute("fill", "none");
                source.setAttribute("stroke", ringColor);
                source.setAttribute("stroke-width", "2.2");
                source.setAttribute("stroke-linecap", "round");
                source.setAttribute("stroke-linejoin", "round");
            }
            else {
                source.setAttribute("viewBox", "-1 -1 12 12");
            }
            // CSS の色の変数は絵の中では効かないので、今の値に置き換える
            const style = getComputedStyle(document.documentElement);
            const text = source.outerHTML.replace(/var\((--[\w-]+)\)/g, (_, name) => style.getPropertyValue(name).trim());
            const image = new Image();
            image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(text)}`;
            statusImages.set(cacheKey, image);
        }
        const image = statusImages.get(cacheKey);
        return image !== undefined && image.complete && image.naturalWidth > 0 ? image : null;
    }
    /** 開いているネットワークの画面（外から玉を選ぶ・色を変える・コメントの件数・見た目・ロックを差し替える・鍵を震わせるために覚える） */
    let live = null;
    /** 詳細パネルで開いた項目を、ネットワークでも選んだ状態にする（画面を開いていなければ何もしない） */
    function selectGraphItem(id) {
        live?.select(id);
    }
    MindmapPreview.selectGraphItem = selectGraphItem;
    /** 描いているネットワークの、名前の横の印に使う件数を差し替える（玉と線と視点は作り直さず、次のコマから新しい件数で印を置く。描いていなければ何もしない） */
    function setGraphComments(counts) {
        live?.setComments(counts);
    }
    MindmapPreview.setGraphComments = setGraphComments;
    /** 描いているネットワークの見た目を差し替える（玉・線・視点・選んだ項目・ロックは作り直さず、次のコマからその見た目で描く。描いていなければ何もしない） */
    function setGraphLook(look) {
        live?.setLook(look);
    }
    MindmapPreview.setGraphLook = setGraphLook;
    /** 描いているネットワークのロックを差し替える（玉・線・視点は作り直さず、中心と強調を新しい注目の起点へ寄せる。描いていなければ何もしない） */
    function setGraphLock(id) {
        live?.setLock(id);
    }
    MindmapPreview.setGraphLock = setGraphLock;
    /** 描いているネットワークの閉じた鍵を震わせる（`L` キーで `shake` になったときに入口が呼ぶ。玉や余白を押したときは画面の中で同じ処理をする） */
    function shakeGraphKey() {
        live?.shake();
    }
    MindmapPreview.shakeGraphKey = shakeGraphKey;
    /** ネットワークの画面を返す。`selectedId` は詳細パネルで開いている項目、`lockedId` は効いているロック（注目の起点にする）、`look` は今当てている見た目、`defaultLook` はワークスペースの既定の見た目 */
    function graphScreen({ index, on, filters, drawerOpen, selectedId, lockedId, look, defaultLook, comments, }) {
        // ===== 絞り込み: 条件に合う項目の ID =====
        const conditions = graphConditions();
        const rows = [...index.byId].map(([id, entry]) => ({ id, ...entry }));
        const shownIds = shownGraphIds({ index, filters });
        // ===== 状態 =====
        const canvas = MindmapPreview.h({
            tag: "canvas",
            attrs: {
                id: "graph-canvas",
                class: "g3-wrap",
                role: "img",
                "aria-label": "すべての項目のネットワーク。L キーで、詳細を開いている項目をロック・解除",
            },
        });
        // 絞り込みの条件に合う項目が 1 件も無いときに、枠の中央に出す文
        const emptyNotice = MindmapPreview.h({ tag: "p", attrs: { class: "empty map-empty", hidden: shownIds.size > 0 }, children: ["表示する項目はありません。"] });
        // 値を選んでいる条件があるときは、キャンバスの上に条件のチップの行を置く
        const chips = MindmapPreview.activeConditionCount(filters) > 0
            ? MindmapPreview.filterChips({
                filters,
                labels: Object.fromEntries(conditions.map((condition) => [condition.key, condition.label])),
                onFilter: on.filter,
            })
            : null;
        // 名前の横のコメントの印を重ねる層（キャンバスと同じ大きさで、押下はキャンバスへ通す）
        const markLayer = MindmapPreview.h({ tag: "div", attrs: { class: "g3-marks" } });
        // 今当てている見た目。キャンバスの右上の、アイコンの無いドロップダウンで選ぶ（ワークスペースの既定の見た目に「（既定）」を添える）
        let lookNow = look;
        const lookSelect = MindmapPreview.h({
            tag: "select",
            attrs: {
                onchange: (event) => {
                    const value = event.target.value;
                    setLook(value);
                    on.look(value);
                },
            },
            children: MindmapPreview.NETWORK_LOOKS.map((option) => MindmapPreview.h({
                tag: "option",
                attrs: { value: option.key, selected: option.key === look },
                children: [option.key === defaultLook ? `${option.label}（既定）` : option.label],
            })),
        });
        const lookPick = MindmapPreview.h({
            tag: "label",
            attrs: { class: "look-pick" },
            children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["ネットワークの見た目"] }), lookSelect],
        });
        const root = MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen graph", "data-look": look },
            children: [
                chips,
                MindmapPreview.h({ tag: "div", attrs: { class: "map-frame space" }, children: [emptyNotice, canvas, comments === undefined ? null : markLayer, lookPick] }),
                MindmapPreview.screenDrawer({
                    drawerOpen,
                    rows,
                    columns: conditions,
                    filters,
                    shown: shownIds.size,
                    onFilter: on.filter,
                    onClose: on.closeDrawer,
                }),
            ],
        });
        const labelCache = new Map();
        let colors = readColors();
        /** 名前の横のコメントの印に使う件数 */
        let commentCounts = comments ?? {};
        /** 玉の ID → 名前の横に置いた印 */
        const markSlots = new Map();
        let balls = [];
        let ballById = new Map();
        let links = [];
        /** 群れのおおよその半径（近い順に 9 割目の玉まで） */
        let reach = 40;
        // 回転は「目標」と「今」を分け、今を目標へ毎コマ少しずつ寄せる（動き出しも止まり際もなめらかにする）
        const camera = {
            yaw: 0.6,
            pitch: -0.25,
            yawTarget: 0.6,
            pitchTarget: -0.25,
            yawSpeed: 0,
            pitchSpeed: 0,
            distance: 520,
            distanceTarget: 520,
            fit: 520,
            center: { x: 0, y: 0, z: 0 },
            centerTarget: { x: 0, y: 0, z: 0 },
        };
        /** ロックの判定をする幅か（幅 900px 以下では詳細が全面に出るので、ロックしない） */
        const wide = matchMedia(MindmapPreview.LOCK_QUERY);
        const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
        /** 効いているロック（絞り込みで描いていなければ null）。画面を作ったときの値から `setGraphLock` で差し替える */
        let locked = lockedId;
        let focus = selectedId;
        let hover = null;
        /** 詳細パネルで開いている項目 */
        let current = selectedId;
        let lastInput = 0;
        let birth = performance.now();
        let projected = new Map();
        let width = 0;
        let height = 0;
        let dpr = 1;
        /** 鍵が震え始めた時刻 */
        let shakeStart = Number.NEGATIVE_INFINITY;
        /** 直前に押した位置と項目（素早い 2 回目を、詳細が開いて枠がずれても同じ玉への 2 回押しとして扱う） */
        let lastPress = null;
        /** 注目の起点: ロックした項目（ロックを判定する幅で、描いている玉のとき）。ロックしていなければ、渡した項目 */
        const anchorOf = (id) => (wide.matches && locked !== null && ballById.has(locked) ? locked : id);
        /** 玉・太さ・色ごとに、文字を 1 回だけ画像に描いて取っておく */
        const labelImage = (ball, bold, color) => {
            const key = `${ball.id}|${bold}|${color}`;
            const cached = labelCache.get(key);
            if (cached !== undefined)
                return cached;
            const font = (bold ? FONT_BOLD : FONT_NORMAL).replace("10px", `${10 * LABEL_RESOLUTION}px`);
            const image = document.createElement("canvas");
            const measure = image.getContext("2d");
            measure.font = font;
            measure.letterSpacing = `${0.8 * LABEL_RESOLUTION}px`;
            image.width = Math.ceil(measure.measureText(ball.label).width) + 4;
            image.height = LABEL_HEIGHT * LABEL_RESOLUTION;
            const context = image.getContext("2d");
            context.font = font;
            context.letterSpacing = `${0.8 * LABEL_RESOLUTION}px`;
            context.fillStyle = color;
            context.textAlign = "center";
            context.textBaseline = "bottom";
            context.fillText(ball.label, image.width / 2, image.height);
            labelCache.set(key, image);
            return image;
        };
        /** 玉の名前の横の印を返す。件数が変わっていれば作り直す（大きさは作ったときに 1 回だけ測る） */
        const markSlotOf = (id, count) => {
            const slot = markSlots.get(id);
            if (slot !== undefined && slot.count === count)
                return slot;
            slot?.element.remove();
            const element = MindmapPreview.commentMark({ count });
            element.classList.add("cmk-float");
            element.style.visibility = "hidden";
            markLayer.append(element);
            const made = { element, count, width: element.offsetWidth, height: element.offsetHeight, visible: false };
            markSlots.set(id, made);
            return made;
        };
        /** 印を見せる・隠す（変わったときだけ触る） */
        const showMark = ({ slot, visible }) => {
            if (slot.visible === visible)
                return;
            slot.visible = visible;
            slot.element.style.visibility = visible ? "" : "hidden";
        };
        /** 玉と線を作る（絞り込みの条件に合う項目で） */
        const rebuild = () => {
            const graph = buildGraph({ index, shownIds });
            balls = placeBalls(index, graph);
            ballById = new Map(balls.map((ball) => [ball.id, ball]));
            links = graph.links.flatMap((link) => {
                const s = ballById.get(link.source);
                const t = ballById.get(link.target);
                return s === undefined || t === undefined ? [] : [{ s, t, type: link.type }];
            });
            settle(balls, links);
            // 全体が枠に収まる距離（外れた玉に引っぱられないよう、近い順に 9 割目の玉までの半径を使う）
            const radii = balls.map((ball) => Math.hypot(ball.x, ball.y, ball.z)).sort((a, b) => a - b);
            reach = Math.max(40, radii[Math.floor(radii.length * 0.9)] ?? 40);
            const box = Math.max(1, Math.min(canvas.clientWidth || 600, canvas.clientHeight || 460));
            camera.fit = ((MindmapPreview.FOCAL * reach) / (box * 0.42) + reach * 0.4) * 0.72;
            camera.distance = camera.distanceTarget = camera.fit;
            camera.center = { x: 0, y: 0, z: 0 };
            camera.centerTarget = { x: 0, y: 0, z: 0 };
            birth = performance.now();
            select(current);
        };
        /** 項目を選ぶ（その玉へゆっくり寄る）。ロック中は、ほかの項目を開いても中心と強調をロックした項目に留める。選ぶのをやめたら、全体を見る位置へ戻す */
        const select = (id) => {
            current = id;
            const anchor = anchorOf(id);
            const ball = anchor === null ? undefined : ballById.get(anchor);
            focus = ball?.id ?? hover;
            camera.distanceTarget = ball === undefined ? camera.fit : camera.fit * 0.38;
            if (ball === undefined)
                camera.centerTarget = { x: 0, y: 0, z: 0 };
        };
        /** 見た目を差し替える（玉・線・視点・選んだ項目・ロックは作り直さない） */
        const setLook = (next) => {
            lookNow = next;
            root.dataset["look"] = next;
            lookSelect.value = next;
            // 名前の色は見た目ごとに変わる
            labelCache.clear();
        };
        // ===== 投影 =====
        /** 玉の位置を画面に透視で投影する */
        const project = (point) => {
            const cx = point.x - camera.center.x;
            const cy = point.y - camera.center.y;
            const cz = point.z - camera.center.z;
            const cosYaw = Math.cos(camera.yaw);
            const sinYaw = Math.sin(camera.yaw);
            const cosPitch = Math.cos(camera.pitch);
            const sinPitch = Math.sin(camera.pitch);
            const x1 = cx * cosYaw - cz * sinYaw;
            const z1 = cx * sinYaw + cz * cosYaw;
            const y1 = cy * cosPitch - z1 * sinPitch;
            const z2 = cy * sinPitch + z1 * cosPitch;
            const f = MindmapPreview.FOCAL / (z2 + camera.distance);
            return { sx: width / 2 + x1 * f, sy: height / 2 + y1 * f, f, z: z2 };
        };
        /** 視点の回転だけをかける（中心を引かない。無限に遠い星の向きに使う） */
        const rotate = (point) => {
            const cosYaw = Math.cos(camera.yaw);
            const sinYaw = Math.sin(camera.yaw);
            const cosPitch = Math.cos(camera.pitch);
            const sinPitch = Math.sin(camera.pitch);
            const x1 = point.x * cosYaw - point.z * sinYaw;
            const z1 = point.x * sinYaw + point.z * cosYaw;
            return { x: x1, y: point.y * cosPitch - z1 * sinPitch, z: point.y * sinPitch + z1 * cosPitch };
        };
        /** 画面のずれを、今の向きで世界の座標のずれに戻す */
        const screenToWorld = (dx, dy) => {
            const cosYaw = Math.cos(camera.yaw);
            const sinYaw = Math.sin(camera.yaw);
            const cosPitch = Math.cos(camera.pitch);
            const sinPitch = Math.sin(camera.pitch);
            const y = dy * cosPitch;
            const z1 = -dy * sinPitch;
            return { x: dx * cosYaw + z1 * sinYaw, y, z: -dx * sinYaw + z1 * cosYaw };
        };
        /** 全体が収まる距離で見たときの倍率（玉と文字の大きさの基準） */
        const baseScale = () => MindmapPreview.FOCAL / camera.fit;
        const radiusOf = (ball, scale) => ball.radius * 1.05 * (scale / baseScale());
        /** 画面の点にある、いちばん手前の玉 */
        const hitTest = (x, y) => {
            let best = null;
            let bestDepth = Number.POSITIVE_INFINITY;
            for (const ball of balls) {
                const p = projected.get(ball.id);
                if (p === undefined || p.z + camera.distance <= 10)
                    continue;
                const reachOf = Math.max(8, radiusOf(ball, p.f)) + 4;
                if (Math.hypot(p.sx - x, p.sy - y) < reachOf && p.z < bestDepth) {
                    best = ball;
                    bestDepth = p.z;
                }
            }
            return best;
        };
        // ===== 操作 =====
        let drag = null;
        let moved = 0;
        canvas.addEventListener("pointerdown", (event) => {
            drag = { x: event.clientX, y: event.clientY, time: performance.now() };
            moved = 0;
            canvas.setPointerCapture(event.pointerId);
            lastInput = performance.now();
            camera.yawSpeed = camera.pitchSpeed = 0;
        });
        canvas.addEventListener("pointermove", (event) => {
            const rect = canvas.getBoundingClientRect();
            if (drag !== null) {
                const dx = event.clientX - drag.x;
                const dy = event.clientY - drag.y;
                const now = performance.now();
                const dt = Math.max(8, now - drag.time);
                moved += Math.abs(dx) + Math.abs(dy);
                camera.yawTarget += dx * 0.0032;
                camera.pitchTarget = Math.max(-1.3, Math.min(1.3, camera.pitchTarget + dy * 0.0032));
                camera.yawSpeed = dx * 0.0032 * (16 / dt);
                camera.pitchSpeed = dy * 0.0032 * (16 / dt);
                drag = { x: event.clientX, y: event.clientY, time: now };
                lastInput = now;
                return;
            }
            const target = hitTest(event.clientX - rect.left, event.clientY - rect.top);
            const id = target?.id ?? null;
            if (id !== hover) {
                hover = id;
                if (anchorOf(current) === null)
                    focus = id;
            }
            canvas.style.cursor = id === null ? "grab" : "pointer";
        });
        canvas.addEventListener("pointerleave", () => {
            if (drag === null && hover !== null) {
                hover = null;
                if (anchorOf(current) === null)
                    focus = null;
            }
        });
        canvas.addEventListener("pointerup", (event) => {
            const rect = canvas.getBoundingClientRect();
            // ほとんど動かさずに離した: 玉か余白を押した
            if (drag !== null && moved < 5) {
                const hit = hitTest(event.clientX - rect.left, event.clientY - rect.top);
                if (!wide.matches) {
                    // 幅 900px 以下ではロックせず、押した玉の項目を開く
                    if (hit !== null) {
                        select(hit.id);
                        on.open(hit.id);
                    }
                }
                else {
                    // 押した玉（余白なら null）で、ロックの付け外し・詳細の切り替え・鍵の震えを決める。素早い 2 回目は前に押した玉への 2 回押しにする
                    const press = { time: performance.now(), x: event.clientX, y: event.clientY, id: hit?.id ?? null };
                    const pressed = MindmapPreview.resolvePress({ last: lastPress, press });
                    lastPress = press;
                    if (on.lock(pressed) === "shake")
                        shakeStart = press.time;
                }
            }
            // 止めてから離したときは滑らせない
            if (drag !== null && performance.now() - drag.time > 80)
                camera.yawSpeed = camera.pitchSpeed = 0;
            drag = null;
        });
        // ホイール: マウスのある位置へ向かって寄る・離れる（距離も中心も目標へなめらかに寄せる）
        canvas.addEventListener("wheel", (event) => {
            event.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const mx = event.clientX - rect.left - width / 2;
            const my = event.clientY - rect.top - height / 2;
            const old = camera.distanceTarget;
            const next = Math.max(camera.fit * 0.15, Math.min(camera.fit * 2.5, old * Math.exp(event.deltaY * 0.0016)));
            if (anchorOf(current) === null) {
                const f = MindmapPreview.FOCAL / old;
                const shift = screenToWorld((mx / f) * (1 - next / old), (my / f) * (1 - next / old));
                camera.centerTarget = {
                    x: camera.centerTarget.x + shift.x,
                    y: camera.centerTarget.y + shift.y,
                    z: camera.centerTarget.z + shift.z,
                };
            }
            camera.distanceTarget = next;
            lastInput = performance.now();
            // 中心は群れの中に収め、全体まで離れたら戻す
            const limit = camera.fit * 0.35;
            const length = Math.hypot(camera.centerTarget.x, camera.centerTarget.y, camera.centerTarget.z);
            if (length > limit) {
                camera.centerTarget = {
                    x: (camera.centerTarget.x * limit) / length,
                    y: (camera.centerTarget.y * limit) / length,
                    z: (camera.centerTarget.z * limit) / length,
                };
            }
            if (next >= camera.fit * 0.95 && anchorOf(current) === null)
                camera.centerTarget = { x: 0, y: 0, z: 0 };
        }, { passive: false });
        // 背景のダブルクリックで、全体を見る位置へ戻す
        canvas.addEventListener("dblclick", () => {
            if (anchorOf(current) !== null)
                return;
            camera.centerTarget = { x: 0, y: 0, z: 0 };
            camera.distanceTarget = camera.fit;
        });
        // ===== 毎コマの描き =====
        const resize = () => {
            dpr = Math.min(2, window.devicePixelRatio || 1);
            width = canvas.clientWidth;
            height = canvas.clientHeight;
            canvas.width = width * dpr;
            canvas.height = height * dpr;
        };
        new ResizeObserver(resize).observe(canvas);
        const context = canvas.getContext("2d");
        /** 注目している玉につながる玉を、注目している玉の近くへゆっくり寄せる。注目が外れると元の位置へ戻す */
        const pullNear = () => {
            const focused = focus === null ? undefined : ballById.get(focus);
            const near = new Set();
            if (focused !== undefined) {
                for (const link of links) {
                    if (link.s.id === focused.id)
                        near.add(link.t.id);
                    if (link.t.id === focused.id)
                        near.add(link.s.id);
                }
            }
            for (const ball of balls) {
                const home = ball.home;
                const pivot = focused?.home;
                const goal = pivot !== undefined && near.has(ball.id)
                    ? {
                        x: pivot.x + (home.x - pivot.x) * PULL_KEEP,
                        y: pivot.y + (home.y - pivot.y) * PULL_KEEP,
                        z: pivot.z + (home.z - pivot.z) * PULL_KEEP,
                    }
                    : home;
                ball.x += (goal.x - ball.x) * PULL_EASE;
                ball.y += (goal.y - ball.y) * PULL_EASE;
                ball.z += (goal.z - ball.z) * PULL_EASE;
            }
        };
        /** 1 コマ分の線（画面に入るものだけ）を、奥行きの濃さと沈み具合つきで `LookLink` にする */
        const buildLinkViews = ({ ease }) => {
            const views = [];
            for (const link of links) {
                const a = projected.get(link.s.id);
                const b = projected.get(link.t.id);
                if (a === undefined || b === undefined)
                    continue;
                if (a.z + camera.distance <= 10 || b.z + camera.distance <= 10)
                    continue;
                if ((a.sx < 0 && b.sx < 0) || (a.sx > width && b.sx > width) || (a.sy < 0 && b.sy < 0) || (a.sy > height && b.sy > height))
                    continue;
                const depth = Math.max(0, Math.min(1, 1.25 - ((a.z + b.z) / 2 + camera.distance) / (camera.distance * 2.2)));
                views.push({
                    from: { x: a.sx, y: a.sy, radius: radiusOf(link.s, a.f) * ease },
                    to: { x: b.sx, y: b.sy, radius: radiusOf(link.t, b.f) * ease },
                    type: link.type,
                    fromColor: colors.kind[link.s.kind],
                    toColor: colors.kind[link.t.kind],
                    alpha: depth * Math.min(link.s.fade, link.t.fade),
                });
            }
            return views;
        };
        /** 注目している項目とつながる線（この上を光が流れる） */
        const buildFocusLinks = ({ focused, ease }) => {
            const views = [];
            const focusedBall = focused === null ? undefined : ballById.get(focused);
            const from = focused === null ? undefined : projected.get(focused);
            if (focusedBall === undefined || from === undefined)
                return views;
            for (const link of links) {
                if (link.s.id !== focusedBall.id && link.t.id !== focusedBall.id)
                    continue;
                const other = link.s.id === focusedBall.id ? link.t : link.s;
                const to = projected.get(other.id);
                if (to === undefined)
                    continue;
                if (from.z + camera.distance <= 10 || to.z + camera.distance <= 10)
                    continue;
                views.push({
                    from: { x: from.sx, y: from.sy, radius: radiusOf(focusedBall, from.f) * ease },
                    to: { x: to.sx, y: to.sy, radius: radiusOf(other, to.f) * ease },
                    type: link.type,
                    fromColor: colors.kind[focusedBall.kind],
                    toColor: colors.kind[other.kind],
                    alpha: 1,
                });
            }
            return views;
        };
        const frame = (now) => {
            // 画面から外れたら止める
            if (!canvas.isConnected) {
                if (live !== null && live.select === select)
                    live = null;
                return;
            }
            requestAnimationFrame(frame);
            if (document.hidden || width === 0)
                return;
            const reduced = reducedMotion.matches;
            pullNear();
            // 離した後の滑りと、何もしていないときのごくゆっくりした自動の回転（動きを減らす設定では回さない）
            if (drag === null) {
                camera.yawTarget += camera.yawSpeed;
                camera.pitchTarget = Math.max(-1.3, Math.min(1.3, camera.pitchTarget + camera.pitchSpeed));
                camera.yawSpeed *= 0.955;
                camera.pitchSpeed *= 0.93;
                if (!reduced && now - lastInput > IDLE_BEFORE_ROTATE_MS && hover === null)
                    camera.yawTarget += AUTO_ROTATE_STEP;
            }
            camera.yaw += (camera.yawTarget - camera.yaw) * 0.07;
            camera.pitch += (camera.pitchTarget - camera.pitch) * 0.07;
            const anchorNow = anchorOf(current);
            const selectedBall = anchorNow === null ? undefined : ballById.get(anchorNow);
            if (selectedBall !== undefined) {
                camera.centerTarget = { x: selectedBall.x, y: selectedBall.y, z: selectedBall.z };
            }
            camera.center.x += (camera.centerTarget.x - camera.center.x) * 0.025;
            camera.center.y += (camera.centerTarget.y - camera.center.y) * 0.025;
            camera.center.z += (camera.centerTarget.z - camera.center.z) * 0.025;
            camera.distance += (camera.distanceTarget - camera.distance) * 0.04;
            // 開いたときは中心から広がる
            const born = Math.min(1, (now - birth) / 1400);
            const ease = 1 - (1 - born) ** 3;
            const focused = focus !== null && ballById.has(focus) ? focus : null;
            const near = new Set(focused === null ? [] : [focused]);
            if (focused !== null) {
                for (const link of links) {
                    if (link.s.id === focused)
                        near.add(link.t.id);
                    if (link.t.id === focused)
                        near.add(link.s.id);
                }
            }
            const baseK = baseScale();
            const dark = document.documentElement.dataset["theme"] === "dark";
            context.setTransform(dpr, 0, 0, dpr, 0, 0);
            context.clearRect(0, 0, width, height);
            projected = new Map(balls.map((ball) => [
                ball.id,
                project({
                    x: ball.x * ease + camera.center.x * (1 - ease),
                    y: ball.y * ease + camera.center.y * (1 - ease),
                    z: ball.z * ease + camera.center.z * (1 - ease),
                }),
            ]));
            // 玉: 奥から順に、大きさ・濃さ・沈み具合を計算して見た目の描き方へ渡す。遠いほど小さく薄く、注目しているときはつながらないものを沈める（詳細を開いている項目は沈めない）
            const order = [...balls].sort((a, b) => (projected.get(b.id)?.z ?? 0) - (projected.get(a.id)?.z ?? 0));
            const views = [];
            for (const [rank, ball] of order.entries()) {
                const p = projected.get(ball.id);
                if (p === undefined || p.z + camera.distance <= 10)
                    continue;
                const r0 = radiusOf(ball, p.f);
                // 画面の外の玉は描かない（光のにじみの分だけ余白を広く取る）
                if (!onScreen(p.sx, p.sy, width, height, r0 * 6 + 40) || r0 > Math.max(width, height))
                    continue;
                const depth = Math.max(0.15, Math.min(1, 1.25 - (p.z + camera.distance) / (camera.distance * 2.2)));
                ball.fade += ((focused !== null && !near.has(ball.id) && ball.id !== current ? 0.18 : 1) - ball.fade) * 0.03;
                // 手前に来すぎた玉は薄くして、奥を隠さないようにする
                const close = Math.min(1, Math.max(0, ((p.z + camera.distance) / camera.distance - 0.08) / 0.2));
                if (close <= 0.02)
                    continue;
                views.push({
                    ball,
                    depth,
                    close,
                    rank,
                    star: {
                        id: ball.id,
                        kind: ball.kind,
                        degree: ball.degree,
                        x: p.sx,
                        y: p.sy,
                        radius: Math.max(1.2, r0 * ease),
                        alpha: (0.35 + 0.55 * depth) * ball.fade * close,
                        color: colors.kind[ball.kind],
                        selected: ball.id === current,
                        hover: ball.id === hover,
                        strong: near.has(ball.id) || ball.id === hover,
                        seed: ball.seed,
                    },
                });
            }
            const lookFrame = {
                context,
                width,
                height,
                dark,
                colors: { line: colors.line, ring: colors.ring, dot: colors.dot },
                now,
                stars: views.map((view) => view.star),
                links: buildLinkViews({ ease }),
                focusLinks: buildFocusLinks({ focused, ease }),
                focusId: focused,
                near,
                rotate,
                project: (point) => {
                    const q = project(point);
                    return { x: q.sx, y: q.sy, depth: q.z + camera.distance, scale: q.f };
                },
                spread: reach,
                reducedMotion: reduced,
            };
            MindmapPreview.drawLook({ look: lookNow, frame: lookFrame });
            context.globalCompositeOperation = "source-over";
            context.setLineDash([]);
            // 鍵を置く玉: ロックした項目。ロックしていなければ、詳細を開いている項目
            const lockedNow = anchorOf(null);
            const keyView = wide.matches ? (views.find((view) => view.ball.id === (lockedNow ?? current)) ?? null) : null;
            const keyClosed = keyView !== null && keyView.ball.id === lockedNow;
            // 鍵を出すか: 閉じた鍵はロック中いつも、開いた鍵は詳細を開いている玉にカーソルを乗せたときだけ
            const keyShown = keyView !== null && (keyClosed || hover === keyView.ball.id);
            /** 鍵の中心（名前が出ない距離では、玉の右上の札） */
            let keySpot = null;
            /** このコマに印を置いた玉 */
            const markedBalls = new Set();
            for (const view of views) {
                const { ball, depth, close, rank, star } = view;
                const { x, y, radius } = star;
                const marked = star.selected || star.hover;
                // 名前: 玉と同じ倍率で大きさが変わる（玉の幅に英字 6 文字ほど）。いつもは薄く、注目している項目とつながる項目ははっきり出す
                const scale = (projected.get(ball.id)?.f ?? baseK) / baseK;
                const fontSize = 4.6 * scale;
                const alpha = (star.strong ? 0.85 : 0.42 * ball.fade) * depth ** 1.4 * Math.max(0, Math.min(1, (fontSize - 3.5) / 2.5));
                if (!(alpha > 0.03 && ease > 0.9 && onScreen(x, y - radius, width, height, 400)))
                    continue;
                const color = star.selected ? colors.ring : MindmapPreview.lookLabelColor({ look: lookNow, dark, fallback: colors.label });
                // 毎コマ文字を作らず、画像に倍率をかけて置く
                const image = labelImage(ball, marked, color);
                const k = (dpr * fontSize) / 10 / LABEL_RESOLUTION;
                const nameBottom = y - radius * (MindmapPreview.LABEL_LIFT[lookNow] ?? 1) - 3 * scale;
                context.globalAlpha = alpha * close;
                context.setTransform(k, 0, 0, k, dpr * x, dpr * nameBottom);
                context.drawImage(image, -image.width / 2, -image.height);
                context.setTransform(dpr, 0, 0, dpr, 0, 0);
                const nameWidth = (image.width / LABEL_RESOLUTION) * (fontSize / 10);
                const nameHeight = LABEL_HEIGHT * (fontSize / 10);
                const nameCenterY = nameBottom - nameHeight / 2;
                const nameRight = x + nameWidth / 2;
                // 状態の印: 注目しているときだけ、起点とつながる項目の名前の左に、名前と同じ濃さで置く（資料の成果物は箱）
                const item = index.byId.get(ball.id)?.item;
                if (selectedBall !== undefined && near.has(ball.id) && item !== undefined) {
                    const statusMarkImage = statusImage({ item, ringColor: colors.ring });
                    if (statusMarkImage !== null) {
                        const size = fontSize * STATUS_MARK_SCALE;
                        context.globalAlpha = alpha * close;
                        context.drawImage(statusMarkImage, x - nameWidth / 2 - fontSize * STATUS_MARK_GAP - size, nameCenterY - size / 2, size, size);
                    }
                }
                // コメントの印: 名前を文字 8px 以上で描いた、件数のある玉に、名前と同じ濃さで置く。名前・鍵・コメントの印の順で、鍵を出すときだけ鍵の幅を空ける
                const count = commentCounts[ball.id] ?? 0;
                const slot = count > 0 && fontSize >= COMMENT_MARK_MIN_FONT ? markSlotOf(ball.id, count) : null;
                const keyHere = view === keyView && keyShown;
                const left = nameRight + (keyHere ? KEY_GAP + KEY_SIZE : 0) + COMMENT_MARK_GAP;
                if (keyHere)
                    keySpot = { x: nameRight + KEY_GAP + KEY_SIZE / 2, y: nameCenterY, badge: false, alpha: alpha * close };
                if (slot !== null) {
                    const top = nameCenterY - slot.height / 2;
                    // 名前と印が描く枠（上端は名前か印の高いほう、下端は低いほう）が、キャンバスに収まるときだけ置く
                    const frameTop = Math.min(top, nameCenterY - nameHeight / 2);
                    const frameBottom = Math.max(top + slot.height, nameCenterY + nameHeight / 2);
                    const fits = x - nameWidth / 2 >= 0 && left + slot.width <= width && frameTop >= 0 && frameBottom <= height;
                    if (fits) {
                        slot.element.style.transform = `translate(${left}px, ${top}px)`;
                        slot.element.style.opacity = String(alpha * close);
                        // 手前の玉ほど上に重ねる（重なり順は層の中に閉じる）
                        slot.element.style.zIndex = String(rank + 1);
                        showMark({ slot, visible: true });
                        markedBalls.add(ball.id);
                    }
                }
            }
            // 鍵: 閉じた鍵はロック中いつも、開いた鍵は詳細を開いている玉にカーソルを乗せたときだけ出す。押しても何も起きない
            if (keyView !== null && keyShown) {
                // 名前が出ていない遠い距離では、玉の右上に札に入れて置く
                const spot = keySpot ?? { x: keyView.star.x + keyView.star.radius * 0.8 + 8, y: keyView.star.y - keyView.star.radius * 0.8 - 8, badge: true, alpha: 1 };
                // 外れない操作をされた直後は、赤くして左右に震わせ、だんだん収める（CSS のアニメーションに頼らず毎コマ当てるので、動きを減らす設定でも止めない）
                const elapsed = now - shakeStart;
                const shaking = keyClosed && elapsed < MindmapPreview.SHAKE_MS;
                const { decay, wave } = shaking ? MindmapPreview.shakeAt(elapsed) : { decay: 0, wave: 0 };
                const keyX = spot.x + wave * MindmapPreview.SHAKE_SHIFT * decay;
                const red = MindmapPreview.shakeColor();
                const keyColor = shaking ? red : keyClosed ? colors.ring : colors.label;
                if (shaking) {
                    context.globalAlpha = 0.55 * decay;
                    context.drawImage(MindmapPreview.bakeGlow({ color: red, falloff: 2 }), keyX - 22, spot.y - 22, 44, 44);
                }
                if (spot.badge) {
                    context.globalAlpha = keyClosed ? 0.95 : 0.6;
                    context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--surface").trim();
                    context.beginPath();
                    context.arc(keyX, spot.y, KEY_SIZE * 0.85, 0, Math.PI * 2);
                    context.fill();
                    context.strokeStyle = keyColor;
                    context.lineWidth = 1;
                    context.stroke();
                }
                drawKeyIcon({
                    context,
                    x: keyX,
                    y: spot.y,
                    size: KEY_SIZE * (1 + MindmapPreview.SHAKE_GROW * decay),
                    closed: keyClosed,
                    color: keyColor,
                    alpha: keyClosed ? 0.95 : 0.45,
                    swing: wave * MindmapPreview.SHAKE_SWING * decay,
                });
            }
            context.globalAlpha = 1;
            // このコマに置かなかった印は隠し、件数が無くなった玉の印は外す
            for (const [id, slot] of markSlots) {
                if (markedBalls.has(id))
                    continue;
                showMark({ slot, visible: false });
                if ((commentCounts[id] ?? 0) === 0) {
                    slot.element.remove();
                    markSlots.delete(id);
                }
            }
        };
        // ===== 起動 =====
        // 文字の書体が読み込まれたら、取っておいた文字の画像を作り直す
        document.fonts?.addEventListener("loadingdone", () => labelCache.clear());
        // テーマが変わったら、色を読み直す
        const refreshColors = () => {
            colors = readColors();
            labelCache.clear();
        };
        new MutationObserver(refreshColors).observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["data-theme"],
        });
        live = {
            select,
            refreshColors,
            setComments: (counts) => {
                // 渡していない（配る書き出しなど）ときは印を置かない
                if (comments !== undefined)
                    commentCounts = counts;
            },
            setLook,
            setLock: (id) => {
                locked = id;
                select(current);
            },
            shake: () => {
                shakeStart = performance.now();
            },
        };
        // 枠の大きさが決まってから玉を置き、描き始める
        const start = new ResizeObserver(() => {
            if (canvas.clientWidth === 0)
                return;
            start.disconnect();
            resize();
            rebuild();
            requestAnimationFrame(frame);
        });
        start.observe(canvas);
        return root;
    }
    MindmapPreview.graphScreen = graphScreen;
})(MindmapPreview || (MindmapPreview = {}));
// 起動。記録を読み（配る書き出しは埋め込みから、サーバーの配信は記録の取得から）、URL のハッシュが指す画面を描き、操作を画面の移動・書き換えの知らせ・コメントの読み書き・端末の保存領域につなぐ。
var MindmapPreview;
(function (MindmapPreview) {
    /** 埋め込みのデータの要素の ID */
    const DATA_ELEMENT_ID = "mindmap-data";
    /** 端末の保存領域のキー */
    MindmapPreview.PREFS_KEY = "mindmap-preview";
    /** 入力が止まってから書きかけを保つまでの待ち（ミリ秒）。打つたびに書かず、打ち終えた直後に閉じても失うのがこの待ちの分だけで済む長さ */
    MindmapPreview.DRAFT_SAVE_DELAY_MS = 500;
    /** 画面の下に「ワークスペースの既定が変わりました。」を出しておくミリ秒 */
    MindmapPreview.NOTICE_MS = 6000;
    /** 画面の下に「{n} 件を保存しました。」を出しておくミリ秒 */
    MindmapPreview.SAVED_NOTICE_MS = 5000;
    /** 追加の入力で案を採用したときの、足す検討事項の状態 */
    const ADOPTED_DECISION_STATUS = "決定済み";
    /** そのタブの「前回開いてから」の始まり（`OpenedPoint` の JSON）を残す sessionStorage のキー。あれば `POST /api/opened` を呼ばない（同じタブで読み込み直しても範囲を変えない） */
    MindmapPreview.SINCE_KEY = "mindmap-since";
    /** そのタブで変えた詳細パネルの幅（px の整数の文字列）を残す sessionStorage のキー。種類で分けない。配る書き出しでも同じ */
    MindmapPreview.PANEL_WIDTH_KEY = "mindmap-panel-width";
    /** 入力欄のキー。向けた先（`target` と `loc` の組か、`thread`）を 1 つの文字列にする */
    function formKey(target, loc, thread = null) {
        return JSON.stringify([target, loc?.kind ?? null, loc?.start ?? null, loc?.end ?? null, loc?.key ?? null, loc?.text ?? null, thread]);
    }
    MindmapPreview.formKey = formKey;
    /** 狭い幅（詳細パネルを別画面として積む幅） */
    const NARROW_QUERY = "(max-width: 900px)";
    /** タブのアイコン */
    const TAB_ICON = {
        overview: "home",
        decisions: "decision",
        tasks: "task",
        research: "research",
        docs: "doc",
        terms: "term",
        notes: "note",
        logs: "log",
    };
    /** タブの名前（種類の名前は読み込み順によらないよう、呼ばれたときに引く） */
    function tabLabel(key) {
        return key === "overview" ? "概要" : MindmapPreview.KIND_LABEL[key];
    }
    /** 画面の名前（ネットワークは種類のタブに無いので、ここで持つ） */
    function screenName(tab) {
        return tab === "graph" ? "ネットワーク" : tabLabel(tab);
    }
    /** `mindmap-data` の要素の中身を `JSON.parse` して返す。中身が空なら（サーバーの配信）null */
    function readEmbeddedData(doc) {
        const text = doc.getElementById(DATA_ELEMENT_ID)?.textContent;
        // 要素が無い（同梱の雛形か書き出しの誤り）
        if (text === undefined || text === null)
            throw new Error("記録を読み込めませんでした。");
        // 中身が空: サーバーの配信なので、記録は取得で読む
        if (text.trim() === "")
            return null;
        try {
            return JSON.parse(text);
        }
        catch {
            throw new Error("記録を読み込めませんでした。");
        }
    }
    MindmapPreview.readEmbeddedData = readEmbeddedData;
    /** 既定の設定 */
    function defaultPrefs() {
        return {
            theme: null,
            columns: {},
            look: null,
            kinds: null,
            diffSel: null,
            filters: {},
            minimap: null,
            bodyLayout: null,
            tablePin: null,
            tableHead: null,
            tableStripes: null,
            sectionFold: null,
        };
    }
    /** 端末の保存領域から設定を読む。読めないときは既定を返す */
    function loadPrefs(storage) {
        try {
            const saved = storage.getItem(MindmapPreview.PREFS_KEY);
            if (saved === null)
                return defaultPrefs();
            const parsed = { ...defaultPrefs(), ...JSON.parse(saved) };
            // 選べない値の見た目・種類は、その項目だけワークスペースの既定に従う
            const looks = MindmapPreview.NETWORK_LOOKS.map((option) => option.key);
            if (!looks.includes(parsed.look))
                parsed.look = null;
            const kinds = MindmapPreview.KIND_KEYS;
            if (!Array.isArray(parsed.kinds) || !parsed.kinds.every((kind) => kinds.includes(kind)))
                parsed.kinds = null;
            // 画面ごとの条件が値の配列の対応でないときは、残した条件を使わない
            if (!isFiltersByTab(parsed.filters))
                parsed.filters = {};
            // 差分のミニマップの上書きは false だけを読む（表示するは上書きを持たない）
            if (parsed.minimap !== false)
                parsed.minimap = null;
            // 本文の差分の並べ方の上書きは side だけを読む（インラインは上書きを持たない）
            if (parsed.bodyLayout !== "side")
                parsed.bodyLayout = null;
            // 本文の表とセクションの見せ方の上書きは、既定と違う値だけを読む
            if (parsed.tablePin !== false)
                parsed.tablePin = null;
            if (parsed.tableHead !== false)
                parsed.tableHead = null;
            if (parsed.tableStripes !== true)
                parsed.tableStripes = null;
            if (parsed.sectionFold !== false)
                parsed.sectionFold = null;
            return parsed;
        }
        catch {
            return defaultPrefs();
        }
    }
    MindmapPreview.loadPrefs = loadPrefs;
    /** 画面ごとの絞り込みの条件として読めるか（画面のキーごとに、条件のキー → 文字の配列の対応） */
    function isFiltersByTab(value) {
        if (typeof value !== "object" || value === null || Array.isArray(value))
            return false;
        return Object.values(value).every((filters) => typeof filters === "object" &&
            filters !== null &&
            !Array.isArray(filters) &&
            Object.values(filters).every((values) => Array.isArray(values) && values.every((v) => typeof v === "string")));
    }
    /** 絞り込みの条件が同じか（値の並びと、値の無い条件は区別しない） */
    function sameFilters(a, b) {
        const normal = (filters) => JSON.stringify(Object.entries(filters)
            .filter(([, values]) => values.length > 0)
            .map(([key, values]) => [key, [...values].sort()])
            .sort(([x], [y]) => (x < y ? -1 : x > y ? 1 : 0)));
        return normal(a) === normal(b);
    }
    /** 絞り込みの条件を端末に残す画面（種類のタブとネットワーク。概要は絞り込みを持たない。読み込み順によらないよう、呼ばれたときに作る） */
    function filterTabs() {
        return [...MindmapPreview.KIND_KEYS, "graph"];
    }
    /** 設定を端末の保存領域に残し、書けたかを返す。保存領域が例外を送るときは偽を返す（開いている間だけ設定を保つ） */
    function savePrefs({ storage, prefs }) {
        try {
            storage.setItem(MindmapPreview.PREFS_KEY, JSON.stringify(prefs));
            return true;
        }
        catch {
            return false;
        }
    }
    MindmapPreview.savePrefs = savePrefs;
    /** 項目ごとに、個人の上書きがあればそれを、無ければワークスペースの既定を、それも無ければ組み込みの既定を使う */
    function resolveDisplay(prefs, display) {
        const defaultLook = display?.network_look ?? MindmapPreview.BUILTIN_LOOK;
        const defaultKinds = new Set(display?.visible_kinds ?? MindmapPreview.KIND_KEYS);
        // 上書きを持つ項目の名前を、見た目・種類・ライト / ダーク・表の列・絞り込み・差分のミニマップ・本文の表とセクションの見せ方・本文の差分の並べ方の順に並べる（条件が画面の既定と同じ画面は並べない）
        const overrides = [
            ...(prefs.look === null ? [] : ["ネットワークの見た目"]),
            ...(prefs.kinds === null ? [] : ["表示する種類"]),
            ...(prefs.theme === null ? [] : ["ライト / ダーク"]),
            ...MindmapPreview.KIND_KEYS.filter((kind) => prefs.columns[kind] !== undefined).map((kind) => `表の列（${MindmapPreview.KIND_LABEL[kind]}）`),
            ...filterTabs().filter((tab) => prefs.filters[tab] !== undefined && !sameFilters(prefs.filters[tab], MindmapPreview.initialFilters(tab, {}, null))).map((tab) => `絞り込み（${screenName(tab)}）`),
            ...(prefs.minimap === false ? [MindmapPreview.MINIMAP_LABEL] : []),
            ...(prefs.tablePin === false ? [MindmapPreview.BODY_VIEW_LABELS.pin] : []),
            ...(prefs.tableHead === false ? [MindmapPreview.BODY_VIEW_LABELS.head] : []),
            ...(prefs.tableStripes === true ? [MindmapPreview.BODY_VIEW_LABELS.stripes] : []),
            ...(prefs.sectionFold === false ? [MindmapPreview.BODY_VIEW_LABELS.fold] : []),
            ...(prefs.bodyLayout === "side" ? [MindmapPreview.BODY_LAYOUT_LABEL] : []),
        ];
        return {
            look: prefs.look ?? defaultLook,
            kinds: prefs.kinds === null ? defaultKinds : new Set(prefs.kinds),
            defaultLook,
            defaultKinds,
            overrides,
            // 上書きが false のときだけ表示しない
            minimap: prefs.minimap !== false,
            // 上書きが side のときだけ左右に並べる
            bodyLayout: prefs.bodyLayout === "side" ? "side" : "inline",
            // 上書きのある項目だけ既定と逆にする
            bodyView: {
                pin: prefs.tablePin !== false,
                head: prefs.tableHead !== false,
                stripes: prefs.tableStripes === true,
                fold: prefs.sectionFold !== false,
            },
        };
    }
    MindmapPreview.resolveDisplay = resolveDisplay;
    /** 「既定に戻す」で、見た目・表示する種類・ライト / ダーク・表の列・絞り込みの条件・差分のミニマップ・本文の表とセクションの見せ方・本文の差分の並べ方を外した設定を返す（`diffSel` は残し、渡した設定は変えない） */
    function clearOverrides(prefs) {
        return {
            ...prefs,
            theme: null,
            look: null,
            kinds: null,
            columns: {},
            filters: {},
            minimap: null,
            bodyLayout: null,
            tablePin: null,
            tableHead: null,
            tableStripes: null,
            sectionFold: null,
        };
    }
    MindmapPreview.clearOverrides = clearOverrides;
    /** 本文の見せ方の項目 → 個人の上書きの項目 */
    const BODY_VIEW_PREF = { pin: "tablePin", head: "tableHead", stripes: "tableStripes", fold: "sectionFold" };
    /** 表示の既定が同じか（無いキーは同じ無しとして比べる） */
    function sameDisplay(a, b) {
        const key = (display) => JSON.stringify([display?.network_look ?? null, display?.visible_kinds ?? null]);
        return key(a) === key(b);
    }
    /** 端末の保存領域（開けない環境では、何も返さない保存領域） */
    function openStorage(kind) {
        try {
            return window[kind];
        }
        catch {
            return {
                length: 0,
                clear: () => undefined,
                getItem: () => null,
                key: () => null,
                removeItem: () => undefined,
                // 残せない旨を呼び手に伝える（`savePrefs` が偽を返す）
                setItem: () => {
                    throw new Error("保存領域が使えません");
                },
            };
        }
    }
    /** そのタブで変えた詳細パネルの幅を読む。正の整数でなければ、残っていないものとして扱う（既定の幅で開く） */
    function readPanelWidth(session) {
        let saved;
        try {
            saved = session.getItem(MindmapPreview.PANEL_WIDTH_KEY);
        }
        catch {
            return null;
        }
        return saved !== null && /^[1-9]\d*$/.test(saved) ? Number(saved) : null;
    }
    MindmapPreview.readPanelWidth = readPanelWidth;
    /** 変えた詳細パネルの幅をそのタブに残す。書けない保存領域では何もしない（開き直すと既定の幅で開く） */
    function writePanelWidth({ session, width }) {
        try {
            session.setItem(MindmapPreview.PANEL_WIDTH_KEY, String(width));
        }
        catch {
            return;
        }
    }
    MindmapPreview.writePanelWidth = writePanelWidth;
    /** そのタブの「前回開いてから」の始まりを決める。同じタブで読み込み直したときは、残した始まりをそのまま使う */
    async function resolveSince({ serverMode, prefs, persist, headSeq, session = openStorage("sessionStorage"), post = MindmapPreview.postOpened, now = () => new Date().toISOString(), }) {
        // 同じタブに残した始まりがあれば使う（読めない・前の版の日時の文字列は残っていないものとして続ける）
        try {
            const kept = JSON.parse(session.getItem(MindmapPreview.SINCE_KEY) ?? "null");
            if (MindmapPreview.isOpenedPoint(kept))
                return kept;
        }
        catch {
            // 読めない保存領域・JSON でない値: 決め直す
        }
        // タブを開いた時点
        let opened = { at: now(), seq: headSeq };
        let previous;
        if (serverMode) {
            // サーバーの配信は、ワークスペースに残る前回の時点を引き、今の時点に書き換えてもらう
            const reply = await post();
            previous = reply?.previous ?? null;
            opened = reply?.opened ?? opened;
        }
        else {
            // 配る書き出しは、前回の時点を端末の設定に持ち、今の時点に書き換える
            previous = MindmapPreview.isOpenedPoint(prefs.opened) ? prefs.opened : null;
            prefs.opened = opened;
            persist();
        }
        // 前回の時点が無い・通し番号が今の記録より先（ワークスペースを戻した・作り直した）ときは、今の時点からにする
        const since = previous !== null && previous.seq <= headSeq ? previous : opened;
        try {
            session.setItem(MindmapPreview.SINCE_KEY, JSON.stringify(since));
        }
        catch {
            // 残せない環境では、読み込み直すたびに決め直す
        }
        return since;
    }
    MindmapPreview.resolveSince = resolveSince;
    /** 変更履歴のモーダルに、差分を出さない行と、まだまとめていない変更・前回開いてから・まとまりの行を新しい順に並べる */
    function historyPoints({ changes, since }) {
        /** その時点で足した・変えた・消した項目の数（合わせた範囲で足して消した項目は、消した項目として 1 件に数える） */
        const countOf = (sel) => {
            const point = MindmapPreview.resolveDiffPoint(changes, sel, since);
            return point === null ? 0 : point.added.size + point.changed.size + point.removed.size;
        };
        const hasPending = changes.pending.added.length + changes.pending.changed.length + (changes.pending.removed ?? []).length > 0;
        return [
            { sel: "", name: "差分を出さない（今の内容）", sub: "印と差分を出さずに今の内容だけを読む" },
            ...(hasPending
                ? [{ sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: countOf("pending") }]
                : []),
            { sel: "since", name: "前回開いてから", sub: `${MindmapPreview.formatJst(since.at)} より後`, count: countOf("since") },
            ...changes.sets.map((set) => ({ sel: set.id, name: set.summary, sub: MindmapPreview.formatJst(set.at), count: countOf(set.id) })),
        ];
    }
    /** 選んだ時点の、項目の ID → 差分の印 */
    function marksOf(point) {
        if (point === null)
            return undefined;
        return Object.fromEntries([
            ...[...point.added].map((id) => [id, "new"]),
            ...[...point.changed].map((id) => [id, "changed"]),
        ]);
    }
    /** レビュー中のコメントを `target` ごとに数え、項目の ID → 件数を返す（箇所を指すコメントもその項目に数え、項目を指さないコメントと件数 0 の項目は含めない） */
    function commentCounts(items) {
        const counts = {};
        for (const item of items) {
            if (item.target === null)
                continue;
            counts[item.target] = (counts[item.target] ?? 0) + 1;
        }
        return counts;
    }
    MindmapPreview.commentCounts = commentCounts;
    /** 2 つの件数の対応が同じか */
    function sameCounts(a, b) {
        const keys = Object.keys(a);
        return keys.length === Object.keys(b).length && keys.every((key) => a[key] === b[key]);
    }
    /** mdmark を読み終えるのを待ち（読めなくても続ける）、記録を読み、ハッシュが指す画面を描き、操作と履歴をつなぐ */
    async function start() {
        await MindmapPreview.loadMdmark();
        let embedded;
        try {
            embedded = readEmbeddedData(document);
        }
        catch (error) {
            document.body.prepend(MindmapPreview.h({ tag: "p", attrs: { class: "md-error" }, children: [error.message] }));
            return;
        }
        void run(embedded);
    }
    MindmapPreview.start = start;
    /** サーバーが記録を読めるまで待つ。読めない間は、接続の状態と理由だけを出し、書き換えの知らせか接続が戻ったときに読み直す */
    function waitForRecords(theme) {
        const holder = MindmapPreview.h({ tag: "div", attrs: { id: "unavailable" } });
        document.body.prepend(holder);
        return new Promise((resolve) => {
            const attempt = async () => {
                const result = await MindmapPreview.fetchRecords();
                if (result.ok) {
                    stop();
                    holder.remove();
                    resolve(result.data);
                    return;
                }
                const message = result.reason === "invalid" && result.detail !== null
                    ? result.detail
                    : "サーバーにつながりません。起動スクリプトで立ち上げ直し、示された新しい URL で開いてください。";
                holder.replaceChildren(MindmapPreview.topbar({
                    title: "mindstella",
                    tabs: [],
                    current: "overview",
                    theme,
                    onNavigate: () => undefined,
                    onSearch: () => undefined,
                    onTheme: () => undefined,
                    connection: "offline",
                }), MindmapPreview.h({ tag: "p", attrs: { class: "md-error" }, children: [message] }));
            };
            const stop = MindmapPreview.subscribeEvents({
                onChanged: () => void attempt(),
                onConnection: (connected) => {
                    if (connected)
                        void attempt();
                },
            });
            void attempt();
        });
    }
    /** 記録を用意し（サーバーの配信では取得して）、画面を描いて操作とつなぐ */
    async function run(embedded) {
        /** サーバーの配信か（配る書き出しは記録を埋め込みから読み、送信も書き換えの知らせも持たない） */
        const serverMode = embedded === null;
        const storage = openStorage("localStorage");
        const session = openStorage("sessionStorage");
        const prefs = loadPrefs(storage);
        const persist = () => savePrefs({ storage, prefs });
        MindmapPreview.restoreTablePrefs(prefs.columns, (kind, tablePrefs) => {
            if (tablePrefs === null)
                delete prefs.columns[kind];
            else
                prefs.columns[kind] = tablePrefs;
            display.storageOk = persist();
            // 表の列の上書きは、パネルの「この端末で変えている項目」に合わせる
            resolved = resolveDisplay(prefs, data.settings.display);
            if (display.open)
                renderSettings();
        });
        // ===== テーマ =====
        /** 端末のライト / ダーク（個人の上書きが無いときに従う） */
        const systemTheme = () => (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        let theme = prefs.theme ?? systemTheme();
        document.documentElement.dataset["theme"] = theme;
        // ===== 記録 =====
        let data = embedded ?? (await waitForRecords(theme));
        let index = MindmapPreview.buildIndex(data);
        /** サーバーが返した記録そのもの（保存待ちの編集を当てる前）。`data` は保存待ちの編集を当てた、画面に出す値 */
        let serverData = data;
        /** 保存待ちの編集を当てる前の索引（保存待ちのパネルが項目の種類とタイトルを引く） */
        let serverIndex = index;
        document.title = `${data.settings.summary} | mindstella`;
        let connection = "online";
        // 表示の設定: 項目ごとに、個人の上書き → ワークスペースの既定 → 組み込みの既定の順で読み分けた値
        let resolved = resolveDisplay(prefs, data.settings.display);
        const display = { open: false, confirm: null, message: null, savedDisplay: null, storageOk: true };
        /** 表示しない種類のタブを指す route は、概要へ置き換える（`id` は残し、詳細パネルは開く） */
        const visibleRoute = (next) => next.tab === "overview" || next.tab === "graph" || resolved.kinds.has(next.tab)
            ? next
            : { ...next, tab: "overview", view: MindmapPreview.defaultView("overview"), filters: {} };
        // 差分の表示: そのタブの「前回開いてから」の始まりと、選んだ時点（持たない・記録に無いときは差分を出さない）
        const since = await resolveSince({ serverMode, prefs, persist, headSeq: data.changes.sets[0]?.until_seq ?? 0 });
        // ===== 画面の土台 =====
        const top = MindmapPreview.h({ tag: "div", attrs: { id: "top" } });
        const main = MindmapPreview.h({ tag: "main", attrs: { class: "content", id: "main" } });
        document.body.prepend(top, main);
        /** ハッシュの `diff`（無ければ端末の設定）が指す時点を引き、引けた時点を端末の設定と route に揃える（引けなければどちらも null） */
        const settleDiffPoint = (next) => {
            const settled = MindmapPreview.resolveDiffPoint(data.changes, next.diff ?? prefs.diffSel ?? null, since);
            const sel = settled?.sel ?? null;
            if ((prefs.diffSel ?? null) !== sel) {
                prefs.diffSel = sel;
                persist();
            }
            return { route: { ...next, diff: sel }, point: settled };
        };
        const initial = settleDiffPoint(visibleRoute(MindmapPreview.parseHash({ hash: location.hash, index })));
        let route = initial.route;
        let point = initial.point;
        let fullViewer = null;
        /** 詳細パネルがもう画面に入れた見出し（同じ項目・同じ見出しでは、描き直しのたびに本文のスクロールを戻さない） */
        let shownHeading = null;
        const filterState = { byTab: {}, drawerOpen: false };
        const lockState = { graph: null, map: null };
        const stack = { front: "detail" };
        const editState = {
            edits: [],
            blocked: [],
            open: false,
            editing: null,
            adding: null,
            status: "idle",
            errors: new Map(),
            toast: null,
            workspaceOpen: false,
            optionDrafts: new Map(),
            sentEdits: new Map(),
            editsReadSeq: 0,
            editsAppliedSeq: 0,
            addSend: null,
        };
        /** 送信中の編集の値のキー（`adopt` は案の記号を持たず、項目ごとに 1 つ） */
        const sentKeyOf = ({ target, op, key }) => op === "adopt" ? `${target}:adopt` : `${target}:${op}:${key}`;
        /** 送信中の編集の値を、保存待ちの編集と同じ形に並べる（記録に当てるためだけの写し） */
        const sentAsEdits = () => [...editState.sentEdits].map(([sentKey, { value }]) => {
            const [target = "", op = "set", ...rest] = sentKey.split(":");
            return {
                id: "",
                target,
                op: op,
                key: op === "adopt" ? String(value) : rest.join(":"),
                value,
                before: null,
                created: "",
            };
        });
        /** 差分の表示中でなければ、保存待ちの編集（項目の追加を除く）を当てた記録と索引を作り直す。追加する項目は索引に入れず、一覧の画面の `adds` として別に渡す */
        const rebuildIndex = () => {
            data =
                point === null
                    ? MindmapPreview.applyEdits(serverData, [
                        ...editState.edits.filter((entry) => entry.op !== "item-add"),
                        // 送信したがまだ読み取りに載っていない値を上に重ね、描き直しで入力欄を古い値に戻さない
                        ...sentAsEdits(),
                    ])
                    : serverData;
            index = MindmapPreview.buildIndex(data);
            serverIndex = MindmapPreview.buildIndex(serverData);
        };
        /** 差分の表示に移ったら、保存待ちのパネル・設定の画面・編集の表示を閉じる。そのうえで索引を作り直す */
        const syncEditView = () => {
            if (point !== null) {
                editState.open = false;
                editState.workspaceOpen = false;
                editState.editing = null;
                editState.adding = null;
            }
            rebuildIndex();
        };
        // ===== 移動 =====
        /** 詳細パネルを別画面として積む幅か */
        const isNarrow = () => matchMedia(NARROW_QUERY).matches;
        /** 画面の既定の URL（絞り込みは書かない）に route を書き、画面を描く */
        const go = (next, push) => {
            leaveEditViews();
            const screenChanged = next.tab !== route.tab || next.view !== route.view || Object.keys(next.filters).length > 0;
            const idChanged = next.id !== route.id;
            // 差分の時点は、画面・項目を移っても引き継ぐ
            route = { ...next, diff: route.diff };
            MindmapPreview.navigate({ route: { ...route, filters: {} }, push });
            render({ screen: screenChanged || (route.tab === "decisions" && route.view === "map" && idChanged) });
        };
        /** 項目を開く。パネル・全画面の中の移動は履歴に積み、見てきた項目を行き来できるようにする */
        const openItem = (id, inPanel) => {
            // 追加する項目は、追加の入力で開く
            if (id.startsWith(MindmapPreview.NEW_ID_PREFIX)) {
                openAdded(id);
                return;
            }
            flushDrafts();
            leaveEditViews();
            const next = { ...route, id, filters: {}, heading: null };
            const trail = history.state;
            if (inPanel && route.id !== null) {
                // 今いる履歴にも先の項目を持たせ、戻った後に「→」で進めるようにする
                const items = [...(trail?.items ?? [route.id]).slice(0, (trail?.position ?? 0) + 1), id];
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false, trail: { items, position: trail?.position ?? 0 } });
                route = next;
                MindmapPreview.navigate({ route: next, push: true, trail: { items, position: items.length - 1 } });
                render({ screen: route.tab === "decisions" && route.view === "map" });
                return;
            }
            route = next;
            // 狭い幅では詳細を別画面として積み、戻る操作で一覧へ戻す
            MindmapPreview.navigate({ route: next, push: isNarrow(), trail: { items: [id], position: 0 } });
            render({ screen: route.tab === "decisions" && route.view === "map" });
        };
        /** 詳細パネルを閉じる */
        const closeDetail = () => {
            flushDrafts();
            if (isNarrow() && history.state !== null && history.state.items !== undefined && history.length > 1) {
                history.back();
                return;
            }
            route = { ...route, id: null, full: false, filters: {}, heading: null };
            MindmapPreview.navigate({ route, push: false });
            render({ screen: route.tab === "decisions" && route.view === "map" });
            reopenPendingPanel();
        };
        /** 項目を、その種類の画面で開く（画面を移るので履歴に積む） */
        const openFromSearch = (id) => {
            const kind = index.byId.get(id)?.kind;
            if (kind === undefined)
                return;
            // 表示しない種類の項目は、概要の上の詳細パネルで開く
            const tab = resolved.kinds.has(kind) ? kind : "overview";
            go({ tab, view: MindmapPreview.defaultView(tab), id, full: false, filters: {}, heading: null, diff: route.diff }, tab !== route.tab);
        };
        // ===== ロック =====
        /** 効いているロック。画面ごとの `LockState` の項目が、その画面の絞り込みの条件を通る（描いている）ときだけその ID、通らないときは null（`LockState` は残し、条件を戻して描かれたらまたロック中に戻る） */
        const effectiveLock = (key) => {
            const id = lockState[key];
            if (id === null)
                return null;
            const shown = key === "graph"
                ? MindmapPreview.shownGraphIds({ index, filters: filterState.byTab["graph"] ?? {} })
                : MindmapPreview.shownDecisionIds({ index, filters: filterState.byTab["decisions"] ?? {} });
            return shown.has(id) ? id : null;
        };
        /** 玉か節（余白なら null）を押した、または `L` キーを押した。`lockTap` で判定し、`lock`・`unlock` のときだけ `LockState` を変えて画面に反映する。`open` は詳細を切り替え、`blank` は詳細を閉じて全体の表示へ戻し、`shake` は何も変えない（画面が鍵を震わせる） */
        const lockPress = ({ key, pressed }) => {
            const result = MindmapPreview.lockTap({ locked: effectiveLock(key), pressed, open: route.id });
            if (result.action === "lock" || result.action === "unlock") {
                lockState[key] = result.locked;
                // ネットワークは視点を保ったまま中心と強調を寄せ、マップは詳細パネルをそのままに描き直す
                if (key === "graph")
                    MindmapPreview.setGraphLock(effectiveLock("graph"));
                else
                    redrawKeepingState();
            }
            else if (result.action === "open" && pressed !== null) {
                openItem(pressed, false);
            }
            else if (result.action === "blank" && route.id !== null) {
                closeDetail();
            }
            return result.action;
        };
        /** ネットワークの見た目のドロップダウンで選んだ値を個人の上書きに残す（ネットワークは作り直さず、次のコマから当てる） */
        const changeLook = (value) => {
            prefs.look = value;
            changePrefs({ redrawMain: false });
            MindmapPreview.setGraphLook(resolved.look);
        };
        // ===== 描く =====
        /** トップバーとタブの帯 */
        const renderTop = () => {
            const marks = marksOf(point);
            top.replaceChildren(MindmapPreview.topbar({
                title: data.settings.summary,
                tabs: MindmapPreview.TAB_KEYS.filter((key) => key === "overview" || resolved.kinds.has(key)).map((key) => ({
                    key,
                    label: tabLabel(key),
                    icon: TAB_ICON[key],
                    count: key === "overview" ? undefined : data[key].length,
                    // 差分の表示の間、新規・変更・消した項目を持つ種類のタブに点を重ねる
                    marked: key !== "overview" &&
                        ((marks !== undefined && data[key].some((item) => marks[item.id] !== undefined)) ||
                            MindmapPreview.removedOf({ point, kind: key }).length > 0),
                })),
                current: route.tab,
                theme,
                connection,
                readAt: serverMode ? data.built_at : null,
                comments: serverMode,
                commentCount: comment.review.items.length,
                commentsOpen: comment.listOpen,
                commentsUnread: MindmapPreview.anyOpenUnseen(comment.threads),
                onComments: () => (comment.listOpen ? closeList() : openList()),
                settingsOpen: display.open,
                onSettings: () => (display.open ? closeSettings() : openSettings()),
                // 概要以外の画面に絞り込みのボタンを置き、値を選んでいる条件の数をバッジに出す
                filter: route.tab !== "overview",
                filterCount: MindmapPreview.activeConditionCount(filterState.byTab[route.tab] ?? {}),
                filterOpen: filterState.drawerOpen,
                onFilter: toggleDrawer,
                pending: serverMode && point === null && editState.edits.length > 0,
                pendingCount: editState.edits.length,
                pendingOpen: editState.open,
                pendingBlocked: editState.blocked.length > 0,
                onPending: togglePending,
                diffPoint: point === null ? null : { name: point.name, sub: point.sub },
                onHistory: openHistory,
                onDiffOff: () => selectPoint(null),
                onNavigate: (tab) => go({ ...route, tab, view: MindmapPreview.defaultView(tab), filters: {} }, true),
                onSearch: openSearch,
                onTheme: (next) => {
                    theme = next;
                    prefs.theme = next;
                    changePrefs({ redrawMain: false });
                    document.documentElement.dataset["theme"] = next;
                },
            }));
        };
        /** 今の画面 */
        const screenElement = () => {
            const on = {
                open: (id) => openItem(id, false),
                view: (view) => go({ ...route, view, filters: {} }, false),
                filter: changeFilters,
                closeDrawer,
            };
            const marks = marksOf(point);
            // サーバーにつながって開いたときだけ、項目ごとのコメントの件数を渡す（配る書き出しは印を出さない）
            const comments = serverMode ? commentsNow : undefined;
            const filters = filterState.byTab[route.tab] ?? {};
            const { drawerOpen } = filterState;
            // 選んだ時点で消した、この画面の種類の項目
            const removed = MindmapPreview.removedOf({ point, kind: route.tab });
            switch (route.tab) {
                case "overview":
                    return MindmapPreview.overviewScreen({
                        index,
                        on: { open: on.open, navigate: (next) => go({ ...next, id: route.id }, true) },
                        marks,
                        visibleKinds: resolved.kinds,
                    });
                case "decisions":
                    return MindmapPreview.decisionsScreen({
                        index,
                        route,
                        on: { ...on, clear: closeDetail, lock: (id) => lockPress({ key: "map", pressed: id }) },
                        lockedId: effectiveLock("map"),
                        filters,
                        drawerOpen,
                        marks,
                        comments,
                        removed,
                        edit: screenEdit("decisions"),
                    });
                case "tasks":
                    return MindmapPreview.tasksScreen({ index, route, on, filters, drawerOpen, marks, comments, removed, edit: screenEdit("tasks") });
                case "docs":
                    return MindmapPreview.docsScreen({ index, route, on, filters, drawerOpen, marks, comments, removed, edit: screenEdit("docs") });
                case "graph":
                    return MindmapPreview.graphScreen({
                        index,
                        on: {
                            open: on.open,
                            filter: changeFilters,
                            closeDrawer,
                            lock: (id) => lockPress({ key: "graph", pressed: id }),
                            look: changeLook,
                        },
                        filters,
                        drawerOpen,
                        selectedId: route.id,
                        lockedId: effectiveLock("graph"),
                        look: resolved.look,
                        defaultLook: resolved.defaultLook,
                        comments,
                    });
                default:
                    return MindmapPreview.recordsScreen({
                        index,
                        route,
                        on: { open: on.open, filter: changeFilters, closeDrawer },
                        filters,
                        drawerOpen,
                        marks,
                        comments,
                        removed,
                        edit: screenEdit(route.tab),
                    });
            }
        };
        /** 本文の領域を描く。画面（タブ・表示形式）が変わったときだけ描き直す */
        const renderMain = () => {
            main.classList.toggle("map-view", route.tab === "decisions" && route.view === "map");
            // 概要は題名が h1。それ以外の画面は、画面の名前を見えない h1 にする（見出しで画面を探せるように）
            main.replaceChildren(...(route.tab === "overview"
                ? []
                : [MindmapPreview.h({ tag: "h1", attrs: { class: "sr-only" }, children: [screenName(route.tab)] })]), screenElement());
            if (route.tab === "graph")
                MindmapPreview.selectGraphItem(route.id);
        };
        /** 画面の絞り込みの条件の定義と行（残した条件を今の記録で刈り込むのに使う）。概要は絞り込みを持たないので null */
        const filterSource = (tab) => {
            const open = () => undefined;
            switch (tab) {
                case "overview":
                    return null;
                case "graph":
                    return { rows: [...index.byId].map(([id, entry]) => ({ id, ...entry })), columns: MindmapPreview.graphConditions() };
                case "decisions":
                    return { rows: index.data.decisions, columns: MindmapPreview.decisionColumns({ index, open }) };
                case "tasks":
                    return { rows: index.data.tasks, columns: MindmapPreview.taskColumns({ index, open }) };
                case "docs":
                    return { rows: index.data.docs, columns: MindmapPreview.docColumns(index) };
                default:
                    return { rows: index.data[tab], columns: MindmapPreview.recordColumns({ index, kind: tab, open }) };
            }
        };
        /** サーバーの配信で残した、その画面の条件を今の記録で刈り込んだもの。残した条件が無い画面と、配る書き出しは null */
        const savedFilters = (tab) => {
            const saved = prefs.filters[tab];
            const source = filterSource(tab);
            if (!serverMode || saved === undefined || source === null)
                return null;
            return MindmapPreview.pruneFilters({ ...source, saved });
        };
        /** 今の画面の絞り込みを用意する。ハッシュの `f.{列}` があればそれだけを（開き直したときも）、無く初めて開く画面なら端末に残した条件か既定を入れ、ハッシュの分は一度だけ使う。概要には絞り込みのドロワーを置かないので閉じる（タブを押したときも、戻る・進むで移ったときも通る） */
        const prepareFilters = () => {
            if (route.tab === "overview")
                filterState.drawerOpen = false;
            if (Object.keys(route.filters).length > 0 || filterState.byTab[route.tab] === undefined) {
                filterState.byTab[route.tab] = MindmapPreview.initialFilters(route.tab, route.filters, savedFilters(route.tab));
            }
            route = { ...route, filters: {} };
        };
        /** 本文の差分の並べ方を切り替えた: 個人の上書きに残し、開いている詳細パネル・詳細の全画面だけを描き直す（履歴にもハッシュにも書かない）。本文を送った位置と、押したボタンのフォーカスを保つ */
        const changeBodyLayout = (layout) => {
            const bodySelector = route.full ? "dialog.full .panel-body" : "aside.panel .panel-body";
            const scrollTop = document.querySelector(bodySelector)?.scrollTop ?? 0;
            prefs.bodyLayout = layout === "side" ? "side" : null;
            display.storageOk = persist();
            resolved = resolveDisplay(prefs, data.settings.display);
            renderDetail();
            // 描き直した本文の高さは、文書に入った後の次のコマで決まる
            requestAnimationFrame(() => {
                const next = document.querySelector(bodySelector);
                if (next === null)
                    return;
                next.scrollTop = scrollTop;
                next.querySelector(`[data-layout="${layout}"]`)?.focus({ preventScroll: true });
            });
            renderSettings();
        };
        /** 詳細パネルと全画面 */
        const renderDetail = () => {
            // 項目を追加する入力: 詳細パネルと同じ置き方で、追加の入力を開く
            if (isAdding()) {
                document.querySelector("aside.panel:not(.pe-add-panel)")?.remove();
                const full = document.querySelector("dialog.full");
                full?.close();
                full?.remove();
                fullViewer = null;
                closePill();
                document.body.classList.add("panel-open");
                MindmapPreview.markSelected(null);
                renderAddPanel();
                return;
            }
            document.querySelector("aside.pe-add-panel")?.remove();
            const existing = document.querySelector("aside.panel");
            const fullDialog = document.querySelector("dialog.full");
            fullViewer = null;
            closePill();
            document.body.classList.toggle("panel-open", route.id !== null && !route.full);
            MindmapPreview.markSelected(route.id);
            // 別の項目へ移るかパネルを閉じた: 詳細パネルで始めた書き換えは、一覧を開いていても捨てる（入力欄の無い一覧の行に「修正」「削除」の無い行を残さない）。一覧を開いていない間は、消した行と書き換えをすべて捨てる
            if (route.id !== detailShown) {
                detailShown = route.id;
                // 詳細パネルを開く・別の項目へ移った: 左のパネルを開いていても詳細パネルを前に出す
                if (route.id !== null)
                    stack.front = "detail";
                const hadEdit = editing !== null;
                if (!comment.listOpen) {
                    comment.removed = [];
                    editing = null;
                }
                else if (editingIn === "detail") {
                    editing = null;
                }
                if (editing === null) {
                    editError = null;
                    editBody = null;
                    // 一覧を開いていれば、本文だけで残っていた行を直す
                    if (hadEdit && comment.listOpen)
                        renderComments();
                }
            }
            // 別の項目へ移った・パネルを閉じた: 編集の表示は読む表示に戻す（溜めた編集は保存待ちに残る）。追加する項目の入力は別に持つ
            if (editState.editing !== null && !editState.editing.startsWith(MindmapPreview.NEW_ID_PREFIX) && editState.editing !== route.id) {
                editState.editing = null;
            }
            // 開いている項目が無い: パネルも全画面も閉じる
            if (route.id === null) {
                flushDrafts();
                comment.opened = null;
                existing?.classList.remove("open");
                fullDialog?.close();
                fullDialog?.remove();
                return;
            }
            const panel = MindmapPreview.detailPanel({
                id: route.id,
                index,
                full: route.full,
                minimap: resolved.minimap,
                bodyLayout: resolved.bodyLayout,
                bodyView: resolved.bodyView,
                edit: detailEdit(),
                // 詳細パネルの左端に、そのタブで変えた幅から始める幅の区切りを置く（全画面は置かない。幅 900px 以下は CSS が隠し、窓を広げたときに出る）
                resizer: route.full
                    ? null
                    : MindmapPreview.panelResizer({
                        stored: readPanelWidth(session),
                        mapView: () => route.tab === "decisions" && route.view === "map",
                        onChange: (width) => writePanelWidth({ session, width }),
                    }),
                on: {
                    open: (id) => openItem(id, true),
                    layout: changeBodyLayout,
                    close: closeDetail,
                    full: (full) => {
                        // 全画面の中で図を拡大しているときは、本文へ戻る
                        if (!full && fullViewer !== null)
                            return closeFullViewer();
                        go({ ...route, full }, false);
                    },
                    back: () => history.back(),
                    forward: () => history.forward(),
                    diagram: showDiagram,
                    frame: { select: frameSelect, clear: frameClear },
                    // 本文の見出しへ移った: ハッシュの `h` を、履歴に積まずに置き換える
                    heading: (heading) => {
                        route = { ...route, heading };
                        shownHeading = heading === null || route.id === null ? null : { id: route.id, heading };
                        MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
                    },
                    // 本文のまとまりのリンクを押した: 記録にあるまとまりのときだけ、変更履歴で選んだときと同じに切り替える
                    changeSet: openChangeSet,
                },
                comment: serverMode
                    ? {
                        form: formProps(route.id),
                        reviews: comment.review.items.filter((item) => item.target === route.id),
                        edit: {
                            removed: comment.removed.filter((item) => item.target === route.id),
                            editing,
                            editingIn,
                            editError,
                            editBody,
                            on: reviewRowHandlers(MindmapPreview.REVIEW_FOCUS),
                        },
                    }
                    : null,
                highlight: openedLocation(),
                diff: point,
                // 開いたときにだけ見出しを画面に入れる
                heading: shownHeading?.id === route.id && shownHeading.heading === route.heading ? null : route.heading,
            });
            shownHeading = route.heading === null ? null : { id: route.id, heading: route.heading };
            if (route.full) {
                existing?.classList.remove("open");
                fullDialog?.remove();
                document.body.append(panel);
                panel.showModal();
                return;
            }
            fullDialog?.close();
            fullDialog?.remove();
            if (existing === null) {
                // 初めて開く: すべり込ませるため、置いてから次のコマで開いた状態にする
                document.body.append(panel);
                requestAnimationFrame(() => panel.classList.add("open"));
            }
            else {
                // 開いたまま項目を移った: すべり込ませずに中身だけを入れ替える
                existing.className = `${panel.className} open`;
                existing.replaceChildren(...panel.children);
            }
        };
        /** コメントの一覧の行から開いたとき、そのコメントの箇所。別の項目へ移っていれば示すのをやめる */
        const openedLocation = () => {
            // スレッドの向けた項目から開いた: その項目の中でだけ箇所を示す
            if (comment.highlight !== null) {
                if (comment.highlight.target === route.id)
                    return comment.highlight.loc;
                comment.highlight = null;
            }
            const opened = comment.review.items.find((item) => item.id === comment.opened);
            if (opened === undefined || opened.target !== route.id) {
                comment.opened = null;
                return null;
            }
            return opened.loc;
        };
        /** 描く（`screen` が真のとき本文の領域も描き直す） */
        const render = ({ screen }) => {
            prepareFilters();
            renderTop();
            if (screen) {
                const wide = document.querySelector(".table-wrap, .map-wrap, .board");
                const keep = wide === null ? 0 : wide.scrollTop;
                renderMain();
                void keep;
            }
            renderDetail();
            renderPending();
            renderWorkspace();
            if (route.tab === "graph")
                MindmapPreview.selectGraphItem(route.id);
            // 作り直した本文にも、開いているパネルの下の部品を止める
            scheduleInert();
        };
        // ===== 絞り込み =====
        /** 開いているパネルが覆った本文の部品を止める関数が返した、止めた分を外す関数 */
        let releaseInert = null;
        /** 開いている左のパネル（絞り込みのドロワー・コメントの一覧・表示の設定のパネル）。開いていなければ null */
        const openLeftPanel = () => filterState.drawerOpen
            ? document.querySelector("dialog.drawer")
            : comment.listOpen
                ? document.querySelector(".comments-panel")
                : editState.open
                    ? document.querySelector(".pending-panel")
                    : display.open
                        ? document.querySelector(".settings-drawer")
                        : null;
        /** 幅 900px 以下で詳細パネルと左のパネルを両方開いていて、左のパネルを前に出しているか */
        const isLeftFront = () => isNarrow() &&
            route.id !== null &&
            !route.full &&
            stack.front === "left" &&
            (filterState.drawerOpen || comment.listOpen || display.open || editState.open);
        /** 幅 900px 以下で両方を開いているとき、前に出す側を `left-front` で決め、後ろになった側の部品に `inert` を付ける。それ以外は付けた分を外す */
        const applyStack = () => {
            const detail = document.querySelector("aside.panel");
            const left = openLeftPanel();
            const both = isNarrow() && route.id !== null && !route.full && detail !== null && left !== null;
            const leftFront = both && stack.front === "left";
            document.body.classList.toggle("left-front", leftFront);
            if (detail !== null)
                detail.inert = leftFront;
            if (left !== null)
                left.inert = both && !leftFront;
        };
        /** 前に止めた分を外してから、開いているパネル（絞り込みのドロワー・コメントの一覧・表示の設定のパネル）が覆った本文の部品を止め、詳細パネルとの前後を当てる */
        const applyInert = () => {
            releaseInert?.();
            releaseInert = null;
            const panel = openLeftPanel();
            if (panel !== null)
                releaseInert = MindmapPreview.inertBehind(panel);
            applyStack();
        };
        // 幅が 900px をまたいだとき、前後と `inert` をやり直す
        matchMedia(NARROW_QUERY).addEventListener("change", applyInert);
        /** パネルが開いた後（ドロワーは文書に入った後の次のマイクロタスクで開く）に、本文の部品を止める */
        const scheduleInert = () => queueMicrotask(applyInert);
        /** 画面の条件を変えて描き直す（ドロワーは開いたまま） */
        const changeFilters = (next) => {
            filterState.byTab[route.tab] = next;
            // サーバーの配信では、条件を変えるたびに端末へ残す（表示の設定の「この端末で変えている項目」も合わせる）
            if (serverMode) {
                prefs.filters[route.tab] = { ...next };
                display.storageOk = persist();
                resolved = resolveDisplay(prefs, data.settings.display);
                if (display.open)
                    renderSettings();
            }
            redrawKeepingState();
        };
        /** 絞り込みのドロワーを閉じ、絞り込みのボタンへフォーカスを戻す */
        const closeDrawer = () => {
            filterState.drawerOpen = false;
            redrawKeepingState();
            document.querySelector("[data-act='filter']")?.focus();
        };
        /** 絞り込みのドロワーを開く・閉じる（開くときはコメントの一覧と表示の設定のパネルを閉じる） */
        const toggleDrawer = () => {
            if (filterState.drawerOpen) {
                closeDrawer();
                return;
            }
            if (comment.listOpen)
                closeList();
            if (display.open) {
                display.open = false;
                renderSettings();
            }
            editState.open = false;
            renderPending();
            filterState.drawerOpen = true;
            stack.front = "left";
            redrawKeepingState();
        };
        // ===== 図の拡大 =====
        /** 図を拡大して見る。詳細パネルからはモーダル、全画面からは全画面の中身を切り替える */
        const showDiagram = (svg, diff) => {
            if (route.full) {
                const dialog = document.querySelector("dialog.full");
                const body = dialog?.querySelector(".panel-body");
                if (dialog === null || dialog === undefined || body === null || body === undefined)
                    return;
                body.hidden = true;
                const viewer = MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "full-viewer" },
                    children: [MindmapPreview.diagramViewer({ svg, on: { close: closeFullViewer }, diff })],
                });
                body.after(viewer);
                fullViewer = viewer;
                return;
            }
            const modal = MindmapPreview.h({ tag: "dialog", attrs: { class: "viewer", "aria-label": "図の拡大" } });
            modal.append(MindmapPreview.diagramViewer({ svg, on: { close: () => modal.close() }, diff }));
            modal.addEventListener("close", () => modal.remove());
            document.body.append(modal);
            modal.showModal();
        };
        /** 全画面の中の図の拡大を閉じて、本文に戻す */
        const closeFullViewer = () => {
            fullViewer?.remove();
            fullViewer = null;
            const body = document.querySelector("dialog.full .panel-body");
            if (body !== null)
                body.hidden = false;
        };
        // ===== 全体の検索 =====
        /** 検索を開く（開いているときは何もしない） */
        const openSearch = () => {
            if (document.querySelector("dialog.search") !== null)
                return;
            const dialog = MindmapPreview.searchDialog({
                index,
                on: {
                    open: (id) => {
                        dialog.close();
                        openFromSearch(id);
                    },
                    close: () => dialog.remove(),
                },
            });
            document.body.append(dialog);
            dialog.showModal();
        };
        // ===== コメント =====
        const api = MindmapPreview.commentApi();
        const comment = {
            review: { items: [], drafts: [] },
            forms: new Map(),
            pendingLoc: new Map(),
            checked: new Set(),
            removed: [],
            stale: new Map(),
            listOpen: false,
            opened: null,
            highlight: null,
            threads: [],
            threadsError: null,
            view: "list",
            reviewFrom: "list",
            filter: "open",
            tag: null,
            openedThread: null,
            composing: false,
            reason: { open: false, body: "", status: "idle", detail: null },
            reviewFocus: null,
            expanded: new Set(),
        };
        const threadsApi = MindmapPreview.threadApi();
        /** 一覧のスクロールの位置（スレッドを開くときに控え、一覧へ戻るときに戻す） */
        let listScroll = 0;
        /** まとめて送った結果・本文を直している行・直せなかった理由・項目を指さない入力にフォーカスがあるか */
        let outcome = null;
        let editing = null;
        /** `editing` の修正を始めた場所（入力欄はその場所だけに描く） */
        let editingIn = "list";
        let editError = null;
        let editBody = null;
        /** 詳細パネルが今出している項目（別の項目へ移ったか閉じたかを知るため） */
        let detailShown = null;
        /** チェックした状態で入れるのは、初めて読んだコメントだけ */
        const knownIds = new Set();
        /** 各画面へ渡す項目の ID → コメントの件数。画面は描き直すたびにこれを読むので、件数が変わったときは同じ物の中身を入れ替える */
        const commentsNow = {};
        /** レビュー中のコメントの件数が変わっていれば、画面を描き直さずに印だけを差し替える（つながりは次のコマから） */
        const syncCommentMarks = () => {
            const next = commentCounts(comment.review.items);
            if (sameCounts(commentsNow, next))
                return;
            for (const key of Object.keys(commentsNow))
                delete commentsNow[key];
            Object.assign(commentsNow, next);
            MindmapPreview.refreshCommentMarks({ root: main, counts: commentsNow });
            MindmapPreview.setGraphComments(commentsNow);
        };
        /** 書きかけを保つ待ちのタイマー（入力欄のキー → タイマー） */
        const draftTimers = new Map();
        /** 読んだレビュー中を状態に入れる。初めて読んだコメントはチェックした状態で入れ、最初の読み込みだけ書きかけの箇所を入力に添える */
        const applyReview = (review, first) => {
            comment.review = review;
            syncCommentMarks();
            for (const item of review.items) {
                if (knownIds.has(item.id))
                    continue;
                knownIds.add(item.id);
                comment.checked.add(item.id);
            }
            if (!first)
                return;
            for (const draft of review.drafts) {
                if (draft.target !== null && draft.loc !== null && !comment.pendingLoc.has(draft.target)) {
                    comment.pendingLoc.set(draft.target, draft.loc);
                }
            }
        };
        /** レビュー中のコメントと書きかけを読み直す。届かないときは前の写しのまま */
        const loadReview = async (first = false) => {
            const result = await api.read();
            if (result.ok && result.data !== null)
                applyReview(result.data, first);
        };
        /** 利用者の既読にする要求を送っているスレッドの ID（応答を待つ間に読み直しても、同じスレッドへ重ねて送らない） */
        const seenSending = new Set();
        /** 既読にする要求が失敗したスレッドの ID（別のスレッドを開くか一覧へ戻るまで、同じスレッドへ重ねて送らない） */
        const seenFailed = new Set();
        /** 開いているスレッドに利用者の未読があれば、写しを既読にして印を待たずに消し、要求は応答を待たずに送る。失敗しても画面に出さず、写しをサーバーの値に戻す */
        const markOpenedSeen = () => {
            const opened = comment.openedThread;
            if (comment.view !== "thread" || opened === null || opened.pending)
                return;
            if (seenSending.has(opened.id) || seenFailed.has(opened.id))
                return;
            const thread = comment.threads.find((entry) => entry.id === opened.id);
            if (thread === undefined || !MindmapPreview.hasUnseen(thread))
                return;
            seenSending.add(opened.id);
            const wasUnseen = MindmapPreview.anyOpenUnseen(comment.threads);
            comment.threads = MindmapPreview.withSeen({ threads: comment.threads, id: opened.id });
            if (wasUnseen !== MindmapPreview.anyOpenUnseen(comment.threads))
                preserving(renderTop);
            void threadsApi
                .seen(opened.id)
                .then(async (result) => {
                if (result.ok)
                    return;
                // 断られた・届かないとき: 送っている控えから失敗の控えへ移して、写しをサーバーの値に戻す
                seenSending.delete(opened.id);
                seenFailed.add(opened.id);
                await loadThreads();
                renderComments();
            })
                .finally(() => seenSending.delete(opened.id));
        };
        /** スレッドを読み直す。読めたら置き換え（トップバーの未読の点が変わるなら描き直し）、断られた・届かないときは前のまま残して理由を持つ */
        const loadThreads = async () => {
            const result = await threadsApi.read();
            if (result.ok && result.data !== null) {
                const wasUnseen = MindmapPreview.anyOpenUnseen(comment.threads);
                // 既読にする要求を送っている間は、送る前のサーバーの値で写しを未読に戻さない
                comment.threads = [...seenSending].reduce((threads, id) => MindmapPreview.withSeen({ threads, id }), result.data.threads);
                comment.threadsError = null;
                if (wasUnseen !== MindmapPreview.anyOpenUnseen(comment.threads))
                    preserving(renderTop);
                markOpenedSeen();
                return;
            }
            comment.threadsError = { detail: result.ok ? null : result.detail };
        };
        /** 向けた先の入力欄の状態。無ければ、同じ向けた先の書きかけの本文で作る */
        const formStateOf = (target, loc, thread = null) => {
            const key = formKey(target, loc, thread);
            let state = comment.forms.get(key);
            if (state === undefined) {
                const draft = comment.review.drafts.find((entry) => formKey(entry.target, entry.loc, entry.thread ?? null) === key);
                state = { target, loc, thread, body: draft?.body ?? "", status: "idle", count: null, detail: null };
                comment.forms.set(key, state);
            }
            return state;
        };
        /** 書きかけをすぐ保つ（空なら消える）。届かないときは何も出さない */
        const saveDraftNow = (state) => {
            const key = formKey(state.target, state.loc, state.thread);
            window.clearTimeout(draftTimers.get(key));
            draftTimers.delete(key);
            void api.saveDraft({
                ...(state.target === null ? {} : { target: state.target }),
                ...(state.loc === null ? {} : { loc: state.loc }),
                ...(state.thread === null ? {} : { thread: state.thread }),
                body: state.body,
            });
        };
        /** 入力が止まってから書きかけを保つ */
        const scheduleDraft = (state) => {
            const key = formKey(state.target, state.loc, state.thread);
            window.clearTimeout(draftTimers.get(key));
            draftTimers.set(key, window.setTimeout(() => saveDraftNow(state), MindmapPreview.DRAFT_SAVE_DELAY_MS));
        };
        /** 待っている書きかけを全て、待たずに保つ（パネル・一覧を閉じるときと項目を移るとき） */
        const flushDrafts = () => {
            for (const key of [...draftTimers.keys()]) {
                const state = comment.forms.get(key);
                if (state !== undefined)
                    saveDraftNow(state);
            }
        };
        /** 開いている入力の結果を消す。入力中の欄を作り直さない（変換の途中を壊さないため） */
        const clearSendResult = () => {
            const form = document.activeElement?.closest("form.send");
            const message = form?.querySelector(".send-msg");
            if (message !== null && message !== undefined) {
                message.className = "send-msg";
                message.replaceChildren();
            }
            form?.querySelector("textarea")?.removeAttribute("aria-invalid");
        };
        /** 入力欄を、今の状態で差し替える（`focus` なら入力欄へフォーカスを戻す）。別の項目へ移っていたら状態だけ持っておく */
        const redrawForm = ({ target, focus }) => {
            // 項目を指さない入力（新しいスレッド）はパネルの一部なので、パネルを描き直す
            if (target === null) {
                renderComments();
                if (focus) {
                    const field = document.querySelector(".comments-panel .talk-new form.send textarea");
                    field?.focus();
                    field?.setSelectionRange(field.value.length, field.value.length);
                }
                return;
            }
            const current = document.querySelector(route.full ? "dialog.full form.send" : "aside.panel form.send");
            if (current === null || route.id !== target)
                return;
            const next = MindmapPreview.sendForm(formProps(target));
            current.replaceWith(next);
            if (!focus)
                return;
            const field = next.querySelector("textarea");
            field?.focus();
            field?.setSelectionRange(field.value.length, field.value.length);
        };
        /** 箇所を外す。書きかけは箇所を持たない向けた先へ移す */
        const unquote = (state) => {
            const { target } = state;
            if (target === null || state.loc === null)
                return;
            const plain = formStateOf(target, null);
            // 箇所を持つ書きかけを消し、本文を箇所を持たない向けた先へ移す
            const moved = state.body;
            saveDraftNow({ ...state, body: "" });
            comment.forms.delete(formKey(target, state.loc));
            comment.pendingLoc.delete(target);
            if (moved !== "") {
                plain.body = plain.body === "" ? moved : `${plain.body}\n${moved}`;
                saveDraftNow(plain);
            }
            redrawForm({ target, focus: true });
        };
        /** 入力欄の引数。`target` が null なら、コメントの一覧の下端の項目を指さない入力 */
        const formProps = (target) => {
            const loc = target === null ? null : (comment.pendingLoc.get(target) ?? null);
            const state = formStateOf(target, loc);
            return {
                target,
                loc,
                body: state.body,
                status: state.status,
                count: state.count,
                detail: state.detail,
                collapsed: false,
                ...(target === null ? { label: "新しいスレッド" } : {}),
                on: {
                    input: (body) => {
                        state.body = body;
                        scheduleDraft(state);
                        // 溜めた・本文が空の結果は、入力を始めたら消す（溜められなかった結果は次に溜めるまで残す）
                        if (state.status === "saved" || state.status === "empty") {
                            state.status = "idle";
                            clearSendResult();
                        }
                    },
                    save: (body) => void saveComment(state, body),
                    unquote: () => unquote(state),
                    copy: (body) => void navigator.clipboard?.writeText(body),
                    focus: () => undefined,
                    blur: () => undefined,
                },
            };
        };
        /** 本文を溜め、結果を状態に残して部品を描き直す */
        const saveComment = async (state, body) => {
            state.body = body;
            // 空白だけ: 溜めず、入力欄へフォーカスを戻す
            if (body.trim() === "") {
                Object.assign(state, { status: "empty", detail: null });
                redrawForm({ target: state.target, focus: true });
                return;
            }
            // 溜める前に、この向けた先の書きかけを保つ待ちを止める（応答を待つ間にタイマーが切れて、消えた書きかけを書き戻さないため）
            window.clearTimeout(draftTimers.get(formKey(state.target, state.loc)));
            draftTimers.delete(formKey(state.target, state.loc));
            Object.assign(state, { status: "saving", detail: null });
            redrawForm({ target: state.target, focus: true });
            const result = await api.add({
                ...(state.target === null ? {} : { target: state.target }),
                ...(state.loc === null ? {} : { loc: state.loc }),
                body,
            });
            if (!result.ok || result.data === null) {
                // 断られた・届かない: 本文を残す
                Object.assign(state, { status: "failed", detail: result.ok ? null : result.detail });
                // 止めた待ちを戻す（本文を残したまま閉じても、書きかけは保つ）
                scheduleDraft(state);
                redrawForm({ target: state.target, focus: true });
                return;
            }
            // 溜めた: 入力欄と添えた箇所を空にし、結果は箇所を持たない入力に出す
            const added = result.data;
            if (state.loc !== null && state.target !== null) {
                comment.forms.delete(formKey(state.target, state.loc));
                comment.pendingLoc.delete(state.target);
            }
            const shown = formStateOf(state.target, null);
            Object.assign(shown, { status: "saved", count: added.count, detail: null });
            // 箇所を持たない入力を溜めたときだけ本文を空にする（箇所を持つ入力を溜めたときは、別の向けた先の書きかけを残す）
            if (state.loc === null)
                shown.body = "";
            knownIds.add(added.id);
            comment.checked.add(added.id);
            await loadReview();
            refreshComments();
            redrawForm({ target: state.target, focus: true });
        };
        // ===== コメントの一覧 =====
        /** 開いているスレッドの返信の入力の引数（書きかけの本文を含む） */
        const replyState = () => {
            const opened = comment.openedThread;
            // スレッドを開いていない・まだ送っていない新しいスレッド: 返信の入力は出さない
            if (opened === null || opened.pending)
                return { body: "", status: "idle", count: null, detail: null };
            const { body, status, count, detail } = formStateOf(null, null, opened.id);
            return { body, status: status === "empty" ? "idle" : status, count, detail };
        };
        /** 描き直す前に、打っている途中の理由を状態に写す（理由は確定のときにだけ入力部品が知らせるため） */
        const captureTyped = () => {
            const reasonField = document.querySelector(".comments-panel form.th-reason textarea");
            if (reasonField !== null && comment.reason.open)
                comment.reason.body = reasonField.value;
        };
        /** 一覧を作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
        const renderComments = () => {
            const current = document.querySelector(".comments-panel");
            if (!comment.listOpen) {
                current?.remove();
                scheduleInert();
                return;
            }
            captureTyped();
            const active = document.activeElement;
            const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
            // 入力欄（新しいスレッド・返信・理由）に打っている途中なら、選択も保つ
            const typing = active instanceof HTMLTextAreaElement && active.closest(".comments-panel form.send, .comments-panel form.th-reason") !== null
                ? active
                : null;
            const typingForm = typing?.closest("form")?.classList.contains("th-reason") === true ? "form.th-reason" : "form.send";
            const selection = typing === null ? null : { start: typing.selectionStart, end: typing.selectionEnd };
            const scroll = current?.querySelector(".comments-body")?.scrollTop ?? 0;
            const next = MindmapPreview.commentsPanel(panelProps());
            if (current === null) {
                document.body.append(next);
                requestAnimationFrame(() => next.classList.add("open"));
            }
            else {
                current.className = `${next.className} open`;
                current.replaceChildren(...next.children);
            }
            const panel = document.querySelector(".comments-panel");
            const body = panel?.querySelector(".comments-body");
            if (body !== null && body !== undefined)
                body.scrollTop = scroll;
            if (typing !== null && selection !== null) {
                const restored = panel?.querySelector(`${typingForm} textarea`);
                restored?.focus();
                restored?.setSelectionRange(selection.start, selection.end);
            }
            else if (focusKey !== null) {
                panel?.querySelector(`[data-focus="${focusKey}"]`)?.focus();
            }
            scheduleInert();
        };
        /** トップバーの件数・詳細パネルのレビュー中のコメント・一覧を、入力中の欄とスクロールの位置を保って描き直す */
        const refreshComments = () => {
            preserving(() => {
                renderTop();
                renderDetail();
            });
            renderComments();
        };
        /** パネルの中の画面の状態を、開いた直後（スレッドの一覧）に戻す */
        const resetPanelView = () => {
            comment.view = "list";
            comment.reviewFrom = "list";
            comment.openedThread = null;
            comment.composing = false;
            comment.reason = { open: false, body: "", status: "idle", detail: null };
            comment.reviewFocus = null;
        };
        /** コメントの一覧を開く（絞り込みのドロワーは閉じ、スレッドの一覧から始める） */
        const openList = () => {
            // 絞り込みのドロワー・表示の設定のパネルとは 1 つだけを開く
            if (filterState.drawerOpen) {
                filterState.drawerOpen = false;
                redrawKeepingState();
            }
            display.open = false;
            renderSettings();
            editState.open = false;
            renderPending();
            comment.listOpen = true;
            stack.front = "left";
            resetPanelView();
            renderTop();
            renderComments();
            // スレッドを読み直して、届いていた AI の返信などを足す
            void loadThreads().then(renderComments);
        };
        /** 一覧で始めた書き換えを捨てる（一覧を閉じると、詳細パネルの行が本文だけのまま残るため）。捨てたかを返す */
        const discardListEdit = () => {
            if (editing === null || editingIn !== "list")
                return false;
            editing = null;
            editError = null;
            editBody = null;
            return true;
        };
        /** コメントの一覧を閉じる */
        const closeList = () => {
            flushDrafts();
            comment.listOpen = false;
            comment.opened = null;
            comment.highlight = null;
            comment.removed = [];
            comment.expanded.clear();
            discardListEdit();
            renderTop();
            renderComments();
            renderDetail();
        };
        /** 行の向けた項目を、一覧を開いたまま詳細パネルに開く（箇所があればその箇所を示す） */
        const openRow = (item) => {
            if (item.target === null)
                return;
            comment.opened = item.id;
            comment.highlight = null;
            // いま開いている項目を指す行でも、詳細パネルを一覧の前に出す
            stack.front = "detail";
            if (route.id === item.target) {
                renderDetail();
                renderComments();
                return;
            }
            openItem(item.target, false);
            renderComments();
        };
        /** 本文の中の ID・スレッドの向けた項目を、パネルを開いたまま詳細パネルに開く（箇所があればその箇所を示す） */
        const openFromThread = (id, loc) => {
            comment.opened = null;
            comment.highlight = loc === undefined ? null : { target: id, loc };
            // いま開いている項目を指すときでも、詳細パネルをパネルの前に出す
            stack.front = "detail";
            if (route.id === id) {
                renderDetail();
                renderComments();
                return;
            }
            openItem(id, false);
            renderComments();
        };
        /** スレッドを開く。一覧のスクロールの位置を控え、理由の入力は閉じて空にする */
        const openThread = (id, pending) => {
            listScroll = document.querySelector(".comments-panel .comments-body")?.scrollTop ?? 0;
            comment.openedThread = { id, pending };
            comment.view = "thread";
            seenFailed.clear();
            comment.reason = { open: false, body: "", status: "idle", detail: null };
            renderComments();
            markOpenedSeen();
        };
        /** スレッドの返信の書きかけを、待たずに保つ */
        const flushReplyDraft = () => {
            const opened = comment.openedThread;
            if (opened === null || opened.pending)
                return;
            const state = comment.forms.get(formKey(null, null, opened.id));
            if (state !== undefined && draftTimers.has(formKey(null, null, opened.id)))
                saveDraftNow(state);
        };
        /** 一覧・開く前の画面へ戻る（スレッドの画面と、レビュー中の書き込みの画面の「戻る」） */
        const goBack = () => {
            if (comment.view === "thread") {
                flushReplyDraft();
                const opened = comment.openedThread;
                comment.view = "list";
                comment.openedThread = null;
                seenFailed.clear();
                comment.reason = { open: false, body: "", status: "idle", detail: null };
                renderComments();
                // 控えたスクロールの位置と、開いていた行へのフォーカスを戻す
                const body = document.querySelector(".comments-panel .comments-body");
                if (body !== null)
                    body.scrollTop = listScroll;
                if (opened !== null) {
                    const key = opened.pending ? `thread:new:${opened.id}` : `thread:${opened.id}`;
                    document.querySelector(`.comments-panel [data-focus="${key}"]`)?.focus();
                }
                return;
            }
            if (comment.view === "review") {
                const opened = comment.openedThread;
                // 開く前に見ていた、まだ送っていない新しいスレッドが、送るか消すかで無くなっていたら一覧へ戻る
                const gone = comment.reviewFrom === "thread" &&
                    opened !== null &&
                    opened.pending &&
                    !comment.review.items.some((item) => item.id === opened.id) &&
                    !comment.removed.some((item) => item.id === opened.id);
                comment.view = gone ? "list" : comment.reviewFrom;
                if (gone)
                    comment.openedThread = null;
                comment.reviewFocus = null;
                renderComments();
                document.querySelector('.comments-panel [data-focus="review"]')?.focus();
            }
        };
        /** レビュー中の書き込みの画面を開く（開く前の画面を控える） */
        const openReview = () => {
            flushDrafts();
            comment.reviewFrom = comment.view === "thread" ? "thread" : "list";
            const opened = comment.openedThread;
            comment.reviewFocus = comment.view === "thread" && opened !== null && !opened.pending ? opened.id : null;
            comment.view = "review";
            renderComments();
        };
        /** 開いているスレッドの状態を変える（理由は空白だけなら送らない） */
        const changeStatus = async (status, reason) => {
            const opened = comment.openedThread;
            if (opened === null || opened.pending)
                return;
            comment.reason = { open: true, body: reason, status: "saving", detail: null };
            renderComments();
            const result = await threadsApi.setStatus(opened.id, status, reason);
            // 断られた・届かない: 理由の入力を開いたまま、理由を出す
            if (!result.ok) {
                comment.reason = { open: true, body: reason, status: "failed", detail: result.detail };
                renderComments();
                return;
            }
            comment.reason = { open: false, body: "", status: "idle", detail: null };
            await loadThreads();
            renderComments();
            document.querySelector('.comments-panel [data-focus="status"]')?.focus();
        };
        /** 返信を溜める。溜めたらレビュー中を読み直して、パネルを描き直す */
        const saveReply = async (threadId, body) => {
            const state = formStateOf(null, null, threadId);
            state.body = body;
            // 溜める前に、この返信の書きかけを保つ待ちを止める（応答を待つ間にタイマーが切れて、消えた書きかけを書き戻さないため）
            window.clearTimeout(draftTimers.get(formKey(null, null, threadId)));
            draftTimers.delete(formKey(null, null, threadId));
            Object.assign(state, { status: "saving", detail: null });
            renderComments();
            const result = await api.add({ thread: threadId, body });
            if (!result.ok || result.data === null) {
                // 断られた・届かない: 本文を残す
                Object.assign(state, { status: "failed", detail: result.ok ? null : result.detail });
                scheduleDraft(state);
                renderComments();
                return;
            }
            Object.assign(state, { body: "", status: "saved", count: result.data.count, detail: null });
            knownIds.add(result.data.id);
            comment.checked.add(result.data.id);
            await loadReview();
            refreshComments();
            document.querySelector(".comments-panel form.reply textarea")?.focus();
        };
        /** 返信の入力の中身が変わった。書きかけを保つ待ちを入れ、溜めた・失敗の結果は消す */
        const typeReply = (body) => {
            const opened = comment.openedThread;
            if (opened === null || opened.pending)
                return;
            const state = formStateOf(null, null, opened.id);
            state.body = body;
            scheduleDraft(state);
            // 溜めた結果は、入力を始めたら消す（溜められなかった結果は次に溜めるまで残す）
            if (state.status === "saved") {
                state.status = "idle";
                clearSendResult();
            }
        };
        /** コメントの一覧の引数 */
        const panelProps = () => ({
            view: comment.view,
            items: comment.review.items,
            removed: comment.removed,
            threads: comment.threads,
            threadsError: comment.threadsError,
            filter: comment.filter,
            tag: comment.tag,
            opened: comment.openedThread,
            composing: comment.composing,
            free: formProps(null),
            reply: replyState(),
            reason: comment.reason,
            checked: comment.checked,
            editing,
            editingIn,
            editError,
            editBody,
            stale: comment.stale,
            result: outcome,
            selected: comment.opened,
            reviewFocus: comment.reviewFocus,
            titleOf: (id) => index.byId.get(id)?.item.title ?? null,
            changeSetOf: (id) => data.changes.sets.find((set) => set.id === id)?.summary ?? null,
            expanded: comment.expanded,
            on: {
                close: closeList,
                review: openReview,
                back: goBack,
                filter: (filter) => {
                    comment.filter = filter;
                    renderComments();
                },
                tag: (tag) => {
                    comment.tag = comment.tag === tag ? null : tag;
                    renderComments();
                },
                clearTag: () => {
                    comment.tag = null;
                    renderComments();
                },
                compose: (open) => {
                    comment.composing = open;
                    renderComments();
                    // 出したときは入力欄へ、畳んだときは「新しいスレッド」へフォーカスを移す
                    const target = open ? ".comments-panel .talk-new form.send textarea" : '.comments-panel [data-focus="compose"]';
                    document.querySelector(target)?.focus();
                },
                openThread,
                openId: openFromThread,
                changeSet: openChangeSet,
                reply: (thread, body) => void saveReply(thread, body),
                replyInput: typeReply,
                reasonOpen: (open) => {
                    comment.reason = { open, body: "", status: "idle", detail: null };
                    renderComments();
                    const target = open ? '.comments-panel [data-focus="reason"]' : '.comments-panel [data-focus="status"]';
                    document.querySelector(target)?.focus();
                },
                reasonInput: (body) => {
                    comment.reason.body = body;
                },
                setStatus: (status, reason) => void changeStatus(status, reason),
                check: (id, checked) => {
                    if (checked)
                        comment.checked.add(id);
                    else
                        comment.checked.delete(id);
                    renderComments();
                },
                checkAll: (checked) => {
                    comment.checked = checked
                        ? new Set(comment.review.items.filter((item) => !MindmapPreview.isBlockedReply(item, comment.threads)).map((item) => item.id))
                        : new Set();
                    renderComments();
                },
                send: () => void sendChecked(),
                open: openRow,
                ...reviewRowHandlers(""),
                unloc: (id) => void detachLocation(id),
                fold: (id, open) => {
                    // 部品が行の中でその場で切り替えているので、描き直さず覚えるだけにする
                    if (open)
                        comment.expanded.add(id);
                    else
                        comment.expanded.delete(id);
                },
            },
        });
        /** 読み直して一覧まで描き直す */
        const reloadAndRefresh = async () => {
            await loadReview();
            refreshComments();
        };
        /** 行の本文を直す。`toDetail` は詳細パネルから直したときに、描き直した後のフォーカスを移す先を渡す */
        const saveEdit = async (id, body, toDetail) => {
            const result = await api.update(id, { body });
            if (!result.ok) {
                // 断られた・届かない: 入力を残して理由を出す
                editError = result.detail ?? "サーバーが止まっています。立ち上げ直してから直してください。";
                editBody = body;
                refreshComments();
                toDetail(`edit:${id}`);
                return;
            }
            editing = null;
            editError = null;
            editBody = null;
            await reloadAndRefresh();
            toDetail(`edit-open:${id}`);
        };
        /** 行を消す（確認は挟まず、元の場所に「元に戻す」を出す） */
        const removeComment = async (id) => {
            const result = await api.remove(id);
            if (result.ok && result.data !== null) {
                const { count: _count, ...item } = result.data;
                comment.removed = [...comment.removed, item];
                comment.stale.delete(id);
            }
            await reloadAndRefresh();
        };
        /** 消した行を、同じ ID と日時で元の場所に戻す */
        const restoreComment = async (id) => {
            const item = comment.removed.find((entry) => entry.id === id);
            if (item === undefined)
                return;
            const result = await api.add({
                id: item.id,
                created: item.created,
                ...(item.target === null ? {} : { target: item.target }),
                ...(item.loc === null ? {} : { loc: item.loc }),
                ...(item.thread === null ? {} : { thread: item.thread }),
                body: item.body,
            });
            if (result.ok)
                comment.removed = comment.removed.filter((entry) => entry.id !== id);
            await reloadAndRefresh();
        };
        /** 詳細パネルの中の部品へフォーカスを移す（全画面のときは全画面の中） */
        const focusDetail = (key) => {
            const host = route.full ? "dialog.full" : "aside.panel";
            document.querySelector(`${host} [data-focus="${key}"]`)?.focus();
        };
        /** 行の修正・書き換えを送る・キャンセル・削除・元に戻す。コメントの一覧（接頭辞は空）と詳細パネル（`detail-`）で同じ処理を使い、詳細パネルのときだけ、描き直した後のフォーカスを移す */
        const reviewRowHandlers = (focus) => {
            const toDetail = (key) => {
                if (focus !== "")
                    focusDetail(`${focus}${key}`);
            };
            return {
                edit: (id) => {
                    editing = id;
                    editingIn = focus === "" ? "list" : "detail";
                    editError = null;
                    editBody = null;
                    refreshComments();
                    toDetail(`edit:${id}`);
                },
                saveEdit: (id, body) => void saveEdit(id, body, toDetail),
                cancelEdit: () => {
                    const canceled = editing;
                    editing = null;
                    editError = null;
                    editBody = null;
                    refreshComments();
                    if (canceled !== null)
                        toDetail(`edit-open:${canceled}`);
                },
                remove: (id) => void removeComment(id).then(() => toDetail(`restore:${id}`)),
                restore: (id) => void restoreComment(id).then(() => toDetail(`edit-open:${id}`)),
            };
        };
        /** 箇所が合わないコメントから箇所を外し、項目へのコメントにする */
        const detachLocation = async (id) => {
            const result = await api.update(id, { loc: null });
            if (result.ok)
                comment.stale.delete(id);
            await reloadAndRefresh();
        };
        /** チェックしたコメントを溜めた順にまとめて送る */
        const sendChecked = async () => {
            const ids = comment.review.items
                .filter((item) => comment.checked.has(item.id) && !MindmapPreview.isBlockedReply(item, comment.threads))
                .map((item) => item.id);
            // 送るものが無い
            if (ids.length === 0)
                return;
            outcome = { kind: "sending" };
            renderComments();
            const result = await api.send(ids);
            if (result.ok && result.data !== null) {
                comment.removed = [];
                comment.stale = new Map();
                outcome = { kind: "sent", count: ids.length, at: result.data.sent, entered: result.data.entered };
            }
            else if (!result.ok && result.status === 409) {
                comment.stale = new Map(result.stale.map((entry) => [entry.id, entry.reason]));
                outcome = { kind: "stale", count: result.stale.length };
            }
            else {
                outcome = { kind: "failed", detail: result.ok ? null : result.detail };
            }
            await loadThreads();
            await reloadAndRefresh();
        };
        // ===== 選んだ箇所のコメントの入口 =====
        /** 出している入口 */
        let pill = null;
        /** ポインターを押している間は入口を出さない（選び終えてから出す） */
        let pointerHeld = false;
        /** HTML の本文の枠の中で選んでいる範囲（選びを外すと null）。枠の文書の選択は親の文書の選択に入らないので別に持つ */
        let frameSelected = null;
        /** 入口を閉じる */
        const closePill = () => {
            pill?.remove();
            pill = null;
        };
        /** 選んだ箇所と選んだ範囲の矩形の近くに入口を出す。押したら入力に箇所を添える */
        const openPill = ({ loc, anchor, host }) => {
            if (route.id === null)
                return;
            const id = route.id;
            // 上に収まるかを決めるため、本文のスクロール領域の矩形を渡す
            const scroller = host.querySelector(".panel-body") ?? host;
            pill = MindmapPreview.selectionComment({
                anchor,
                area: { viewport: { width: innerWidth, height: innerHeight }, scroller: scroller.getBoundingClientRect() },
                on: {
                    press: () => {
                        closePill();
                        comment.pendingLoc.set(id, loc);
                        redrawForm({ target: id, focus: true });
                    },
                    close: () => {
                        closePill();
                        host.querySelector(".md")?.focus();
                    },
                },
            });
            // 全画面はモーダルなので、入口もその中に置く（外に置くと押せない）
            (host.matches("dialog") ? host : document.body).append(pill);
        };
        /** 図の拡大を開いている間か、詳細パネルの外か（入口を出さない場面） */
        const pillBlocked = () => !serverMode || route.id === null || document.querySelector("dialog.viewer") !== null || fullViewer !== null;
        /** 選んだ範囲から箇所を求め、あれば入口を出し、無ければ閉じる。枠の中の選択が生きていて、親の文書の選択が空のときは、枠の入口をそのままにする */
        const updatePill = () => {
            const selection = getSelection();
            const parentSelected = selection !== null && selection.rangeCount > 0 && !selection.isCollapsed;
            if (!parentSelected && frameSelected !== null)
                return;
            closePill();
            const host = document.querySelector(route.full ? "dialog.full[open]" : "aside.panel");
            // 図の拡大を開いている間・選んだ範囲が無い・詳細パネル（全画面を開いている間は全画面）の外
            if (pillBlocked())
                return;
            if (selection === null || selection.rangeCount === 0 || selection.isCollapsed || host === null)
                return;
            const range = selection.getRangeAt(0);
            if (!host.contains(range.commonAncestorContainer))
                return;
            const loc = MindmapPreview.selectionLocation(range);
            const rects = range.getClientRects();
            const first = rects[0];
            const last = rects[rects.length - 1];
            if (loc === null || first === undefined || last === undefined)
                return;
            openPill({ loc, anchor: { first, last }, host });
        };
        /** HTML の本文の枠で文を選び終えた: 元の HTML の行の範囲の箇所にして入口を出す */
        const frameSelect = (selection) => {
            frameSelected = selection;
            closePill();
            const host = document.querySelector(route.full ? "dialog.full[open]" : "aside.panel");
            if (pillBlocked() || host === null)
                return;
            openPill({
                loc: { kind: "body", start: selection.start, end: selection.end, text: selection.text },
                anchor: selection.rects,
                host,
            });
        };
        /** HTML の本文の枠で選びを外した: 入口を閉じる */
        const frameClear = () => {
            frameSelected = null;
            closePill();
        };
        document.addEventListener("pointerdown", (event) => {
            pointerHeld = true;
            // 枠の外を押したら、枠の中の選択を外す（入口を押したときは外さない）
            if (event.target?.closest?.(".selection-comment") === null || event.target === document) {
                for (const frame of document.querySelectorAll("iframe.html-frame")) {
                    frame.contentWindow?.getSelection()?.removeAllRanges();
                }
            }
        });
        document.addEventListener("pointerup", () => {
            pointerHeld = false;
            window.setTimeout(updatePill, 0);
        });
        document.addEventListener("selectionchange", () => {
            if (!pointerHeld)
                updatePill();
        });
        // ===== 書き換えの知らせ =====
        /** 入力中の欄の選択とスクロールの位置を保って、渡した描き方で描き直す */
        const preserving = (draw) => {
            const field = document.activeElement;
            const form = field instanceof HTMLTextAreaElement ? field.closest("form.send") : null;
            const inList = form !== null && form.closest(".comments-panel") !== null;
            const selection = field instanceof HTMLTextAreaElement && form !== null ? { start: field.selectionStart, end: field.selectionEnd } : null;
            const bodyFocused = field instanceof HTMLElement && field.matches(".panel-body");
            // 編集の表示・設定の画面の入力欄: 溜める前に打った値と選択を、描き直した後の同じ入力欄に戻す
            const typed = (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement) &&
                field.id !== "" &&
                field.closest(".pe-form") !== null
                ? field
                : null;
            const typedState = typed === null
                ? null
                : {
                    id: typed.id,
                    value: typed.value,
                    start: typed instanceof HTMLSelectElement ? null : typed.selectionStart,
                    end: typed instanceof HTMLSelectElement ? null : typed.selectionEnd,
                };
            // 全画面のときは詳細パネルも文書に残るので、今の画面の本文を引く
            const bodySelector = route.full ? "dialog.full .panel-body" : "aside.panel .panel-body";
            const panelScroll = document.querySelector(bodySelector)?.scrollTop ?? 0;
            const pageScroll = window.scrollY;
            draw();
            const panelBody = document.querySelector(bodySelector);
            if (panelBody !== null)
                panelBody.scrollTop = panelScroll;
            if (bodyFocused)
                panelBody?.focus({ preventScroll: true });
            window.scrollTo(0, pageScroll);
            if (typedState !== null) {
                const restored = document.getElementById(typedState.id);
                if (restored instanceof HTMLInputElement || restored instanceof HTMLTextAreaElement || restored instanceof HTMLSelectElement) {
                    const text = !(restored instanceof HTMLInputElement) || !["checkbox", "radio"].includes(restored.type);
                    if (text && restored.value !== typedState.value)
                        restored.value = typedState.value;
                    restored.focus({ preventScroll: true });
                    // 選択を持てない型の入力欄（数・日付など）は、フォーカスだけを戻す
                    try {
                        if (!(restored instanceof HTMLSelectElement) && typedState.start !== null && typedState.end !== null) {
                            restored.setSelectionRange(typedState.start, typedState.end);
                        }
                    }
                    catch {
                        // 選択を持てない型
                    }
                }
            }
            if (selection !== null) {
                const restored = document.querySelector(inList ? ".comments-panel form.send textarea" : route.full ? "dialog.full form.send textarea" : "aside.panel form.send textarea");
                restored?.focus();
                restored?.setSelectionRange(selection.start, selection.end);
            }
        };
        /** 入力中の欄の選択とスクロールの位置を保って、画面を描き直す */
        const redrawKeepingState = () => preserving(() => render({ screen: true }));
        // ===== 表示の設定 =====
        /** 端末の上書きを変えた後に、残して読み分け直し、描き直す。開いている画面の種類を外したときは概要へ移る（履歴に積まない） */
        const changePrefs = ({ redrawMain }) => {
            display.storageOk = persist();
            resolved = resolveDisplay(prefs, data.settings.display);
            const visible = visibleRoute(route);
            const moved = visible !== route;
            if (moved) {
                route = visible;
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
            }
            if (redrawMain || moved)
                redrawKeepingState();
            else
                renderTop();
            renderSettings();
        };
        /** 表示の設定の中身の引数 */
        const settingsProps = () => ({
            look: resolved.look,
            defaultLook: resolved.defaultLook,
            kinds: resolved.kinds,
            defaultKinds: resolved.defaultKinds,
            counts: Object.fromEntries(MindmapPreview.KIND_KEYS.map((kind) => [kind, data[kind].length])),
            overrides: resolved.overrides,
            canSave: serverMode,
            minimap: resolved.minimap,
            bodyView: resolved.bodyView,
            message: display.message,
            storageOk: display.storageOk,
            onWorkspace: serverMode && point === null ? openWorkspace : null,
            on: {
                kinds: (kinds) => {
                    prefs.kinds = kinds;
                    changePrefs({ redrawMain: true });
                },
                // 表示するは上書きを外し、表示しないだけを上書きとして残す。開いている詳細をその場で描き直す
                minimap: (shown) => {
                    prefs.minimap = shown ? null : false;
                    changePrefs({ redrawMain: true });
                },
                // 既定と違う値だけを上書きとして残し、開いている詳細をその場で描き直す
                bodyView: ({ key, value }) => {
                    prefs[BODY_VIEW_PREF[key]] = (value === MindmapPreview.BODY_VIEW_DEFAULT[key] ? null : value);
                    changePrefs({ redrawMain: true });
                },
                reset: () => {
                    // 見た目・表示する種類・ライト / ダーク・表の列・絞り込みの条件・差分のミニマップ・本文の表とセクションの見せ方・本文の差分の並べ方を全て外し、ワークスペースの既定の表示に戻す
                    Object.assign(prefs, clearOverrides(prefs));
                    MindmapPreview.clearTablePrefs();
                    // 開いている画面は、画面の既定の条件で開き直す
                    filterState.byTab = {};
                    theme = systemTheme();
                    document.documentElement.dataset["theme"] = theme;
                    changePrefs({ redrawMain: true });
                    document.querySelector('.settings-drawer [data-focus="over"]')?.focus();
                },
                save: openConfirm,
                close: closeSettings,
            },
        });
        /** 表示の設定のパネルを作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
        const renderSettings = () => {
            const current = document.querySelector(".settings-drawer");
            if (!display.open) {
                current?.remove();
                return;
            }
            const active = document.activeElement;
            const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
            const scroll = current?.querySelector(".st-wrap")?.scrollTop ?? 0;
            const next = MindmapPreview.settingsDrawer({ panel: settingsProps() });
            if (current === null) {
                document.body.append(next);
                requestAnimationFrame(() => next.classList.add("open"));
            }
            else {
                current.className = `${next.className} open`;
                current.replaceChildren(...next.children);
            }
            const panel = document.querySelector(".settings-drawer");
            const wrap = panel?.querySelector(".st-wrap");
            if (wrap !== null && wrap !== undefined)
                wrap.scrollTop = scroll;
            if (focusKey !== null)
                panel?.querySelector(`[data-focus="${focusKey}"]`)?.focus();
        };
        /** 表示の設定のパネルを開く。コメントの一覧と絞り込みのドロワーは閉じ、右の詳細パネルは開いたままにする（履歴に積まない） */
        const openSettings = () => {
            if (comment.listOpen) {
                flushDrafts();
                comment.listOpen = false;
                comment.opened = null;
                comment.highlight = null;
                comment.removed = [];
                comment.expanded.clear();
                renderComments();
                if (discardListEdit())
                    renderDetail();
            }
            editState.open = false;
            renderPending();
            display.open = true;
            stack.front = "left";
            if (filterState.drawerOpen) {
                filterState.drawerOpen = false;
                redrawKeepingState();
            }
            else {
                renderTop();
            }
            renderSettings();
            scheduleInert();
        };
        /** 表示の設定のパネルを閉じ、トップバーのボタンへフォーカスを戻す */
        const closeSettings = () => {
            display.open = false;
            renderTop();
            renderSettings();
            scheduleInert();
            document.querySelector("[data-act='settings']")?.focus();
        };
        // ===== ワークスペースの既定の保存 =====
        /** 既定の保存の確かめを今の状態で描く（開き直して、最初のフォーカスを取り消すに置く） */
        const renderConfirm = () => {
            const old = document.querySelector("dialog.sconfirm");
            old?.close();
            old?.remove();
            if (display.confirm === null)
                return;
            const dialog = MindmapPreview.settingsConfirm({
                from: { look: resolved.defaultLook, kinds: resolved.defaultKinds },
                to: { look: resolved.look, kinds: resolved.kinds },
                busy: display.confirm.busy,
                error: display.confirm.error,
                on: { save: () => void saveDefault(), cancel: closeConfirm },
            });
            document.body.append(dialog);
            dialog.showModal();
        };
        /** 確かめを開く */
        const openConfirm = () => {
            display.confirm = { busy: false, error: null };
            renderConfirm();
        };
        /** 何も書かずに確かめを閉じ、「ワークスペースの既定にする」へフォーカスを戻す */
        const closeConfirm = () => {
            display.confirm = null;
            renderConfirm();
            document.querySelector('.settings-drawer [data-focus="save"]')?.focus();
        };
        /** 今当てている見た目と表示する種類を、ワークスペースの既定として保存する */
        const saveDefault = async () => {
            if (display.confirm === null)
                return;
            display.confirm = { busy: true, error: null };
            renderConfirm();
            const result = await MindmapPreview.putDisplay({
                network_look: resolved.look,
                visible_kinds: MindmapPreview.KIND_KEYS.filter((kind) => resolved.kinds.has(kind)),
            });
            if (!result.ok) {
                // 断られた・届かない: 確かめの中に理由を出し、config.yaml と画面の表示は保存の前のまま
                display.confirm = {
                    busy: false,
                    error: result.detail === null
                        ? "保存できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから保存してください。"
                        : `保存できませんでした。${result.detail}`,
                };
                renderConfirm();
                return;
            }
            // 書けた: 返った既定を記録に入れ、個人の上書きはそのまま残す
            const saved = result.data?.display ?? { network_look: resolved.look, visible_kinds: MindmapPreview.KIND_KEYS.filter((kind) => resolved.kinds.has(kind)) };
            serverData = { ...serverData, settings: { ...serverData.settings, display: saved } };
            rebuildIndex();
            display.savedDisplay = saved;
            display.message = { kind: "ok", text: `ワークスペースの既定にしました（${MindmapPreview.formatJst(new Date().toISOString())}）。` };
            display.confirm = null;
            renderConfirm();
            resolved = resolveDisplay(prefs, data.settings.display);
            redrawKeepingState();
            renderSettings();
            document.querySelector('.settings-drawer [data-focus="same"]')?.focus();
        };
        // ===== 編集と保存待ち（サーバーの配信だけ） =====
        const editsApi = MindmapPreview.editApi();
        /** 直前の保存をサーバーが断った理由（保存待ちのパネルに出す）。次に保存するか、編集を取り消すまで残す */
        let rejected = null;
        /** 幅 900px 以下で保存待ちのパネルから項目を開いたとき、詳細パネルを閉じたらパネルを開き直すか */
        let reopenPending = false;
        /** 保存待ちの編集を読み直す。読み取りには送った順に番号を振り、後から送った読み取りを当てた後に届いた古い結果は当てずに捨てる。読めたときだけ置き換え、書き込めなかった編集の控えは今の編集に残る分だけにする。`edits` がこの読み取り以降の状態になったか（当てた・より新しい結果を当て済み）を返す */
        const loadEdits = async () => {
            editState.editsReadSeq += 1;
            const seq = editState.editsReadSeq;
            const result = await editsApi.read();
            if (!result.ok || result.data === null)
                return false;
            // 後から送った読み取りをもう当てている: この結果は古いので捨てる
            if (seq < editState.editsAppliedSeq)
                return true;
            editState.editsAppliedSeq = seq;
            editState.edits = result.data.items;
            const ids = new Set(editState.edits.map((entry) => entry.id));
            editState.blocked = editState.blocked.filter((entry) => ids.has(entry.id));
            settleSentEdits(seq);
            return true;
        };
        /** 保存待ちの編集が指すキー（送信中の編集の値のキーと同じ形） */
        const sentKeyOfEdit = (entry) => sentKeyOf({ target: entry.target, op: entry.op, key: entry.key ?? "" });
        /** 読み取りを `edits` に当てた後、送信中の値を外す。同じキーで同じ値の編集が載ったキーと、溜められた後に送った読み取り（番号が `settledSeq` 以上）を当てたキーは、値によらず外す（その読み取りがサーバーの今の保存待ちを表す） */
        const settleSentEdits = (seq) => {
            const applied = new Map(editState.edits.map((entry) => [sentKeyOfEdit(entry), JSON.stringify(entry.value)]));
            for (const [sentKey, sent] of [...editState.sentEdits]) {
                const sameValue = applied.get(sentKey) === JSON.stringify(sent.value);
                const settled = sent.settledSeq !== null && seq >= sent.settledSeq;
                if (sameValue || settled)
                    editState.sentEdits.delete(sentKey);
            }
        };
        /** 書き込めなかった編集の ID */
        const blockedIds = () => new Set(editState.blocked.map((entry) => entry.id));
        /** 保存待ちの編集がある項目の印（項目の ID・仮の ID → 印の種類） */
        const editMarks = () => {
            const blocked = blockedIds();
            const marks = {};
            for (const target of new Set(editState.edits.map((entry) => entry.target))) {
                const mark = MindmapPreview.pendingMarkOf({ edits: editState.edits, blocked, target });
                if (mark !== null)
                    marks[target] = mark;
            }
            return marks;
        };
        /** 追加する項目の編集を、一覧の画面に渡す項目にする（`id` は仮の ID） */
        const addedItem = (entry) => ({ id: entry.target, title: "", created: entry.created, updated: entry.created, ...entry.value });
        /** 一覧の画面に渡す編集の入口。配る書き出しと差分の表示中は null */
        const screenEdit = (kind) => {
            if (!serverMode || point !== null)
                return null;
            return {
                marks: editMarks(),
                adds: editState.edits.filter((entry) => entry.op === "item-add" && entry.key === kind).map(addedItem),
                onAdd: () => startAdd(kind),
            };
        };
        /** 編集が指す、項目のキーか案の記号（項目の追加・削除と設定は持たない） */
        const keyOf = (entry) => {
            if (entry.op === "adopt")
                return typeof entry.value === "string" ? entry.value : entry.key;
            if (entry.op === "item-add" || entry.op === "item-remove" || entry.op === "setting")
                return null;
            return entry.key;
        };
        /** 項目のキー・案の記号 → 印の種類。項目の ID には項目の印 */
        const keyMarks = (id) => {
            const blocked = blockedIds();
            const marks = {};
            const own = MindmapPreview.pendingMarkOf({ edits: editState.edits, blocked, target: id });
            if (own !== null)
                marks[id] = own;
            for (const entry of editState.edits.filter((other) => other.target === id)) {
                const key = keyOf(entry);
                if (key === null)
                    continue;
                const mark = MindmapPreview.pendingMarkOf({ edits: editState.edits, blocked, target: id, key });
                if (mark !== null)
                    marks[key] = mark;
            }
            return marks;
        };
        /** 項目のキー・案の記号 → 直前の保存で書き込めなかった編集 */
        const blockedByKey = (id) => {
            const byId = new Map(editState.blocked.map((entry) => [entry.id, entry]));
            const result = {};
            for (const entry of editState.edits) {
                const blocked = byId.get(entry.id);
                const key = keyOf(entry);
                if (entry.target === id && blocked !== undefined && key !== null)
                    result[key] = blocked;
            }
            return result;
        };
        /** 向け先の、キー → 溜められなかった理由 */
        const formErrors = (target) => {
            const prefix = `${target}:`;
            return Object.fromEntries([...editState.errors].filter(([key]) => key.startsWith(prefix)).map(([key, text]) => [key.slice(prefix.length), text]));
        };
        /** 溜められなかった理由の文（届かないとき・断られたとき） */
        const failureText = (result) => result.status === null
            ? "サーバーにつながらないため、溜められませんでした。"
            : `溜められませんでした。${result.detail ?? ""}`;
        /** 編集を溜めた後の描き直し（入力中の欄・スクロールの位置を保つ。ネットワークは作り直さない） */
        const redrawEdit = () => preserving(() => render({ screen: route.tab !== "graph" }));
        /** 編集 1 件を溜める。溜められたら保存待ちの編集を読み直して描き直し、断られた・届かないときは入力を残して理由を持つ。溜められたときは返った結果を返す */
        const submitEdit = async ({ payload, error, after, }) => {
            const errorKey = `${error.target}:${error.key}`;
            // 送る値を送信中として持つ（項目の追加・削除と案の追加は除く）。読み取りに載るまで、描き直しで入力欄に重ねる
            const sentKey = payload.op === "item-add" || payload.op === "option-add" || payload.op === "item-remove"
                ? null
                : sentKeyOf({ target: payload.target ?? MindmapPreview.SETTINGS_TARGET, op: payload.op, key: payload.key ?? "" });
            const sentValue = payload.value;
            if (sentKey !== null)
                editState.sentEdits.set(sentKey, { value: sentValue, settledSeq: null });
            const result = await editsApi.add(payload);
            if (!result.ok || result.data === null) {
                // 断られた・届かない: 送信中の値は外さず、理由と一緒に入力欄に残す
                editState.errors.set(errorKey, result.ok ? "溜められませんでした。" : failureText(result));
                redrawEdit();
                return null;
            }
            editState.errors.delete(errorKey);
            // 溜められた: 値が入れたままなら、この後に送る読み取りを当てたときに外す（その間に入れ直した値は、その値の結果を待つ）
            const sent = sentKey === null ? undefined : editState.sentEdits.get(sentKey);
            if (sent !== undefined && sent.value === sentValue)
                sent.settledSeq = editState.editsReadSeq + 1;
            await loadEdits();
            after?.(result.data);
            rebuildIndex();
            redrawEdit();
            return result.data;
        };
        /** 案の編集の理由は、案の入力の下にまとめて出す */
        const errorKeyOf = (input) => ["option-add", "option-edit", "option-remove", "adopt"].includes(input.op) ? "options" : (input.key ?? "");
        /** 項目の削除の編集を外す */
        const cancelRemoval = async (id) => {
            const found = editState.edits.find((entry) => entry.target === id && entry.op === "item-remove");
            if (found !== undefined)
                await undoEdit(found.id);
        };
        /** 編集 1 件を保存待ちから外す。外したら、書き込めなかった編集の控えからも外す */
        const undoEdit = async (id) => {
            const result = await editsApi.remove(id);
            if (!result.ok) {
                if (result.status === null)
                    editState.status = "offline";
                renderPending();
                return;
            }
            const gone = new Set(result.data?.removed ?? [id]);
            editState.blocked = editState.blocked.filter((entry) => !gone.has(entry.id));
            // 外した編集と同じキーの送信中の値も外す
            for (const entry of editState.edits.filter((other) => gone.has(other.id)))
                editState.sentEdits.delete(sentKeyOfEdit(entry));
            if (editState.blocked.length === 0 && editState.status === "idle")
                rejected = null;
            await loadEdits();
            rebuildIndex();
            redrawEdit();
        };
        /** 書きかけの案を持つ編集の表示（`editing`。仮の ID が振られる前の追加の入力は `NEW_ID_PREFIX`） */
        const draftView = () => editState.editing ?? (editState.adding !== null ? MindmapPreview.NEW_ID_PREFIX : null);
        /** 書きかけの案を最後に描いた編集の表示。変わっていたら書きかけを空にする */
        let draftsShownFor = null;
        /** 向け先の書きかけの案。`editing` が変わった（差分の表示に移った・保存できたときを含む）ら、先に書きかけを空にする */
        const draftsOf = (target) => {
            const view = draftView();
            if (view !== draftsShownFor) {
                editState.optionDrafts.clear();
                draftsShownFor = view;
            }
            return editState.optionDrafts.get(target) ?? [];
        };
        /** 書きかけの案を置く・書き換える。置いたときだけ描き直し、その案の中身の入力欄へフォーカスを移す（打つたびには描き直さない） */
        const putDraft = (target, draft) => {
            const drafts = editState.optionDrafts.get(target) ?? [];
            const found = drafts.find((other) => other.key === draft.key);
            if (found !== undefined) {
                found.content = draft.content;
                return;
            }
            editState.optionDrafts.set(target, [...drafts, { ...draft }]);
            redrawEdit();
            document.getElementById(`pe-${MindmapPreview.safeId(target)}-opt-${draft.key}`)?.focus();
        };
        /** その記号の案を溜められた: 書きかけから外す */
        const dropDraft = (target, key) => {
            const rest = (editState.optionDrafts.get(target) ?? []).filter((draft) => draft.key !== key);
            if (rest.length === 0)
                editState.optionDrafts.delete(target);
            else
                editState.optionDrafts.set(target, rest);
        };
        /** 詳細パネルの編集の表示の引数 */
        const editFormProps = ({ id, kind, item }) => {
            const own = editState.edits.filter((entry) => entry.target === id);
            return {
                kind,
                item,
                settings: index.data.settings,
                marks: keyMarks(id),
                removing: own.some((entry) => entry.op === "item-remove"),
                removedOptions: own.filter((entry) => entry.op === "option-remove").map((entry) => entry.key ?? ""),
                blocked: blockedByKey(id),
                referrers: serverIndex.referencedBy.get(id) ?? [],
                errors: formErrors(id),
                usedTags: MindmapPreview.usedTags({ index, threads: comment.threads }),
                body: index.data.bodies[item.body ?? ""] ?? "",
                optionDrafts: draftsOf(id),
                on: {
                    change: (input) => void submitEdit({
                        payload: { target: id, ...input },
                        error: { target: id, key: errorKeyOf(input) },
                        after: () => {
                            if (input.op === "option-add")
                                dropDraft(id, input.key);
                        },
                    }),
                    remove: () => void submitEdit({ payload: { target: id, op: "item-remove" }, error: { target: id, key: "" } }),
                    cancelRemove: () => void cancelRemoval(id),
                    draft: (draft) => putDraft(id, draft),
                },
            };
        };
        /** 詳細パネルの編集の入口。配る書き出し・差分の表示中は null */
        const detailEdit = () => {
            if (!serverMode || point !== null || route.id === null)
                return null;
            const id = route.id;
            const entry = index.byId.get(id);
            if (entry === undefined)
                return null;
            return {
                editing: editState.editing === id,
                marks: keyMarks(id),
                form: editFormProps({ id, kind: entry.kind, item: entry.item }),
                onToggle: () => toggleEdit(id),
            };
        };
        /** 「編集する」「編集を終える」。編集の表示にしたときは最初の入力欄へ、読む表示に戻したときは「編集する」へフォーカスを移す */
        const toggleEdit = (id) => {
            editState.editing = editState.editing === id ? null : id;
            redrawEdit();
            const host = route.full ? "dialog.full" : "aside.panel";
            if (editState.editing === id)
                document.querySelector(`${host} [data-first]`)?.focus();
            else
                document.querySelector(`${host} [data-act="edit"]`)?.focus();
        };
        // ----- 項目を追加する入力 -----
        /** 項目を追加する入力を開いているか（タイトルを書く前の入力と、仮の ID を振られた項目の入力） */
        const isAdding = () => serverMode && point === null && (editState.adding !== null || (editState.editing?.startsWith(MindmapPreview.NEW_ID_PREFIX) ?? false));
        /** 追加する入力の項目の種類 */
        const addingKind = () => {
            if (editState.adding !== null)
                return editState.adding;
            const entry = editState.edits.find((other) => other.op === "item-add" && other.target === editState.editing);
            return entry === undefined ? null : (entry.key ?? "");
        };
        /** 今日の日付（JST の `YYYY-MM-DD`。会話ログの日付の初期値） */
        const todayJst = () => new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
        /** 設定の画面と追加の入力を閉じる（画面・項目を移るとき） */
        const leaveEditViews = () => {
            editState.workspaceOpen = false;
            if (editState.adding !== null || editState.editing?.startsWith(MindmapPreview.NEW_ID_PREFIX) === true) {
                editState.adding = null;
                editState.editing = null;
                editState.addSend = null;
            }
        };
        /** 追加の入力の最初の入力欄（タイトル）へフォーカスを移す */
        const focusAddInput = () => document.querySelector("aside.pe-add-panel [data-first]")?.focus();
        /** 「項目を追加」。開いていた詳細パネルを閉じ、空の項目の入力を詳細パネルと同じ置き方で開く */
        const startAdd = (kind) => {
            flushDrafts();
            editState.workspaceOpen = false;
            editState.adding = kind;
            editState.editing = null;
            editState.addSend = newAddSend({ kind, target: null, value: null });
            editState.optionDrafts.clear();
            if (route.id !== null) {
                route = { ...route, id: null, full: false, filters: {}, heading: null };
                MindmapPreview.navigate({ route, push: false });
            }
            redrawEdit();
            focusAddInput();
        };
        /** 追加する項目（仮の ID）を、追加の入力で開く */
        const openAdded = (target) => {
            flushDrafts();
            editState.workspaceOpen = false;
            editState.adding = null;
            editState.editing = target;
            // 保存待ちのその `item-add` の値から送信の並びを作る
            const entry = editState.edits.find((other) => other.op === "item-add" && other.target === target);
            editState.addSend =
                entry === undefined
                    ? null
                    : newAddSend({ kind: (entry.key ?? ""), target, value: { ...entry.value } });
            if (route.id !== null) {
                route = { ...route, id: null, full: false, filters: {}, heading: null };
                MindmapPreview.navigate({ route, push: false });
            }
            redrawEdit();
            focusAddInput();
        };
        /** 追加の入力を閉じる。タイトルを書いていなければ何も溜めていない */
        const closeAdd = () => {
            editState.adding = null;
            editState.editing = null;
            editState.addSend = null;
            redrawEdit();
            reopenPendingPanel();
        };
        /** 足す項目の案の操作を、`value` の `options` に当てる（`adopt` では選んだ案だけを採用にし、状態を決定済みにする） */
        const applyAddOption = ({ value, input }) => {
            let options = (value["options"] ?? []).map((option) => ({ ...option }));
            const content = input.value?.content ?? "";
            switch (input.op) {
                case "option-add":
                    options.push({ key: input.key, content });
                    break;
                case "option-edit":
                    for (const option of options)
                        if (option.key === input.key)
                            option.content = content;
                    break;
                case "option-remove":
                    options = options.filter((option) => option.key !== input.key);
                    break;
                case "adopt":
                    // 選んだ案だけを採用にする（採用を外すときは全て外す）
                    for (const option of options) {
                        if (option.key === input.value)
                            option.adopted = true;
                        else
                            delete option.adopted;
                    }
                    if (input.value !== null)
                        value["status"] = ADOPTED_DECISION_STATUS;
                    break;
                default:
                    return;
            }
            if (options.length === 0)
                delete value["options"];
            else
                value["options"] = options;
        };
        /** 送信の並びの、最初の `item-add` が断られた・届かなかった回数（その前に積んだ入力は送らずに書く前の入力に残す） */
        const firstAddFailures = new WeakMap();
        /** 追加の入力を開いたときの送信の並び */
        const newAddSend = ({ kind, target, value }) => ({
            kind,
            target,
            value,
            draft: {},
            tail: Promise.resolve(),
        });
        /** 追加の入力でキーを書いたとき。送信の並びに積み、前の送信が終わってから順に送る */
        const submitAddField = async ({ input }) => {
            const send = editState.addSend;
            if (send === null)
                return;
            const failuresAtQueue = firstAddFailures.get(send) ?? 0;
            send.tail = send.tail.then(() => sendAddField({ send, input, failuresAtQueue }));
            await send.tail;
        };
        /** 並びの 1 件を送る。タイトルを書くまでは溜めず、書いたら `item-add` を溜め（返った仮の ID を並びに持つ）、続くキーと案の操作は並びの最後に溜められた `value` に当てて同じ `item-add` を送り直す */
        const sendAddField = async ({ send, input, failuresAtQueue, }) => {
            const target = send.target;
            const next = { ...(send.value ?? { ...MindmapPreview.addDefaults({ kind: send.kind, today: todayJst() }), ...send.draft }) };
            // 案の操作は案の並びに当て、それ以外はキーの値を書き換える
            if (input.op !== "set")
                applyAddOption({ value: next, input });
            else if (input.value === null)
                delete next[input.key];
            else
                next[input.key] = input.value;
            if (target === null) {
                send.draft = next;
                const title = next["title"];
                // タイトルを書くまでは溜めない。待っていた最初の `item-add` が断られた・届かなかったときも送らずに残す
                if (typeof title !== "string" || title.trim() === "")
                    return;
                if ((firstAddFailures.get(send) ?? 0) > failuresAtQueue)
                    return;
            }
            const result = await submitEdit({
                payload: { ...(target === null ? {} : { target }), op: "item-add", key: send.kind, value: next },
                error: { target: target ?? MindmapPreview.NEW_ID_PREFIX, key: errorKeyOf(input) },
                after: (added) => {
                    send.value = next;
                    if (target !== null) {
                        if (input.op === "option-add")
                            dropDraft(target, input.key);
                        return;
                    }
                    send.target = added.target;
                    send.draft = {};
                    // 並びの追加の入力を閉じた・別の追加を始めた後は、開いている入力を書き換えない
                    if (editState.addSend !== send)
                        return;
                    editState.editing = added.target;
                    editState.adding = null;
                    // 仮の ID が振られた: 振られる前の書きかけの案を仮の ID へ移す（書きかけは空にしない）
                    const drafts = editState.optionDrafts.get(MindmapPreview.NEW_ID_PREFIX);
                    editState.optionDrafts.delete(MindmapPreview.NEW_ID_PREFIX);
                    if (drafts !== undefined)
                        editState.optionDrafts.set(added.target, drafts);
                    draftsShownFor = added.target;
                    // 溜めた案と同じ記号の書きかけは外す
                    for (const option of next["options"] ?? [])
                        dropDraft(added.target, option.key);
                },
            });
            if (result === null && target === null)
                firstAddFailures.set(send, (firstAddFailures.get(send) ?? 0) + 1);
        };
        /** 追加の入力のパネルを描く（詳細パネルと同じ形と置き場所） */
        const renderAddPanel = () => {
            const kind = addingKind();
            if (kind === null)
                return;
            const entry = editState.edits.find((other) => other.op === "item-add" && other.target === editState.editing);
            const item = entry === undefined
                ? { id: MindmapPreview.NEW_ID_PREFIX, title: "", created: "", updated: "", ...MindmapPreview.addDefaults({ kind, today: todayJst() }), ...(editState.addSend?.draft ?? {}) }
                : addedItem(entry);
            const record = item;
            const form = MindmapPreview.detailEditForm({
                kind,
                item,
                settings: index.data.settings,
                marks: entry === undefined ? {} : keyMarks(item.id),
                removing: false,
                removedOptions: [],
                blocked: entry === undefined ? {} : blockedByKey(item.id),
                referrers: [],
                errors: formErrors(entry === undefined ? MindmapPreview.NEW_ID_PREFIX : item.id),
                usedTags: MindmapPreview.usedTags({ index, threads: comment.threads }),
                body: typeof record["body"] === "string" ? record["body"] : "",
                optionDrafts: draftsOf(item.id),
                on: {
                    change: (input) => void submitAddField({ input }),
                    remove: () => undefined,
                    cancelRemove: () => undefined,
                    draft: (draft) => putDraft(item.id, draft),
                },
            });
            const body = MindmapPreview.h({
                tag: "div",
                attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "追加する項目の入力" },
                children: [form],
            });
            const panel = MindmapPreview.h({
                tag: "aside",
                attrs: { class: "panel open pe-add-panel pe-editing", "aria-label": `${MindmapPreview.KIND_LABEL[kind]}を追加` },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "panel-head" },
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: closeAdd },
                                children: [MindmapPreview.icon("back")],
                            }),
                            MindmapPreview.h({
                                tag: "span",
                                attrs: { class: "panel-kind" },
                                children: [MindmapPreview.h({ tag: "span", attrs: { class: "panel-kind-label" }, children: [`${MindmapPreview.KIND_LABEL[kind]}を追加`] })],
                            }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { class: "icon-btn panel-close-x", type: "button", "aria-label": "追加の入力を閉じる", onclick: closeAdd },
                                children: [MindmapPreview.icon("x")],
                            }),
                        ],
                    }),
                    MindmapPreview.diffMinimapFrame({ body, shown: false }),
                ],
            });
            const current = document.querySelector("aside.pe-add-panel");
            if (current === null) {
                document.body.append(panel);
            }
            else {
                current.className = panel.className;
                current.setAttribute("aria-label", panel.getAttribute("aria-label") ?? "");
                current.replaceChildren(...panel.children);
            }
        };
        // ----- 保存待ちのパネル -----
        /** 保存待ちのパネルの引数 */
        const pendingProps = () => ({
            edits: editState.edits,
            blocked: editState.blocked,
            index: serverIndex,
            status: editState.status,
            rejected,
            on: {
                close: closePending,
                open: openPendingTarget,
                undo: (id) => void undoFromPanel(id),
                save: () => void saveEdits(),
            },
        });
        /** 保存待ちのパネルを作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
        const renderPending = () => {
            const current = document.querySelector(".pending-panel");
            if (!editState.open || point !== null || !serverMode) {
                current?.remove();
                return;
            }
            const active = document.activeElement;
            const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
            const scroll = current?.querySelector(".comments-body")?.scrollTop ?? 0;
            const next = MindmapPreview.pendingEditsPanel(pendingProps());
            if (current === null) {
                document.body.append(next);
                // 開いた状態にしてから見出しへフォーカスを移す（閉じている間は隠れていて、フォーカスを受けない）
                requestAnimationFrame(() => {
                    next.classList.add("open");
                    next.querySelector("h2")?.focus();
                });
            }
            else {
                current.className = `${next.className} open`;
                current.replaceChildren(...next.children);
            }
            const panel = document.querySelector(".pending-panel");
            const body = panel?.querySelector(".comments-body");
            if (body !== null && body !== undefined)
                body.scrollTop = scroll;
            if (focusKey !== null)
                panel?.querySelector(`[data-focus="${focusKey}"]`)?.focus();
        };
        /** 保存待ちのパネルを開く・閉じる。開くときはコメントの一覧・表示の設定・絞り込みのドロワーを閉じる */
        const togglePending = () => {
            if (editState.open) {
                closePending();
                return;
            }
            if (comment.listOpen)
                closeList();
            if (display.open) {
                display.open = false;
                renderSettings();
            }
            if (filterState.drawerOpen)
                filterState.drawerOpen = false;
            editState.open = true;
            stack.front = "left";
            reopenPending = false;
            redrawKeepingState();
        };
        /** 保存待ちのパネルを閉じ、トップバーの保存待ちのボタンへフォーカスを戻す（保存待ちの編集は残る） */
        const closePending = () => {
            editState.open = false;
            reopenPending = false;
            renderTop();
            renderPending();
            scheduleInert();
            document.querySelector("[data-act='pending']")?.focus();
        };
        /** 幅 900px 以下で保存待ちのパネルから開いた項目の詳細パネルを閉じたら、保存待ちのパネルを開き直す */
        const reopenPendingPanel = () => {
            if (!reopenPending || route.id !== null || isAdding())
                return;
            reopenPending = false;
            editState.open = true;
            stack.front = "left";
            renderTop();
            renderPending();
            scheduleInert();
        };
        /** 保存待ちのパネルのまとまりの項目を開く。項目は詳細パネルを編集の表示で、追加する項目は追加の入力で、設定は設定の画面で開く（幅 900px 以下ではパネルを閉じ、詳細パネルを閉じたら開き直す） */
        const openPendingTarget = (target) => {
            if (isNarrow()) {
                editState.open = false;
                reopenPending = true;
            }
            if (target === MindmapPreview.SETTINGS_TARGET) {
                openWorkspace();
                return;
            }
            if (target.startsWith(MindmapPreview.NEW_ID_PREFIX)) {
                openAdded(target);
                return;
            }
            editState.editing = target;
            stack.front = "detail";
            if (route.id === target)
                redrawEdit();
            else
                openItem(target, false);
            document.querySelector(`${route.full ? "dialog.full" : "aside.panel"} [data-first]`)?.focus();
        };
        /** パネルの「取り消す」。外した後は次の行の取り消すボタン（無ければ見出し）へフォーカスを移す */
        const undoFromPanel = async (id) => {
            const before = [...document.querySelectorAll(".pending-panel .pe-undo")];
            const at = before.findIndex((button) => button.dataset["focus"] === `undo:${id}`);
            await undoEdit(id);
            const after = [...document.querySelectorAll(".pending-panel .pe-undo")];
            (after[at] ?? after[at - 1] ?? document.querySelector(".pending-panel h2"))?.focus();
        };
        /** 保存待ちの編集をまとめて保存する。全て書けたらパネルを閉じて知らせを出し、書き込めない編集があれば何も保存せずにその旨を出し、届かなければ `offline` にする */
        const saveEdits = async () => {
            if (editState.edits.length === 0 || editState.status === "saving")
                return;
            const count = editState.edits.length;
            editState.status = "saving";
            rejected = null;
            renderPending();
            const result = await editsApi.save();
            if (result.ok) {
                editState.blocked = [];
                editState.sentEdits.clear();
                editState.open = false;
                editState.editing = null;
                editState.adding = null;
                editState.errors.clear();
                editState.status = "idle";
                editState.toast = `${count} 件を保存しました。`;
                await reload();
                showSavedNotice(count);
                return;
            }
            if (result.status === 409 && result.blocked !== undefined) {
                editState.blocked = result.blocked;
                editState.status = "idle";
                editState.open = true;
                redrawEdit();
                document.querySelector('.pending-panel [data-focus="alert"]')?.focus();
                return;
            }
            // 届かない: 保存待ちの編集は残し、次に保存するまで `offline` のままにする。断られた: その理由を出す
            editState.status = result.status === null ? "offline" : "idle";
            if (result.status !== null)
                rejected = result.detail ?? "";
            editState.open = true;
            redrawEdit();
            document.querySelector('.pending-panel [data-focus="alert"]')?.focus();
        };
        /** 保存した知らせを画面の下に出し、`SAVED_NOTICE_MS` 経ったら消す */
        const showSavedNotice = (count) => {
            document.querySelector(".pe-toast")?.remove();
            const notice = MindmapPreview.savedNotice({ count });
            document.body.append(notice);
            window.setTimeout(() => {
                notice.remove();
                editState.toast = null;
            }, MindmapPreview.SAVED_NOTICE_MS);
        };
        // ----- 設定の画面 -----
        /** 設定の画面の引数 */
        const workspaceProps = () => {
            const blocked = blockedIds();
            const marks = {};
            for (const entry of editState.edits) {
                if (entry.target !== MindmapPreview.SETTINGS_TARGET || entry.key === null)
                    continue;
                const mark = MindmapPreview.pendingMarkOf({ edits: editState.edits, blocked, target: MindmapPreview.SETTINGS_TARGET, key: entry.key });
                if (mark !== null)
                    marks[entry.key] = mark;
            }
            return {
                settings: index.data.settings,
                index,
                marks,
                errors: formErrors(MindmapPreview.SETTINGS_TARGET),
                on: {
                    change: (input) => void submitEdit({
                        payload: { op: "setting", ...input },
                        error: { target: MindmapPreview.SETTINGS_TARGET, key: input.key },
                    }),
                    close: closeWorkspace,
                },
            };
        };
        /** 設定の画面を描く（開いている間は本文の区画を置き換える）。閉じている間は作らない */
        const renderWorkspace = () => {
            const current = document.querySelector(".pe-ws");
            const show = serverMode && point === null && editState.workspaceOpen;
            main.hidden = show;
            if (!show) {
                current?.remove();
                return;
            }
            const next = MindmapPreview.workspaceSettings(workspaceProps());
            if (current === null)
                main.after(next);
            else
                current.replaceWith(next);
        };
        /** 表示の設定のパネルの「設定を編集する」。表示の設定は閉じ、設定の画面を開く（幅 900px 以下では保存待ちのパネルも閉じる） */
        const openWorkspace = () => {
            display.open = false;
            renderSettings();
            if (isNarrow())
                editState.open = false;
            editState.workspaceOpen = true;
            editState.editing = null;
            redrawKeepingState();
            document.querySelector(".pe-ws h1")?.focus();
        };
        /** 設定の画面を閉じ、開く前の画面へ戻る（溜めた編集は保存待ちに残る） */
        const closeWorkspace = () => {
            editState.workspaceOpen = false;
            redrawKeepingState();
            document.querySelector("[data-act='settings']")?.focus();
        };
        // ===== 変更履歴と差分の表示 =====
        /** 選んだ時点を変えて残し、どの画面もその時点の差分の表示で描き直す（記録は読み直さず、履歴に積まない）。null は差分の表示をやめる */
        const selectPoint = (sel) => {
            prefs.diffSel = sel;
            persist();
            point = MindmapPreview.resolveDiffPoint(data.changes, sel, since);
            syncEditView();
            // 選んだ時点を共有できるよう、履歴に積まずにハッシュへ書く
            route = { ...route, diff: sel };
            MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
            redrawKeepingState();
        };
        /** 本文・書き込みのまとまりのリンクを押した: 記録にあるまとまりのときだけ、変更履歴で選んだときと同じに切り替える */
        const openChangeSet = (id) => {
            if (MindmapPreview.resolveDiffPoint(data.changes, id, since) !== null)
                selectPoint(id);
        };
        /** 変更履歴のモーダルを開く（開いているときは何もしない） */
        const openHistory = () => {
            if (document.querySelector("dialog.hist") !== null)
                return;
            const dialog = MindmapPreview.historyDialog({
                points: historyPoints({ changes: data.changes, since }),
                current: point?.sel ?? "",
                onPick: (sel) => selectPoint(sel === "" ? null : sel),
                // 選ばずに閉じたときも、選んだときも、「変更履歴」のボタンへフォーカスを戻す
                onClose: () => document.querySelector("[data-act='hist']")?.focus(),
            });
            document.body.append(dialog);
            dialog.showModal();
        };
        /** 流している読み直し（終わるまで、続けて頼まれた読み直しを 1 回にまとめて待たせる） */
        let reloading = null;
        /** 流している間に読み直しを頼まれたか */
        let reloadQueued = false;
        /** 記録を読み直して描き直す。読み直しは 1 回ずつ順に流し、流している間に頼まれたら、終わった後にもう 1 回だけ読み直す（その間に続けて頼まれた分は 1 回にまとめる）。返す Promise は頼んだ分の読み直しが終わると解決する */
        const reload = () => {
            if (reloading !== null) {
                reloadQueued = true;
                return reloading;
            }
            reloading = (async () => {
                try {
                    do {
                        reloadQueued = false;
                        await reloadOnce();
                    } while (reloadQueued);
                }
                finally {
                    reloading = null;
                }
            })();
            return reloading;
        };
        /** 記録を 1 回読み直して描き直す。読み直しが読めないとき（422 など）は描き直さない */
        const reloadOnce = async () => {
            const result = await MindmapPreview.fetchRecords();
            if (!result.ok)
                return;
            await loadReview();
            await loadThreads();
            await loadEdits();
            const previousDisplay = serverData.settings.display;
            serverData = result.data;
            rebuildIndex();
            // ロックした項目が無くなっていれば、ロックを外す
            if (lockState.graph !== null && !index.byId.has(lockState.graph))
                lockState.graph = null;
            if (lockState.map !== null && index.byId.get(lockState.map)?.kind !== "decisions")
                lockState.map = null;
            // 表示の既定が変わった: 上書きを持たない項目に新しい既定を当て、知らせる（自分が既定にした直後の知らせは出さない）
            if (display.savedDisplay !== null && sameDisplay(display.savedDisplay, data.settings.display)) {
                display.savedDisplay = null;
            }
            else if (!sameDisplay(previousDisplay, data.settings.display)) {
                display.savedDisplay = null;
                MindmapPreview.settingsNotice({ durationMs: MindmapPreview.NOTICE_MS });
                display.message = { kind: "info", text: `ワークスペースの既定が変わりました（${MindmapPreview.formatJst(new Date().toISOString())}）。` };
            }
            resolved = resolveDisplay(prefs, data.settings.display);
            // 開いていた画面の種類が表示しない種類になった: 概要へ移る
            const visible = visibleRoute(route);
            if (visible !== route) {
                route = visible;
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
            }
            // 選んだ時点と「前回開いてから」の始まりは保ち、新しい記録で印を引き直す
            point = MindmapPreview.resolveDiffPoint(data.changes, prefs.diffSel ?? null, since);
            // 選んだ時点が引けなくなった（まとまりが消えた・まだまとめていない変更が空になった）: 差分を出さず、ハッシュからも外す
            if (point === null && route.diff !== null) {
                prefs.diffSel = null;
                persist();
                route = { ...route, diff: null };
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
            }
            // 差分の表示に移っていれば保存待ちの編集は当てず、そうでなければ当て直す
            syncEditView();
            document.title = `${data.settings.summary} | mindstella`;
            // 開いていた項目が消えた: 詳細パネルを閉じる
            if (route.id !== null && !index.byId.has(route.id)) {
                route = { ...route, id: null, full: false, filters: {}, heading: null };
                MindmapPreview.navigate({ route, push: false });
            }
            redrawKeepingState();
            renderComments();
            renderSettings();
        };
        // ===== 操作と履歴 =====
        /** コメントの一覧の Esc。入力欄に打っている間は入力欄から外れるだけにし（パネルは動かさない）、スレッド・レビュー中の書き込みの画面では戻り、一覧ならパネルを閉じる */
        const closeListByEscape = () => {
            const active = document.activeElement;
            if (MindmapPreview.isTyping(active)) {
                if (active instanceof HTMLElement)
                    active.blur();
            }
            else if (comment.view === "list") {
                closeList();
            }
            else {
                goBack();
            }
        };
        document.addEventListener("keydown", (event) => {
            // L: ネットワークで、詳細を開いている項目をもう一度押したのと同じ規則でロックを付け外しする。修飾キーがあるとき・変換中・入力欄にフォーカスがあるとき・重ねる面を開いているときは受けない
            if (event.key.toLowerCase() === "l" &&
                !event.ctrlKey &&
                !event.altKey &&
                !event.metaKey &&
                !event.isComposing &&
                !MindmapPreview.isTyping(document.activeElement) &&
                document.querySelector("dialog[open]") === null &&
                document.querySelector(":popover-open") === null &&
                matchMedia(MindmapPreview.LOCK_QUERY).matches &&
                route.tab === "graph" &&
                route.id !== null) {
                if (lockPress({ key: "graph", pressed: route.id }) === "shake")
                    MindmapPreview.shakeGraphKey();
            }
            // Ctrl+K（macOS は Cmd+K）で全体の検索を開く。入力欄に入力中でも開き、開いているときは検索の言葉を選び直す
            if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "k") {
                event.preventDefault();
                const opened = document.querySelector("dialog.search input");
                if (opened !== null)
                    opened.select();
                else
                    openSearch();
            }
            // Esc: 幅 900px 以下で左のパネルを前に出しているときは、その左のパネルから閉じる（詳細パネルは閉じない）。重ねる面が無いときは、詳細パネルを閉じる
            if (event.key === "Escape" &&
                isLeftFront() &&
                document.querySelector("dialog[open]:not(.drawer)") === null &&
                document.querySelector(":popover-open") === null) {
                if (filterState.drawerOpen)
                    closeDrawer();
                else if (comment.listOpen)
                    closeListByEscape();
                else if (editState.open)
                    closePending();
                else
                    closeSettings();
            }
            else if (event.key === "Escape" &&
                route.id !== null &&
                !route.full &&
                document.querySelector("dialog[open]:not(.drawer)") === null &&
                document.querySelector(":popover-open") === null) {
                closeDetail();
            }
            else if (event.key === "Escape" &&
                route.id === null &&
                comment.listOpen &&
                document.querySelector("dialog[open]:not(.drawer)") === null &&
                document.querySelector(":popover-open") === null) {
                closeListByEscape();
            }
            else if (event.key === "Escape" &&
                route.id === null &&
                editState.open &&
                document.querySelector("dialog[open]:not(.drawer)") === null &&
                document.querySelector(":popover-open") === null) {
                closePending();
            }
            else if (event.key === "Escape" &&
                isAdding() &&
                document.querySelector("dialog[open]:not(.drawer)") === null &&
                document.querySelector(":popover-open") === null) {
                // 入力欄に打っている間は入力欄から外れるだけにし、追加の入力は閉じない
                if (MindmapPreview.isTyping(document.activeElement))
                    document.activeElement.blur();
                else
                    closeAdd();
            }
            else if (event.key === "Escape" &&
                route.id === null &&
                display.open &&
                document.querySelector("dialog[open]") === null &&
                document.querySelector(":popover-open") === null) {
                closeSettings();
            }
        });
        /** ハッシュが変わったとき（戻る・進む・手で書き換えた）、その画面を描く */
        const onLocationChange = () => {
            const parsed = MindmapPreview.parseHash({ hash: location.hash, index });
            const visible = visibleRoute(parsed);
            // 差分の時点を引き直し、引けた時点に揃える
            const settled = settleDiffPoint(visible);
            const next = settled.route;
            point = settled.point;
            syncEditView();
            // 表示しない種類のタブを指していた・時点が引けなかった: ハッシュを置き換える
            if (visible !== parsed || next.diff !== parsed.diff)
                MindmapPreview.navigate({ route: { ...next, filters: {} }, push: false });
            // 画面・表示形式・項目・差分の時点が同じで絞り込み（`f.{列}`）も無いときは、描き直さない。絞り込みだけを足したハッシュは、開き直しとして使う
            if (MindmapPreview.toHash(next) === MindmapPreview.toHash(route) && Object.keys(next.filters).length === 0)
                return;
            leaveEditViews();
            const screen = next.tab !== route.tab ||
                next.view !== route.view ||
                next.diff !== route.diff ||
                Object.keys(next.filters).length > 0 ||
                (next.tab === "decisions" && next.view === "map" && next.id !== route.id);
            route = next;
            render({ screen });
            reopenPendingPanel();
            // 絞り込みは画面に渡した後、ハッシュから消す（残すと、次のハッシュの変化で使い回される）
            if (Object.keys(next.filters).length > 0)
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
        };
        addEventListener("popstate", onLocationChange);
        addEventListener("hashchange", onLocationChange);
        // ===== 最初の描き =====
        // サーバーの配信では、レビュー中のコメントと書きかけを読んでおく（コメントのボタンの件数と入力に使う）
        if (serverMode) {
            await loadReview(true);
            await loadThreads();
            await loadEdits();
            syncEditView();
        }
        // 記録に無い項目を指すハッシュは、項目の無いハッシュに置き換える
        const requested = new URLSearchParams(location.hash.replace(/^#/, "")).get("id");
        if (requested !== null && route.id === null)
            MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
        render({ screen: true });
        // 絞り込みは画面に渡した後、ハッシュから消す
        MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
        // ===== 書き換えの知らせにつなぐ（サーバーの配信だけ） =====
        if (serverMode) {
            MindmapPreview.subscribeEvents({
                onChanged: () => void reload(),
                onConnection: (connected) => {
                    // 切れた: 接続の状態を出し、最後に読めた記録で描き続ける
                    if (!connected) {
                        connection = "offline";
                        renderTop();
                        return;
                    }
                    // つながり直した: 切れていた間の書き換えを読み直す（最初の接続は切れていないので何もしない）
                    if (connection === "offline") {
                        connection = "online";
                        renderTop();
                        void reload();
                    }
                },
            });
        }
    }
    // 文書が読み込まれたら起動する（記録の要素が無い文書では、読んだだけでは何もしない）
    if (document.getElementById(DATA_ELEMENT_ID) !== null) {
        if (document.readyState === "loading")
            document.addEventListener("DOMContentLoaded", () => void start());
        else
            void start();
    }
})(MindmapPreview || (MindmapPreview = {}));
