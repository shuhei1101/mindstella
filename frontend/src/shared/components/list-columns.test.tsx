import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { commonColumns, favoriteColumn } from "@/shared/components/list-columns";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-24T03:00:00+00:00"));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("commonColumns", () => {
  // 日時の列が末尾にあり、セルを time で描く（正常系）
  test("common_columns_when_datetime", () => {
    // 準備
    const columns = commonColumns();
    const row = { id: "D-1", title: "題", created: "2026-11-02T01:15:00+00:00", updated: "2026-11-20T09:40:00+00:00" };
    // 実行
    const { container } = render(<>{columns.updated.cell?.(row)}</>);
    // 検証
    expect(Object.keys(columns).slice(-2)).toEqual(["created", "updated"]);
    const time = container.querySelector("time");
    expect(time).toHaveAttribute("datetime", "2026-11-20T09:40:00+00:00");
    expect(time).toHaveTextContent("11/20 18:40");
    expect(columns.created.get(row)).toBe("2026-11-02T01:15:00+00:00");
  });
});

describe("favoriteColumn", () => {
  // 登録した行は ★ で、星を押すと行の ID で知らせる（正常系）
  test("favorite_column", async () => {
    // 準備
    const onToggle = vi.fn();
    const column = favoriteColumn(new Set(["D-1"]), onToggle);
    const on = { id: "D-1", title: "題" };
    const off = { id: "D-2", title: "別" };
    // 実行
    render(<>{column.cell?.(off)}</>);
    await userEvent.click(screen.getByRole("button", { name: "別をお気に入りに登録" }));
    // 検証
    expect(column.key).toBe("favorite");
    expect(column.label).toBe("お気に入り");
    expect(column.get?.(on)).toBe("★");
    expect(column.get?.(off)).toBe("");
    expect(onToggle).toHaveBeenCalledWith("D-2");
  });
});
