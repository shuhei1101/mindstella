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
    const { rerender, container } = render(<ReplyForm thread="TH-1" body="案 A" status="idle" voice="recording" elapsed={5} levels={[0.5]} onVoiceDone={onVoiceDone} onVoiceBlocked={onVoiceBlocked} onSubmit={vi.fn()} onInput={vi.fn()} />);
    const hidden = screen.queryByRole("textbox");
    const bars = container.querySelectorAll('[data-part="voice-wave"][aria-hidden="true"] i').length;
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "文字起こし" }));
    const elapsed = screen.getByText("0:05");
    rerender(<ReplyForm thread="TH-1" body="" status="idle" voice="disabled" voiceReason="理由" onVoiceDone={onVoiceDone} onVoiceBlocked={onVoiceBlocked} onSubmit={vi.fn()} onInput={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "音声で入力" }));
    // 検証
    expect([hidden, bars]).toEqual([null, 1]);
    expect(onVoiceDone).toHaveBeenCalledWith("TH-1", "案 A");
    expect(elapsed).toBeTruthy();
    expect(onVoiceBlocked).toHaveBeenCalledTimes(1);
  });

  // 録音を終えたら入力欄へフォーカスを戻す（正常系）
  test("reply_form_when_recording_ended", async () => {
    // 準備
    const props = { thread: "TH-1", body: "確認: でよい", status: "idle" as const, onSubmit: vi.fn(), onInput: vi.fn() };
    const { rerender } = render(<ReplyForm {...props} voice="idle" />);
    const textbox = screen.getByRole<HTMLTextAreaElement>("textbox");
    await userEvent.click(textbox);
    textbox.setSelectionRange(4, 4);
    // 実行
    rerender(<ReplyForm {...props} voice="recording" levels={[0.5]} />);
    const doneFocused = screen.getByRole("button", { name: "文字起こし" }) === document.activeElement;
    rerender(<ReplyForm {...props} voice="idle" />);
    // 検証
    const restored = screen.getByRole<HTMLTextAreaElement>("textbox");
    expect(doneFocused).toBe(true);
    expect(restored).toHaveFocus();
    expect([restored.selectionStart, restored.selectionEnd]).toEqual([4, 4]);
  });

  // 既定の挙動でレビュー中に追加した結果（正常系）
  test("reply_form_when_reviewed", () => {
    // 準備と実行
    render(<ReplyForm thread="TH-1" body="" status="reviewed" onSubmit={vi.fn()} onInput={vi.fn()} />);
    // 検証
    expect(screen.getByRole("status")).toHaveTextContent("文字起こしの結果をレビュー中に追加しました。");
  });
});
