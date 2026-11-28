import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SessionStatusBanner, type SessionStatus } from "@/shared/components/session-status-banner";

describe("SessionStatusBanner", () => {
  // 状態ごとの役割と文言を出す（正常系）
  test.each<{ name: string; status: SessionStatus; role: string | null; text: string }>([
    { name: "restarting", status: { kind: "restarting", waiting: 2 }, role: "status", text: "送信したコメント 2 件は、準備ができてから入力します。" },
    { name: "failed", status: { kind: "failed", reason: "空いたアカウントがありません。", retrying: false }, role: "alert", text: "空いたアカウントがありません。" },
    { name: "retrying", status: { kind: "failed", reason: "空いたアカウントがありません。", retrying: true }, role: "alert", text: "再起動中" },
    { name: "launch_record_missing", status: { kind: "launch_record_missing" }, role: "alert", text: "追加の MCP とプラグインの記録がありません" },
    { name: "running", status: { kind: "running" }, role: null, text: "" },
  ])("session_status_banner: $name", ({ status, role, text }) => {
    // 実行
    const { container } = render(<SessionStatusBanner status={status} onRestart={vi.fn()} onClose={vi.fn()} />);
    // 検証
    expect(container.firstElementChild?.getAttribute("role") ?? null).toBe(role);
    expect(container.textContent).toContain(text);
  });

  // 「再起動中」の間は押せない（正常系）
  test("session_status_banner_when_retrying", () => {
    // 実行
    render(<SessionStatusBanner status={{ kind: "failed", reason: "x", retrying: true }} onRestart={vi.fn()} onClose={vi.fn()} />);
    // 検証
    expect(screen.getByRole("button", { name: /再起動中/ })).toBeDisabled();
  });

  // 再起動と閉じるを伝える（正常系）
  test("session_status_banner_when_clicked", async () => {
    // 準備
    const onRestart = vi.fn();
    const onClose = vi.fn();
    const { rerender } = render(<SessionStatusBanner status={{ kind: "failed", reason: "x", retrying: false }} onRestart={onRestart} onClose={onClose} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "再起動" }));
    rerender(<SessionStatusBanner status={{ kind: "launch_record_missing" }} onRestart={onRestart} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: "警告を閉じる" }));
    // 検証
    expect(onRestart).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
