import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { apiClient } from "@/shared/adapters/api-client";
import { AppError } from "@/shared/core/app-error";
import { resetEmbeddedDataForTest } from "@/shared/core/embedded";
import { server } from "@/testing/msw/server";

describe("apiClient", () => {
  afterEach(() => {
    history.replaceState(null, "", "/");
    document.body.replaceChildren();
    resetEmbeddedDataForTest();
    vi.restoreAllMocks();
  });

  // 成功の本文を返す（正常系）
  test("api_client", async () => {
    // 準備
    server.use(http.get("/api/example", () => HttpResponse.json({ value: 1 })));
    // 実行
    const response = await apiClient<{ data: { value: number }; status: number }>("/api/example");
    // 検証
    expect(response.data).toEqual({ value: 1 });
    expect(response.status).toBe(200);
  });

  // 失敗を AppError にする（異常系）
  test("api_client_when_error", async () => {
    // 準備
    server.use(
      http.get("/api/example", () =>
        HttpResponse.json({ type: "about:blank", title: "Unprocessable Entity", status: 422, detail: "合わない" }, { status: 422 }),
      ),
    );
    // 実行・検証
    await expect(apiClient("/api/example")).rejects.toMatchObject({ constructor: AppError, statusCode: 422, message: "合わない" });
  });

  // ワークスペースのパスの頭を付けて呼ぶ（正常系）
  test("api_client_when_workspace_path", async () => {
    // 準備
    history.replaceState(null, "", "/w/mindstella-x-1/");
    server.use(http.get("/w/mindstella-x-1/api/records", () => HttpResponse.json({ value: 2 })));
    // 実行
    const response = await apiClient<{ data: { value: number }; status: number }>("/api/records");
    // 検証
    expect(response.data).toEqual({ value: 2 });
    expect(response.status).toBe(200);
  });

  // 配る書き出しは埋め込みから応答を作り fetch を呼ばない（正常系）
  test("api_client_when_embedded", async () => {
    // 準備
    const data = document.createElement("script");
    data.type = "application/json";
    data.id = "mindmap-data";
    data.textContent = '{"settings":{"summary":"家計簿"}}';
    document.body.append(data);
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    // 実行
    const response = await apiClient<{ data: unknown; status: number }>("/api/records");
    const written = apiClient("/api/comments", { method: "POST", body: "{}" });
    // 検証
    expect(response.data).toEqual({ settings: { summary: "家計簿" } });
    expect(response.status).toBe(200);
    await expect(written).rejects.toMatchObject({ constructor: AppError, statusCode: 404 });
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
