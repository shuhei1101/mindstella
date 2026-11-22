import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { Button } from "@/shared/components/ui/button";

afterEach(() => {
  vi.useRealTimers();
});

describe("Button", () => {
  // 待つ間は押せず、1 秒を超えたら回るマーカーを出す（正常系）
  test("button_when_pending", () => {
    // 準備
    vi.useFakeTimers();
    const onClick = vi.fn();
    render(<Button pending onClick={onClick}><span data-testid="label">保存する</span></Button>);
    const button = screen.getByRole("button", { name: "保存する" });
    // 実行（999ms）
    act(() => { vi.advanceTimersByTime(999); });
    fireEvent.click(button);
    // 検証
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(onClick).not.toHaveBeenCalled();
    expect(button.querySelector("[data-part='pending-spinner']")).toBeNull();
    expect(screen.getByTestId("label")).toBeInTheDocument();
    // 実行（1000ms）
    act(() => { vi.advanceTimersByTime(1); });
    // 検証
    expect(button.querySelector("[data-part='pending-spinner']")).not.toBeNull();
    expect(screen.getByTestId("label")).toBeInTheDocument();
  });
});
