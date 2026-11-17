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

  // 外部の変更のまとまりに札を付ける（正常系）
  test("history_dialog_when_external", () => {
    // 実行
    render(
      <HistoryDialog
        points={[
          { sel: "V-2", name: "答えを直した", sub: "11/02 09:00", count: 1 },
          { sel: "V-1", name: "ほかのセッションの書き込み", sub: "11/01 09:00", count: 1, external: true },
        ]}
        current=""
        onSelect={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    // 検証
    expect(screen.getByRole("button", { name: /答えを直した/ })).not.toHaveTextContent("外部の変更");
    expect(screen.getByRole("button", { name: /ほかのセッションの書き込み/ })).toHaveTextContent("外部の変更");
  });
});
