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

  // 画面の移動でタグの条件を外す（正常系）
  test("use_preview_search_when_change_tab_with_tag_condition", async () => {
    // 準備
    const { result } = await renderPreviewHook(`/?tab=decisions&tagmatch=any&tx=${encodeURIComponent('{"field":"tags","op":"ne","values":["廃止"]}')}`, usePreviewSearch);
    // 実行
    act(() => result.current.setTab("tasks"));
    // 検証
    await waitFor(() => expect(result.current.search.tab).toBe("tasks"));
    expect(result.current.search.tagmatch).toBeUndefined();
    expect(result.current.search.tx).toBeUndefined();
  });

  // タグの条件をまとめて置き換える（正常系）
  test("use_preview_search_when_set_tag_condition", async () => {
    // 準備
    const { result, router } = await renderPreviewHook("/?tab=tasks&f.tags=%E7%94%BB%E9%9D%A2", usePreviewSearch);
    const before = router.history.length;
    const tx = '{"field":"tags","op":"ne","values":["廃止"]}';
    // 実行
    act(() => result.current.setTagCondition({ f: { status: "未着手" }, tagmatch: undefined, tx }));
    // 検証
    await waitFor(() => expect(result.current.search.tx).toBe(tx));
    expect(result.current.search.f).toEqual({ status: "未着手" });
    expect(router.history.length).toBe(before);
  });
  // コメントの一覧の中の移動は置き換える（正常系）
  test("use_preview_search_when_set_comments", async () => {
    // 準備
    const { result, history } = await renderPreviewHook("/?panel=comments", usePreviewSearch);
    const before = history.length;
    // 実行
    act(() => result.current.setComments({ thread: "TH-1" }));
    // 検証
    await waitFor(() => expect(result.current.search.thread).toBe("TH-1"));
    expect(history.length).toBe(before);
  });

  // コメントの一覧を閉じる（正常系）
  test("use_preview_search_when_close_comments", async () => {
    // 準備
    const { result } = await renderPreviewHook("/?panel=comments&thread=TH-1&review=1&tstatus=all&ttag=%E7%94%BB%E9%9D%A2", usePreviewSearch);
    // 実行
    act(() => result.current.setPanel(undefined));
    // 検証
    await waitFor(() => expect(result.current.search.panel).toBeUndefined());
    expect(result.current.search).not.toHaveProperty("thread");
    expect(result.current.search.review).toBeUndefined();
    expect(result.current.search.tstatus).toBeUndefined();
    expect(result.current.search.ttag).toBeUndefined();
  });

  // 並べ替えは積み、初期設定に戻すときは置き換える（正常系）
  test("use_preview_search_when_set_sort", async () => {
    // 準備
    const { result, history } = await renderPreviewHook("/?tab=decisions&view=table", usePreviewSearch);
    const before = history.length;
    // 実行
    act(() => result.current.setSort("title"));
    // 検証
    await waitFor(() => expect(result.current.search.sort).toBe("title"));
    expect(history.length).toBe(before + 1);
    // 実行
    act(() => result.current.setSort(undefined, { replace: true }));
    // 検証
    await waitFor(() => expect(result.current.search.sort).toBeUndefined());
    expect(history.length).toBe(before + 1);
  });

  // ドロワーのタグの条件は 1 つ積む（正常系）
  test("use_preview_search_when_push_tag_condition", async () => {
    // 準備
    const { result, history } = await renderPreviewHook("/?tab=tasks", usePreviewSearch);
    const before = history.length;
    // 実行
    act(() => result.current.pushTagCondition({ f: { tags: "画面|保存" }, tagmatch: "any", tx: undefined }));
    await waitFor(() => expect(result.current.search.tagmatch).toBe("any"));
    act(() => result.current.pushTagMatch(undefined));
    // 検証
    await waitFor(() => expect(result.current.search.tagmatch).toBeUndefined());
    expect(result.current.search.f).toEqual({ tags: "画面|保存" });
    expect(history.length).toBe(before + 2);
  });

  // 一覧から開いたマーカーを持つ（正常系）
  test("use_preview_search_when_open_item_from_list", async () => {
    // 準備
    const { result, history } = await renderPreviewHook("/?tab=decisions", usePreviewSearch);
    // 実行
    act(() => result.current.openItem("D-2", { fromList: true }));
    await waitFor(() => expect(result.current.search.id).toBe("D-2"));
    // 検証
    expect(result.current.fromList).toBe(true);
    // 実行
    act(() => result.current.openItem("D-1"));
    await waitFor(() => expect(result.current.search.id).toBe("D-1"));
    // 検証
    expect(result.current.fromList).toBe(false);
    expect((history.location.state as { trail?: { items: string[] } }).trail?.items).toEqual(["D-2", "D-1"]);
  });

  // 詳細の戻るは並べ替えの履歴を飛ばす（正常系）
  test("use_preview_search_when_back_item_skips_sort", async () => {
    // 準備
    const { result } = await renderPreviewHook("/?tab=decisions&view=table", usePreviewSearch);
    act(() => result.current.openItem("D-2"));
    await waitFor(() => expect(result.current.search.id).toBe("D-2"));
    act(() => result.current.setSort("-updated"));
    await waitFor(() => expect(result.current.search.sort).toBe("-updated"));
    act(() => result.current.openItem("D-4"));
    await waitFor(() => expect(result.current.search.id).toBe("D-4"));
    // 実行
    act(() => result.current.backItem());
    // 検証
    await waitFor(() => expect(result.current.search.id).toBe("D-2"));
    expect(result.current.search.sort).toBe("-updated");
    expect(result.current.canBack).toBe(false);
  });

  // タブの切り替えは置き換える（正常系）
  test("use_preview_search_when_set_tab_replaces", async () => {
    // 準備
    const { result, history } = await renderPreviewHook("/?tab=decisions", usePreviewSearch);
    act(() => result.current.openItem("D-1"));
    await waitFor(() => expect(result.current.search.id).toBe("D-1"));
    const before = history.length;
    // 実行
    act(() => result.current.setTab("tasks"));
    // 検証
    await waitFor(() => expect(result.current.search.tab).toBe("tasks"));
    expect(history.length).toBe(before);
  });
});
