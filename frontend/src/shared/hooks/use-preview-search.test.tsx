import { act, waitFor } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { renderPreviewHook } from "@/testing/render";

describe("usePreviewSearch", () => {
  // 項目の移動は積む（正常系）
  test("use_preview_search_when_open_item", async () => {
    // 準備
    const { result, history } = await renderPreviewHook("/?tab=decisions", usePreviewSearch);
    const before = history.length;
    // 実行
    act(() => result.current.openItem("D-1"));
    // 検証
    await waitFor(() => expect(result.current.search.id).toBe("D-1"));
    expect(history.length).toBe(before + 1);
  });

  // 絞り込みは置き換える（正常系）
  test("use_preview_search_when_set_filters", async () => {
    // 準備
    const { result, history } = await renderPreviewHook("/?tab=decisions", usePreviewSearch);
    const before = history.length;
    // 実行
    act(() => result.current.setFilters({ status: "保留" }));
    // 検証
    await waitFor(() => expect(result.current.search.f).toEqual({ status: "保留" }));
    expect(history.length).toBe(before);
  });

  // 画面の移動（正常系）
  test("use_preview_search_when_change_tab", async () => {
    // 準備
    const { result } = await renderPreviewHook("/?tab=decisions&view=table&id=D-1&diff=V-1&sort=id&f.status=%E4%BF%9D%E7%95%99", usePreviewSearch);
    // 実行
    act(() => result.current.setTab("tasks"));
    // 検証
    await waitFor(() => expect(result.current.search.tab).toBe("tasks"));
    expect(result.current.search).toMatchObject({ id: "D-1", diff: "V-1", f: {} });
    expect(result.current.search.view).toBeUndefined();
    expect(result.current.search.sort).toBeUndefined();
  });
});
