import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SettingsConfirm } from "@/features/settings/display-settings/components/settings-confirm";
import { KIND_KEYS } from "@/shared/core/records";

const from = { look: "deep" as const, visibleKinds: [...KIND_KEYS] };
const to = { look: "dust" as const, visibleKinds: KIND_KEYS.filter((kind) => kind !== "notes") };

describe("SettingsConfirm", () => {
  // 保存する（正常系）
  test("settings_confirm", async () => {
    // 準備
    const onSave = vi.fn();
    render(<SettingsConfirm from={from} to={to} busy={false} error={null} onSave={onSave} onCancel={vi.fn()} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "保存する" }));
    // 検証
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  // 保存の途中（正常系）
  test("settings_confirm_when_busy", async () => {
    // 準備
    const onCancel = vi.fn();
    render(<SettingsConfirm from={from} to={to} busy error={null} onSave={vi.fn()} onCancel={onCancel} />);
    // 実行
    await userEvent.keyboard("{Escape}");
    // 検証
    expect(screen.getByRole("button", { name: /保存しています/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "取り消す" })).toBeDisabled();
    expect(onCancel).not.toHaveBeenCalled();
  });
});
