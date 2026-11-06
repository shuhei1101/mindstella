import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ViewSwitch } from "@/shared/components/view-switch";

describe("ViewSwitch", () => {
  // 形式を切り替える（正常系）
  test("view_switch", async () => {
    // 準備
    const onChange = vi.fn();
    render(<ViewSwitch views={[{ key: "board", label: "ボード" }, { key: "table", label: "表" }]} current="board" onChange={onChange} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "表" }));
    // 検証
    expect(onChange).toHaveBeenCalledWith("table");
  });
});
