import { describe, expect, test } from "vitest";

import { cn } from "@/shared/lib/cn";

describe("cn", () => {
  // 後のクラスで上書きする（正常系）
  test("cn", () => {
    // 実行
    const className = cn("px-2", "px-4");
    // 検証
    expect(className).toBe("px-4");
  });
});
