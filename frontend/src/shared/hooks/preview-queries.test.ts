import { QueryClient } from "@tanstack/react-query";
import { describe, expect, test, vi } from "vitest";

import { invalidatePreview, previewQueries } from "@/shared/hooks/preview-queries";

const KEYS = [["/api/records"], ["/api/comments"], ["/api/edits"], ["/api/threads"]];

describe("previewQueries", () => {
  // 4 つを返す（正常系）
  test("preview_queries", () => {
    expect(previewQueries().map((query) => query.queryKey)).toEqual(KEYS);
  });
});

describe("invalidatePreview", () => {
  // 4 つを読み直す（正常系）
  test("invalidate_preview", async () => {
    // 準備
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    await invalidatePreview(queryClient);
    // 検証
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toEqual(KEYS);
  });
});
