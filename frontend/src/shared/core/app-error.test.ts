import { describe, expect, test } from "vitest";

import { AppError } from "@/shared/core/app-error";

describe("AppError.fromResponse", () => {
  // problem+json から作る（正常系）
  test("from_response", () => {
    // 実行
    const error = AppError.fromResponse({ type: "about:blank", title: "Unprocessable Entity", status: 422, detail: "合わない" }, 422);
    // 検証
    expect(error.statusCode).toBe(422);
    expect(error.message).toBe("合わない");
  });

  // problem+json でない本文（正常系）
  test("from_response_when_not_problem", () => {
    // 実行
    const error = AppError.fromResponse(null, 500);
    // 検証
    expect(error.statusCode).toBe(500);
    expect(error.message).toBe("HTTP 500");
  });
});
