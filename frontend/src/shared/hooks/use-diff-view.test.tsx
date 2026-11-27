import { waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, test } from "vitest";

import { useDiffView } from "@/shared/hooks/use-diff-view";
import { prune } from "@/shared/stores/read-changes-store";
import { RECORDS } from "@/testing/msw/handlers";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

const withChanges = () =>
  server.use(
    http.get("/api/records", () =>
      HttpResponse.json({
        ...RECORDS,
        changes: {
          last_seq: 2,
          sets: [
            { id: "V-2", at: "2026-11-02T00:00:00+00:00", summary: "2 回目", until_seq: 2, added: ["D-3"], changed: [] },
            { id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: ["D-1"], changed: [] },
          ],
          pending: { added: [], changed: [] },
        },
      }),
    ),
  );

// 既読のまとまりを持つ端末の保存領域のキー
const READ_CHANGES_KEY = "mindmap-read-changes";

/** 保存領域のどれかのワークスペースの既読にある、まとまりの ID を返す */
const storedReadIds = (): string[] => {
  const raw = localStorage.getItem(READ_CHANGES_KEY);
  return raw === null ? [] : Object.values((JSON.parse(raw) as { state: { read: Record<string, string[]> } }).state.read).flat();
};

beforeEach(() => {
  // 前のテストの既読（保存領域とメモリの上）と、そのタブで選んだ時点を持ち越さない
  prune("", []);
  localStorage.removeItem(READ_CHANGES_KEY);
  sessionStorage.clear();
});

describe("useDiffView", () => {
  // URL の時点で解決する（正常系）
  test("use_diff_view", async () => {
    // 準備
    withChanges();
    // 実行
    const { result } = await renderPreviewHook("/?tab=decisions&diff=V-2", useDiffView);
    // 検証
    await waitFor(() => expect(result.current.point?.sel).toBe("V-2"));
  });

  // そのタブの時点を URL に書く（正常系）
  test("use_diff_view_when_saved", async () => {
    // 準備
    withChanges();
    sessionStorage.setItem("mindmap-filters", JSON.stringify({ diffSel: "V-1" }));
    // 実行
    const { router } = await renderPreviewHook("/?tab=decisions", useDiffView);
    // 検証
    await waitFor(() => expect(router.state.location.search).toMatchObject({ diff: "V-1" }));
  });

  // 開いたまとまりを既読にし、まだまとめていない変更は既読にしない（正常系）
  test.each([
    { diff: "V-2", expected: ["V-2"] },
    { diff: "pending", expected: [] },
  ])("use_diff_view_when_marked_read", async ({ diff, expected }) => {
    // 準備
    withChanges();
    // 実行
    await renderPreviewHook(`/?tab=decisions&diff=${diff}`, useDiffView);
    // 検証
    await waitFor(() => expect(storedReadIds()).toEqual(expected));
  });

  // まとまりの ID でない時点は差分を出さず URL から除外する（正常系）
  test("use_diff_view_when_not_set_id", async () => {
    // 準備
    withChanges();
    // 実行
    const { result, router } = await renderPreviewHook("/?tab=decisions&diff=since", useDiffView);
    // 検証
    await waitFor(() => expect(router.state.location.search).not.toHaveProperty("diff"));
    expect(result.current.point).toBeNull();
  });
});
