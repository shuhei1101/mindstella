import { act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { useSaveDisplayDefault } from "@/features/settings/display-settings/use-save-display-default";
import { AppError } from "@/shared/core/app-error";
import { server } from "@/testing/msw/server";
import { renderPreviewHook } from "@/testing/render";

const queryKeys = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.map(([filters]) => (filters as { queryKey?: unknown } | undefined)?.queryKey);

describe("useSaveDisplayDefault", () => {
  // 読み直す（正常系）
  test("use_save_display_default", async () => {
    // 準備
    server.use(http.put("/api/config/display", () => HttpResponse.json({ display: { network_look: "deep", visible_kinds: ["decisions"] } })));
    const { result, queryClient } = await renderPreviewHook("/", useSaveDisplayDefault);
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    // 実行
    const saved = await act(() => result.current.mutateAsync({ network_look: "deep", visible_kinds: ["decisions"] }));
    // 検証
    expect(saved).toMatchObject({ network_look: "deep", visible_kinds: ["decisions"] });
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
    const error = await result.current.mutateAsync({ network_look: "deep", visible_kinds: [] }).catch((reason: unknown) => reason);
    // 検証
    expect(error).toBeInstanceOf(AppError);
    expect((error as AppError).message).toBe("config.yaml に書けません");
  });
});
