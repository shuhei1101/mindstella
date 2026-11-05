import { QueryClient } from "@tanstack/react-query";
import { describe, expect, test } from "vitest";

import { createAppRouter } from "@/app/router";

describe("createAppRouter", () => {
  // basepath と context を持つ（正常系）
  test("create_app_router", () => {
    // 準備
    const queryClient = new QueryClient();
    // 実行
    const router = createAppRouter(queryClient);
    // 検証
    expect(router.options.basepath).toBe("/spa");
    expect(router.options.context).toEqual({ queryClient });
  });
});
