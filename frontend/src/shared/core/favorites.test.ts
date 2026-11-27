import { describe, expect, test } from "vitest";

import { favoritesFirst, favoritesOnly, toggleFavorite } from "@/shared/core/favorites";

const items = (...ids: string[]) => ids.map((id) => ({ id }));

describe("favoritesFirst", () => {
  // お気に入りを先頭に並べ、それぞれの中の順を保つ（正常系）
  test("favorites_first", () => {
    // 実行
    const result = favoritesFirst(items("D-1", "D-2", "D-3", "D-4"), new Set(["D-3", "D-1", "D-9"]));
    // 検証
    expect(result.map((item) => item.id)).toEqual(["D-1", "D-3", "D-2", "D-4"]);
  });
});

describe("favoritesOnly", () => {
  // お気に入りだけを残す（正常系）
  test.each([
    { favorites: new Set(["D-3", "D-1"]), expected: ["D-1", "D-3"] },
    { favorites: new Set<string>(), expected: [] },
  ])("favorites_only $expected", ({ favorites, expected }) => {
    // 実行
    const result = favoritesOnly(items("D-1", "D-2", "D-3"), favorites);
    // 検証
    expect(result.map((item) => item.id)).toEqual(expected);
  });
});

describe("toggleFavorite", () => {
  // 登録と解除（正常系）
  test.each([
    { favorites: ["D-1"], id: "D-2", expected: ["D-1", "D-2"] },
    { favorites: ["D-1", "D-2"], id: "D-1", expected: ["D-2"] },
  ])("toggle_favorite $id", ({ favorites, id, expected }) => {
    // 準備
    const before = [...favorites];
    // 実行
    const result = toggleFavorite(favorites, id);
    // 検証
    expect(result).toEqual(expected);
    expect(favorites).toEqual(before);
  });
});
