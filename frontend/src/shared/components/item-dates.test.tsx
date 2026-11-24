import { render } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ItemDates } from "@/shared/components/item-dates";

afterEach(() => {
  vi.useRealTimers();
});

describe("ItemDates", () => {
  // 作成と更新を time で描く（正常系）
  test("item_dates", () => {
    // 準備
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-24T03:00:00+00:00"));
    // 実行
    const { container } = render(<ItemDates created="2026-11-02T01:15:00+00:00" updated="2026-11-20T09:40:00+00:00" />);
    // 検証
    const times = [...container.querySelectorAll("time")];
    expect(times.map((time) => time.getAttribute("datetime"))).toEqual(["2026-11-02T01:15:00+00:00", "2026-11-20T09:40:00+00:00"]);
    expect(times.map((time) => time.parentElement?.textContent)).toEqual(["作成 11/02 10:15", "更新 11/20 18:40"]);
  });
});
