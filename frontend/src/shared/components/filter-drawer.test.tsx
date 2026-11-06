import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { FilterDrawer } from "@/shared/components/filter-drawer";

describe("FilterDrawer", () => {
  // 値を選ぶ（正常系）
  test("filter_drawer", async () => {
    // 準備
    const onToggleValue = vi.fn();
    render(<FilterDrawer groups={[{ key: "status", label: "状態", values: [{ value: "保留", count: 2 }] }]} selected={{}} total={2} shown={2} onToggleValue={onToggleValue} onClearGroup={vi.fn()} onClearAll={vi.fn()} onClose={vi.fn()} onTextChange={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("checkbox", { name: /保留/ }));
    // 検証
    expect(onToggleValue).toHaveBeenCalledWith("status", "保留");
  });
});
