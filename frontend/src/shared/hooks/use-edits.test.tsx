import { act, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { AppError } from "@/shared/core/app-error";
import { useAddEdit, useCancelEdit, useSaveEdits } from "@/shared/hooks/use-edits";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

describe("useAddEdit", () => {
  // 読み直す（正常系）
  test("use_add_edit", async () => {
    // 準備
    const { result, queryClient } = await renderPreviewHook("/", useAddEdit);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    await act(() => result.current.mutateAsync({ op: "set", target: "D-1", key: "answer", value: "答え" }));
    // 検証
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toContainEqual(["/api/edits"]);
  });

  // 400 の detail（異常系）
  test("use_add_edit_when_error", async () => {
    // 準備
    server.use(http.post("/api/edits", () => HttpResponse.json({ type: "about:blank", title: "Bad Request", status: 400, detail: "編集できないキーです" }, { status: 400, headers: { "Content-Type": "application/problem+json" } })));
    const { result } = await renderPreviewHook("/", useAddEdit);
    // 実行
    const error = await result.current.mutateAsync({ op: "set", target: "D-1", key: "updated_by", value: "user" }).catch((reason: unknown) => reason);
    // 検証
    expect(error).toBeInstanceOf(AppError);
    expect((error as AppError).detail).toBe("編集できないキーです");
  });
});

describe("useCancelEdit", () => {
  // 読み直す（正常系）
  test("use_cancel_edit", async () => {
    // 準備
    const { result, queryClient } = await renderPreviewHook("/", useCancelEdit);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    await act(() => result.current.mutateAsync("E-1"));
    // 検証
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toContainEqual(["/api/edits"]);
  });
});

describe("useSaveEdits", () => {
  // 記録を読み直す（正常系）
  test("use_save_edits", async () => {
    // 準備
    const { result, queryClient } = await renderPreviewHook("/", useSaveEdits);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    await act(() => result.current.mutateAsync());
    // 検証
    await waitFor(() => expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toEqual([["/api/records"], ["/api/comments"], ["/api/edits"], ["/api/threads"]]));
  });

  // 書き込めない編集（異常系）
  test("use_save_edits_when_blocked", async () => {
    // 準備
    const blocked = [{ id: "E-1", reason: "changed", detail: "書き換わった", refs: [] }];
    server.use(http.post("/api/edits/save", () => HttpResponse.json({ type: "about:blank", title: "Conflict", status: 409, detail: "書き込めません", blocked }, { status: 409, headers: { "Content-Type": "application/problem+json" } })));
    const { result } = await renderPreviewHook("/", useSaveEdits);
    // 実行
    const reply = await act(() => result.current.mutateAsync());
    // 検証
    expect(reply.blocked).toEqual(blocked);
  });
});
