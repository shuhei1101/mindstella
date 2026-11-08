import { act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { AppError } from "@/shared/core/app-error";
import { useAddComment, useRemoveComment, useSaveDraft, useSendComments, useUpdateComment } from "@/shared/hooks/use-comments";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

const queryKeys = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.map(([filters]) => (filters as { queryKey?: unknown } | undefined)?.queryKey);

afterEach(() => {
  vi.useRealTimers();
});

describe("useAddComment", () => {
  // 読み直す（正常系）
  test("use_add_comment", async () => {
    // 準備
    server.use(http.post("/api/comments", () => HttpResponse.json({ id: "C-3", created: "2026-11-01T00:00:00+00:00", count: 3 }, { status: 201 })));
    const { result, queryClient } = await renderPreviewHook("/", useAddComment);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    await act(() => result.current.mutateAsync({ target: "D-1", loc: null, body: "本文" }));
    // 検証
    expect(queryKeys(invalidate)).toContainEqual(["/api/comments"]);
  });

  // 届かない（異常系）
  test("use_add_comment_when_unreachable", async () => {
    // 準備
    server.use(http.post("/api/comments", () => HttpResponse.error()));
    const { result } = await renderPreviewHook("/", useAddComment);
    // 実行
    const error = await result.current.mutateAsync({ target: "D-1", loc: null, body: "本文" }).catch((reason: unknown) => reason);
    // 検証
    expect(error).not.toBeInstanceOf(AppError);
    expect(error).toBeInstanceOf(Error);
  });
});

describe("useUpdateComment", () => {
  // 箇所を外す（正常系）
  test("use_update_comment", async () => {
    // 準備
    const bodies: unknown[] = [];
    server.use(
      http.patch("/api/comments/:id", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ id: "C-1", body: "本文", loc: null });
      }),
    );
    const { result } = await renderPreviewHook("/", useUpdateComment);
    // 実行
    await act(() => result.current.mutateAsync({ id: "C-1", loc: null }));
    // 検証
    expect(bodies).toEqual([{ loc: null }]);
  });
});

describe("useRemoveComment", () => {
  // 中身を返す（正常系）
  test("use_remove_comment", async () => {
    // 準備
    server.use(http.delete("/api/comments/:id", () => HttpResponse.json({ id: "C-1", target: "D-1", loc: null, body: "本文", created: "2026-11-01T00:00:00+00:00", count: 1 })));
    const { result } = await renderPreviewHook("/", useRemoveComment);
    // 実行
    const removed = await act(() => result.current.mutateAsync("C-1"));
    // 検証
    expect(removed).toMatchObject({ id: "C-1", created: "2026-11-01T00:00:00+00:00" });
  });
});

describe("useSendComments", () => {
  // 読み直す（正常系）
  test("use_send_comments", async () => {
    // 準備
    server.use(http.post("/api/comments/send", () => HttpResponse.json({ sent: "2026-11-01T00:00:00+00:00", items: [], entered: true }, { status: 201 })));
    const { result, queryClient } = await renderPreviewHook("/", useSendComments);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    await act(() => result.current.mutateAsync(["C-1"]));
    // 検証
    expect(queryKeys(invalidate)).toEqual(expect.arrayContaining([["/api/comments"], ["/api/threads"]]));
  });

  // 箇所が合わない（異常系）
  test("use_send_comments_when_stale", async () => {
    // 準備
    server.use(
      http.post("/api/comments/send", () =>
        HttpResponse.json(
          { type: "about:blank", title: "Conflict", status: 409, detail: "箇所が合いません", stale: [{ id: "C-1", reason: "本文の 3 行目がありません" }] },
          { status: 409, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const { result, queryClient } = await renderPreviewHook("/", useSendComments);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    const error = await result.current.mutateAsync(["C-1"]).catch((reason: unknown) => reason);
    // 検証
    expect(error).toBeInstanceOf(AppError);
    expect((error as AppError).body).toMatchObject({ stale: [{ id: "C-1" }] });
    expect(queryKeys(invalidate)).not.toContainEqual(["/api/comments"]);
  });
});

describe("useSaveDraft", () => {
  // 止まってから送る（正常系）
  test("use_save_draft", async () => {
    // 準備
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let calls = 0;
    server.use(
      http.put("/api/drafts", () => {
        calls += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { result } = await renderPreviewHook("/", useSaveDraft);
    // 実行
    act(() => {
      result.current({ target: "D-1", loc: null, thread: null, body: "一" });
      result.current({ target: "D-1", loc: null, thread: null, body: "一二" });
      result.current({ target: "D-1", loc: null, thread: null, body: "一二三" });
    });
    await act(() => vi.advanceTimersByTimeAsync(600));
    // 検証
    expect(calls).toBe(1);
  });
});
