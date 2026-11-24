// カード・ボードの並べ替え。並べる項目を選ぶボタンの組で、同じ項目をもう一度押すと向きが逆になる
import { Icon } from "@/shared/components/icon";
import { sortRows, type ListColumn } from "@/shared/core/list-rows";
import type { Item } from "@/shared/core/records";
import { Button } from "@/shared/components/ui/button";

export type CardSortKey = "default" | "created" | "updated";

export type CardSortDir = "asc" | "desc";

export type CardSortValue = { key: CardSortKey; dir: CardSortDir };

/** 画面を開いた直後の並べ替え。資料は更新日時の新しい順、ほかの種類は連番 */
export const INITIAL_CARD_SORT = {
  docs: { key: "updated", dir: "desc" },
  other: { key: "default", dir: "asc" },
} as const satisfies Record<string, CardSortValue>;

const OPTIONS = [
  { key: "default", label: "連番" },
  { key: "created", label: "作成日時" },
  { key: "updated", label: "更新日時" },
] as const satisfies readonly { key: CardSortKey; label: string }[];

/** 初めて選んだ日時の項目は新しい順、選んでいる項目をもう一度選ぶと向きを逆にする */
export const nextCardSort = (current: CardSortValue, key: CardSortKey): CardSortValue => {
  if (key === "default") return { key, dir: "asc" };
  if (current.key !== key) return { key, dir: "desc" };
  return { key, dir: current.dir === "desc" ? "asc" : "desc" };
};

/** 並びを URL の `sort` にする。画面の既定と同じ並びは書かず、連番は `id`、降順は頭に `-` を付ける */
export const cardSortToParam = (value: CardSortValue, initial: CardSortValue): string | undefined => {
  if (value.key === initial.key && value.dir === initial.dir) return undefined;
  if (value.key === "default") return "id";
  return value.dir === "desc" ? `-${value.key}` : value.key;
};

/** URL の `sort` を並びにする。無ければ画面の既定、`id`・`-id`・知らない値は連番 */
export const cardSortFromParam = (sort: string | undefined, initial: CardSortValue): CardSortValue => {
  if (sort === undefined) return initial;
  const dir: CardSortDir = sort.startsWith("-") ? "desc" : "asc";
  const key = dir === "desc" ? sort.slice(1) : sort;
  return key === "created" || key === "updated" ? { key, dir } : { key: "default", dir: "asc" };
};

/** 並びを `sortRows` の `sort` にする（連番は `id`） */
export const cardSortToRowSort = (value: CardSortValue): string => {
  const key = value.key === "default" ? "id" : value.key;
  return value.dir === "desc" ? `-${key}` : key;
};

const ITEM_SORT_COLUMNS: ListColumn<Item>[] = [
  { key: "id", label: "連番", get: (item) => item.id },
  { key: "created", label: "作成日時", get: (item) => item.created },
  { key: "updated", label: "更新日時", get: (item) => item.updated },
];

/** カード・ボードの項目を `sortRows` の `sort`（`id`・`created`・`updated`、降順は頭に `-`）の順に並べる */
export const sortItems = (items: readonly Item[], sort: string): Item[] => sortRows({ rows: items, columns: ITEM_SORT_COLUMNS, sort });

export type CardSortProps = { value: CardSortValue; onChange: (value: CardSortValue) => void };

export const CardSort = ({ value, onChange }: CardSortProps) => (
  <div role="group" aria-label="並べ替え" className="flex flex-none items-center gap-1 text-small">
    <span className="text-xs text-muted-foreground">並べ替え</span>
    {OPTIONS.map((option) => {
      const selected = value.key === option.key;
      const dirLabel = value.dir === "desc" ? "新しい順" : "古い順";
      return (
        <Button key={option.key} variant={selected ? "secondary" : "ghost"} aria-pressed={selected} title={selected && option.key !== "default" ? `${option.label}（${dirLabel}）` : option.label} onClick={() => { onChange(nextCardSort(value, option.key)); }}>
          {option.label}
          {selected && option.key !== "default" ? <Icon name="arrow" className={value.dir === "desc" ? "rotate-90" : "-rotate-90"} /> : null}
        </Button>
      );
    })}
  </div>
);
