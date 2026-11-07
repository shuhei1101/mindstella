import { describe, expect, test } from "vitest";

import { displayDefaults, kindsText, lookLabel, overrideNames, resetPrefs } from "@/shared/core/display";
import { KIND_KEYS } from "@/shared/core/records";

describe("lookLabel", () => {
  // 名前を返す（正常系）
  test("look_label", () => {
    expect(lookLabel("deep")).toBe("深宇宙");
  });
});

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
    const prefs = { kinds: ["decisions" as const], minimap: false as const, reviewOrder: "oldest" as const };
    // 実行と検証
    expect(overrideNames({ prefs, theme: null })).toEqual(["表示する種類", "差分のミニマップ", "コメントの並び"]);
  });
});

describe("resetPrefs", () => {
  // 残す項目（正常系）
  test("reset_prefs", () => {
    // 準備
    const prefs = { look: "dust", theme: "dark", kinds: ["decisions"], diffSel: "V-1", commentsPinned: true, unknownKey: 1 };
    // 実行
    const result = resetPrefs(prefs);
    // 検証
    expect(result["diffSel"]).toBe("V-1");
    expect(result["commentsPinned"]).toBe(true);
    expect(result["unknownKey"]).toBe(1);
    expect(result["look"] ?? null).toBeNull();
    expect(result["theme"] ?? null).toBeNull();
    expect(result["kinds"] ?? null).toBeNull();
  });
});

describe("displayDefaults", () => {
  // 既定が無い（正常系）
  test("display_defaults_when_missing", () => {
    expect(displayDefaults(undefined)).toEqual({ look: "deep", kinds: [...KIND_KEYS] });
  });
});
