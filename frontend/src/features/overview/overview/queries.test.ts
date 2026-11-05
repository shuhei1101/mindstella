import { describe, expect, test } from "vitest";

import { overviewQueries } from "@/features/overview/overview/queries";

describe("overviewQueries", () => {
  // 4 つの API の query（正常系）
  test("overview_queries", () => {
    // 実行
    const queries = overviewQueries();
    // 検証
    expect(queries.map((query) => query.queryKey[0])).toEqual(["/api/records", "/api/comments", "/api/edits", "/api/threads"]);
  });
});
