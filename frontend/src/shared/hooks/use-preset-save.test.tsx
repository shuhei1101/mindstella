import { renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vitest";

import { usePresetSave } from "@/shared/hooks/use-preset-save";
import { server } from "@/testing/msw/server";

const EXPR = { field: "tags", op: "eq", values: ["画面"] } as const;

describe("usePresetSave", () => {
  // 名前と式を送信する（正常系）
  test("use_preset_save", async () => {
    // 準備
    const posted = vi.fn<(body: unknown) => Response>(() => HttpResponse.json({ preset: { name: "画面の設計", filter: EXPR }, count: 1 }, { status: 201 }));
    server.use(http.post("/api/presets", async ({ request }) => posted(await request.json())));
    const { result } = renderHook(() => usePresetSave(EXPR));
    // 実行
    const saved = await result.current("画面の設計");
    // 検証
    expect(saved).toEqual({ error: null });
    expect(posted).toHaveBeenCalledWith({ name: "画面の設計", filter: EXPR });
  });

  // 問題の応答の detail を返す（異常系）
  test.each([
    { status: 409, detail: "同じ名前のプリセット「画面の設計」が既にあります。", expected: "同じ名前のプリセット「画面の設計」が既にあります。" },
    { status: 500, detail: "書けません", expected: "保存できませんでした。もう一度お試しください。" },
  ])("use_preset_save_when_problem", async ({ status, detail, expected }) => {
    // 準備
    server.use(http.post("/api/presets", () => HttpResponse.json({ type: "about:blank", title: "error", status, detail }, { status, headers: { "Content-Type": "application/problem+json" } })));
    const { result } = renderHook(() => usePresetSave(EXPR));
    // 実行
    const saved = await result.current("画面の設計");
    // 検証
    expect(saved).toEqual({ error: expected });
  });
});
