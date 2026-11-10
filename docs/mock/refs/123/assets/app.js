// develop のプレビューのスクリプト（tsc が生成した .js を build の順につないだもの）に、PR #123 の変更を当てたもの。
// 当てた箇所には「123:」のコメントを付けた。見た目ごとの描き方は stella.js が持つ。
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
        // 123: ネットワークの入口は、4 つの星を線で結び端の 1 つをきらめく星にした星座の形にする。鍵はロックの印
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
        changed: '<circle cx="12" cy="12" r="5"/>',
        arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
        save: '<path d="M5 4h11l3 3v13H5Z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
        sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
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
    /** 背景（ボタンなどの上でない所）をつかんで、スクロールする要素を動かせるようにする。`onPress` は、背景を押して離したとき（ドラッグでないとき）に呼ぶ */
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
        scroller.addEventListener("pointerup", () => {
            const pressed = drag !== null && !drag.moved;
            release();
            if (pressed)
                onPress?.();
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
    /** ID を種類の順 → 連番の順に比べる */
    function compareIds(a, b) {
        const rank = (id) => MindmapPreview.KIND_KEYS.indexOf(KIND_OF_PREFIX[id.slice(0, 1)] ?? "logs");
        return rank(a) - rank(b) || Number(a.slice(2)) - Number(b.slice(2));
    }
    MindmapPreview.compareIds = compareIds;
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
                for (const target of item[key] ?? []) {
                    const sources = referencedBy.get(target) ?? [];
                    sources.push(item.id);
                    referencedBy.set(target, sources);
                }
            }
        }
        for (const sources of referencedBy.values())
            sources.sort(compareIds);
        return {
            data,
            byId,
            referencedBy,
            readyIds: new Set(data.derived.next.map((candidate) => candidate.id)),
        };
    }
    MindmapPreview.buildIndex = buildIndex;
    /** 前提・後続・関連タスク・経緯・関連・参照している項目を返す */
    function relatedItems({ id, index }) {
        const entry = index.byId.get(id);
        const item = entry?.item;
        const referrers = index.referencedBy.get(id) ?? [];
        /** ID の項目が、キーで id を指しているか */
        const points = (referrer, key) => (index.byId.get(referrer)?.item[key] ?? []).includes(id);
        const kindOf = (referrer) => index.byId.get(referrer)?.kind;
        const successors = referrers.filter((referrer) => points(referrer, "depends_on"));
        const tasks = referrers.filter((referrer) => kindOf(referrer) === "tasks" && points(referrer, "for"));
        // 経緯: この項目を更新した会話ログと、この項目が経緯として指す会話ログ
        const incomingLogs = referrers.filter((referrer) => kindOf(referrer) === "logs" && points(referrer, "related"));
        const logs = [...new Set([...incomingLogs, ...(item?.sources ?? [])])].sort(compareIds);
        const related = item?.related ?? [];
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
        parts.push(bodies[item.body ?? ""] ?? "");
        return parts.join("\n").toLowerCase();
    }
    /** 空白で区切った語を全て含む項目を、ID かタイトルが言葉と完全に一致する項目を先にして返す（大文字・小文字と前後の空白を区別しない） */
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
                    const exact = item.id.toLowerCase() === whole || item.title.trim().toLowerCase() === whole;
                    hits.push({ id: item.id, kind, title: item.title, exact });
                }
            }
        }
        // 完全に一致する項目を先にする（それぞれ今の種類の順・連番の順のまま）
        return [...hits.filter((hit) => hit.exact), ...hits.filter((hit) => !hit.exact)];
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
// 描画のライブラリ（marked・DOMPurify・elkjs・mermaid）と差分のライブラリ（jsdiff）の有無と呼び出し、選んだ範囲から箇所を求める処理。読めなかったときは名前を出し、代わりの読み込みはしない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 描画のライブラリの名前 → 読めたときに置かれるグローバルの名前 */
    MindmapPreview.LIBRARIES = {
        marked: "marked",
        DOMPurify: "DOMPurify",
        elkjs: "ELK",
        mermaid: "mermaid",
        jsdiff: "Diff",
    };
    /** 図の入れ物が原文を持つ属性の名前 */
    MindmapPreview.DIAGRAM_SOURCE_ATTR = "data-source";
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
    /** 項目の値を描いた要素が持つ、項目のキーのパスの属性 */
    MindmapPreview.VALUE_KEY_ATTR = "data-key";
    /** 改行の数を返す */
    function countNewlines(text) {
        return text.split("\n").length - 1;
    }
    /** token の並びに、先頭の行から raw の改行を足し進めた行を持たせる（リストの項目・引用の中も同じ） */
    function assignLines({ tokens, start }) {
        let line = start;
        for (const token of tokens) {
            token.line = line;
            if (token.type === "list" && token.items) {
                assignLines({ tokens: token.items, start: line });
            }
            else if ((token.type === "list_item" || token.type === "blockquote") && token.tokens) {
                // 項目の中の token は字下げを外した raw を持つが、改行の数は元と同じ
                assignLines({ tokens: token.tokens, start: line });
            }
            line += countNewlines(token.raw);
        }
    }
    /** token が持つ行を返す */
    function lineOf(token) {
        return token.line;
    }
    /** 描いた HTML の最初の開きタグに、行の印を足す */
    function withLine(html, line) {
        if (line === undefined)
            return html;
        return html.replace(/^<(\w+)/, `<$1 ${MindmapPreview.LINE_ATTR}="${line + 1}"`);
    }
    /** 本文の Markdown を、空行を持たないブロックごとに行の印を付けて HTML に描く */
    function renderWithLines(source) {
        const tokens = marked.lexer(source);
        assignLines({ tokens: tokens, start: 0 });
        const renderer = new marked.Renderer();
        const base = {
            heading: renderer.heading.bind(renderer),
            paragraph: renderer.paragraph.bind(renderer),
            code: renderer.code.bind(renderer),
            listitem: renderer.listitem.bind(renderer),
            table: renderer.table.bind(renderer),
        };
        renderer.heading = (token) => withLine(base.heading(token), lineOf(token));
        renderer.paragraph = (token) => withLine(base.paragraph(token), lineOf(token));
        // mermaid の図は印を付けない（図の中の選択を本文の外として扱う）
        // フェンスで囲んだコードは、中身がフェンスの次の行から始まる
        renderer.code = (token) => {
            if (token.lang === "mermaid")
                return base.code(token);
            const line = lineOf(token);
            const fence = token.codeBlockStyle === "indented" ? 0 : 1;
            return withLine(base.code(token), line === undefined ? undefined : line + fence);
        };
        // 段落を持つ項目は中の段落が印を持つので、段落を持たない項目だけ li に付ける
        renderer.listitem = (item) => (item.loose ? base.listitem(item) : withLine(base.listitem(item), lineOf(item)));
        // 表は行ごとに 1 行。見出しの行の次に区切りの行がある
        renderer.table = (token) => {
            const start = lineOf(token);
            if (start === undefined)
                return base.table(token);
            let row = 0;
            return base.table(token).replace(/<tr>/g, () => {
                const line = row === 0 ? start : start + 1 + row;
                row += 1;
                return `<tr ${MindmapPreview.LINE_ATTR}="${line + 1}">`;
            });
        };
        return marked.parser(tokens, { renderer });
    }
    MindmapPreview.renderWithLines = renderWithLines;
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
        const startBlock = lineBlock(range.startContainer);
        const endBlock = lineBlock(range.endContainer);
        // 本文の外
        if (!startBlock || !endBlock)
            return null;
        const first = Number(startBlock.getAttribute(MindmapPreview.LINE_ATTR));
        const last = Number(endBlock.getAttribute(MindmapPreview.LINE_ATTR));
        return {
            kind: "body",
            start: first + linesBefore({ block: startBlock, node: range.startContainer, offset: range.startOffset }),
            end: last + linesBefore({ block: endBlock, node: range.endContainer, offset: range.endOffset }),
            text,
        };
    }
    MindmapPreview.selectionLocation = selectionLocation;
    /** 選択の端から、値のキーのパスを持つ最も近い要素を返す（無ければ null） */
    function keyElement(node) {
        const element = node instanceof Element ? node : node.parentElement;
        return element?.closest(`[${MindmapPreview.VALUE_KEY_ATTR}]`) ?? null;
    }
    /** 本文の Markdown を無害化した要素にする。mermaid のコードブロックは図の入れ物に置き換える */
    function renderMarkdown(source) {
        const root = MindmapPreview.h({ tag: "div", attrs: { class: "md" } });
        const missing = missingLibraries(["marked", "DOMPurify"]);
        const hasDiagram = source.includes("```mermaid");
        // marked か DOMPurify が読めていない: 知らせと原文を出す
        if (missing.length > 0) {
            const names = [...missing];
            if (hasDiagram && missingLibraries(["mermaid"]).length > 0)
                names.push("mermaid");
            root.append(libraryNotice({ names, what: "本文" }), MindmapPreview.h({ tag: "pre", attrs: { class: "md-raw" }, children: [source] }));
            return root;
        }
        // 描いた HTML は無害化してから差し込む（記録は利用者のもの）
        root.innerHTML = DOMPurify.sanitize(renderWithLines(source));
        // mermaid のコードブロックを、原文を持つ図の入れ物（拡大・Raw・コピーの道具つき）に置き換える
        for (const code of root.querySelectorAll("code.language-mermaid")) {
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
    /** 描いた本文の見出しに、見出しを指す名前（`data-heading`）と右の # のリンクを付け、本文の中の `#見出し` のリンクをその見出しへの移動にする。押したときは既定の動作を止め、見出しの名前を `onHeading` に知らせる */
    function linkHeadings({ root, onHeading }) {
        // 本文の中の `[文言](#見出し)` のリンク（# のリンクを足す前の分）。同じ名前の見出しがあるときだけ知らせ、無ければ何もしない
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
    /** 英数字と記号だけの用語か（ファイル名・識別子の一部に当てないよう、語の切れ目でだけ当てる） */
    const ASCII_TERM = /^[!-~ ]+$/;
    /** 描いた本文の文中の、用語集の用語を印に、記録にある項目の ID をリンクにする。`pre`・図・リンク・見出しの中は飛ばし、インラインコードは中身がちょうど用語か ID のときだけ当てる。押したときは既定の動作を止め、その項目の ID を `onOpen` に知らせる */
    function linkBody({ root, index, selfId, onOpen, }) {
        // 項目自身の用語と、タイトルが空の用語には付けない。長い用語から順に当てる
        const terms = index.data.terms
            .filter((term) => term.id !== selfId && term.title.trim() !== "")
            .sort((a, b) => b.title.length - a.title.length);
        const byTitle = new Map(terms.map((term) => [term.title, term]));
        const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const termPattern = (title) => ASCII_TERM.test(title) ? `(?<![A-Za-z0-9_.-])${escape(title)}(?![A-Za-z0-9_-])` : escape(title);
        // 項目の ID（英大文字 - 数字。前後が英数字のものは当てない）と、長い用語の順
        const pattern = new RegExp(["(?<![A-Za-z0-9-])[A-Z]+-[0-9]+(?![0-9])", ...terms.map((term) => termPattern(term.title))].join("|"), "g");
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => node.parentElement?.closest("pre, figure, a, button, svg, .mermaid, h1, h2, h3, h4, h5, h6") !== null
                ? NodeFilter.FILTER_REJECT
                : NodeFilter.FILTER_ACCEPT,
        });
        const nodes = [];
        for (let node = walker.nextNode(); node !== null; node = walker.nextNode())
            nodes.push(node);
        for (const node of nodes) {
            const text = node.textContent ?? "";
            // インラインコードは、中身がちょうど用語か ID のときだけ（パスや識別子の一部には付けない）
            const inCode = node.parentElement?.closest("code") !== null;
            const parts = [];
            let last = 0;
            for (const match of text.matchAll(pattern)) {
                const word = match[0];
                const term = byTitle.get(word);
                const isId = term === undefined;
                // 記録に無い ID・項目自身の ID・コードの一部は、そのままにする
                if ((isId && (!index.byId.has(word) || word === selfId)) || (inCode && text.trim() !== word))
                    continue;
                const target = isId ? word : term.id;
                parts.push(text.slice(last, match.index), MindmapPreview.h({
                    tag: "a",
                    attrs: {
                        class: isId ? "idref" : "term",
                        href: hashWith({ id: target, heading: null }),
                        "data-id": target,
                        "aria-describedby": isId ? null : MindmapPreview.TERM_TIP_ID,
                        onclick: (event) => {
                            event.preventDefault();
                            onOpen(target);
                        },
                    },
                    children: [word],
                }));
                last = (match.index ?? 0) + word.length;
            }
            if (parts.length === 0)
                continue;
            parts.push(text.slice(last));
            node.replaceWith(...parts.filter((part) => part !== ""));
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
    /** 「まだまとめていない変更」の名前と補足 */
    const PENDING_NAME = "まだまとめていない変更";
    const PENDING_SUB = "AI がまだ区切っていない書き換え";
    /** 「前回開いてから」の名前 */
    const SINCE_NAME = "前回開いてから";
    /** 選んだ時点の名前・補足・印・範囲から、時点を組み立てる */
    function buildPoint({ sel, name, sub, groups, fromSeq, untilSeq, }) {
        const added = new Set(groups.flatMap((group) => group.added));
        // 足した項目は、変えても変更の印にしない
        const changed = new Set(groups.flatMap((group) => group.changed).filter((id) => !added.has(id)));
        return { sel, name, sub, added, changed, fromSeq, untilSeq };
    }
    /** 選んだ時点の識別子から、印を付ける項目と変更履歴の範囲を決める。差分を出さないときは null */
    function resolveDiffPoint(changes, sel, since) {
        if (sel === null)
            return null;
        const sets = changes.sets;
        // 先頭のまとまりまでの変更履歴（それより後がまだまとめていない分）
        const latestSeq = sets[0]?.until_seq ?? 0;
        if (sel === "pending") {
            // まだまとめていない変更が無い
            if (changes.pending.added.length === 0 && changes.pending.changed.length === 0)
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
// URL のハッシュの読み書きと履歴。画面・表示形式・開いている項目・全画面・絞り込みを、`URLSearchParams` の形で持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** タブの帯に並べる画面（つながりは帯の右端に別に置く） */
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
        return { tab, view, id, full: id !== null && params.get("full") === "1", filters, heading };
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
// サーバーの配信とのやり取り。記録の取得・レビュー中のコメントと書きかけ・まとめて送る・書き換えの知らせの購読。
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
    /** プレビューを開いたことを知らせ、前回開いた日時を返す。届かない・200 でない・読めないときは null */
    async function postOpened(fetchFn = window.fetch.bind(window)) {
        try {
            const response = await fetchFn(MindmapPreview.API_PATHS.opened, { method: "POST" });
            if (!response.ok)
                return null;
            const body = (await response.json());
            return typeof body.previous === "string" ? body.previous : null;
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
        let detail = null;
        try {
            const problem = (await response.json());
            detail = typeof problem.detail === "string" ? problem.detail : null;
            stale = Array.isArray(problem.stale) ? problem.stale : [];
        }
        catch {
            // 本文が JSON でない
        }
        return {
            ok: false,
            status: response.status,
            detail: detail ?? (response.statusText || String(response.status)),
            stale,
        };
    }
    MindmapPreview.callApi = callApi;
    /** コメント・書きかけの 6 つの呼び出しを束ねて返す */
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
// トップバー。話し合いの題名・全体の検索の入口・変更履歴・ライト / ダークの切り替え・表示の設定・絞り込み・コメントのボタンと、画面を移るタブの帯（右端につながりの入口）を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 件数の表示を揺らさない上限 */
    const COMMENT_COUNT_CAP = 99;
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
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["新規・変更の項目があります"] })],
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
    function commentsButton({ count, open, onClick }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `comments-btn${open ? " open" : ""}`,
                type: "button",
                "data-act": "comments",
                "aria-label": `コメント（レビュー中 ${count} 件）`,
                "aria-expanded": String(open),
                onclick: () => onClick?.(),
            },
            children: [
                MindmapPreview.icon("comment"),
                MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["コメント"] }),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: `count${count === 0 ? " zero" : ""}` },
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
                count === 0 ? null : MindmapPreview.h({ tag: "span", attrs: { class: "fbadge", "aria-hidden": "true" }, children: [count] }),
            ],
        });
    }
    /** トップバーとタブの帯を返す */
    function topbar({ title, tabs, current, theme, onNavigate, onSearch, onTheme, connection = "online", readAt = null, comments = false, commentCount = 0, commentsOpen = false, onComments, diffPoint = null, onHistory, onDiffOff, settingsOpen = false, onSettings, filter = false, filterCount = 0, filterOpen = false, onFilter, }) {
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
                comments ? commentsButton({ count: commentCount, open: commentsOpen, onClick: onComments }) : null,
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
                // 123: 入口の名前を「ネットワーク」、アイコンを星座の形にする
                tabLink({ key: "graph", label: "ネットワーク", icon: "network" }, current, onNavigate, "tab-special"),
            ],
        });
        return MindmapPreview.h({ tag: "div", attrs: { class: "top" }, children: [bar, tabbar] });
    }
    MindmapPreview.topbar = topbar;
})(MindmapPreview || (MindmapPreview = {}));
// 差分の印。差分の表示の間、選んだ時点で足した項目に新規（太い +）、変えた項目に変更（塗った ●）の印を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類 → 画面に出す名前 */
    const DIFF_LABEL = { new: "新規", changed: "変更" };
    /** 差分の印。色だけでなく形（+ と ●）でも新規と変更を分け、名前は読み上げに残す */
    function diffMark({ kind, labeled = false }) {
        const label = DIFF_LABEL[kind];
        const glyph = MindmapPreview.icon(kind === "new" ? "plus" : "changed");
        const tone = kind === "new" ? "df-new" : "df-chg";
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
    /** 画面を開いたときの絞り込みを返す。URL のハッシュの `f.{列}` があればそれだけ、無ければ画面の既定 */
    function initialFilters(tab, fromHash) {
        if (Object.keys(fromHash).length > 0)
            return { ...fromHash };
        return tab === "decisions" ? { status: [...DEFAULT_DECISION_STATUSES] } : {};
    }
    MindmapPreview.initialFilters = initialFilters;
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
    function buildTable({ props: { kind, columns, rows, sort = null, filters = {}, pinTo = null, hiddenColumns, popover = null, marks, comments, on }, previous, }) {
        const hidden = new Set(hiddenColumns ?? columns.filter((column) => column.hidden).map((column) => column.key));
        const visible = columns.filter((column) => !hidden.has(column.key));
        // 固定する列の数（左端から pinTo の列まで）
        const pinned = pinTo === null ? 0 : visible.findIndex((column) => column.key === pinTo) + 1;
        const shownRows = sortRows({ rows: filterRows({ rows, columns, filters }), columns, sort });
        // 描き直しでは前の入れ物をそのまま使い、スクロールの位置を失わない
        const root = previous ?? MindmapPreview.h({ tag: "div", attrs: { class: "table-block", "data-kind": kind } });
        const wrap = previous?.querySelector(".table-wrap") ??
            MindmapPreview.h({ tag: "div", attrs: { class: "table-wrap" } });
        // ===== 条件のチップと、表示する列のボタン =====
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
        /** 表示する列のポップオーバーの中身 */
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
                    popoverTitle("表示する列"),
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
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "btn",
                        type: "button",
                        "data-popover": "columns",
                        "aria-label": "表示する列",
                        onclick: openPopover,
                    },
                    children: [
                        MindmapPreview.icon("cols"),
                        MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: ["表示する列"] }),
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
        const cellContent = (column, row) => {
            const content = column.cell?.(row) ?? valuesOf(column, row).join(column.num === true ? "" : "、");
            if (column.fixed !== true)
                return content;
            // タイトルの列は、押すと詳細を開くボタンにし、差分の印があれば右に置く
            const opener = MindmapPreview.h({
                tag: "button",
                attrs: { class: "row-open", type: "button", "data-id": row.id, onclick: () => on.open(row.id) },
                children: [content],
            });
            const mark = MindmapPreview.markFor({ marks, id: row.id });
            const commentPlaceElement = comments === undefined ? null : MindmapPreview.commentPlace({ id: row.id, count: comments[row.id] });
            if (mark === null && commentPlaceElement === null)
                return opener;
            const fragment = document.createDocumentFragment();
            fragment.append(...[opener, mark, commentPlaceElement].filter((node) => node !== null));
            return fragment;
        };
        const body = shownRows.length > 0
            ? shownRows.map((row) => MindmapPreview.h({
                tag: "tr",
                attrs: { "data-id": row.id, class: row.id === MindmapPreview.currentSelection() ? "selected" : "" },
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
                        children: [cellContent(column, row)],
                    })),
                ],
            }))
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
        return Array.isArray(value) ? value.map(String) : [];
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
                get: (row) => texts(row, "tags"),
                cell: (row) => MindmapPreview.tagList(texts(row, "tags")),
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
    function managedTable({ kind, columns, rows, filters, onFilter, open, marks, comments, }) {
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
    function sendForm({ target, loc = null, body = "", status = "idle", count = null, detail = null, collapsed = false, on, }) {
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
                rows: folded ? 1 : 2,
                "aria-label": target === null ? NO_TARGET_LABEL : null,
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
// 選んだ箇所のコメントの入口。本文の文章か項目の値を選び終えたときに、選んだ範囲の近くに出すピルの形のボタン。
var MindmapPreview;
(function (MindmapPreview) {
    /** 入口の大きさ（位置を決めるため固定する）。押せる的は高さ 32px 以上 */
    const PILL_WIDTH = 104;
    const PILL_HEIGHT = 32;
    /** 選んだ範囲との間の空きと、画面の端から内側に収める幅 */
    const PILL_GAP = 6;
    const SCREEN_EDGE = 8;
    /** 入口を返す。選んだ範囲の終わりの下に出し、下に収まらなければ始まりの上に出す。左右は画面の端から内側に収める */
    function selectionComment({ anchor, viewport, on }) {
        const below = anchor.last.bottom + PILL_GAP;
        // 下に収まらない: 選んだ範囲の始まりの上に出す
        const top = below + PILL_HEIGHT > viewport.height - SCREEN_EDGE ? anchor.first.top - PILL_GAP - PILL_HEIGHT : below;
        const left = Math.max(SCREEN_EDGE, Math.min(anchor.last.left, viewport.width - SCREEN_EDGE - PILL_WIDTH));
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "selection-comment",
                type: "button",
                "aria-label": "選んだ箇所にコメント",
                style: `position:fixed;left:${left}px;top:${top}px;width:${PILL_WIDTH}px;height:${PILL_HEIGHT}px`,
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
            children: [MindmapPreview.icon("comment"), MindmapPreview.h({ tag: "span", children: ["コメント"] })],
        });
    }
    MindmapPreview.selectionComment = selectionComment;
})(MindmapPreview || (MindmapPreview = {}));
// 表示の設定の中身。つながりの見た目と表示する種類を選び、この端末で変えている項目・既定に戻す・ワークスペースの既定にするを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 選べるつながりの見た目（見た目ごとの描き分けは別の作業が作る） */
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
    // 123: 見た目はネットワークのドロップダウンだけで選ぶため、パネルには見た目の選びを置かない
    /** 概要・つながりの行（常に出す。チェックの箱を持たない） */
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
    /** 表示する種類の選び（先頭にまとめて選ぶチェック、概要とつながりは常に出す行） */
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
                        children: ["今の選びはワークスペースの既定と同じです。"],
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
    /** 表示の設定の中身を返す */
    function settingsPanel(props) {
        const { canSave, message = null, storageOk = true } = props;
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "st-wrap" },
            children: [
                storageOk ? null : storageNote(),
                kindsField(props),
                resetBlock(props),
                canSave ? saveBlock(props) : null,
                messageLine(message),
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
        return { tab, view, id: null, full: false, filters, heading: null };
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
        // 123: 直前に押した節（素早い 2 回目を同じ節への 2 回押しとして扱う）
        lastTap: null,
    };
    /** 123: 2 回押しとみなす間隔（ms） */
    const MAP_DOUBLE_TAP_MS = 450;
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
    /** 木の節と枝を、配置された座標で描く。選んだ項目の根までの枝と依存の線を強調し、ほかを薄くする */
    function drawMap({ laid, canvas, selected, open, marks, comments, }) {
        const positions = new Map(laid.children.map((node) => [node.id, node]));
        const parentOf = new Map(laid.edges.map((edge) => [edge.targets[0], edge.sources[0]]));
        // 123: 強調の起点はロックした節。ロックしていなければ、詳細を開いている節
        const opened = selected;
        const lockedId = MindmapPreview.lockOf("map");
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
                    // 123: 詳細を開いている節に sel、ロックした節に locked を付ける（押したときはロックの規則へ渡す）
                    class: `map-node n-item${opened === item.id ? " sel" : ""}${lockedHere && lockedId === item.id ? " locked" : ""}${hit ? " hit" : ""}${rel}`,
                    type: "button",
                    "data-node": item.id,
                    style,
                    title: `${item.title}（${item.status ?? ""}）`,
                    onclick: () => open(item.id),
                },
                children: [
                    // 123: 鍵は節の右上の内側に置く。開いた鍵は詳細を開いている節にカーソルを乗せたときだけ、閉じた鍵はロック中いつも出す（出し分けは CSS）
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
                            comments === undefined ? null : MindmapPreview.commentPlace({ id: item.id, count: comments[item.id] }),
                        ],
                    }),
                ],
            });
        });
        canvas.classList.toggle("focusing", selected !== null);
        // 123: ロック中は、開いた鍵を出さない。モックの「開いた鍵」の見本では、乗せなくても出す
        canvas.classList.toggle("has-lock", lockedHere);
        canvas.classList.toggle("demo-open", window.MOCK123?.demo === "open");
        canvas.style.width = `${laid.width ?? 0}px`;
        canvas.style.height = `${laid.height ?? 0}px`;
        canvas.replaceChildren(edgeSvg, ...nodes);
    }
    /** 狭い幅で使う、字下げした縦の一覧 */
    function outline({ index, decisions, open, marks, comments, }) {
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
    function mapView({ index, route, on, marks, comments }, { shown, chips, makeDrawer, }) {
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
        let outlineElement = outline({ index, decisions: shown, open: on.open, marks, comments });
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
        /** 配置を求めて、マップを描く。選んだ項目が変わってその節があるときは、その節が中央に来るようにマップを送り、それ以外は描き直す前のスクロールの位置へ戻す */
        const draw = async () => {
            outlineElement.replaceWith((outlineElement = outline({ index, decisions: shown, open: on.open, marks, comments })));
            if (MindmapPreview.missingLibraries(["elkjs"]).length > 0)
                return;
            const key = shown.map((item) => item.id).join(",");
            const graph = buildDecisionTree({ index, decisions: shown });
            emptyNotice.hidden = graph.children.length > 0;
            current = await layoutOf(graph, key);
            drawMap({ laid: current, canvas, selected: route.id, open: tap, marks, comments });
            applyZoom();
            // 123: 中央へ送る節は、ロックした節。ロックしていなければ詳細を開いている節（ロック中にほかの節を開いても送り直さない）
            const lockedId = MindmapPreview.lockOf("map");
            const anchorId = lockedId !== null && current.children.some((n) => n.id === lockedId) ? lockedId : route.id;
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
        // 123: 節を押したとき: ネットワークと同じ規則でロックする
        /** ロックした節の鍵（描き直しても今の要素を引く） */
        const lockedKey = () => canvas.querySelector(".n-item.locked .lk");
        const tap = (id) => {
            mapState.lastTap = { id, time: performance.now() };
            const action = MindmapPreview.lockTap({ key: "map", id, open: route.id });
            if (action === "shake")
                MindmapPreview.shakeKeyElement(lockedKey);
            else if (action === "lock" || action === "unlock")
                void draw();
            else if (action === "open")
                on.open(id);
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
        ], route, on.view);
        toolbarElement.append(keyword);
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
        // 余白を押したときは、選んでいる項目があるときだけ選びを外す
        MindmapPreview.enableDragScroll(wrap, () => {
            // 123: 節を押した直後に描き直しで節が消えた位置への素早い 2 回目は、その節への 2 回押しとして扱う
            const last = mapState.lastTap;
            if (last !== null && performance.now() - last.time < MAP_DOUBLE_TAP_MS) {
                tap(last.id);
                return;
            }
            // 123: ロック中に余白を押したら、ロック・詳細・表示を変えずに鍵を震わせる
            if (MindmapPreview.lockOf("map") !== null) {
                MindmapPreview.shakeKeyElement(lockedKey);
                return;
            }
            if (route.id !== null)
                on.clear();
        });
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
    /** 検討事項の画面を返す */
    function decisionsScreen(props) {
        const { index, route, on, marks, comments, filters, drawerOpen } = props;
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
        ], route, on.view);
        if (route.view === "board") {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "screen decisions" },
                children: [
                    toolbarElement,
                    chips,
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
                        }),
                        emptyText: "検討事項はありません。",
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
                MindmapPreview.managedTable({
                    kind: "decisions",
                    columns,
                    rows: shown,
                    filters,
                    onFilter: on.filter,
                    open: on.open,
                    marks,
                    ...(comments === undefined ? {} : { comments }),
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
    function boardCard({ index, item, meta, links, open, mark, comments, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: item.id === MindmapPreview.currentSelection() ? "card selected" : "card",
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
    function board({ columns, card, emptyText, }) {
        const element = MindmapPreview.h({
            tag: "div",
            attrs: { class: "board", style: `--cols:${columns.length}` },
            children: [
                ...columns.map(({ status, items, excluded = false }) => MindmapPreview.h({
                    tag: "section",
                    attrs: { class: "board-col", "aria-label": status },
                    children: [
                        MindmapPreview.h({
                            tag: "h3",
                            children: [
                                MindmapPreview.statusMark(status),
                                status,
                                MindmapPreview.h({ tag: "span", attrs: { class: "n" }, children: [items.length] }),
                            ],
                        }),
                        // 状態の条件で外した列は、列を残して外した旨を出す
                        ...(excluded
                            ? [MindmapPreview.emptyNote("状態の条件で外しています。")]
                            : items.length > 0
                                ? items.map(card)
                                : [MindmapPreview.emptyNote(emptyText)]),
                    ],
                })),
            ],
        });
        MindmapPreview.enableDragScroll(element);
        return element;
    }
    MindmapPreview.board = board;
    /** 表示形式の切り替えを置いた道具の行 */
    function toolbar(views, route, onView) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "toolbar" },
            children: [MindmapPreview.viewSwitch({ views, current: route.view, onChange: onView })],
        });
    }
    MindmapPreview.toolbar = toolbar;
    /** タスクの画面を返す */
    function tasksScreen({ index, route, on, marks, comments, filters, drawerOpen }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        const columns = [
            common.id,
            common.title(),
            common.status(MindmapPreview.TASK_STATUSES),
            common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
            {
                key: "for",
                label: "進める検討事項",
                priority: 3,
                get: (row) => MindmapPreview.rowTexts(row, "for"),
                cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.rowTexts(row, "for"), on.open),
            },
            common.target,
            common.category,
            common.phase,
            common.tags,
        ];
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
                }),
                emptyText: "タスクはありません。",
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
            });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen tasks" },
            children: [
                toolbar([
                    { key: "board", label: "ボード" },
                    { key: "table", label: "表" },
                ], route, on.view),
                chips,
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
    /** 資料の画面を返す */
    function docsScreen({ index, route, on, marks, comments, filters, drawerOpen }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        const columns = [
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
            common.target,
            common.category,
            common.phase,
            common.tags,
        ];
        const toolbarElement = MindmapPreview.toolbar([
            { key: "cards", label: "カード" },
            { key: "board", label: "ボード" },
            { key: "table", label: "表" },
        ], route, on.view);
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
                    MindmapPreview.managedTable({
                        kind: "docs",
                        columns,
                        rows: shown,
                        filters,
                        onFilter: on.filter,
                        open: on.open,
                        marks,
                        ...(comments === undefined ? {} : { comments }),
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
                    card: (item) => docCard({ index, doc: item, open: on.open, inBoard: true, mark: marks?.[item.id], comments }),
                    emptyText: "資料はありません。",
                })
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "doc-grid" },
                children: shown.length > 0
                    ? orderDocs(shown).map((row) => docCard({ index, doc: row, open: on.open, inBoard: false, mark: marks?.[row.id], comments }))
                    : [MindmapPreview.h({ tag: "p", attrs: { class: "no-match" }, children: ["該当する資料はありません。別の条件を試してください。"] })],
            });
        return MindmapPreview.h({ tag: "div", attrs: { class: "screen docs" }, children: [toolbarElement, chips, content, drawer] });
    }
    MindmapPreview.docsScreen = docsScreen;
    /** 資料のカード（納品物の印・種類・状態・カテゴリー・フェーズ・タグ）。ボードの中では列で状態が分かるので状態の印を出さず、開いている資料に選択の印を付ける */
    function docCard({ index, doc, open, inBoard, mark, comments, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `card doc-card${doc.deliverable === true ? " deliv-card" : ""}${inBoard && doc.id === MindmapPreview.currentSelection() ? " selected" : ""}`,
                type: "button",
                "data-id": doc.id,
                onclick: () => open(doc.id),
            },
            children: [
                doc.deliverable === true ? MindmapPreview.deliverableBadge() : null,
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "doc-kind" },
                    children: [MindmapPreview.icon(doc.kind === "図" ? "graph" : "cards"), doc.kind ?? ""],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "c-ttl" }, children: [doc.title] }),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "c-meta" },
                    children: [
                        mark === undefined ? null : MindmapPreview.diffMark({ kind: mark }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [doc.id] }),
                        inBoard ? null : MindmapPreview.statusBadge(doc.status),
                        MindmapPreview.h({ tag: "span", children: [[doc.category, doc.phase].filter(Boolean).join(" · ")] }),
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
    /** 調査・用語集・メモ・会話ログの画面を返す。種類は `route.tab` で決まる */
    function recordsScreen({ index, route, on, filters, drawerOpen, marks, comments, }) {
        const kind = route.tab;
        const common = MindmapPreview.commonColumns(index.data.settings);
        const related = (label) => ({
            key: "related",
            label,
            priority: 3,
            get: (row) => MindmapPreview.rowTexts(row, "related"),
            cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.rowTexts(row, "related"), on.open),
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
        const columns = columnsOf[kind];
        // 絞り込みの条件に合う項目を表に渡す
        const shown = MindmapPreview.filterRows({ rows: index.data[kind], columns, filters });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen records" },
            children: [
                MindmapPreview.managedTable({
                    kind,
                    columns,
                    rows: shown,
                    filters,
                    onFilter: on.filter,
                    open: on.open,
                    marks,
                    ...(comments === undefined ? {} : { comments }),
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
// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。差分の表示の間は、選んだ時点の前後の差分も出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 前の値が無いときに出す文字 */
    const NO_VALUE = "（なし）";
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
    /** 読み上げにだけ残す文字 */
    function srOnly(text) {
        return MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [text] });
    }
    /** 差分の記号（見えるのは記号だけで、名前は読み上げに残す） */
    function signMarks(op) {
        const { glyph, name } = SIGNS[op];
        return [MindmapPreview.h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: [glyph] }), ...(name === "" ? [] : [srOnly(name)])];
    }
    /** 変わったキーの前の値と今の値を並べる。前の値は取り消し線、今の値は下線。plain は面を塗らず、線と矢印だけで示す */
    function keyDiff({ was, now, plain = false }) {
        const empty = (value) => value === null || value === undefined || value === false || value === "";
        return MindmapPreview.h({
            tag: "span",
            attrs: { class: plain ? "df-kv df-plain" : "df-kv" },
            children: [
                MindmapPreview.h({
                    tag: "del",
                    attrs: { class: "df-was" },
                    children: [srOnly("前の値: "), empty(was) ? NO_VALUE : was],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "df-arrow", "aria-hidden": "true" }, children: ["→"] }),
                MindmapPreview.h({
                    tag: "ins",
                    attrs: { class: "df-now" },
                    children: [srOnly("今の値: "), empty(now) ? NO_VALUE : now],
                }),
            ],
        });
    }
    /** キーの値を、差分に並べる文字にする。値が無ければ null */
    function valueText(value) {
        if (value === undefined || value === null || value === "")
            return null;
        if (Array.isArray(value))
            return value.length === 0 ? null : value.join("、");
        return String(value);
    }
    /** 前の版と後の版を比べ、値が変わったキー（ツールが付けるキーと本文の名前を除く）の見せ方を返す */
    function keyDiffs(before, after) {
        const left = { ...before };
        const right = { ...after };
        const changed = new Set([...new Set([...Object.keys(left), ...Object.keys(right)])].filter((key) => !UNDIFFED_KEYS.has(key) && JSON.stringify(left[key]) !== JSON.stringify(right[key])));
        return {
            has: (key) => changed.has(key),
            show: (key, render = valueText, plain = false) => changed.has(key) ? keyDiff({ was: render(left[key]), now: render(right[key]), plain }) : render(right[key]),
            before,
        };
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
    /** 案の採用の状態の名前 */
    function optionResult(option) {
        if (option === undefined)
            return null;
        return option.adopted === true ? "採用" : option.adopted === false ? "不採用" : "検討中";
    }
    /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由を出す）。previous があれば、変わった値に前の値を並べる */
    function optionCards(options, previous) {
        const compare = previous !== null;
        const removed = (previous ?? []).filter((entry) => !options.some((option) => option.key === entry.key));
        return MindmapPreview.h({
            tag: "div",
            children: [
                ...options.map((option) => {
                    const before = previous?.find((entry) => entry.key === option.key);
                    const result = optionResult(option) ?? "検討中";
                    const rows = [
                        ["メリット", "pros", option.pros],
                        ["デメリット", "cons", option.cons],
                        ["備考", "note", option.note],
                        ["理由", "reason", option.reason],
                    ];
                    // 前の値と違う値は前の値と今の値を並べる。前に無かった案は全ての値を足した印にする
                    const shown = rows.filter(([, field, value]) => (value !== undefined && value !== "") || (compare && before?.[field] !== undefined));
                    const valueOf = (field, value) => compare && before?.[field] !== value ? keyDiff({ was: before?.[field] ?? null, now: value ?? null }) : value;
                    const resultChild = compare && optionResult(before) !== result ? keyDiff({ was: optionResult(before), now: result, plain: true }) : result;
                    return MindmapPreview.h({
                        tag: "div",
                        attrs: {
                            class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}`,
                        },
                        children: [
                            MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "o-head" },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                                    valueSpan(`options[${option.key}].content`, [
                                        compare && before?.content !== option.content ? keyDiff({ was: before?.content ?? null, now: option.content }) : option.content,
                                    ]),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "res" }, children: [resultChild] }),
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
        ];
        const rows = pairs.flatMap(([label, key, value]) => {
            const changed = diff?.has(key) === true;
            // 値が無く、変わってもいないキーは出さない
            if ((value === undefined || value === "") && !changed)
                return [];
            return [
                MindmapPreview.h({ tag: "dt", attrs: { class: changed ? "df-key" : null }, children: [label] }),
                MindmapPreview.h({ tag: "dd", attrs: { class: changed ? "df-key" : null }, children: [diff === null ? value : diff.show(key)] }),
            ];
        });
        const tagsChanged = diff?.has("tags") === true;
        if ((item.tags ?? []).length > 0 || tagsChanged) {
            rows.push(MindmapPreview.h({ tag: "dt", attrs: { class: tagsChanged ? "df-key" : null }, children: ["タグ"] }), MindmapPreview.h({ tag: "dd", attrs: { class: tagsChanged ? "df-key" : null }, children: [tagsChanged ? diff?.show("tags") : MindmapPreview.tagList(item.tags)] }));
        }
        return MindmapPreview.h({ tag: "dl", attrs: { class: "d-meta" }, children: [...rows] });
    }
    /** この項目へのレビュー中のコメントの節（読むだけ。直す・消す・チェックはコメントの一覧で行う） */
    function reviewSection(items) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "d-sec d-review" },
            children: [
                MindmapPreview.h({
                    tag: "h3",
                    children: ["レビュー中のコメント", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })],
                }),
                items.length === 0
                    ? MindmapPreview.emptyNote("レビュー中のコメントはありません。")
                    : MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "d-list review-list" },
                        children: items.map((comment) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                comment.loc === null
                                    ? null
                                    : MindmapPreview.h({
                                        tag: "div",
                                        attrs: { class: "review-loc" },
                                        children: [
                                            MindmapPreview.h({ tag: "span", attrs: { class: "review-loc-name" }, children: [MindmapPreview.locationLabel(comment.loc)] }),
                                            MindmapPreview.h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [comment.loc.text] }),
                                        ],
                                    }),
                                MindmapPreview.h({ tag: "p", attrs: { class: "review-body" }, children: [comment.body] }),
                            ],
                        })),
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
    /** 差分の記号を頭に置いた、足した塊・消した塊の囲み */
    function diffBlock({ op, children }) {
        return MindmapPreview.h({
            tag: op === "add" ? "ins" : "del",
            attrs: { class: "df-blk" },
            children: [...signMarks(op), ...children],
        });
    }
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
        lowerHeadings(rendered);
        plainDiagrams(rendered);
        return rendered;
    }
    /** 消した行のかたまりを、今の本文の差し込む場所の前（無ければ本文の最後）へ差し込む */
    function insertRemovedBlocks({ root, blocks }) {
        // 差し込む前の、行の印を持つ今のブロック（差し込む要素は印を持たない）
        const stamped = [...root.querySelectorAll(`[${MindmapPreview.LINE_ATTR}]`)];
        const lineOf = (element) => Number(element.getAttribute(MindmapPreview.LINE_ATTR));
        for (const block of blocks) {
            const rendered = renderRemoved(block);
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
                    continue;
                }
                if (previous?.tagName === "TR") {
                    previous.after(...rows);
                    continue;
                }
            }
            const piece = diffBlock({ op: "del", children: [...rendered.childNodes] });
            if (target === undefined) {
                root.append(piece);
                continue;
            }
            // 足した塊の囲みの中・箇条書きや表の中ではなく、その外側の前へ差し込む
            const outer = target.parentElement?.matches("ins.df-blk") === true ? target.parentElement : target;
            (outer.closest("ul, ol, table") ?? outer).before(piece);
        }
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
    /** 前後の本文を行ごとに比べ、今の本文を描いて足した部分と消した部分に印を付ける。差分を計算しきれなかったら null */
    function renderBodyDiff({ before, after }) {
        const compared = MindmapPreview.diffLineParts(before, after);
        if (compared === null)
            return null;
        const parts = withoutDiagramEdits({ parts: compared, before });
        const rendered = MindmapPreview.renderMarkdown(after);
        lowerHeadings(rendered);
        markAddedBlocks({ root: rendered, parts, source: after });
        insertRemovedBlocks({ root: rendered, blocks: MindmapPreview.placeRemovedBlocks(parts) });
        return rendered;
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
    /** 記法の行ごとの差分を、足した行（+）・消した行（−）の印つきの行にする */
    function rawDiffLines(parts) {
        const op = { added: "add", removed: "del", same: "same" };
        return parts.flatMap((part) => part.lines.map((text) => MindmapPreview.h({
            tag: "span",
            attrs: { class: `df-line${part.kind === "same" ? "" : ` df-${op[part.kind]}`}` },
            children: [...signMarks(op[part.kind]), text],
        })));
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
        const parts = MindmapPreview.diffLineParts(withTrailingNewline(beforeSource), withTrailingNewline(afterSource));
        if (raw !== null && parts !== null) {
            raw.classList.add("df-raw");
            raw.replaceChildren(...rawDiffLines(parts));
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
    /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
    function detailBody({ id, index, on, reviews, view }) {
        const entry = index.byId.get(id);
        const body = MindmapPreview.h({ tag: "div", attrs: { class: "detail" } });
        if (entry === undefined)
            return body;
        const { kind } = entry;
        const item = view?.shown ?? entry.item;
        const keys = view?.keys ?? null;
        const related = MindmapPreview.relatedItems({ id, index });
        /** キーの値。変わっていれば前の値と今の値を並べる */
        const textOf = (key, value) => (keys?.has(key) === true ? keys.show(key) : value);
        const labelled = (label, key, value) => {
            const changed = keys?.has(key) === true;
            if ((value === undefined || value === "") && !changed)
                return null;
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: changed ? "d-answer df-key" : "d-answer" },
                children: [MindmapPreview.h({ tag: "b", children: [label] }), valueSpan(key, [textOf(key, value)])],
            });
        };
        /** 見出しの下の 1 段落 */
        const lead = (key, value, className) => {
            if ((value === undefined || value === "") && keys?.has(key) !== true)
                return null;
            return MindmapPreview.h({ tag: "p", attrs: { class: className, [MindmapPreview.VALUE_KEY_ATTR]: key }, children: [textOf(key, value)] });
        };
        /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす。差分の表示の間は、本文と図の差分を重ねる */
        const bodySection = (label) => {
            const source = view?.body ?? index.data.bodies[item.body ?? ""];
            if (source === undefined)
                return null;
            let rendered = null;
            let notice = null;
            let diagramBefore = null;
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
                    rendered = renderBodyDiff({ before: versions.beforeBody, after: source });
                    if (rendered === null)
                        notice = noteBox(NOTE_BODY_TOO_LARGE);
                }
            }
            const root = rendered ?? MindmapPreview.renderMarkdown(source);
            if (rendered === null)
                lowerHeadings(root);
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
            });
            MindmapPreview.linkBody({ root, index, selfId: id, onOpen: on.open });
            const drawn = MindmapPreview.renderDiagrams(root);
            if (diagramBefore !== null) {
                const before = diagramBefore;
                void drawn.then(() => decorateDiagrams({ root, before }));
            }
            root.addEventListener("click", (event) => {
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
            });
            const content = document.createDocumentFragment();
            content.append(...(notice === null ? [] : [notice]), root);
            return section(label, content);
        };
        /** 関係する項目の節（1 件以上あるときだけ） */
        const relation = (label, ids) => ids.length === 0 ? null : section(label, itemList(index, ids, on.open));
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
                        keys?.has("title") === true ? keys.show("title") : item.title,
                        item.deliverable === true ? MindmapPreview.deliverableBadge() : null,
                        view?.kind === "new" ? MindmapPreview.diffMark({ kind: "new", labeled: true }) : null,
                    ],
                }),
                metaList({ item, settings: index.data.settings, diff: keys }),
            ],
        });
        if (kind === "decisions") {
            const previous = keys?.has("options") === true ? (keys.before.options ?? []) : null;
            MindmapPreview.append({
                parent: body,
                children: [
                    lead("lead", item.lead, "d-lead"),
                    labelled("決定内容", "answer", item.answer),
                    labelled("理由", "reason", item.reason),
                    (item.options ?? []).length > 0 || previous !== null ? section("案", optionCards(item.options ?? [], previous)) : null,
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
                    labelled("理由", "reason", item.reason),
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
                    labelled("結論", "conclusion", item.conclusion),
                    listSection("調査の観点", "angles", item.angles),
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "docs") {
            MindmapPreview.append({ parent: body, children: [bodySection("本文")] });
        }
        else if (kind === "terms") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled("意味", "meaning", item.meaning),
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
                relation(kind === "logs" ? "更新した項目" : "関連", related.related),
                relation("参照元", related.referencedBy),
                reviews === null ? null : reviewSection(reviews),
            ],
        });
        return body;
    }
    /** 見出し（前へ・次へ・全画面・閉じる）を作る */
    function detailHead({ id, index, full, on }) {
        const entry = index.byId.get(id);
        const trail = history.state;
        const position = trail?.position ?? 0;
        const length = trail?.items.length ?? 1;
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
                        entry === undefined ? "" : `${MindmapPreview.KIND_LABEL[entry.kind]} `,
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
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
    /** 詳細パネルの節の見出し（h3）の下に、本文の見出し（h1〜h6）を並べるための段の差 */
    const BODY_HEADING_OFFSET = 3;
    /** 見出しの要素の最も下の段（h6） */
    const LOWEST_HEADING_LEVEL = 6;
    /** 本文の見出しを、パネルの節の見出しより下の段（h4〜h6）に下げる。見た目は元の段のまま（`data-md-level`） */
    function lowerHeadings(root) {
        for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
            const level = Number(heading.tagName.slice(1));
            const lowered = Math.min(level + BODY_HEADING_OFFSET, LOWEST_HEADING_LEVEL);
            const replacement = MindmapPreview.h({
                tag: `h${lowered}`,
                attrs: {
                    "data-md-level": level,
                    // 元の Markdown の行の印を引き継ぐ
                    [MindmapPreview.LINE_ATTR]: heading.getAttribute(MindmapPreview.LINE_ATTR),
                    // h6 を超える段は、読み上げの段で伝える
                    "aria-level": level + BODY_HEADING_OFFSET > LOWEST_HEADING_LEVEL ? level + BODY_HEADING_OFFSET : null,
                },
                children: [...heading.childNodes],
            });
            heading.replaceWith(replacement);
        }
    }
    /** 本文の見出しを、本文のスクロール領域の中で画面に入れる（本文に無ければ false） */
    function scrollToHeading({ root, slug }) {
        const target = root.querySelector(`[data-heading="${CSS.escape(slug)}"]`);
        if (target === null)
            return false;
        target.scrollIntoView({ block: "start" });
        return true;
    }
    /** 用語のツールチップを隠すまで待つミリ秒（印からツールチップへポインターを動かす間に消さない） */
    const TIP_HIDE_DELAY_MS = 150;
    /** 用語のツールチップを隠す待ちのタイマー */
    let tipTimer = 0;
    /** 用語のツールチップ（1 つを使い回す。重ねる面の上にも出せるよう、ポップオーバーにする）。ツールチップに乗せている間は消さず、Esc で消す */
    function termTip() {
        const existing = document.getElementById(MindmapPreview.TERM_TIP_ID);
        if (existing !== null)
            return existing;
        const tip = MindmapPreview.h({ tag: "div", attrs: { id: MindmapPreview.TERM_TIP_ID, class: "term-tip", role: "tooltip", popover: "manual" } });
        tip.addEventListener("mouseenter", () => window.clearTimeout(tipTimer));
        tip.addEventListener("mouseleave", () => hideTermTip(false));
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape")
                hideTermTip(true);
        });
        document.body.append(tip);
        return tip;
    }
    /** 用語の印の下（収まらなければ上）にツールチップを出す */
    function showTermTip({ mark, term }) {
        const tip = termTip();
        window.clearTimeout(tipTimer);
        tip.replaceChildren(MindmapPreview.h({ tag: "span", attrs: { class: "tt-head" }, children: [term.title, MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [term.id] })] }), MindmapPreview.h({ tag: "span", attrs: { class: "tt-body" }, children: [term.meaning ?? ""] }));
        if (!tip.matches(":popover-open"))
            tip.showPopover();
        const gap = 6;
        const margin = 8;
        const rect = mark.getBoundingClientRect();
        const below = innerHeight - rect.bottom - gap - margin >= tip.offsetHeight;
        tip.style.left = `${Math.max(margin, Math.min(rect.left, innerWidth - tip.offsetWidth - margin))}px`;
        tip.style.top = `${below ? rect.bottom + gap : rect.top - gap - tip.offsetHeight}px`;
    }
    /** 用語のツールチップを隠す（`now` が偽のときは、少し待ってから） */
    function hideTermTip(now) {
        window.clearTimeout(tipTimer);
        const hide = () => {
            const tip = document.getElementById(MindmapPreview.TERM_TIP_ID);
            if (tip?.matches(":popover-open") === true)
                tip.hidePopover();
        };
        if (now)
            hide();
        else
            tipTimer = window.setTimeout(hide, TIP_HIDE_DELAY_MS);
    }
    /** 本文の用語の印に乗せる・フォーカスするとツールチップを出し、外れると隠す（本文の要素に委ねて付ける） */
    function attachTermTips({ root, index }) {
        /** イベントの先の用語の印と、その用語 */
        const termOf = (event) => {
            const mark = event.target.closest?.("a.term") ?? null;
            const term = index.byId.get(mark?.getAttribute("data-id") ?? "")?.item;
            return mark === null || term === undefined ? null : { mark, term };
        };
        for (const type of ["mouseover", "focusin"]) {
            root.addEventListener(type, (event) => {
                const found = termOf(event);
                if (found !== null)
                    showTermTip(found);
            });
        }
        root.addEventListener("mouseout", (event) => {
            if (termOf(event) !== null)
                hideTermTip(false);
        });
        root.addEventListener("focusout", (event) => {
            if (termOf(event) !== null)
                hideTermTip(true);
        });
        // 印を押して項目へ移るときは、ツールチップを残さない
        root.addEventListener("click", (event) => {
            if (termOf(event) !== null)
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
    /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
    function detailPanel(props) {
        const { id, index, full, on, comment, highlight = null, diff = null, heading = null } = props;
        const kind = index.byId.get(id)?.kind;
        // 中にフォーカスできる要素が無い項目でも、キーボードで送れるように領域ごとフォーカスできるようにする
        const body = MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "詳細の本文" },
            children: [detailBody({ id, index, on, reviews: comment === null ? null : comment.reviews, view: resolveDiffView({ id, index, diff }) })],
        });
        const head = detailHead(props);
        // 見出しと下端の入力の間の本文だけをスクロールする
        const footer = comment === null ? null : MindmapPreview.sendForm(comment.form);
        let root;
        if (!full) {
            root = MindmapPreview.h({
                tag: "aside",
                attrs: { class: `panel${kind === "docs" ? " wide" : ""}`, "aria-label": "詳細" },
                children: [head, body, footer],
            });
        }
        else {
            const dialog = MindmapPreview.h({ tag: "dialog", attrs: { class: "full", "aria-label": "詳細の全画面" }, children: [head, body, footer] });
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
        attachTermTips({ root: body, index });
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
// コメントの一覧。見ている画面に重ねて左から出すパネルに、レビュー中のコメントを並べ、チェックしたものだけをまとめて送る。
var MindmapPreview;
(function (MindmapPreview) {
    /** コメントの ID の連番 */
    function commentNumber(id) {
        return Number(id.replace(/^\D+-/, ""));
    }
    /** 送った結果の文言（印と文）。結果が無いときは null */
    function outcomeContent({ result, checkedCount }) {
        if (result === null) {
            // チェックが 0 件
            return checkedCount === 0 ? [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: ["送るコメントにチェックを付けてください。"] })] : null;
        }
        if (result.kind === "sending") {
            return [MindmapPreview.h({ tag: "span", attrs: { class: "spinner", "aria-hidden": "true" } }), MindmapPreview.h({ tag: "span", children: ["送っています"] })];
        }
        if (result.kind === "sent") {
            const time = result.at === undefined ? "" : MindmapPreview.formatJst(result.at).slice(-5);
            return [MindmapPreview.icon("check"), MindmapPreview.h({ tag: "span", children: [`${result.count ?? 0} 件を送りました（${time}）。`] })];
        }
        if (result.kind === "stale") {
            return [MindmapPreview.icon("alert"), MindmapPreview.h({ tag: "span", children: [`送れませんでした。箇所が合わないコメントが ${result.count ?? 0} 件あります。`] })];
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
    /** 行の向けた項目（押すとその項目を開く。項目を指さない・消えた項目は押せない） */
    function targetCell(item, props) {
        // 項目を指さない
        if (item.target === null)
            return MindmapPreview.h({ tag: "span", attrs: { class: "row-target none" }, children: ["項目を指さない"] });
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
    /** 本文をその場で直す入力欄と「やめる」「直す」 */
    function editForm(item, props) {
        const field = MindmapPreview.h({
            tag: "textarea",
            attrs: {
                name: "body",
                rows: 2,
                "aria-label": `${item.id} へのコメントの本文`,
                "data-focus": `edit:${item.id}`,
                onkeydown: (event) => {
                    if (event.key === "Escape") {
                        event.stopPropagation();
                        props.on.cancelEdit();
                    }
                },
            },
            children: [props.editBody ?? item.body],
        });
        const message = MindmapPreview.h({ tag: "p", attrs: { class: "send-msg failed", role: "alert" }, children: props.editError ? [MindmapPreview.icon("alert"), props.editError] : [] });
        return MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "row-edit",
                novalidate: true,
                onsubmit: (event) => {
                    event.preventDefault();
                    // 空白だけは送らない
                    if (field.value.trim() === "") {
                        message.replaceChildren(MindmapPreview.icon("alert"), "コメントを入れてから直してください。");
                        field.focus();
                        return;
                    }
                    props.on.saveEdit(item.id, field.value);
                },
            },
            children: [
                field,
                message,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-edit-actions" },
                    children: [
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn ghost", type: "button", onclick: props.on.cancelEdit }, children: ["やめる"] }),
                        MindmapPreview.h({ tag: "button", attrs: { class: "btn primary", type: "submit" }, children: ["直す"] }),
                    ],
                }),
            ],
        });
    }
    /** コメントの行 */
    function commentRow(item, props) {
        const reason = props.stale.get(item.id);
        const label = item.target === null ? "項目を指さないコメント" : `${item.target} へのコメント`;
        return MindmapPreview.h({
            tag: "li",
            attrs: {
                class: `row${item.id === props.selected ? " selected" : ""}${reason === undefined ? "" : " stale"}`,
                "data-comment": item.id,
            },
            children: [
                MindmapPreview.h({
                    tag: "input",
                    attrs: {
                        type: "checkbox",
                        class: "row-check",
                        checked: props.checked.has(item.id),
                        "aria-label": `${label}を送る`,
                        "data-focus": `check:${item.id}`,
                        onchange: (event) => props.on.check(item.id, event.target.checked),
                    },
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-main" },
                    children: [
                        targetCell(item, props),
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
                        props.editing === item.id ? editForm(item, props) : MindmapPreview.h({ tag: "p", attrs: { class: "review-body" }, children: [item.body] }),
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
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "row-actions" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "icon-btn",
                                type: "button",
                                "aria-label": `${label}を直す`,
                                title: "直す",
                                "data-focus": `edit-open:${item.id}`,
                                onclick: () => props.on.edit(item.id),
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
                                "data-focus": `remove:${item.id}`,
                                onclick: () => props.on.remove(item.id),
                            },
                            children: [MindmapPreview.icon("trash")],
                        }),
                    ],
                }),
            ],
        });
    }
    /** 削除した行（元の場所に「コメントを削除しました。」と「元に戻す」を出す） */
    function removedRow(item, props) {
        return MindmapPreview.h({
            tag: "li",
            attrs: { class: "row removed", "data-comment": item.id },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "removed-msg" }, children: ["コメントを削除しました。"] }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: { class: "btn ghost", type: "button", "data-focus": `restore:${item.id}`, onclick: () => props.on.restore(item.id) },
                    children: [MindmapPreview.icon("undo"), "元に戻す"],
                }),
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
    /** コメントの一覧を返す */
    function commentsPanel(props) {
        const { items, removed, checked, result, on } = props;
        const checkedCount = items.filter((item) => checked.has(item.id)).length;
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
                    items.length === 0
                        ? null
                        : selectAllBox({
                            ids: items.map((item) => item.id),
                            checked,
                            onChange: on.checkAll,
                        }),
                    items.length === 0
                        ? null
                        : MindmapPreview.h({ tag: "span", attrs: { class: "send-count" }, children: [`${checkedCount} / ${items.length} 件`] }),
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
        // 消したコメントは元の場所（ID の連番の順）に出す
        const rows = [...items.map((item) => ({ item, gone: false })), ...removed.map((item) => ({ item, gone: true }))].sort((a, b) => commentNumber(a.item.id) - commentNumber(b.item.id));
        return MindmapPreview.h({
            tag: "aside",
            attrs: { class: "comments-panel", "aria-label": "コメントの一覧" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-head" },
                    children: [
                        MindmapPreview.h({ tag: "h2", children: ["レビュー中のコメント", MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [items.length] })] }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "コメントの一覧を閉じる", "data-focus": "close", onclick: on.close },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                band,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "comments-body" },
                    children: [
                        isEmpty
                            ? MindmapPreview.h({ tag: "p", attrs: { class: "comments-empty" }, children: [MindmapPreview.icon("comment"), "レビュー中のコメントはありません。"] })
                            : MindmapPreview.h({
                                tag: "ul",
                                attrs: { class: "comments-list" },
                                children: rows.map(({ item, gone }) => (gone ? removedRow(item, props) : commentRow(item, props))),
                            }),
                    ],
                }),
                MindmapPreview.h({ tag: "div", attrs: { class: "comments-free" }, children: [MindmapPreview.sendForm(props.free)] }),
            ],
        });
    }
    MindmapPreview.commentsPanel = commentsPanel;
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
            /** 結果 1 件のボタン。完全に一致するまとまりでは、種類を添える */
            const resultButton = (hit, withKind) => {
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
                                withKind ? MindmapPreview.h({ tag: "span", attrs: { class: "sr-kind" }, children: [MindmapPreview.KIND_LABEL[hit.kind]] }) : null,
                                MindmapPreview.h({ tag: "br" }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "sr-sub" }, children: [item === undefined ? "" : summaryOf(item)] }),
                            ],
                        }),
                    ],
                });
            };
            // 完全に一致する項目は種類の見出しより上の「完全に一致」に出し、下の種類のまとまりには重ねない
            const exact = hits.filter((hit) => hit.exact);
            const top = exact.length === 0
                ? []
                : [MindmapPreview.h({ tag: "h3", attrs: { class: "sr-exact" }, children: ["完全に一致"] }), ...exact.map((hit) => resultButton(hit, true))];
            const groups = MindmapPreview.KIND_KEYS.flatMap((kind) => {
                const ofKind = hits.filter((hit) => hit.kind === kind && !hit.exact);
                return ofKind.length === 0
                    ? []
                    : [MindmapPreview.h({ tag: "h3", children: [MindmapPreview.KIND_LABEL[kind]] }), ...ofKind.map((hit) => resultButton(hit, false))];
            });
            results.replaceChildren(...top, ...groups);
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
        const parts = MindmapPreview.diffLineParts(before.endsWith("\n") ? before : `${before}\n`, source.endsWith("\n") ? source : `${source}\n`);
        if (parts === null)
            return raw;
        raw.classList.add("df-raw");
        raw.replaceChildren(...MindmapPreview.rawDiffLines(parts));
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
                            children: [MindmapPreview.icon("back"), "本文へ戻る"],
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
// つながり。全種類の項目を、関連（依存・関連・根拠・進めるタスク）でつないで 3D で描く。ライブラリを使わず、平たい円をキャンバスへ透視で描く。
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
                for (const target of item[key] ?? []) {
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
    /** 状態を持つ種類（検討事項・タスク・資料）の状態を重ねた並び（つながりの状態の条件の値の順） */
    const GRAPH_STATUS_ORDER = [
        ...new Set([...MindmapPreview.DECISION_STATUSES, ...MindmapPreview.TASK_STATUSES, ...MindmapPreview.DOC_STATUSES]),
    ];
    /** つながりで絞る条件（種類・状態・タグ）の定義を返す。値は索引の項目（`{kind, item}`）から取る */
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
            { key: "tags", label: "タグ", get: (row) => entry(row).item.tags ?? [] },
        ];
    }
    MindmapPreview.graphConditions = graphConditions;
    /** 線の種類ごとの見た目（実線・点線・破線・一点鎖線） */
    const LINK_DASH = {
        depends: [],
        related: [1.5, 3],
        source: [6, 4],
        for: [10, 3, 2, 3],
    };
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
    /** 透視の基準の長さ */
    const FOCAL = 700;
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
    // 123: ===== ロック: 注目の起点を 1 つの項目に留める。ページを開いている間だけ保ち、タブを行き来しても残す =====
    /** 2 回押しとみなす間隔（ms）と位置のずれ（px） */
    const DOUBLE_TAP_MS = 450;
    const DOUBLE_TAP_PX = 24;
    /** 鍵が震えて収まるまでの時間（ms）・震えの往復の回数・左右の振れ幅（px）・上を軸に傾く角度（rad）・震え始めに大きくする割合・赤い光のにじみの半径（px） */
    const SHAKE_MS = 1000;
    const SHAKE_WAVES = 5;
    const SHAKE_SHIFT = 6;
    const SHAKE_SWING = 0.45;
    const SHAKE_GROW = 0.45;
    const SHAKE_GLOW = 4;
    /** ネットワークの鍵の一辺（px）と、名前・コメントの印との隙間（px） */
    const KEY_SIZE = 12;
    const KEY_GAP = 3;
    /** 状態の印の大きさと名前との間（名前の文字の高さに対する割合） */
    const STATUS_MARK_SCALE = 0.8;
    const STATUS_MARK_GAP = 0.4;
    /** ロックしている項目（ネットワークと検討事項のマップで別々に持つ）。モックの見本の状態は、開く前に `window.MOCK123.lock` へ入れておく */
    const locked = { graph: window.MOCK123?.lock?.graph ?? null, map: window.MOCK123?.lock?.map ?? null };
    /** ロックしている項目の ID */
    function lockOf(key) {
        return locked[key];
    }
    MindmapPreview.lockOf = lockOf;
    /** 押した項目（余白なら null）と詳細を開いている項目から、ロックの付け外し・詳細の切り替え・鍵の震えのどれをするかを返す。ネットワークとマップで同じ規則を使う */
    function lockTap({ key, id, open }) {
        const now = locked[key];
        if (now !== null) {
            // ロックした項目は、詳細を開いている状態でもう一度押したときだけ外す。開いていなければ詳細を戻すだけ
            if (id === now) {
                if (open !== id)
                    return "open";
                locked[key] = null;
                return "unlock";
            }
            // 詳細を開いている別の項目をもう一度押した・余白を押したときは、ロック・詳細・表示を変えずに知らせる
            return id === null || id === open ? "shake" : "open";
        }
        if (id === null)
            return "blank";
        // ロックしていないとき: 詳細を開いている項目をもう一度押したらロックする
        if (id === open) {
            locked[key] = id;
            return "lock";
        }
        return "open";
    }
    MindmapPreview.lockTap = lockTap;
    /** 震え始めてからの時間で、収まり具合（1 → 0）と振れ（-1〜1）を返す */
    function shakeAt(elapsed) {
        return { decay: 1 - elapsed / SHAKE_MS, wave: Math.sin((elapsed / SHAKE_MS) * Math.PI * 2 * SHAKE_WAVES) };
    }
    /** 震える鍵の赤（ライトとダークで濃さを変える） */
    function shakeColor() {
        const dark = document.documentElement.dataset["theme"] === "dark";
        return getComputedStyle(document.documentElement).getPropertyValue(dark ? "--red-300" : "--red-700").trim();
    }
    /** 要素の鍵（検討事項のマップの節の鍵）を、ネットワークの鍵と同じ動きで震わせる。毎コマ当て、描き直されても `find` で今の要素を引いて続きから震わせる */
    let elementShakeAt = Number.NEGATIVE_INFINITY;
    function shakeKeyElement(find) {
        const running = performance.now() - elementShakeAt < SHAKE_MS;
        elementShakeAt = performance.now();
        if (running)
            return;
        const step = (now) => {
            const key = find();
            const elapsed = Math.max(0, now - elementShakeAt);
            if (elapsed >= SHAKE_MS) {
                key?.removeAttribute("style");
                return;
            }
            if (key !== null) {
                const { decay, wave } = shakeAt(elapsed);
                const color = shakeColor();
                // 南京錠のように上を軸に振れ、大きくなって赤く光り、だんだん収まる
                key.style.cssText = `transform-origin: 50% 0; transform: translateX(${wave * SHAKE_SHIFT * decay}px) rotate(${wave * SHAKE_SWING * decay}rad) scale(${1 + SHAKE_GROW * decay}); color: ${color}; filter: drop-shadow(0 0 ${SHAKE_GLOW * decay}px ${color});`;
            }
            requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }
    MindmapPreview.shakeKeyElement = shakeKeyElement;
    const LOCK_PATH = new Path2D("M7 11V7a5 5 0 0 1 10 0v4");
    const UNLOCK_PATH = new Path2D("M7 11V7a5 5 0 0 1 9.9-1");
    /** 鍵のマーク（24 の枠の線画）を、中心と一辺を指定してキャンバスに描く。振れは鍵の上端を軸にする */
    function drawKeyIcon({ context, x, y, size, closed, color, alpha, swing }) {
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
    /** 状態の印（一覧と同じ SVG）と資料の成果物の箱を、今の配色で絵にして取っておく。読み込み中は null */
    const statusImages = new Map();
    function statusImage(item, ringColor) {
        const theme = document.documentElement.dataset["theme"] ?? "";
        const deliverable = item["deliverable"] === true;
        const cacheKey = `${deliverable ? "deliverable" : item.status}|${theme}`;
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
        return image.complete && image.naturalWidth > 0 ? image : null;
    }
    /** 開いているつながりの画面（外から玉を選ぶ・色を変える・コメントの件数を差し替えるために覚える） */
    let live = null;
    /** 詳細パネルで開いた項目を、つながりの画面でも選んだ状態にする（画面を開いていなければ何もしない） */
    function selectGraphItem(id) {
        live?.select(id);
    }
    MindmapPreview.selectGraphItem = selectGraphItem;
    /** 描いているつながりの、名前の横の印に使う件数を差し替える（玉と線と視点は作り直さず、次のコマから新しい件数で印を置く。描いていなければ何もしない） */
    function setGraphComments(counts) {
        live?.setComments(counts);
    }
    MindmapPreview.setGraphComments = setGraphComments;
    /** つながりの画面を返す。`selected` は最初に選んでおく項目、`look` はつながりの見た目（値ごとの描き分けは別の作業が作る） */
    function graphScreen({ index, on, filters, drawerOpen, selected = null, look = MindmapPreview.BUILTIN_LOOK, defaultLook = look, comments, }) {
        // ===== 絞り込み: 条件に合う項目の ID =====
        const conditions = graphConditions();
        const rows = [...index.byId].map(([id, entry]) => ({ id, ...entry }));
        const shownIds = new Set(MindmapPreview.filterRows({ rows, columns: conditions, filters }).map((row) => row.id));
        // ===== 状態 =====
        const canvas = MindmapPreview.h({ tag: "canvas", attrs: { id: "graph-canvas", class: "g3-wrap", role: "img", "aria-label": "すべての項目のネットワーク" } });
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
        // 123: 今当てている見た目。キャンバスの右上の、アイコンの無いドロップダウンで選ぶ（ワークスペースの既定の見た目に「既定」を添える）
        let lookNow = look;
        const lookPick = MindmapPreview.h({
            tag: "label",
            attrs: { class: "look-pick" },
            children: [
                MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["ネットワークの見た目"] }),
                MindmapPreview.h({
                    tag: "select",
                    attrs: {
                        onchange: (event) => {
                            lookNow = event.target.value;
                            root.dataset["look"] = lookNow;
                            labelCache.clear();
                            on.look?.(lookNow);
                        },
                    },
                    children: MindmapPreview.NETWORK_LOOKS.map((option) => MindmapPreview.h({
                        tag: "option",
                        attrs: { value: option.key, selected: option.key === look },
                        children: [option.key === defaultLook ? `${option.label}（既定）` : option.label],
                    })),
                }),
            ],
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
        /** 名前の横の印に使う件数 */
        let commentCounts = comments ?? {};
        /** 玉の ID → 名前の横に置いた印 */
        const markSlots = new Map();
        let balls = [];
        let ballById = new Map();
        let links = [];
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
        // 123: 注目の起点はロックした項目、ロックしていなければ詳細を開いている項目
        /** 見た目の描き方へ渡す、玉の並びと視点の距離（星図の球・深宇宙の塵が、作った値をここに取っておく） */
        let scene = { nodes: [], idx: new Map(), dist: 520 };
        /** 鍵が震え始めた時刻 */
        let shakeStart = Number.NEGATIVE_INFINITY;
        /** 直前に押した玉（素早い 2 回目を、詳細が開いて枠がずれても同じ玉への 2 回押しとして扱う） */
        let lastTap = null;
        const anchorOf = (id) => {
            const lockedId = lockOf("graph");
            return lockedId !== null && ballById.has(lockedId) ? lockedId : id;
        };
        let focus = selected;
        let hover = null;
        let current = selected;
        let lastInput = 0;
        let birth = performance.now();
        let projected = new Map();
        let width = 0;
        let height = 0;
        let dpr = 1;
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
            // 123: 見た目の描き方が読む名前（半径・線の数・またたきの位相）を玉に持たせる
            for (const ball of balls) {
                ball.r = ball.radius;
                ball.deg = ball.degree;
                ball.seed = window.STELLA.hash(ball.id);
            }
            scene = { nodes: balls, idx: new Map(balls.map((ball, position) => [ball.id, position])), dist: camera.distance };
            links = graph.links.flatMap((link) => {
                const s = ballById.get(link.source);
                const t = ballById.get(link.target);
                return s === undefined || t === undefined ? [] : [{ s, t, type: link.type }];
            });
            settle(balls, links);
            // 全体が枠に収まる距離（外れた玉に引っぱられないよう、近い順に 9 割目の玉までの半径を使う）
            const radii = balls.map((ball) => Math.hypot(ball.x, ball.y, ball.z)).sort((a, b) => a - b);
            const reach = Math.max(40, radii[Math.floor(radii.length * 0.9)] ?? 40);
            const box = Math.max(1, Math.min(canvas.clientWidth || 600, canvas.clientHeight || 460));
            camera.fit = ((FOCAL * reach) / (box * 0.42) + reach * 0.4) * 0.72;
            camera.distance = camera.distanceTarget = camera.fit;
            camera.center = { x: 0, y: 0, z: 0 };
            camera.centerTarget = { x: 0, y: 0, z: 0 };
            birth = performance.now();
            select(current);
        };
        /** 項目を選ぶ（その玉へゆっくり寄る）。選ぶのをやめたら、全体を見る位置へ戻す */
        const select = (id) => {
            current = id;
            // 123: ロック中は、ほかの項目を開いても中心と強調をロックした項目に留める
            const anchor = anchorOf(id);
            const ball = anchor === null ? undefined : ballById.get(anchor);
            focus = ball?.id ?? hover;
            camera.distanceTarget = ball === undefined ? camera.fit : camera.fit * 0.38;
            if (ball === undefined)
                camera.centerTarget = { x: 0, y: 0, z: 0 };
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
            const f = FOCAL / (z2 + camera.distance);
            return { sx: width / 2 + x1 * f, sy: height / 2 + y1 * f, f, z: z2 };
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
        const baseScale = () => FOCAL / camera.fit;
        const radiusOf = (ball, scale) => ball.radius * 1.05 * (scale / baseScale());
        /** 画面の点にある、いちばん手前の玉 */
        const hitTest = (x, y) => {
            let best = null;
            let bestDepth = Number.POSITIVE_INFINITY;
            for (const ball of balls) {
                const p = projected.get(ball.id);
                if (p === undefined || p.z + camera.distance <= 10)
                    continue;
                const reach = Math.max(8, radiusOf(ball, p.f)) + 4;
                if (Math.hypot(p.sx - x, p.sy - y) < reach && p.z < bestDepth) {
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
            // ほとんど動かさずに離した: 玉を押した
            if (drag !== null && moved < 5) {
                // 123: 押した玉（余白なら null）で、ロックの付け外し・詳細の切り替え・鍵の震えを決める
                const now = performance.now();
                const second = lastTap !== null && now - lastTap.time < DOUBLE_TAP_MS && Math.hypot(event.clientX - lastTap.x, event.clientY - lastTap.y) < DOUBLE_TAP_PX;
                const target = second ? (ballById.get(lastTap.id) ?? null) : hitTest(event.clientX - rect.left, event.clientY - rect.top);
                lastTap = target !== null && !second ? { id: target.id, time: now, x: event.clientX, y: event.clientY } : null;
                const action = lockTap({ key: "graph", id: target?.id ?? null, open: current });
                if (action === "shake")
                    shakeStart = now;
                else if (action === "lock" || action === "unlock")
                    select(current);
                else if (action === "open" && target !== null) {
                    select(target.id);
                    on.open(target.id);
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
                const f = FOCAL / old;
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
            pullNear();
            // 離した後の滑りと、何もしていないときのごくゆっくりした自動の回転
            if (drag === null) {
                camera.yawTarget += camera.yawSpeed;
                camera.pitchTarget = Math.max(-1.3, Math.min(1.3, camera.pitchTarget + camera.pitchSpeed));
                camera.yawSpeed *= 0.955;
                camera.pitchSpeed *= 0.93;
                if (now - lastInput > IDLE_BEFORE_ROTATE_MS && hover === null)
                    camera.yawTarget += AUTO_ROTATE_STEP;
            }
            camera.yaw += (camera.yawTarget - camera.yaw) * 0.07;
            camera.pitch += (camera.pitchTarget - camera.pitch) * 0.07;
            const anchorNow = anchorOf(current);
            const selectedBall = anchorNow === null ? undefined : ballById.get(anchorNow);
            // 123: モックの「鍵の震え」の見本では、押さなくても一定の間隔で震えを繰り返す
            if (window.MOCK123?.demo === "shake" && now - shakeStart > 1800)
                shakeStart = now;
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
            // 123: 線と玉は、見た目ごとの描き方（stella.js）へ渡して描く。線は画面に入るものだけを、奥行きの濃さと沈み具合つきで渡す
            const lookStyle = window.STELLA.styles[lookNow];
            const dark = document.documentElement.dataset["theme"] === "dark";
            const linkViews = [];
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
                linkViews.push({ l: link, a, b, dep: depth, fade: Math.min(link.s.fade, link.t.fade), ca: colors.kind[link.s.kind], cb: colors.kind[link.t.kind] });
            }
            // 注目している項目とつながる線（この上を光が流れる）
            const focusLinks = [];
            if (focused !== null) {
                const from = projected.get(focused);
                const focusedBall = ballById.get(focused);
                for (const link of links) {
                    if (link.s.id !== focused && link.t.id !== focused)
                        continue;
                    const other = link.s.id === focused ? link.t : link.s;
                    const to = projected.get(other.id);
                    if (from === undefined || to === undefined || focusedBall === undefined)
                        continue;
                    if (from.z + camera.distance <= 10 || to.z + camera.distance <= 10)
                        continue;
                    focusLinks.push({ l: link, from, to, other, cf: colors.kind[focusedBall.kind], ct: colors.kind[other.kind] });
                }
            }
            // 玉: 奥から順に、大きさ・濃さ・沈み具合を計算して渡す。注目しているときはつながらないものを沈める（ロック中に詳細を開いている項目は沈めない）
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
                    n: ball,
                    p,
                    depth,
                    dim: ball.fade,
                    rad: Math.max(1.2, r0 * ease),
                    close,
                    strong: near.has(ball.id) || ball.id === hover,
                    selected: ball.id === current,
                    hover: ball.id === hover,
                    color: colors.kind[ball.kind],
                    seed: ball.seed,
                    rank,
                });
            }
            scene.dist = camera.distance;
            /** 天球の向き: 中心を引かずに回転だけをかける（遠くの星・星図の線に使う） */
            const rotate = (x, y, z) => {
                const cosYaw = Math.cos(camera.yaw);
                const sinYaw = Math.sin(camera.yaw);
                const cosPitch = Math.cos(camera.pitch);
                const sinPitch = Math.sin(camera.pitch);
                const x1 = x * cosYaw - z * sinYaw;
                const z1 = x * sinYaw + z * cosYaw;
                return { x: x1, y: y * cosPitch - z1 * sinPitch, z: y * sinPitch + z1 * cosPitch };
            };
            const env = { ctx: context, W: width, H: height, dpr, now, dark, C: colors, G: scene, sel: focused, near, k0: baseK, ease, rot: rotate, proj: project, links: linkViews, selLinks: focusLinks, nodes: views, dash: LINK_DASH };
            context.globalCompositeOperation = "source-over";
            lookStyle.draw(env);
            context.globalCompositeOperation = "source-over";
            context.setLineDash([]);
            // 鍵を置く玉: ロックした項目。ロックしていなければ、詳細を開いている項目
            const lockedId = lockOf("graph");
            const keyView = views.find((view) => view.n.id === (lockedId !== null && ballById.has(lockedId) ? lockedId : current)) ?? null;
            const keyClosed = keyView !== null && keyView.n.id === lockedId;
            // 鍵を出すか: 閉じた鍵はロック中いつも、開いた鍵は詳細を開いている玉にカーソルを乗せたときだけ
            const keyShown = keyView !== null && (keyClosed || hover === keyView.n.id || window.MOCK123?.demo === "open");
            /** 鍵とコメントの印の順（A: 名前・鍵・コメントの印 / B: 名前・コメントの印・鍵）。モックで見比べるために切り替える */
            const keyFirst = (window.MOCK123?.order ?? "A") === "A";
            /** 鍵の中心（名前が出ない距離では、玉の右上の札） */
            let keySpot = null;
            /** このコマに印を置いた玉 */
            const markedBalls = new Set();
            for (const view of views) {
                const { n: ball, p, depth, close, strong, rank } = view;
                const radius = view.rad;
                const marked = view.selected || view.hover;
                // 名前: 玉と同じ倍率で大きさが変わる（玉の幅に英字 6 文字ほど）。いつもは薄く、注目している項目とつながる項目ははっきり出す
                const scale = p.f / baseK;
                const fontSize = 4.6 * scale;
                const alpha = (strong ? 0.85 : 0.42 * ball.fade) * depth ** 1.4 * Math.max(0, Math.min(1, (fontSize - 3.5) / 2.5));
                if (!(alpha > 0.03 && ease > 0.9 && onScreen(p.sx, p.sy - radius, width, height, 400)))
                    continue;
                const color = view.selected ? colors.ring : (lookStyle.labelColor?.(env, view) ?? colors.label);
                // 毎コマ文字を作らず、画像に倍率をかけて置く
                const image = labelImage(ball, marked, color);
                const k = (dpr * fontSize) / 10 / LABEL_RESOLUTION;
                const nameBottom = p.sy - radius * (lookStyle.labelLift ?? 1) - 3 * scale;
                context.globalAlpha = alpha * close;
                context.setTransform(k, 0, 0, k, dpr * p.sx, dpr * nameBottom);
                context.drawImage(image, -image.width / 2, -image.height);
                context.setTransform(dpr, 0, 0, dpr, 0, 0);
                const nameWidth = (image.width / LABEL_RESOLUTION) * (fontSize / 10);
                const nameHeight = LABEL_HEIGHT * (fontSize / 10);
                const nameCenterY = nameBottom - nameHeight / 2;
                const nameRight = p.sx + nameWidth / 2;
                // 状態の印: 注目しているときだけ、起点とつながる項目の名前の左に、名前と同じ濃さで置く（資料の成果物は箱）
                const item = index.byId.get(ball.id)?.item;
                if (focused !== null && near.has(ball.id) && item !== undefined) {
                    const statusMarkImage = statusImage(item, colors.ring);
                    if (statusMarkImage !== null) {
                        const size = fontSize * STATUS_MARK_SCALE;
                        context.globalAlpha = alpha * close;
                        context.drawImage(statusMarkImage, p.sx - nameWidth / 2 - fontSize * STATUS_MARK_GAP - size, nameCenterY - size / 2, size, size);
                    }
                }
                // コメントの印: 名前を文字 8px 以上で描いた、件数のある玉に、名前と同じ濃さで置く
                const count = commentCounts[ball.id] ?? 0;
                const hasComment = count > 0 && fontSize >= COMMENT_MARK_MIN_FONT;
                const slot = hasComment ? markSlotOf(ball.id, count) : null;
                const keyHere = view === keyView && keyShown;
                // A は名前のすぐ右に鍵、その右にコメントの印。B は名前のすぐ右にコメントの印、その右に鍵。鍵を出さないときは鍵の幅を空けない
                const keyWidth = keyHere ? KEY_GAP + KEY_SIZE : 0;
                const left = nameRight + (keyFirst ? keyWidth : 0) + COMMENT_MARK_GAP;
                if (keyHere) {
                    const keyLeft = nameRight + (keyFirst || slot === null ? 0 : COMMENT_MARK_GAP + slot.width) + KEY_GAP;
                    keySpot = { x: keyLeft + KEY_SIZE / 2, y: nameCenterY, badge: false, alpha: alpha * close };
                }
                if (slot !== null) {
                    const top = nameCenterY - slot.height / 2;
                    // 名前と印が描く枠（上端は名前か印の高いほう、下端は低いほう）が、キャンバスに収まるときだけ置く
                    const frameTop = Math.min(top, nameCenterY - nameHeight / 2);
                    const frameBottom = Math.max(top + slot.height, nameCenterY + nameHeight / 2);
                    const fits = p.sx - nameWidth / 2 >= 0 && left + slot.width <= width && frameTop >= 0 && frameBottom <= height;
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
            if (keyView !== null) {
                // 名前が出ていない遠い距離では、玉の右上に札に入れて置く
                const spot = keySpot ?? { x: keyView.p.sx + keyView.rad * 0.8 + 8, y: keyView.p.sy - keyView.rad * 0.8 - 8, badge: true, alpha: 1 };
                if (keyShown) {
                    // 外れない操作をされた直後は、赤くして左右に震わせ、だんだん収める
                    const elapsed = now - shakeStart;
                    const shaking = keyClosed && elapsed < SHAKE_MS;
                    const { decay, wave } = shaking ? shakeAt(elapsed) : { decay: 0, wave: 0 };
                    const x = spot.x + wave * SHAKE_SHIFT * decay;
                    const red = shakeColor();
                    const keyColor = shaking ? red : keyClosed ? colors.ring : colors.label;
                    if (shaking) {
                        context.globalAlpha = 0.55 * decay;
                        context.drawImage(window.STELLA.glow(red, 2), x - 22, spot.y - 22, 44, 44);
                    }
                    if (spot.badge) {
                        context.globalAlpha = keyClosed ? 0.95 : 0.6;
                        context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--surface").trim();
                        context.beginPath();
                        context.arc(x, spot.y, KEY_SIZE * 0.85, 0, Math.PI * 2);
                        context.fill();
                        context.strokeStyle = keyColor;
                        context.lineWidth = 1;
                        context.stroke();
                    }
                    drawKeyIcon({ context, x, y: spot.y, size: KEY_SIZE * (1 + SHAKE_GROW * decay), closed: keyClosed, color: keyColor, alpha: keyClosed ? 0.95 : 0.45, swing: wave * SHAKE_SWING * decay });
                }
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
    /** そのタブの「前回開いてから」の始まりの日時を残す sessionStorage のキー。あれば `POST /api/opened` を呼ばない（同じタブで読み込み直しても範囲を変えない） */
    MindmapPreview.SINCE_KEY = "mindmap-since";
    /** 入力欄のキー。向けた先（`target` と `loc` の組）を 1 つの文字列にする */
    function formKey(target, loc) {
        return JSON.stringify([target, loc?.kind ?? null, loc?.start ?? null, loc?.end ?? null, loc?.key ?? null, loc?.text ?? null]);
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
    /** 画面の名前（つながりは種類のタブに無いので、ここで持つ） */
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
        return { theme: null, columns: {}, look: null, kinds: null, diffSel: null };
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
            return parsed;
        }
        catch {
            return defaultPrefs();
        }
    }
    MindmapPreview.loadPrefs = loadPrefs;
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
        // 上書きを持つ項目の名前を、見た目・種類・ライト / ダーク・表の列の順に並べる
        const overrides = [
            ...(prefs.look === null ? [] : ["ネットワークの見た目"]),
            ...(prefs.kinds === null ? [] : ["表示する種類"]),
            ...(prefs.theme === null ? [] : ["ライト / ダーク"]),
            ...MindmapPreview.KIND_KEYS.filter((kind) => prefs.columns[kind] !== undefined).map((kind) => `表の列（${MindmapPreview.KIND_LABEL[kind]}）`),
        ];
        return {
            look: prefs.look ?? defaultLook,
            kinds: prefs.kinds === null ? defaultKinds : new Set(prefs.kinds),
            defaultLook,
            defaultKinds,
            overrides,
        };
    }
    MindmapPreview.resolveDisplay = resolveDisplay;
    /** 「既定に戻す」で、見た目・表示する種類・ライト / ダーク・表の列を外した設定を返す（`diffSel` は残し、渡した設定は変えない） */
    function clearOverrides(prefs) {
        return { ...prefs, theme: null, look: null, kinds: null, columns: {} };
    }
    MindmapPreview.clearOverrides = clearOverrides;
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
    /** そのタブの「前回開いてから」の始まりを決める。同じタブで読み込み直したときは、残した日時をそのまま使う */
    async function resolveSince({ serverMode, prefs, persist, }) {
        const session = openStorage("sessionStorage");
        let kept;
        try {
            kept = session.getItem(MindmapPreview.SINCE_KEY);
        }
        catch {
            kept = null;
        }
        if (kept !== null)
            return kept;
        const now = new Date().toISOString();
        let previous;
        if (serverMode) {
            previous = await MindmapPreview.postOpened();
        }
        else {
            // 配る書き出しは、前回開いた日時を端末の設定に持ち、今の日時に書き換える
            previous = prefs.opened ?? null;
            prefs.opened = now;
            persist();
        }
        // 前回開いた日時が無い・呼べなかったときは、タブを開いた日時にする
        const since = previous ?? now;
        try {
            session.setItem(MindmapPreview.SINCE_KEY, since);
        }
        catch {
            // 残せない環境では、読み込み直すたびに決め直す
        }
        return since;
    }
    /** 変更履歴のモーダルに、差分を出さない行と、まだまとめていない変更・前回開いてから・まとまりの行を新しい順に並べる */
    function historyPoints({ changes, since }) {
        /** その時点で足した・変えた項目の数 */
        const countOf = (sel) => {
            const point = MindmapPreview.resolveDiffPoint(changes, sel, since);
            return point === null ? 0 : point.added.size + point.changed.size;
        };
        const hasPending = changes.pending.added.length + changes.pending.changed.length > 0;
        return [
            { sel: "", name: "差分を出さない（今の内容）", sub: "印と差分を出さずに今の内容だけを読む" },
            ...(hasPending
                ? [{ sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: countOf("pending") }]
                : []),
            { sel: "since", name: "前回開いてから", sub: `${MindmapPreview.formatJst(since)} より後`, count: countOf("since") },
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
    /** 記録を読み、ハッシュが指す画面を描き、操作と履歴をつなぐ */
    function start() {
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
        const since = await resolveSince({ serverMode, prefs, persist });
        let point = MindmapPreview.resolveDiffPoint(data.changes, prefs.diffSel ?? null, since);
        // ===== 画面の土台 =====
        const top = MindmapPreview.h({ tag: "div", attrs: { id: "top" } });
        const main = MindmapPreview.h({ tag: "main", attrs: { class: "content", id: "main" } });
        document.body.prepend(top, main);
        let route = visibleRoute(MindmapPreview.parseHash({ hash: location.hash, index }));
        let fullViewer = null;
        /** 詳細パネルがもう画面に入れた見出し（同じ項目・同じ見出しでは、描き直しのたびに本文のスクロールを戻さない） */
        let shownHeading = null;
        const filterState = { byTab: {}, drawerOpen: false };
        // ===== 移動 =====
        /** 詳細パネルを別画面として積む幅か */
        const isNarrow = () => matchMedia(NARROW_QUERY).matches;
        /** 画面の既定の URL（絞り込みは書かない）に route を書き、画面を描く */
        const go = (next, push) => {
            const screenChanged = next.tab !== route.tab || next.view !== route.view || Object.keys(next.filters).length > 0;
            const idChanged = next.id !== route.id;
            route = next;
            MindmapPreview.navigate({ route: { ...route, filters: {} }, push });
            render({ screen: screenChanged || (route.tab === "decisions" && route.view === "map" && idChanged) });
        };
        /** 項目を開く。パネル・全画面の中の移動は履歴に積み、見てきた項目を行き来できるようにする */
        const openItem = (id, inPanel) => {
            flushDrafts();
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
        };
        /** 項目を、その種類の画面で開く（画面を移るので履歴に積む） */
        const openFromSearch = (id) => {
            const kind = index.byId.get(id)?.kind;
            if (kind === undefined)
                return;
            // 表示しない種類の項目は、概要の上の詳細パネルで開く
            const tab = resolved.kinds.has(kind) ? kind : "overview";
            go({ tab, view: MindmapPreview.defaultView(tab), id, full: false, filters: {}, heading: null }, tab !== route.tab);
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
                    // 差分の表示の間、新規・変更の項目を持つ種類のタブに点を重ねる
                    marked: key !== "overview" && marks !== undefined && data[key].some((item) => marks[item.id] !== undefined),
                })),
                current: route.tab,
                theme,
                connection,
                readAt: serverMode ? data.built_at : null,
                comments: serverMode,
                commentCount: comment.review.items.length,
                commentsOpen: comment.listOpen,
                onComments: () => (comment.listOpen ? closeList() : openList()),
                settingsOpen: display.open,
                onSettings: () => (display.open ? closeSettings() : openSettings()),
                // 概要以外の画面に絞り込みのボタンを置き、値を選んでいる条件の数をバッジに出す
                filter: route.tab !== "overview",
                filterCount: MindmapPreview.activeConditionCount(filterState.byTab[route.tab] ?? {}),
                filterOpen: filterState.drawerOpen,
                onFilter: toggleDrawer,
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
            // 123: モックは埋め込みの記録で開くため、コメントの印の見本の件数を `window.MOCK123.comments` から渡す
            const comments = serverMode ? commentsNow : window.MOCK123?.comments;
            const filters = filterState.byTab[route.tab] ?? {};
            const { drawerOpen } = filterState;
            switch (route.tab) {
                case "overview":
                    return MindmapPreview.overviewScreen({
                        index,
                        on: { open: on.open, navigate: (next) => go({ ...next, id: route.id }, true) },
                        marks,
                        visibleKinds: resolved.kinds,
                    });
                case "decisions":
                    return MindmapPreview.decisionsScreen({ index, route, on: { ...on, clear: closeDetail }, filters, drawerOpen, marks, comments });
                case "tasks":
                    return MindmapPreview.tasksScreen({ index, route, on, filters, drawerOpen, marks, comments });
                case "docs":
                    return MindmapPreview.docsScreen({ index, route, on, filters, drawerOpen, marks, comments });
                case "graph":
                    return MindmapPreview.graphScreen({
                        index,
                        // 123: 見た目のドロップダウンで選んだ値を個人の上書きに残す（ネットワークは描き直さず、次のコマから当てる）
                        on: {
                            open: on.open,
                            filter: changeFilters,
                            closeDrawer,
                            look: (value) => {
                                prefs.look = value;
                                changePrefs({ redrawMain: false });
                            },
                        },
                        filters,
                        drawerOpen,
                        selected: route.id,
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
        /** 今の画面の絞り込みを用意する。ハッシュの `f.{列}` があればそれだけを（開き直したときも）、無く初めて開く画面なら既定を入れ、ハッシュの分は一度だけ使う。概要には絞り込みのドロワーを置かないので閉じる（タブを押したときも、戻る・進むで移ったときも通る） */
        const prepareFilters = () => {
            if (route.tab === "overview")
                filterState.drawerOpen = false;
            if (Object.keys(route.filters).length > 0 || filterState.byTab[route.tab] === undefined) {
                filterState.byTab[route.tab] = MindmapPreview.initialFilters(route.tab, route.filters);
            }
            route = { ...route, filters: {} };
        };
        /** 詳細パネルと全画面 */
        const renderDetail = () => {
            const existing = document.querySelector("aside.panel");
            const fullDialog = document.querySelector("dialog.full");
            fullViewer = null;
            closePill();
            document.body.classList.toggle("panel-open", route.id !== null && !route.full);
            MindmapPreview.markSelected(route.id);
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
                on: {
                    open: (id) => openItem(id, true),
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
                    // 本文の見出しへ移った: ハッシュの `h` を、履歴に積まずに置き換える
                    heading: (heading) => {
                        route = { ...route, heading };
                        shownHeading = heading === null || route.id === null ? null : { id: route.id, heading };
                        MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
                    },
                },
                comment: serverMode
                    ? { form: formProps(route.id), reviews: comment.review.items.filter((item) => item.target === route.id) }
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
            if (route.tab === "graph")
                MindmapPreview.selectGraphItem(route.id);
            // 作り直した本文にも、開いているパネルの下の部品を止める
            scheduleInert();
        };
        // ===== 絞り込み =====
        /** 開いているパネルが覆った本文の部品を止める関数が返した、止めた分を外す関数 */
        let releaseInert = null;
        /** 前に止めた分を外してから、開いているパネル（絞り込みのドロワー・コメントの一覧・表示の設定のパネル）が覆った本文の部品を止める */
        const applyInert = () => {
            releaseInert?.();
            releaseInert = null;
            const panel = filterState.drawerOpen
                ? document.querySelector("dialog.drawer")
                : comment.listOpen
                    ? document.querySelector(".comments-panel")
                    : display.open
                        ? document.querySelector(".settings-drawer")
                        : null;
            if (panel !== null)
                releaseInert = MindmapPreview.inertBehind(panel);
        };
        /** パネルが開いた後（ドロワーは文書に入った後の次のマイクロタスクで開く）に、本文の部品を止める */
        const scheduleInert = () => queueMicrotask(applyInert);
        /** 画面の条件を変えて描き直す（ドロワーは開いたまま） */
        const changeFilters = (next) => {
            filterState.byTab[route.tab] = next;
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
            filterState.drawerOpen = true;
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
        };
        /** まとめて送った結果・本文を直している行・直せなかった理由・項目を指さない入力にフォーカスがあるか */
        let outcome = null;
        let editing = null;
        let editError = null;
        let editBody = null;
        let freeFocused = false;
        /** 入力欄を差し替えている間か（外した入力欄の blur を受けないため） */
        let formRedrawing = false;
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
        /** 幅 720px 以下か（項目を指さない入力を畳む幅） */
        const isCompact = () => matchMedia("(max-width: 720px)").matches;
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
        /** 向けた先の入力欄の状態。無ければ、同じ向けた先の書きかけの本文で作る */
        const formStateOf = (target, loc) => {
            const key = formKey(target, loc);
            let state = comment.forms.get(key);
            if (state === undefined) {
                const draft = comment.review.drafts.find((entry) => formKey(entry.target, entry.loc) === key);
                state = { target, loc, body: draft?.body ?? "", status: "idle", count: null, detail: null };
                comment.forms.set(key, state);
            }
            return state;
        };
        /** 書きかけをすぐ保つ（空なら消える）。届かないときは何も出さない */
        const saveDraftNow = (state) => {
            const key = formKey(state.target, state.loc);
            window.clearTimeout(draftTimers.get(key));
            draftTimers.delete(key);
            void api.saveDraft({
                ...(state.target === null ? {} : { target: state.target }),
                ...(state.loc === null ? {} : { loc: state.loc }),
                body: state.body,
            });
        };
        /** 入力が止まってから書きかけを保つ */
        const scheduleDraft = (state) => {
            const key = formKey(state.target, state.loc);
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
            const current = target === null
                ? document.querySelector(".comments-panel form.send")
                : document.querySelector("aside.panel form.send, dialog.full form.send");
            if (current === null || (target !== null && route.id !== target))
                return;
            const next = MindmapPreview.sendForm(formProps(target));
            // 外した入力欄の blur は、利用者が外へ出たのではないので受けない
            formRedrawing = true;
            current.replaceWith(next);
            formRedrawing = false;
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
                collapsed: target === null && isCompact() && !freeFocused && state.body === "",
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
                    focus: () => {
                        if (target !== null || freeFocused)
                            return;
                        freeFocused = true;
                        // 畳んでいた入力だけを広げる（広げない入力は作り直さず、入力中の欄を壊さない）
                        if (isCompact() && state.body === "")
                            redrawForm({ target: null, focus: true });
                    },
                    blur: () => {
                        if (formRedrawing || target !== null || !freeFocused)
                            return;
                        freeFocused = false;
                        // 本文が空のまま外へ出たら畳む
                        if (isCompact() && state.body === "")
                            redrawForm({ target: null, focus: false });
                    },
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
        /** 一覧を作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
        const renderComments = () => {
            const current = document.querySelector(".comments-panel");
            if (!comment.listOpen) {
                current?.remove();
                scheduleInert();
                return;
            }
            const active = document.activeElement;
            const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
            const typing = active instanceof HTMLTextAreaElement && active.closest(".comments-panel form.send") !== null ? active : null;
            const selection = typing === null ? null : { start: typing.selectionStart, end: typing.selectionEnd };
            const scroll = current?.querySelector(".comments-body")?.scrollTop ?? 0;
            const next = MindmapPreview.commentsPanel({
                items: comment.review.items,
                removed: comment.removed,
                checked: comment.checked,
                editing,
                editError,
                editBody,
                stale: comment.stale,
                result: outcome,
                selected: comment.opened,
                titleOf: (id) => index.byId.get(id)?.item.title ?? null,
                free: formProps(null),
                on: {
                    close: closeList,
                    check: (id, checked) => {
                        if (checked)
                            comment.checked.add(id);
                        else
                            comment.checked.delete(id);
                        renderComments();
                    },
                    checkAll: (checked) => {
                        comment.checked = checked ? new Set(comment.review.items.map((item) => item.id)) : new Set();
                        renderComments();
                    },
                    send: () => void sendChecked(),
                    open: openRow,
                    edit: (id) => {
                        editing = id;
                        editError = null;
                        editBody = null;
                        renderComments();
                    },
                    saveEdit: (id, body) => void saveEdit(id, body),
                    cancelEdit: () => {
                        editing = null;
                        editError = null;
                        editBody = null;
                        renderComments();
                    },
                    remove: (id) => void removeComment(id),
                    restore: (id) => void restoreComment(id),
                    unloc: (id) => void detachLocation(id),
                },
            });
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
                const restored = panel?.querySelector("form.send textarea");
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
        /** コメントの一覧を開く（絞り込みのドロワーは閉じる） */
        const openList = () => {
            // 絞り込みのドロワー・表示の設定のパネルとは 1 つだけを開く
            if (filterState.drawerOpen) {
                filterState.drawerOpen = false;
                redrawKeepingState();
            }
            display.open = false;
            renderSettings();
            comment.listOpen = true;
            renderTop();
            renderComments();
        };
        /** コメントの一覧を閉じる */
        const closeList = () => {
            flushDrafts();
            comment.listOpen = false;
            comment.opened = null;
            comment.removed = [];
            renderTop();
            renderComments();
            renderDetail();
        };
        /** 行の向けた項目を、一覧を開いたまま詳細パネルに開く（箇所があればその箇所を示す） */
        const openRow = (item) => {
            if (item.target === null)
                return;
            comment.opened = item.id;
            if (route.id === item.target) {
                renderDetail();
                renderComments();
                return;
            }
            openItem(item.target, false);
            renderComments();
        };
        /** 読み直して一覧まで描き直す */
        const reloadAndRefresh = async () => {
            await loadReview();
            refreshComments();
        };
        /** 行の本文を直す */
        const saveEdit = async (id, body) => {
            const result = await api.update(id, { body });
            if (!result.ok) {
                // 断られた・届かない: 入力を残して理由を出す
                editError = result.detail ?? "サーバーが止まっています。立ち上げ直してから直してください。";
                editBody = body;
                renderComments();
                return;
            }
            editing = null;
            editError = null;
            editBody = null;
            await reloadAndRefresh();
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
                body: item.body,
            });
            if (result.ok)
                comment.removed = comment.removed.filter((entry) => entry.id !== id);
            await reloadAndRefresh();
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
            const ids = comment.review.items.filter((item) => comment.checked.has(item.id)).map((item) => item.id);
            // 送るものが無い
            if (ids.length === 0)
                return;
            outcome = { kind: "sending" };
            renderComments();
            const result = await api.send(ids);
            if (result.ok && result.data !== null) {
                comment.removed = [];
                comment.stale = new Map();
                outcome = { kind: "sent", count: ids.length, at: result.data.sent };
            }
            else if (!result.ok && result.status === 409) {
                comment.stale = new Map(result.stale.map((entry) => [entry.id, entry.reason]));
                outcome = { kind: "stale", count: result.stale.length };
            }
            else {
                outcome = { kind: "failed", detail: result.ok ? null : result.detail };
            }
            await reloadAndRefresh();
        };
        // ===== 選んだ箇所のコメントの入口 =====
        /** 出している入口 */
        let pill = null;
        /** ポインターを押している間は入口を出さない（選び終えてから出す） */
        let pointerHeld = false;
        /** 入口を閉じる */
        const closePill = () => {
            pill?.remove();
            pill = null;
        };
        /** 選んだ範囲から箇所を求め、あれば入口を出し、無ければ閉じる */
        const updatePill = () => {
            closePill();
            const selection = getSelection();
            const host = document.querySelector("dialog.full[open], aside.panel");
            // 図の拡大を開いている間・選んだ範囲が無い・詳細パネルの外
            if (!serverMode || route.id === null || document.querySelector("dialog.viewer") !== null || fullViewer !== null)
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
            const id = route.id;
            pill = MindmapPreview.selectionComment({
                anchor: { first, last },
                viewport: { width: innerWidth, height: innerHeight },
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
        document.addEventListener("pointerdown", () => {
            pointerHeld = true;
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
            if (selection !== null) {
                const restored = document.querySelector(inList ? ".comments-panel form.send textarea" : "aside.panel form.send textarea, dialog.full form.send textarea");
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
            message: display.message,
            storageOk: display.storageOk,
            on: {
                look: (value) => {
                    prefs.look = value;
                    changePrefs({ redrawMain: true });
                },
                kinds: (kinds) => {
                    prefs.kinds = kinds;
                    changePrefs({ redrawMain: true });
                },
                reset: () => {
                    // 見た目・表示する種類・ライト / ダーク・表の列を全て外し、ワークスペースの既定の表示に戻す
                    Object.assign(prefs, clearOverrides(prefs));
                    MindmapPreview.clearTablePrefs();
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
                comment.removed = [];
                renderComments();
            }
            display.open = true;
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
            data = { ...data, settings: { ...data.settings, display: saved } };
            index = MindmapPreview.buildIndex(data);
            display.savedDisplay = saved;
            display.message = { kind: "ok", text: `ワークスペースの既定にしました（${MindmapPreview.formatJst(new Date().toISOString())}）。` };
            display.confirm = null;
            renderConfirm();
            resolved = resolveDisplay(prefs, data.settings.display);
            redrawKeepingState();
            renderSettings();
            document.querySelector('.settings-drawer [data-focus="same"]')?.focus();
        };
        // ===== 変更履歴と差分の表示 =====
        /** 選んだ時点を変えて残し、どの画面もその時点の差分の表示で描き直す（記録は読み直さず、履歴に積まない）。null は差分の表示をやめる */
        const selectPoint = (sel) => {
            prefs.diffSel = sel;
            persist();
            point = MindmapPreview.resolveDiffPoint(data.changes, sel, since);
            redrawKeepingState();
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
        /** 記録を読み直して描き直す。読み直しが読めないとき（422 など）は描き直さない */
        const reload = async () => {
            const result = await MindmapPreview.fetchRecords();
            if (!result.ok)
                return;
            await loadReview();
            const previousDisplay = data.settings.display;
            data = result.data;
            index = MindmapPreview.buildIndex(data);
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
        document.addEventListener("keydown", (event) => {
            // Ctrl+K（macOS は Cmd+K）で全体の検索を開く。入力欄に入力中でも開き、開いているときは検索の言葉を選び直す
            if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "k") {
                event.preventDefault();
                const opened = document.querySelector("dialog.search input");
                if (opened !== null)
                    opened.select();
                else
                    openSearch();
            }
            // Esc: 重ねる面が無いときは、詳細パネルを閉じる
            if (event.key === "Escape" &&
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
                closeList();
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
            const next = visibleRoute(parsed);
            // 表示しない種類のタブを指していた: ハッシュを概要に置き換える
            if (next !== parsed)
                MindmapPreview.navigate({ route: { ...next, filters: {} }, push: false });
            // 画面・表示形式・項目が同じで絞り込み（`f.{列}`）も無いときは、描き直さない。絞り込みだけを足したハッシュは、開き直しとして使う
            if (MindmapPreview.toHash(next) === MindmapPreview.toHash(route) && Object.keys(next.filters).length === 0)
                return;
            const screen = next.tab !== route.tab ||
                next.view !== route.view ||
                Object.keys(next.filters).length > 0 ||
                (next.tab === "decisions" && next.view === "map" && next.id !== route.id);
            route = next;
            render({ screen });
            // 絞り込みは画面に渡した後、ハッシュから消す（残すと、次のハッシュの変化で使い回される）
            if (Object.keys(next.filters).length > 0)
                MindmapPreview.navigate({ route: { ...route, filters: {} }, push: false });
        };
        addEventListener("popstate", onLocationChange);
        addEventListener("hashchange", onLocationChange);
        // ===== 最初の描き =====
        // サーバーの配信では、レビュー中のコメントと書きかけを読んでおく（コメントのボタンの件数と入力に使う）
        if (serverMode)
            await loadReview(true);
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
            document.addEventListener("DOMContentLoaded", start);
        else
            start();
    }
})(MindmapPreview || (MindmapPreview = {}));
