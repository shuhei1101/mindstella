import { act, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { useItemConfirmed } from "@/shared/hooks/use-item-confirmed";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

const ok = () => http.put("/api/items/:id/confirmed", async ({ request, params }) => {
  await delay(50);
  const body = (await request.json()) as { confirmed: boolean };
  return HttpResponse.json({ id: params.id, confirmed: body.confirmed });
});

describe("useItemConfirmed", () => {
  // 押した直後に押した後の値を描き、成功で記録を読み直す（正常系）
  test("use_item_confirmed", async () => {
    // 準備
    server.use(ok());
    const { result, queryClient } = await renderPreviewHook("/", () => useItemConfirmed("D-1", false));
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    act(() => result.current.toggle());
    // 検証
    await waitFor(() => expect(result.current.saving).toBe(true));
    expect(result.current.confirmed).toBe(true);
    await waitFor(() => expect(result.current.saving).toBe(false));
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toContainEqual(["/api/records"]);
    expect(result.current.error).toBeNull();
  });

  // 失敗で元の値に戻し、次に押すと文を消す（異常系）
  test("use_item_confirmed_when_failed", async () => {
    // 準備
    server.use(http.put("/api/items/:id/confirmed", () => HttpResponse.json({ type: "about:blank", title: "Internal Server Error", status: 500, detail: "書き込めませんでした: history.yaml" }, { status: 500, headers: { "Content-Type": "application/problem+json" } })));
    const { result } = await renderPreviewHook("/", () => useItemConfirmed("D-1", false));
    // 実行
    act(() => result.current.toggle());
    // 検証
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toContain("確認済みを書き換えられませんでした。");
    expect(result.current.error).toContain("書き込めませんでした: history.yaml");
    expect(result.current.confirmed).toBe(false);
    server.use(ok());
    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.error).toBeNull());
  });
});
