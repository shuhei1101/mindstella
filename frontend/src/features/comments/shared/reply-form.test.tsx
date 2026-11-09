import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ReplyForm } from "@/features/comments/shared/reply-form";

describe("ReplyForm", () => {
  // 溜める（正常系）
  test("reply_form", async () => {
    // 準備
    const onSubmit = vi.fn();
    render(<ReplyForm thread="TH-1" body="案 A にする" status="idle" onSubmit={onSubmit} onInput={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("textbox"));
    await userEvent.keyboard("{Control>}{Enter}{/Control}");
    // 検証
    expect(onSubmit).toHaveBeenCalledWith("TH-1", "案 A にする");
    const submit = screen.getByRole("button", { name: "レビューに追加" });
    expect(submit).toHaveTextContent(/^$/);
    expect(submit).toHaveAttribute("title", "レビューに追加（Ctrl+Enter）");
  });

  // 溜めている（正常系）
  test("reply_form_when_saving", () => {
    // 準備と実行
    render(<ReplyForm thread="TH-1" body="案 A にする" status="saving" onSubmit={vi.fn()} onInput={vi.fn()} />);
    // 検証
    expect(screen.getByRole("textbox")).toHaveAttribute("readonly");
    expect(screen.getByRole("button", { name: /レビューに追加/ })).toBeDisabled();
  });

  // 音声入力の状態とイベント（正常系）
  test("reply_form_when_voice", async () => {
    // 準備
    const onVoiceDone = vi.fn();
    const onVoiceBlocked = vi.fn();
    const { rerender } = render(<ReplyForm thread="TH-1" body="案 A" status="idle" voice="recording" elapsed={5} onVoiceDone={onVoiceDone} onVoiceBlocked={onVoiceBlocked} onSubmit={vi.fn()} onInput={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "文字起こし" }));
    const elapsed = screen.getByText("0:05");
    rerender(<ReplyForm thread="TH-1" body="" status="idle" voice="disabled" voiceReason="理由" onVoiceDone={onVoiceDone} onVoiceBlocked={onVoiceBlocked} onSubmit={vi.fn()} onInput={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "音声で入力" }));
    // 検証
    expect(onVoiceDone).toHaveBeenCalledWith("TH-1", "案 A");
    expect(elapsed).toBeTruthy();
    expect(onVoiceBlocked).toHaveBeenCalledTimes(1);
  });
});
