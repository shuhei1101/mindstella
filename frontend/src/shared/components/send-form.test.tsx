import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SendForm } from "@/shared/components/send-form";

describe("SendForm", () => {
  // 溜める（正常系）
  test("send_form", async () => {
    // 準備
    const onSubmit = vi.fn();
    render(<SendForm target="D-1" loc={null} body="案 A にする" status="idle" onSubmit={onSubmit} onInput={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /レビューに追加/ }));
    // 検証
    expect(onSubmit).toHaveBeenCalledWith("D-1", null, "案 A にする");
  });

  // 空白だけ（異常系）
  test("send_form_when_empty", async () => {
    // 準備
    const onSubmit = vi.fn();
    render(<SendForm target="D-1" loc={null} body="   " status="idle" onSubmit={onSubmit} onInput={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /レビューに追加/ }));
    // 検証
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
