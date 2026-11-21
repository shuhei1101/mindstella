import { describe, expect, test } from "vitest";

import { describeTagExpr, matchesTagExpr, parseTagExpr, presetChoicesOf, simpleTagsOf, tagExprOf, type PresetFilter } from "@/shared/core/presets";

const INCLUDE_EXCLUDE: PresetFilter = { and: [{ field: "tags", op: "eq", values: ["画面"] }, { field: "tags", op: "ne", values: ["廃止"] }] };

describe("parseTagExpr", () => {
  // 束を持つ式を読む（正常系）
  test("parse_tag_expr", () => {
    expect(parseTagExpr(JSON.stringify(INCLUDE_EXCLUDE))).toEqual(INCLUDE_EXCLUDE);
  });

  // 読めない値（異常系）
  test.each([["{"], ['{"field":"tags","op":"gt","values":[]}'], ['{"field":"tags","op":"eq","values":[1]}']])("parse_tag_expr_when_invalid %s", (text) => {
    expect(parseTagExpr(text)).toBeNull();
  });
});

describe("matchesTagExpr", () => {
  // 含むと含まないの組み合わせ（正常系）
  test.each([
    [["画面"], true],
    [["画面", "廃止"], false],
    [[], false],
  ])("matches_tag_expr %j", (tags, expected) => {
    expect(matchesTagExpr(tags, INCLUDE_EXCLUDE)).toBe(expected);
  });

  // 入れ子の束と表記の揺れ（正常系）
  test.each([
    [["保存"], true],
    [["ｶﾞﾒﾝ"], false],
    [["画面", "廃止"], true],
  ])("matches_tag_expr_when_nested %j", (tags, expected) => {
    const nested: PresetFilter = { or: [{ field: "tags", op: "eq", values: ["保存"] }, { and: [{ field: "tags", op: "eq", values: ["画面", "廃止"], match: "all" }] }] };
    expect(matchesTagExpr(tags, nested)).toBe(expected);
  });
});

describe("simpleTagsOf", () => {
  // 簡易で表せる式と表せない式（正常系）
  test.each<[PresetFilter, ReturnType<typeof simpleTagsOf>]>([
    [{ field: "tags", op: "eq", values: ["画面", "廃止"], match: "all" }, { tags: ["画面", "廃止"], match: "all" }],
    [{ field: "tags", op: "ne", values: ["廃止"] }, null],
    [INCLUDE_EXCLUDE, null],
  ])("simple_tags_of %#", (filter, expected) => {
    expect(simpleTagsOf(filter)).toEqual(expected);
  });
});

describe("tagExprOf", () => {
  // 組み合わせ方ごとの条件（正常系）
  test("tag_expr_of", () => {
    expect(tagExprOf({ tags: ["画面", "廃止"], match: "all" })).toEqual({ field: "tags", op: "eq", values: ["画面", "廃止"], match: "all" });
    expect(tagExprOf({ tags: ["画面"], match: "any" })).toEqual({ field: "tags", op: "eq", values: ["画面"] });
  });
});

describe("describeTagExpr", () => {
  // 束と否定の文（正常系）
  test("describe_tag_expr", () => {
    expect(describeTagExpr(INCLUDE_EXCLUDE)).toBe("「画面」を含む かつ 「廃止」を含まない");
    expect(describeTagExpr({ not: { field: "tags", op: "eq", values: ["通知"] } })).toBe("（「通知」を含む）以外");
  });
});

describe("presetChoicesOf", () => {
  // 件数と選択済み（正常系）
  test("preset_choices_of", () => {
    // 準備
    const presets = [
      { name: "画面の設計", filter: INCLUDE_EXCLUDE },
      { name: "通知", filter: { field: "tags" as const, op: "eq" as const, values: ["通知"] } },
    ];
    const rowTags = [["画面"], ["画面", "廃止"], ["画面"], ["保存"]];
    // 実行
    const choices = presetChoicesOf({ presets, rowTags, current: INCLUDE_EXCLUDE });
    // 検証
    expect(choices).toEqual([
      { name: "画面の設計", count: 2, applied: true },
      { name: "通知", count: 0, applied: false },
    ]);
  });
});
