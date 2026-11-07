import { render, screen } from "@testing-library/react";
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
  bodyView: { pin: true, head: true, stripes: false, fold: true },
  onKindsChange: vi.fn(),
  onReset: vi.fn(),
  onSaveDefault: vi.fn(),
  onClose: vi.fn(),
  onMinimapChange: vi.fn(),
  onBodyViewChange: vi.fn(),
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
});
