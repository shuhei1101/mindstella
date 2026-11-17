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

  // 誤りを返した値は追加せず、入力欄の直下に原因を出す（正常系）
  test("chips_input_when_validate", async () => {
    // 準備
    const onChange = vi.fn();
    const validate = (value: string) => (value === "保存先" ? { value: "D-2" } : { error: `${value} が見つかりません。ID を確認してください。` });
    render(<ChipsInput controlId="rel" name="前提" values={[]} validate={validate} onChange={onChange} />);
    const input = screen.getByRole("combobox", { name: /前提/ });
    // 実行
    await userEvent.type(input, "保存先{Enter}");
    await userEvent.type(input, "D-99{Enter}");
    // 検証
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(["D-2"], null);
    expect(input).toHaveValue("D-99");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("入力の誤り: D-99 が見つかりません。ID を確認してください。");
  });
});
