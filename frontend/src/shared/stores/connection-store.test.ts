import { describe, expect, test } from "vitest";

import { useConnectionStore } from "@/shared/stores/connection-store";

describe("useConnectionStore.setConnection", () => {
  // 書き換える（正常系）
  test("set_connection", () => {
    // 実行
    useConnectionStore.getState().setConnection("offline");
    // 検証
    expect(useConnectionStore.getState().connection).toBe("offline");
  });
});

describe("useConnectionStore.setRefreshing", () => {
  // 書き換える（正常系）
  test("set_refreshing", () => {
    // 実行
    useConnectionStore.getState().setRefreshing(true);
    // 検証
    expect(useConnectionStore.getState().refreshing).toBe(true);
  });
});
