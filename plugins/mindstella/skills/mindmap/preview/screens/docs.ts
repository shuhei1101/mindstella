// 資料。カード（既定）・ボード・表で見る。納品物を先頭に印付きで並べ、資料の状態を出す。

namespace MindmapPreview {
  /** 納品物を先頭に、それぞれ連番の順に並べた資料を返す */
  export function orderDocs(docs: Item[]): Item[] {
    return [...docs].sort(
      (a, b) =>
        Number(b.deliverable === true) - Number(a.deliverable === true) || compareIds(a.id, b.id),
    );
  }

  /** 納品物の列の値 */
  const DELIVERABLE_VALUES = ["納品物", "納品物以外"];

  /** 資料の表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
  export function docColumns(index: RecordIndex): Column[] {
    const common = commonColumns(index.data.settings);
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
        cell: (row) =>
          row["deliverable"] === true ? deliverableBadge() : h({ tag: "span", attrs: { class: "muted" }, children: ["—"] }),
      },
      common.status(DOC_STATUSES),
      common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
      common.target,
      common.category,
      common.phase,
      common.tags,
    ];
  }

  /** 資料の画面を返す */
  export function docsScreen({ index, route, on, marks, comments, filters, drawerOpen, removed = [] }: ScreenProps): HTMLElement {
    const columns = docColumns(index);
    const toolbarElement = toolbar(
      [
        { key: "cards", label: "カード" },
        { key: "board", label: "ボード" },
        { key: "table", label: "表" },
      ],
      route,
      on.view,
    );
    // 絞り込みの条件に合う資料を、カード・ボード・表に同じ結果で渡す
    const shown = filterRows({ rows: index.data.docs, columns, filters }) as Item[];
    const drawer = screenDrawer({
      drawerOpen,
      rows: index.data.docs,
      columns: columns.filter((column) => column.filterable === true),
      textColumns: textColumns(columns),
      filters,
      shown: shown.length,
      onFilter: on.filter,
      onClose: on.closeDrawer,
    });
    if (route.view === "table") {
      return h({
        tag: "div",
        attrs: { class: "screen docs" },
        children: [
          toolbarElement,
          removedBand({ items: removed }),
          managedTable({
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
    const chips =
      activeConditionCount(filters) > 0
        ? filterChips({
            filters,
            labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
            onFilter: on.filter,
          })
        : null;
    const content =
      route.view === "board"
        ? // 列ごとに納品物を先頭に並べ直す
          board({
            columns: boardColumns({
              items: shown,
              statuses: [...DOC_STATUSES],
              statusFilter: filters["status"] ?? [],
            }).map((column) => ({ ...column, items: orderDocs(column.items) })),
            card: (item) => docCard({ index, doc: item, open: on.open, inBoard: true, mark: marks?.[item.id], comments }),
            emptyText: "資料はありません。",
          })
        : h({
            tag: "div",
            attrs: { class: "doc-grid" },
            children:
              shown.length > 0
                ? orderDocs(shown).map((row) =>
                    docCard({ index, doc: row, open: on.open, inBoard: false, mark: marks?.[row.id], comments }),
                  )
                : [h({ tag: "p", attrs: { class: "no-match" }, children: ["該当する資料はありません。別の条件を試してください。"] })],
          });
    return h({
      tag: "div",
      attrs: { class: "screen docs" },
      children: [toolbarElement, chips, removedBand({ items: removed }), content, drawer],
    });
  }

  /** 資料のカード（納品物の印・種類・状態・カテゴリー・フェーズ・タグ）。ボードの中では列で状態が分かるので状態の印を出さず、開いている資料に選択の印を付ける */
  function docCard({
    index,
    doc,
    open,
    inBoard,
    mark,
    comments,
  }: {
    index: RecordIndex;
    doc: Item;
    open: (id: string) => void;
    inBoard: boolean;
    /** 差分の印（差分の表示の間で、その資料に印があるとき） */
    mark?: DiffKind | undefined;
    /** 項目の ID → レビュー中のコメントの件数。渡したとき、メタ情報の並びの右端に印を置く場所を置く */
    comments?: Record<string, number> | undefined;
  }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: `card doc-card${doc.deliverable === true ? " deliv-card" : ""}${inBoard && doc.id === currentSelection() ? " selected" : ""}${doc.withdrawn === true ? " is-withdrawn" : ""}`,
        type: "button",
        "data-id": doc.id,
        onclick: () => open(doc.id),
      },
      children: [
        doc.deliverable === true ? deliverableBadge() : null,
        h({
          tag: "span",
          attrs: { class: "doc-kind" },
          children: [icon(doc.kind === "図" ? "graph" : "cards"), doc.kind ?? ""],
        }),
        h({ tag: "span", attrs: { class: "c-ttl" }, children: [doc.title] }),
        // 取り下げた資料は、差分の表示によらず差分の印より前に札を置く
        doc.withdrawn === true ? withdrawnBadge() : null,
        h({
          tag: "span",
          attrs: { class: "c-meta" },
          children: [
            mark === undefined ? null : diffMark({ kind: mark }),
            h({ tag: "span", attrs: { class: "mono" }, children: [doc.id] }),
            inBoard ? null : statusBadge(doc.status),
            h({ tag: "span", children: [[doc.category, doc.phase].filter(Boolean).join(" · ")] }),
            comments === undefined ? null : commentPlace({ id: doc.id, count: comments[doc.id] }),
          ],
        }),
        (doc.tags ?? []).length > 0 ? h({ tag: "span", attrs: { class: "c-tags" }, children: [tagList(doc.tags)] }) : null,
      ],
    });
  }
}
