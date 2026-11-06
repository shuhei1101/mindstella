import { waitFor } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { useScreenFilters } from "@/shared/hooks/use-screen-filters";
import { readPrefs } from "@/shared/stores/prefs-store";
import { PREFS_KEY } from "@/shared/stores/theme-store";
import { renderPreviewHook } from "@/testing/render";

describe("useScreenFilters", () => {
  // URL の条件で開いて保存を書き換える（正常系）
  test("use_screen_filters", async () => {
    // 実行
    const { result } = await renderPreviewHook("/?tab=decisions&f.status=%E4%BF%9D%E7%95%99", () => useScreenFilters("decisions"));
    // 検証
    expect(result.current.filters).toEqual({ status: ["保留"] });
    await waitFor(() => expect(readPrefs().filters?.["decisions"]).toEqual({ status: ["保留"] }));
  });

  // 保存した条件を URL に書く（正常系）
  test("use_screen_filters_when_saved", async () => {
    // 準備
    localStorage.setItem(PREFS_KEY, JSON.stringify({ filters: { tasks: { status: ["保留"] } } }));
    // 実行
    const { router } = await renderPreviewHook("/?tab=tasks", () => useScreenFilters("tasks"));
    // 検証
    await waitFor(() => expect(router.state.location.search).toMatchObject({ f: { status: "保留" } }));
  });

  // 既定の条件（正常系）
  test("use_screen_filters_when_default", async () => {
    // 実行
    const { result } = await renderPreviewHook("/?tab=decisions", () => useScreenFilters("decisions"));
    // 検証
    expect(result.current.filters).toEqual({ status: ["要見直し", "未決定", "未整理", "保留"] });
  });
});
