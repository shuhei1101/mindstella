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

  // 未読の行にマーカーを付け、すべて既読にするを押すとイベントを通知する（正常系）
  test("history_dialog_when_unread", async () => {
    // 準備
    const onMarkAllRead = vi.fn();
    render(
      <HistoryDialog
        points={[
          { sel: "V-2", name: "2 回目", sub: "11/02 09:00", count: 1, unread: false },
          { sel: "V-1", name: "1 回目", sub: "11/01 09:00", count: 1, unread: true },
        ]}
        current=""
        onSelect={vi.fn()}
        onClose={vi.fn()}
        onMarkAllRead={onMarkAllRead}
      />,
    );
    // 検証
    expect(screen.getByText("未読 1 件")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /1 回目/ })).toHaveTextContent("未読");
    expect(screen.getByRole("button", { name: /2 回目/ })).not.toHaveTextContent("未読");
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "すべて既読にする" }));
    // 検証
    expect(onMarkAllRead).toHaveBeenCalledTimes(1);
  });

  // 未読が無ければすべて既読にするを押せない（正常系）
  test("history_dialog_when_all_read", () => {
    // 実行
    render(<HistoryDialog points={[{ sel: "V-1", name: "1 回目", sub: "11/01 09:00", count: 1, unread: false }]} current="" onSelect={vi.fn()} onClose={vi.fn()} onMarkAllRead={vi.fn()} />);
    // 検証
    expect(screen.getByText("未読はありません")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "すべて既読にする" })).toBeDisabled();
  });
});
