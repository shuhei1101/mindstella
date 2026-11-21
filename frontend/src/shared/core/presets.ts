// タグの式（絞り込みのプリセットと画面のタグの条件）の適用・表示・プリセットの並びの計算
import type { TagMatch } from "@/shared/core/filters";

/** タグを比べる条件。`ne` は選んだタグをどれも持たない、`eq` は `match` が `all` なら全て、それ以外はどれかを持つ */
export type PresetCondition = { field: "tags"; op: "eq" | "ne"; values: string[]; match?: "any" | "all" };

/** タグの式の束 */
export type PresetBundle = { and: PresetFilter[] } | { or: PresetFilter[] } | { not: PresetFilter };

/** タグの式。条件か `and`・`or`・`not` の束 */
export type PresetFilter = PresetCondition | PresetBundle;

/** 設定の `presets` の 1 件 */
export type Preset = { name: string; description?: string; filter: PresetFilter };

/** 束の入れ子の深さの上限（最上位の束を 1 レイヤーとする） */
export const MAX_TAG_EXPR_LAYERS = 3;

/** タグを NFKC と小文字にそろえる */
const normalizeTag = (tag: string): string => tag.normalize("NFKC").toLowerCase();

const matchesNode = (names: ReadonlySet<string>, node: PresetFilter): boolean => {
  if ("and" in node) return node.and.every((child) => matchesNode(names, child));
  if ("or" in node) return node.or.some((child) => matchesNode(names, child));
  if ("not" in node) return !matchesNode(names, node.not);
  const values = node.values.map(normalizeTag);
  // 値の無い条件は絞らない
  if (values.length === 0) return true;
  // タグの無い項目も、選んだタグをどれも持たないので合う
  if (node.op === "ne") return values.every((value) => !names.has(value));
  if (node.match === "all") return values.every((value) => names.has(value));
  return values.some((value) => names.has(value));
};

/** URL の式（JSON）を読む。式として読めない値は null */
export const parseTagExpr = (text: string): PresetFilter | null => {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    // URL は利用者が書き換えられる外部入力のため、読めない値は条件を持たないものとして扱う
    return null;
  }
  return isTagExpr(value) ? value : null;
};

const isTagExpr = (value: unknown): value is PresetFilter => {
  if (typeof value !== "object" || value === null) return false;
  const node = value as Record<string, unknown>;
  if (Array.isArray(node["and"])) return node["and"].every(isTagExpr);
  if (Array.isArray(node["or"])) return node["or"].every(isTagExpr);
  if ("not" in node) return isTagExpr(node["not"]);
  return node["field"] === "tags" && (node["op"] === "eq" || node["op"] === "ne") && Array.isArray(node["values"]) && node["values"].every((item) => typeof item === "string");
};

/** 項目のタグの名前がタグの式に合うかを返却する */
export const matchesTagExpr = (tags: readonly string[], filter: PresetFilter): boolean => matchesNode(new Set(tags.map(normalizeTag)), filter);

/** タグの並びと組み合わせ方を、1 つの条件の式にする */
export const tagExprOf = ({ tags, match }: { tags: readonly string[]; match: TagMatch }): PresetCondition => ({ field: "tags", op: "eq", values: [...tags], ...(match === "all" ? { match: "all" as const } : {}) });

/** 式が 1 つの「含む」の条件なら、タグの並びと組み合わせ方を返却する。それ以外は null */
export const simpleTagsOf = (filter: PresetFilter): { tags: string[]; match: TagMatch } | null => {
  if ("and" in filter || "or" in filter || "not" in filter || filter.op !== "eq") return null;
  return { tags: filter.values, match: filter.match === "all" ? "all" : "any" };
};

const describeNode = (node: PresetFilter): string => {
  if ("and" in node) return node.and.map((child) => wrap(child)).join(" かつ ");
  if ("or" in node) return node.or.map((child) => wrap(child)).join(" または ");
  if ("not" in node) return `（${describeNode(node.not)}）でない`;
  const joint = node.match === "all" ? "と" : "か";
  const names = node.values.map((value) => `「${value}」`).join(joint);
  return node.op === "ne" ? `${names}を含まない` : `${names}を含む`;
};

const wrap = (node: PresetFilter): string => ("and" in node || "or" in node ? `（${describeNode(node)}）` : describeNode(node));

/** 式を条件のチップに出す文にする */
export const describeTagExpr = (filter: PresetFilter): string => describeNode(filter);

/** ドロワーに並べるプリセット 1 件。`applied` は今のタグの式がそのプリセットと同じ */
export type PresetChoice = { name: string; description?: string; count: number; applied: boolean };

/** 設定のプリセットを並び順のまま、画面の項目のうち式に合う件数と、今のタグの式と同じかを添えて返却する */
export const presetChoicesOf = ({ presets, rowTags, current }: { presets: readonly Preset[]; rowTags: readonly (readonly string[])[]; current: PresetFilter | null }): PresetChoice[] =>
  presets.map((preset) => ({
    name: preset.name,
    ...(preset.description === undefined ? {} : { description: preset.description }),
    count: rowTags.filter((one) => matchesTagExpr(one, preset.filter)).length,
    applied: current !== null && JSON.stringify(current) === JSON.stringify(preset.filter),
  }));
