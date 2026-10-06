// 調査・用語集・メモ・会話ログ。種類ごとの列を持つ表だけを出す。

namespace MindmapPreview {
  /** 表だけを持つ画面の種類 */
  type RecordKind = "research" | "terms" | "notes" | "logs";

  /** 調査・用語集・メモ・会話ログの画面を返す。種類は `route.tab` で決まる */
  export function recordsScreen({
    index,
    route,
    on,
    filters,
    drawerOpen,
    marks,
    comments,
  }: {
    index: RecordIndex;
    route: Route;
    on: {
      open: (id: string) => void;
      /** 条件を変える（新しい `filters`。ドロワーと表のチップから） */
      filter: (filters: Filters) => void;
      /** 絞り込みのドロワーを閉じる */
      closeDrawer: () => void;
    };
    /** 絞り込みの条件（入口の `FilterState` のこの種類の分） */
    filters: Filters;
    /** 絞り込みのドロワーを開いているか */
    drawerOpen: boolean;
    /** 項目の ID → 差分の印。差分の表示の間だけ渡す */
    marks?: DiffMarks;
    /** 項目の ID → レビュー中のコメントの件数（入口の `commentCounts`）。サーバーにつながって開いたときだけ渡し、印を置く場所をカードと表に置く */
    comments?: Record<string, number>;
  }): HTMLElement {
    const kind = route.tab as RecordKind;
    const common = commonColumns(index.data.settings);
    const related = (label: string): Column => ({
      key: "related",
      label,
      priority: 3,
      get: (row) => rowTexts(row, "related"),
      cell: (row) => idLinksCell(rowTexts(row, "related"), on.open),
    });
    const columnsOf: Record<RecordKind, Column[]> = {
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
          get: (row) => rowTexts(row, "aliases"),
          cell: (row) => tagList(rowTexts(row, "aliases")),
        },
        {
          key: "avoid",
          label: "使わない表記",
          priority: 3,
          get: (row) => rowTexts(row, "avoid"),
          cell: (row) => tagList(rowTexts(row, "avoid")),
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
    const shown = filterRows({ rows: index.data[kind], columns, filters });
    return h({
      tag: "div",
      attrs: { class: "screen records" },
      children: [
        managedTable({
          kind,
          columns,
          rows: shown,
          filters,
          onFilter: on.filter,
          open: on.open,
          marks,
          ...(comments === undefined ? {} : { comments }),
        }),
        screenDrawer({
          drawerOpen,
          rows: index.data[kind],
          columns: columns.filter((column) => column.filterable === true),
          textColumns: textColumns(columns),
          filters,
          shown: shown.length,
          onFilter: on.filter,
          onClose: on.closeDrawer,
        }),
      ],
    });
  }
}
