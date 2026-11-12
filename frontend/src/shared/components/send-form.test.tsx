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
    const submit = screen.getByRole("button", { name: "レビューに追加" });
    expect(submit).toHaveTextContent(/^$/);
    expect(submit).toHaveAttribute("title", "レビューに追加（Ctrl+Enter）");
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

  // 閉じた形と開閉（正常系）
  test("send_form_when_closed", async () => {
    // 準備
    const onToggleOpen = vi.fn();
    render(<SendForm target="D-1" loc={null} body="案 A にする" status="idle" open={false} onSubmit={vi.fn()} onInput={vi.fn()} onToggleOpen={onToggleOpen} />);
    const toggle = screen.getByRole("button", { name: "コメントの入力を開く" });
    // 実行
    await userEvent.click(toggle);
    // 検証
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button", { name: "レビューに追加" })).toBeNull();
    expect(screen.getByText("書きかけ")).toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(onToggleOpen).toHaveBeenCalledWith(true);
  });

  // 音声入力の状態ごとのボタンと結果の行（正常系）
  test("send_form_when_voice", () => {
    // 準備と実行
    const { rerender, container } = render(<SendForm target="D-1" loc={null} body="" status="idle" voice="idle" onSubmit={vi.fn()} onInput={vi.fn()} />);
    const mic = screen.getByRole("button", { name: "音声で入力" });
    // 検証
    expect(mic.compareDocumentPosition(screen.getByRole("button", { name: "レビューに追加" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    rerender(<SendForm target="D-1" loc={null} body="" status="idle" voice="disabled" voiceReason="理由の文" onSubmit={vi.fn()} onInput={vi.fn()} />);
    const disabledMic = screen.getByRole("button", { name: "音声で入力" });
    expect(disabledMic).toHaveAttribute("aria-disabled", "true");
    expect(disabledMic).toHaveAccessibleDescription("理由の文");
    rerender(<SendForm target="D-1" loc={null} body="" status="idle" voice="recording" elapsed={72} levels={[0.2, 0.8]} onSubmit={vi.fn()} onInput={vi.fn()} />);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(container.querySelectorAll('[data-part="voice-wave"][aria-hidden="true"] i')).toHaveLength(2);
    expect(screen.getByRole("button", { name: "文字起こし" })).toHaveFocus();
    expect(screen.getByRole("button", { name: "キャンセル" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "文字起こし" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "レビューに追加" })).toBeNull();
    expect(screen.getByText("1:12")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("status")).toHaveTextContent("録音中");
    rerender(<SendForm target="D-1" loc={null} body="確認: " status="idle" voice="transcribing" onSubmit={vi.fn()} onInput={vi.fn()} />);
    expect(screen.getByRole("button", { name: "キャンセル" })).toBeDisabled();
    expect(screen.getByRole("textbox")).toHaveAttribute("readonly");
  });

  // 音声入力のイベント（正常系）
  test("send_form_when_voice_events", async () => {
    // 準備
    const onVoiceStart = vi.fn();
    const onVoiceCancel = vi.fn();
    const onVoiceDone = vi.fn();
    const onVoiceBlocked = vi.fn();
    const handlers = { onVoiceStart, onVoiceCancel, onVoiceDone, onVoiceBlocked, onSubmit: vi.fn(), onInput: vi.fn() };
    const { rerender } = render(<SendForm target="D-1" loc={null} body="" status="idle" voice="idle" {...handlers} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "音声で入力" }));
    rerender(<SendForm target="D-1" loc={null} body="確認: " status="idle" voice="recording" {...handlers} />);
    await userEvent.click(screen.getByRole("button", { name: "キャンセル" }));
    await userEvent.click(screen.getByRole("button", { name: "文字起こし" }));
    rerender(<SendForm target="D-1" loc={null} body="" status="idle" voice="disabled" voiceReason="理由" {...handlers} />);
    await userEvent.click(screen.getByRole("button", { name: "音声で入力" }));
    // 検証
    expect(onVoiceStart).toHaveBeenCalledTimes(1);
    expect(onVoiceCancel).toHaveBeenCalledTimes(1);
    expect(onVoiceDone).toHaveBeenCalledWith("D-1", null, "確認: ");
    expect(onVoiceBlocked).toHaveBeenCalledTimes(1);
  });

  // 録音を終えたら入力欄へフォーカスを戻す（正常系）
  test("send_form_when_recording_ended", async () => {
    // 準備
    const props = { target: "D-1", loc: null, body: "確認: でよい", status: "idle" as const, onSubmit: vi.fn(), onInput: vi.fn() };
    const { rerender } = render(<SendForm {...props} voice="idle" />);
    const textbox = screen.getByRole<HTMLTextAreaElement>("textbox");
    await userEvent.click(textbox);
    textbox.setSelectionRange(4, 4);
    // 実行
    rerender(<SendForm {...props} voice="recording" levels={[0.5]} />);
    rerender(<SendForm {...props} voice="idle" />);
    // 検証
    const restored = screen.getByRole<HTMLTextAreaElement>("textbox");
    expect(restored).toHaveFocus();
    expect([restored.selectionStart, restored.selectionEnd]).toEqual([4, 4]);
  });
});
