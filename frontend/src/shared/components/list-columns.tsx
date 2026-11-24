// 一覧の表の共通の列
import { StatusMark } from "@/shared/components/icon";
import type { Row, TableColumn } from "@/shared/components/table";
import { TagList } from "@/shared/components/tag-list";
import { formatItemDateTime } from "@/shared/core/format";
import { tagNames, type Tag } from "@/shared/core/records";

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

/** 日時の列。セルは表示の書式の `time`、並べ替えと絞り込みは元の ISO 8601 の値で行う */
const dateColumn = (key: "created" | "updated", label: string) =>
  ({
    key,
    label,
    get: (row: Row) => textOf(row, key),
    cell: (row: Row) => {
      const value = textOf(row, key);
      return value === undefined || formatItemDateTime(value) === "" ? null : (
        <time dateTime={value} className="whitespace-nowrap">
          {formatItemDateTime(value)}
        </time>
      );
    },
  }) satisfies TableColumn;

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

export const commonColumns = () => ({
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
  tags: { key: "tags", label: "タグ", filterable: true, get: rowTags, cell: (row: Row) => <TagList values={rowTags(row)} /> } satisfies TableColumn,
  text: (key: string, label: string, options: Partial<TableColumn> = {}): TableColumn => ({ key, label, get: (row) => textOf(row, key), ...options }),
  created: dateColumn("created", "作成日時"),
  updated: dateColumn("updated", "更新日時"),
});
