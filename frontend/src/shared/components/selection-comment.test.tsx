import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SelectionComment } from "@/shared/components/selection-comment";

const rect = (top: number): DOMRect => new DOMRect(100, top, 200, 20);
const area = { viewport: { width: 1280, height: 800 }, scroller: new DOMRect(0, 60, 1280, 740) };

describe("SelectionComment", () => {
  // 押す（正常系）
  test("selection_comment", async () => {
    // 準備
    const onOpen = vi.fn();
    render(<SelectionComment anchor={{ first: rect(300), last: rect(320) }} area={area} onOpen={onOpen} onClose={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "選んだ箇所にコメント" }));
    // 検証
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  // 上に収まらない（正常系）
  test("selection_comment_when_below", () => {
    // 準備と実行
    render(<SelectionComment anchor={{ first: rect(62), last: rect(82) }} area={area} onOpen={vi.fn()} onClose={vi.fn()} />);
    const button = screen.getByRole("button", { name: "選んだ箇所にコメント" });
    // 検証
    expect(Number.parseFloat(button.style.top)).toBeGreaterThanOrEqual(82 + 20);
  });
});
