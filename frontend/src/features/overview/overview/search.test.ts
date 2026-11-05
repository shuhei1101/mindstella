import { describe, expect, test } from "vitest";

import { parseOverviewSearch } from "@/features/overview/overview/search";

describe("parseOverviewSearch", () => {
  // overview を受ける（正常系）
  test("parse_overview_search", () => {
    // 実行
    const search = parseOverviewSearch({ tab: "overview" });
    // 検証
    expect(search).toEqual({ tab: "overview" });
  });

  // 決めた値以外は落とす（正常系）
  test("parse_overview_search_when_unknown", () => {
    // 実行
    const search = parseOverviewSearch({ tab: "unknown" });
    // 検証
    expect(search).toEqual({ tab: undefined });
  });
});
