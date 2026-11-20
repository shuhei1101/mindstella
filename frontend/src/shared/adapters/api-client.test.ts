import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test } from "vitest";

import { apiClient } from "@/shared/adapters/api-client";
import { AppError } from "@/shared/core/app-error";
import { server } from "@/testing/msw/server";

describe("apiClient", () => {
  afterEach(() => {
    history.replaceState(null, "", "/");
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
    history.replaceState(null, "", "/w/mindstella-x-1/spa/");
    server.use(http.get("/w/mindstella-x-1/api/records", () => HttpResponse.json({ value: 2 })));
    // 実行
    const response = await apiClient<{ data: { value: number }; status: number }>("/api/records");
    // 検証
    expect(response.data).toEqual({ value: 2 });
    expect(response.status).toBe(200);
  });
});
