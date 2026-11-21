// 絞り込みのプリセットのタグの式を、絞り込みのドロワーのタグの条件と組み合わせ方に置き換える計算
import type { TagMatch } from "@/shared/core/filters";

/** タグを比べる条件。`ne` は選んだタグをどれも持たない、`eq` は `match` が `all` なら全て、それ以外はどれかを持つ */
export type PresetCondition = { field: "tags"; op: "eq" | "ne"; values: string[]; match?: "any" | "all" };

/** タグの式。条件か `and`・`or`・`not` の束 */
export type PresetFilter = PresetCondition | { and: PresetFilter[] } | { or: PresetFilter[] } | { not: PresetFilter };

/** 設定の `presets` の 1 件 */
export type Preset = { name: string; description?: string; filter: PresetFilter };

/** プリセットを選んだときにタグの条件へ入れるタグと組み合わせ方 */
export type PresetTags = { tags: string[]; match: TagMatch };

/** タグの式を、タグの条件で表せるタグと組み合わせ方にする。表せない式（`ne`・束）は null */
export const presetTagsOf = (filter: PresetFilter): PresetTags | null => {
  if ("and" in filter || "or" in filter || "not" in filter || filter.op !== "eq") return null;
  return { tags: filter.values, match: filter.match === "all" ? "all" : "any" };
};

/** ドロワーに並べるプリセット 1 件。`applied` は今のタグの条件がそのプリセットと同じ */
export type PresetChoice = { name: string; description?: string; count: number; applied: boolean };

const matches = (tags: readonly string[], { tags: wanted, match }: PresetTags): boolean =>
  match === "all" ? wanted.every((tag) => tags.includes(tag)) : wanted.some((tag) => tags.includes(tag));

/** 並び順を問わず同じタグの集まりか */
const sameTags = (left: readonly string[], right: readonly string[]): boolean => left.length === right.length && left.every((tag) => right.includes(tag));

/** 設定のプリセットのうちタグの条件で表せるものを並び順のまま、画面の項目のうち合う件数と、今のタグの条件と同じかを添えて返却する */
export const presetChoicesOf = ({ presets, rowTags, tags, tagMatch }: { presets: readonly Preset[]; rowTags: readonly (readonly string[])[]; tags: readonly string[]; tagMatch: TagMatch }): PresetChoice[] =>
  presets.flatMap((preset) => {
    const wanted = presetTagsOf(preset.filter);
    if (wanted === null) return [];
    // タグが 1 つなら組み合わせ方は問わない
    const applied = sameTags(tags, wanted.tags) && (wanted.tags.length < 2 || tagMatch === wanted.match);
    return [{ name: preset.name, ...(preset.description === undefined ? {} : { description: preset.description }), count: rowTags.filter((one) => matches(one, wanted)).length, applied }];
  });
