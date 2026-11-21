import { act, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { useScreenFilters } from "@/shared/hooks/use-screen-filters";
import { readScreenState } from "@/shared/stores/screen-state-store";
import { renderPreviewHook } from "@/testing/render";

afterEach(() => {
  sessionStorage.clear();
});

describe("useScreenFilters", () => {
  // URL の条件で開いて保存を書き換える（正常系）
  test("use_screen_filters", async () => {
    // 実行
    const { result } = await renderPreviewHook("/?tab=decisions&f.status=%E4%BF%9D%E7%95%99", () => useScreenFilters("decisions"));
    // 検証
    expect(result.current.filters).toEqual({ status: ["保留"] });
    await waitFor(() => expect(readScreenState().filters?.["decisions"]).toEqual({ status: ["保留"] }));
  });

  // 保存した条件を URL に書く（正常系）
  test("use_screen_filters_when_saved", async () => {
    // 準備
    sessionStorage.setItem("mindmap-filters", JSON.stringify({ filters: { tasks: { status: ["保留"] } } }));
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

  // タグの組み合わせ方を URL と保存領域に書く（正常系）
  test("use_screen_filters_when_tag_match", async () => {
    // 準備
    const { result, router } = await renderPreviewHook("/?tab=tasks&f.tags=%E7%94%BB%E9%9D%A2", () => useScreenFilters("tasks"));
    // 実行
    act(() => {
      result.current.setTagMatch("any");
    });
    // 検証
    await waitFor(() => expect(router.state.location.search).toMatchObject({ tagmatch: "any" }));
    expect(readScreenState().tagMatch?.["tasks"]).toBe("any");
    // 実行
    act(() => {
      result.current.setTagMatch("all");
    });
    // 検証
    await waitFor(() => expect(router.state.location.search).not.toHaveProperty("tagmatch"));
    expect(readScreenState().tagMatch?.["tasks"]).toBe("all");
  });

  // タグを加えて履歴に 1 つ積む（正常系）
  test("use_screen_filters_when_add_tag", async () => {
    // 準備
    const { result, router } = await renderPreviewHook("/?tab=tasks&f.tags=%E4%BF%9D%E5%AD%98", () => useScreenFilters("tasks"));
    const before = router.history.length;
    // 実行
    act(() => {
      result.current.addTag("画面");
    });
    await waitFor(() => expect(router.state.location.search).toMatchObject({ f: { tags: "保存|画面" } }));
    act(() => {
      result.current.addTag("画面");
    });
    // 検証
    expect(router.state.location.search).toMatchObject({ f: { tags: "保存|画面" } });
    expect(router.history.length).toBe(before + 1);
  });

  // 概要から加えるとその種類の画面へ移る（正常系）
  test("use_screen_filters_when_overview", async () => {
    // 準備
    const { result, router } = await renderPreviewHook("/?tab=overview", () => useScreenFilters("overview"));
    const before = router.history.length;
    // 実行
    act(() => {
      result.current.addTag("画面", "tasks");
    });
    // 検証
    await waitFor(() => expect(router.state.location.search).toMatchObject({ tab: "tasks", f: { tags: "画面" } }));
    expect(router.history.length).toBe(before + 1);
  });
});
