import { act, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { useSaveDisplayDefault } from "@/features/settings/display-settings/use-save-display-default";
import { AppError } from "@/shared/core/app-error";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";
import { useQuery } from "@tanstack/react-query";
import { recordsQuery } from "@/shared/hooks/preview-queries";
import { RECORDS } from "@/testing/msw/handlers";
import { gateRefetch } from "@/testing/gated-get";

const queryKeys = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.map(([filters]) => (filters as { queryKey?: unknown } | undefined)?.queryKey);

describe("useSaveDisplayDefault", () => {
  // 読み直す（正常系）
  test("use_save_display_default", async () => {
    // 準備
    server.use(http.put("/api/config/display", () => HttpResponse.json({ display: { visible_kinds: ["decisions"] } })));
    const { result, queryClient } = await renderPreviewHook("/", useSaveDisplayDefault);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    const saved = await act(() => result.current.mutateAsync({ visible_kinds: ["decisions"] }));
    // 検証
    expect(saved).toMatchObject({ visible_kinds: ["decisions"] });
    expect(queryKeys(invalidate)).toContainEqual(["/api/records"]);
  });

  // 書けない（異常系）
  test("use_save_display_default_when_error", async () => {
    // 準備
    server.use(
      http.put("/api/config/display", () =>
        HttpResponse.json({ type: "about:blank", title: "Forbidden", status: 403, detail: "config.yaml に書けません" }, { status: 403, headers: { "Content-Type": "application/problem+json" } }),
      ),
    );
    const { result } = await renderPreviewHook("/", useSaveDisplayDefault);
    // 実行
    const error = await result.current.mutateAsync({ visible_kinds: [] }).catch((reason: unknown) => reason);
    // 検証
    expect(error).toBeInstanceOf(AppError);
    expect((error as AppError).message).toBe("config.yaml に書けません");
  });

  // 再読み込みが終わるまで pending（正常系）
  test("use_save_display_default_pending_until_refetched", async () => {
    // 準備
    server.use(http.put("/api/config/display", () => HttpResponse.json({ display: { visible_kinds: ["decisions"] } })));
    const gate = gateRefetch("*/api/records", RECORDS);
    const { result } = await renderPreviewHook("/", () => ({ query: useQuery(recordsQuery()), save: useSaveDisplayDefault() }));
    await waitFor(() => { expect(result.current.query.isSuccess).toBe(true); });
    // 実行
    act(() => { void result.current.save.mutateAsync({ visible_kinds: ["decisions"] }); });
    // 検証
    await waitFor(() => { expect(gate.gets).toBe(2); });
    expect(result.current.save.isPending).toBe(true);
    act(() => { gate.release(); });
    await waitFor(() => { expect(result.current.save.isPending).toBe(false); });
  });
});
