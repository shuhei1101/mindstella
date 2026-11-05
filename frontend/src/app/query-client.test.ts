import { describe, expect, test } from "vitest";

import { createQueryClient } from "@/app/query-client";

describe("createQueryClient", () => {
  // 既定の option で作る（正常系）
  test("create_query_client", () => {
    // 実行
    const queryClient = createQueryClient();
    // 検証
    expect(queryClient.getDefaultOptions().queries).toMatchObject({ staleTime: 60000, refetchOnWindowFocus: false, retry: false });
  });
});
