import { describe, expect, test } from "vitest";

import { readPrefs, writePrefs } from "@/shared/stores/prefs-store";
import { PREFS_KEY } from "@/shared/stores/theme-store";

describe("readPrefs", () => {
  // 読めない JSON（異常系）
  test("read_prefs_when_invalid", () => {
    // 準備
    localStorage.setItem(PREFS_KEY, "{壊れた");
    // 実行・検証
    expect(readPrefs()).toEqual({});
  });

  // 今の画面が書いた JSON を読める（正常系）
  test("read_prefs_when_legacy_written", () => {
    // 準備
    const legacy = {
      columns: { decisions: { hidden: ["phase"], pinTo: "title" } },
      filters: { decisions: { status: ["保留"] } },
      diffSel: "V-1",
      minimap: false,
      bodyLayout: "side",
      tablePin: false,
    };
    localStorage.setItem(PREFS_KEY, JSON.stringify(legacy));
    // 実行・検証
    expect(readPrefs()).toMatchObject(legacy);
  });
});

describe("writePrefs", () => {
  // 知らない項目を残す（正常系）
  test("write_prefs", () => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify({ theme: "dark", look: "glow", commentsPinned: true }));
    // 実行
    writePrefs({ diffSel: "V-1" });
    // 検証
    expect(JSON.parse(localStorage.getItem(PREFS_KEY) as string)).toEqual({ theme: "dark", look: "glow", commentsPinned: true, diffSel: "V-1" });
  });
});
