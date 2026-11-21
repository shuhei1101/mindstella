import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, test } from "vitest";

import { createAppRouter } from "@/app/router";
import { resetEmbeddedDataForTest } from "@/shared/core/embedded";

describe("createAppRouter", () => {
  afterEach(() => {
    document.body.replaceChildren();
    resetEmbeddedDataForTest();
    history.replaceState(null, "", "/");
  });

  // basepath と context を持つ（正常系）
  test("create_app_router", () => {
    // 準備
    history.replaceState(null, "", "/w/mindstella-x-1/");
    const queryClient = new QueryClient();
    // 実行
    const router = createAppRouter(queryClient);
    // 検証
    expect(router.options.basepath).toBe("/w/mindstella-x-1");
    expect(router.options.context).toEqual({ queryClient });
  });

  // 配る書き出しはハッシュの履歴（正常系）
  test("create_app_router_when_embedded", () => {
    // 準備
    const data = document.createElement("script");
    data.type = "application/json";
    data.id = "mindmap-data";
    data.textContent = '{"settings":{}}';
    document.body.append(data);
    history.replaceState(null, "", "/x/export.html#/?tab=docs");
    const queryClient = new QueryClient();
    // 実行
    const router = createAppRouter(queryClient);
    // 検証
    expect(router.options.basepath).toBe("/");
    expect(router.history.location.pathname).toBe("/");
    expect(router.history.location.search).toBe("?tab=docs");
    expect(window.location.pathname).toBe("/x/export.html");
  });

  // スクロール位置の復元を有効にする（正常系）
  test("create_app_router_when_scroll_restoration", () => {
    // 実行
    const router = createAppRouter(new QueryClient());
    // 検証
    expect(router.options.scrollRestoration).toBe(true);
  });
});
