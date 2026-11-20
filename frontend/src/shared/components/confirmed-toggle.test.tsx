import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ConfirmedToggle } from "@/shared/components/confirmed-toggle";

describe("ConfirmedToggle", () => {
  // 未確認で押すと切り替えを知らせる（正常系）
  test("confirmed_toggle", async () => {
    // 準備
    const onToggle = vi.fn();
    render(<ConfirmedToggle confirmed={false} onToggle={onToggle} />);
    const button = screen.getByRole("button", { name: "確認済み" });
    // 実行
    await userEvent.click(button);
    // 検証
    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(button).toHaveAttribute("aria-pressed", "false");
    expect(button).toHaveAttribute("title", "確認済みにする");
  });

  // 確認済みは押した状態と解除の title（正常系）
  test("confirmed_toggle_when_confirmed", () => {
    // 準備・実行
    render(<ConfirmedToggle confirmed onToggle={vi.fn()} />);
    // 検証
    const button = screen.getByRole("button", { name: "確認済み" });
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(button).toHaveAttribute("title", "確認済みを解除する");
  });

  // 書き込みの間は押せない（正常系）
  test("confirmed_toggle_when_saving", async () => {
    // 準備
    const onToggle = vi.fn();
    render(<ConfirmedToggle confirmed={false} saving onToggle={onToggle} />);
    const button = screen.getByRole("button", { name: "確認済み" });
    // 実行
    await userEvent.click(button);
    // 検証
    expect(button).toBeDisabled();
    expect(onToggle).not.toHaveBeenCalled();
  });
});
