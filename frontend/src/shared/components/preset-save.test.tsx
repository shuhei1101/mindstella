import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { PresetSave } from "@/shared/components/preset-save";

describe("PresetSave", () => {
  // 名前を入れて保存する（正常系）
  test("preset_save", async () => {
    // 準備
    const onSave = vi.fn(() => Promise.resolve({ error: null }));
    render(<PresetSave hasTagCondition hasOtherConditions={false} onSave={onSave} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "プリセットとして保存" }));
    await userEvent.type(screen.getByLabelText("プリセットの名前"), " 廃止する画面 ");
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    // 検証
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith("廃止する画面");
    expect(await screen.findByRole("button", { name: "プリセットとして保存" })).toBeInTheDocument();
    expect(screen.queryByLabelText("プリセットの名前")).not.toBeInTheDocument();
  });

  // タグの条件が無いと開かない（正常系）
  test("preset_save_when_no_tag_condition", async () => {
    // 準備
    render(<PresetSave hasTagCondition={false} hasOtherConditions={false} onSave={vi.fn()} />);
    const button = screen.getByRole("button", { name: "プリセットとして保存" });
    // 実行
    await userEvent.click(button);
    // 検証
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveAccessibleDescription("タグの条件を選ぶと、プリセットとして保存できます。");
    expect(screen.queryByLabelText("プリセットの名前")).not.toBeInTheDocument();
  });

  // 空の名前は送信しない（異常系）
  test("preset_save_when_empty_name", async () => {
    // 準備
    const onSave = vi.fn();
    render(<PresetSave hasTagCondition hasOtherConditions={false} onSave={onSave} defaultOpen />);
    // 実行
    await userEvent.type(screen.getByLabelText("プリセットの名前"), "   ");
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    // 検証
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText("プリセットの名前を入れてください。")).toBeInTheDocument();
    expect(screen.getByLabelText("プリセットの名前")).toHaveAttribute("aria-invalid", "true");
  });

  // 保存できなかった理由を出す（異常系）
  test("preset_save_when_error", async () => {
    // 準備
    const message = "同じ名前のプリセット「画面の設計」が既にあります。別の名前を入れてください。";
    const onSave = vi.fn(() => Promise.resolve({ error: message }));
    render(<PresetSave hasTagCondition hasOtherConditions={false} onSave={onSave} defaultOpen defaultName="画面の設計" />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    // 検証
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByLabelText("プリセットの名前")).toHaveValue("画面の設計");
  });

  // 保存中はもう一度送信しない（正常系）
  test("preset_save_when_saving", async () => {
    // 準備
    const onSave = vi.fn(() => new Promise<{ error: string | null }>(() => undefined));
    render(<PresetSave hasTagCondition hasOtherConditions={false} onSave={onSave} defaultOpen defaultName="画面の設計" />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    await userEvent.click(screen.getByRole("button", { name: "保存中…" }));
    // 検証
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "保存中…" })).toHaveAttribute("aria-disabled", "true");
  });
});
