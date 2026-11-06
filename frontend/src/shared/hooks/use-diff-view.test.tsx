import { waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { OPENED_SESSION_KEY, useDiffView } from "@/shared/hooks/use-diff-view";
import { PREFS_KEY } from "@/shared/stores/theme-store";
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

  // 端末の時点を URL に書く（正常系）
  test("use_diff_view_when_saved", async () => {
    // 準備
    withChanges();
    localStorage.setItem(PREFS_KEY, JSON.stringify({ diffSel: "V-1" }));
    // 実行
    const { router } = await renderPreviewHook("/?tab=decisions", useDiffView);
    // 検証
    await waitFor(() => expect(router.state.location.search).toMatchObject({ diff: "V-1" }));
  });

  // 同じタブで呼び直さない（正常系）
  test("use_diff_view_when_opened_stored", async () => {
    // 準備
    sessionStorage.setItem(OPENED_SESSION_KEY, JSON.stringify({ at: "2026-11-01T00:00:00+00:00", seq: 1 }));
    const opened = vi.fn(() => HttpResponse.json({ previous: null, opened: { at: "2026-11-01T00:00:00+00:00", seq: 1 } }));
    server.use(http.post("/api/opened", opened));
    // 実行
    const { result } = await renderPreviewHook("/?tab=decisions", useDiffView);
    await waitFor(() => expect(result.current.since).not.toBeNull());
    // 検証
    expect(opened).not.toHaveBeenCalled();
    sessionStorage.clear();
  });
});
