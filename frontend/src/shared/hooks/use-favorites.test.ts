import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { useFavorites } from "@/shared/hooks/use-favorites";
import { readPrefs } from "@/shared/stores/prefs-store";
import { PREFS_KEY } from "@/shared/stores/theme-store";

describe("useFavorites", () => {
  // 保存領域の値と既定（正常系）
  test.each([
    { stored: {}, ids: [], first: true, only: false },
    { stored: { favorites: ["D-1"], favoritesFirst: false, favoritesOnly: true }, ids: ["D-1"], first: false, only: true },
  ])("use_favorites $stored", ({ stored, ids, first, only }) => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify(stored));
    // 実行
    const { result } = renderHook(() => useFavorites());
    // 検証
    expect([...result.current.ids]).toEqual(ids);
    expect(result.current.first).toBe(first);
    expect(result.current.only).toBe(only);
  });

  // 登録・解除と絞り込みの解除を書き込む（正常系）
  test("use_favorites_when_toggle", () => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify({ minimap: false, favoritesOnly: true }));
    const { result } = renderHook(() => useFavorites());
    // 実行・検証
    act(() => { result.current.toggle("D-2"); });
    expect(readPrefs().favorites).toEqual(["D-2"]);
    act(() => { result.current.toggle("D-2"); });
    expect(readPrefs().favorites).toEqual([]);
    act(() => { result.current.clearOnly(); });
    expect(readPrefs().favoritesOnly).toBeNull();
    expect(readPrefs().minimap).toBe(false);
  });
});
