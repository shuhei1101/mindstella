import { screen, within } from "@testing-library/react";
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
    renderRoute("/?panel=display");
    // 実行
    await userEvent.click(await screen.findByRole("checkbox", { name: /メモ/ }));
    // 検証
    expect(stored()["kinds"]).not.toContain("notes");
  });

  // 既定に戻す（正常系）
  test("display_settings_panel_when_reset", async () => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify({ kinds: ["decisions"], theme: "dark", commentsPinned: true }));
    renderRoute("/?panel=display");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: "既定に戻す" }));
    // 検証
    expect(stored()["kinds"] ?? null).toBeNull();
    expect(stored()["theme"] ?? null).toBeNull();
    expect(stored()["commentsPinned"]).toBe(true);
  });

  // 「レビューに追加」の後のフォーカスを変えて自動に戻す（正常系）
  test("display_settings_panel_when_focus_after_add", async () => {
    // 準備
    renderRoute("/?panel=display");
    const group = await screen.findByRole("group", { name: "レビューに追加した後のフォーカス" });
    // 実行
    await userEvent.click(within(group).getByRole("radio", { name: "入力欄へ戻す" }));
    // 検証
    expect(stored()["focusAfterAdd"]).toBe("input");
    expect((await screen.findByText("この端末で変えている項目")).parentElement).toHaveTextContent("レビューに追加した後のフォーカス");
    // 実行（自動に戻す）
    await userEvent.click(within(group).getByRole("radio", { name: /^自動/ }));
    // 検証
    expect(stored()["focusAfterAdd"] ?? null).toBeNull();
  });
});

describe("DisplaySettingsPanel favorites", () => {
  // チェックを切り替えると保存領域が上書きと null を行き来する（正常系）
  test("display_settings_panel_when_favorites", async () => {
    // 準備
    renderRoute("/?panel=display");
    const group = await screen.findByRole("group", { name: "お気に入り" });
    const first = within(group).getByRole("checkbox", { name: "お気に入りを一番上にする" });
    const only = within(group).getByRole("checkbox", { name: "お気に入りだけを表示する" });
    // 実行・検証
    await userEvent.click(first);
    expect(stored()["favoritesFirst"]).toBe(false);
    await userEvent.click(first);
    expect(stored()["favoritesFirst"] ?? null).toBeNull();
    await userEvent.click(only);
    expect(stored()["favoritesOnly"]).toBe(true);
    await userEvent.click(only);
    expect(stored()["favoritesOnly"] ?? null).toBeNull();
  });
});
