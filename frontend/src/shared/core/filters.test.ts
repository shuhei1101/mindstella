import { describe, expect, test } from "vitest";

import { defaultFilters, filtersFromSearch, filtersToSearch, matchesFilters } from "@/shared/core/filters";

describe("matchesFilters", () => {
  // 値の条件（正常系）
  test("matches_filters", () => {
    expect(matchesFilters({ status: "保留" }, { status: ["要見直し", "保留"] })).toBe(true);
  });

  // 文字の条件は大文字・小文字を区別しない（正常系）
  test("matches_filters_when_text", () => {
    expect(matchesFilters({ title: "ABCD" }, { "~title": ["abc"] })).toBe(true);
  });

  // 合わない（正常系）
  test("matches_filters_when_not_match", () => {
    expect(matchesFilters({ status: "完了" }, { status: ["保留"] })).toBe(false);
  });

  // タグの組み合わせ方（正常系）
  test.each([
    { tags: ["画面"], tagMatch: "all" as const, expected: false },
    { tags: ["画面"], tagMatch: "any" as const, expected: true },
    { tags: ["画面", "保存"], tagMatch: "all" as const, expected: true },
  ])("matches_filters_when_tag_match $tagMatch $tags", ({ tags, tagMatch, expected }) => {
    expect(matchesFilters({ tags }, { tags: ["画面", "保存"] }, tagMatch)).toBe(expected);
  });
});

describe("defaultFilters", () => {
  // 検討事項の既定（正常系）
  test("default_filters", () => {
    expect(defaultFilters("decisions")).toEqual({ status: ["要見直し", "未決定", "未整理", "保留"] });
  });
});

describe("filtersFromSearch", () => {
  // 値を分ける（正常系）
  test("filters_from_search", () => {
    expect(filtersFromSearch({ status: "保留|完了", "~title": "a|b" })).toEqual({ status: ["保留", "完了"], "~title": ["a|b"] });
  });
});

describe("filtersToSearch", () => {
  // 値をつなぐ（正常系）
  test("filters_to_search", () => {
    expect(filtersToSearch({ status: ["保留", "完了"] })).toEqual({ status: "保留|完了" });
  });
});
