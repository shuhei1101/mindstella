import { afterEach, describe, expect, test } from "vitest";

import { resetEmbeddedDataForTest } from "@/shared/core/embedded";
import { dropLegacyScreenState, readListScroll, readScreenState, writeListScroll, writeScreenState } from "@/shared/stores/screen-state-store";
import { PREFS_KEY } from "@/shared/stores/theme-store";

afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  document.body.replaceChildren();
  resetEmbeddedDataForTest();
  history.replaceState(null, "", "/");
});

describe("readScreenState", () => {
  // 読めない JSON（異常系）
  test("read_screen_state_when_invalid", () => {
    // 準備
    sessionStorage.setItem("mindmap-filters", "{broken");
    // 実行・検証
    expect(readScreenState()).toEqual({});
    // 準備
    sessionStorage.setItem("mindmap-filters", JSON.stringify({ tagMatch: { tasks: "both" } }));
    // 実行・検証
    expect(readScreenState().tagMatch?.["tasks"]).toBeUndefined();
  });
});

describe("writeScreenState", () => {
  // そのタブの保存領域に書き、端末の保存領域に書かない（正常系）
  test("write_screen_state", () => {
    // 準備
    history.replaceState(null, "", "/w/mindstella-x-1/");
    // 実行
    writeScreenState({ filters: { tasks: { tags: ["画面"] } } });
    // 検証
    expect(JSON.parse(sessionStorage.getItem("mindmap-filters:mindstella-x-1") ?? "{}")).toEqual({ filters: { tasks: { tags: ["画面"] } } });
    expect(localStorage.length).toBe(0);
  });

  // 配る書き出しでは保存領域に書かない（正常系）
  test("write_screen_state_when_embedded", () => {
    // 準備
    const data = document.createElement("script");
    data.type = "application/json";
    data.id = "mindmap-data";
    data.textContent = '{"settings":{}}';
    document.body.append(data);
    // 実行
    writeScreenState({ filters: { tasks: { tags: ["画面"] } } });
    // 検証
    expect(sessionStorage.length).toBe(0);
    expect(readScreenState().filters).toEqual({ tasks: { tags: ["画面"] } });
  });
});

describe("dropLegacyScreenState", () => {
  // 残った条件だけを削除する（正常系）
  test("drop_legacy_screen_state", () => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify({ filters: { tasks: { status: ["保留"] } }, diffSel: "V-1", theme: "dark", columns: { tasks: { hidden: [], pinTo: null } } }));
    // 実行
    dropLegacyScreenState();
    // 検証
    expect(JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}")).toEqual({ theme: "dark", columns: { tasks: { hidden: [], pinTo: null } } });
    expect(sessionStorage.length).toBe(0);
  });
});

describe("readListScroll", () => {
  // 壊れた値は読まない（異常系）
  test("read_list_scroll_when_broken", () => {
    // 準備
    sessionStorage.setItem("mindmap-list-scroll", JSON.stringify({ "tasks:board": { top: -1, left: 0 }, "decisions:table": { top: "a", left: 0 } }));
    // 実行・検証
    expect(readListScroll("tasks:board")).toBeNull();
    expect(readListScroll("decisions:table")).toBeNull();
    // 準備
    sessionStorage.setItem("mindmap-list-scroll", "{broken");
    // 実行・検証
    expect(readListScroll("tasks:board")).toBeNull();
  });
});

describe("writeListScroll", () => {
  // キーごとに残す（正常系）
  test("write_list_scroll", () => {
    // 実行
    writeListScroll("tasks:board", { top: 400, left: 20 });
    writeListScroll("decisions:table", { top: 120, left: 0 });
    // 検証
    expect(readListScroll("tasks:board")).toEqual({ top: 400, left: 20 });
    expect(readListScroll("decisions:table")).toEqual({ top: 120, left: 0 });
  });
});
