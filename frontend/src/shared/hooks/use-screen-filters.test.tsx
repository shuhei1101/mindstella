import { act, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import type { PresetFilter } from "@/shared/core/presets";
import { useScreenFilters } from "@/shared/hooks/use-screen-filters";
import { readScreenState } from "@/shared/stores/screen-state-store";
import { renderPreviewHook } from "@/testing/render";

const INCLUDE_EXCLUDE = { and: [{ field: "tags", op: "eq", values: ["画面"] }, { field: "tags", op: "ne", values: ["廃止"] }] } satisfies PresetFilter;

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

  // 保存した条件と「どれかを含む」を URL に書く（正常系）
  test("use_screen_filters_when_saved_tag_match", async () => {
    // 準備
    sessionStorage.setItem("mindmap-filters", JSON.stringify({ filters: { tasks: { tags: ["画面", "保存"] } }, tagMatch: { tasks: "any" } }));
    // 実行
    const { result, router } = await renderPreviewHook("/?tab=tasks", () => useScreenFilters("tasks"));
    // 検証
    await waitFor(() => expect(router.state.location.search).toMatchObject({ f: { tags: "画面|保存" }, tagmatch: "any" }));
    expect(result.current.tagMatch).toBe("any");
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

  // 同じ画面で戻ると、保存した条件を戻さず外す（正常系）
  test("use_screen_filters_when_back", async () => {
    // 準備
    const { result, router } = await renderPreviewHook("/?tab=tasks", () => useScreenFilters("tasks"));
    act(() => {
      result.current.addTag("画面");
    });
    await waitFor(() => expect(router.state.location.search).toMatchObject({ f: { tags: "画面" } }));
    // 実行
    act(() => {
      router.history.back();
    });
    // 検証
    await waitFor(() => expect(router.state.location.search).toEqual({ tab: "tasks" }));
    await waitFor(() => expect(readScreenState().filters?.["tasks"]).toBeUndefined());
    expect(result.current.filters).toEqual({});
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

  // 簡易で表せる式と表せない式を書き分ける（正常系）
  test("use_screen_filters_when_set_tag_expr", async () => {
    // 準備
    const { result, router } = await renderPreviewHook("/?tab=tasks", () => useScreenFilters("tasks"));
    const both: PresetFilter = { field: "tags", op: "eq", values: ["画面", "廃止"], match: "all" };
    // 実行
    act(() => {
      result.current.setTagExpr(both);
    });
    // 検証
    await waitFor(() => expect(router.state.location.search).toMatchObject({ f: { tags: "画面|廃止" } }));
    expect(router.state.location.search).not.toHaveProperty("tx");
    // 実行
    act(() => {
      result.current.setTagExpr(INCLUDE_EXCLUDE);
    });
    // 検証
    await waitFor(() => expect(router.state.location.search).toHaveProperty("tx"));
    expect(router.state.location.search.f ?? {}).toEqual({});
    expect(result.current.tagExpr).toEqual(INCLUDE_EXCLUDE);
  });

  // 式で絞っているときにタグを加える（正常系）
  test("use_screen_filters_when_add_tag_to_expr", async () => {
    // 準備
    const { result, router } = await renderPreviewHook(`/?tab=tasks&tx=${encodeURIComponent(JSON.stringify(INCLUDE_EXCLUDE))}`, () => useScreenFilters("tasks"));
    const before = router.history.length;
    // 実行
    act(() => {
      result.current.addTag("保存");
    });
    // 検証
    await waitFor(() => expect(result.current.tagExpr).toEqual({ and: [...INCLUDE_EXCLUDE.and, { field: "tags", op: "eq", values: ["保存"] }] }));
    expect(router.state.location.search.f ?? {}).toEqual({});
    expect(router.history.length).toBe(before + 1);
  });

  // 式に同じタグの「含む」があるときはタグを加えない（正常系）
  test("use_screen_filters_when_add_same_tag_to_expr", async () => {
    // 準備
    const tx = JSON.stringify(INCLUDE_EXCLUDE);
    const { result, router } = await renderPreviewHook(`/?tab=tasks&tx=${encodeURIComponent(tx)}`, () => useScreenFilters("tasks"));
    const before = router.history.length;
    // 実行
    act(() => {
      result.current.addTag("画面");
    });
    // 検証
    expect(router.state.location.search.tx).toBe(tx);
    expect(router.history.length).toBe(before);
  });
});

