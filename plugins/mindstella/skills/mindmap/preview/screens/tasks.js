"use strict";
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
