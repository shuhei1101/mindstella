"use strict";
// 検討事項。ボード（既定）・表で見る。
var MindmapPreview;
(function (MindmapPreview) {
    /** 検討事項の表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
    function decisionColumns({ index, open }) {
        const common = MindmapPreview.commonColumns();
        return [
            common.id,
            common.title(),
            common.status(MindmapPreview.DECISION_STATUSES),
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
                get: (row) => MindmapPreview.refsOf(row, "depends_on"),
                cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.refsOf(row, "depends_on"), open),
            },
            common.tags,
        ];
    }
    MindmapPreview.decisionColumns = decisionColumns;
    /** 検討事項の画面を返す */
    function decisionsScreen({ index, route, on, marks, comments, filters, drawerOpen, removed = [], edit = null }) {
        const columns = decisionColumns({ index, open: on.open });
        // 絞り込みの条件に合う検討事項を、ボード・表に同じ結果で渡す
        const shown = MindmapPreview.filterRows({ rows: index.data.decisions, columns, filters });
        // 表以外の表示形式では、ツールバーの下に条件のチップの行を置く
        const chips = MindmapPreview.activeConditionCount(filters) > 0
            ? MindmapPreview.filterChips({
                filters,
                labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
                onFilter: on.filter,
            })
            : null;
        const makeDrawer = () => MindmapPreview.screenDrawer({
            drawerOpen,
            rows: index.data.decisions,
            columns: columns.filter((column) => column.filterable === true),
            textColumns: MindmapPreview.textColumns(columns),
            filters,
            shown: shown.length,
            onFilter: on.filter,
            onClose: on.closeDrawer,
        });
        const toolbarElement = MindmapPreview.toolbar([
            { key: "board", label: "ボード" },
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
                            meta: [],
                            links: MindmapPreview.refsOf(item, "depends_on"),
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
