// 一覧の行の絞り込み・並べ替え・ドロワーの条件の組み立て（今の画面の `components/table.ts` と同じ振る舞い）
import { TEXT_FILTER_PREFIX, withoutKey, type Filters } from "@/shared/core/filters";

/** 列から値を取る定義 */
export type ListColumn<R> = {
  key: string;
  label: string;
  get: (row: R) => unknown;
  /** 値の並びの順（無ければ日本語の順） */
  order?: readonly string[];
};

/** ドロワーの条件 */
export type ListGroup = { key: string; label: string; values: { value: string; count: number }[]; mark?: "status" | "kind" };

const LEADING_CONDITION_KEYS = ["kind", "type", "status", "tags"];

const valuesOf = <R,>(column: ListColumn<R>, row: R): string[] => {
  const value = column.get(row);
  if (value === null || value === undefined) return [];
  return Array.isArray(value) ? value.map(String) : [String(value as string | number)];
};

const compareValues = <R,>(column: ListColumn<R>, a: string, b: string): number => {
  const { order } = column;
  if (order === undefined) return a.localeCompare(b, "ja");
  const rank = (value: string): number => {
    const index = order.indexOf(value);
    return index < 0 ? order.length : index;
  };
  return rank(a) - rank(b);
};

/** 条件ごとに合う行を返す（条件の中はどれかに当たればよく、条件の間は全てに当たる） */
export const filterRows = <R,>({ rows, columns, filters }: { rows: readonly R[]; columns: readonly ListColumn<R>[]; filters: Filters }): R[] => {
  const active = Object.entries(filters).filter(([, values]) => values.length > 0);
  return rows.filter((row) =>
    active.every(([key, wanted]) => {
      const isText = key.startsWith(TEXT_FILTER_PREFIX);
      const columnKey = isText ? key.slice(TEXT_FILTER_PREFIX.length) : key;
      const column = columns.find((candidate) => candidate.key === columnKey);
      if (column === undefined) return true;
      const cells = valuesOf(column, row);
      if (isText) {
        const lowered = cells.map((cell) => cell.toLowerCase());
        return wanted.every((word) => lowered.some((cell) => cell.includes(word.toLowerCase())));
      }
      return wanted.some((value) => cells.includes(value));
    }),
  );
};

/** `sort`（降順は頭に `-`）で行を並べ替える。同じ値は元の順 */
export const sortRows = <R,>({ rows, columns, sort }: { rows: readonly R[]; columns: readonly ListColumn<R>[]; sort: string | undefined }): R[] => {
  if (sort === undefined) return [...rows];
  const descending = sort.startsWith("-");
  const key = descending ? sort.slice(1) : sort;
  const column = columns.find((candidate) => candidate.key === key);
  if (column === undefined) return [...rows];
  const direction = descending ? -1 : 1;
  const compare = (a: R, b: R): number => {
    const x = column.get(a);
    const y = column.get(b);
    if (typeof x === "number" && typeof y === "number") return x - y;
    return compareValues(column, valuesOf(column, a).join(" "), valuesOf(column, b).join(" "));
  };
  return rows
    .map((row, position) => ({ row, position }))
    .sort((a, b) => direction * compare(a.row, b.row) || a.position - b.position)
    .map(({ row }) => row);
};

/** 今の並べ替えから次の並べ替えを返す（昇順 → 降順 → 解除） */
export const nextSort = (sort: string | undefined, key: string): string | undefined => {
  if (sort === key) return `-${key}`;
  return sort === `-${key}` ? undefined : key;
};

/** ドロワーの条件と、値ごとの件数を組む（件数はその条件以外の条件で絞った行で数える） */
export const drawerGroups = <R,>({ rows, columns, conditions, filters }: { rows: readonly R[]; columns: readonly ListColumn<R>[]; conditions: readonly ListColumn<R>[]; filters: Filters }): ListGroup[] => {
  const rank = (key: string): number => {
    const position = LEADING_CONDITION_KEYS.indexOf(key);
    return position < 0 ? LEADING_CONDITION_KEYS.length : position;
  };
  return [...conditions]
    .sort((a, b) => rank(a.key) - rank(b.key))
    .flatMap((column) => {
      const counts = new Map<string, number>();
      for (const row of rows) for (const value of valuesOf(column, row)) counts.set(value, 0);
      for (const row of filterRows({ rows, columns, filters: withoutKey(filters, column.key) })) {
        for (const value of valuesOf(column, row)) counts.set(value, (counts.get(value) ?? 0) + 1);
      }
      if (counts.size === 0) return [];
      const values = [...counts].map(([value, count]) => ({ value, count })).sort((a, b) => compareValues(column, a.value, b.value));
      const mark = column.key === "status" ? ({ mark: "status" } as const) : column.key === "type" ? ({ mark: "kind" } as const) : {};
      return [{ key: column.key, label: column.label, values, ...mark }];
    });
};
