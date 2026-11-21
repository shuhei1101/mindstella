// 絞り込みのプリセットのタグの式を、項目のタグに適用する計算

/** タグを比べる条件。`ne` は選んだタグをどれも持たない、`eq` は `match` が `all` なら全て、それ以外はどれかを持つ */
export type PresetCondition = { field: "tags"; op: "eq" | "ne"; values: string[]; match?: "any" | "all" };

/** タグの式。条件か `and`・`or`・`not` の束 */
export type PresetFilter = PresetCondition | { and: PresetFilter[] } | { or: PresetFilter[] } | { not: PresetFilter };

/** 設定の `presets` の 1 件 */
export type Preset = { name: string; description?: string; filter: PresetFilter };

/** タグを NFKC と小文字にそろえる */
const normalizeTag = (tag: string): string => tag.normalize("NFKC").toLowerCase();

const matchesNode = (names: ReadonlySet<string>, node: PresetFilter): boolean => {
  if ("and" in node) return node.and.every((child) => matchesNode(names, child));
  if ("or" in node) return node.or.some((child) => matchesNode(names, child));
  if ("not" in node) return !matchesNode(names, node.not);
  const values = node.values.map(normalizeTag);
  // タグの無い項目も、選んだタグをどれも持たないので合う
  if (node.op === "ne") return values.every((value) => !names.has(value));
  if (node.match === "all") return values.every((value) => names.has(value));
  return values.some((value) => names.has(value));
};

/** 項目のタグの名前がタグの式に合うかを返却する */
export const matchesPreset = (tags: readonly string[], filter: PresetFilter): boolean => matchesNode(new Set(tags.map(normalizeTag)), filter);

/** 一覧の上に並べるプリセット 1 件 */
export type PresetChoice = { name: string; description?: string; count: number };

/** 設定のプリセットを並び順のまま、記録の取得の件数を添えて返却する */
export const presetChoicesOf = ({ presets, counts }: { presets: readonly Preset[]; counts: Readonly<Record<string, number>> }): PresetChoice[] =>
  presets.map((preset) => ({ name: preset.name, ...(preset.description === undefined ? {} : { description: preset.description }), count: counts[preset.name] ?? 0 }));
