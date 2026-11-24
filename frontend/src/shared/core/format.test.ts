import { describe, expect, test } from "vitest";

import { formatItemDateTime } from "@/shared/core/format";

describe("formatItemDateTime", () => {
  // 今年は年を出さない（正常系）
  test.each([
    { iso: "2026-11-20T09:40:00+00:00", expected: "11/20 18:40" },
    { iso: "2025-12-28T00:00:00+00:00", expected: "2025/12/28 09:00" },
    { iso: "2025-12-31T16:00:00+00:00", expected: "01/01 01:00" },
  ])("format_item_date_time", ({ iso, expected }) => {
    // 準備
    const now = new Date("2026-11-24T03:00:00+00:00");
    // 実行・検証
    expect(formatItemDateTime(iso, now)).toBe(expected);
  });
});
