import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, test } from "vitest";

import { createAppRouter } from "@/app/router";

describe("createAppRouter", () => {
  afterEach(() => {
    history.replaceState(null, "", "/");
  });

  // basepath と context を持つ（正常系）
  test("create_app_router", () => {
    // 準備
    history.replaceState(null, "", "/w/mindstella-x-1/spa/");
    const queryClient = new QueryClient();
    // 実行
    const router = createAppRouter(queryClient);
    // 検証
    expect(router.options.basepath).toBe("/w/mindstella-x-1/spa");
    expect(router.options.context).toEqual({ queryClient });
  });
});
