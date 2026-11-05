import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ChipsInput } from "@/shared/components/chips-input";

describe("ChipsInput", () => {
  // 値を足す（正常系）
  test("chips_input", async () => {
    // 準備
    const onChange = vi.fn();
    render(<ChipsInput controlId="tags" name="タグ" values={["一"]} onChange={onChange} />);
    // 実行
    await userEvent.type(screen.getByRole("combobox", { name: /タグ/ }), "二{Enter}");
    // 検証
    expect(onChange).toHaveBeenCalledWith(["一", "二"], null);
  });
});
