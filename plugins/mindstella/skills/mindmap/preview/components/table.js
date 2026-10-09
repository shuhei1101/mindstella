"use strict";
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
