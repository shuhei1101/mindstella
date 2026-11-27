import { describe, expect, test } from "vitest";

import { displayDefaults, focusAfterAddTarget, kindsText, overrideNames, resetPrefs } from "@/shared/core/display";
import { KIND_KEYS } from "@/shared/core/records";

describe("kindsText", () => {
  // 外した種類（正常系）
  test("kinds_text", () => {
    // 準備
    const kinds = new Set(KIND_KEYS.filter((kind) => kind !== "notes" && kind !== "logs"));
    // 実行と検証
    expect(kindsText(kinds)).toBe("メモ・会話ログを表示しない");
  });
});

describe("overrideNames", () => {
  // 変えている項目（正常系）
  test("override_names", () => {
    // 準備
    const prefs = {
      kinds: ["decisions" as const],
      minimap: false as const,
      reviewOrder: "oldest" as const,
      focusAfterAdd: "none" as const,
    };
    // 実行と検証
    expect(overrideNames({ prefs, theme: null })).toEqual([
      "表示する種類",
      "差分のミニマップ",
      "コメントの並び",
      "レビューに追加した後のフォーカス",
    ]);
  });
});

describe("resetPrefs", () => {
  // 残す項目（正常系）
  test("reset_prefs", () => {
    // 準備
    const prefs = {
      theme: "dark",
      kinds: ["decisions"],
      focusAfterAdd: "none",
      diffSel: "V-1",
      commentsPinned: true,
      unknownKey: 1,
    };
    // 実行
    const result = resetPrefs(prefs);
    // 検証
    expect(result["diffSel"]).toBe("V-1");
    expect(result["commentsPinned"]).toBe(true);
    expect(result["unknownKey"]).toBe(1);
    expect(result["theme"] ?? null).toBeNull();
    expect(result["kinds"] ?? null).toBeNull();
    expect(result["focusAfterAdd"] ?? null).toBeNull();
  });
});

describe("displayDefaults", () => {
  // 既定が無い（正常系）
  test("display_defaults_when_missing", () => {
    expect(displayDefaults(undefined)).toEqual({ kinds: [...KIND_KEYS] });
  });
});

describe("focusAfterAddTarget", () => {
  // 上書きと端末の種類で移動先を決める（正常系）
  test.each([
    { name: "auto_fine", prefs: {}, coarse: false, expected: "input" },
    { name: "auto_coarse", prefs: {}, coarse: true, expected: "submit" },
    { name: "input_coarse", prefs: { focusAfterAdd: "input" as const }, coarse: true, expected: "input" },
    { name: "none_fine", prefs: { focusAfterAdd: "none" as const }, coarse: false, expected: "submit" },
  ])("focus_after_add_target ($name)", ({ prefs, coarse, expected }) => {
    expect(focusAfterAddTarget(prefs, coarse)).toBe(expected);
  });
});

describe("overrideNames favorites", () => {
  // お気に入りの 2 つの上書き（正常系）
  test.each([
    { prefs: { favoritesFirst: false as const, favoritesOnly: true as const }, expected: ["お気に入りを一番上にする", "お気に入りだけを表示する"] },
    { prefs: { favorites: ["D-1"] }, expected: [] },
  ])("override_names_when_favorites $expected", ({ prefs, expected }) => {
    // 実行と検証
    expect(overrideNames({ prefs, theme: null })).toEqual(expected);
  });
});

describe("resetPrefs favorites", () => {
  // お気に入りの登録を残し、2 つの上書きを外す（正常系）
  test("reset_prefs_when_favorites", () => {
    // 実行
    const result = resetPrefs({ favorites: ["D-1"], favoritesFirst: false, favoritesOnly: true });
    // 検証
    expect(result["favorites"]).toEqual(["D-1"]);
    expect(result["favoritesFirst"] ?? null).toBeNull();
    expect(result["favoritesOnly"] ?? null).toBeNull();
  });
});
