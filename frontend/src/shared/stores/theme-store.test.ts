import { afterEach, describe, expect, test } from "vitest";

import { PREFS_KEY, useThemeStore } from "@/shared/stores/theme-store";

describe("useThemeStore.setTheme", () => {
  // theme だけを残す（正常系）
  test("set_theme", () => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify({ theme: "light", columns: { decisions: ["id"] } }));
    // 実行
    useThemeStore.getState().setTheme("dark");
    // 検証
    expect(JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}")).toEqual({ theme: "dark", columns: { decisions: ["id"] } });
    expect(document.documentElement.dataset["theme"]).toBe("dark");
  });

  // ワークスペースごとのキーに残す（正常系）
  test("set_theme_when_workspace_path", () => {
    // 準備
    history.replaceState(null, "", "/w/mindstella-x-1/");
    localStorage.setItem(PREFS_KEY, JSON.stringify({ theme: "light" }));
    // 実行
    useThemeStore.getState().setTheme("dark");
    // 検証
    expect(JSON.parse(localStorage.getItem(`${PREFS_KEY}:mindstella-x-1`) ?? "{}")).toEqual({ theme: "dark" });
    expect(JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}")).toEqual({ theme: "light" });
  });

  afterEach(() => {
    history.replaceState(null, "", "/");
    localStorage.clear();
  });
});
