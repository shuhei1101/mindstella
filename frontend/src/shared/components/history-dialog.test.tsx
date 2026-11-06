import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { HistoryDialog } from "@/shared/components/history-dialog";

describe("HistoryDialog", () => {
  // 時点を選ぶ（正常系）
  test("history_dialog", async () => {
    // 準備
    const onSelect = vi.fn();
    render(<HistoryDialog points={[{ sel: "V-1", name: "1 回目", sub: "11/01 09:00", count: 1 }]} current="" onSelect={onSelect} onClose={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /1 回目/ }));
    // 検証
    expect(onSelect).toHaveBeenCalledWith("V-1");
  });
});
