// SPA の search params（インターフェース定義『SPAを開く』の request）の Zod スキーマと、記録に合わない値を外す処理、今の画面へ写すハッシュ
import { z } from "zod";

import { bodyFormatOf, type Kind, type RecordIndex } from "@/shared/core/records";

/** 画面が持つ表示形式 */
const VIEWS_OF_TAB: Record<string, readonly string[]> = {
  decisions: ["board", "map", "table"],
  tasks: ["board", "table"],
  docs: ["cards", "board", "table"],
};

const F_PREFIX = "f.";

export const PreviewSearchSchema = z.object({
  tab: z.enum(["overview", "decisions", "tasks", "research", "docs", "terms", "notes", "logs", "settings"]).optional().catch(undefined),
  view: z.enum(["map", "board", "cards", "table"]).optional().catch(undefined),
  id: z.string().regex(/^[DTRAGNL]-\d+$/).optional().catch(undefined),
  full: z.enum(["1"]).optional().catch(undefined),
  h: z.string().optional().catch(undefined),
  diff: z.string().optional().catch(undefined),
  sort: z.string().optional().catch(undefined),
  panel: z.enum(["pending"]).optional().catch(undefined),
  f: z.record(z.string(), z.string()).catch({}),
});

export type PreviewSearch = z.infer<typeof PreviewSearchSchema>;

/** 開く画面 */
export type PreviewTab = NonNullable<PreviewSearch["tab"]>;

/** `normalizeSearch` の判定に要る値 */
export type SearchContext = {
  index: RecordIndex;
  pendingCount: number;
  visibleKinds: readonly Kind[];
  diffActive: boolean;
  sortColumns: readonly string[];
};

/** `f.` で始まるキーを `f` に集めて検証する */
export const parsePreviewSearch = (search: Record<string, unknown>): PreviewSearch => {
  const f: Record<string, string> = {};
  const rest: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(search)) {
    if (key.startsWith(F_PREFIX)) f[key.slice(F_PREFIX.length)] = String(value);
    else rest[key] = value;
  }
  return PreviewSearchSchema.parse({ ...rest, f: { ...f, ...(rest["f"] as Record<string, string> | undefined) } });
};

/** search を URL の引数の形にする（`f` を `f.{列}` に展開する） */
export const flattenSearch = ({ f, ...rest }: PreviewSearch): Record<string, string | undefined> => ({
  ...rest,
  ...Object.fromEntries(Object.entries(f).map(([key, value]) => [`${F_PREFIX}${key}`, value])),
});

/** URL の search の文字列を読む。値は全て文字列のまま扱う（今の画面のハッシュと同じ値にするため、JSON として読まない） */
export const parseSearchString = (text: string): Record<string, unknown> => Object.fromEntries(new URLSearchParams(text));

/** search を URL の search の文字列にする。値の無い引数は書かない */
export const stringifySearchString = (search: Record<string, unknown>): string => {
  const flat = "f" in search ? flattenSearch(search as PreviewSearch) : (search as Record<string, string | undefined>);
  const text = new URLSearchParams(Object.entries(flat).filter((entry): entry is [string, string] => entry[1] !== undefined)).toString();
  return text === "" ? "" : `?${text}`;
};

/** その時点の差分を出せるか */
const diffExists = (diff: string, index: RecordIndex): boolean => {
  const { changes } = index.data;
  if (diff === "since") return true;
  if (diff === "pending") return changes.pending.added.length + changes.pending.changed.length + (changes.pending.removed ?? []).length > 0;
  return changes.sets.some((set) => set.id === diff);
};

/** 記録・画面に合わない値を外す */
// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
export const normalizeSearch = (search: PreviewSearch, context: SearchContext): PreviewSearch => {
  const { index, pendingCount, visibleKinds, diffActive, sortColumns } = context;
  const next: PreviewSearch = { ...search };
  const hidden = next.tab !== undefined && next.tab !== "overview" && next.tab !== "settings" && !visibleKinds.includes(next.tab);
  if (hidden || (next.tab === "settings" && diffActive)) delete next.tab;
  if (next.view !== undefined && !(VIEWS_OF_TAB[next.tab ?? ""] ?? ["table"]).includes(next.view)) delete next.view;
  const entry = next.id === undefined ? undefined : index.byId.get(next.id);
  if (entry === undefined) delete next.id;
  if (next.id === undefined) {
    delete next.full;
    delete next.h;
  } else if (next.h !== undefined && bodyFormatOf(entry?.item.body) === "html") {
    delete next.h;
  }
  if (next.diff !== undefined && !diffExists(next.diff, index)) delete next.diff;
  if (next.sort !== undefined && !sortColumns.includes(next.sort.replace(/^-/, ""))) delete next.sort;
  if (next.panel !== undefined && (pendingCount === 0 || diffActive)) delete next.panel;
  return next;
};

/** 今の画面のハッシュの引数にする。ネットワークは `view` を写さない */
export const toLegacyHash = (search: PreviewSearch, tab: string | undefined = search.tab): Record<string, string> => {
  const hash: Record<string, string | undefined> = { tab, view: tab === "graph" ? undefined : search.view, id: search.id, full: search.full, diff: search.diff };
  return Object.fromEntries(Object.entries(hash).filter((entry): entry is [string, string] => entry[1] !== undefined));
};
