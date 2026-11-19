import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SettingsPanel } from "@/features/settings/display-settings/components/settings-panel";
import { KIND_KEYS } from "@/shared/core/records";

const base = {
  look: "deep" as const,
  defaultLook: "deep" as const,
  visibleKinds: [...KIND_KEYS],
  defaultKinds: [...KIND_KEYS],
  counts: {},
  overrides: [],
  canSave: true,
  message: null,
  storageAvailable: true,
  minimap: true,
  bodyView: { fold: true },
  onKindsChange: vi.fn(),
  onReset: vi.fn(),
  onSaveDefault: vi.fn(),
  onClose: vi.fn(),
  onMinimapChange: vi.fn(),
  onBodyViewChange: vi.fn(),
  focusAfterAdd: "auto" as const,
  pointerCoarse: false,
  onFocusAfterAddChange: vi.fn(),
};

describe("SettingsPanel", () => {
  // 種類を外す（正常系）
  test("settings_panel", async () => {
    // 準備
    const onKindsChange = vi.fn();
    render(<SettingsPanel {...base} onKindsChange={onKindsChange} />);
    // 実行
    await userEvent.click(screen.getByRole("checkbox", { name: /メモ/ }));
    // 検証
    expect(onKindsChange).toHaveBeenCalledWith(KIND_KEYS.filter((kind) => kind !== "notes"));
  });

  // 既定と同じ（正常系）
  test("settings_panel_when_same_as_default", () => {
    // 準備と実行
    render(<SettingsPanel {...base} />);
    // 検証
    expect(screen.queryByRole("button", { name: "ワークスペースの既定にする" })).not.toBeInTheDocument();
    expect(screen.getByText("見た目と表示する種類は、ワークスペースの既定と同じです。")).toBeInTheDocument();
  });

  // 「レビューに追加した後のフォーカス」のラジオ（正常系）
  test.each([
    { pointerCoarse: false, sub: "この端末では入力欄へ戻します" },
    { pointerCoarse: true, sub: "この端末では戻しません" },
  ])("settings_panel_when_focus_after_add (pointerCoarse: $pointerCoarse)", async ({ pointerCoarse, sub }) => {
    // 準備
    const onFocusAfterAddChange = vi.fn();
    render(<SettingsPanel {...base} focusAfterAdd="auto" pointerCoarse={pointerCoarse} onFocusAfterAddChange={onFocusAfterAddChange} />);
    const section = screen.getByRole("group", { name: "コメントの入力" });
    const group = within(section).getByRole("group", { name: "レビューに追加した後のフォーカス" });
    const radios = within(group).getAllByRole("radio");
    // 実行
    await userEvent.click(within(group).getByRole("radio", { name: /戻さない/ }));
    // 検証
    expect(radios).toHaveLength(3);
    expect(radios[0]).toHaveAccessibleName(new RegExp(`^自動.*${sub}`));
    expect(radios[1]).toHaveAccessibleName("入力欄へ戻す");
    expect(radios[2]).toHaveAccessibleName("戻さない");
    expect(radios[0]).toBeChecked();
    expect(group).toHaveAccessibleDescription("自動は、マウスで操作する端末では入力欄へ戻し、タッチで操作する端末では戻しません。");
    expect(onFocusAfterAddChange).toHaveBeenCalledWith("none");
  });
});
