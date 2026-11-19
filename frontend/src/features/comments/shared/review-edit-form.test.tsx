import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ReviewEditForm } from "@/features/comments/shared/review-edit-form";

/** 修正の入力の共通の props */
const base = { id: "C-1", label: "TH-1 への返信", body: "確認: ", onBodyChange: vi.fn(), onSubmit: vi.fn(), onCancel: vi.fn() };

describe("ReviewEditForm", () => {
  // マイクのボタンと録音中の切り替え（正常系）
  test("review_edit_form_voice", async () => {
    // 準備
    const user = userEvent.setup();
    const onVoiceStart = vi.fn();
    const onVoiceDone = vi.fn();
    const onVoiceCancel = vi.fn();
    const handlers = { onVoiceStart, onVoiceDone, onVoiceCancel };
    const { rerender } = render(<ReviewEditForm {...base} {...handlers} voice="idle" />);
    // 実行
    await user.click(screen.getByRole("button", { name: "音声で入力" }));
    // 検証
    expect(onVoiceStart).toHaveBeenCalledTimes(1);
    // 準備
    rerender(<ReviewEditForm {...base} {...handlers} voice="recording" elapsed={3} levels={[0.5]} />);
    // 検証
    expect(screen.queryByRole("button", { name: "修正" })).toBeNull();
    // 実行
    await user.click(screen.getByRole("button", { name: "文字起こし" }));
    await user.click(screen.getByRole("button", { name: "キャンセル" }));
    // 検証
    expect(onVoiceDone).toHaveBeenCalledTimes(1);
    expect(onVoiceCancel).toHaveBeenCalledTimes(1);
    // 準備
    rerender(<ReviewEditForm {...base} {...handlers} body="確認: 案 A にする" voice="idle" voiceStatus="inserted" />);
    // 検証
    expect(screen.getByText("文字起こしの結果を挿入しました。")).toBeInTheDocument();
    // 準備
    rerender(<ReviewEditForm {...base} />);
    // 検証
    expect(screen.queryByRole("button", { name: "音声で入力" })).toBeNull();
    expect(screen.getByRole("button", { name: "修正" })).toBeInTheDocument();
  });
});
