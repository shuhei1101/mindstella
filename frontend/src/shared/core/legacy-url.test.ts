import { describe, expect, test } from "vitest";

import { toLegacyUrl } from "@/shared/core/legacy-url";

describe("toLegacyUrl", () => {
  // 引数をハッシュにする（正常系）
  test("to_legacy_url", () => {
    // 実行
    const url = toLegacyUrl({ tab: "decisions", view: "table", "f.status": "要見直し" });
    // 検証
    expect(url).toBe("/mindstella.html#tab=decisions&view=table&f.status=%E8%A6%81%E8%A6%8B%E7%9B%B4%E3%81%97");
  });
});
