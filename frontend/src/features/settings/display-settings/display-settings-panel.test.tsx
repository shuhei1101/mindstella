import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test } from "vitest";

import { renderRoute } from "@/testing/render";

const PREFS_KEY = "mindmap-preview";
const stored = (): Record<string, unknown> => JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}") as Record<string, unknown>;

afterEach(() => {
  localStorage.clear();
});

describe("DisplaySettingsPanel", () => {
  // 種類を外す（正常系）
  test("display_settings_panel", async () => {
    // 準備
    renderRoute("/spa/?panel=display");
    // 実行
    await userEvent.click(await screen.findByRole("checkbox", { name: /メモ/ }));
    // 検証
    expect(stored()["kinds"]).not.toContain("notes");
  });

  // 既定に戻す（正常系）
  test("display_settings_panel_when_reset", async () => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify({ kinds: ["decisions"], theme: "dark", diffSel: "V-1" }));
    renderRoute("/spa/?panel=display");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "既定に戻す" }));
    // 検証
    expect(stored()["kinds"] ?? null).toBeNull();
    expect(stored()["theme"] ?? null).toBeNull();
    expect(stored()["diffSel"]).toBe("V-1");
  });
});
