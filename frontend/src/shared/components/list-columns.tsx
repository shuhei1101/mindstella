// 一覧の表の共通の列（今の画面の `commonColumns` と同じ並び）
import { StatusMark } from "@/shared/components/icon";
import type { Row, TableColumn } from "@/shared/components/table";
import { TagList } from "@/shared/components/tag-list";
import { tagNames, type Settings, type Tag } from "@/shared/core/records";

const textOf = (row: Row, key: string): string | undefined => {
  const value = row[key];
  return typeof value === "string" ? value : undefined;
};

/** 行の値を文字の配列で取る */
export const rowTexts = (row: Row, key: string): string[] => {
  const value = row[key];
  return Array.isArray(value) ? value.map(String) : [];
};

const rowTags = (row: Row): string[] => tagNames(row["tags"] as readonly (Tag | string)[] | undefined);

/** ID の並びを押せる題に並べる */
export const IdLinks = ({ ids, titleOf, onOpen }: { ids: readonly string[]; titleOf: (id: string) => string; onOpen: (id: string) => void }) => (
  <span className="flex flex-col gap-0.5">
    {ids.map((id) => (
      <button key={id} type="button" data-id={id} title={titleOf(id)} className="cursor-pointer text-left font-mono text-xs underline-offset-2 hover:underline" onClick={() => { onOpen(id); }}>
        {id}
      </button>
    ))}
  </span>
);

export const commonColumns = (settings: Settings) => ({
  id: { key: "id", label: "ID", get: (row: Row) => row.id, cell: (row: Row) => <span className="font-mono text-xs">{row.id}</span> } satisfies TableColumn,
  title: (label = "タイトル"): TableColumn => ({ key: "title", label, fixed: true, get: (row) => textOf(row, "title") }),
  status: (order: readonly string[]): TableColumn => ({
    key: "status",
    label: "状態",
    filterable: true,
    order,
    get: (row) => textOf(row, "status"),
    cell: (row) => {
      const status = textOf(row, "status");
      return status === undefined ? null : (
        <span className="inline-flex items-center gap-1 whitespace-nowrap">
          <StatusMark status={status} />
          {status}
        </span>
      );
    },
  }),
  target: { key: "target", label: settings.target_label, filterable: true, get: (row: Row) => textOf(row, "target") } satisfies TableColumn,
  category: { key: "category", label: "カテゴリー", filterable: true, get: (row: Row) => textOf(row, "category") } satisfies TableColumn,
  phase: { key: "phase", label: "フェーズ", filterable: true, order: settings.phases, get: (row: Row) => textOf(row, "phase") } satisfies TableColumn,
  tags: { key: "tags", label: "タグ", filterable: true, get: rowTags, cell: (row: Row) => <TagList values={rowTags(row)} /> } satisfies TableColumn,
  text: (key: string, label: string, options: Partial<TableColumn> = {}): TableColumn => ({ key, label, get: (row) => textOf(row, key), ...options }),
});
