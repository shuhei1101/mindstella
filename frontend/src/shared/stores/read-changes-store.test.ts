import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

// 既読のまとまりを持つ端末の保存領域のキー
const READ_CHANGES_KEY = "mindmap-read-changes";

/** 保存領域の既読のまとまりを参照する（無ければ空） */
const storedRead = (): Record<string, string[]> => {
  const raw = localStorage.getItem(READ_CHANGES_KEY);
  return raw === null ? {} : (JSON.parse(raw) as { state: { read: Record<string, string[]> } }).state.read;
};

/** 保存領域を空にした状態で store のモジュールを読み込み直す（テストごとに既読を持ち越さない） */
const loadStore = async () => {
  vi.resetModules();
  return import("@/shared/stores/read-changes-store");
};

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("markRead", () => {
  // 既読に加え、重なりを持たず、ほかのワークスペースは変えない（正常系）
  test("mark_read", async () => {
    // 準備
    const { markRead } = await loadStore();
    // 実行
    markRead("a", ["V-1"]);
    markRead("a", ["V-1", "V-2"]);
    markRead("b", ["V-1"]);
    // 検証
    expect(storedRead()).toEqual({ a: ["V-1", "V-2"], b: ["V-1"] });
  });
});

describe("prune", () => {
  // 記録に無い ID だけを削除する（正常系）
  test("prune", async () => {
    // 準備
    const { markRead, prune } = await loadStore();
    markRead("a", ["V-1", "V-2"]);
    // 実行
    prune("a", ["V-2", "V-3"]);
    // 検証
    expect(storedRead().a).toEqual(["V-2"]);
  });
});

describe("useUnreadSetIds", () => {
  // 既読に無いまとまりだけを返却する（正常系）
  test("use_unread_set_ids", async () => {
    // 準備
    const { markRead, useUnreadSetIds } = await loadStore();
    markRead("a", ["V-1"]);
    // 実行
    const { result } = renderHook(() => useUnreadSetIds("a", ["V-3", "V-2", "V-1"]));
    // 検証
    expect(result.current).toEqual(["V-3", "V-2"]);
  });

  // ほかのタブが既読を書き換えたら読み直し、相手の既読を上書きしない（正常系）
  test("use_unread_set_ids_when_other_tab_writes", async () => {
    // 準備
    const { markRead, useUnreadSetIds } = await loadStore();
    const { result } = renderHook(() => useUnreadSetIds("a", ["V-3", "V-2", "V-1"]));
    const value = JSON.stringify({ state: { read: { a: ["V-3"] } }, version: 0 });
    localStorage.setItem(READ_CHANGES_KEY, value);
    // 実行
    await act(async () => {
      window.dispatchEvent(new StorageEvent("storage", { key: READ_CHANGES_KEY, newValue: value }));
      await Promise.resolve();
    });
    markRead("a", ["V-2"]);
    // 検証
    await waitFor(() => expect(result.current).toEqual(["V-1"]));
    expect(storedRead().a).toEqual(["V-3", "V-2"]);
  });

  // 保存領域を使用できなくてもタブの中で既読を持つ（異常系）
  test("use_unread_set_ids_when_storage_unavailable", async () => {
    // 準備
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("保存領域を使用できません", "QuotaExceededError");
    });
    const { markRead, useUnreadSetIds } = await loadStore();
    // 実行
    markRead("a", ["V-1"]);
    const { result } = renderHook(() => useUnreadSetIds("a", ["V-1"]));
    // 検証
    expect(result.current).toEqual([]);
  });
});
