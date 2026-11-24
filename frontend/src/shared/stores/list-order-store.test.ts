import { describe, expect, test } from "vitest";

import { siblingOf } from "@/shared/stores/list-order-store";

describe("siblingOf", () => {
  // 前後を求める（正常系）
  test.each([
    { orders: [["D-2", "D-4", "D-5"]], id: "D-4", expected: { position: 2, total: 3, prev: "D-2", next: "D-5" } },
    { orders: [["D-2", "D-4", "D-5"]], id: "D-2", expected: { position: 1, total: 3, prev: null, next: "D-4" } },
    { orders: [["D-2", "D-4", "D-5"]], id: "D-9", expected: null },
    { orders: [["D-1"], ["D-2", "D-3"]], id: "D-3", expected: { position: 2, total: 2, prev: "D-2", next: null } },
  ])("sibling_of", ({ orders, id, expected }) => {
    // 実行・検証
    expect(siblingOf(orders, id)).toEqual(expected);
  });
});
