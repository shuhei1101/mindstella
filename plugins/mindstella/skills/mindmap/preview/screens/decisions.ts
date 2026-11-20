// 検討事項。ボード（既定）・表で見る。

namespace MindmapPreview {
  /** 検討事項の表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
  export function decisionColumns({ index, open }: { index: RecordIndex; open: (id: string) => void }): Column[] {
    const common = commonColumns();
    return [
      common.id,
      common.title(),
      common.status(DECISION_STATUSES),
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
        get: (row) => refsOf(row as unknown as Item, "depends_on"),
        cell: (row) => idLinksCell(refsOf(row as unknown as Item, "depends_on"), open),
      },
      common.tags,
    ];
  }

  /** 検討事項の画面を返す */
  export function decisionsScreen({ index, route, on, marks, comments, filters, drawerOpen, removed = [], edit = null }: ScreenProps): HTMLElement {
    const columns = decisionColumns({ index, open: on.open });
    // 絞り込みの条件に合う検討事項を、ボード・表に同じ結果で渡す
    const shown = filterRows({ rows: index.data.decisions, columns, filters }) as Item[];
    // 表以外の表示形式では、ツールバーの下に条件のチップの行を置く
    const chips =
      activeConditionCount(filters) > 0
        ? filterChips({
            filters,
            labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
            onFilter: on.filter,
          })
        : null;
    const makeDrawer = (): HTMLDialogElement | null =>
      screenDrawer({
        drawerOpen,
        rows: index.data.decisions,
        columns: columns.filter((column) => column.filterable === true),
        textColumns: textColumns(columns),
        filters,
        shown: shown.length,
        onFilter: on.filter,
        onClose: on.closeDrawer,
      });
    const toolbarElement = toolbar(
      [
        { key: "board", label: "ボード" },
        { key: "table", label: "表" },
      ],
      route,
      on.view,
      edit === null ? null : addItemButton({ kind: "decisions", onAdd: edit.onAdd }),
    );
    if (route.view === "board") {
      return h({
        tag: "div",
        attrs: { class: "screen decisions" },
        children: [
          toolbarElement,
          chips,
          removedBand({ items: removed }),
          board({
            columns: boardColumns({
              items: shown,
              statuses: [...DECISION_STATUSES],
              statusFilter: filters["status"] ?? [],
            }),
            card: (item) =>
              boardCard({
                index,
                item,
                meta: [],
                links: refsOf(item, "depends_on"),
                open: on.open,
                mark: marks?.[item.id],
                comments,
                edit,
              }),
            emptyText: "検討事項はありません。",
            added: addedCards({ edit, statuses: DECISION_STATUSES, open: on.open }),
          }),
          makeDrawer(),
        ],
      });
    }
    return h({
      tag: "div",
      attrs: { class: "screen decisions" },
      children: [
        toolbarElement,
        removedBand({ items: removed }),
        managedTable({
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
}
