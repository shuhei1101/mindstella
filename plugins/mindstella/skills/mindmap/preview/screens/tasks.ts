// タスク。ボード（既定）と表で見る。

namespace MindmapPreview {
  /** 画面が受ける、表示形式の切り替え・項目を開く・絞り込みの操作 */
  export type ScreenProps = {
    index: RecordIndex;
    /** 表示形式と絞り込み */
    route: Route;
    on: {
      /** 項目を詳細パネルで開く */
      open: (id: string) => void;
      /** 表示形式を切り替える */
      view: (view: View) => void;
      /** 条件を変える（新しい `filters`。ドロワーと表のチップから） */
      filter: (filters: Filters) => void;
      /** 絞り込みのドロワーを閉じる */
      closeDrawer: () => void;
    };
    /** 絞り込みの条件（入口の `FilterState` のこの画面の分） */
    filters: Filters;
    /** 絞り込みのドロワーを開いているか */
    drawerOpen: boolean;
    /** 項目の ID → 差分の印。差分の表示の間だけ渡す */
    marks?: DiffMarks;
  };

  /** 状態の並びの順に、状態ごとの項目を返す（項目が 0 件の列も返す。列の中は連番の順）。`excluded` は状態の条件で外した列 */
  export function boardColumns({
    items,
    statuses,
    statusFilter = [],
  }: {
    items: Item[];
    statuses: string[];
    /** 状態の条件で選んだ値（空なら状態で絞っていない） */
    statusFilter?: string[];
  }): { status: string; items: Item[]; excluded: boolean }[] {
    return statuses.map((status) => ({
      status,
      items: items
        .filter((item) => item.status === status)
        .sort((a, b) => compareIds(a.id, b.id)),
      excluded: statusFilter.length > 0 && !statusFilter.includes(status),
    }));
  }

  /** ボードのカード（押すと詳細を開く）。`links` が項目を指す ID の並びなら、その題を添える */
  export function boardCard({
    index,
    item,
    meta,
    links,
    open,
    mark,
  }: {
    index: RecordIndex;
    item: Item;
    meta: (string | undefined)[];
    links: string[];
    open: (id: string) => void;
    /** 差分の印（差分の表示の間で、その項目に印があるとき） */
    mark?: DiffKind | undefined;
  }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: item.id === currentSelection() ? "card selected" : "card",
        type: "button",
        "data-id": item.id,
        onclick: () => open(item.id),
      },
      children: [
        h({ tag: "div", attrs: { class: "c-ttl" }, children: [item.title] }),
        h({
          tag: "div",
          attrs: { class: "c-meta" },
          children: [
            mark === undefined ? null : diffMark({ kind: mark }),
            h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
            ...meta.filter(Boolean).map((value) => h({ tag: "span", children: [value] })),
          ],
        }),
        links.length > 0
          ? h({
            tag: "div",
            attrs: { class: "c-for" },
            children: [
              ...links.map((id) =>
                h({
                  tag: "div",
                  children: [
                    h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
                    ` ${titleOf(index, id)}`,
                  ],
                }),
              ),
            ],
          })
          : null,
      ],
    });
  }

  /** 状態ごとの列にカードを並べたボード。横に送れ、背景のドラッグで動かせる */
  export function board({
    columns,
    card,
    emptyText,
  }: {
    columns: { status: string; items: Item[]; excluded?: boolean }[];
    card: (item: Item) => HTMLElement;
    /** 0 件の列に出す文 */
    emptyText: string;
  }): HTMLElement {
    const element = h({
      tag: "div",
      attrs: { class: "board", style: `--cols:${columns.length}` },
      children: [
        ...columns.map(({ status, items, excluded = false }) =>
          h({
            tag: "section",
            attrs: { class: "board-col", "aria-label": status },
            children: [
              h({
                tag: "h3",
                children: [
                  statusMark(status),
                  status,
                  h({ tag: "span", attrs: { class: "n" }, children: [items.length] }),
                ],
              }),
              // 状態の条件で外した列は、列を残して外した旨を出す
              ...(excluded
                ? [emptyNote("状態の条件で外しています。")]
                : items.length > 0
                  ? items.map(card)
                  : [emptyNote(emptyText)]),
            ],
          }),
        ),
      ],
    });
    enableDragScroll(element);
    return element;
  }

  /** 表示形式の切り替えを置いた道具の行 */
  export function toolbar(views: { key: View; label: string }[], route: Route, onView: (view: View) => void): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "toolbar" },
      children: [viewSwitch({ views, current: route.view, onChange: onView })],
    });
  }

  /** タスクの画面を返す */
  export function tasksScreen({ index, route, on, marks, filters, drawerOpen }: ScreenProps): HTMLElement {
    const common = commonColumns(index.data.settings);
    const columns: Column[] = [
      common.id,
      common.title(),
      common.status(TASK_STATUSES),
      common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
      {
        key: "for",
        label: "進める検討事項",
        priority: 3,
        get: (row) => rowTexts(row, "for"),
        cell: (row) => idLinksCell(rowTexts(row, "for"), on.open),
      },
      common.target,
      common.category,
      common.phase,
      common.tags,
    ];
    // 絞り込みの条件に合うタスクを、ボードと表に同じ結果で渡す
    const shown = filterRows({ rows: index.data.tasks, columns, filters }) as Item[];
    // ボードでは、ツールバーの下に条件のチップの行を置く（表は表の上に持つ）
    const chips =
      route.view === "board" && activeConditionCount(filters) > 0
        ? filterChips({
            filters,
            labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
            onFilter: on.filter,
          })
        : null;
    const content =
      route.view === "board"
        ? board({
            columns: boardColumns({
              items: shown,
              statuses: [...TASK_STATUSES],
              statusFilter: filters["status"] ?? [],
            }),
            card: (item) =>
              boardCard({
                index,
                item,
                meta: [item.kind, item.category],
                links: item.for ?? [],
                open: on.open,
                mark: marks?.[item.id],
              }),
            emptyText: "タスクはありません。",
          })
        : managedTable({
            kind: "tasks",
            columns,
            rows: shown,
            filters,
            onFilter: on.filter,
            open: on.open,
            marks,
          });
    return h({
      tag: "div",
      attrs: { class: "screen tasks" },
      children: [
        toolbar(
          [
            { key: "board", label: "ボード" },
            { key: "table", label: "表" },
          ],
          route,
          on.view,
        ),
        chips,
        content,
        screenDrawer({
          drawerOpen,
          rows: index.data.tasks,
          columns: columns.filter((column) => column.filterable === true),
          filters,
          shown: shown.length,
          onFilter: on.filter,
          onClose: on.closeDrawer,
        }),
      ],
    });
  }
}
