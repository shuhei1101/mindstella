import { act, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { useMarkThreadSeen, useSetThreadStatus } from "@/features/comments/shared/use-threads";
import { AppError } from "@/shared/core/app-error";
import { threadsQuery } from "@/shared/hooks/preview-queries";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

const queryKeys = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.map(([filters]) => (filters as { queryKey?: unknown } | undefined)?.queryKey);

const unseenThreads = {
  threads: [{ id: "TH-1", status: "open", summary: "", tags: [], target: null, loc: null, events: [], posts: [{ id: "TH-1-1", author: "ai", body: "質問", created: "2026-11-01T00:00:00+00:00", seen: false }] }],
};

describe("useSetThreadStatus", () => {
  // 読み直す（正常系）
  test("use_set_thread_status", async () => {
    // 準備
    server.use(http.patch("/api/threads/:id", () => HttpResponse.json({ id: "TH-1", status: "closed", changed: true })));
    const { result, queryClient } = await renderPreviewHook("/", useSetThreadStatus);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    await act(() => result.current.mutateAsync({ id: "TH-1", status: "closed", reason: "決まった" }));
    // 検証
    expect(queryKeys(invalidate)).toContainEqual(["/api/threads"]);
  });

  // エラーの detail（異常系）
  test("use_set_thread_status_when_error", async () => {
    // 準備
    server.use(
      http.patch("/api/threads/:id", () =>
        HttpResponse.json({ type: "about:blank", title: "Conflict", status: 409, detail: "スレッドが見つかりません" }, { status: 409, headers: { "Content-Type": "application/problem+json" } }),
      ),
    );
    const { result } = await renderPreviewHook("/", useSetThreadStatus);
    // 実行
    const error = await result.current.mutateAsync({ id: "TH-1", status: "closed", reason: null }).catch((reason: unknown) => reason);
    // 検証
    expect(error).toBeInstanceOf(AppError);
    expect((error as AppError).message).toBe("スレッドが見つかりません");
  });
});

describe("useMarkThreadSeen", () => {
  // 印をすぐ消す（正常系）
  test("use_mark_thread_seen", async () => {
    // 準備
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseenThreads)),
      http.post("/api/threads/:id/seen", async () => {
        await delay("infinite");
        return HttpResponse.json({ id: "TH-1", seen: ["TH-1-1"] });
      }),
    );
    const { result, queryClient } = await renderPreviewHook("/", useMarkThreadSeen);
    await queryClient.fetchQuery(threadsQuery());
    // 実行
    act(() => {
      result.current.mutate("TH-1");
    });
    // 検証
    await waitFor(() => {
      const data = queryClient.getQueryData(threadsQuery().queryKey) as { data: typeof unseenThreads } | undefined;
      expect(data?.data.threads[0]?.posts[0]?.seen).toBe(true);
    });
  });

  // 失敗したら読み直す（異常系）
  test("use_mark_thread_seen_when_error", async () => {
    // 準備
    server.use(
      http.get("/api/threads", () => HttpResponse.json(unseenThreads)),
      http.post("/api/threads/:id/seen", () => HttpResponse.json({ type: "about:blank", title: "Internal Server Error", status: 500, detail: "書けません" }, { status: 500, headers: { "Content-Type": "application/problem+json" } })),
    );
    const { result, queryClient } = await renderPreviewHook("/", useMarkThreadSeen);
    await queryClient.fetchQuery(threadsQuery());
    // 実行
    await act(async () => {
      await result.current.mutateAsync("TH-1").catch(() => undefined);
    });
    // 検証
    await waitFor(() => {
      const data = queryClient.getQueryData(threadsQuery().queryKey) as { data: typeof unseenThreads } | undefined;
      expect(data?.data.threads[0]?.posts[0]?.seen).toBe(false);
    });
  });
});
