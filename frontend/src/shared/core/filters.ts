// 画面ごとの絞り込みの条件（今の画面の `Filters` と同じ形）の計算
import { toText } from "@/shared/core/format";
import type { PreviewTab } from "@/shared/core/preview-search";

/** 列の `key` → 選んだ値の配列。`~{列}` は文字の条件 */
export type Filters = Record<string, string[]>;

/** 文字の条件のキーの頭 */
export const TEXT_FILTER_PREFIX = "~";

/** 条件から 1 つのキーを除く */
export const withoutKey = (filters: Filters, key: string): Filters => Object.fromEntries(Object.entries(filters).filter(([name]) => name !== key));

/** 検討事項の既定の状態の条件 */
const DECISION_DEFAULT_STATUSES = ["要見直し", "未決定", "未整理", "保留"];

const toStrings = (value: unknown): string[] => {
  if (Array.isArray(value)) return value.map(String);
  return value === undefined || value === null ? [] : [toText(value)];
};

/** 条件に行が合うかを返す（条件の中はどれか、条件の間は全て。`~{列}` は文字の条件） */
export const matchesFilters = (row: Record<string, unknown>, filters: Filters): boolean =>
  Object.entries(filters).every(([key, values]) => {
    if (values.length === 0) return true;
    if (key.startsWith(TEXT_FILTER_PREFIX)) {
      const texts = toStrings(row[key.slice(TEXT_FILTER_PREFIX.length)]).map((text) => text.toLowerCase());
      return values.every((value) => texts.some((text) => text.includes(value.toLowerCase())));
    }
    const cells = toStrings(row[key]);
    return values.some((value) => cells.includes(value));
  });

/** 画面の既定の条件を返す */
export const defaultFilters = (tab: PreviewTab): Filters => (tab === "decisions" ? { status: DECISION_DEFAULT_STATUSES } : {});

/** search の `f` の値を条件にする */
export const filtersFromSearch = (f: Record<string, string>): Filters =>
  Object.fromEntries(Object.entries(f).map(([key, value]) => [key, key.startsWith(TEXT_FILTER_PREFIX) ? [value] : value.split("|")]));

/** 条件を search の `f` の値にする */
export const filtersToSearch = (filters: Filters): Record<string, string> =>
  Object.fromEntries(Object.entries(filters).filter(([, values]) => values.length > 0).map(([key, values]) => [key, values.join("|")]));
